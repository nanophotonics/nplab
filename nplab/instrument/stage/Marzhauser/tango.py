"""Created January 2022
Author: James Stevenson
"""

from nplab.instrument import Instrument
from nplab.instrument.stage import Stage
from ctypes import c_int, c_double, c_bool, c_char_p, byref, POINTER, cdll
import sys
import os


class Tango(Stage):
    """Control object for Marzhauser Tango stages

    Originally written for a Tango 3 Desktop 3-axis stage. The Tango DLL looks
    valid for all Tango stages, so hopefully this class works for others too.
    """
    def __init__(self, unit='u', com_name=None):
        Instrument.__init__(self)
        self.unit = unit

        # Connect to Tango
        lsid = c_int()
        return_value = tango_dll.LSX_CreateLSID(byref(lsid))
        assert return_value == 0, get_useful_error_message(return_value, 'LSX_CreateLSID')
        self.lsid = lsid.value
        if com_name is None:
            # Connect to the first Tango found on USB or PCI
            self.ConnectSimple(-1, None, 57600, False)
        else:
            # Connect to Tango on a specified port
            self.ConnectSimple(1, com_name, 57600, False)

        self.set_units(unit)

    def close(self):
        """Close Tango connection and perform necessary cleanup"""
        self.Disconnect()
        self.FreeLSID()

    def move(self, pos, axis=None, relative=False):
        """Move the stage along a single axis"""
        if axis not in self.axis_names:
            raise f'{axis} is not a valid axis, must be one of {self.axis_names}'
        axis_number = translate_axis(axis)
        if relative:
            self.MoveRelSingleAxis(axis_number, pos, True)
        else:
            self.MoveAbsSingleAxis(axis_number, pos, True)

    def get_position(self, axis=None):
        """Get current positions of all axes, or, optionally, a single axis"""
        if axis is None:
            return self.GetPos()
        return self.GetPosSingleAxis(axis)

    def is_moving(self, axes=None):
        """Returns True if any of the specified axes are in motion."""
        velocities = self.IsVel()
        if axes is not None:
            for axis in axes:
                if velocities[axis] != 0:
                    return True
        else:
            for velocity in velocities.values():
                if velocity != 0:
                    return True
        return False

    def set_units(self, unit):
        """Sets all dimensions to the desired unit"""
        unit_code = translate_unit(unit)
        self.SetDimensions(unit_code, unit_code, unit_code, unit_code)

    def set_velocity(self, velocity, axis=None):
        """Set velocity for all axes or, optionally, a specified axis"""
        if axis is None:
            for axis_name in self.axis_names:
                self.SetVelSingleAxis(translate_axis(axis_name), velocity)
        else:
            self.SetVelSingleAxis(translate_axis(axis), velocity)

    # ============== Wrapped DLL Functions ==============
    # The following functions directly correspond to Tango DLL functions
    # As much as possible, they should present Python-like interfaces:
    # 1) Accept and return Python variables, not ctypes types
    # 2) Return values rather than set them to referenced variables
    # 3) Check for error codes and raise exceptions
    # Note: error codes and explanations are in the Tango DLL documentation
    def ConnectSimple(self, interface_type, com_name, baud_rate, show_protocol):
        """Wrapper for DLL function LSX_ConnectSimple"""
        #  com_name must be a bytes object, which we get by encoding as utf8
        if type(com_name) == str:
            com_name = com_name.encode('utf-8')
        try:
            return_value = tango_dll.LSX_ConnectSimple(c_int(self.lsid),
                                                       c_int(interface_type),
                                                       com_name,
                                                       c_int(baud_rate),
                                                       c_bool(show_protocol))
        except Exception as e:
            raise Exception(f'Tango.LSX_ConnectSimple raised exception: {str(e)}')
        assert return_value == 0, get_useful_error_message(return_value, 'LSX_ConnectSimple')

    def Disconnect(self):
        """Wrapper for DLL function LSX_Disconnect"""
        try:
            return_value = tango_dll.LSX_Disconnect(c_int(self.lsid))
        except Exception as e:
            raise Exception(f'Tango.LSX_Disconnect raised exception: {str(e)}')
        assert return_value == 0, get_useful_error_message(return_value, 'LSX_Disconnect')

    def FreeLSID(self):
        """Wrapper for DLL function LSX_FreeLSID"""
        try:
            return_value = tango_dll.LSX_FreeLSID(c_int(self.lsid))
        except Exception as e:
            raise Exception(f'Tango.LSX_FreeLSID raised exception: {str(e)}')
        assert return_value == 0, get_useful_error_message(return_value, 'LSX_FreeLSID')

    def SetDimensions(self, x_dim, y_dim, z_dim, a_dim):
        """Wrapper for DLL function LSX_SetDimensions"""
        try:
            return_value = tango_dll.LSX_SetDimensions(c_int(self.lsid),
                                                       c_int(x_dim),
                                                       c_int(y_dim),
                                                       c_int(z_dim),
                                                       c_int(a_dim))
        except Exception as e:
            raise Exception(f'Tango.LSX_SetDimensions raised exception: {str(e)}')
        assert return_value == 0, get_useful_error_message(return_value, 'LSX_SetDimensions')

    def MoveAbsSingleAxis(self, axis_number, value, wait):
        """Wrapper for DLL function LSX_MoveAbsSingleAxis"""
        try:
            return_value = tango_dll.LSX_MoveAbsSingleAxis(c_int(self.lsid),
                                                           c_int(axis_number),
                                                           c_double(value),
                                                           c_bool(wait))
        except Exception as e:
            raise Exception(f'Tango.LSX_MoveAbsSingleAxis raised exception: {str(e)}')
        assert return_value == 0, get_useful_error_message(return_value, 'LSX_MoveAbsSingleAxis')

    def MoveRelSingleAxis(self, axis_number, value, wait):
        """Wrapper for DLL function LSX_MoveRelSingleAxis"""
        try:
            return_value = tango_dll.LSX_MoveRelSingleAxis(c_int(self.lsid),
                                                           c_int(axis_number),
                                                           c_double(value),
                                                           c_bool(wait))
        except Exception as e:
            raise Exception(f'Tango.LSX_MoveRelSingleAxis raised exception: {str(e)}')
        assert return_value == 0, get_useful_error_message(return_value, 'LSX_MoveRelSingleAxis')

    def GetPos(self):
        """Wrapper for DLL function LSX_GetPos"""
        x_pos = c_double()
        y_pos = c_double()
        z_pos = c_double()
        a_pos = c_double()
        try:
            return_value = tango_dll.LSX_GetPos(c_int(self.lsid),
                                                byref(x_pos),
                                                byref(y_pos),
                                                byref(z_pos),
                                                byref(a_pos))
        except Exception as e:
            raise Exception(f'Tango.LSX_GetPos raised exception: {str(e)}')
        assert return_value == 0, get_useful_error_message(return_value, 'LSX_GetPos')
        return {'x': x_pos.value, 'y': y_pos.value,
                'z': z_pos.value, 'a': a_pos.value}

    def GetPosSingleAxis(self, axis_number):
        """Wrapper for DLL function LSX_GetPosSingleAxis"""
        pos = c_double()
        try:
            return_value = tango_dll.LSX_GetPosSingleAxis(c_int(self.lsid),
                                                          c_int(axis_number),
                                                          byref(pos))
        except Exception as e:
            raise Exception(f'Tango.LSX_GetPosSingleAxis raised exception: {str(e)}')
        assert return_value == 0, get_useful_error_message(return_value, 'LSX_GetPosSingleAxis')
        return pos.value

    def GetVel(self):
        """Wrapper for DLL function LSX_GetVel
        Returns axis velocities as they are set to move at, whether they are
        moving now or not.
        """
        x_velocity = c_double()
        y_velocity = c_double()
        z_velocity = c_double()
        a_velocity = c_double()
        try:
            return_value = tango_dll.LSX_GetVel(c_int(self.lsid),
                                                byref(x_velocity),
                                                byref(y_velocity),
                                                byref(z_velocity),
                                                byref(a_velocity))
        except Exception as e:
            raise Exception(f'Tango.LSX_GetVel raised exception: {str(e)}')
        assert return_value == 0, get_useful_error_message(return_value, 'LSX_GetVel')
        return {'x': x_velocity.value, 'y': y_velocity.value,
                'z': z_velocity.value, 'a': a_velocity.value}

    def IsVel(self):
        """Wrapper for DLL function LSX_IsVel
        Gets the actual velocities at which the axes are currently travelling.
        """
        x_velocity = c_double()
        y_velocity = c_double()
        z_velocity = c_double()
        a_velocity = c_double()
        try:
            return_value = tango_dll.LSX_IsVel(c_int(self.lsid),
                                               byref(x_velocity),
                                               byref(y_velocity),
                                               byref(z_velocity),
                                               byref(a_velocity))
        except Exception as e:
            raise Exception(f'Tango.LSX_IsVel raised exception: {str(e)}')
        assert return_value == 0, get_useful_error_message(return_value, 'LSX_IsVel')
        return {'x': x_velocity.value, 'y': y_velocity.value,
                'z': z_velocity.value, 'a': a_velocity.value}

    def SetVelSingleAxis(self, axis_number, velocity):
        """Wrapper for DLL function LSX_SetVelSingleAxis
        Set velocity a single axis is to move at, whether it is moving now or not.
        """
        try:
            return_value = tango_dll.LSX_SetVelSingleAxis(c_int(self.lsid),
                                                          c_int(axis_number),
                                                          c_double(velocity))
        except Exception as e:
            raise Exception(f'Tango.LSX_SetVelSingleAxis raised exception: {str(e)}')
        assert return_value == 0, get_useful_error_message(return_value, 'LSX_SetVelSingleAxis')


