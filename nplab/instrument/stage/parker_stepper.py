# -*- coding: utf-8 -*-
"""
Created on Fri Aug  3 16:53:34 2018

@author: ep558,wmd22
"""
from __future__ import division
from __future__ import print_function


from builtins import str
from past.utils import old_div
import nplab.instrument.serial_instrument as si

class ParkerStepper(si.SerialInstrument):
    '''Stepper object for controlling timedelay
    
    '''
    def __init__(self, port=None,max_steps = 12000000,calibration = 7500.0):
        '''Setup baud rate, return charcter and timeout '''
        self.termination_character = '\r'
        self.port_settings = {'baudrate':9600,'timeout':1}
        si.SerialInstrument.__init__(self,port=port)
        self.calibration = calibration
        self.max_steps = float(max_steps)
        self.initialise()
    def initialise(self):
        '''Set Calibration and make stepper ready to run '''
        self.write("SSA1")
        self.query("CMDDIR1") #Should be a query?
        self.write("MPI")
        self.write("A5")
        self.write("V4")
        self.write("8ER3200")
        self.write("8OSB1")
        self.write("8OSH0")
        self.write("8OSC0")
        self.write("8OSD0")
        self.write("8FSA0")
        self.query("8OS")  #SHOULD BE A QUERY?
        self.query("8FS")
    
    def moveto(self,newlocation,blocking = True):
        '''Moves to the requested stepper position
        Args:
            newlocation(int):   The new postion you want the stepper to move to                
        '''
        if newlocation>=self.max_steps or newlocation<0:
            print('Move failed as new postion was out of range')
            return None
        self.write("MN")
        self.write("MPA")
        self.write("8D"+str(newlocation))
        self.write("G")
        if blocking == True:
            self.location()
        
    def step(self,stepsize,blocking = True):
        '''Perform a signal step of size x
        Args:
            stepsize(int): '''
        self.write("MN")
        self.write("MPI")
        self.write("8D"+str(stepsize))
        self.write("G")
        if blocking == True:
            self.location()
        
    def loop(self,repeats,start,finish,velocity = 4,acceleration = 5):
        '''Perform a number of loops using the inbuilt loop function
        Args:
            repeats(int):  Number of loops
            start(int) :    Start location
            finish(int):    End location
            velocity(int):  Stepper veolocity
            acceleration(int):  Stepper acceleration
            '''
        self.write("A"+str(acceleration))
        self.write("V"+str(velocity))
        self.write("L"+str(repeats))
        self.moveto(start)
        self.moveto(finish)
        self.write("N")
    def location(self):
        '''Determine the current stepper position in picoseconds and steps
        Returns:
            stepper position picoseconds
            stepper position steps
            '''
        Success = False
        while Success ==False:
            try:
                loc = [old_div(self.int_query("8PR"),(self.calibration)),self.int_query("8PR")]
                if loc != [old_div(self.int_query("8PR"),(self.calibration)),self.int_query("8PR")]:
                    raise ValueError
                Success = True
            except ValueError:
                Success = False
        return loc
        

    def movepositive(self):
        '''Move continuesly positive until a stop command is recieved '''
        self.write("MC")
        self.write("H+")
        self.write("G")

    def movenegative(self):
        '''Move continuesly negative until a stop command is recieved '''
        self.write("MC")
        self.write("H-")
        self.write("G")

    def stop(self):
        '''Force the stepper to stop in its current position '''
        self.write("S")
    
    def home(self, velocity = -3): 
        '''Move the stepper to its home position
        Args:
            velocity(int):  Stepper velocity
        Notes:
            The correct sign (+/-) for the velocity for home movement must be 
            given otherwise the stepper will go to the wrong end of the stage'''
        self.write("GH"+str(velocity))
    
    def zero(self): 
        '''Set the current stepper position as zero '''
        self.write("PZ")

    def get_qt_ui(self):
        if not hasattr(self,'ui'):
            self.ui = Stepper_Ui(self)
        return self.ui
 #       'New code starts here
from nplab.utils.gui import QtCore, QtGui, QtWidgets, uic
from nplab.ui.ui_tools import UiTools
import os

class Stepper_Ui(QtWidgets.QWidget, UiTools):
    def __init__(self,stepper):
        super(Stepper_Ui, self).__init__()
      #  assert(stepper==Stepper) # checking if the object is a stepper
        self.stepper = stepper
        ui_file = os.path.join(os.path.dirname(__file__),'stepper_GUI.ui') # GUI path . e.g. look into location of the current file and search for the given name
        uic.loadUi(ui_file, self) #loading the ui file 
        
        self.move_spinBox.setMaximum(int(self.stepper.max_steps))
        self.move_percent_doubleSpinBox.setMaximum(100.0)
        
        self.current_button.clicked.connect(self.update_positions)
        
        self.setpercent_pushButton.clicked.connect(self.move_to_percent)
        self.setsteps_pushButton.clicked.connect(self.move_to)
        self.update_positions()
    def update_positions(self):
        current_pos = float(self.stepper.location()[1])
        self.current_number.setText(str(current_pos))
        self.current_percent.setText(str(old_div(100.0*current_pos,self.stepper.max_steps))[:4]+'%')
    
    def move_to_percent(self):
        percent=self.move_percent_doubleSpinBox.value()
        steps=int(old_div((percent*self.stepper.max_steps),100))
        self.stepper.moveto(steps,blocking = False)
        
    def move_to(self):
        steps= self.move_spinBox.value()
        self.stepper.moveto(steps)
    
    
    
    	
		
#		self.current_number=self.location()
	#	self.set_number=self.moveto(finish)
	#	set_button
