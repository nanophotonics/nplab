# NPlab code to control Acton spectrometer

import time
from nplab.instrument.serial_instrument import SerialInstrument
import serial

#logger = logging.getLogger(__name__)

class Acton(SerialInstrument):
    port_settings = dict(baudrate=9600,
                         bytesize=serial.EIGHTBITS,
                         parity=serial.PARITY_NONE,
                         stopbits=serial.STOPBITS_ONE,
                         timeout=5,  # wait at most one second for a response
                         writeTimeout=1,  # similarly, fail if writing takes >1s
                         xonxoff=False, rtscts=False, dsrdtr=False,
                         )
                         
    def __init__(self, port, debug=False, echo=True, dummy=False):
        SerialInstrument.__init__(self, port)
        
        self.echo=echo
        
        self.ser.flushInput()
        self.ser.flushOutput()
        # model info
        #self.write_command("MONO-RESET")
        self.model = self.write_command("MODEL")
        self.serial_number = self.write_command("SERIAL")
        # load grating info
        self.read_grating_info()
    

    def read_done_status(self):
        resp = self.write_command("MONO-?DONE")  # returns either 1 or 0 for done or not done
        return bool(int(resp))
    
    def read_wl(self):
        resp = self.write_command("?NM")
        "700.000 nm"
        self.wl = float(resp.split()[0])
        return self.wl
        
    def write_wl(self, wl, waittime=1.0):
        wl = float(wl)
        resp = self.write_command("%0.3f NM" % wl,waittime=waittime)
#        if self.debug: logger.debug("write_wl wl:{} resp:{}".format( wl, resp))
        
    def write_wl_fast(self, wl, waittime=1.0):
        wl = float(wl)
        resp = self.write_command("%0.3f GOTO" % wl,waittime=waittime)
#        if self.debug: logger.debug("write_wl_fast wl:{} resp:{}".format( wl, resp))
        

    def write_wl_nonblock(self, wl):
        wl = float(wl)
        resp = self.write_command("%0.3f >NM" % wl)
#        if self.debug: logger.debug("write_wl_nonblock wl:{} resp:{}".format( wl, resp))
        
    def read_grating_info(self):
        grating_string = self.write_command("?GRATINGS", waittime=1.0)
        """
            \x1a1  300 g/mm BLZ=  500NM 
            2  300 g/mm BLZ=  1.0UM 
            3  150 g/mm BLZ=  500NM 
            4  Not Installed     
            5  Not Installed     
            6  Not Installed     
            7  Not Installed     
            8  Not Installed     
            9  Not Installed     
            ok
        """
        # 0x1A is the arrow char, indicates selected grating
        
        if self.echo:
            gratings = grating_string.splitlines()[1:-1] # needed for echo
        else:
            gratings = grating_string.splitlines()[0:-1] # for no echo
#        if self.debug: print(gratings)
        
        print gratings
        self.gratings = []
        
        for grating in gratings:
#            if self.debug: logger.debug("grating: {}".format( grating ))
            grating_num, name = grating.strip('\x1a').strip(' ').split(' ', 1)
            #if self.debug: logger.debug("grating stripped: {}".format( grating ))
            num = int(grating_num)
            self.gratings.append( (num, name) )
        
        self.gratings_dict = {num: name for num,name in self.gratings}
        
        return self.gratings
        
    def read_turret(self):
        resp = self.write_command("?TURRET")
        self.turret = int(resp)
        return self.turret
    
    def write_turret(self, turret):
        assert turret in [1,2,3]
        "%i TURRET"
    
    def read_grating(self):
        resp = self.write_command("?GRATING")
        self.grating = int(resp)
        return self.grating
        
    def read_grating_name(self):
        self.read_grating()
        return self.gratings[self.grating-1]
        
    def write_grating(self, grating):
        assert 0 < grating < 10 
        self.write_command("%i GRATING" % grating)        
        
    def read_exit_mirror(self):
        resp = self.write_command("EXIT-MIRROR ?MIRROR")
        self.exit_mirror = resp.upper()
        return self.exit_mirror
    
    def write_exit_mirror(self, pos):
        pos = pos.upper()
        assert pos in ['FRONT', 'SIDE']
        self.write_command("EXIT-MIRROR %s" % pos)
        
    def read_entrance_slit(self):
        resp = self.write_command("SIDE-ENT-SLIT ?MICRONS")
        #"480 um" or "no motor"
        print(repr(resp))
        if resp == 'no motor':
            self.entrance_slit = -1
        else:
            self.entrance_slit = int(resp.split()[0])
        return self.entrance_slit
        
    def write_entrance_slit(self, pos):
        assert 5 <= pos <= 3000
        self.write_command("SIDE-ENT-SLIT %i MICRONS" % pos)
        # should return new pos

    def home_entrance_slit(self):
        # TODO
        "SIDE-ENT-SLIT SHOME"

        
    def read_exit_slit(self):
        resp = self.write_command("SIDE-EXIT-SLIT ?MICRONS")
        #"960 um" or "no motor"
        if resp == 'no motor':
            self.exit_slit = -1
        else:
            self.exit_slit = int(resp.split()[0])
        return self.exit_slit
        
    def write_exit_slit(self, pos):
        assert 5 <= pos <= 3000
        self.write_command("SIDE-EXIT-SLIT %i MICRONS" % pos)
        

#    def write_command(self, cmd):
#        if self.debug: print "write_command:", cmd
#        self.ser.write(cmd + "\r\n")
#        response = self.ser.readline()
#        if self.debug: print "\tresponse:", repr(response)
#        assert response[-4:] == "ok\r\n"
#        return response[:-4].strip()
    
    def write_command(self, cmd, waittime=0.5):
#        if self.debug: logger.debug("write_command cmd: {}".format( cmd ))
#        if self.dummy: return "0"
        cmd_bytes = (cmd).encode('ASCII')
        self.ser.write(cmd_bytes+b"\r")
        time.sleep(waittime)
        
        out = bytearray()
        char = b""
        missed_char_count = 0
        while char != b"k":
            char = self.ser.read()
            #if self.debug: print("readbyte", repr(char))
            if char == b"": #handles a timeout here
                missed_char_count += 1
#                if self.debug: logger.debug("no character returned, missed %i so far" % missed_char_count)
                if missed_char_count > 3:
                    return 0
                continue
            out += char

        
        out += self.ser.read(2) #Should be "\r\n"
        
        out = out.decode('ascii')

#        if self.debug:
##            logger.debug( "complete message" +  repr(out))
#            print("complete message" + repr(out))
        #assert out[-3:] == ";FF"
        #assert out[:7] == "@%03iACK" % self.address   
        
        assert out[-5:] == " ok\r\n"
        out = out[:-5].strip()
    
        # When echo is enabled, verify echoed command and strip
        if self.echo:
            echo = out[0:len(cmd_bytes)]        
            rest = out[len(cmd_bytes):]
            print("echo, rest, cmd:", echo, rest, cmd_bytes)
            assert echo == cmd
            return rest
        else:
            return out
        #self.ser.flushInput()
        #self.ser.flushOutput()
        #return out
    
    def close(self):
        self.ser.close()


if __name__ == "__main__":

    port = "COM6"
    ac = Acton(port=port)
