from __future__ import division
from __future__ import print_function
from builtins import str
from builtins import range
from builtins import object
from past.utils import old_div
import visa
import numpy as np
import time

def Sigmoid(x,Shift=0.68207277,Scale=8.49175969):
    Zero=1./(np.exp(Shift*Scale)+1)
    One=1./(np.exp(-(1-Shift)*Scale)+1)
    
    Output=(x-Shift)*Scale
    Output=np.exp(-Output)+1
    Output=1./Output
    return old_div((Output-Zero),(One-Zero))
    
def Inverse_Sigmoid(x,Shift=0.68207277,Scale=8.49175969):
    Zero=1./(np.exp(Shift*Scale)+1)
    One=1./(np.exp(-(1-Shift)*Scale)+1)
    
    Output=-np.log((1./(((One-Zero)*x)+Zero))-1)
    Output/=Scale
    Output+=Shift 
    return Output

class AOM(object): 
    def __init__(self,address = 'USB0::0x0957::0x0407::MY44037993::0::INSTR'):
        rm = visa.ResourceManager()
        self.Power_Supply=rm.open_resource(address)
        self.mode = 'R'
        self.Power_Supply.write("FUNC DC")
        self.Power_Supply.write("VOLT:OFFS 1")
        
    def Switch_Mode(self):
        if self.mode=='R':
            self.mode = 'L'
        else:
            self.mode = 'R'
    @property
    def mode(self):
        return self._mode
    @mode.setter
    def mode(self, value):
        self._mode = value        
        out = 'SYSTEM:'        
        if value =='R': out+='REMOTE'
        else: out+= 'LOCAL'
        self.Power_Supply.write(out)

        
    def Power(self,Fraction=None):
#        if Fraction is None:
#            Voltage=float(self.Power_Supply.ask("SOUR:VOLT:OFFS?"))
#            return Inverse_Sigmoid(Voltage)
#        else:
#            if Fraction<0:
#                Fraction=0.
#            if Fraction>1:
#                Fraction=1.
#            Voltage=Sigmoid(Fraction)
#            self.Power_Supply.write("VOLT:OFFS "+str(Voltage))
#            
        if Fraction is None:
            return float(self.Power_Supply.ask("SOUR:VOLT:OFFS?"))
        else:
            if Fraction<0:
                Fraction=0.
            if Fraction>1:
                Fraction=1.
            self.Power_Supply.write("VOLT:OFFS "+str(Fraction))  
        
    def Get_Power(self):
        return float(self.Power_Supply.ask("SOUR:VOLT:OFFS?"))
    
    def Power_Apply(self, shape, frequency, amplitude, offset):
        self.Power_Supply.write("APPL:%s %d Hz, %f VPP, %f V" % (shape, frequency, amplitude, offset))
        
    def Find_Power(self,Power,Power_Meter,Laser_Shutter,Steps=10,Tolerance=1.):
        Bounds=[0,1]
        Laser_Shutter.close_shutter()
        Laser_Shutter.set_mode(1)
        
        def Take_Reading():
            Laser_Shutter.open_shutter()
            Output=[]
            Fail=0
            while len(Output)<20:
                try:
                    Output.append(Power_Meter.read)
                    Fail=0
                except:
                    Fail+=1
                if Fail==10:
                    raise Exception('Restart power meter')
            Laser_Shutter.close_shutter()
            return np.median(Output)*1000000
            
        x=[0.,1]
        y=[]
        for i in x:
            self.Power(i)   
            y.append(Take_Reading())         
            time.sleep(1)
        
        
        if y[0]>Power or y[1]<Power:
            print('Out of Range!')
            return
        
        for i in range(2):
            Bound=np.mean(x)
            self.Power(Bound)   
            Reading=Take_Reading()
            if Reading>Power:
                x[1]=Bound
                y[1]=Reading
            else:
                x[0]=Bound
                y[0]=Reading
            time.sleep(1)
            
        Step=0
        Error=np.inf
        while Step<Steps or Error>Tolerance:
            Step+=1
            print('Error:',str(round(Error,2)),'uW')
            if x[1]!=x[0]:
                m=old_div((y[1]-y[0]),(x[1]-x[0]))
                c=y[0]-(m*x[0])
                Guess=old_div((Power-c),m)
                self.Power(Guess)
                Reading=Take_Reading()
                Error=np.abs(Reading-Power)
                if Power<Reading:
                    y[1]=Reading
                    x[1]=Guess
                else:
                    y[0]=Reading
                    x[0]=Guess
                time.sleep(1)
            else:
                Step=np.inf 
                Error=0
        if x[1]!=x[0]:
            m=old_div((y[1]-y[0]),(x[1]-x[0]))
            c=y[0]-(m*x[0])
            Guess=old_div((Power-c),m)
        else:
            Guess=x[0]
        self.Power(Guess)
        Reading=Take_Reading()
        return Guess,Reading
        
if __name__ == '__main__':
    aom = AOM()
    aom.Switch_Mode()
    
    
            
