# -*- coding: utf-8 -*-
"""
Created on Wed May 31 14:20:06 2017

A control mechanism for running a 32-bit instrument from a 64-bit python console

@author: Will
"""
import numpy as np
import mmap
import time
import re
import inspect

from nplab.instrument.message_bus_instrument import MessageBusInstrument
from nplab.instrument.camera import DummyCamera


class VirtualInstrument_listener(object):
    def __init__(self,memory_size=65536,memory_identifier='VirtualInstMemory'):
        self.memory_map_in = mmap.mmap(0,memory_size , memory_identifier+'In')
        self.memory_map_out = mmap.mmap(0,memory_size*100 , memory_identifier+'Out')
        self.end_line = 'THE END\n'
        self.out_size = memory_size*100
        self.memory_identifier = memory_identifier
        np.set_printoptions(threshold=np.inf)
    def begin_listening(self):
        """ Start the listening loop
        """
        running = True
        while running == True:
            time.sleep(0.2)
            self.memory_map_in.seek(0)
            command_str = self.memory_map_in.readline()
            self.memory_map_in.seek(0)
            self.memory_map_in.write(self.end_line)
            command_str = re.sub('\n','',command_str)
     #       print 'command string in listening', command_str
            if command_str != self.end_line[:-1]:
                data = self.run_command_str(command_str)
                if data != None:
                    self.memory_map_out.seek(0)
          #          print data 
                    if not hasattr(data,'__iter__'):
                        data = (data,)
                    self.memory_map_out.write('data = [];')
                    for data_i in data:
                        try:
                            data_i_str = np.array_str(data_i)
            #                print data_i_str
                            try:
                                self.memory_map_out.write('data.append(np.array('+data_i_str+'));')
                            except ValueError:
                                print 'Memory map size error, Increase the output map size'

                        except AttributeError:
                            self.memory_map_out.write('data.append('+str(data_i)+');')
                    self.memory_map_out.write('\n'+self.end_line)
            
                    
                
                
                
            
    def run_command_str(self,input_str):
        #example input string = create_dataset(name='blah',data = 'blah')
        command = re.sub(r'\((.*?)\)','',input_str)
        if hasattr(self,command):
            print 'command' , command
            function = getattr(self,command)
            input_list = re.findall(r'\((.*?)\)',input_str)[0].split(',')
            if len(input_list)>1:
                input_dict = {}
                for input_param in input_list:
                    input_param_split = input_param.split('=')
                    if len(input_param_split)==2:
                        input_dict[input_param.split('=')[0]] = input_param.split('=')[1]
                    else:
                        print 'Arguments must be named for use through VirtualInstrument'
                print 'input_dict', input_dict
                return function(**input_dict)
            else:
                print'got to run'
                return function()                
#            return_vals = exec('self.'+input_str)
            
        else:
            print command, 'does not exist'
    def test_command(arg1,arg2='potato'):
        print arg1,arg2
        
class VirtualInstrument_speaker(MessageBusInstrument):
    def __init__(self,memory_size=65536,memory_identifier='VirtualInstMemory'):
        self.end_line = 'THE END\n'
        self.memory_map_in = mmap.mmap(0,memory_size , memory_identifier+'In')
        self.memory_map_in.write(self.end_line)
        self.memory_map_out = mmap.mmap(0,memory_size*100 , memory_identifier+'Out')
        self.memory_map_out.write(self.end_line)

        self.out_size = memory_size*100
        self.memory_identifier = memory_identifier
        self.listener = virtual_dum_cam_listener(memory_size,memory_identifier)
    def read(self):
        self.memory_map_out.seek(0)
        reading = True
        lines = ''
        while reading:
            new_line = self.memory_map_out.readline()
#            print new_line
            if new_line == self.end_line:
                reading=False
            else:
                lines+=new_line
            if new_line=='':
                return None
#        print 'lines', lines
        data = re.sub('\n','',lines)
#        print 'data', data
        data = re.sub(r'\]  *\[','],[',data)
  #      data = re.sub(r'([\[\]])  *([0-9])','\1\2',data)
