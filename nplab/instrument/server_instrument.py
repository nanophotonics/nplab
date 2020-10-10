# -*- coding: utf-8 -*-
"""
Functions for TCP server and client class creation for nplab instruments.

For example, you might have an instrument that needs to be connected to a particular computer (e.g. because of an
acquisition card, or because it only has 32bit DLLs), but you want to run your experiment from another computer (e.g. a
64bit computer). The create_server_class and create_client_class functions allows you to create a server instance that
will run on the computer connected to the instrument, and a client instance that will run on your desired computer.

The create_client_class creates a class that overrides the class' __dict__ values so that when you call a class method
(e.g. camera.capture()), it creates a string message that is sent over TCP (e.g. "{'command': 'capture'}").
The create_server_class creates a class that reads these messages and passes them on appropriately to the instrument
instance.

For TCP messaging we use repr and ast.literal_eval instead of json.dumps and json.loads because they allow us to easily
send Python lists/tuples

NOTE: class.__dict__ does not contain superclass attributes or methods, so by default we only override the class methods
    but not any of the base classes. If you want to also send the superclass methods to the server, you need to
    explicitly list which methods you want to send
    (https://stackoverflow.com/questions/7241528/python-get-only-class-attribute-no-superclasses)

WARN: this has not been extensively tested, and can definitely have some issues if the user is not careful about
    thinking what functions and replies he wants to send over the TCP communication and which ones he doesn't (e.g. you
    would not want to send the instrument.show_gui() command through TCP), and also that PyQT signals are not --and
    cannot be-- sent through the TCP, which might cause some confusion.

EXAMPLE:
    Creating a server and client instruments for a Princeton Instruments PVCAM which only has 32bit DLLs that do not
    work in Windows 10. First create a client class that also sends PvcamSdk functions to the server. You might want to
    also add a list of the nplab.instrument.camera methods:
    >>>> camera_client = create_client_class(Pvcam,
    >>>>                                     PvcamSdk.__dict__.keys() + ["get_camera_parameter", "set_camera_parameter"],
    >>>>                                     ('get_qt_ui', "raw_snapshot", "get_control_widget", "get_preview_widget"))
    >>>> camera_server = create_server_class(Pvcam)
    Then, on the computer connected to the camera, run:
    >>>> camera = camera_server((IP, port), 0)
    >>>> camera.run()
    And on the client computer run:
    >>>> camera = camera_client((IP, port))
    >>>> camera.show_gui()
"""
from __future__ import division

from future import standard_library
standard_library.install_aliases()
from builtins import str
from past.utils import old_div
from nplab.utils.log import create_logger
from nplab.utils.array_with_attrs import ArrayWithAttrs
import threading
import socketserver
import socket
import ast
import inspect
import numpy as np
import sys
import re

BUFFER_SIZE = 3131894
message_end = 'tcp_termination'.encode()


def parse_arrays(value):
    """Utility function to convert arrays to strings to be sent over TCP

    :param value: array to be converted
    :return:
    """
    if type(value) == ArrayWithAttrs:
        reply = repr(dict(array=value.tolist(), attrs=value.attrs))
    elif type(value) == np.ndarray:
        reply = repr(dict(array=value.tolist()))
    else:
        reply = repr(value)
    return reply


def parse_strings(value):
    """Utility function to convert strings back into arrays

    :param value: string containing an array
    :return:
    """
    if not isinstance(value, dict):
        value = ast.literal_eval(value)
    if isinstance(value, dict):
        if 'array' in value and 'attrs' in value:
            return ArrayWithAttrs(value['array'], value['attrs'])
        elif 'array' in value:
            return np.array(value['array'])
    else:
        return value


def subselect(string, size=100):
    """Utility function to create a shortened version of strings for logging

    :param string: string to be shortened
    :param size: maximum size of string allowed
    :return:
    """
    if len(string) > size:
        return '%s ... %s' % (string[:int(size/2)], string[-int(size/2):])
    else:
        return string


class ServerHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            raw_data = self.request.recv(BUFFER_SIZE).strip()
            while message_end not in raw_data:
                raw_data += self.request.recv(BUFFER_SIZE).strip()
            raw_data = re.sub(re.escape(message_end) + b'$', b'', raw_data)
            self.server._logger.debug("Server received: %s" % subselect(raw_data))

            if raw_data == b"list_attributes":
                instr_reply = list(self.server.instrument.__dict__.keys())
            else:
                command_dict = ast.literal_eval(raw_data.decode())
                if "command" in command_dict:
                    if "args" in command_dict and "kwargs" in command_dict:
                        instr_reply = getattr(self.server.instrument,
                                              command_dict["command"])(*command_dict["args"], **command_dict["kwargs"])
                    elif "args" in command_dict:
                        instr_reply = getattr(self.server.instrument, command_dict["command"])(*command_dict["args"])
                    elif "kwargs" in command_dict:
                        instr_reply = getattr(self.server.instrument, command_dict["command"])(**command_dict["kwargs"])
                    else:
                        instr_reply = getattr(self.server.instrument, command_dict["command"])()
                elif "variable_get" in command_dict:
                    instr_reply = getattr(self.server.instrument, command_dict["variable_get"])
                elif "variable_set" in command_dict:
                    setattr(self.server.instrument, command_dict["variable_set"],
                            parse_strings(command_dict["variable_value"]))
                    instr_reply = ''
                else:
                    instr_reply = "Dictionary did not contain a 'command' or 'variable' key"
        except Exception as e:
            self.server._logger.warn(e)
            instr_reply = dict(error=e)
        self.server._logger.debug("Instrument reply: %s" % subselect(str(instr_reply)))

        try:
            if type(instr_reply) == ArrayWithAttrs:
                reply = repr(dict(array=instr_reply.tolist(), attrs=instr_reply.attrs))
            elif type(instr_reply) == np.ndarray:
                reply = repr(dict(array=instr_reply.tolist()))
            else:
                reply = repr(instr_reply)
        except Exception as e:
            self.server._logger.warn(e)
            reply = repr(dict(error=str(e)))
        self.request.sendall(reply.encode() + message_end)
        self.server._logger.debug(
            "Server replied %s %s: %s" % (len(reply), sys.getsizeof(reply), subselect(reply)))


def create_server_class(original_class):
    """
    Given an nplab instrument class, returns a class that acts as a TCP server for that instrument.

    :param original_class: an nplab instrument class
    :return: server class
    """

    class Server(socketserver.TCPServer):
        def __init__(self, server_address, *args, **kwargs):
            """
            To instantiate the server class, the TCP address needs to be given first, and then the arguments that would
            be passed normally to the nplab instrument

            :param server_address: 2-tuple. IP address and port for the server to listen on
            :param args: arguments to be passed to the nplab instrument
            :param kwargs: named arguments for the nplab instrument
            """
            socketserver.TCPServer.__init__(self, server_address, ServerHandler, True)
            self.instrument = original_class(*args, **kwargs)
            self._logger = create_logger('TCP server')
            self.thread = None

        def run(self, with_gui=True, backgrounded=False):
            """
            Start running the server

            :param with_gui: bool. Runs the server in the background and opens the nplab instrument GUI
            :param backgrounded: bool. Runs the server in the background
            :return:
            """
            if with_gui or backgrounded:
                if self.thread is not None:
                    del self.thread
                self.thread = threading.Thread(target=self.serve_forever)
                self.thread.setDaemon(True)  # don't hang on exit
                self.thread.start()
                if with_gui:
                    self.instrument.show_gui()
            else:
                self.serve_forever()
    return Server


