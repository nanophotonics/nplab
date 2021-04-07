# -*- coding: utf-8 -*-
"""
Created on Mon Mar  1 16:21:57 2021

@author: ee306
"""

from nplab.utils.gui import QtWidgets, uic
from nplab.ui.ui_tools import UiTools
from nplab.utils.notified_property import DumbNotifiedProperty, register_for_property_changes
from nplab import datafile
from nplab.utils.show_gui_mixin import ShowGUIMixin
import os 

class DataGroupCreator(QtWidgets.QWidget,UiTools, ShowGUIMixin):
    
    group_name = DumbNotifiedProperty('particle_%d')
    gui_current_group = DumbNotifiedProperty(None)
    use_created_group = DumbNotifiedProperty(False)
    
    def __init__(self, file=None):
        super().__init__()
        uic.loadUi(os.path.dirname(__file__)+'\data_group_creator.ui', self)
        if file is None:
            self.file = datafile.current()
        else:
            self.file = file
        self._use_created_group = False
        self.auto_connect_by_name()        
        register_for_property_changes(self, 'use_created_group', self.use_created_group_changed)
        
    def create_group(self):
        init_use_cur = datafile._use_current_group
        datafile._use_current_group = False
        self.gui_current_group = self.file.create_group(self.group_name)
        if self.use_created_group_checkBox.checkState(): 
            datafile._current_group = self.gui_current_group
        datafile._use_current_group = init_use_cur
        
    def use_created_group_changed(self, new):
        datafile._use_current_group = new
        if new:
            if hasattr(self, 'gui_current_group'):
                datafile._current_group = self.gui_current_group
            else: print('No created group (yet)!')
            
    def add_note(self):
        note = self.note_textEdit.toPlainText()
        if note:
            if self.use_created_group:
                place = self.gui_current_group
            else:
                place = self.file
            place.create_dataset('note_%d', data=note, attrs={'is_note': True})
            
    def get_qt_ui(self):
        return self 
       
if __name__ == '__main__':
    l = DataGroupCreator()
    l.show_gui(False)
    datafile.current().show_gui(False)
    