#        print 'subbed_data',data
  #      data = re.sub(r'  ',',',data)
        data = re.sub(r'([0-9])  *([0-9])',r'\1,\2',data)
        data = re.sub(r'([0-9])  *([0-9])',r'\1,\2',data)
        data = re.sub(' *','',data)
  #      data = re.sub(r'  ',',',data)
#        print '2nd sub data',data
        self.memory_map_out.seek(0)
        self.memory_map_out.write(self.end_line+'\n')
        try:
            exec(data)
            return data
    #        return data
        except:
            return None
       #     return lines
    def write(self,command):
        self.memory_map_in.seek(0)
        self.memory_map_in.write(command+'\n')
        self.memory_map_in.write(self.end_line)
        
class DummyCameraStripped(DummyCamera):
    def __init__(self):
        DummyCamera.__init__(self)
        

        
def function_builder(command_name):
    def function(*args,**kargs):
        input_str = ''
        obj = args[0]
        if len(args)>1:
            for input_value in args[1:]:
                input_str+=str(input_value)+','
        for input_name,input_value in kargs.iteritems():
            input_str = input_str+input_name+'='+input_value+','
        input_str = input_str[:-1]
        print 'input str',input_str, command_name
        obj.memory_map_in.seek(0)
        obj.memory_map_in.write(command_name+'('+input_str+')\n')
        print 'written string',command_name+'('+input_str+')\n'
        time.sleep(1)
        return obj.read()
    return function
        #print input_str
     
#function_dict = {}  
for command_name in DummyCamera.__dict__.keys():
    command =getattr(DummyCameraStripped,command_name)
    print command_name,inspect.ismethod(command),command
    if inspect.ismethod(command):
         setattr(DummyCameraStripped,command_name,function_builder(command_name))

class virtual_dum_cam(DummyCameraStripped,VirtualInstrument_speaker):
    def __init__(self):
        VirtualInstrument_speaker.__init__(self)
   #     DummyCameraStripped.__init__(self)
       
   #     super(virtual_dum_cam).__init__()
        
   
class virtual_dum_cam_listener(DummyCamera,VirtualInstrument_listener):
    def __init__(self,memory_size=65536,memory_identifier='VirtualInstMemory'):
        VirtualInstrument_listener.__init__(self,memory_size,memory_identifier)
        DummyCamera.__init__(self)
             
    

def create_speaker_class(original_class):
 #   listener_class = getattr(nplab,full_class_name)
    class original_class_Stripped(original_class):
        def __init__(self):
            original_class.__init__(self)
#    function_dict = {}  
    for command_name in original_class.__dict__.keys():
        command = getattr(original_class_Stripped,command_name)
        print command_name,inspect.ismethod(command),command
        if inspect.ismethod(command):
             setattr(original_class_Stripped,command_name,function_builder(command_name))
    class virtual_speaker_class(original_class_Stripped,VirtualInstrument_speaker):
        def __init__(self,memory_size=65536,memory_identifier='VirtualInstMemory_'+original_class.__name__):
            VirtualInstrument_speaker.__init__(self,memory_size,memory_identifier)
    return virtual_speaker_class()

def create_listener_class(original_class):
    class virtual_listener(original_class,VirtualInstrument_listener):
        def __init__(self,memory_size=65536,memory_identifier='VirtualInstMemory_'+original_class.__name__):
            print memory_identifier
            original_class.__init__(self)      
            VirtualInstrument_listener.__init__(self,memory_size,memory_identifier)
            print self.memory_identifier
            
    return virtual_listener

def create_listener_by_name(module_name,class_name):
    exec('from '+(module_name+" import "+class_name)+' as '+ class_name)
    exec('virtual_listener=create_listener_class('+class_name+')')
    print type(virtual_listener)
    return virtual_listener

def setup_communication(original_class):
    speaker_class = create_speaker_class(original_class)
    import subprocess
    subprocess.call(["python32",
                     "-c",
                     "\"exec('from nplab.instrument.virtual_instrument import inialise_listenser;inialise_listenser(\"'+original_class.__module__+'\",\"'+original_class.__name__+'\")')\""])
    return speaker_class()
def inialise_listenser(module_name,class_name):
    print 'start'
    listener_class = create_listener_by_name(module_name,class_name)
    listener = listener_class()
    listener.begin_listening()
    print 'hello'
    return 1