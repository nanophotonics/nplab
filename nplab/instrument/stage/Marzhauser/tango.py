from nplab.instrument import Instrument
from nplab.instrument.stage import Stage
import ctypes
import sys
import os

# Load the Tango DLL
system_bits = '64' if (sys.maxsize > 2**32) else '32'
path_here = os.path.dirname(__file__)
tango_dll = ctypes.cdll.LoadLibrary(f'{path_here}/DLL/{system_bits}/Tango_DLL.dll')

# Set arg types for all dll functions we call
# LSID: Used to tell the DLL which Tango we are sending a command to
# The DLL can have up to 8 simultaneously connected Tangos
tango_dll.LSX_CreateLSID.argtypes = [ctypes.POINTER(ctypes.c_int)]
tango_dll.LSX_ConnectSimple.argtypes = [ctypes.c_int, ctypes.c_int,
                                        ctypes.c_char_p,
                                        ctypes.c_int, ctypes.c_bool]
tango_dll.LSX_Disconnect.argtypes = [ctypes.c_int]
tango_dll.LSX_FreeLSID.argtypes = [ctypes.c_int]
tango_dll.LSX_SetDimensions.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int,
                                        ctypes.c_int, ctypes.c_int]
tango_dll.LSX_MoveRelSingleAxis.argtypes = [ctypes.c_int, ctypes.c_int,
                                            ctypes.c_double, ctypes.c_bool]
tango_dll.LSX_MoveAbsSingleAxis.argtypes = [ctypes.c_int, ctypes.c_int,
                                            ctypes.c_double, ctypes.c_bool]
tango_dll.LSX_GetPos.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_double),
                                 ctypes.POINTER(ctypes.c_double),
                                 ctypes.POINTER(ctypes.c_double),
                                 ctypes.POINTER(ctypes.c_double)]
tango_dll.LSX_GetPosSingleAxis.argtypes = [ctypes.c_int, ctypes.c_int,
                                           ctypes.POINTER(ctypes.c_double)]
tango_dll.LSX_GetVel.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_double),
                                 ctypes.POINTER(ctypes.c_double),
                                 ctypes.POINTER(ctypes.c_double),
                                 ctypes.POINTER(ctypes.c_double)]
tango_dll.LSX_IsVel.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_double),
                                ctypes.POINTER(ctypes.c_double),
                                ctypes.POINTER(ctypes.c_double),
                                ctypes.POINTER(ctypes.c_double)]
tango_dll.LSX_SetVelSingleAxis.argtypes = [ctypes.c_int, ctypes.c_int,
                                           ctypes.c_double]


