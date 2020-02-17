"""


Issues:
    - The waitStop property for moving doesn't really work, and if you send two move commands quickly after each other,
    the system doesn't react fast enough and doesn't reach the final destination.
"""
from __future__ import print_function

from builtins import map
from builtins import hex
from builtins import str
from builtins import range
import time

from nplab.instrument.serial_instrument import SerialInstrument
from nplab.instrument.stage import Stage

# never wait for more than this e.g. during wait_states
MAX_WAIT_TIME_SEC = 20

# time to wait after sending a command. This number has been arrived at by
# trial and error
COMMAND_WAIT_TIME_SEC = 1

# States from page 65 of the manual
STATE_NOT_REFERENCED_FROM_RESET = '0A'
STATE_NOT_REFERENCED_FROM_CONFIGURATION = '0C'
STATE_READY_FROM_HOMING = '32'
STATE_READY_FROM_MOVING = '33'

STATE_CONFIGURATION = '14'

STATE_DISABLE_FROM_READY = '3C'
STATE_DISABLE_FROM_MOVING = '3D'
STATE_DISABLE_FROM_JOGGING = '3E'


class SMC100ReadTimeOutException(Exception):
    def __init__(self):
        super(SMC100ReadTimeOutException, self).__init__('Read timed out')


class SMC100WaitTimedOutException(Exception):
    def __init__(self):
        super(SMC100WaitTimedOutException, self).__init__('Wait timed out')


class SMC100DisabledStateException(Exception):
    def __init__(self, state):
        super(SMC100DisabledStateException, self).__init__('Disabled state encountered: ' + state)


class SMC100RS232CorruptionException(Exception):
    def __init__(self, c):
        super(SMC100RS232CorruptionException, self).__init__('RS232 corruption detected: %s' % (hex(ord(c))))


class SMC100InvalidResponseException(Exception):
    def __init__(self, cmd, resp):
        s = 'Invalid response to %s: %s' % (cmd, resp)
        super(SMC100InvalidResponseException, self).__init__(s)