# =============================================================================
# ============================== Module functions =============================
# =============================================================================
def translate_unit(unit):
    """Translate English looking unit to unit code that Tango understands"""
    if unit == 'Microsteps':
        return 0
    elif unit == 'um':
        return 1
    elif unit == 'mm':
        return 2
    elif unit == 'degree':
        return 3
    elif unit == 'revolutions':
        return 4
    elif unit == 'cm':
        return 5
    elif unit == 'm':
        return 6
    elif unit == 'inch':
        return 7
    elif unit == 'mil':
        return 8
    else:
        raise Exception(f'Tried to put translate unknown unit: {unit}')


def translate_axis(axis):
    """Translate an axis (x, y, z, a) to axis-code that Tango understands"""
    if axis == 'x':
        return 1
    elif axis == 'y':
        return 2
    elif axis == 'z':
        return 3
    elif axis == 'a':
        return 4
    else:
        raise Exception(f'Tried to translate unknown axis: {axis}')


#  Error codes from Tango DLL have explanations in the documentation
#  If you learn anything helpful about an error, add it in (e.g. error 4005)
#  These are labelled "DLL Error Messages", but there are also "Tango Error
#  Messages" in the docs. I don't know when those might arise.
tango_error_strings = {
    4001: 'internal error',
    4002: 'internal error',
    4003: 'function call with wrong LSID value or maximum of 8 open connections reached',
    4004: 'Unknown interface type (may appear with Connect...)',
    4005: """Error while initializing interface
    Dev comment: This can happen if you specify the wrong port, or other software is already connected to the Tango.""",
    4006: 'No connection with controller (e.g. if SetPitch is called before Connect)',
    4007: 'Timeout while reading from interface',
    4008: 'Error during command transmission to Tango controller',
    4009: 'Command aborted (with SetAbortFlag)',
    4010: 'Command is not supported by Tango controller',
    4011: 'Manual Joystick mode switched on (may appear with SetJoystickOn/Off)',
    4012: 'No move command possible, because manual joystick enabled',
    4013: 'Closed Loop Controller Timeout (could not settle within target window)',
    # No reference to code 4014 in docs
    4015: 'Limit switch activated in travel direction',
    4016: 'Repeated vector start!! (Closed Loop controller)',
    4017: 'Error while calibrating (Limit switch not correctly released)',
    # Docs have a visual gap here but don't say why
    4101: 'No valid axis name',
    4102: 'No executable instruction',
    4103: 'Too many characters in command line',
    4104: 'Invalid instruction',
    4105: 'Number is not inside allowed range',
    4106: 'Wrong number of parameters',
    4107: 'Either ! or ? is missing',
    4108: 'No TVR possible, while axis active',
    4109: '-',  # Yes, that is what the docs say
    4110: 'Function not configured',
    4111: '-',  # Yes, that is what the docs say
    4112: 'Limit switch active',
    4113: 'Function not executable, because encoder detected'
}


