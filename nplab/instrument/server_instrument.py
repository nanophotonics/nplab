# -*- coding: utf-8 -*-
"""
Functions for TCP server and client class creation for nplab instruments. Not e

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

NOTE: class.__dict__ does not contain superclass attributes or methods (https://stackoverflow.com/questions/7241528/python-get-only-class-attribute-no-superclasses)
    Hence, by default we only override the methods of the class, but not of any of the base classes, so if you want to
    also send the super methods to the server, you need to explicitly list which methods you want to send.

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

from nplab.utils.log import create_logger
from nplab.utils.array_with_attrs import ArrayWithAttrs
import threading
import SocketServer
import socket
import ast
import inspect
import numpy as np
import sys
import re

BUFFER_SIZE = 3131894
message_end = 'tcp_termination'


class ServerHandler(SocketServer.BaseRequestHandler):
    def handle(self):
        try:
            raw_data = self.request.recv(BUFFER_SIZE).strip()
            self.server._logger.debug("Server received: %s" % raw_data)
            if raw_data == "list_attributes":
                instr_reply = repr(self.server.instrument.__dict__.keys())
            else:
                command_dict = ast.literal_eval(raw_data)

                if "command" in command_dict:
                    if "args" in command_dict and "kwargs" in command_dict:
                        instr_reply = getattr(self.server.instrument, command_dict["command"])(*command_dict["args"], **command_dict["kwargs"])
                    elif "args" in command_dict:
                        instr_reply = getattr(self.server.instrument, command_dict["command"])(*command_dict["args"])
                    elif "kwargs" in command_dict:
                        instr_reply = getattr(self.server.instrument, command_dict["command"])(**command_dict["kwargs"])
                    else:
                        instr_reply = getattr(self.server.instrument, command_dict["command"])()
                elif "variable_get" in command_dict:
                    instr_reply = getattr(self.server.instrument, command_dict["variable_get"])
                elif "variable_set" in command_dict:
                    setattr(self.server.instrument, command_dict["variable_set"], command_dict["variable_value"])
                    instr_reply = ''
                else:
                    instr_reply = "JSON dictionary did not contain a 'command' or 'variable' key"
        except Exception as e:
            self.server._logger.warn(e)
            instr_reply = dict(error=e)
        self.server._logger.debug("Instrument reply: %s" % str(instr_reply))

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
        reply += message_end
        self.request.sendall(reply)
        self.server._logger.debug(
            "Server replied %s %s: %s ... %s" % (len(reply), sys.getsizeof(reply), reply[:10], reply[-10:]))


def create_server_class(original_class):
    """

    :param original_class:
    :return:
    """
    class server(SocketServer.TCPServer):
        def __init__(self, server_address, *args, **kwargs):
            SocketServer.TCPServer.__init__(self, server_address, ServerHandler, True)
            self.instrument = original_class(*args, **kwargs)
            self._logger = create_logger('TCP server')
            self.thread = None

        def run(self, with_gui=True, backgrounded=False):
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

    return server


def create_client_class(original_class, tcp_methods=None, excluded_methods=('get_qt_ui',),
                        excluded_attributes=('ui', '_ShowGUIMixin__gui_instance')):
    """

    :param original_class:
    :param tcp_methods:
    :param excluded_methods:
    :param excluded_attributes:
    :return:
    """

    def method_builder(command_name):
        """

        :param command_name:
        :return:
        """

        def function(*args, **kwargs):
            obj = args[0]
            command_dict = dict(command=command_name)
            if len(args) > 1:
                command_dict["args"] = args[1:]
            if len(kwargs.keys()) > 0:
                command_dict["kwargs"] = kwargs
            print "Command dictionary: ", command_dict
            reply = obj.send_to_server(repr(command_dict))
            if type(reply) == dict:
                if "array" in reply:
                    if "attrs" in reply:
                        reply = ArrayWithAttrs(np.array(reply["array"]), reply["attrs"])
                    else:
                        reply = np.array(reply["array"])
            return reply

        return function

    class new_class(original_class):  # copies the class
        def __init__(self, address):
            self.address = address
            self._logger = create_logger(original_class.__name__ + '_client')
            self.instance_attributes = self.send_to_server("list_attributes", address)

        def __setattr__(self, item, value):
            # print "Setting: ", item
            if item in self.method_list:
                super(new_class, self).__setattr__(item, value)
            elif item in ['instance_attributes', 'address', '_logger'] + excluded_attributes:
                original_class.__setattr__(self, item, value)
            elif item in self.instance_attributes:
                self.send_to_server(repr(dict(variable_set=item, variable_value=value)))
            else:
                original_class.__setattr__(self, item, value)

        def send_to_server(self, command, address=None):
            if address is None:
                address = self.address
            self._logger.debug("Client sending: %s" % command[:50])
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(address)
                sock.sendall(command)
                self._logger.debug("Client sent: %s" % command[:50])
                received = sock.recv(BUFFER_SIZE)
                while message_end not in received:
                    received += sock.recv(BUFFER_SIZE)
                received = re.sub(re.escape(message_end) + '$', '', received)
                self._logger.debug("Client received: %s" % received[:20])
                sock.close()
            except Exception as e:
                raise e
            return ast.literal_eval(received)

    if tcp_methods is None:
        tcp_methods = original_class.__dict__.keys()
    excluded_attributes = list(excluded_attributes)

    methods = []
    for command_name in tcp_methods:
        command = getattr(new_class, command_name)
        # only replaces methods that are not magic (__xx__) and are not explicitly excluded
        if inspect.ismethod(command) and not command_name.startswith('__') and command_name not in excluded_methods:
            setattr(new_class, command_name, method_builder(command_name))
            methods += [command_name]
    setattr(new_class, "method_list", methods)

    def my_getattr(self, item):
        # print "Getting: ", item, item in ["address", "instance_attributes"]
        if item in ["address", "instance_attributes", "method_list", "_logger", "__init__"] + excluded_attributes:
            return object.__getattribute__(self, item)
        elif item in self.instance_attributes:
            return self.send_to_server(repr(dict(variable_get=item)))
        elif item in excluded_methods:
            return original_class.__getattribute__(self, item)
        else:
            super(new_class, self).__getattr__(item)
    setattr(new_class, "__getattr__", my_getattr)
    return new_class


