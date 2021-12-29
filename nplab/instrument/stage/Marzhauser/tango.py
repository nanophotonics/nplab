from nplab.instrument import Instrument
from nplab.instrument.stage import Stage
import ctypes
import sys

# Load the Tango DLL
system_bits = '64' if (sys.maxsize > 2**32) else '32'
tango_dll = ctypes.cdll.LoadLibrary(f'DLL/{system_bits}/Tango_DLL')

# Set arg types for all dll functions we call
# LSID: Used to tell the DLL which Tango we are sending a command to
# The DLL can have up to 8 simultaneously connected Tangos
tango_dll.LSX_CreateLSID.argtypes = [ctypes.POINTER(ctypes.c_int)]
tango_dll.LSX_ConnectSimple.argtypes = [ctypes.c_int, ctypes.c_int,
                                        ctypes.POINTER(ctypes.c_char),
                                        ctypes.c_int, ctypes.c_bool]
tango_dll.LSX_Disconnect.argtypes = [ctypes.c_int]
tango_dll.LSX_FreeLSID.argtypes = [ctypes.c_int]


class TangoWrapper():
    # Every time we call functions in the DLL, we want to check for errors
    # To simplify the Tango class, we move all that boilerplate into TangoWrapper
    def CreateLSID(self, lsid_ref):
        return_value = tango_dll.LSX_CreateLSID(lsid_ref)
        assert return_value != 0, f'Tango.LSX_CreateLSID returned {return_value}'

    def ConnectSimple(self, lsid, interface_type, com_name, baud_rate, show_protocol):
        return_value = tango_dll.LSX_ConnectSimple(lsid, interface_type, com_name, baud_rate,
                                                   show_protocol)
        assert return_value != 0, f'Tango.LSX_ConnectSimple returned {return_value}'

    def Disconnect(self, lsid):
        return_value = tango_dll.LSX_Disconnect(lsid)
        assert return_value != 0, f'Tango.LSX_Disconnect returned {return_value}'

    def FreeLSID(self, lsid):
        return_value = tango_dll.LSX_FreeLSID(lsid)
        assert return_value != 0, f'Tango.LSX_FreeLSID returned {return_value}'


tango_wrapper = TangoWrapper()


class Tango(Stage):
    def __init__(self, unit='m'):
        Instrument.__init__(self)
        self.unit = unit

        # Connect to Tango
        self.lsid = ctypes.c_int()
        tango_wrapper.CreateLSID(ctypes.byref(self.lsid))
        tango_wrapper.ConnectSimple(self.lsid, ctypes.c_int(-1), None, ctypes.c_int(57600),
                                    ctypes.c_bool(False))

    def move(self, pos, axis=None, relative=False):
        raise NotImplementedError("You must override move() in a Stage subclass")

    def get_position(self, axis=None):
        raise NotImplementedError("You must override get_position in a Stage subclass.")

    def is_moving(self, axes=None):
        """Returns True if any of the specified axes are in motion."""
        raise NotImplementedError("The is_moving method must be subclassed and implemented before it's any use!")
