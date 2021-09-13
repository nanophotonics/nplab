# -*- coding: utf-8 -*-
"""
Created on Fri Mar  5 12:47:58 2021

@author: Hera
"""
from nplab.utils.gui import QtWidgets
from nplab.utils.thread_utils import background_action
from nplab.utils.array_with_attrs import ArrayWithAttrs
from nplab.instrument import Instrument
from itertools import zip_longest
import re
import winsound, random
import numpy as np

def squawk():
    for i in range(5):
        winsound.Beep(random.randrange(37,3500),random.randrange(70,750)) 
    return 'I did a thing'

class Rotators(QtWidgets.QWidget, Instrument):
    ''' takes a list of rotators (must have a move function, should be a subclass of Stage),
    and makes a simple gui for them. Enter a list of angles to turn to, and they will be
    iterated through according to the rules of itertools.zip_longest, and the payload 
    function called, and its results saved. payload should return the data to be saved. 
    allowed formats:
        A: 0, 10, 20
        B: 0, 45, 90
        C: 
            #will not move rotator c
        A: np.linspace(0, 360, 10)
        B: np.arange(0, 360, 10)
        C: 45
        # will set C to 45 deg, B will continue moving and taking measurements 
        # after A runs out
        '''
    def __init__(self, rotators, payload=squawk):
        QtWidgets.QWidget.__init__(self)
        Instrument.__init__(self)
        self.rotators = rotators
        self.payload = payload
        
        self.edits = {r: [] for r in rotators}
        
        lines_widget = QtWidgets.QWidget()
        lines_layout = QtWidgets.QFormLayout()
        
        for label, r in rotators.items():
            l = QtWidgets.QLabel(label)
            self.edits[label] = (t := QtWidgets.QLineEdit())
            t.editingFinished.connect(self.textChanged)
            lines_layout.addRow(l, t)  
        lines_widget.setLayout(lines_layout)
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(lines_widget)
        self.run_pushButton = QtWidgets.QPushButton('Run')
        self.run_pushButton.clicked.connect(self.run)
        layout.addWidget(self.run_pushButton)
        self.setLayout(layout)

    def textChanged(self):
       self.angles = {r: self.parse_edit(self.edits[r]) for r in self.rotators}
       
    @staticmethod
    def parse_edit(edit):
        text = edit.text()
        if text:
            if text.startswith('np.'):
                return eval(text.strip()).tolist()
            split = (s for s in re.split(r',| |;', text) if s)
            return list(map(float, split))
        else:
            return []
        
    @background_action
    def run(self, checked):
        zipped_angles = zip_longest(*self.angles.values(), fillvalue=None)
        rotators = [self.rotators[key] for key in self.angles]
        for angles in (zipped_angles):
            for r, a in zip(rotators, angles):
                if a is not None:
                    r.move(a)
            data = ArrayWithAttrs(self.payload())
            data.attrs.update({l: r.position for l, r in self.rotators.items()})
            self.create_dataset('rotator_data_%d', data=data)
  
    def get_qt_ui(self):
         return self
if __name__ == '__main__':
    from nplab.instrument.stage.Thorlabs_ELL8K import Thorlabs_ELL8K, BusDistributor
    bus = BusDistributor('COM6')
    ells = {l: Thorlabs_ELL8K(bus, l) for l in 'ABC'}
    rotators = Rotators(ells)
    rotators.show_gui()
