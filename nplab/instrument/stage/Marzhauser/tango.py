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
tango_dll.LSX_SetDimensions.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                        ctypes.c_int, ctypes.c_int]
tango_dll.LSX_MoveRelSingleAxis.argtypes = [ctypes.c_int, ctypes.c_int,
                                            ctypes.c_double, ctypes.c_bool]
tango_dll.LSX_MoveAbsSingleAxis.argtypes = [ctypes.c_int, ctypes.c_int,
                                            ctypes.c_double, ctypes.c_bool]


class Tango(Stage):
    def __init__(self, unit='m'):
        Instrument.__init__(self)
        self.unit = unit

        # Connect to Tango
        self.lsid = ctypes.c_int()
        Tango.CreateLSID(ctypes.byref(self.lsid))
        self.ConnectSimple(ctypes.c_int(-1), None, ctypes.c_int(57600),
                           ctypes.c_bool(False))
        self.set_units(unit)

    def close(self):
        self.Disconnect()
        self.FreeLSID()

    def move(self, pos, axis, relative=False):
        """Move the stage along a single axis"""
        if axis not in self.axis_names:
            raise f'{axis} is not a valid axis, must be one of {self.axis_names}'
        axis_number = self.translate_axis(axis)
        if relative:
            self.MoveRelSingleAxis(axis_number, ctypes.c_double(pos),
                                   ctypes.c_bool(True))
        else:
            self.MoveAbsSingleAxis(axis_number, ctypes.c_double(pos),
                                   ctypes.c_bool(True))

    def get_position(self, axis=None):
        raise NotImplementedError("You must override get_position in a Stage subclass.")

    def is_moving(self, axes=None):
        """Returns True if any of the specified axes are in motion."""
        raise NotImplementedError("The is_moving method must be subclassed and implemented before it's any use!")

    def set_units(self, unit):
        """Sets all dimensions to the desired unit"""
        unit_code = Tango.translate_unit(unit)
        Tango.SetDimensions(unit_code, unit_code, unit_code, unit_code)

    @staticmethod
    def translate_unit(unit):
        if (unit == 'Microsteps'):
            return ctypes.c_int(0)
        elif (unit == 'um'):
            return ctypes.c_int(1)
        elif (unit == 'mm'):
            return ctypes.c_int(2)
        elif (unit == 'degree'):
            return ctypes.c_int(3)
        elif (unit == 'revolutions'):
            return ctypes.c_int(4)
        elif (unit == 'cm'):
            return ctypes.c_int(5)
        elif (unit == 'm'):
            return ctypes.c_int(6)
        elif (unit == 'inch'):
            return ctypes.c_int(7)
        elif (unit == 'mil'):
            return ctypes.c_int(8)
        else:
            raise f'Tried to put translate unknown unit: {unit}'

    @staticmethod
    def translate_axis(axis):
        if (axis == 'x'):
            return ctypes.c_int(1)
        elif (axis == 'y'):
            return ctypes.c_int(2)
        elif (axis == 'z'):
            return ctypes.c_int(3)
        elif (axis == 'a'):
            return ctypes.c_int(4)
        else:
            raise f'Tried to translate unknown axis: {axis}'

    @staticmethod
    def CreateLSID(lsid_ref):
        return_value = tango_dll.LSX_CreateLSID(lsid_ref)
        assert return_value != 0, f'Tango.LSX_CreateLSID returned {return_value}'

    def ConnectSimple(self, interface_type, com_name, baud_rate, show_protocol):
        return_value = tango_dll.LSX_ConnectSimple(self.lsid, interface_type,
                                                   com_name, baud_rate,
                                                   show_protocol)
        assert return_value != 0, f'Tango.LSX_ConnectSimple returned {return_value}'

    def Disconnect(self):
        return_value = tango_dll.LSX_Disconnect(self.lsid)
        assert return_value != 0, f'Tango.LSX_Disconnect returned {return_value}'

    def FreeLSID(self):
        return_value = tango_dll.LSX_FreeLSID(self.lsid)
        assert return_value != 0, f'Tango.LSX_FreeLSID returned {return_value}'

    def SetDimensions(self, x_dim, y_dim, z_dim, a_dim):
        return_value = tango_dll.LSX_SetDimensions(self.lsid, x_dim, y_dim, z_dim, a_dim)
        assert return_value != 0, f'Tango.LSX_SetDimensions returned {return_value}'

    def MoveAbsSingleAxis(self, axis_number, value, wait):
        return_value = tango_dll.LSX_MoveAbsSingleAxis(self.lsid, axis_number, value, wait)
        assert return_value != 0, f'Tango.LSX_MoveAbsSingleAxis returned {return_value}'
        assert return_value != 0, f'Tango.LSX_MoveAbsSingleAxis returned {return_value}'