class SMC100(SerialInstrument, Stage):
    """
    Class to interface with Newport's SMC100 controller.
    The SMC100 accepts commands in the form of:
      <ID><command><arguments><CR><LF>
    Reply, if any, will be in the form
      <ID><command><result><CR><LF>
    There is minimal support for manually setting stage parameter as Newport's
    ESP stages can supply the SMC100 with the correct configuration parameters.
    Some effort is made to take up backlash, but this should not be trusted too
    much.
    The move commands must be used with care, because they make assumptions
    about the units which is dependent on the STAGE. I only have TRB25CC, which
    has native units of mm. A more general implementation will move the move
    methods into a stage class.
    """

    def __init__(self, port, smcID=(1, ), **kwargs):
        """
        If backlash_compensation is False, no backlash compensation will be done.
        If silent is False, then additional output will be emitted to aid in
        debugging.
        If sleepfunc is not None, then it will be used instead of time.sleep. It
        will be given the number of seconds (float) to sleep for, and is provided
        for ease integration with single threaded GUIs.
        Note that this method only connects to the controller, it otherwise makes
        no attempt to home or configure the controller for the attached stage. This
        delibrate to minimise realworld side effects.
        If the controller has previously been configured, it will suffice to simply
        call home() to take the controller out of not referenced mode. For a brand
        new controller, call reset_and_configure().
        """
        self.port_settings = dict(baudrate=57600,
                    bytesize=8,
                    stopbits=1,
                    parity='N',
                    xonxoff=True,
                    timeout=0.050)

        SerialInstrument.__init__(self, port)
        Stage.__init__(self)
        # self._logger.debug('Connecting to SMC100 on %s' % (port))

        self.software_home = None
        self._last_sendcmd_time = 0
        if not hasattr(smcID, '__iter__'):
            smcID = (smcID, )
        self._smcID = list(smcID)
        self.axis_names = ()
        for id in self._smcID:
            self.axis_names += (str(id), )
            self._send_cmd('ID', id, '?', True)  # Just testing the connection

    def __del__(self):
        self.close()

    def _send_cmd(self, command, axes=None, argument=None, expect_response=False, retry=False):
        """
        Send the specified command along with the argument, if any. The response
        is checked to ensure it has the correct prefix, and is returned WITHOUT
        the prefix.
        It is important that for GET commands, e.g. 1ID?, the ? is specified as an
        ARGUMENT, not as part of the command. Doing so will result in assertion
        failure.
        If expect_response is True, a response is expected from the controller
        which will be verified and returned without the prefix.
        If expect_response is True, and retry is True or an integer, then when the
        response does not pass verification, the command will be sent again for
        retry number of times, or until success if retry is True.
        The retry option MUST BE USED CAREFULLY. It should ONLY be used read-only
        commands, because otherwise REPEATED MOTION MIGHT RESULT. In fact some
        commands are EXPLICITLY REJECTED to prevent this, such as relative move.
        """
        if axes is None:
            axes = self.axis_names #self._smcID[0]
        elif not hasattr(axes, '__iter__'):
            axes = (axes, )

        reply = ()
        for axis in axes:
            if type(axis) != str:
                axis = str(axis)
            assert command[-1] != '?'

            if argument is None:
                argument = ''

            prefix = axis + command
            tosend = prefix + str(argument)

            # prevent certain commands from being retried automatically
            no_retry_commands = ['PR', 'OR']
            if command in no_retry_commands:
                retry = False

            done = False
            while not done:
                if expect_response:
                    self.ser.flushInput()

                self.ser.flushOutput()

                self.ser.write(tosend)
                self.ser.write('\r\n')

                self.ser.flush()

                if expect_response:
                    try:
                        response = self._readline()
                        if response.startswith(prefix):
                            reply += (response[len(prefix):], )
                            done = True
                        else:
                            raise SMC100InvalidResponseException(command, response)
                    except Exception as ex:
                        if not retry or retry <= 0:
                            raise ex
                        else:
                            if type(retry) == int:
                                retry -= 1
                            continue
                else:
                    # we only need to delay when we are not waiting for a response
                    now = time.time()
                    dt = now - self._last_sendcmd_time
                    dt = COMMAND_WAIT_TIME_SEC - dt
                    # print dt
                    if dt > 0:
                        time.sleep(dt)
                    self._last_sendcmd_time = now
                    done = True
                    # return None
        return reply

    def _readline(self):
        """
        Returns a line, that is reads until \r\n.
        OK, so you are probably wondering why I wrote this. Why not just use
        self.ser.readline()?
        I am glad you asked.
        With python < 2.6, pySerial uses serial.FileLike, that provides a readline
        that accepts the max number of chars to read, and the end of line
        character.
        With python >= 2.6, pySerial uses io.RawIOBase, whose readline only
        accepts the max number of chars to read. io.RawIOBase does support the
        idea of a end of line character, but it is an attribute on the instance,
        which makes sense... except pySerial doesn't pass the newline= keyword
        argument along to the underlying class, and so you can't actually change
        it.
        """
        done = False
        line = str()
        # print 'reading line',
        while not done:
            c = self.ser.read()
            # ignore \r since it is part of the line terminator
            if len(c) == 0:
                raise SMC100ReadTimeOutException()
            elif c == '\r':
                continue
            elif c == '\n':
                done = True
            elif ord(c) > 32 and ord(c) < 127:
                line += c
            else:
                raise SMC100RS232CorruptionException(c)

        return line

    def _wait_states(self, targetstates, ignore_disabled_states=False):
        """
        Waits for the controller to enter one of the the specified target state.
        Controller state is determined via the TS command.
        If ignore_disabled_states is True, disable states are ignored. The normal
        behaviour when encountering a disabled state when not looking for one is
        for an exception to be raised.
        Note that this method will ignore read timeouts and keep trying until the
        controller responds.  Because of this it can be used to determine when the
        controller is ready again after a command like PW0 which can take up to 10
        seconds to execute.
        If any disable state is encountered, the method will raise an error,
        UNLESS you were waiting for that state. This is because if we wait for
        READY_FROM_MOVING, and the stage gets stuck we transition into
        DISABLE_FROM_MOVING and then STAY THERE FOREVER.
        The state encountered is returned.
        """
        starttime = time.time()
        done = [False]*len(self.axis_names)
        self._logger.debug('waiting for states %s' % (str(targetstates)))
        while not all(done):
            for axes in range(len(self.axis_names)):
                waittime = time.time() - starttime
                if waittime > MAX_WAIT_TIME_SEC:
                    raise SMC100WaitTimedOutException()

                try:
                    state = self.get_status()[axes][1]
                    if state in targetstates:
                        self._logger.debug('in state %s' % (state))
                        done[axes] = True
                        # return state
                    elif not ignore_disabled_states:
                        disabledstates = [
                            STATE_DISABLE_FROM_READY,
                            STATE_DISABLE_FROM_JOGGING,
                            STATE_DISABLE_FROM_MOVING]
                        if state in disabledstates:
                            raise SMC100DisabledStateException(state)

                except SMC100ReadTimeOutException:
                    self._logger.info('Read timed out, retrying in 1 second')
                    time.sleep(1)
                    continue

    def reset_and_configure(self):
        """
        Configures the controller by resetting it and then asking it to load
        stage parameters from an ESP compatible stage. This is then followed
        by a homing action.
        """
        self._send_cmd('RS')
        self._send_cmd('RS')

        self._wait_states(STATE_NOT_REFERENCED_FROM_RESET, ignore_disabled_states=True)

        stage = self._send_cmd('ID', '?', True)
        self._logger.info('Found stage %s' %stage)

        # enter config mode
        self._send_cmd('PW', 1)
        self._wait_states(STATE_CONFIGURATION)

        # load stage parameters
        self._send_cmd('ZX', 1)

        # enable stage ID check
        self._send_cmd('ZX', 2)

        # exit configuration mode
        self._send_cmd('PW', 0)

        # wait for us to get back into NOT REFERENCED state
        self._wait_states(STATE_NOT_REFERENCED_FROM_CONFIGURATION)

    def get_position(self, axis=None):
        pos = self._send_cmd('TP', axes=axis, argument='?', expect_response=True, retry=10)
        pos = list(map(float, pos))
        return pos

    def home(self, **kwargs):
        """
        Homes the controller. If waitStop is True, then this method returns when
        homing is complete.
        Note that because calling home when the stage is already homed has no
        effect, and homing is generally expected to place the stage at the
        origin, an absolute move to 0 um is executed after homing. This ensures
        that the stage is at origin after calling this method.
        Calling this method is necessary to take the controller out of not referenced
        state after a restart.
        """
        self._send_cmd('OR')
        if 'waitStop' in kwargs and kwargs['waitStop']:
            # wait for the controller to be ready
            st = self._wait_states((STATE_READY_FROM_HOMING, STATE_READY_FROM_MOVING))
            if st == STATE_READY_FROM_MOVING:
                self.move([0]*len(self.axis_names), **kwargs)
        else:
            self.move([0]*len(self.axis_names), **kwargs)

    def stop(self):
        self._send_cmd('ST')

    def get_status(self):
        """
        Executes TS? and returns the the error code as integer and state as string
        as specified on pages 64 - 65 of the manual.
        """

        resps = self._send_cmd('TS', argument='?', expect_response=True, retry=10)
        reply = ()
        for resp in resps:
            errors = int(resp[0:4], 16)
            state = resp[4:]
            assert len(state) == 2
            reply += ([errors, state], )

        return reply

    def move(self, pos, axis=None, relative=False, waitStop=True):
        if axis is None:
            axis = self.axis_names
        if not hasattr(pos, '__iter__'):
            pos = [pos]
        if relative:
            index = 0
            for ax in axis:
                self._send_cmd('PR', axes=ax, argument=pos[index])
                index += 1
        else:
            index = 0
            for ax in axis:
                self._send_cmd('PA', axes=ax, argument=pos[index])
                index += 1

        if waitStop:
            # If we were previously homed, then something like PR0 will have no
            # effect and we end up waiting forever for ready from moving because
            # we never left ready from homing. This is why STATE_READY_FROM_HOMING
            # is included.
            self._wait_states((STATE_READY_FROM_MOVING, STATE_READY_FROM_HOMING))

    def move_referenced(self, position_mm, **kwargs):
        """
        Moves to an absolute position referenced from the software home

        Args:
            position_mm: position from the software home
            **kwargs: kwargs to be passed to the move command

        Returns:

        """

        if not hasattr(position_mm, '__iter__'):
            position_mm = (position_mm, )

        final_pos = list(map(lambda x, y: x+y, self.software_home, position_mm))

        self.move(final_pos, **kwargs)

    def set_software_home(self):
        """
        Sets a software home, so that we can easily go back to similar sample positions

        Returns:

        """
        self.software_home = self.get_position()

    def go_software_home(self):
        self.move_referenced([0]*len(self.axis_names))

    def set_velocity(self, velocity):
        self._send_cmd('VA_Set', velocity)

    # def get_qt_ui(self):
    #     return SMC100UI(self)


