# -*- coding: utf-8 -*-
"""
Created on Tue Jul 21 10:22:28 2015

@author: WMD
"""
from __future__ import print_function

import nplab.instrument.serial_instrument as si
from nplab.instrument.stage import Stage
import serial
import time



ERROR_CODE = {'0': 'No error',
              '2': 'Driver fault (thermal shut down)',
              '6': 'Unknown command',
              '7': 'Parameter out of range',
              '8': 'No motor connected',
              '26': 'Positive software limit detected',
              '27': 'Negative software limit detected',
              '38': 'Command parameter missing',
              '50': 'Communication overflow',
              '213': 'Motor not enabled',
              '214': 'Invalid axis',
              '226': 'Command not allowed during motion',
              '227': 'Command not allowed',
              '240': 'Jog wheel over speed'
              }

class NanoPZ(si.SerialInstrument,Stage):
    def __init__(self, port=None,controllerNOM ="1"):
        self.port_settings = {
                    'baudrate':19200,
                    'bytesize':serial.EIGHTBITS,
                    'parity':serial.PARITY_NONE,
                    'stopbits':serial.STOPBITS_ONE,
                    'timeout':1, #wait at most one second for a response
                    'writeTimeout':1, #similarly, fail if writing takes >1s
                    'xonxoff':True, 'rtscts':False, 'dsrdtr':False,
                    }
        si.SerialInstrument.__init__(self,port=port)
        self.termination_character = '\r'
        self.stepsize = 10
        if controllerNOM<10:
            controllerNOM = "0%s" %controllerNOM
        self.controllerNOM = controllerNOM
        self.motor_on()

    def _send_command(self, msg):
        self.ser.write('{0}{1}'.format(self.controllerNOM, msg))

    def _readerror(self):
        '''
        This function returns the current error (if any)

        Could be useful to have it check for errors after every function call

        Returns:

        '''
        self.ser.write('{0}TE?'.format(self.controllerNOM))
        a = self.ser.readline()
        b = a.split(' ')[1]
        error = b.split('\r')[0]

        if error != 0:
            self._logger.warn('%s' % (ERROR_CODE[error]))
            return ERROR_CODE[error]

    def getHardwareStatus(self):
        self._send_command('PH?')
        status = self.ser.readline()
        return status

    def getControllerStatus(self):
        self._send_command('TS?')
        status = self.ser.readline()
        return status

    def stop_motion(self):
        self._send_command('ST')

    def move(self, pos, relative=True):
        if relative:
            self._send_command("PR{0}".format(pos))
        else:
            self._logger.warn('NanoPZ does not have absolute moving')
        
    # def move_rel(self,value):
    #     self.write("{0}PR{1}".format(self.controllerNOM, value))
    
    def move_step(self,direction):
        self.move_rel(direction*self.stepsize)
        
    def motor_on(self):
        self._send_command("MO")
        
    def get_position(self, axis=None):
        return self.query("{0}TP?".format(self.controllerNOM))[len("{0}TP?")-1:]
        
    def set_zero(self):
        self._send_command("OR")
        
    def lower_limit(self,value):
        if value <0:
            self._send_command("SL{0}".format(value))
        else:
            print("The lower Limit must be less than 0, current lower limit = ",self.query("{0}SL?".format(self.controllerNOM)))
            
    def upper_limit(self,value):
        if value >0:
            self._send_command("SR{0}".format(value))
        else:
            print("The upper Limit must be greater than 0, current upper limit = ",self.query("{0}SR?".format(self.controllerNOM)))


        
if __name__ == '__main__':
    teststage = NanoPZ(port = "COM25")
        