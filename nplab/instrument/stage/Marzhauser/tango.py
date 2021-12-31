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
tango_dll.LSX_GetVel.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_double),
                                 ctypes.POINTER(ctypes.c_double),
                                 ctypes.POINTER(ctypes.c_double),
                                 ctypes.POINTER(ctypes.c_double)]


class Tango(Stage):
    def __init__(self, unit='m'):
        Instrument.__init__(self)
        self.unit = unit

        # Connect to Tango
        lsid = ctypes.c_int()
        return_value = tango_dll.LSX_CreateLSID(ctypes.byref(lsid))
        assert return_value != 0, f'Tango.LSX_CreateLSID returned {return_value}'
        self.lsid = lsid.value
        self.ConnectSimple(-1, None, 57600, False)

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
            self.MoveRelSingleAxis(axis_number, pos, True)
        else:
            self.MoveAbsSingleAxis(axis_number, pos, True)

    def get_position(self, axis=None):
        raise NotImplementedError("You must override get_position in a Stage subclass.")

    def is_moving(self, axes=None):
        """Returns True if any of the specified axes are in motion."""
        velocities = self.GetVel()
        for velocity in velocities.values():
            if velocity != 0:
                return True
        return False

    def set_units(self, unit):
        """Sets all dimensions to the desired unit"""
        unit_code = Tango.translate_unit(unit)
        self.SetDimensions(unit_code, unit_code, unit_code, unit_code)

    @staticmethod
    def translate_unit(unit):
        if (unit == 'Microsteps'):
            return 0
        elif (unit == 'um'):
            return 1
        elif (unit == 'mm'):
            return 2
        elif (unit == 'degree'):
            return 3
        elif (unit == 'revolutions'):
            return 4
        elif (unit == 'cm'):
            return 5
        elif (unit == 'm'):
            return 6
        elif (unit == 'inch'):
            return 7
        elif (unit == 'mil'):
            return 8
        else:
            raise f'Tried to put translate unknown unit: {unit}'

    @staticmethod
    def translate_axis(axis):
        if (axis == 'x'):
            return 1
        elif (axis == 'y'):
            return 2
        elif (axis == 'z'):
            return 3
        elif (axis == 'a'):
            return 4
        else:
            raise f'Tried to translate unknown axis: {axis}'

    # ============== Wrapped DLL Functions ==============
    # The following functions directly correspond to Tango DLL functions
    # As much as possible, they should present Python-like interfaces:
    # 1) Accept and return Python variables, not ctype types
    # 2) Return values rather than set them to referenced variables
    # 3) Check for error codes and raise exceptions
    def ConnectSimple(self, interface_type, com_name, baud_rate, show_protocol):
        return_value = tango_dll.LSX_ConnectSimple(ctypes.c_int(self.lsid),
                                                   ctypes.c_int(interface_type),
                                                   ctypes.byref(ctypes.c_char(com_name)),
                                                   ctypes.c_int(baud_rate),
                                                   ctypes.c_bool(show_protocol))
        assert return_value != 0, f'Tango.LSX_ConnectSimple returned {return_value}'

    def Disconnect(self):
        return_value = tango_dll.LSX_Disconnect(ctypes.c_int(self.lsid))
        assert return_value != 0, f'Tango.LSX_Disconnect returned {return_value}'

    def FreeLSID(self):
        return_value = tango_dll.LSX_FreeLSID(ctypes.c_int(self.lsid))
        assert return_value != 0, f'Tango.LSX_FreeLSID returned {return_value}'

    def SetDimensions(self, x_dim, y_dim, z_dim, a_dim):
        return_value = tango_dll.LSX_SetDimensions(ctypes.c_int(self.lsid),
                                                   ctypes.c_int(x_dim),
                                                   ctypes.c_int(y_dim),
                                                   ctypes.c_int(z_dim),
                                                   ctypes.c_int(a_dim))
        assert return_value != 0, f'Tango.LSX_SetDimensions returned {return_value}'

    def MoveAbsSingleAxis(self, axis_number, value, wait):
        return_value = tango_dll.LSX_MoveAbsSingleAxis(ctypes.c_int(self.lsid),
                                                       ctypes.c_int(axis_number),
                                                       ctypes.c_double(value),
                                                       ctypes.c_bool(wait))
        assert return_value != 0, f'Tango.LSX_MoveAbsSingleAxis returned {return_value}'

    def MoveRelSingleAxis(self, axis_number, value, wait):
        return_value = tango_dll.LSX_MoveRelSingleAxis(ctypes.c_int(self.lsid),
                                                       ctypes.c_int(axis_number),
                                                       ctypes.c_double(value),
                                                       ctypes.c_bool(wait))
        assert return_value != 0, f'Tango.LSX_MoveRelSingleAxis returned {return_value}'

    def GetVel(self):
        x_velocity = ctypes.c_double()
        y_velocity = ctypes.c_double()
        z_velocity = ctypes.c_double()
        a_velocity = ctypes.c_double()
        return_value = tango_dll.LSX_GetVel(ctypes.c_int(self.lsid),
                                            ctypes.byref(x_velocity),
                                            ctypes.byref(y_velocity),
                                            ctypes.byref(z_velocity),
                                            ctypes.byref(a_velocity))
        assert return_value != 0, f'Tango.LSX_MoveAbsSingleAxis returned {return_value}'
        return {'x': x_velocity.value, 'y': y_velocity.value,
                'z': z_velocity.value, 'a': a_velocity.value}
