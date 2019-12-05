# -*- coding: utf-8 -*-

from __future__ import print_function
from builtins import object
from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager
# from IPython.qt.console.rich_ipython_widget import RichIPythonWidget
# from IPython.qt.inprocess import QtInProcessKernelManager
from nplab.utils.gui import QtCore
import sys
import os
from IPython.lib import guisupport


class Ipython(object):
    def __init__(self, scripts_path=''):
        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel()
        self.kernel = self.kernel_manager.kernel
        sys.stdout = self.kernel.stdout
        sys.stderr = self.kernel.stderr

        self.scripts_path = scripts_path
        self.kernel.gui = 'qt4'

        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()

        self.control = RichJupyterWidget()
        self.control.kernel_manager = self.kernel_manager
        self.control.kernel_client = self.kernel_client
        self.control.exit_requested.connect(self.stop)

        self.control.setWindowTitle("IPython shell")

        self.execute('import numpy as np')
        self.execute('from matplotlib import pyplot as plt')
        self.execute('%matplotlib')
        self.execute('')

    def __del__(self):
        self.stop()
        self.close()

    def show(self):
        self.control.show()

        self.control.setWindowState(
            self.control.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)
        self.control.activateWindow()

    def stop(self):
        self.kernel_client.stop_channels()
        self.kernel_manager.shutdown_kernel()

    def close(self):
        self.control.close()

    def push(self, vardic):
        self.kernel.shell.push(vardic)

    def execute(self, cmd):
        self.control.execute(cmd)

    def run_script(self, scriptname):
        scriptpath = os.path.join(self.scripts_path, scriptname)
        return self.control.execute('run -i %s' % scriptpath)


class QIPythonWidget(RichJupyterWidget):
    """
    Convenience class for a live IPython console widget. We can replace the standard banner using the customBanner
    argument. Modified from https://stackoverflow.com/questions/11513132/embedding-ipython-qt-console-in-a-pyqt-application
    """

    def __init__(self, custom_banner=None, scripts_path='', *args, **kwargs):
        if custom_banner is not None:
            self.banner = custom_banner
        self.scripts_path = scripts_path
        super(QIPythonWidget, self).__init__(*args, **kwargs)
        self.kernel_manager = kernel_manager = QtInProcessKernelManager()
        kernel_manager.start_kernel()
        kernel_manager.kernel.gui = 'qt'
        self.kernel_client = kernel_client = self._kernel_manager.client()
        kernel_client.start_channels()
        self.kernel = self.kernel_manager.kernel
        sys.stdout = self.kernel.stdout
        sys.stderr = self.kernel.stderr

        def stop():
            kernel_client.stop_channels()
            kernel_manager.shutdown_kernel()
            guisupport.get_app_qt4().exit()

        self.exit_requested.connect(stop)

        self.execute_command("import numpy as np")
        self.execute_command("from matplotlib import pyplot as plt")
        self.execute_command("%matplotlib")

    def push_vars(self, variable_dict):
        """ Given a dictionary containing name / value pairs, push those variables to the IPython console widget """
        self.kernel_manager.kernel.shell.push(variable_dict)

    def clear(self):
        """ Clears the terminal """
        self._control.clear()

    def print_text(self, text):
        """ Prints some plain text to the console """
        self._append_plain_text(text)

    def execute_command(self, command):
        """ Execute a command in the frame of the console widget """
        self._execute(command, False)

    def run_script(self, scriptname):
        try:
            scriptpath = os.path.join(self.scripts_path, scriptname)
            self._execute('run -i %s' % scriptpath, False)
        except Exception as e:
            print('Failed because ', e)

