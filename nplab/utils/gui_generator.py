from __future__ import print_function
from nplab.utils.gui import QtWidgets, uic, QtCore
from nplab.ui.ui_tools import UiTools
import nplab.datafile as df
from nplab.utils.log import create_logger, ColoredFormatter

import os
import sys
import inspect
import numpy as np

import pyqtgraph
import pyqtgraph.dockarea

import logging

LOGGER = create_logger('GeneratedGUI')


class GuiGenerator(QtWidgets.QMainWindow, UiTools):
    """A object for generating a main gui through stitching together multiple guis 
    by the generation of dock widgets, this allow the user to create a save a custom
    gui without all of the hard work
    """

    def __init__(self, instrument_dict, parent=None, dock_settings_path=None,
                 scripts_path=None, working_directory=None, file_path=None, terminal = False):  #
        """Args:
            instrument_dict(dict) :     This is a dictionary containing the
                                        instruments objects where the key is the 
                                        objects new name in the generated new Ipython 
                                        console
            dock_settings_path(str):    A path for loading a previous dock widget
                                        configuration
            scripts_path(str):          The path of any scripts the user may want to
                                        run using the drop down menu at the top
                                        of the gui
            working_directory(str):     A path to the requested working directory - 
                                        handy if you always wish to save data to 
                                        the same directories
            file_path(str):             A path to the file for saving data. If None,
                                        a dialog will ask for one. Can be a relative
                                        path (from working_directory) or an absolute path
            terminal(bool):             Specifies whether the generated gui has an ipython 
                                        console. Sripts ran in an ipython console cannot 
                                        generate another one.
                                """
        super(GuiGenerator, self).__init__(parent)
        self._logger = LOGGER
        self.instr_dict = instrument_dict
        if working_directory is None:
            self.working_directory = os.path.join(os.getcwd())
        else:
            self.working_directory = working_directory
        if file_path is None:
            self.data_file = df.current(working_directory=working_directory)
        elif os.path.isabs(file_path):
            df.set_current(file_path)
            self.data_file = df.current()
        else:
            df.set_current(self.working_directory + '/' + file_path)
            self.data_file = df.current()

        self.instr_dict["HDF5"] = self.data_file
        self.setDockNestingEnabled(1)

        uic.loadUi(os.path.join(os.path.dirname(__file__), 'guigenerator.ui'), self)

        self.allDocks = {}
        self.allWidgets = {}
        self.actions = dict(Views={}, Instruments={})

        self.dockwidgetArea = pyqtgraph.dockarea.DockArea()
        self.dockWidgetArea = self.replace_widget(self.verticalLayout, self.centralWidget(), self.dockwidgetArea)
        self.dockWidgetAllInstruments.setWidget(self.dockwidgetArea)
        self.dockWidgetAllInstruments.setTitleBarWidget(QtWidgets.QWidget())  # This trick makes the title bar disappear

        # Iterate over all the opened instruments. If the instrument has a GUI (i.e. if they have the get_qt_ui function
        # defined inside them), then create a pyqtgraph.Dock for it and add its widget to the Dock. Also prints out any
        # instruments that do not have GUIs
        self._logger.info('Opening all GUIs')

        for instr in self.instr_dict:
            self._open_one_gui(instr)
            
        self.script_menu = None
        if scripts_path is not None:
            self.scripts_path = scripts_path
        else:
            self.scripts_path = 'scripts'
        sys.path.append(self.scripts_path)
        self.terminalWindow = None
        self.terminal = terminal
        if terminal:
            self.menuTerminal()
            self._addActionViewMenu('Terminal')
        self.makeScriptMenu()

        self.NightMode = 1

        # address of h5 file
        self.filename = df.current().filename

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
            self._logger.debug('Called %s on line %g of %s' % (returned.__name__, codeline, filename))
        return returned

    def _open_one_gui(self, instrument_name):
        """A command for opening a single Instruemnt guiand creating a dock through acquiring the 
        get_qt_ui function for a single panel or if invidual control and preview widgets
        are possible then the get_control_widget and get_preview_widgets will be sed
        """
        if hasattr(self.instr_dict[instrument_name], 'get_control_widget') or hasattr(self.instr_dict[instrument_name],
                                                                                      'get_preview_widget'):
            if hasattr(self.instr_dict[instrument_name], 'get_control_widget'):
                self.allWidgets[instrument_name + ' controls'] = self.instr_dict[instrument_name].get_control_widget()
                self.allDocks[instrument_name + ' controls'] = pyqtgraph.dockarea.Dock(instrument_name + ' controls')
                self.dockwidgetArea.addDock(self.allDocks[instrument_name + ' controls'], 'left')
                self.allDocks[instrument_name + ' controls'].addWidget(self.allWidgets[instrument_name + ' controls'])
                self._addActionViewMenu(instrument_name + ' controls')
            if hasattr(self.instr_dict[instrument_name], 'get_preview_widget'):
                self.allWidgets[instrument_name + ' display'] = self.instr_dict[instrument_name].get_preview_widget()
                self.allDocks[instrument_name + ' display'] = pyqtgraph.dockarea.Dock(instrument_name + ' display')
                self.dockwidgetArea.addDock(self.allDocks[instrument_name + ' display'], 'left')
                self.allDocks[instrument_name + ' display'].addWidget(self.allWidgets[instrument_name + ' display'])
                self._addActionViewMenu(instrument_name + ' display')
        elif hasattr(self.instr_dict[instrument_name], 'get_qt_ui'):
            self.allWidgets[instrument_name] = self.instr_dict[instrument_name].get_qt_ui()
            self.allDocks[instrument_name] = pyqtgraph.dockarea.Dock(instrument_name)
            self.dockwidgetArea.addDock(self.allDocks[instrument_name], 'left')
            self.allDocks[instrument_name].addWidget(self.allWidgets[instrument_name])
            self._addActionViewMenu(instrument_name)
        else:
            self._logger.warn('%s does not have a get_qt_ui' % instrument_name)

    def _addActionViewMenu(self, instr):
        """Create the actions menu - such as enabled and disabling gui's on the fly """
        if instr not in self.actions['Views']:
            action = QtWidgets.QAction(instr, self)
            self.menuView.addAction(action)
            action.setCheckable(True)
            action.setChecked(True)
            action.triggered.connect(lambda: self._toggleView(instr))
            self.actions['Views'][instr] = action

    def _toggleView(self, instr):
        """A function for togalling a single gui """
        if self.actions['Views'][instr].isChecked():
            self.allDocks[instr].show()
            self.dockwidgetArea.addDock(self.allDocks[instr], 'left')
        else:
            self.allDocks[instr].close()

    def _setupSignals(self):
        """Connect signals for the different general gui buttons/menu's """
        self.actionExit.triggered.connect(self.close)
        self.actionNightMode.triggered.connect(self.toggleNightMode)
        self.actionTerminal.triggered.connect(self.menuTerminal)
        self.actionShowBrowser.triggered.connect(self.toggle_browser)
        self.actionNewExperiment.triggered.connect(self.menuNewExperiment)
        self.actionCloseExperiment.triggered.connect(self.menuCloseExperiment)
        self.actionSaveExperiment.triggered.connect(self.menuSaveExperiment)
        self.actionSaveSettings.triggered.connect(self.menuSaveSettings)
        self.actionRecallSettings.triggered.connect(self.menuLoadSettings)
        # For some reason the following does not work if put in a loop
        actions = self.menuVerbose.actions()
        actions[0].triggered.connect(lambda: self.VerboseChanged(actions[0]))
        actions[1].triggered.connect(lambda: self.VerboseChanged(actions[1]))
        actions[2].triggered.connect(lambda: self.VerboseChanged(actions[2]))

    def toggle_browser(self):
        """enable or disable the file browser """
        self.actions['Views']['HDF5'].toggle()
        self._toggleView('HDF5')

    def toggleNightMode(self):
        """A function to switch all the colors to night mode - handy when working in an optics lab """
        try:
            if self.actionNightMode.isChecked():
                import qdarkstyle
                self.setStyleSheet(qdarkstyle.load_stylesheet(pyside=False))
            else:
                self.setStyleSheet('')
        except Exception as e:
            print(e)
            print('trying Qt 5')
            try:
                if self.actionNightMode.isChecked():
                    import qdarkstyle
                    self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
                else:
                    self.setStyleSheet('')
            except Exception as ee:
                print(ee)
                print('Qt 5 style sheet failed')

    def menuSaveSettings(self):
        """A function for saving the current dock layout and settings to a numpy
        binary array file"""
        dock_state = self.dockWidgetArea.saveState()
        if self.dock_settings_path == None:
            import nplab.utils.gui
            from nplab.utils.gui import QtGui, QtWidgets
            #     app = nplab.utils.gui.get_qt_app()  # ensure Qt is running
            self.dock_settings_path = QtWidgets.QFileDialog.getSaveFileName(
                caption="Create new dock settings file",
                directory=self.working_directory,
                #            options=qtgui.QFileDialog.DontConfirmOverwrite,
            )[0]

        np.save(self.dock_settings_path, dock_state)

    def menuLoadSettings(self):
        """A function for loading the current dock layout and settings to a numpy
        binary array file"""
        if self.dock_settings_path == None:
            import nplab.utils.gui
            from nplab.utils.gui import QtGui, QtWidgets
            #          app = nplab.utils.gui.get_qt_app()  # ensure Qt is running
            self.dock_settings_path = QtWidgets.QFileDialog.getOpenFileName(
                caption="Select Existing Data File",
                directory=self.working_directory,
            )[0]
        try:
            loaded_state = np.load(self.dock_settings_path, allow_pickle=True)
            loaded_state = loaded_state[()]
            self.dockWidgetArea.restoreState(loaded_state)
        except Exception as e:
            self._logger.debug(e)
            self._logger.warn(
                'The dock_settings file does not exist! or it is for the wrong docks!')

    def menuNewExperiment(self):
        """A start new experiement button casuing the gui to close ask for a new file
            and reopen"""
        dock_state = self.dockWidgetArea.saveState()
        self.toggle_browser()
        self.data_file.flush()
        self.data_file.close()
        self.data_file = df.current(working_directory=self.working_directory)
        self.instr_dict['HDF5'] = self.data_file
        self._open_one_gui('HDF5')
        self.dockWidgetArea.restoreState(dock_state)


    def menuSaveExperiment(self):
        """push to data to hard drive """
        self.data_file.flush()

    def menuCloseExperiment(self):
        """Close the current data_file """
        try:
            self.data_file.flush()
            self.data_file.close()
            self.allWidgets['HDF5'].treeWidget.model.refresh_tree()
        except Exception as e:
            self._logger.info("You likely tried closing a closed file: %s" % e)

    def menuTerminal(self):
        """ Create an ipython console for use within the experiment and push
        all the equipment to it with the requested names
        """
        from nplab.utils import terminal
        if self.terminalWindow is None:
            if os.environ["QT_API"] == "pyqt5":
                self.terminalWindow = terminal.QIPythonWidget(scripts_path=self.scripts_path)
                self.terminalWindow.push_vars({'gui': self, 'exper': self.instr_dict})
                self.terminalWindow.push_vars(self.instr_dict)
                self.terminalWindow.execute_command('import nplab.datafile as df')
                self.terminalWindow.execute_command('')
                handle = logging.StreamHandler(self.terminalWindow.kernel_manager.kernel.stdout)
            else:
                self.terminalWindow = terminal.Ipython()
                self.terminalWindow.push({'gui': self, 'exper': self.instr_dict})
                self.terminalWindow.push(self.instr_dict)
                self.terminalWindow.execute('import nplab.datafile as df')
                self.terminalWindow.execute('data_file = df.current()')
                self.terminalWindow.execute('')
                handle = logging.StreamHandler(self.terminalWindow.kernel.stdout)
            formatter = ColoredFormatter('[%(name)s] - %(levelname)s: %(message)s - %(asctime)s ', '%H:%M')
            handle.setFormatter(formatter)
            self._logger.addHandler(handle)
            instr_logger = logging.getLogger('Instrument')
            instr_logger.addHandler(handle)

            self.allDocks['Terminal'] = pyqtgraph.dockarea.Dock('Terminal')
            if os.environ["QT_API"] == "pyqt5":
                self.allWidgets['Terminal'] = self.terminalWindow
            else:
                self.allWidgets['Terminal'] = self.terminalWindow.control
            self.dockwidgetArea.addDock(self.allDocks['Terminal'], 'left')
            self.allDocks['Terminal'].addWidget(self.allWidgets['Terminal'])
        else:
            self.actions['Views']['Terminal'].toggle()
            self._toggleView('Terminal')

    '''Script menu'''

    def makeScriptMenu(self):
        """Generate a menu for running the scripts found in the scripts path locationlocation """
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
                    menuitem.triggered.connect(partial(self.menuScriptClicked, '\\'.join((dirpath,fn))))

        script_menu.addSeparator()
        refreshScripts = script_menu.addAction('Refresh')
        refreshScripts.triggered.connect(self.refreshScriptMenu)
        self.script_menu = script_menu

    def refreshScriptMenu(self):
        """clear and recompile the scripts menu """
        self.script_menu.clear()
        self.makeScriptMenu()

    def menuScriptClicked(self, scriptname):
        """Runs the selected script """
        if self.terminal:
            if self.terminalWindow is None:
                self.menuTerminal()
                self.terminalWindow.run_script(scriptname)
        else: 
            print('Running',os.path.join(self.scripts_path, scriptname))
            exec(open(os.path.join(self.scripts_path, scriptname)).read())
            
    def VerboseChanged(self, action):
        """Automatically change the loggers 
        verbosity level across all instruments upon 
        request  """
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
        """A quick are you sure you want to quit function """
        quit_msg = "Are you sure you want to exit the program?"
        print(quit_msg)
        try:
            if os.environ["QT_API"] == "pyqt5":
                reply = QtWidgets.QMessageBox.question(self, 'Message', quit_msg,
                                                       QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Save | QtWidgets.QMessageBox.No)

            else:
                reply = QtWidgets.QMessageBox.question(self, 'Message', quit_msg,
                                                       QtWidgets.QMessageBox.Yes, QtWidgets.QMessageBox.Save,
                                                       QtWidgets.QMessageBox.No)

            if reply != QtWidgets.QMessageBox.No:
                if reply == QtWidgets.QMessageBox.Save:
                    self.menuSaveSettings()
                    # self.experiment.save_load_all_settings()
                #            self.experiment.isLive = 0

                #            if self.experiment.ExpFile is not None:
                #                self.experiment.ExpFile.flush()
                #                self.experiment.ExpFile.close()
                #            self.experiment.__del__()
                event.accept()
            else:
                event.ignore()
        except Exception as e:
            print(e)