# class SMC1002axis(instruments.InstrumentBase):
#     metadata = {'software_home', 'CurPos'}
#
#     def get_single_metadata(self, name):
#         if name == 'CurPos':
#             self.get_position_mm()
#         return getattr(self, name)
#
#     def __init__(self, port, backlash_compensation=True, sleepfunc=None, **kwargs):
#         instruments.InstrumentBase.__init__(self, **kwargs)
#
#         self.axisV = SMC100(1, port, backlash_compensation, sleepfunc, **kwargs)
#         self.axisH = SMC100(2, self.axisV._port, backlash_compensation, sleepfunc, **kwargs)
#
#         self.axisH._port = self.axisV._port
#
#         self.software_home = (0, 0)
#         self.CurPos = (0, 0)
#
#     def __del__(self):
#         del self.axisH
#         del self.axisV
#
#     def set_software_home(self, home_val=None):
#         # if home_val is None:
#         #     self.axisH.set_software_home()
#         #     time.sleep(0.1)
#         #     self.axisV.set_software_home()
#         # else:
#         #     self.axisH.software_home = home_val[1]
#         #     self.axisV.software_home = home_val[0]
#         self.software_home = self.get_position_mm()
#         self.axisV.software_home = self.software_home[0]
#         self.axisH.software_home = self.software_home[1]
#         # self.software_home = (self.axisV.software_home, self.axisH.software_home)
#
#     def go_software_home(self):
#         self.move_absolute_mm(self.software_home)
#         # self.axisV.move_absolute_mm(self.software_home[0])
#         # time.sleep(0.1)
#         # self.axisH.move_absolute_mm(self.software_home[1])
#         #
#         # self.get_position_mm()
#
#     def home(self, waitStop=True):
#         self.axisH.home(waitStop)
#         self.axisV.home(waitStop)
#
#         self.get_position_mm()
#
#     def move_absolute_mm(self, (vertPos, horzPos), waitStop=True):
#         self.CurPos = (vertPos, horzPos)
#
#         self.axisV.move_absolute_mm(vertPos, waitStop=False)
#         time.sleep(0.1)
#         self.axisH.move_absolute_mm(horzPos, waitStop=False)
#
#         if waitStop:
#             self.axisH._wait_states((STATE_READY_FROM_MOVING, STATE_READY_FROM_HOMING))
#             self.axisV._wait_states((STATE_READY_FROM_MOVING, STATE_READY_FROM_HOMING))
#         self.updateGUI.emit()
#
#     def move_abs_homed_mm(self, (vertPos, horzPos), waitStop=True):
#         """
#         :param (vertPos, horzPos):
#         :param waitStop:
#         :return:
#         """
#         self.CurPos = (vertPos, horzPos)
#
#         self.axisV.move_abs_homed_mm(vertPos, waitStop=False)
#         time.sleep(0.1)
#         self.axisH.move_abs_homed_mm(horzPos, waitStop=False)
#
#         if waitStop:
#             self.axisH._wait_states((STATE_READY_FROM_MOVING, STATE_READY_FROM_HOMING))
#             self.axisV._wait_states((STATE_READY_FROM_MOVING, STATE_READY_FROM_HOMING))
#         self.updateGUI.emit()
#
#     def move_relative_mm(self, (vertPos, horzPos), waitStop=True):
#         self.CurPos = (vertPos, horzPos)
#
#         self.axisV.move_relative_mm(vertPos, waitStop=False)
#         time.sleep(0.1)
#         self.axisH.move_relative_mm(horzPos, waitStop=False)
#         time.sleep(0.1)
#
#         if waitStop:
#             self.axisH._wait_states((STATE_READY_FROM_MOVING, STATE_READY_FROM_HOMING))
#             self.axisV._wait_states((STATE_READY_FROM_MOVING, STATE_READY_FROM_HOMING))
#         self.updateGUI.emit()
#
#     def get_position_mm(self):
#         posV = self.axisV.get_position_mm()
#         time.sleep(0.1)
#         posH = self.axisH.get_position_mm()
#
#         self.CurPos = (posV, posH)
#
#         self.updateGUI.emit()
#         return (posV, posH)
#
#     def find_image(self, edge_image, start=None):
#         raise NotImplementedError
#         if start is not None:
#             self.axisV.move_absolute_mm(start[0])
#             self.axisH.move_absolute_mm(start[1])
#
#             # Move horizontally until we get to an edge
#             # Move upwards until we get to the image
#
#             # To do:
#             # Figure out how to detect whether we are at an edge
#             # Figure out how to refocus at each sample position
#             # Figure out if cross-correlation can work for centering the image, and calibrate the stage movement to the camera
#
#     def get_qt_ui(self):
#         return SMC100UI(self)


