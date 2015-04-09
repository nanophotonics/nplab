# -*- coding: utf-8 -*-
"""
Message Bus Instrument
======================

This base class 

@author: Richard Bowman
"""
from traits.api import HasTraits, Bool, Int, Str, Button, Array, Enum, List
import nplab
import time
import threading
import serial
import serial.tools.list_ports
import io
import re
import numpy as np

class MessageBusInstrument(object):
    """
    Message Bus Instrument
    ======================
    
    An instrument that communicates by sending strings back and forth over a bus.
    
    This base class provides commonly-used mechanisms that support the use of
    serial or VISA instruments.  The SerialInstrument and VISAInstrument classes
    both inherit from this class.
    
    Subclassing Notes
    -----------------
    
    The minimum you need to do to create a working subclass is override the
    `write()` and `readline()` methods.  You probably also want to provide an
    open() and close() method to deal with the underlying port, and put
    something sensible in __init__ to open your port when it's created.

    It's also a very good idea to provide some way to flush the input buffer
    with `flush_input_buffer()`.    
    """
    termination_character = "\n" #: All messages to or from the instrument end with this character.
    termination_line = None #: If multi-line responses are recieved, they must end with this string
    
    def write(self,query_string):
        """Write a string to the serial port"""
        raise NotImplementedError("Subclasses of MessageBusInstrument must override the write method!")
    def flush_input_buffer(self):
        """Make sure there's nothing waiting to be read.
        
        This function should be overridden to make sure nothing's lurking in
        the input buffer that could confuse a query.
        """
        pass
    def readline(self, timeout=None):
        """Read one line from the underlying bus.  Must be overriden."""
        raise NotImplementedError("Subclasses of MessageBusInstrument must override the readline method!")
    def read_multiline(self, termination_line=None, timeout=None):
        """Read one line from the underlying bus.  Must be overriden.
        
        This should not need to be reimplemented unless there's a more efficient
        way of reading multiple lines than multiple calls to readline()."""
        if termination_line is None:
            termination_line = self.termination_line
        assert isinstance(termination_line, str), "If you perform a multiline query, you must specify a termination line either through the termination_line keyword argument or the termination_line property of the NPSerialInstrument."
        response = ""
        last_line = "dummy"
        while termination_line not in last_line and len(last_line) > 0: #read until we get the termination line.
            last_line = self.readline(timeout)
            response += last_line
        return response
    def query(self,queryString,multiline=False,termination_line=None,timeout=None):
        """
        Write a string to the stage controller and return its response.
        
        It will block until a response is received.  The multiline and termination_line commands
        will keep reading until a termination phrase is reached.
        """
        self.flush_input_buffer()
        self.write(queryString)
        if termination_line is not None:
            multiline = True
        if multiline:
            return self.read_multiline(termination_line)
        else:
            return self.readline(timeout).strip() #question: should we strip the final newline?
    def parsed_query(self, query_string, response_string=r"(\d+)", re_flags=0, parse_function=int, **kwargs):
        """
        Perform a query, then parse the result.
        
        By default it looks for an integer and returns one, otherwise it will
        match a custom regex string and return the subexpressions, parsed through
        the supplied functions.
        
        TODO: make this accept friendlier sscanf style arguments, and produce parse functions automatically
        """
        reply = self.query(query_string, **kwargs)
        res = re.search(response_string, reply, flags=re_flags)
        if res is None:
            raise ValueError("Stage response to '%s' ('%s') wasn't matched by /%s/" % (query_string, reply, response_string))
        try:
            if len(res.groups()) == 1:
                return parse_function(res.groups()[0])
            else:
                return map(parse_function,res.groups())
        except ValueError:
            raise ValueError("Stage response to %s ('%s') couldn't be parsed by the supplied function" % (query_string, reply))
    def int_query(self, query_string, response_string=r"(\d+)", re_flags=0, **kwargs):
        """Perform a query and return the result(s) as integer(s) (see parsedQuery)"""
        return self.parsed_query(query_string, response_string, re_flags, int, **kwargs)
    def float_query(self, query_string, response_string=r"([.\d]+)", re_flags=0, **kwargs):
        """Perform a query and return the result(s) as float(s) (see parsedQuery)"""
        return self.parsed_query(query_string, response_string, re_flags, float, **kwargs)
            