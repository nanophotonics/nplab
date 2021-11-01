# -*- coding: utf-8 -*-
"""
Created on Mon Mar  8 18:08:38 2021

@author: Eoin
"""
from nplab.instrument import Instrument
from nplab.utils.notified_property import (DumbNotifiedProperty,  # ##
                                           NotifiedProperty)


### = changed
class GradStudent(Instrument):
    angry = DumbNotifiedProperty(False) ###
    catchphrase = DumbNotifiedProperty("This is fine") ###
    
    def __init__(self):
        super().__init__()
        self._logger.info(f'Initializing {self.__class__}')
        self._beers = 0
        
    def get_beers(self):
        print(f"I've had {self._beers} beers")
        return self._beers
    
    def set_beers(self, new_value):
        if new_value > self._beers:
            print(f'drinking {new_value - self._beers} more beers')
        if new_value < self._beers:
            print(f'drinking {self._beers - new_value} coffees')
        self._beers = new_value
        
    beers = NotifiedProperty(get_beers, set_beers) ###
    
    def speak(self):
        if self.angry:
            print(self.catchphrase.upper()) # upper case
        else:
            print(self.catchphrase)
        print(self._beers*'hic...  ')
        
    def get_qt_ui(self):
        return GradStudentUI(self)

student = GradStudent()

#%%    
import os

from nplab.utils.gui import QtWidgets, uic
from nplab.utils.notified_property import register_for_property_changes  # ##


class GradStudentUI(QtWidgets.QWidget): 
    def __init__(self, student):
        super().__init__()
        uic.loadUi(os.path.dirname(__file__) + '\\' + 'grad_student.ui', self)
        self.student = student
        self.setup_signals()
        
    def setup_signals(self):
        self.angry_checkBox.clicked.connect(self.update_angry) 
        self.angry_checkBox.setChecked(self.student.angry)
        register_for_property_changes(self.student, ### object to control
                                      'angry', # object's attribute
                                      self.angry_checkBox.setChecked) 
                                      # function to call when attribute changed
                                      # argument is new value
        
        self.catchphrase_lineEdit.textChanged.connect(self.update_catchphrase)
        self.catchphrase_lineEdit.setText(self.student.catchphrase)
        register_for_property_changes(self.student, ###
                                      'catchphrase',
                                      self.catchphrase_lineEdit.setText)
        
        self.beers_spinBox.valueChanged.connect(self.update_beers)
        self.beers_spinBox.setValue(self.student.beers)
        register_for_property_changes(self.student, ###
                                      'beers',
                                      self.beers_spinBox.setValue)
        
        self.speak_pushButton.clicked.connect(self.student.speak)
        
    def update_angry(self, new): 
        self.student.angry = new
        
    def update_catchphrase(self, new):
        self.student.catchphrase = new
        
    def update_beers(self, new):
        self.student.beers = new
    
if __name__ == '__main__':
    student = GradStudent()
    gui = student.show_gui(blocking=False)