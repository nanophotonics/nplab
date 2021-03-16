# -*- coding: utf-8 -*-
"""
Created on Mon Mar  8 18:08:38 2021

@author: Eoin
"""

from nplab.instrument import Instrument

class GradStudent(Instrument):
    angry = False
    catchphrase = "This is fine"
    
    def __init__(self):
        super().__init__()
        self._logger.info(f'Initializing {self.__class__}') 
             # critical > warning > info > debug
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
        
    beers = property(get_beers, set_beers)
    
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
# same as from PyQt5 import QtWidgets, uic

class GradStudentUI(QtWidgets.QWidget):
    def __init__(self, student):
        super().__init__()
        uic.loadUi(os.path.dirname(__file__) + '\\' + 'grad_student.ui', self)
        self.student = student
        self.setup_signals()
        
    def setup_signals(self):
        self.angry_checkBox.clicked.connect(self.update_angry) # signal
        self.angry_checkBox.setChecked(self.student.angry)
        
        self.catchphrase_lineEdit.textChanged.connect(self.update_catchphrase)
        self.catchphrase_lineEdit.setText(self.student.catchphrase)
        
        self.beers_spinBox.valueChanged.connect(self.update_beers)
        self.beers_spinBox.setValue(self.student.beers)
        
        self.speak_pushButton.clicked.connect(self.student.speak)
        
    def update_angry(self, new): # slot
        self.student.angry = new
        
    def update_catchphrase(self, new):
        self.student.catchphrase = new
        
    def update_beers(self, new):
        self.student.beers = new
        

if __name__ == '__main__':
    student = GradStudent()
    student.show_gui(blocking=False)