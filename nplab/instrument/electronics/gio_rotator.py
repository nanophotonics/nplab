# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 10:36:15 2020

@author: Eoin Elliott
"""
import time
from nplab.instrument.serial_instrument import SerialInstrument

class ArduinoRotator(SerialInstrument):
    STEPS_PER_REV = 16361.3
    max_int = 32_767 # biggest integer the arduino can hold
    def __init__(self, port):
        self.termination_character = '\n'
        SerialInstrument.__init__(self, port)
        self.flush_input_buffer()
        self.ignore_echo = True
        self.timeout = 0.5
        time.sleep(2) # for some reason this is necessary to change default speed
        self.speed = 15
        self._logger.setLevel('WARN')
        
    # def query(self, queryString, **args):
    #     return super().query(queryString, timeout=self.timeout, **args)
   
    @property
    def speed(self):
        return self._speed
    
    @speed.setter
    def speed(self, value):
        if value < 1: self._speed = 1
        if value > 15: self._speed = 15
        self._speed = int(value)
        self.write(f'S{self._speed}', ignore_echo=True)
        
    
    def move_raw(self, steps):
        start = time.time()
        cmd = f'M{int(steps)}'
        self._logger.info('command: ' + cmd)
        self.write(cmd, ignore_echo=True)
        while time.time() - start < 200:
            reply = self.readline().strip()
            if reply == '1':
                break
            if reply:
                self._logger.info('ki-> '+ reply)
            time.sleep(0.1)
    
    def move_a_lot(self, steps):
        if steps == 0: return  
        movements = 0
        sign = (1, -1)[steps<0]
        steps = abs(steps)
        if (-self.max_int > steps) or (steps > self.max_int):
            movements = steps // self.max_int
            steps = steps % self.max_int
        for movement in range(movements):
            self._logger.info('starting new command, rotation may be discontinuous')
            self.move_raw(sign*self.max_int)
        self.move_raw(sign*steps)
    
    def move(self, degrees):
        ''''clockwise'''
        self._logger.info(f'moving {degrees} degrees')
        self.move_a_lot(int(-degrees*self.STEPS_PER_REV/360))
    
    def calibrate(self, rotations: int = 5):
        print(f'rotating clockwise {rotations} rotations')
        self.speed = 15
        self.move(rotations*360)
        overshoot = float(input('''How far did it over/undershoot
                          (in degrees)?'''))
        
        self.STEPS_PER_REV = self.STEPS_PER_REV*(rotations)/(rotations+overshoot/360)
        print(f'{self.STEPS_PER_REV=} ')
    
if __name__ == '__main__':    
    ard = ArduinoRotator('COM3')
    ard._logger.setLevel('INFO')
    