class Tango(Stage):
    def __init__(self, unit='u'):
        Instrument.__init__(self)
        self.unit = unit

        # Connect to Tango
        lsid = ctypes.c_int()
        return_value = tango_dll.LSX_CreateLSID(ctypes.byref(lsid))
        assert return_value == 0, f'Tango.LSX_CreateLSID returned {return_value}'
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
        if axis is None:
            return self.GetPos()
        return self.GetPosSingleAxis(axis)

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
            raise Exception(f'Tried to put translate unknown unit: {unit}')

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
            raise Exception(f'Tried to translate unknown axis: {axis}')

    # ============== Wrapped DLL Functions ==============
    # The following functions directly correspond to Tango DLL functions
    # As much as possible, they should present Python-like interfaces:
    # 1) Accept and return Python variables, not ctype types
    # 2) Return values rather than set them to referenced variables
    # 3) Check for error codes and raise exceptions
    # Note: error codes and explanations are in the Tango DLL documentation
    def ConnectSimple(self, interface_type, com_name, baud_rate, show_protocol):
        #  com_name must be a bytes object, which we get by encoding as utf8
        if type(com_name) == str:
            com_name = com_name.encode('utf-8')
        try:
            return_value = tango_dll.LSX_ConnectSimple(ctypes.c_int(self.lsid),
                                                       ctypes.c_int(interface_type),
                                                       com_name),
                                                       ctypes.c_int(baud_rate),
                                                       ctypes.c_bool(show_protocol))
        except Exception as e:
            raise Exception(f'Tango.LSX_ConnectSimple raised exception: {str(e)}')
        if return_value == 4005:
            raise Exception('Tango DLL raised error 4005: "Error while ' \
                            'initializing interface." This can happen if ' \
                            'you specify the wrong port, or other software ' \
                            'is already be connected to the Tango.')
        else:
            assert return_value == 0, f'Tango.LSX_ConnectSimple returned {return_value}'

    def Disconnect(self):
        try:
            return_value = tango_dll.LSX_Disconnect(ctypes.c_int(self.lsid))
        except Exception as e:
            raise Exception(f'Tango.LSX_Disconnect raised exception: {str(e)}')
        assert return_value == 0, f'Tango.LSX_Disconnect returned {return_value}'

    def FreeLSID(self):
        try:
            return_value = tango_dll.LSX_FreeLSID(ctypes.c_int(self.lsid))
        except Exception as e:
            raise Exception(f'Tango.LSX_FreeLSID raised exception: {str(e)}')
        assert return_value == 0, f'Tango.LSX_FreeLSID returned {return_value}'

    def SetDimensions(self, x_dim, y_dim, z_dim, a_dim):
        try:
            return_value = tango_dll.LSX_SetDimensions(ctypes.c_int(self.lsid),
                                                       ctypes.c_int(x_dim),
                                                       ctypes.c_int(y_dim),
                                                       ctypes.c_int(z_dim),
                                                       ctypes.c_int(a_dim))
        except Exception as e:
            raise Exception(f'Tango.LSX_SetDimensions raised exception: {str(e)}')
        assert return_value == 0, f'Tango.LSX_SetDimensions returned {return_value}'

    def MoveAbsSingleAxis(self, axis_number, value, wait):
        try:
            return_value = tango_dll.LSX_MoveAbsSingleAxis(ctypes.c_int(self.lsid),
                                                           ctypes.c_int(axis_number),
                                                           ctypes.c_double(value),
                                                           ctypes.c_bool(wait))
        except Exception as e:
            raise Exception(f'Tango.LSX_MoveAbsSingleAxis raised exception: {str(e)}')
        assert return_value == 0, f'Tango.LSX_MoveAbsSingleAxis returned {return_value}'

    def MoveRelSingleAxis(self, axis_number, value, wait):
        try:
            return_value = tango_dll.LSX_MoveRelSingleAxis(ctypes.c_int(self.lsid),
                                                           ctypes.c_int(axis_number),
                                                           ctypes.c_double(value),
                                                           ctypes.c_bool(wait))
        except Exception as e:
            raise Exception(f'Tango.LSX_MoveRelSingleAxis raised exception: {str(e)}')
        assert return_value == 0, f'Tango.LSX_MoveRelSingleAxis returned {return_value}'

    def GetPos(self):
        x_pos = ctypes.c_double()
        y_pos = ctypes.c_double()
        z_pos = ctypes.c_double()
        a_pos = ctypes.c_double()
        try:
            return_value = tango_dll.LSX_GetPos(ctypes.c_int(self.lsid),
                                                ctypes.byref(x_pos),
                                                ctypes.byref(y_pos),
                                                ctypes.byref(z_pos),
                                                ctypes.byref(a_pos))
        except Exception as e:
            raise Exception(f'Tango.LSX_GetPos raised exception: {str(e)}')
        assert return_value == 0, f'Tango.LSX_GetPos returned {return_value}'
        return {'x': x_pos.value, 'y': y_pos.value,
                'z': z_pos.value, 'a': a_pos.value}

    def GetPosSingleAxis(self, axis_number):
        pos = ctypes.double()
        try:
            return_value = tango_dll.LSX_GetPosSingleAxis(ctypes.c_int(self.lsid),
                                                          ctypes.byref(pos))
        except Exception as e:
            raise Exception(f'Tango.LSX_GetPosSingleAxis raised exception: {str(e)}')
        assert return_value == 0, f'Tango.LSX_GetPosSingleAxis returned {return_value}'
        return pos.value

    def GetVel(self):
        """Get target velocity of each axis"""
        x_velocity = ctypes.c_double()
        y_velocity = ctypes.c_double()
        z_velocity = ctypes.c_double()
        a_velocity = ctypes.c_double()
        try:
            return_value = tango_dll.LSX_GetVel(ctypes.c_int(self.lsid),
                                                ctypes.byref(x_velocity),
                                                ctypes.byref(y_velocity),
                                                ctypes.byref(z_velocity),
                                                ctypes.byref(a_velocity))
        except Exception as e:
            raise Exception(f'Tango.LSX_GetVel raised exception: {str(e)}')
        assert return_value == 0, f'Tango.LSX_GetVel returned {return_value}'
        return {'x': x_velocity.value, 'y': y_velocity.value,
                'z': z_velocity.value, 'a': a_velocity.value}

    def IsVel(self):
        """Get the actual velocities at which the axes are currently travelling"""
        x_velocity = ctypes.c_double()
        y_velocity = ctypes.c_double()
        z_velocity = ctypes.c_double()
        a_velocity = ctypes.c_double()
        try:
            return_value = tango_dll.LSX_IsVel(ctypes.c_int(self.lsid),
                                                ctypes.byref(x_velocity),
                                                ctypes.byref(y_velocity),
                                                ctypes.byref(z_velocity),
                                                ctypes.byref(a_velocity))
        except Exception as e:
            raise Exception(f'Tango.LSX_IsVel raised exception: {str(e)}')
        assert return_value == 0, f'Tango.LSX_IsVel returned {return_value}'
        return {'x': x_velocity.value, 'y': y_velocity.value,
                'z': z_velocity.value, 'a': a_velocity.value}

    def SetVelSingleAxis(self, axis_number, velocity):
        """Set single-axis target velocity"""
        try:
            return_value = tango_dll.LSX_SetVelSingleAxis(ctypes.c_int(self.lsid),
                                                          ctypes.c_int(axis_number),
                                                          ctypes.c_double(velocity))
        except Exception as e:
            raise Exception(f'Tango.LSX_SetVelSingleAxis raised exception: {str(e)}')
        assert return_value == 0, f'Tango.LSX_SetVelSingleAxis returned {return_value}'