def get_useful_error_message(error_code, function_name=None):
    """Generate an error message with a useful explanation."""
    error_string = tango_error_strings[error_code]
    if function_name is None:
        return f'Tango DLL returned error code {error_code}: {error_string}'
    return f'Tango.{function_name} returned error code {error_code}: {error_string}'


# =============================================================================
# ================================ DLL Import =================================
# =============================================================================
system_bits = '64' if (sys.maxsize > 2**32) else '32'
path_here = os.path.dirname(__file__)
tango_dll = cdll.LoadLibrary(f'{path_here}/DLL/{system_bits}/Tango_DLL.dll')

# Set arg types for all dll functions we call
# LSID: Used to tell the DLL which Tango we are sending a command to
# The DLL can have up to 8 simultaneously connected Tangos
tango_dll.LSX_CreateLSID.argtypes = [POINTER(c_int)]
tango_dll.LSX_ConnectSimple.argtypes = [c_int, c_int, c_char_p, c_int, c_bool]
tango_dll.LSX_Disconnect.argtypes = [c_int]
tango_dll.LSX_FreeLSID.argtypes = [c_int]
tango_dll.LSX_SetDimensions.argtypes = [c_int, c_int, c_int, c_int, c_int]
tango_dll.LSX_MoveRelSingleAxis.argtypes = [c_int, c_int, c_double, c_bool]
tango_dll.LSX_MoveAbsSingleAxis.argtypes = [c_int, c_int, c_double, c_bool]
tango_dll.LSX_GetPos.argtypes = [c_int, POINTER(c_double), POINTER(c_double),
                                 POINTER(c_double), POINTER(c_double)]
tango_dll.LSX_GetPosSingleAxis.argtypes = [c_int, c_int, POINTER(c_double)]
tango_dll.LSX_GetVel.argtypes = [c_int, POINTER(c_double), POINTER(c_double),
                                 POINTER(c_double), POINTER(c_double)]
tango_dll.LSX_IsVel.argtypes = [c_int, POINTER(c_double), POINTER(c_double),
                                POINTER(c_double), POINTER(c_double)]
tango_dll.LSX_SetVelSingleAxis.argtypes = [c_int, c_int, c_double]
