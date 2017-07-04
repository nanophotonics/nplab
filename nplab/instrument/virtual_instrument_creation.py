# -*- coding: utf-8 -*-
"""
Created on Mon Jul 03 09:23:39 2017

@author: wmd22
A scipt for creating the 32 bit listener in the 64-32 control method
"""
import nplab
import inspect

def create_listener_class(listener_class):
 #   listener_class = getattr(nplab,full_class_name)
    class listener_class_Stripped(listener_class):
        def __init__(self):
            listener_class.__init__(self)
#    function_dict = {}  
    for command_name in listener_class.__dict__.keys():
        command = getattr(listener_class_Stripped,command_name)
        print command_name,inspect.ismethod(command),command
        if inspect.ismethod(command):
             setattr(listener_class_Stripped,command_name,function_builder(command_name))

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
        return obj.read()
    return function