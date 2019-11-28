"""
The base scanning experiment classes are found in this file, supporting the basic functionality
of scanning experiments and adding supporting for utilising HDF5 files for data storage.
"""
from __future__ import print_function
__author__ = 'alansanders'

from nplab.experiment.experiment import ExperimentWithDataDeque
from threading import Thread
import time
from nplab import datafile


class ScanningExperiment(ExperimentWithDataDeque):
    """
    This class defines the core methods required for a threaded scanning experiment.
    """
    def __init__(self):
        super(ScanningExperiment, self).__init__()
        self.status = 'inactive'
        self.abort_requested = False
        self.acquisition_thread = None

    def run(self):
        """
        Starts the scan in its own thread.

        :return:
        """
        if isinstance(self.acquisition_thread, Thread) and self.acquisition_thread.is_alive():
            print('scan already running')
            return
        self.init_scan()
        self.acquisition_thread = Thread(target=self.scan, args=())
        self.acquisition_thread.start()
        
    def abort(self):
        """Requests an abort of the currently running grid scan."""
        if not hasattr(self, 'acquisition_thread'):
            return
        if self.acquisition_thread.is_alive():
            print('aborting')
            self.abort_requested = True
            self.acquisition_thread.join()
            
    def init_scan(self):
        """
        This is called before the experiment enters its own thread. Methods that should be
        executed in the main thread should be called here (e.g. graphing).

        :return:
        """
        pass

    def open_scan(self):
        """
        This is called after the experiment enters its own thread to setup the scan. Methods
        that should be executed in line with the experiment should be called here (e.g. data
        storage).

        :return:
        """
        pass

    def scan_function(self, index):
        """Applied at each position in the grid scan."""
        raise NotImplementedError
    
    def _timed_scan_function(self, index):
        """
        Supplementary function that can be used

        :param indices:
        :return:
        """
        t0 = time.time()
        self.scan_function(index)
        dt = time.time() - t0
        self._step_times[index] = dt  # TODO: check initialisation of this
        
    def scan(self):
        raise NotImplementedError
        
    def analyse_scan(self):
        """
        This is called before the scan is closed to perform any final calculations.
        :return:
        """
        pass

    def close_scan(self):
        """
        Closes the scan whilst still in the experiment thread.

        :return:
        """
        self.update(force=True)
        
    def update(self, force=False):
        """
        This is the function that is called in the event loop and at the end of the scan
        and should be reimplemented when subclassing to deal with data updates and GUIs.
        """
        pass


class ScanningExperimentHDF5(ScanningExperiment):
    """
    This class adds HDF5 file functionality for recording scans in a standardised manner.
    """
    def __init__(self):
        super(ScanningExperimentHDF5, self).__init__()
        self.f = datafile.current()
        self.data = None
        self.description = ''

    def __del__(self):
        if isinstance(self.f, datafile.DataFile):
            self.f.close()