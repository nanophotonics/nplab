# -*- coding: utf-8 -*-
"""
@author: jb2444

controls an electrooptic modulator through an arduino operating a DFROBOT DAC,
that produces the DC voltage required for controlling the modulator setpoint.

designed to work with Arduino script:
Arduino_power_control_python_communication.ino

the commands to arduino are transferred by COM over USB connection;

command are to be written as <command:value>;
the <> signs need to be includded.

GVI:get_Vin(); ST:set_target(); SVO:set_Vout();GVO:get_Vout;  IL:is_locked; SL:start_locking();QL:quit_locking;SS:set_step;GS:get_step
GT:get_target; SIT: set_input_tolerance; GIT: get_input_tolerance;

variables:
step_size = 10; // 10mV
ulim = 5000; // 5V
llim = 0; //0 V
Vin = 0; input voltage is read and communicated in arduino DAC units that mean almost nothing,
Vout = 1500; output voltage defined in mV;
int target_voltage = 400; // in port values
bool is_locking = false;
bool is_target_value=false;
float voltage_step=3;
float input_tolerance=2;
int lock_time=1000;


"""

from nplab.ui.ui_tools import QuickControlBox
from nplab.instrument.serial_instrument import SerialInstrument
import numpy as np
import matplotlib.pyplot as plt
from time import sleep
from random import shuffle
from nplab.analysis.curve_fitting import my_curve_fit
from nplab.analysis.find_index import find_index

def fit_func(x, *params):
    F=np.zeros(x.shape)
    P=np.array([])
    for value in params:
        P=np.append(P,value)
    F=P[0]*(1+np.sin(P[1]*x+P[2]))+P[3]    
    return F

# def find_setpoint(x,y):
#     ind1 = find_index(y,np.max(y))[0][0]
#     ind2 = find_index(y,np.min(y))[0][0]
#     x_value = np.round((x[ind1]+x[ind2])/2)
#     return x_value

class Modulator(SerialInstrument):
    termination_character = '\n'
    s_mark='<'
    e_mark='>'
    legal_input=[ 'GVI', #:get_Vin() 
                 'ST', #set_target(); 
                 'SVO', #set_Vout();
                 'GVO', #get_Vout;  
                 'IL', #:is_locked; 
                 'SL', # start_locking();
                 'QL', # quit_locking;
                 'SS', #:set_step;
                 'GS', #:get_step
                 'GT', #:get_target; 
                 'SIT', #: set_input_tolerance; 
                 'GIT', #: get_input_tolerance;
                 ]
        
    port_settings = {'baudrate': 9600,
                     'timeout': 0.05}
    def __init__(self, port=None): # initialize communication and set device to zero
        SerialInstrument.__init__(self, port)
        
    def correct_input(self, command): # check legal input
        if (command in self.legal_input): 
            return True
        else:
            return False
       
    def get_property(self,command, report_success=False): # get parameter
        if self.correct_input(command):
            return self.query(self.s_mark+command+self.e_mark)
        else: 
            print('wrong command')

    def set_property(self, command,value): # set state
        if self.correct_input(command):
            self.write(self.s_mark+command+':'+str(value)+self.e_mark)
    
    def flush_buffer(self, *args, **kwargs):
        out = super().query(*args, **kwargs)
        self.log(out, 'info')
        while self.readline() != '':
            pass
        print('finished flushing buffer' + str(self.readline()))
        return out            
    
#    
    
    # def get_Vin(self):
    #     return self.get_property('GVI')
    def get_Vin(self):
        """
        adapted from serial bus instrument / query 
        because of an unexplained empty line in answer
        """
        termination = '\r\n'
        with self.communications_lock:
            self.flush_input_buffer()
            self.write('<GVI>')
            data=''
            while data=='':
                data = self.readline()
            data=data[0:data.find(termination)]
            return int(data)
    
    def get_target(self):
        return self.get_property('GT')
    def set_target(self):
        self.set_property('ST')
        print('target set to value: ')
        return self.get_target()
    def get_Vout(self):
        output = self.get_property('GVO')
        return float(output)
        
    def set_Vout(self,Vout):
        if Vout>=0 and Vout<=5000:
            self.set_property(command = 'SVO',value = Vout)
            output = self.get_Vout()
            print('voltage set to:'+str(output)+'mV')
        else: print('volatege not set, must be >=0 and <=5000')
        
    def is_locked(self):
        return self.get_property('IL') == 'True'
    
    def start_lock(self):
        self.write(self.s_mark+'SL'+self.e_mark)
    
    def stop_lock(self):
        self.write(self.s_mark+'QL'+self.e_mark)
    
    def set_step(self,value):
        if value>=0 and value<=1000:
            self.set_property('SS',value)
        else: print('step out of bounds')
        
    def get_step(self):
        return float(self.get_property('GS'))
    
    
    def get_input_tolerance(self):
        return float(self.get_property('GIT'))
    
    def set_input_tolerance(self,value):
        if value>0 and value<100:
            self.set_property('SIT',value)
      
    def sweep(self,start=100,stop=5000,num_of_steps=30,do_shuffle = True):
        Vout_vec=np.linspace(start,stop,num_of_steps)
        if do_shuffle:
            shuffle(Vout_vec)
        Vin = []
        for v in Vout_vec:
            self.set_Vout(v)
            #sleep(3)
            Vin.append(self.get_Vin())
        plt.figure()
        plt.scatter(Vout_vec,Vin)
        if do_shuffle:
           Vin = [a for junk,a in sorted(zip(Vout_vec,Vin))]
           Vout_vec=sorted(Vout_vec)
        return np.array(Vout_vec),np.array(Vin)
        
    def sweep_and_setpoint(self):
        x,y = self.sweep(start=100,stop=5000,num_of_steps=30,do_shuffle = True)
        calc_params, yfit, Rsquared = my_curve_fit(fit_func, 
                                                   x,
                                                   y,
                                                   [40,1/5000,1000,20] # fit for Bessel
                                                   )
        x_fake = np.linspace(np.min(x),np.max(x),1000)
        y_fake = fit_func(x_fake,calc_params)
        plt.figure()
        plt.scatter(x,y)
        plt.plot(x_fake,y_fake)
        ind1 = find_index(y_fake,np.max(y_fake))[0][0]
        period = np.abs(calc_params[1])
        quarter_period = 3.1415/(2*period)
        setpoint = np.round(x_fake[ind1]+quarter_period)
        plt.scatter(setpoint,fit_func(setpoint,calc_params))
        #setpoint = find_setpoint(x, y)
        self.set_Vout(setpoint)
    # def get_qt_ui(self):
    #     """Return a graphical interface for the lamp slider."""
    #     return MagnetUI(self)

# class MagnetUI(QuickControlBox):
#     def __init__(self, Magnet):
#         super().__init__(title='Magnet')
#         self.Magnet = Magnet
#         self.add_button('North')  # or function to connect
#         self.add_button('South')  # or function to connect
#         self.add_button('Zero')  # or function to connect
#         self.auto_connect_by_name(controlled_object=Magnet)

#%%
if __name__ == '__main__':
    modulator = Modulator('COM3')
    
    # magnet._logger.setLevel('INFO')
    # ui = magnet.show_gui(False)
    # ui.show()
