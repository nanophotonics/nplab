# -*- coding: utf-8 -*-
"""
Created on Fri Nov  3 17:02:07 2023

@author: smrs3
"""

import numpy as np
import nplab.datafile as df
import ctypes
import glob
import os.path
import pandas as pd
import time
from Timer import Timer

##folder path where Ivium data files are saved.
# Ivium data must also be saved as CSV files. make sure Options>Data handling options....>Always create data csv files..." is checked 
folder_path = r'D:\Ivium'   


file_type = r'\*csv'
data_file = df.current()

t = Timer()
t.start()
#%% START-UP potentiostat
'''REMINDER: make sure IviumSoft is running and potentiostat is connected on IviumSoft'''


#double check this is the path for the ivium driver
ivium_dll=ctypes.CDLL("C:\IviumStat\Software Development Driver\Ivium_remdriver64.dll")
#must run this to connect DLL to Ivium software
ivium_dll.IV_open(None)
IV_status=ivium_dll.IV_getdevicestatus(None)

if IV_status!=1:
    print("Check Ivium status")
else:
    print("Ivium connection ok")
    
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