# -*- coding: utf-8 -*-
"""
Created on Fri Sep 22 15:27:17 2017

@author: William Deacon (fo263)
"""
from __future__ import print_function
from builtins import str
from nplab.instrument.serial_instrument import SerialInstrument
from nplab.ui.ui_tools import QuickControlBox
import pyqtgraph as pg
import threading
import serial
from collections import deque
from nplab.utils.gui import QtCore, QtWidgets
import numpy as np
import time
from nplab.utils.notified_property import NotifiedProperty

class Frequency_counter_F390(SerialInstrument):
    port_settings = dict(baudrate=115200,
                         bytesize=serial.EIGHTBITS,
                         parity=serial.PARITY_NONE,
                         xonxoff=True,
                         timeout= 1.0)
    termination_character = "\n"
    update_data_signal = QtCore.Signal(np.ndarray)
    def __init__(self,port = None,integration_time = 1):
        SerialInstrument.__init__(self, port=port)
        self.live_window = 100
        self._live_view = False
        self.int_time = integration_time
        self.write('FO') #do not apply low pass filter
        self.write('Z5') #for 50 Ohms impedance
        
    function_dict = {'0' :  'B Input Period',
                    '1':    'A Input Period',
                    '2':    'A Input Frequency',
                    '3':    'B Input Frequency',
                    '4':    'Frequency Ratio B:A',
                    '5':    'A Input Width High',
                    '6':    'A Input Width Low',
                    '7':    'A Input Count',
                    '8':    'A Input Ratio H:L',
                    '9':    'A Input Duty Cycle',
                    'C':    'C Input Frequency',
                    'D':    'C Input Period'}
    def get_function(self):
        '''A property to set the required function of the frequency counter
        Args:
            f: the a string value of the function shown in the table below and in self.function_dict
            
            0 B Input Period
            1 A Input Period
            2 A Input Frequency
            3 B Input Frequency
            4 Frequency Ratio B:A
            5 A Input Width High
            6 A Input Width Low
            7 A Input Count
            8 A Input Ratio H:L
            9 A Input Duty Cycle
            C C Input Frequency
            D C Input Period
        returns:
            the current function
            '''
        return self.function_dict(self._function)
    def set_function(self,f):
        self._function = str(f)
        self.write('F'+str(f))

    function = property(fget=get_function,fset=set_function)
    
    def get_identity(self):
        '''Returns the device id (good for testing comms) '''
        return self.query('*IDN?')
    
    def test_communications(self):
        '''A command to allow autodetection to work '''
        if self.get_identity().split(',')[0] == 'Thurlby-Thandar':
            return True
    def measure_next(self):
        '''Return the next valid measurement'''
        try:
            return float(self.query('N?')[:-2])
        except:
            print(self.query('N?')[:-2])
    def measure_next_fast(self):
        '''Return the invalid measurement (i.e. refereshs at LCD refresh rate, not the measreument rate)'''
        try:
            return float(self.query('?')[:-2])
        except:
            print(self.query('?')[:-2])