# class SMC100UI(QtWidgets.QWidget):
#     def __init__(self, smc100):
#         if isinstance(smc100, SMC100):
#             self.axes = False
#         elif isinstance(smc100, SMC1002axis):
#             self.axes = True
#         else:
#             raise AssertionError("instrument must be a SMC100")
#
#         super(SMC100UI, self).__init__()
#
#         self.SMC100 = smc100
#         self.signal = QtCore.SIGNAL('SMC100GUIupdate')
#         self.SolsTiSMonitorThread = None
#         self.stepSize = 100
#
#         if self.axes:
#             uic.loadUi(os.path.join(os.path.dirname(__file__), 'uiFiles/smc1002axes.ui'), self)
#             self.lineEditHorzPos.returnPressed.connect(lambda: self.PosChanged())
#             self.lineEditVertPos.returnPressed.connect(lambda: self.PosChanged())
#
#             self.lineEditStepSize.returnPressed.connect(self.StepSizeChanged)
#             self.pushButtonLeft.clicked.connect(lambda: self.Move(dir='l'))
#             self.pushButtonRight.clicked.connect(lambda: self.Move(dir='r'))
#             self.pushButtonUp.clicked.connect(lambda: self.Move(dir='u'))
#             self.pushButtonDown.clicked.connect(lambda: self.Move(dir='d'))
#
#             self.pushButtonGoHome.clicked.connect(self.GoSoftwareHome)
#             self.pushButtonSetHome.clicked.connect(self.SetSoftwareHome)
#         else:
#             uic.loadUi(os.path.join(os.path.dirname(__file__), 'uiFiles/SMC100.ui'), self)
#             self.lineEditPos.returnPressed.connect(self.PosChanged)
#
#         self.SMC100.updateGUI.connect(self.updateGUI)
#
#     def updateGUI(self):
#         if self.axes:
#             horz_pos = self.SMC100.axisH.get_position_mm()
#             vert_pos = self.SMC100.axisV.get_position_mm()
#             self.lineEditHorzPos.setText(str(float('%.3f' % horz_pos)).rstrip('0'))
#             self.lineEditVertPos.setText(str(float('%.3f' % vert_pos)).rstrip('0'))
#         else:
#             pos = self.SMC100.get_position_mm()
#             self.lineEditPos.setText(str(pos))
#
#     def PosChanged(self):
#         if self.axes:
#             horz_pos = float(self.lineEditHorzPos.text())
#             vert_pos = float(self.lineEditVertPos.text())
#
#             self.SMC100.move_absolute_mm((vert_pos, horz_pos))
#         else:
#             pos = float(self.lineEditPos.text())
#             self.SMC100.move_absolute_mm(pos)
#
#     def StepSizeChanged(self):
#         self.stepSize = float(self.lineEditStepSize.text())
#
#     def Move(self, dir):
#         if dir == 'l':
#             # self.SMC100.axisH.move_relative_um(self.stepSize)
#             self.SMC100.move_relative_mm((0, self.stepSize * 1e-3))
#         if dir == 'r':
#             # self.SMC100.axisH.move_relative_um(-self.stepSize)
#             self.SMC100.move_relative_mm((0, -self.stepSize * 1e-3))
#         if dir == 'u':
#             # self.SMC100.axisV.move_relative_um(self.stepSize)
#             self.SMC100.move_relative_mm((self.stepSize * 1e-3, 0))
#         if dir == 'd':
#             # self.SMC100.axisV.move_relative_um(-self.stepSize)
#             self.SMC100.move_relative_mm((-self.stepSize * 1e-3, 0))
#
#     def SetSoftwareHome(self):
#         self.SMC100.set_software_home()
#
#     def GoSoftwareHome(self):
#         self.SMC100.go_software_home()


# Tests #####################################################################



if __name__ == '__main__':
    smc100 = SMC100('COM13', (1,2))
    print('Axes: ', smc100.axis_names)

    print(smc100.get_position()) #_mm() #get_position()
    print(smc100.get_status())

    smc100.show_gui()

    # smc100.show_gui()
    # test_configure()

    # test_general()

    # test_GUI()
