# -*- coding: utf-8 -*-
"""
Created on Fri Nov 03 11:06:56 2017

@author: wmd22
"""
from __future__ import print_function
from builtins import zip
from builtins import str
import pyqtgraph as pg
import pyqtgraph.dockarea
from nplab.utils.gui import QtCore, QtWidgets, QtGui
from nplab.ui.ui_tools import QuickControlBox
from nplab.utils.notified_property import DumbNotifiedProperty, NotifiedProperty
import nplab.datafile as df
import numpy as np
import inspect
import os

#from . import ParticleException

class Task_Manager(pyqtgraph.dockarea.DockArea):
    """ A taskmanager that allows the user to construcut a function from a list of 
    functions with gui controlled input paramters 
    """
    current_selected_task = DumbNotifiedProperty()

    def __init__(self, all_tasks_list=[], particle_scanner=None,
                working_directory=None):
        """ Args:
            all_tasks_list(list): A list of the tasks to be automatically added
                                to the task list
            particle_scanner(TrackingWizard): The particle tracking object the
                                                constructed function will be 
                                                used by
            work_directory(str): The working idrectory path
        """
        super(Task_Manager, self).__init__()
        if particle_scanner is None:
            print('No scanner defined!')
            raise ValueError
        else:
            self.scanner = particle_scanner
        if working_directory is None:
            self.working_directory = os.getcwd()
        else:
            self.working_directory = working_directory
        self.selected_tasks_controls = dict()
        self.selected_tasks = dict()
        self.selected_tasks_docks = dict()
        self.all_tasks_list = all_tasks_list
        self.task_control_box = QuickControlBox('Task Control')
        self.current_selected_task_index = 0
        self.task_control_box.add_combobox('current_selected_task_index',
                                           self.all_tasks_list,
                                           title = 'Current selected task')
        self.task_control_box.add_lineedit('new_task_method')
        self.task_control_box.add_button('add_new_task_to_list')
        self.task_control_box.add_button('add_task',title ='Add task')
        self.task_control_box.add_button('save_tasks',title ='Save tasks')
        self.task_control_box.add_button('load_tasks',title ='Load tasks')
        self.task_control_box.add_button('clear_tasks', title='Clear tasks')
        self.task_control_box.auto_connect_by_name(controlled_object = self)
        self.layout.addWidget(self.task_control_box)
        self.line_edit_types = [np.ndarray,type(None),list]
        self.abort_tasks = False
    
    def add_task_to_list(self,task_str):
        """Add a new task to the task_list 
        Args
            task_str(str): the name of the new task (fucntion)"""
        if task_str not in self.all_tasks_list:
            self.all_tasks_list = self.all_tasks_list+[task_str]
            combo_box = self.task_control_box.controls['current_selected_task_index']
            combo_box.addItem(task_str)
        else:
            print('Task is already in the list!')
    
    def add_new_task_to_list(self):
        """ Pull the new task name from the gui and add it to the list
        """
        new_task_str = self.task_control_box.controls['new_task_method'].text()
        self.add_task_to_list(new_task_str)
    
    def update_tasks_from_list(self,new_tasks):
        """Add a list of new_tasks to the task list
        Args:
            new_tasks(list[str]): a list containing the names of all the 
                                requested new functions"""
        for new_task in new_tasks:
            self.add_new_task_to_list(new_task)
        
    def get_current_selected_task(self):
        """wppaer to grab the current task """
        return self.all_tasks_list[self.current_selected_task_index]
    current_selected_task = property(get_current_selected_task)
    
    def add_task(self):
        """ Add a task to the payload by name from the current selected task
        """
        self.add_task_by_name(self.current_selected_task)
    
    def clear_tasks(self):
        self.clear()

    def add_task_by_name(self,name,suffix=None):
        """Find the named task and use inspect to generate a control box prior
        to creating a dock and therefore adding to the payload
        Args:
            name(str): The name of the task to be added, this can either be the 
                        name of the function as it esists in main or the name of 
                        a class method such "CWL.autofocs".
        """
        split_task = name.split('.')
        current_object = self.scanner
        try:
            for attr in split_task:
                if attr != '':
                    current_object = getattr(current_object, attr)
        except AttributeError:
            try:
                import __main__
                current_object = __main__
                for attr in split_task:
                    if attr != '':
                        current_object = getattr(current_object, attr)
            except AttributeError:
                print('The function:'+name+' does not exist')
                return None
                
        full_args = inspect.getargspec(current_object)
        if suffix != None:
            task_name = name+'_'+suffix
        elif name+'_0' not in self.selected_tasks:
            task_name = name+'_0'
        else:
            task_name_iterator = 0
            for task_name in self.selected_tasks:
                if (task_name.split('_')[:-1] ==
                        (name+'_0').split('_')[:-1]):
                    task_name_iterator += 1
            task_name = name+'_' + str(task_name_iterator)
        current_task_box = QuickControlBox(title=task_name)
        current_task_box.add_checkbox('save_returned')
        if 'self' in full_args.args:
            full_args.args.remove('self')
        if (full_args.defaults != None 
                and len(full_args.args)==len(full_args.defaults)):
            print(task_name, 'in full arg loop')
            for arg, default in zip(full_args.args, full_args.defaults):
                if type(default) == int:
                    current_task_box.add_spinbox(arg)
                    current_task_box.controls[arg].setValue(default)
                elif type(default) == float:
                    current_task_box.add_doublespinbox(arg)
                    current_task_box.controls[arg].setValue(default)
                elif type(default) == bool:
                    current_task_box.add_checkbox(arg)
                    current_task_box.controls[arg].setChecked(default)
                elif hasattr(default,'__call__'):
                    current_task_box.add_lineedit(arg)
                    try:
                        current_task_box.controls[arg].setText(default.__name__)
                    except Exception as e:
                        print(e)
                        current_task_box.controls[arg].setText(default.__name__)
                    current_task_box.controls[arg].setReadOnly(True)
                        
                else:
                    current_task_box.add_lineedit(arg)
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
                    current_task_box.controls[arg].setText(txt)
        else:
            for arg in full_args.args:
                current_task_box.add_lineedit(arg)

        self.selected_tasks[task_name] = current_object
        self.selected_tasks_controls[task_name] = current_task_box
        self.selected_tasks_docks[task_name] = pyqtgraph.dockarea.Dock(task_name,autoOrientation=False)
        self.selected_tasks_docks[task_name].titlePos ='top'
        self.selected_tasks_docks[task_name].addWidget(self.selected_tasks_controls[task_name])
        self.addDock(self.selected_tasks_docks[task_name])

        print('add dock win', task_name)
    
    
    def get_selected_task_order(self):
        """Request the current selected order of tasks by looking at the 
        current dock order.        
        """
        state = self.saveState()
        assert state['float'] == [], 'There is a floating task!Please redock!'
        main = state['main']
        horizontal_bool = not any(layout[0] == 'horizontal' for layout in main[1])
        assert horizontal_bool, 'Some of your tasks are set to run parallel!'
        
        dock_order = []
        for dock in main[1]:
            if dock[0] == 'vertical':
                stack_of_docks = dock[1:][0]
                for dock in stack_of_docks:
                    dock_order.append(dock[1])
            else:
                dock_order.append(dock[1])
        return dock_order
    selected_task_order = NotifiedProperty(get_selected_task_order)

    def construct_payload(self):
        """ Generate and return a function using the selected_task_order and their
            inputs.
        """
        def payload(save_group=df._current_group):
            import numpy as np
            for task in self.selected_task_order:
                if self.abort_tasks == True:
                    self.abort_tasks = False
                    raise ParticleException('Particle skip requested by the user')
                function = self.selected_tasks[task]
                control_box = self.selected_tasks_controls[task]
                input_variables= {}
                for variable in list(control_box.controls.keys()):
                    if variable == 'save_returned':
                        continue
                    variable_control = control_box.controls[variable]
                    if type(variable_control) == type(QtWidgets.QLineEdit()) and variable_control.isReadOnly()==True:
                        fullargs = inspect.getargspec(function)
                        args = fullargs.args
                        try:
                            args.remove('self')
                        except ValueError:
                            pass
              #          print fullargs
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
                            namespace = {}
                            exec('temp_var = '+variable_control.text(), namespace)
            #                assert (type(temp_var) == str or
            #                        hasattr(temp_var,'__iter__'))       
                            input_variables[variable]=namespace['temp_var']

                        except Exception as e:
                            print(e)
                            print('Qlineedit input error for ',variable)
                    elif type(variable_control) == QtWidgets.QCheckBox:
                        input_variables[variable]=variable_control.isChecked()
                try:
                    print(input_variables)
                    function_returns = function(**input_variables)
                except TypeError as e:
                    print(input_variables)
                    print('function: ',task)
                    print('Did not recieve the correct inputs!')
                    print('did you make an error in your lineedit inputs? error - ')
                    print(e)
                if control_box.controls['save_returned'].isChecked()==True:
                    save_group.create_dataset(task,
                                              data = function_returns,
                                              attrs = input_variables)
        return payload
    
    def save_tasks(self):
        """Save the current task list so the user can load them at a later date
        without having to add them all manually
        """
        save_dict = dict()
        save_dict['state'] = self.saveState()
        save_dict['controls'] = dict()
        controls_dict = save_dict['controls']
        for task_name in list(self.selected_tasks.keys()):
            controls_dict[task_name] = dict()
            controls_dict[task_name] = dict()
            task_dict = controls_dict[task_name]
            task_controls = self.selected_tasks_controls[task_name]
            for variable in list(task_controls.controls.keys()):
                variable_control = task_controls.controls[variable]
