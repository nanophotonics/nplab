# -*- coding: utf-8 -*-
"""
Created on Fri Nov  3 17:02:07 2023

@author: smrs3
"""

import numpy as np
from nplab import datafile
from nplab.instrument import Instrument
import ctypes
import glob
import os.path
import pandas as pd
import time
import pyvium as iv
#from Timer import Timer



class Ivium(Instrument):
    
    '''
    Class handling Ivium Potentiostat
    '''

    def __init__(self):
        
        Instrument.__init__(self)
        
        # Locate & open Ivium DLL
        self.dll = ctypes.CDLL("C:\IviumStat\Software Development Driver\Ivium_remdriver64.dll")
        self.dll.IV_open(None)

        # Check Ivium status
        self.status = self.dll.IV_getdevicestatus(None)
        assert self.status == 1, 'Check Ivium status'
        print('Ivium connection OK')
        
        # Create h5 datafile if none
        self.data_file = datafile.current()
        
        
    
        
    def get_all_datapoints(self):
        self.data = []
        total_points = self.dll.IV_Ndatapoints(ctypes.c_int(10))
        print(total_points)
        for point_index in range(1,total_points+1):
            t,V,I = self.dll.getdata(point_index)
            self.data.append([t,V,I])

if __name__ == "__main__":

    ivium = Ivium()        


    IV_method=ctypes.create_string_buffer(b"C:\Users\HERA\Documents\GitHub\nplab\nplab\instrument\potentiostat\E_step.imf")
    ivium.dll.IV_readmethod(ctypes.byref(IV_method))
    ivium.dll.IV_startmethod()
    print(ivium.dll.IV_getdevicestatus(None))
    ivium.get_all_datapoints()
    
    
    
#%% Using pyvium


import numpy as np
from nplab import datafile
from nplab.instrument import Instrument
import ctypes
import glob
import os.path
import pandas as pd
import time
import pyvium
from pyvium import Pyvium


class Ivium(Instrument, Pyvium):
    
    '''
    Class handling Ivium Potentiostat
    Uses pyvium library (pip install pyvium -> from pyvium import Pyvium as iv)
    '''

    def __init__(self):
        
        Instrument.__init__(self)
        
        ## Open Ivium dll & connect device
        self.open_driver()
        self.connect_device()

        ## Check Ivium status
        self.status = self.get_device_status()
        assert self.status[0] == 1, 'Check Ivium status'
        print('Ivium connected!')
        
        ## Create h5 datafile if none
        self.data_file = datafile.current()
        
        
    # Re-define start_method() function to wait for Ivium to finish measurement
    @staticmethod
    def start_method(method_file_path = ''):
        '''
        Starts a method procedure.
        If method_file_path is an empty string then the presently loaded procedure is started.
        If the full path to a previously saved method is provided
        then the procedure is loaded from the file and started.
        '''
        pyvium.PyviumVerifiers.verify_driver_is_open()
        pyvium.PyviumVerifiers.verify_iviumsoft_is_running()
        pyvium.PyviumVerifiers.verify_device_is_connected_to_iviumsoft()
        pyvium.PyviumVerifiers.verify_device_is_available()

        result_code, _ = pyvium.Core.IV_startmethod(method_file_path)

        if result_code == 1:
            raise FileNotFoundError
    
    

if __name__ == "__main__":

    ivium = Ivium()        


    # IV_method=ctypes.create_string_buffer(b"C:\Users\HERA\Documents\GitHub\nplab\nplab\instrument\potentiostat\E_step.imf")
    # ivium.dll.IV_readmethod(ctypes.byref(IV_method))
    # ivium.dll.IV_startmethod()
    # print(ivium.dll.IV_getdevicestatus(None))
    # ivium.get_all_datapoints()

 #%%
##folder path where Ivium data files are saved.
# Ivium data must also be saved as CSV files. make sure Options>Data handling options....>Always create data csv files..." is checked 
folder_path = r'D:\Ivium'   


file_type = r'\*csv'
data_file = df.current()

t = Timer()
t.start()
#%% START-UP potentiostat
# '''REMINDER: make sure IviumSoft is running and potentiostat is connected on IviumSoft'''


