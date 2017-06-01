import gc
import os
import re
import inspect
import numpy as np

import h5py
import pyqtgraph
import pyqtgraph.dockarea
from pyqtgraph.graphicsItems.GradientEditorItem import Gradients

from nplab.utils.gui import QtWidgets, QtGui, uic, QtCore
from nplab.utils.terminal import ipython
from nplab.ui.ui_tools import UiTools
import nplab.datafile as df
from nplab.utils.log import create_logger, ColoredFormatter
#from Experiments import settings
#from Experiments.exper_utils import GeneralScan
#from Experiments.exper_utils.h5browser import H5Browser
#from Experiments.exper_utils.workerthreads import *

#pyqtgraph.setConfigOption('leftButtonPan', False)


import logging
LOGGER = create_logger('GeneratedGUI')

class GuiGenerator(QtWidgets.QMainWindow,UiTools):
    def __init__(self, instrument_dict, parent=None, dock_settings_path = None, scripts_path = None,working_directory = None):
        super(GuiGenerator, self).__init__(parent)
        self._logger = LOGGER
        self.instr_dict = instrument_dict
        self.data_file = df.current(working_directory=working_directory)
        self.instr_dict['HDF5'] = self.data_file
        self.setDockNestingEnabled(1)
        
        

        uic.loadUi(os.path.join(os.path.dirname(__file__), 'guigenerator.ui'), self)

        self.allDocks = {}
        self.allWidgets = {}
        self.actions = dict(Views={}, Instruments={})
        
        self.dockwidgetArea = pyqtgraph.dockarea.DockArea()
        self.dockWidgetArea = self.replace_widget(self.verticalLayout, self.centralWidget(),self.dockwidgetArea)
        self.dockWidgetAllInstruments.setWidget(self.dockwidgetArea)
        self.dockWidgetAllInstruments.setTitleBarWidget(QtWidgets.QWidget())  # This trick makes the title bar disappear
                               
        # Iterate over all the opened instruments. If the instrument has a GUI (i.e. if they have the get_qt_ui function
        # defined inside them), then create a pyqtgraph.Dock for it and add its widget to the Dock. Also prints out any
        # instruments that do not have GUIs
        self._logger.info('Opening all GUIs')
        if working_directory==None:
            self.working_directory = os.path.join(os.getcwd())
        else:
            self.working_directory = working_directory
        for instr in self.instr_dict:
            self._open_one_gui(instr)

        self.terminalWindow = None
        self.menuTerminal()
        self._addActionViewMenu('Terminal')
        
        self.script_menu = None
        if scripts_path is not None:
            self.scripts_path = scripts_path
        else:
            self.scripts_path = 'scripts'
        self.makeScriptMenu()

        self.NightMode = 1

        # address of h5 file
        self.filename = df.current().filename

#        self._tabifyAll()
        self._setupSignals()
        if dock_settings_path is not None:
            self.dock_settings_path = dock_settings_path
            self.menuLoadSettings()
        else:
            self.dock_settings_path = None      
        self.showMaximized()
        

    def __getattribute__(self, name):  # All instruments log function and method calls at debugging level

        returned = QtCore.QObject.__getattribute__(self, name)
        if inspect.isfunction(returned) or inspect.ismethod(returned):
            codeline = inspect.getsourcelines(returned)[1]
            filename = inspect.getfile(returned)
            self._logger.debug('Called %s on line %g of %s' %(returned.__name__, codeline, filename))
        return returned

    def _open_one_gui(self, instrument_name):
        if hasattr(self.instr_dict[instrument_name],'get_control_widget') or hasattr(self.instr_dict[instrument_name],'get_preview_widget'):
            if hasattr(self.instr_dict[instrument_name],'get_control_widget'):
                self.allWidgets[instrument_name+' controls'] = self.instr_dict[instrument_name].get_control_widget()
                self.allDocks[instrument_name+' controls'] = pyqtgraph.dockarea.Dock(instrument_name+' controls')
                self.dockwidgetArea.addDock(self.allDocks[instrument_name+' controls'], 'left')
                self.allDocks[instrument_name+' controls'].addWidget(self.allWidgets[instrument_name+' controls'])
                self._addActionViewMenu(instrument_name+' controls')
            if hasattr(self.instr_dict[instrument_name],'get_preview_widget'):
                self.allWidgets[instrument_name+' display'] = self.instr_dict[instrument_name].get_preview_widget()
                self.allDocks[instrument_name+' display'] = pyqtgraph.dockarea.Dock(instrument_name+' display')
                self.dockwidgetArea.addDock(self.allDocks[instrument_name+' display'], 'left')
                self.allDocks[instrument_name+' display'].addWidget(self.allWidgets[instrument_name+' display'])
                self._addActionViewMenu(instrument_name+' display')
        elif hasattr(self.instr_dict[instrument_name],'get_qt_ui'):
            self.allWidgets[instrument_name] = self.instr_dict[instrument_name].get_qt_ui()
            self.allDocks[instrument_name] = pyqtgraph.dockarea.Dock(instrument_name)
            self.dockwidgetArea.addDock(self.allDocks[instrument_name], 'left')
            self.allDocks[instrument_name].addWidget(self.allWidgets[instrument_name])
            self._addActionViewMenu(instrument_name)
        else:
            self._logger.warn('%s does not have a get_qt_ui' %instr)


    def _addActionViewMenu(self, instr):
        if instr not in self.actions['Views']:
            action = QtWidgets.QAction(instr, self)
            self.menuView.addAction(action)
            action.setCheckable(True)
            action.setChecked(True)
            action.triggered.connect(lambda: self._toggleView(instr))
            self.actions['Views'][instr] = action

    def _toggleView(self, instr):
        if self.actions['Views'][instr].isChecked():
            self.allDocks[instr].show()
            self.dockwidgetArea.addDock(self.allDocks[instr], 'left')
        else:
            self.allDocks[instr].close()

    def _addActionInstrMenu(self, instr):
        if instr not in self.actions['Instruments']:
            action = QtWidgets.QAction(instr, self)
            self.menuInstr.addAction(action)
            action.setCheckable(True)
            action.setChecked(settings.addresses[instr]['use?'])
            action.triggered.connect(lambda: self._toggleInstr(instr))
            self.actions['Instruments'][instr] = action
    
    

