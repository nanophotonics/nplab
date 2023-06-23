from nplab.instrument.stage.thorlabs_ello.ell6 import Ell6
from nplab.ui.ui_tools import QuickControlBox

class Ell9(Ell6):
    positions = 4

    def get_qt_ui(self):
        '''
        Get UI for stage
        '''

        return ELL9UI(self)


class ELL6UI(QuickControlBox):
    def __init__(self, instr):
        super().__init__('ELL6')
        self.add_spinbox('position', vmin=0, vmax=1)
        self.auto_connect_by_name(controlled_object=instr)


class ELL9UI(QuickControlBox):
    def __init__(self, instr):
        super().__init__('ELL9')
        self.add_spinbox('position', vmin=0, vmax=3)
        self.auto_connect_by_name(controlled_object=instr)