#                task_dict[variable+'_dtype'] = type(variable_control)
                if (type(variable_control) == QtWidgets.QSpinBox or 
                    type(variable_control) == QtWidgets.QDoubleSpinBox):
                    task_dict[variable] = variable_control.value()
                elif type(variable_control) == QtWidgets.QLineEdit:
                    task_dict[variable] = variable_control.text()
                elif type(variable_control) == QtWidgets.QCheckBox:
                    task_dict[variable] = variable_control.checkState()
        task_settings_path = QtWidgets.QFileDialog.getSaveFileName(
                caption="Create new task settings file",
                directory=self.working_directory)[0]
        np.save(task_settings_path,save_dict)

    def load_tasks(self):
        """ Load a previosuly used task_manger dock arrangement
        """
        for task_control in list(self.selected_tasks_controls.values()):
            task_control.close() 
        for task_control in list(self.selected_tasks_docks.values()):
            task_control.close() 
        self.selected_tasks_controls = dict()
        self.selected_tasks_docks = dict()

        task_settings_path = QtWidgets.QFileDialog.getOpenFileName(
                caption="Select Existing Data File",
                directory=self.working_directory,
                )[0]    
        loaded_dict = np.load(task_settings_path, allow_pickle=True)
      #  print loaded_dict, 'Dict Loaded'
        loaded_dict=loaded_dict[()]
      #  self.restoreState(loaded_dict['state'][])
        controls_dict = loaded_dict['controls']
        for task_name in controls_dict:
            try:
                suffix = str(int(task_name.split('_')[-1]))
                task_method_name = '_'.join(task_name.split('_')[:-1])
            except ValueError:
                suffix = None
                task_method_name = task_name
            self.add_task_by_name(task_method_name,suffix)
            task_dict = controls_dict[task_name]
            task_control = self.selected_tasks_controls[task_name]
            
         #   print task_controls.controls.keys()
            for variable in list(task_control.controls.keys()):
                variable_control = task_control.controls[variable]
                if (type(variable_control) == QtWidgets.QSpinBox or 
                    type(variable_control) == QtWidgets.QDoubleSpinBox):
                    variable_control.setValue(task_dict[variable])
                elif type(variable_control) == QtWidgets.QLineEdit:
                    variable_control.setText(task_dict[variable])
                elif type(variable_control) == QtWidgets.QCheckBox:
                    variable_control.setCheckState(task_dict[variable])
                        
        self.restoreState(loaded_dict['state'])

from particle_tracking_app.particle_tracking_wizard import TrackingWizard, ParticleException