#    def _toggleInstr(self, instr):
#
#        if self.actions['Instruments'][instr].isChecked():
#            if instr not in self.instr_dict.keys():
#                self.experiment.open_instrument_with_settings(instr)
#            if instr not in self.allDocks.keys():
#                self._open_one_gui(instr)
#            self.experiment.instr_dict[instr].updateGUI.emit()
#            self._addActionViewMenu(instr)
#            self._tabifyAll()
#        else:
#            if instr in self.allDocks:
#                self.allDocks[instr].close()
#                del self.allDocks[instr]
#                del self.allWidgets[instr]
#            self.menuView.removeAction(self.actions['Views'][instr])
#            del self.experiment.instr_dicc[instr]
#

    def _setupSignals(self):
        self.actionExit.triggered.connect(self.close)
        self.actionNightMode.triggered.connect(self.toggleNightMode)
        self.actionTerminal.triggered.connect(self.menuTerminal)
        self.actionShowBrowser.triggered.connect(self.toggle_browser)
        self.actionNewExperiment.triggered.connect(self.menuNewExperiment)
        self.actionSaveExperiment.triggered.connect(self.menuSaveExperiment)
        self.actionSaveSettings.triggered.connect(self.menuSaveSettings)
        self.actionRecallSettings.triggered.connect(self.menuLoadSettings)
        # For some reason the following does not work if put in a loop
        actions = self.menuVerbose.actions()
        actions[0].triggered.connect(lambda: self.VerboseChanged(actions[0]))
        actions[1].triggered.connect(lambda: self.VerboseChanged(actions[1]))
        actions[2].triggered.connect(lambda: self.VerboseChanged(actions[2]))
    def toggle_browser(self):
        self.actions['Views']['HDF5'].toggle()
        self._toggleView('HDF5')
    def toggleNightMode(self):
        try:
            if self.actionNightMode.isChecked():
                import qdarkstyle
                self.setStyleSheet(qdarkstyle.load_stylesheet(pyside=False))
            else:
                self.setStyleSheet('')
        except Exception as e:
            print e
            print 'trying Qt 5'
            try:
                if self.actionNightMode.isChecked():
                    import qdarkstyle
                    self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
                else:
                    self.setStyleSheet('')
            except Exception as ee:
                print ee
                print 'Qt 5 style sheet failed'
    def menuSaveSettings(self):
        dock_state = self.dockWidgetArea.saveState()
        if self.dock_settings_path==None:
            import nplab.utils.gui
            from nplab.utils.gui import QtGui,QtWidgets
            app = nplab.utils.gui.get_qt_app()  # ensure Qt is running
            self.dock_settings_path = QtWidgets.QFileDialog.getSaveFileName(
                caption="Create new dock settings file",
                directory=self.working_directory,
    #            options=qtgui.QFileDialog.DontConfirmOverwrite,
            )


        np.save(self.dock_settings_path[0],dock_state)

        
    def menuLoadSettings(self):
        if self.dock_settings_path==None:
            import nplab.utils.gui
            from nplab.utils.gui import QtGui,QtWidgets
            app = nplab.utils.gui.get_qt_app()  # ensure Qt is running
            self.dock_settings_path = QtWidgets.QFileDialog.getOpenFileName(
                caption="Select Existing Data File",
                directory=self.working_directory,
    #            options=qtgui.QFileDialog.DontConfirmOverwrite,
            )[0]        
        try:
            loaded_state = np.load(self.dock_settings_path)
            loaded_state=loaded_state[()]
            self.dockWidgetArea.restoreState(loaded_state)
        except:
            self._logger.warn(
            'The dock_settings file does not exist! or it is for the wrong docks!')

    def menuNewExperiment(self):
        dock_state = self.dockWidgetArea.saveState()
        self.toggle_browser()
        self.data_file = df.current()
        self.instr_dict['HDF5'] = self.data_file
        self._open_one_gui('HDF5')
        self.dockWidgetArea.restoreState(dock_state)