# #double check this is the path for the ivium driver
# ivium_dll=ctypes.CDLL("C:\IviumStat\Software Development Driver\Ivium_remdriver64.dll")
# #must run this to connect DLL to Ivium software
# ivium_dll.IV_open(None)
# IV_status=ivium_dll.IV_getdevicestatus(None)

# if IV_status!=1:
#     print("Check Ivium status")
# else:
#     print("Ivium connection ok")
    
#%% Potentiostat functions

#loads method file for modification
IV_method=ctypes.create_string_buffer(b'R:\smrs3\SERSbot\Ivium py code\E_step.imf')
ivium_dll.IV_readmethod(ctypes.byref(IV_method))

#defines function for running potential step programs on Ivium. Similar scripts can be adapted for other programs like CV or LSV
def run_Estep(set_E=-0.8000, t_samples=15, int_t=1):
    """
    Runs potential step program on IviumSoft by loading a saved method file and modifying parameters as needed. 
    set_E = potential in (V)
    int_t = interval time for measuring current
    t_samples = number of data points per interval time
    total time = t_samples * int_t
    """
    #loads this method file every time just in case other programs/techniques are run separately on Ivium. 
    IV_method=ctypes.create_string_buffer(b'R:\smrs3\SERSbot\Ivium py code\E_step.imf')
    ivium_dll.IV_readmethod(ctypes.byref(IV_method))
    
    #sets potential
    method_parameter=ctypes.create_string_buffer(b'E start')
    method_value=ctypes.create_string_buffer(str.encode(str(set_E)))
    ivium_dll.IV_setmethodparameter(ctypes.byref(method_parameter), ctypes.byref(method_value))

    #sets N samples time
    method_parameter=ctypes.create_string_buffer(b'N samples')
    method_value=ctypes.create_string_buffer(str.encode(str(t_samples)))
    ivium_dll.IV_setmethodparameter(ctypes.byref(method_parameter), ctypes.byref(method_value))

    #sets interval time
    method_parameter=ctypes.create_string_buffer(b'Interval time')
    method_value=ctypes.create_string_buffer(str.encode(str(int_t)))
    ivium_dll.IV_setmethodparameter(ctypes.byref(method_parameter), ctypes.byref(method_value))
    
    #runs modified program on IviumSoft
    ivium_dll.IV_startmethod(ctypes.byref(ctypes.create_string_buffer(b'')))

def save_Estep_data(filename, in_group=False):
    '''
    Work around for importing Ivium data. On IviumSoft, data must also be saved automatically as .CSV files. Function MUST be run AFTER Ivium is done running the desired method. 
    This function works by looking for the latest file saved automatically in the Ivium data folder. 
    must define folder path separetely:
        folder_path = r'D:\Ivium'
    This function specifically saves the current trace; time and set potential are saved as attributes
    '''
    
   
    files = glob.glob(folder_path + file_type)
    max_file = max(files, key=os.path.getctime)

    IV_data = pd.read_csv(max_file, names=["t", "I", "V"])
    IV_data_t=IV_data['t'].values.tolist()
    IV_data_I=IV_data['I'].values.tolist()
    IV_data_V=IV_data['V'].values.tolist()

    IV_data_tI=np.array([IV_data_t, IV_data_I])

    IV_data_attrs={"potential": IV_data_V, 
                    "time": IV_data_t,
                    "filename": max_file
                    }
    if in_group==True:
        group.create_dataset(name = filename,data = IV_data_I, attrs=IV_data_attrs)

    else:
        data_file.create_dataset(name = filename,data = IV_data_I, attrs=IV_data_attrs)

#%% example scripts for running potential step

filename='oxidation'

run_E=1.5
run_time=60

run_Estep(set_E=run_E, t_samples=run_time, int_t=1)
#delay waits for potential step to finish running on Ivium and for the data file to be saved as a CSV
t.delay(run_time+2)


save_Estep_data('IV_'+filename+'_'+str(run_E)+'_'+str(run_time), in_group=True)



#%%
#disconnect Ivium-python connection
ivium_dll.IV_close(None)