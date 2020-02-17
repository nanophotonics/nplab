# -*- coding: utf-8 -*-

"""
Created on Wed May 31 14:20:06 2017

A control mechanism for running a 32-bit instrument from a 64-bit python console.
 It works creating by a pair of "virtual" instruments. One is the speaker element 
 (reciding in the original 64-bit console) and one is the listener (in the created 32-bit console).
 

@author: Will
"""
from __future__ import print_function
from builtins import str
from builtins import object
import numpy as np
import mmap
import time
import re
import inspect

from nplab.instrument.message_bus_instrument import MessageBusInstrument


class VirtualInstrument_listener(object):

    def __init__(self, memory_size=65536, memory_identifier='VirtualInstMemory'):
        """
        A class for creating the listening element of the "virtual" instrument, when subclassed this
        essentially creates a memory map and waits for commands. Upon receiving a command the instrument
        will execute the named command and pass back the results via a second map
        Args:
            memory_size(int):       The size of the in command memory map -
                                    100 times this value is used for the out

            memory_identifier(str): The memory str identifier - this is usually set as the "VirtualInstMemory_'classname'"
        """
        self.memory_map_in = mmap.mmap(0, memory_size, memory_identifier + 'In')
        self.memory_map_out = mmap.mmap(0, memory_size * 100, memory_identifier + 'Out')
        self.end_line = 'THE END\n'
        self.out_size = memory_size * 100
        self.memory_identifier = memory_identifier
        np.set_printoptions(
            threshold=np.inf)  # Set the prints options so that the arrays are printed as strings with no shortening

    def begin_listening(self):
        """ Start the listening loop, this is a never ending loop which looks for 
        commands in the 'In' memory map. The command is run via the 'run_command_str' function.
        The resulting data is then passed back through the out memory map.
        """
        running = True
        while running:
            time.sleep(0.01)
            self.memory_map_in.seek(0)
            command_str = self.memory_map_in.readline()
            self.memory_map_in.seek(0)
            self.memory_map_in.write(self.end_line)
            command_str = re.sub('\n', '', command_str)
            if command_str != self.end_line[:-1]:
                data = self.run_command_str(command_str)
                if data is not None:
                    self.memory_map_out.seek(0)
                    if not hasattr(data, '__iter__'):
                        data = (data,)
                    self.memory_map_out.write('data = [];')
                    for data_i in data:
                        try:
                            data_i_str = np.array_str(data_i)  # attempt to convert array's to a str
                            try:
                                self.memory_map_out.write('data.append(np.array(' + data_i_str + '));')
                            except ValueError:
                                print('Memory map size error, Increase the output map size')

                        except AttributeError:
                            # If the data is not a numpy array it will be passed at its str representation...This should work for most dtypes?
                            self.memory_map_out.write('data.append(' + str(data_i) + ');')
                    self.memory_map_out.write('\n' + self.end_line)

    def run_command_str(self, input_str):
        """
        Parse and run the passed in command from the input string which can
        also contain input arguments
        """
        command = re.sub(r'\((.*?)\)', '', input_str)
        if hasattr(self, command):
            #         print 'command' , command
            function = getattr(self, command)
            input_list = re.findall(r'\((.*?)\)', input_str)[0].split(',')
            if len(input_list) > 1:
                input_dict = {}
                for input_param in input_list:
                    input_param_split = input_param.split('=')
                    if len(input_param_split) == 2:
                        input_dict[input_param.split('=')[0]] = input_param.split('=')[1]
                    else:
                        print('Arguments must be named for use through VirtualInstrument')
                #           print 'input_dict', input_dict
                return function(**input_dict)
            else:
                #           print'got to run'
                return function()
            #            return_vals = exec('self.'+input_str)

        else:
            print(command, 'does not exist')


