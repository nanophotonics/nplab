"""
This is an interface module for instruments produced by Sigma Koki

__author__: Yago
"""

from nplab.utils.thread_utils import locked_action
from nplab.instrument.stage import Stage
from nplab.instrument.serial_instrument import SerialInstrument
import exceptions, time


class GSC01(SerialInstrument, Stage):
    """
    Stage controller GSC-01
    """

    counts_per_degree = 400.
    axis_names = ('1', )
    metadata_property_names = ('position', )

    def __init__(self, address, **kwargs):

        self.port_settings = dict(baudrate=9600,
                                  bytesize=8,
                                  stopbits=1,
                                  parity='N',
                                  xonxoff=True,
                                  timeout=0.5,
                                  writeTimeout=0.5,
                                  rtscts=True
                                  )
        SerialInstrument.__init__(self, address)
        self.termination_character = '\r\n'
        Stage.__init__(self)

        if 'offsetOrigin' in kwargs:
            self.offsetOrigin(kwargs['offsetOrigin'])  # 20000)

        if 'home_on_start' in kwargs.keys():
            if kwargs['home_on_start']:
                self.MechanicalHome()

    def __del__(self):
        try:
            self.ser.close()
        except:
            self._logger.warn("Couldn't close GSC01")

    def wait(self):
        while self.getACK3() != 'R':
            time.sleep(0.1)
            # pass

    def write_cmd(self, command, read=True, wait=False):
        '''
        :param command: serial command to send to device
        :param read: if True, reads out standard 'OK' or 'NG' reply from the GSC-01
        :param fname: name of calling function, only useful when verbose
        :return:
        '''

        self.write(command)

        if read:
            reply = self.readline()
            self._logger.debug('[%s]: %s' % (command, reply))
        else:
            reply = self.readline()
            if reply != 'OK\n':
                self._logger.warn('%s replied %s' % (command, reply))

        if wait:
            self.wait()

        return reply

    def MechanicalHome(self):
        '''
        This command is used to detect the mechanical origin for a stage and set that position as the origin. The moving
        speed S: 500pps, F:5000ps, R:200mS. Running a stop command suspends the operation. Any other commands are not
        acceptable.
        :return:
        '''
        self.write_cmd('H:1', read=False, wait=True)

    def initializeOrigin(self):
        """
        Sets the origin to the current position.
        """
        self.write('R:1')

    def offsetOrigin(self, steps):
        """
        Sets and offset to the homing command, so that the origin is not beside the limit sensors
        Effective only for the homing operation in MINI system. Value is initialised to zero when turning power off.
        :param steps: offset steps (integer)
        :return:
        """

        self.write('S:N%d' % steps)

    @locked_action
    def move(self, pos, axis=None, relative=False, wait=True):
        counts = self.counts_per_degree * pos
        if relative:
            if not (-16777214 <= counts <= 16777214):
                raise exceptions.ValueError('stage1 must be between -16777214 and 16777214.')

            command = 'M:W'
            if counts >= 0:
                command += '+P%d' % counts
            else:
                command += '-P%d' % -counts
        else:
            command = 'A:W'
            if counts >= 0:
                command += '+P%d' % counts
            else:
                command += '-P%d' % -counts
        self.write_cmd(command, read=False)
        self._go()

        if wait:
            t0 = time.time()
            curpos = self.get_position()[0]
            while curpos != pos and time.time()-t0 < 10:
                curpos = self.get_position()[0]
                time.sleep(0.1)

    def get_position(self, axis=None):
        status = self.getStatus()
        counts = status.split(',')[0]
        position = int(counts)/self.counts_per_degree
        self._logger.debug('Status: %s. Counts: %s. Position returned %g' %(status, counts, position))
        return [position]

    def jog(self, direction, timeout=2):
        """
        Moves stage continuously at jogging speed for specified length of time.
        :param direction: either '+' or '-'
        :param timeout: in seconds
        :return:
        """

        self.write('J:1%s' % direction)
        t0 = time.time()
        self._go()
        while time.time() - t0 < timeout:
            time.sleep(0.1)
        self.decelerate()

    def _go(self):
        """
        Moves the stages. To be used internally.
        """
        self.write_cmd('G:', read=False)

    def decelerate(self):
        """
        Decelerates and stop the stages.
        """
        self.write('L:1')

    def stop(self):
        """
        Stops the stages immediately.
        """
        self.write('L:E')

    def setSpeed(self, minSpeed1, maxSpeed1, accelerationTime1):
        """
        Set minimum and maximum speeds and acceleration time.
        :param minSpeed1: between 100 and 20000, in steps of 100 [PPS]
        :param maxSpeed1: between 100 and 20000, in steps of 100 [PPS]
        :param accelerationTime1: between 0 and 1000 [ms]
        :return:
        """
        if not (100 <= minSpeed1 <= maxSpeed1 <= 20000):
            raise exceptions.ValueError('Must be 100 <= minSpeed1 <= maxSpeed1 <= 20000')

        if not (0 <= accelerationTime1 <= 1000):
            raise exceptions.ValueError('Must be 00 <= accelerationTime1 <= 1000.')

        self.write('D:1S%dF%dR%d' % (minSpeed1, maxSpeed1, accelerationTime1))

    def setJogSpeed(self, speed):
        """
        Set jog speed
        :param speed: between 100 and 20000, in steps of 100 [PPS]
        :return:
        """
        if 100 < speed < 20000:
            raise ValueError('Speed must be in 100-20000 range')

        self.write('S:J%d' % speed)

    def enableMotorExcitation(self, stage1=True):
        """
        Turn motor on/off
        :param stage1: True (on) or False (off)
        :return:
        """

        self.write('C:1%d' % stage1)

    def getStatus(self):
        """
        Gets the current status, consisting of position, command status, stop status, and motor readiness
        :return: position, ACK1, ACK2, ACK3
                ACK1:   X   Command Error
                        K   Command accepted normally
                ACK2:   L   Limit Sensor stop
                        K   Normal stop
                ACK3:   B   Busy
                        R   Ready
        """
        return self.write_cmd('Q:')

    def getACK3(self):
        """
        :return: 'R' if motor ready, 'B' if motor busy
        """
        self.write_cmd('!:', read=False)
        return self.readline()

    def getVersion(self):
        """
        Returns the ROM version
        """
        self.write('?:V', read=False)
        return self.readline()


if __name__ == '__main__':
    gsc01 = GSC01('COM14')
    # print 'Line: ', gsc01.readline()
    # gsc01.MechanicalHome()
    # print 'Line: ', gsc01.readline()
    # gsc01.move(0)
    # print 'Line: ', gsc01.readline()
    print 'Status: ', gsc01.getStatus()
    # print 'Line: ', gsc01.readline()
    gsc01.move(10)   # 265140
    print 'Status: ', gsc01.getStatus()
    # gsc01.getStatus()
    # gsc01.move(10)
    # gsc01.getStatus()
    # gsc01.move(0)
    # gsc01.getStatus()

    # print 'Status: ', gsc01.getStatus()
    # print 'ACK3: ', gsc01.getACK3()
    # print 'ACK3: ', gsc01.getACK3()
    # print 'ACK3: ', gsc01.getACK3()
    # print 'ACK3: ', gsc01.getACK3()
    # print gsc01.get_position()
    # gsc01.show_gui()
