import serial
import io
import re
import numpy as np
import time

class ProScan(object):
    """
    This class handles the Prior stage.
    """
    def __init__(self, port):
        """
        Set up the serial port and so on.
        """
        self.ser = serial.Serial( 
                        port=port,
                        baudrate=9600,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1, #wait at most one second for a response
                        writeTimeout=1, #similarly, fail if writing takes >1s
                        xonxoff=False, rtscts=False, dsrdtr=False,)
        self.ser_io = io.TextIOWrapper(io.BufferedRWPair(self.ser, self.ser, 1),  
                               newline = '\r',
                               line_buffering = True)   
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
    def __del__(self):
        self.close()
    def close(self):
        """Release the serial port"""
        self.ser.close()
    def write(self,queryString):
        """Write a string to the serial port"""
        self.ser.write(queryString+'\r')
    def query(self,queryString,multiline=False,termination_line=None):
        """
        Write a string to the stage controller and return its response.
        
        It should return immediately, because even commands that don't give a
        response will return '\r'.  The multiline and termination_line commands
        will keep reading until a termination phrase is reached.
        """
        self.write(queryString)
        
        if termination_line is not None:
            multiline = True
        if multiline:
            response = ""
            last_line = "dummy"
            while termination_line not in last_line \
                        and len(last_line) > 0:
                last_line = self.ser_io.readline().replace("\r","\n").strip()
                response += last_line + "\n"
 #       return self.ser.readline().replace("\r","\n").strip()
        #TODO: use the one below and make it cope with multilines
            return response
        else:
            return self.ser_io.readline().replace("\r","\n").strip()
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
    def position(self):
        """return the current position in microns"""
        pos = self.parsed_query('P',r"([.\d-]+),([.\d-]+),([.\d-]+)")
        return np.array(pos) * self.resolution
    def is_moving(self):
        """return true if the stage is in motion"""
        return self.int_query("$,S")>0
    def parsed_query(self, queryString, responseString=r"(\d+)", re_flags=0, parseFunction=int, **kwargs):
        """
        Perform a query, then parse the result.
        By default it looks for an integer and returns one, otherwise it will
        match a custom regex string and return the subexpressions, parsed through
        parseFunc (which defaults to int()).
        """
        reply = self.query(queryString, **kwargs)
        res = re.search(responseString, reply, flags=re_flags)
        if res is None:
            raise ValueError("Stage response to %s ('%s') wasn't matched by /%s/" % (queryString, reply, responseString))
        try:
            if len(res.groups()) == 1:
                return parseFunction(res.groups()[0])
            else:
                return map(parseFunction,res.groups())
        except ValueError:
            raise ValueError("Stage response to %s ('%s') wasn't matched by /%s/" % (queryString, reply, responseString))
    def int_query(self, queryString, responseString=r"(\d+)", re_flags=0, **kwargs):
        """Perform a query and return the result(s) as integer(s) (see parsedQuery)"""
        return self.parsed_query(queryString, responseString, re_flags, int, **kwargs)
    def float_query(self, queryString, responseString=r"([.\d]+)", re_flags=0, **kwargs):
        """Perform a query and return the result(s) as float(s) (see parsedQuery)"""
        return self.parsed_query(queryString, responseString, re_flags, float, **kwargs)