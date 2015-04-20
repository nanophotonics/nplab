__author__ = 'alansanders'

from traits.api import HasTraits, Int, Range, Button
from traitsui.api import View, Item, HGroup, Spring


class LightSource(HasTraits):

    _min_power = Int(0)
    _max_power = Int(2000)
    power = Range('_min_power', '_max_power', 0, mode='slider', label='Power')
    set_power_button = Button('Set Power')

    view = View(
                HGroup(Item('power'),
                      Item('set_power_button', show_label=False), Spring(),
                      label='Light Source Controls', show_border=True
                      ),
                resizable=True, title="Light Source"
               )

    def __init__(self):
        pass

    def _power_changed(self, value):
        pass

    def _set_power_button_fired(self):
        pass
