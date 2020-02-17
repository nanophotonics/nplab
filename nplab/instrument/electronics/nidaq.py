from __future__ import division
from __future__ import print_function
from builtins import str
from builtins import range
from past.utils import old_div
__author__ = 'alansanders'

from nplab.instrument import Instrument
from pydaqmx import *
import pydaqmx as pdmx #pointess line of code ?
import numpy as np


class NIDAQ(Instrument):
    """An interface for NIDAQ devices."""

    def __init__(self, device_id):
        """

        :param device_id: a string identifier, e.g. 'Dev1'
        """
        super(NIDAQ, self).__init__()
        self.device_id = device_id
        self.current_task = None
        self.channels = None
        self.sample_rate = None
        self.time_interval = None
        self.num_points = None

    def setup_multi_ai(self, channels, sample_rate, time_interval):
        """
        Setup the DAQ device for multiple channel analog input. In this implementation the
        task is not started, only setup with the task committed to improve start speed.

        :rtype : object
        :param channels: an iterable containing a sequence of channel identifiers, e.g. 0,1,2..
        :param sample_rate: the sampling frequency
        :param time_interval: the time interval over which data is sampled
        """
        num_samples = int(sample_rate * time_interval)  # this is the number of points expected per channel
        while num_samples % len(channels) != 0:  # the number of samples must be evenly divisable between all channels
            num_samples += 1  # the number of samples is increased until all channels are equal
        self.num_samples = num_samples
        self.time_interval = time_interval
        analog_input = Task()
        s = ''
        for ch in channels:
            s += '{0}/ai{1},'.format(self.device_id, str(ch))
        analog_input.CreateAIVoltageChan(s, "", DAQmx_Val_Cfg_Default, -10.0, 10.0, DAQmx_Val_Volts, None)
        analog_input.CfgSampClkTiming("", sample_rate, DAQmx_Val_Rising, DAQmx_Val_FiniteSamps, num_samples)
        analog_input.TaskControl(DAQmx_Val_Task_Commit)
        self.current_task = analog_input
        self.channels = channels

    def read_multi_ai(self):
        """
        Read from a DAQ device previously setup using setup_multi_ai. The task is started and
        then stopped once complete. The data is then parsed and returned.

        :rtype : np.ndarray, np.ndarray
        :return: time, data
        """
        analog_input = self.current_task
        read = int32()
        total_samples = self.num_samples * len(self.channels)
        data = np.zeros((total_samples,), dtype=np.float64)
        time = np.linspace(0, self.time_interval, self.num_samples)
        analog_input.StartTask()
        analog_input.ReadAnalogF64(self.num_samples,#DAQmx_Val_Auto,
                                   -1,#DAQmx_Val_WaitInfinitely,
                                   DAQmx_Val_GroupByChannel,
                                   data,
                                   total_samples, byref(read), None)
        analog_input.StopTask()
        data = self._parse_data(self.channels, data)
        return time, data

    def setup_multi_ai_cont(self, channels, sample_rate, time_interval):
        '''
        '''
        analog_input = Task()
        analog_counter = Task()
        num_samples = int(sample_rate * time_interval) # this is the number of points expected per channel
        while num_samples%len(channels) != 0: num_samples += 1
        self.num_samples = num_samples
        self.time_interval = time_interval
        # DAQmx Configure Code
        s = ''
        for ch in channels:
            s += self.device+'/ai'+str(ch)+','
        # create an analog input channel named aiChannel
        analog_input.CreateAIVoltageChan(s, "aiChannel",
                                         DAQmx_Val_Cfg_Default,
                                         -10.0, 10.0, DAQmx_Val_Volts,
                                         None)
        # create the clock for my analog input task
        analog_input.CfgSampClkTiming("/%s/Ctr0InternalOutput"%self.device,
                                      sample_rate, DAQmx_Val_Rising,
                                      DAQmx_Val_ContSamps, num_samples)
        # configure analog input buffer
        #analog_input.SetBufferAttribute(DAQmx_Buf_Input_BufSize, num_samples+1000)
        # create a counter output channel named coChannel */
        analog_counter.CreateCOPulseChanFreq('/%s/ctr0'%self.device,
                                                  "coChannel", DAQmx_Val_Hz,
                                                  DAQmx_Val_Low, 0, sample_rate, 0.5)

    	  # create the clock for my counter output task*/
        analog_counter.CfgImplicitTiming(DAQmx_Val_FiniteSamps, num_samples)
        analog_counter.CfgDigEdgeStartTrig('/%s/PFI0'%self.device, DAQmx_Val_Rising)
        analog_counter.SetTrigAttribute(DAQmx_StartTrig_Retriggerable, True);
        # DAQmx Start Code
        analog_input.StartTask()
        analog_counter.StartTask()
        #analog_input.TaskControl(DAQmx_Val_Task_Commit)
        self.current_task = analog_input
        self.current_counter = analog_counter
        self.channels = channels

    def read_multi_ai_cont(self):
        analog_input = self.current_task
        read = int32()
        total_samples = self.num_samples * len(self.channels)
        data = np.zeros((total_samples,), dtype=np.float64)
        time = np.linspace(0, self.time_interval, self.num_samples)
        analog_input.ReadAnalogF64(self.num_samples,#DAQmx_Val_Auto,
                                   -1,#DAQmx_Val_WaitInfinitely,
                                   DAQmx_Val_GroupByChannel,
                                   data,
                                   total_samples, byref(read), None)
        #print "Acquired %d points"%read.value
        data = self._parse_data(self.channels, data)
        return time, data

    def _parse_data(self, channels, data):
        """
        The readout data is organised into an array n*m long, where n is the number of channels
        and m is the number of samples per channel. This method splits the readout data into n
        segments corresponding to each channel data.

        :param channels:
        :param data:
        :return: data
        """
        data = np.split(data, len(channels))
        return data

    def clear_multi_ai(self):
        """
        Clear the previously committed task as set in setup_multi_ai.

        :return:
        """
        self.current_task.TaskControl(DAQmx_Val_Task_Unreserve)

    def stop_current_task(self):
        """
        Force the current task to stop.

        :return:
        """
        self.current_task.StopTask()



