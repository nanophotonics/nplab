__author__ = 'alansanders'

from nplab.instrument import Instrument
import visa


class VisaInstrument(Instrument):
    """
    An instrument primarily using VISA communications
    """

    def __init__(self, address, settings={}):
        """
        :param address: VISA address as a string
        :param settings: dictionary of instrument settings, including:
            'read_termination', 'write_termination', 'timeout' (0 for inf),
            'send_end' (not recommended to remove end of line character),
            delay (time between write and read during query)
        :type object
        """
        super(VisaInstrument, self).__init__()
        rm = visa.ResourceManager()
        assert address in rm.list_resources(), "The instrument was not found"
        self.instr = rm.open_resource(address, **settings)
        self._address = address
        self._settings = settings

    def __del__(self):
        try:
            self.instr.close()
        except Exception as e:
            print "The serial port didn't close cleanly:", e            print "The serial port didn't close cleanly:", e
            
    def write(self, *args, **kwargs):
        return self.instr.write(*args, **kwargs)
        
    def read(self, *args, **kwargs):
        return self.instr.read(*args, **kwargs)
        
    def query(self, *args, **kwargs):
        return self.instr.query(*args, **kwargs)