#
    def menuSaveExperiment(self):
        self.data_file.flush()

    def menuCloseExperiment(self):
        self.data_file.close()
        self.allWidgets['HDF5'].treeWidget.model.refresh_tree()

    def menuTerminal(self):
        from nplab.utils import terminal

        if self.terminalWindow is None:
            self.terminalWindow = terminal.ipython()
            self.terminalWindow.push({'gui': self, 'exper': self.instr_dict})
            self.terminalWindow.push(self.instr_dict)
            formatter = ColoredFormatter('[%(name)s] - %(levelname)s: %(message)s - %(asctime)s ', '%H:%M')
            handle = logging.StreamHandler(self.terminalWindow.kernel.stdout)
            handle.setFormatter(formatter)
            self._logger.addHandler(handle)
            instr_logger = logging.getLogger('Instrument')
            instr_logger.addHandler(handle)

            self.allDocks['Terminal'] = pyqtgraph.dockarea.Dock('Terminal')
            self.allWidgets['Terminal'] = self.terminalWindow.control
            self.dockwidgetArea.addDock(self.allDocks['Terminal'], 'left')
            self.allDocks['Terminal'].addWidget(self.allWidgets['Terminal'])
        else:
            self.actions['Views']['Terminal'].toggle()
            self._toggleView('Terminal')

    '''Script menu'''

    def makeScriptMenu(self):
        from functools import partial

        if self.script_menu is None:
            script_menu = self.menuBar().addMenu('&Scripts')
        else:
            script_menu = self.script_menu

        menus = {self.scripts_path: script_menu}

        for dirpath, dirnames, filenames in os.walk(self.scripts_path):
            # print filenames
            current = menus[dirpath]
            for dn in dirnames:
                menus[os.path.join(dirpath, dn)] = current.addMenu(dn)
            for fn in filenames:
                if fn != '__init__.py':
                    menuitem = current.addAction(fn)
                    menuitem.triggered.connect(partial(self.menuScriptClicked, fn))

        script_menu.addSeparator()
        refreshScripts = script_menu.addAction('Refresh')
        refreshScripts.triggered.connect(self.refreshScriptMenu)
        self.script_menu = script_menu

    def refreshScriptMenu(self):
        self.script_menu.clear()
        self.makeScriptMenu()

    def menuScriptClicked(self, scriptname):
        if self.terminalWindow is None:
            self.menuTerminal()

        self.terminalWindow.run_script(scriptname)

    def VerboseChanged(self, action):
        instr_logger = logging.getLogger('Instrument')
        if action.isChecked():
            self._logger.setLevel(action.text().upper())
            instr_logger.setLevel(action.text().upper())
            for action2 in self.menuVerbose.actions():
                if action2.text() != action.text():
                    action2.setChecked(False)
        else:
            self.menuVerbose.actions()[1].setChecked(True)
            instr_logger.setLevel('INFO')
            self._logger.setLevel('INFO')

    def closeEvent(self, event):
        quit_msg = "Are you sure you want to exit the program?"
        reply = QtWidgets.QMessageBox.question(self, 'Message', quit_msg,
                                               QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.Save, QtWidgets.QMessageBox.No)

        if reply != QtWidgets.QMessageBox.No:
            if reply == QtWidgets.QMessageBox.Save:
                self.experiment.save_load_all_settings()
#            self.experiment.isLive = 0

#            if self.experiment.ExpFile is not None:
#                self.experiment.ExpFile.flush()
#                self.experiment.ExpFile.close()
#            self.experiment.__del__()
            event.accept()
        else:
            event.ignore()
