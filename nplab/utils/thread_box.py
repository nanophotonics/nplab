# -*- coding: utf-8 -*-
"""
Created on Wed Feb 28 16:00:07 2018

@author: wmd22
"""
from __future__ import print_function
from builtins import zip
from builtins import str
from nplab.ui.ui_tools import QuickControlBox
from nplab.utils.notified_property import NotifiedProperty
from nplab.utils.gui import QtWidgets
from nplab.utils.thread_utils import locked_action, background_action
import nplab.datafile as df

import numpy as np
import inspect
import threading


from nplab.utils.gui import QtWidgets, QtGui, QtCore

class ThreadBox3000(QuickControlBox):
    '''A gui/threading utility for running a function in a thread with a simple control window '''
    def __init__(self,function= None):
        super(ThreadBox3000,self).__init__('ThreadBox3000')
        self.function = function
    def add_controls(self,function):
        '''Inspect the inputted function and automatically generate controls by looking the defaults '''
        full_args = inspect.getargspec(function)
        self.add_checkbox('save_returned')
        self.add_lineedit('function name')
        self.controls['function name'].setText(str(function))
        self.controls['function name'].setReadOnly(True)
        if 'self' in full_args.args:
            full_args.args.remove('self')
        if (full_args.defaults != None 
                and len(full_args.args)==len(full_args.defaults)):
            for arg, default in zip(full_args.args, full_args.defaults):
                if type(default) == int:
                    self.add_spinbox(arg)
                    self.controls[arg].setValue(default)
                elif type(default) == float:
                    self.add_doublespinbox(arg)
                    self.controls[arg].setValue(default)
                elif type(default) == bool:
                    self.add_checkbox(arg)
                    self.controls[arg].setChecked(default)
                elif hasattr(default,'__call__'):
                    self.add_lineedit(arg)
                    try:
                        self.controls[arg].setText(default.__name__)
                    except Exception as e:
                        print(e)
                        self.controls[arg].setText(default.__name__)
                    self.controls[arg].setReadOnly(True)
                        
                else:
                    self.add_lineedit(arg)
                    if type(default)==np.ndarray:
                        
                        temp_txt = np.array2string(default).replace('   ',',') # danger - might need to check formatter
                        temp_txt = temp_txt.replace('  ',',')
                        temp_txt = temp_txt.replace(' ',',')
                        temp_txt = temp_txt.replace('[,','[')
                        temp_txt = temp_txt.replace(',]',']')
                        txt ='np.array('+temp_txt+')'
                    elif type(default)==str:
                        txt= "'"+default+"'"
                    else:
                        txt = str(default)
                    self.controls[arg].setText(txt)
        self.add_button('start')
        self.controls['start'].pressed.connect(self.start)                
    def construct_payload(self):
        '''Construct the function with the arguments set in the control window '''
        def payload(save_group=df._current_group):
            import numpy as np
            input_variables= {}
            for variable in list(self.controls.keys()):
                if variable == 'save_returned' or variable == 'start' or variable == 'function name':
                    continue
                
                variable_control = self.controls[variable]
                if type(variable_control) == type(QtWidgets.QLineEdit()) and variable_control.isReadOnly()==True:
                    fullargs = inspect.getargspec(self.function)
                    args = fullargs.args
                    try:
                        args.remove('self')
                    except ValueError:
                        pass
                    args = np.array(args)
                    defaults = np.array(fullargs.defaults)
                    default_value = defaults[args==variable]
                    input_variables[variable]=default_value[0]
                    print(variable, default_value)
                elif (type(variable_control) == QtWidgets.QSpinBox or 
                    type(variable_control) == QtWidgets.QDoubleSpinBox):
                    input_variables[variable]=variable_control.value()
                elif type(variable_control) == QtWidgets.QLineEdit:
                    try:
                        exec('temp_var = '+variable_control.text(), locals())   
                        input_variables[variable]=temp_var

                    except Exception as e:
                        print(e)
                        print('Qlineedit input error for ',variable)
                elif type(variable_control) == QtWidgets.QCheckBox:
                    input_variables[variable]=variable_control.isChecked()
            try:
                function_returns = self.function(**input_variables)
            except TypeError:
                print(input_variables)
                print('function: ',task)
                print('Did not recieve the correct inputs!')
                print('did you make an error in your lineedit inputs?')
            if self.controls['save_returned'].isChecked()==True:
                save_group.create_dataset(task,
                                          data = function_returns,
                                          attrs = input_variables)
        return payload
    def clean_box(self):
        '''Remove all of the controls from the box '''
        if len(self.children())>1: #check if the box contains any controls
            for child in self.children()[1:]:
                child.deleteLater()
            self.controls = dict()
    def set_function(self,function):
        '''Sets the function, by clearing the old function with 'clean_box' 
            and adding the controls for he new function '''
        self._function = function
        self.clean_box()
        if function is not None:
            self.add_controls(function)
    def get_function(self):
        '''The getter for the current function '''
        return self._function
    function = NotifiedProperty(fget = get_function,fset = set_function)
    @background_action
    @locked_action
    def start(self):
        '''Construct and start the function '''
        self.construct_payload()()
    def get_qt_ui(self):
        return self
    
if __name__ == '__main__':
    def print_hello(spade = '1'):
        print(spade)
    from nplab.utils.gui import get_qt_app
    app = get_qt_app()    
    thread_box = ThreadBox3000(print_hello)
        