class Itask(Task):
    """Essentially a wrapper for the NIDAQ Task object that allows multiple
    Tasks to be run without initialisation each time the Task needs to be run:
    """
    def __init__(self):
        Task.__init__(self)
        self.mode = None

    
    def setupmulti_ao(self,device_id,channels,minoutput,maxoutput):
        """ The command required to setup a task/channel in the analog output 
            configuration
        Args:
            device_id (string): the name of the device setup in NI Max
                                This should alawys be pulled straight from the 
                                NIDAQ object via self.device_id
            channels(list): The channel number you wish to control in list format
            minoutput (float): The minimum voltage the device will apply
            maxoutput(float): the maximum voltage a device can apply"""
        self.device_id = device_id
        self.minoutput = minoutput
        self.maxoutput = maxoutput
        self.channels = channels
        s = ''
        for ch in channels:
            s += '{0}/ao{1},'.format(self.device_id, str(ch))
            
        self.CreateAOVoltageChan(s,'',self.minoutput,self.maxoutput,DAQmx_Val_Volts, None)
        self.mode = "AO"
    
    def set_ao(self,value):
        """ the command for setting analog output voltages, input values are in 
            Volts. self.setupmulti_ao must be called before this method can be used
        
        Args:
            value(float): the new output voltage in Volts
            
        Raises:
            BaseException: The task is not currently in analog output mode i.e. run self.setupmulti_ao()"""
            
        if self.mode != "AO":
            raise BaseException('This Task is not setup for analog output, the current Task is setup for',self.mode)
        value = np.array(float(value))
        self.WriteAnalogF64( len(self.channels), True, 10.0, DAQmx_Val_GroupByChannel, value,  byref(int32()), None)


        
    
    
    
     
    
if __name__ == '__main__':
    from pylab import plot, show
    import timeit
    from time import sleep

    def multi_read(d):
        print(5./6000)
        d.setup_multi_ai([0,1,2,3,4], 1e6, 0.001)
        j = 0
        while j<2:
            time, data = d.read_multi_ai()
            ref = data[0]
            x = old_div(data[1],data[2])
            y = old_div(data[3],data[4])
            new_data = [ref, x, y]
            for i in range(len(new_data)):
                plot(time, new_data[i])
            j += 1
        d.clear_multi_ai()

    def cont_multi_read(d):
        print('should take %s ms' % (1000*5./6000.))
        d.setup_multi_ai_cont([0,1,2,3,4], 1e6, 5./6000.)
        i=0
        while i<10:
            sleep(1)
            time, data = d.read_multi_ai_cont()
            i+=1
        #print timeit.timeit(d.read_multi_ai_cont, number=1000)
        d.clear_multi_ai()
        #d.stop_current_task()

    daq = NIDAQ('Dev2')
    multi_read(daq)
    show()
    
    