# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from builtins import range
from past.utils import old_div
import nplab.instrument.serial_instrument as serial
import nplab.instrument.stage as stage
import re
import numpy as np
import time


class ProScan(serial.SerialInstrument, stage.Stage):
    """
    This class handles the Prior stage.
    """
    port_settings = dict(baudrate=9600,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_TWO,
                        timeout=1, #wait at most .one second for a response
                        writeTimeout=1, #similarly, fail if writing takes >1s
                        xonxoff=False, rtscts=False, dsrdtr=False,
                    )
    termination_character = "\r" #: All messages to or from the instrument end with this character.
    termination_line = "END" #: If multi-line responses are recieved, they must end with this string

    def __init__(self, port=None, use_si_units = False, hardware_version = None):
        """
        Set up the serial port and so on. 
        If the controller is a ProScan II not a ProScan III. 
        The hardware_version must be set to two or the Stopbit value will be incorrect
        """
        if hardware_version == 2:
            self.port_settings['stopbits'] = serial.STOPBITS_ONE
        serial.SerialInstrument.__init__(self, port=port) #this opens the port
        stage.Stage.__init__(self,unit = 'u') #this opens the port
        
        self.query("COMP O") #enable full-featured serial interface
        
#        try: #get the set-up parameters
        self.microstepsPerMicron = self.parsed_query("STAGE",r"MICROSTEPS/MICRON = %d",termination_line="END")
        self.query("RES s %f" % (old_div(1,self.microstepsPerMicron))) #set the resolution to 1 microstep
        self.resolution = self.float_query("RES s")
#        except:
#            raise Exception("Could not establish stage parameters, maybe the com port is wrong?")
        if re.search("FOCUS = NONE", self.query("FOCUS",termination_line="END")) is None:
            self.zAxisPresent = False
        else:
            self.query("UPR Z %d" % 100) #set 100 microns per revolution on the Z drive (for BX51)
            self.query("RES Z %f" % self.resolution) #make resolution isotropic :)
        
        self.query("ENCODER 1") #turn on encoders (if present)
        self.query("SERVO 0") #turn off servocontrol
        self.query("BLSH 0") #turn off backlash control
        
        self.use_si_units = use_si_units
        self.axis_names = ('x', 'y', 'z')
        
    def move_rel(self, dx, block=True):
        """Make a relative move by dx microns/metres (see move)"""
        return self.move(dx, relative=True, block=block)

    def move(self, x, relative=False, axis=None, block=True):
        """
        Move to coordinate x (a np.array of coordinates) in microns, or metres if use_si_units is true
        
        By default we block until the move is over (if possible), if wait==False
        we return immediately.  relative=True does relative motion, otherwise
        motion is absolute.
        """
        querystring = "G"
        if axis is not None and relative:
            # single-axis emulation is fine for relative moves
            return self.move_axis(x, axis, relative=relative, block=block)
        elif axis is not None and not relative:
            # single-axis absolute move
            assert axis.lower() in self.axis_names, ValueError("{0} is not a valid axis name.".format(axis))
            querystring += axis.upper()
            x = [x]
        elif axis is None and relative:
            # relative move
            querystring += "R"
        if self.use_si_units: x = np.array(x) * 1e6
        for i in range(len(x)): querystring += " %d" % int(old_div(x[i],self.resolution))
        self.query(querystring)
        time_0 = time.time()
        #position_0 = self.position
        #print position_0
        try:
            if(block):
                while(self.is_moving()):
                    time.sleep(0.02)
                    if(time.time()-time_0>20): # Set move timelimit in case stage gets stuck
                       # new_position = self.position                        
                        print(x, end=' ')
                        print(self.position)
                        #if(new_position == position_0).all(): #Allow moves that take greater than timelimit             
                        self.emergency_stop()
                        self.move(x, relative, axis, block)
        except KeyboardInterrupt:
            self.emergency_stop()

    def move_axis(self, pos, axis, relative=False, **kwargs):
        """Move along one axis"""
        # We use the built-in emulation for relative moves
        if relative:
            return stage.Stage.move_axis(self, pos, axis, relative=True, **kwargs)
        else:
            return self.move(pos, axis=axis, relative=relative, **kwargs)

    def get_position(self, axis=None):
        """return the current position in microns"""
        if axis is not None:
            return self.select_axis(self.get_position(), axis)
        else:
            pos = self.parsed_query('P',r"%f,%f,%f")
            if self.use_si_units:
                pos = old_div(np.array(pos),1e6)
            return np.array(pos) * self.resolution

    position = property(get_position)

    def is_moving(self):
        """return true if the stage is in motion"""
        return self.int_query("$,S")>0

    def emergency_stop(self):
        return self.query("K")

    def test_communications(self):
        """Check there is a prior stage at the other end of the COM port."""
        response = self.query("?",multiline=True)
        if response.startswith("PROSCAN"):
            return True
        else:
            return False
    def disable_joy(self):
        self.query('H')
    def enable_joy(self):
        self.query('J')