def create_client_class(original_class,
                        tcp_methods=None,
                        excluded_methods=('get_qt_ui', "get_control_widget", "get_preview_widget"),
                        tcp_attributes=None,
                        excluded_attributes=('ui', '_ShowGUIMixin__gui_instance')):
    """
    Given an nplab instrument, returns a class that overrides a series of class methods, so that instead of running
    those methods, it sends a string over TCP an instrument server of the same type. It is also able to get and set
    attributes in the specific class instance of the server.

    :param original_class: an nplab instrument class
    :param tcp_methods: an iterable of method names that are to be sent over TCP. By default it is the
                        original_class.__dict__.keys() excluding magic methods
    :param excluded_methods: methods you do not want to send over TCP. By default the get_qt_ui isn't sent over TCP,
            since it doesn't return something that can be sent over TCP (a pointer to an instance local to the server)
    :param tcp_attributes: attributes you do want to read over TCP.
    :param excluded_attributes: attributes you do not want to read over TCP, e.g. attributes that are inherently local.
            Hence, by default, the GUI attributes are not read over TCP.
    :return: new_class
    """

    def method_builder(method_name):
        """
        Given a method name, return a function that takes in any number of arguments and named arguments, creates a
        dictionary with at most three keys (command, args, kwargs) and sends it to the server that the instance is
        connected to

        :param method_name: string
        :return: method (function)
        """

        def method(*args, **kwargs):
            obj = args[0]
            command_dict = dict(command=method_name)
            if len(args) > 1:
                command_dict["args"] = args[1:]
            if len(list(kwargs.keys())) > 0:
                command_dict["kwargs"] = kwargs
            reply = obj.send_to_server(repr(command_dict))
            if type(reply) == dict:
                if "array" in reply:
                    if "attrs" in reply:
                        reply = ArrayWithAttrs(np.array(reply["array"]), reply["attrs"])
                    else:
                        reply = np.array(reply["array"])
            return reply

        return method

    class NewClass(original_class):
        def __init__(self, address):
            """
            The client instantiation also gets a list of attributes present in the server instrument instance

            :param address: 2-tuple of IP and port to connect to
            """
            self.address = address
            self._logger = create_logger(original_class.__name__ + '_client')
            self.instance_attributes = self.send_to_server("list_attributes", address)

        def __setattr__(self, item, value):
            """
            Overriding the base __setattr__

            :param item:
            :param value:
            :return:
            """
            # print "Setting: ", item
            # If the item is a method, pass it to the NewClass so that it can be sent to the server
            if item in self.method_list:
                super(NewClass, self).__setattr__(item, value)
            # If the item is a local attribute, set it locally
            elif item in ['instance_attributes', 'address', '_logger'] + excluded_attributes:
                original_class.__setattr__(self, item, value)
            # If the item is an attribute of the server instrument, send it over TCP. Note this if needs to happen after
            # the previous one, since it needs to use the self.instance_attributes
            elif item in self.instance_attributes or item in tcp_attributes:
                self.send_to_server(repr(dict(variable_set=item, variable_value=parse_arrays(value))))
            else:
                original_class.__setattr__(self, item, value)

        def send_to_server(self, tcp_string, address=None):
            """
            Opens a TCP port, connects it to address, sends the tcp_string, collects the reply, and returns it after
            literal_eval

            :param tcp_string: string to be sent over TCP
            :param address: address to send to
            :return: ast.literal_eval(reply_string)
            """
            if address is None:
                address = self.address
            if isinstance(tcp_string, str):
                tcp_string = tcp_string.encode()
            self._logger.debug("Client sending: %s" % subselect(tcp_string))
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(address)
                sock.sendall(tcp_string + message_end)
                self._logger.debug("Client sent: %s" % subselect(tcp_string))
                received = sock.recv(BUFFER_SIZE)
                while message_end not in received:
                    received += sock.recv(BUFFER_SIZE)
                received = re.sub(re.escape(message_end) + b'$', b'', received)
                self._logger.debug("Client received: %s" % subselect(received))
                sock.close()
                if b'error' in received:
                    raise RuntimeError('Server error: %s' % subselect(received))
            except Exception as e:
                raise e
            return ast.literal_eval(received.decode())

    if tcp_methods is None:
        tcp_methods = list(original_class.__dict__.keys())
    excluded_methods = list(excluded_methods)
    if tcp_attributes is None:
        tcp_attributes = list()
    excluded_attributes = list(excluded_attributes)

    methods = []
    for command_name in tcp_methods:
        command = getattr(NewClass, command_name)
        # only replaces methods that are not magic (__xx__) and are not explicitly excluded
        if (inspect.ismethod(command) or inspect.isfunction(command)) and not command_name.startswith('__') and command_name not in excluded_methods:
            setattr(NewClass, command_name, method_builder(command_name))
            methods += [command_name]
    setattr(NewClass, "method_list", methods)

    def my_getattr(self, item):
        # print("Getting: ", item, item in ["address", "instance_attributes"])
        if item in ["address", "instance_attributes", "method_list", "_logger", "__init__"] + excluded_attributes:
            # print('Excluded attribute: %s' % item)
            return object.__getattribute__(self, item)
            # return object.__getattr__(self, item)
        elif item in self.instance_attributes or item in tcp_attributes:
            # print('TCP: %s' % item)
            return self.send_to_server(repr(dict(variable_get=item)))
        elif item in excluded_methods:
            # print('Excluded method: %s' % item)
            # return original_class.__getattribute__(self, item)
            return original_class.__getattr__(self, item)
        else:
            return super(NewClass, self).__getattr__(item)

    setattr(NewClass, "__getattr__", my_getattr)

    return NewClass