#    def start_countinous_fast(self):
#        '''Starts fast streaming of values at the LCD refresh rate '''
#        self.write('C?')
#    def start_countinous_single(self):
#        '''Starts continuous streaming of values at the rate of the measurement time'''
#        self.write('E?')
#    def stop_countinous(self):
#        self.write('STOP')
    def get_live_view_window(self):
        return self._live_window
    def set_live_view_window(self,window_length):
        self._live_window = window_length
        '''Set the number of the stored values in the deque '''
        self.live_deque = deque(maxlen=window_length)
        
    live_window = NotifiedProperty(get_live_view_window,set_live_view_window)
    
    int_times = {0.3:'1',
                 1:'2',
                 10:'3',
                 100:'4'}
    impedances = {'50': 'Z5', 
                  '1M': 'Z1'}
    def get_int_time(self):
        '''A property for the integration time possible values are:
                0.3 s, 1s, 10s,100s '''
        return self._int_time
    def set_int_time(self,integration_time):
        self._int_time = integration_time
        try:
            self.write('M'+self.int_times[integration_time])
        except KeyError:
            self.log('Invalid integration time', level ='WARN')
    int_time = NotifiedProperty(get_int_time,set_int_time)
    
    def get_qt_ui(self):
        self.ui = CounterUI(self)
        self.display_ui = self.ui.preview_widget
        self.control_ui = self.ui.control_widget
        return self.ui
    def get_preview_widget(self):
        self.display_ui = CounterPreviewWidget(self)
        return self.display_ui
    def get_control_widget(self):
        self.control_ui = CounterControlUI(self)
        return self.control_ui
    def _live_view_function(self):
        '''The function that is run within the live preview thread '''
        while self._live_view:
            data = None
            data = self.measure_next_fast()
       #     while data == None:
            time.sleep(self.int_time)
            self.live_deque.append([data,time.time()])
            self.display_ui.update_data_signal.emit(np.array(self.live_deque))
       
    def get_live_view(self):
        '''Setting up the notificed property
        live view to allow live view to be switch on and off ''' 
        return self._live_view
    def set_live_view(self,enabled):
        if enabled==True:
            try:
                self._live_view = True
                self._live_view_stop_event = threading.Event()
                self._live_view_thread = threading.Thread(target=self._live_view_function)
                self._live_view_thread.start()
            except AttributeError as e: #if any of the attributes aren't there
                print("Error:", e)
        else:
            if not self._live_view:
                return # do nothing if it's not running.
            print("stopping live view thread")
            try:
                self._live_view = False
                self._live_view_stop_event.set()
                self._live_view_thread.join()
                del(self._live_view_stop_event, self._live_view_thread)
            except AttributeError:
                raise Exception("Tried to stop live view but it doesn't appear to be running!")
    live_view = NotifiedProperty(get_live_view,set_live_view)
                
class CounterPreviewWidget(QtWidgets.QWidget):
    """A Qt Widget to display the live feed from a camera."""
    update_data_signal = QtCore.Signal(np.ndarray)
    
    def __init__(self,counter):
        super(CounterPreviewWidget, self).__init__()
        
     #   self.plot_item = pg.pl

        self.plot_widget = pg.PlotWidget(labels = {'bottom':'Time'})
        self.plot = self.plot_widget.getPlotItem()
        self.setLayout(QtWidgets.QGridLayout())
        self.layout().addWidget(self.plot_widget)
        self.counter = counter
        # We want to make sure we always update the data in the GUI thread.
        # This is done using the signal/slot mechanism
        self.update_data_signal.connect(self.update_widget, type=QtCore.Qt.QueuedConnection)

    def update_widget(self, new_data):
        """Set the data to the latest"""
    #    print 'update',new_data
        self.plot.clear()
        self.plot.plot(new_data[:,1]-new_data[0,1],new_data[:,0])
class CounterControlUI(QuickControlBox):
    '''A quick control box to allow the user to change simple settings '''
    def __init__(self,counter):
        super(CounterControlUI, self).__init__(title = 'Counter_Control')
        self.counter = counter
        self.add_checkbox('live_view')
        self.add_spinbox('live_window')
        self.add_doublespinbox('int_time')
        self.auto_connect_by_name(controlled_object = self.counter)
        
class CounterUI(QtWidgets.QWidget):
    """Generic user interface for a camera."""
    def __init__(self, counter):
        #TODO: better checking (e.g. assert camera has color_image, gray_image methods)
        super(CounterUI, self).__init__()
        self.counter=counter
        
        # Set up the UI        
        self.setWindowTitle(self.counter.__class__.__name__)
        layout = QtWidgets.QVBoxLayout()
        # The image display goes at the top of the window
        self.preview_widget = self.counter.get_preview_widget()
        layout.addWidget(self.preview_widget)
        # The controls go in a layout, inside a group box.
        self.control_widget = self.counter.get_control_widget()
        layout.addWidget(self.control_widget)
        #layout.setContentsMargins(5,5,5,5)
        layout.setSpacing(5)
        self.setLayout(layout)
        
if __name__ == "__main__":
    counter = Frequency_counter_F390(port = 'COM14')
    counter.show_gui(blocking = False)
    