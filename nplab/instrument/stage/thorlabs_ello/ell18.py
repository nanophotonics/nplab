'''
author: im354
'''

import sys
from nplab.utils.gui import *
from nplab.ui.ui_tools import *
from nplab.instrument.stage.thorlabs_ello import ElloDevice, bytes_to_binary, twos_complement_to_int


class Ell18(ElloDevice):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.configuration = self.get_device_info()
        self.TRAVEL = self.configuration["travel"]
        self.PULSES_PER_REVOLUTION = self.configuration["pulses"]
        if self.debug > 0:
            print("Travel (degrees):", self.TRAVEL)
            print("Pulses per revolution", self.PULSES_PER_REVOLUTION)
            print("Device status:", self.get_device_status())
    
    def get_position(self, axis=None):
        '''
        Query stage for its current position, in degrees
        This method overrides the Stage class' method
        '''
        response = self.query_device("gp")
        header = response[0:3]
        if header == "{0}PO".format(self.device_index):
            # position given in twos complement representation
            byte_position = response[3:11]
            binary_position = bytes_to_binary(byte_position)
            pulse_position = twos_complement_to_int(binary_position)
            degrees_position = self.TRAVEL * \
                (float(pulse_position)/self.PULSES_PER_REVOLUTION)
            return degrees_position
        else:
            raise ValueError("Incompatible Header received:{}".format(header))
    def move_absolute(self, angle, blocking=True):
        """Move to absolute position relative to home setting

        Args:
            angle (float): angle to move to, specified in degrees.

        Returns:
            None

        Raises:
            None

        """
        if -360 > angle or angle > 360:
            angle %= 360
        if angle < 0:
            angle = 360+angle
        return super().move_absolute(angle, blocking=blocking)
    def get_qt_ui(self):
        return Thorlabs_ELL18K_UI(self)


class Thorlabs_ELL18K_UI(QtWidgets.QWidget, UiTools):

    def __init__(self, stage, parent=None, debug=0):
        if not isinstance(stage, Ell18):
            raise ValueError(
                "Object is not an instance of the Thorlabs_ELL18K Stage")
        super(Thorlabs_ELL18K_UI, self).__init__()
        
        self.stage = stage  # this is the actual rotation stage
        self.parent = parent
        self.debug = debug
        path = os.path.dirname(__file__)
        uic.loadUi(os.path.join(os.path.dirname(
            path), 'thorlabs_ell18k.ui'), self)

        self.move_relative_btn.clicked.connect(self.move_relative)
        self.move_absolute_btn.clicked.connect(self.move_absolute)
        self.move_home_btn.clicked.connect(self.move_home)
        self.current_angle_btn.clicked.connect(self.update_current_angle)

    def move_relative(self):
        try:
            angle = float(self.move_relative_textbox.text())
        except ValueError as e:
            print(e)
            return
        self.stage.move(pos=angle, relative=True)

    def move_absolute(self):
        try:
            angle = float(self.move_absolute_textbox.text())
        except ValueError as e:
            print(e)
            return
        self.stage.move(pos=angle, relative=False)

    def move_home(self):
        self.stage.move_home()

    def update_current_angle(self):
        angle = self.stage.get_position()
        self.current_angle_value.setText(str(angle))


def test_stage(s):
    '''
    Run from main to test stage
    '''
    debug = False

    print("Status", s.get_device_status())
    print("Info", s.get_device_info())
    print("Homing", s.move_home())
    print("Home position", s.get_position())
    angle = 30
    s.move(angle, relative=True)
    print("30==", s.get_position())
    angle = -30
    s.move(angle, relative=True)
    print("-30==", s.get_position())

    angle = 150
    s.move(angle, relative=False)
    print("150==", s.get_position())

    angle = -10
    s.move(angle, relative=False)
    print("350==", s.get_position())


def test_ui():
    '''
    Run from main to test ui + stage
    '''
    s = Ell18("COM11")
    app = get_qt_app()
    ui = Thorlabs_ELL18K_UI(stage=s)
    ui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":

    stage = Ell18("COM11", debug=False)
    app = get_qt_app()
    ui = Thorlabs_ELL18K_UI(stage)
    ui.show()
    sys.exit(app.exec_())