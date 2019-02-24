# -*- coding: utf-8 -*-
"""
Created on Sun Oct 07 12:43:44 2018

@author: wmd22
"""
import numpy as np
from scipy.interpolate import interp1d
from collections import deque
import time
import threading
class WheelOfPower(object):
    """A quick wrapper to add a filter wheel and a powermeter together to create
    an autocalibrate object which can move to a given power"""
    def __init__(self,power_meter,rotation_stage):
        self.power_meter = power_meter
        self.rotation_stage = rotation_stage
        self.abort_deque = False
        self.deque_time = 1.0
        self.deque_length = 100
        self.history_deque = deque(maxlen = self.deque_length)
    def calibrate(self, start = 0, stop = 360, steps = 360):
        stage_positions = np.linspace(start,stop,steps)
        powers = []
        for position in stage_positions:
            self.rotation_stage.move(position)
            powers.append(self.power_meter.average_power)
        powers = np.array(powers)
        interp_function = interp1d(stage_positions,powers)
        new_stage_positions = np.linspace(start,stop,steps*100)
        new_powers = interp_function(new_stage_positions)
        self.powers = new_powers
        self.stage_position = new_stage_positions
    def power_to_pos(self,power):
        """Find the closest power by looking up the interpolated table """
        return self.stage_position[self.powers==self.find_nearest(self.powers,power)]
    def find_nearest(self,array,value):
        """ find the minimum value of an array"""
        return array[np.abs(array - value).argmin()]
    
    def move_to_power(self,power):
        pos = self.power_to_pos(power)
        self.rotation_stage.move(pos)    
    def update_deque(self):
        running = True
        while running:
            t0 = time.time()
            current_powers = []
            while (time.time()-t0)<self.deque_time:
                current_powers.append(self.power_meter.average_power)
            self.history_deque.append(np.average(current_powers))    
            if self.abort_deque ==True:
                running = False
        self.abort_deque = False
    def start_deque_thread(self):
        self.deque_thread = threading.Thread(target=self.update_deque)
        self.deque_thread.start()
    def clear_deque_thread(self):
        self.history_deque = deque(maxlen = self.deque_length)
        