# -*- coding: utf-8 -*-


from nplab.instrument.visa_instrument import VisaInstrument


class LS331(VisaInstrument):
    """https://www.lakeshore.com/ObsoleteAndResearchDocs/331_Manual.pdf"""
    def __init__(self, address, **kwargs):
        super(LS331, self).__init__(address, **kwargs)

    def get_temperature(self):
        reply = self.query("KRDG?")
        return float(reply[:-2])
    temperature = property(fget=get_temperature)


if __name__ == "__main__":
    ls311 = LS331("GPIB0::12::INSTR")
    print ls311.temperature