class VirtualInstrument_speaker(MessageBusInstrument):

    def __init__(self, memory_size=65536, memory_identifier='VirtualInstMemory'):
        """
        When subclassed creates the speaker half of the virtual instrument.
        It does this by creating read and write functions pass and parse commands/data to
        and from the listener instrument
        Args:
            memory_size(int):       The size of the in command memory map -
                                    100 times this value is used for the out

            memory_identifier(str): The memory str identifier - this is usually set as the "VirtualInstMemory_'classname'"
        """
        self.end_line = 'THE END\n'
        self.memory_map_in = mmap.mmap(0, memory_size, memory_identifier + 'In')
        self.memory_map_in.write(self.end_line)
        self.memory_map_out = mmap.mmap(0, memory_size * 100, memory_identifier + 'Out')
        self.memory_map_out.write(self.end_line)

        self.out_size = memory_size * 100
        self.memory_identifier = memory_identifier

    def read(self):
        """Function for reading from the memory map and parsing any data.
        """
        self.memory_map_out.seek(0)
        reading = True
        lines = ''
        while reading:
            new_line = self.memory_map_out.readline()
            #            print new_line
            if new_line == self.end_line:
                reading = False
            else:
                lines += new_line
            if new_line == '':
                return None
        data = re.sub('\n', '', lines)
        data = re.sub(r'\]  *\[', '],[', data)
        data = re.sub(r'([0-9])  *([0-9])', r'\1,\2', data)
        data = re.sub(r'([0-9])  *([0-9])', r'\1,\2', data)
        data = re.sub(' *', '', data)
        self.memory_map_out.seek(0)
        self.memory_map_out.write(self.end_line + '\n')
        try:
            exec(data)
            return data
        #        return data
        except:
            return None

    #     return lines
    def write(self, command):
        """
        Write the command name and arguments to the In memory map
        """
        self.memory_map_in.seek(0)
        self.memory_map_in.write(command + '\n')
        self.memory_map_in.write(self.end_line)


def function_builder(command_name):
    """A function for generating the write functions for intergrating classes with
    the speaker instrument class.
    """

    def wrapped_function(*args, **kwargs):
        input_str = ''
        obj = args[0]
        if len(args) > 1:
            for input_value in args[1:]:
                input_str += str(input_value) + ','

        for input_name, input_value in list(kwargs.items()):
            input_str = input_str + input_name + '=' + input_value + ','
        input_str = input_str[:-1]
        obj.memory_map_in.seek(0)
        obj.memory_map_in.write(command_name + '(' + input_str + ')\n')
        print(command_name + '(' + input_str + ')\n')
        time.sleep(1)
        return obj.read()

    return wrapped_function


def create_speaker_class(original_class):
    """
    A function that creates a speaker class by subclassing the original class
    and replacing any function calls with write commands that pass the functions to the listener
    """

    class original_class_Stripped(original_class):  # copies the class
        def __init__(self):
            original_class.__init__(self)

    for command_name in list(original_class.__dict__.keys()):  # replaces any method
        command = getattr(original_class_Stripped, command_name)
        if inspect.ismethod(command):
            setattr(original_class_Stripped, command_name, function_builder(command_name))

    class virtual_speaker_class(original_class_Stripped,
                                VirtualInstrument_speaker):  # creates the new class by sublcassing the stripped class and the speaker class
        def __init__(self, memory_size=65536, memory_identifier='VirtualInstMemory_' + original_class.__name__):
            VirtualInstrument_speaker.__init__(self, memory_size, memory_identifier)

    return virtual_speaker_class()


def create_listener_class(original_class):
    """A function that creates a subclass of the orignal class and the listener class
    Args:
        original_class(class):  The instrument class the listener will be a subclass of 
    """

    class virtual_listener(original_class, VirtualInstrument_listener):
        def __init__(self, memory_size=65536, memory_identifier='VirtualInstMemory_' + original_class.__name__):
            original_class.__init__(self)
            VirtualInstrument_listener.__init__(self, memory_size, memory_identifier)

    return virtual_listener


def create_listener_by_name(module_name, class_name):
    """A convenceince function for creating the listener class via the name of the module and class
    """
    exec ('from ' + (module_name + " import " + class_name) + ' as ' + class_name)
    exec ('virtual_listener=create_listener_class(' + class_name + ')')
    return virtual_listener


def setup_communication(original_class):
    """A function that creates both the speaker and the listener class, the speaker is created like a normal class
    while the listener is created using subprocess to call a 32-bit python console.
    Args:
        original_class(class):  The instrument you wish to create in the 32bit console
    Returns:
        speaker_class(class): The instrument used within the 64 bit consle to control the 32 bit instrument
        listner_console(subprocess.Popen): The subprocess console that the listner instrument exists within
    """
    speaker_class = create_speaker_class(original_class)
    import subprocess
    command_str = "exec(\'import qtpy;from nplab.instrument.virtual_instrument import inialise_listenser;inialise_listenser(" + r"\"" + original_class.__module__ + r"\",\"" + original_class.__name__ + r"\"" + ")')"
    listner_console = subprocess.Popen(["python32",
                                        "-c",
                                        command_str])
    return speaker_class, listner_console


# TODO: create an escape loop option for listening
def inialise_listenser(module_name, class_name):
    """The functions that is called within the 32bit console to create the listener and begin listening.
    """
    #   print 'start'
    listener_class = create_listener_by_name(module_name, class_name)
    listener = listener_class()
    listener.begin_listening()


#   print 'hello'
#  return 1

if __name__ == '__main__':
    from nplab.instrument.camera import DummyCamera

    speaker_cam, listener_console_cam = setup_communication(DummyCamera)
