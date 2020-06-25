# -*- coding: utf-8 -*-
"""
Serial Instrument interface

@author: Richard Bowman
"""

from __future__ import print_function
#from traits.api import HasTraits, Bool, Int, Str, Button, Array, Enum, List
from builtins import str
from nplab.instrument.message_bus_instrument import MessageBusInstrument
import threading
import serial
import serial.tools.list_ports
from serial import FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS
from serial import PARITY_NONE, PARITY_EVEN, PARITY_ODD, PARITY_MARK, PARITY_SPACE
from serial import STOPBITS_ONE, STOPBITS_ONE_POINT_FIVE, STOPBITS_TWO


import time

class SerialInstrument(MessageBusInstrument):
    """
    An instrument primarily using serial communications
    """
    port_settings = {}
    initial_character = ''
    """A dictionary of serial port settings.  It is passed as the keyword
    arguments to the constructor of the underlying serial port object, so
    see the documentation for pyserial for full explanations.

    port
        Device name or port number number or None.
    baudrate
        Baud rate such as 9600 or 115200 etc.
    bytesize
        Number of data bits. Possible values: FIVEBITS, SIXBITS, SEVENBITS, EIGHTBITS
    parity
        Enable parity checking. Possible values: PARITY_NONE, PARITY_EVEN, PARITY_ODD PARITY_MARK, PARITY_SPACE
    stopbits
        Number of stop bits. Possible values: STOPBITS_ONE, STOPBITS_ONE_POINT_FIVE, STOPBITS_TWO
    timeout
        Set a read timeout value.
    xonxoff
        Enable software flow control.
    rtscts
        Enable hardware (RTS/CTS) flow control.
    dsrdtr
        Enable hardware (DSR/DTR) flow control.
    writeTimeout
        Set a write timeout value.
    interCharTimeout
        Inter-character timeout, None to disable (default).
    """

    _serial_port_lock = threading.Lock()

    def __init__(self, port=None):
        """
        Set up the serial port and so on.
        """
        MessageBusInstrument.__init__(self) # Using super() here can cause issues with multiple inheritance.
         # Eventually this shouldn't rely on init...
        if self.termination_read is None:
            self.termination_read = self.termination_character
        self.open(port, False)
    def open(self, port=None, quiet=True):
        """Open communications with the serial port.

        If no port is specified, it will attempt to autodetect.  If quiet=True
        then we don't warn when ports are opened multiple times.
        """
        with self.communications_lock:
            if hasattr(self,'ser') and self.ser.isOpen():
                if not quiet: print("Warning: attempted to open an already-open port!")
                return
            if port is None: port=self.find_port()
            assert port is not None, "We don't have a serial port to open, meaning you didn't specify a valid port and autodetection failed.  Are you sure the instrument is connected?"
            self.ser = serial.Serial(port,**self.port_settings)
            # self.ser_io = io.TextIOWrapper(io.BufferedRWPair(self.ser, self.ser,1),
            #                                newline = self.termination_character,
            #                                line_buffering = True)
            #the block above wraps the serial IO layer with a text IO layer
            #this allows us to read/write in neat lines.  NB the buffer size must
            #be set to 1 byte for maximum responsiveness.
            assert self.test_communications(), "The instrument doesn't seem to be responding.  Did you specify the right port?"

    def close(self):
        """Release the serial port"""
        with self.communications_lock:
            try:
                self.ser.close()
            except Exception as e:
                print("The serial port didn't close cleanly:", e)

    def __del__(self):
        self.close()

    def write(self,query_string):
        """Write a string to the serial port"""
        with self.communications_lock:
            assert self.ser.isOpen(), "Warning: attempted to write to the serial port before it was opened.  Perhaps you need to call the 'open' method first?"
            try:
                if self.ser.outWaiting()>0: self.ser.flushOutput() #ensure there's nothing waiting
            except AttributeError:
                if self.ser.out_waiting>0: self.ser.flushOutput() #ensure there's nothing waiting
            self.ser.write(str.encode(self.initial_character+str(query_string)+self.termination_character))
            # self.ser.write(np.char.encode(np.array([self.initial_character+query_string+self.termination_character]), 'utf8'))

    def flush_input_buffer(self):
        """Make sure there's nothing waiting to be read, and clear the buffer if there is."""
        with self.communications_lock:
            if self.ser.inWaiting()>0: self.ser.flushInput()
    
    
    # def readline(self, timeout=None):
            # Retired from python 3 as it frequently times out when using an EOL that isn't \n.
            
    #     """Read one line from the serial port."""
    #     with self.communications_lock:
    #         return self.ser_io.readline().replace(self.termination_read,"\n")
        
    def readline(self, timeout = None):
        with self.communications_lock:
            if hasattr(self, 'timeout') and timeout is None: timeout = self.timeout
            elif timeout is None: timeout = 10
            eol = str.encode(self.termination_character)
            leneol = len(eol)
            line = bytearray()
            start = time.time()
            while time.time()-start<timeout:
                c = self.ser.read(1)
                if c:
                    line += c
                    if line[-leneol:] == eol:
                        break
                else:
                    break
            return line.decode().replace(self.termination_read, '\n')
    
    def test_communications(self):
        """Check if the device is available on the current port.

        This should be overridden by subclasses.  Assume the port has been
        successfully opened and the settings are as defined by self.port_settings.
        Usually this function sends a command and checks for a known reply."""
        with self.communications_lock:
            return True
    def find_port(self):
        """Iterate through the available serial ports and query them to see
        if our instrument is there."""
        with self.communications_lock:
            success = False
            for port_name, _, _ in serial.tools.list_ports.comports(): #loop through serial ports, apparently 256 is the limit?!
                try:
                    print("Trying port",port_name)
                    self.open(port_name)
                    success = True
                    print("Success!")
                except:
                    pass
                finally:
                    try:
                        self.close()
                    except:
                        pass #we don't care if there's an error closing the port...
                if success:
                    break #again, make sure this happens *after* closing the port
            if success:
                return port_name
            else:
                return None

