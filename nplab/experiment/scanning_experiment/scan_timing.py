from __future__ import print_function
from builtins import object
__author__ = 'alansanders'

import numpy as np


class TimedScan(object):
    def __init__(self):
        self._estimated_step_time = 0
        self.total_points = 0

    @property
    def estimated_step_time(self):
        return self._estimated_step_time

    @estimated_step_time.setter
    def estimated_step_time(self, value):
        self._estimated_step_time = value

    def estimate_scan_duration(self):
        """Estimate the duration of a grid scan."""
        estimated_time = self.total_points * self.estimated_step_time
        return self.format_time(estimated_time)

    def get_estimated_time_remaining(self):
        """Estimate the time remaining of the current scan."""
        if not hasattr(self, '_step_times'):
            return np.inf
        mask = np.isfinite(self._step_times)
        if not np.any(mask):
            return 0
        times = self._step_times[mask].flatten()
        average_step_time = np.mean(np.diff(times))
        etr = (self.total_points - self._index) * average_step_time  # remaining steps = self.total_points - index
        return etr

    def format_time(self, t):
        """Formats the time in seconds into a string with convenient units."""
        if t < 120:
            return '{0:.1f} s'.format(t)
        elif (t >= 120) and (t < 3600):
            return '{0:.1f} mins'.format(t / 60.)
        elif t >= 3600:
            return '{0:.1f} hours'.format(t / 3600.)
        else:
            return 'You should probably not be running this scan!'

    def get_formatted_estimated_time_remaining(self):
        """Returns a string of convenient units for the estimated time remaining."""
        if self.acquisition_thread.is_alive():
            etr = self.get_estimated_time_remaining()
            return self.format_time(etr)
        else:
            return 'inactive'

    def print_scan_time(self, t):
        """Prints the duration of the scan."""
        print('Scan took', self.format_time(t))