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
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1, #wait at most one second for a response
                        writeTimeout=1, #similarly, fail if writing takes >1s
                        xonxoff=False, rtscts=False, dsrdtr=False,
                    )
    termination_character = "\r" #: All messages to or from the instrument end with this character.
    termination_line = "END" #: If multi-line responses are recieved, they must end with this string
    def __init__(self, port=None):
        """
        Set up the serial port and so on.
        """
        serial.SerialInstrument.__init__(port=port) #this opens the port
        
        self.query("COMP O") #enable full-featured serial interface
        
#        try: #get the set-up parameters
        self.microstepsPerMicron = self.int_query("STAGE",r"MICROSTEPS/MICRON = (\d+)",termination_line="END")
        self.query("RES s %f" % (1/self.microstepsPerMicron)) #set the resolution to 1 microstep
        self.resolution = self.float_query("RES s")
#        except:
#            raise Exception("Could not establish stage parameters, maybe the com port is wrong?")
        if re.search("FOCUS = NONE", self.query("FOCUS",termination_line="END")) is None:
            self.zAxisPresent = False
        else:
            if self.int_query("VERSION")>=84:
                self.query("UPR Z %d" % 500) #set 500 microns per revolution on the Z drive (for new BX51)
            else:
                self.query("UPR Z %d" % 100) #set 100 microns per revolution on the Z drive (for BX51)
            self.query("RES Z %f" % self.resolution) #make resolution isotropic :)
        
        self.query("ENCODER 1") #turn on encoders (if present)
        self.query("SERVO 0") #turn off servocontrol
        self.query("BLSH 0") #turn off backlash control
    def move_rel(self, dx, block=True):
        """Make a relative move by dx microns (see move)"""
        return self.move(dx, relative=True, block=block)
    def move(self, x, relative=False, block=True):
        """
        Move to coordinate x (a np.array of coordinates) in microns
        
        By default we block until the move is over (if possible), if wait==False
        we return immediately.  relative=True does relative motion, otherwise
        motion is absolute.
        """
        querystring = "GR" if relative else "G" #allow for absolute or relative moves
        for i in range(len(x)): querystring += " %d" % int(x[i]/self.resolution)
        self.query(querystring)
        if(block):
            while(self.is_moving()): time.sleep(0.02)
    def get_position(self):
        """return the current position in microns"""
        pos = self.parsed_query('P',r"%f,%f,%f")
        return np.array(pos) * self.resolution
    def is_moving(self):
        """return true if the stage is in motion"""
        return self.int_query("$,S")>0
    def test_communications(self):
        response = self.query("?",multiline=True)
        if response.startswith("PROSCAN"):
            return True
        else:
            print "response:", response
            return False