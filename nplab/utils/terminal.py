from qtconsole.rich_jupyter_widget import RichJupyterWidget
from qtconsole.inprocess import QtInProcessKernelManager
# from IPython.qt.console.rich_ipython_widget import RichIPythonWidget
# from IPython.qt.inprocess import QtInProcessKernelManager
from nplab.utils.gui import QtCore
import sys

class ipython:
    def __init__(self):
        self.kernel_manager = QtInProcessKernelManager()
        self.kernel_manager.start_kernel()
        self.kernel = self.kernel_manager.kernel
        sys.stdout = self.kernel.stdout
        sys.stderr = self.kernel.stderr
          
       
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
        #self.execute('clear')
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
        return self.control.execute('run -i scripts/%s' %scriptname)
