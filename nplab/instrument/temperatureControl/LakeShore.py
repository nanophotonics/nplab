# -*- coding: utf-8 -*-

from nplab.instrument.visa_instrument import VisaInstrument
from nplab.instrument.temperatureControl import TemperatureControl


class LS331(VisaInstrument, TemperatureControl):
    """https://www.lakeshore.com/ObsoleteAndResearchDocs/331_Manual.pdf"""
    def __init__(self, address, **kwargs):
        super(LS331, self).__init__(address, **kwargs)

    def get_temperature(self):
        reply = self.query("KRDG?")
        return float(reply[:-2])
    temperature = property(fget=get_temperature)
