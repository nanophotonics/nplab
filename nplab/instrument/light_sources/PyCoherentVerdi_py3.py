""" Package for reading parameters of the Verdi laser 

Note that the module uses property attributes. Look at the python documentation 
to understand how property attributes are working if you don't alread know. 


example:

verdi = VerdiDriver(port='COM7')
print verdi.power # print the measured power
print verdi.set_power # print the set power
verdi.set_power = 15.6 # set the power to 15.6 watts 

verdi.list_cmd(['power', 'baseplate_temperature']) # Returns a dictionary with the values of the parameters in the list
verdi.read_all_parameters() # Returns a dictionary with the values of all the parameters
"""

import serial
from VerdiQuery import VerdiQueryClass, VerdiQueryList

DEFAULT_PORT='COM7'

class BaseDriver(serial.Serial):
    def __init__(self, port=DEFAULT_PORT, baudrate=19200, parity='N', stopbits=1 ):
        super(BaseDriver, self).__init__(port=port, baudrate=baudrate, parity=parity)
        
    def write_cmd(self, cmd, value):
        #self.write('%s:%s\r\n'%(cmd, value))
        temp='%s:%s\r\n'%(cmd, value)
        self.write(temp.encode())
        self.readline()
    def read_txt(self, cmd):
        """ Return the result of the command ?cmd """
        #self.write('?%s\r\n'%cmd)
        temp='?%s\r\n'%cmd
        self.write(temp.encode())
        a=self.readline().strip()
        if a=='': a=self.readline().strip()
        temp = 'Error'
        if temp.encode() in a:
            raise Exception(a)
        if a[:6]=="VERDI>":
            a = a[6:]
        temp = '?%s'%cmd
        temp2 = ''
        if temp.encode() in a: a=a.replace(temp.encode(), temp2.encode())        
        return a
    
    def read_number(self, cmd):
        a = self.read_txt(cmd)
        #a = self.read_txt(cmd).encode()
        return eval(a)

    def read_dict_number(self, cmd, dic):
        """ Return the result of the command ?cmd using a human readable output provided by dic """
        a = self.read_number(cmd)
        return dic[a]

    def read_list_cmd(self, liste_cmd):
        """ Returns a dictionary with all the parameters of liste_cmd"""
        return dict([(cmd, self.__getattribute__(cmd)) for cmd in liste_cmd])

class VerdiCommand(object):
    @property
    def set_power(self):
        """Returns or set the light regulation set power in watts"""
        return super(VerdiCommand, self).set_power   
    @set_power.setter
    def set_power(self, value):
        self.write_cmd('P',"%6.4f"%value)

    @property
    def shutter(self):
        """Returns or set the status of the external shutter {0:"CLOSED", 1:"OPEN"}"""
        return super(VerdiCommand, self).shutter
    @shutter.setter
    def set_shutter(self, value):
        if value==True: value=1
        if value==False: value=0
        if isinstance(value, str):
            if value.lower()=='open': value=1
            if value.upper()=='close': value=0
        print('arrived')    
        self.write_cmd('S',str(value))

    @property
    def laser(self):
        """ Returns or set the laser status (OFF, ON) """
        return super(VerdiCommand, self).laser
    
    @laser.setter
    def laser(self, value):
        if isinstance(value, str):
            if value.lower() in ['on', 'enable']:
                value=1
            elif value.lower() in ['off', 'stand by', 'standby']:
                value=0
            else:
                raise Exception('Set value of laser property is %s it should be "off" or "on" (or "stand by" or "enable)"'%value)
        self.write_cmd('L',value)
              
    
    def enable(self):
        """Resets faults and turns laser on (key must be in the "ENABLE" position). Clears
        fault screen on power supply and fault history so lasing will resume if no active fault """
        self.laser = 'ENABLE'

    def stand_by(self):
        """ Put the laser in STANDBY mode (note: If the key is in the "ENABLE" position, then this
        command will override"""
        self.laser = 'OFF'
        
class VerdiDriver(VerdiCommand, VerdiQueryClass,BaseDriver):
    """ Main class for driving the Verdi laser"""
    def read_all_parameters(self):
        """Returns a dictionary with all the parameters"""
        return self.read_list_cmd(VerdiQueryList)

