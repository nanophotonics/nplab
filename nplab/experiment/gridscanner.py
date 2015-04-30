"""
Experiment classes for grid scanning experiments. The main classes are GridScanner,
AcquisitionThread and GridScanController. The AcquisitionThread takes the GridScanner,
which defines the scan, and runs its methods in a thread as called by the GridScanController,
which controls the overall experiment.
"""

__author__ = 'alansanders'

import os
import h5py
from traits.api import HasTraits, Instance, Button, Int, Array, List, Property, Float
from traits.api import Tuple, String, Enum, Dict, Bool, NO_COMPARE
from traitsui.api import View, Item, Group, HGroup, VGroup, spring
import numpy as np
from threading import Thread
from time import sleep, time
import operator
from nplab.instrument.stage import Stage


group_params = {'show_border': True, 'springy': False}


def grid_scanner_group():
    """
    This returns the default layout for the grid scanner group with all the
    control parameters.
    """
    group = Group(
        HGroup(Item('num_axes', width=-30),
               Item('axes', width=-100),
               label='Axes', **group_params),
        HGroup(Item('size', width=-35),
               Item('size_unit', width=-40, show_label=False),
               VGroup(Item('increase_size', width=-10, show_label=False),
                      Item('decrease_size', width=-10, show_label=False), ),
               Item('step', width=-35),
               Item('step_unit', width=-40, show_label=False),
               VGroup(Item('increase_step', width=-10, show_label=False),
                      Item('decrease_step', width=-10, show_label=False), ),
               Item('init', width=-50),
               label='Scan Parameters', **group_params),
        HGroup(Item('grid_shape', style='readonly'),
               Item('update_grid_button', show_label=False),
               **group_params),
        HGroup(Item('status', label='Status', style='readonly')),
        springy=False,
    )
    return group


class GridScanner(HasTraits):
    """
    Instances of grid_scanner are given to the GridScanControl class.
    grid_scanner objects comprise of a scanning stage and a scan function.
    The movement function should be supplied with the required axes and a
    move command. The scan function can be anything but must have the grid
    indices as its arguments.
    It is recommended to use the init_scan, open_scan, close_scan and
    cleanup methods. Open_scan is called first and it typically used to
    open communications to equipment. Init_scan is called after and is
    typically used to initialise data storage arrays. Close_scan is
    typically used to close equipment communications and Cleanup is called
    when the application is terminated.
    A unique grid_scanner subclass is written for each different scan
    overriding the functions.
    The save_data method is included to allow custom data models to be
    saved in the HDF5 format since the data is stored in the grid_scanner
    object rather than the GridScan object.
    
    Methods
    update: Updates any GUI associated with the grid_scanner.
    """

    num_axes = Int(3)
    axes = List()
    size = Array(np.float64, comparison_mode=NO_COMPARE)
    step = Array(np.float64, comparison_mode=NO_COMPARE)
    init = Array(np.float64, comparison_mode=NO_COMPARE)

    size_unit = Enum('um', 'nm', 'mm')
    step_unit = Enum('um', 'nm', 'mm')
    _unit_conversion = Dict({'nm': 1e-9, 'um': 1e-6, 'mm': 1e-3})

    increase_size = Button()
    decrease_size = Button()
    increase_step = Button()
    decrease_step = Button()

    scan_axes = List()
    grid_shape = Tuple

    update_grid_button = Button('Update Grid')
    scanner = Instance(Stage)
    indices = Tuple
    status = String
    acquiring = Bool(False)

    step_time = Float()
    scan_length_estimate = Property(depends_on=['grid_shape', 'step_time'])

    stage_units = Float(1)

    traits_view = View(grid_scanner_group())

    def __init__(self):
        super(GridScanner, self).__init__()
        self.scan_controller = None
        # set the scanner to be used and which axes to scan across
        # along with default positions
        self.scanner = Stage()
        self.num_axes = 3
        self.axes = ['a', 'b', 'c']
        self.size = np.array([2, 2, 1])
        self.step = np.array([0.1, 0.1, 0.2])
        self.init = np.array([0, 0, 0])
        self._step_time = 0.
        self.on_trait_change(self._update_params, 'num_axes')

    def _update_params(self):
        self.axes = [''] * self.num_axes

    def _init_grid(self, size, step, init):
        """
        Creates the grid and the grid (scan) axes from the scan parameters
        and the selected scan axes of the scanner. This does not create the
        data - only the axes of each dimension.
        """
        scan_axes = []
        for i in range(self.num_axes):
            s = size[i] * self._unit_conversion[self.size_unit]
            st = step[i] * self._unit_conversion[self.step_unit]
            ax = np.arange(init[i] - s / 2., init[i] + s / 2., st)
            scan_axes.append(ax)
        self.scan_axes = scan_axes
        self.grid_shape = tuple(ax.size for ax in self.scan_axes)

    def init_scan(self):
        self._init_grid(self.size, self.step, self.init)

    def move(self, ax, position):
        self.scanner.move_axis(position/self.stage_units, axis=ax)

    def get_position(self, ax):
        return self.scanner.get_position(axis=ax)*self.stage_units

    def scan_function(self, *indices):
        raise NotImplementedError("You must subclass scan_function to implement it for your own experiment")

    def open_scan(self):
        self.acquiring = True

    def close_scan(self):
        self.acquiring = False

    def analyse_scan(self):
        #raise NotImplementedError("You must subclass analyse_scan to implement it for your own experiment")
        pass

    def cleanup(self):
        #raise NotImplementedError("You must subclass cleanup to implement it for your own experiment")
        pass
    
    # Traits methods

    def _update_grid_button_fired(self):
        """
        Initialises the grid with the current parameters. This is mainly
        used to check what size grid is being used if size/speed is
        important to the scan.
        """
        self._init_grid(self.size, self.step, self.init)

    def _size_unit_changed(self, name, old, new):
        self.size *= self._unit_conversion[old] / self._unit_conversion[new]

    def _step_unit_changed(self, name, old, new):
        self.step *= self._unit_conversion[old] / self._unit_conversion[new]

    def _increase_size_fired(self):
        self.size *= 2

    def _decrease_size_fired(self):
        self.size /= 2

    def _increase_step_fired(self):
        self.step *= 2

    def _decrease_step_fired(self):
        self.step /= 2

    def update(self):
        raise NotImplementedError("You must subclass update to implement it for your own experiment")

    def set_init_to_current_position(self):
        for i, ax in enumerate(self.axes):
            self.init[i] = self.scanner.get_position(ax)*self.stage_units
        self.init = self.init

    def _get_scan_length_estimate(self):
        num_points = reduce(operator.mul, self.grid_shape, 1)  # could use lambda x,y: x*y for func
        estimated_time = num_points * self.step_time
        if estimated_time < 120:
            return '{0:.1f} s'.format(estimated_time)
        elif (estimated_time >= 120) and (estimated_time < 3600):
            return '{0:.1f} mins'.format(estimated_time/60.)
        elif estimated_time >= 3600:
            return '{0:.1f} hours'.format(estimated_time/3600.)


class AcquisitionThread(Thread):
    """
    Takes a grid_scanner object and scans out a grid, applying a function
    at each point. This function is ran in a separate thread to the main
    loop.
    """

    def __init__(self, grid_scanner):
        Thread.__init__(self)
        self.grid_scanner = grid_scanner
        self.abort_requested = False
        self.grid_scanner.init_scan()
        # for timing purposes
        self.timing_requested = False
        self.step_times = np.zeros(20)
        self.step_times[:] = np.nan
        self.total_points = reduce(operator.mul, self.grid_scanner.grid_shape, 1)  # could use lambda x,y: x*y for func
#        self.f = h5py.File(os.path.join(os.path.expanduser('~'), 'Desktop', 'timing.hdf5'), 'w')
#        self.s = self.f.create_dataset('timing', shape=self.grid_scanner.grid_shape + (2,), dtype=np.float64,
#                                       compression="gzip")
        self.current_step = 1

    def run(self):
        self.grid_scanner.open_scan()
        selected_axes = self.grid_scanner.axes
        scan_axes = self.grid_scanner.scan_axes  # list containing x,y,z arrays of positions to travel to
        # take the scan axes (positions) and turn them into indices to iterate over
        pnts = []
        for i in range(len(scan_axes)):
            pnts.append(range(scan_axes[i].size))

        st0 = time()
        for k in pnts[-1]:  # outer most axis
            if self.abort_requested:
                break
            self.grid_scanner._status = 'Scanning layer {0:d}/{1:d}'.format(k + 1, len(pnts[-1]))
            self.grid_scanner.move(selected_axes[-1], scan_axes[-1][k])
            pnts[-2] = pnts[-2][::-1]  # reverse which way is iterated over each time
            for j in pnts[-2]:
                if self.abort_requested:
                    break
                t0 = time()
                self.grid_scanner.move(selected_axes[-2], scan_axes[-2][j])
                if len(selected_axes) == 3:  # for 3d grid (volume) scans
                    pnts[-3] = pnts[-3][::-1]  # reverse which way is iterated over each time
                    for i in pnts[-3]:
                        if self.abort_requested:
                            break
                        t0 = time()
                        self.grid_scanner.move(selected_axes[-3], scan_axes[-3][i])
                        t1 = time()
                        self.grid_scanner.indices = (i, j, k)
                        self.grid_scanner.scan_function(i, j, k)
                        t2 = time()
                        self.update_time(t0, t1, t2)
                        self.current_step += 1
                elif len(selected_axes) == 2:  # for regular 2d grid scans ignore third axis i
                    t1 = time()
                    self.grid_scanner.indices = (j, k)
                    self.grid_scanner.scan_function(j, k)
                    t2 = time()
                    self.update_time(t0, t1, t2)
                    self.current_step += 1

        st1 = time()
        dt = st1 - st0
        print 'Scan took {0:.1f} s to run'.format(dt)
        # move back to initial positions
        for i in range(len(selected_axes)):
            self.grid_scanner.move(selected_axes[i], self.grid_scanner.init[i])
        self.grid_scanner.analyse_scan()
        self.grid_scanner.close_scan()
#        self.f.close()

    def update_time(self, *times):
        indices = self.grid_scanner.indices
        t0, t1, t2 = times
        dt1 = t1 - t0
        dt2 = t2 - t1
#        self.s[indices + (0,)] = 1e3 * dt1
#        self.s[indices + (1,)] = 1e3 * dt2
        self.step_times[:-1] = self.step_times[1:]
        self.step_times[-1] = t2 - t0

    def get_estimated_time_remaining(self):
        mask = np.isfinite(self.step_times)
        if not np.any(mask):
            return 0
        average_step_time = np.mean(self.step_times[mask])
        remaining_steps = self.total_points - self.current_step
        etr = remaining_steps * average_step_time
        return etr


def grid_scan_group():
    group = VGroup(
        Item('estimated_time_remaining', style='readonly'),
        HGroup(Item('acquire_button', show_label=False),
               Item('abort_button', show_label=False)),
    )
    return group


class GridScanControl(HasTraits):
    """
    Scans a grid in a separate acquisition thread using a grid_scanner
    scanner, applying the grid_scanner scan function at each point. The
    grid_scanner object contains the scanner stage and the scan function
    along with the GUI layout required for the scan. GridScan only provides
    methods for starting, maintaining and stopping grid scans.
    """

    grid_scanner = Instance(GridScanner)
    acquisition_thread = Instance(AcquisitionThread)
    display_thread = Instance(Thread)
    acquire_button = Button('Scan Grid')
    abort_button = Button('Abort Scan')
    estimated_time_remaining = String()

    traits_view = View(
        VGroup(Item('grid_scanner', style='custom', show_label=False),
               grid_scan_group(),
               spring),
        width=700, height=400, resizable=True, title="Grid Scan")

    def __init__(self, grid_scanner, gui_update_rate=0.5):
        super(GridScanControl, self).__init__()
        self.grid_scanner = grid_scanner
        self.grid_scanner.scan_controller = self
        self._gui_update_rate = gui_update_rate

    def _acquire_button_fired(self):
        # Create a separate acquisition thread and start it.
        self.acquisition_thread = AcquisitionThread(self.grid_scanner)
        self.display_thread = Thread(target=self._update_gui)
        self.acquisition_thread.start()
        self.display_thread.start()

    def _abort_button_fired(self):
        self.acquisition_thread.abort_requested = True

    def _update_gui(self):
        # wait for thread to start acquiring
        while (not self.grid_scanner.acquiring) or (self.grid_scanner.indices is ()):
            sleep(self._gui_update_rate)
        # once acquiring update gui
        while self.acquisition_thread.is_alive() and self.grid_scanner.acquiring:
            self.grid_scanner.update()
            sleep(self._gui_update_rate)
            self.estimated_time_remaining = self._get_estimated_time_remaining()

    def _get_estimated_time_remaining(self):
        if self.acquisition_thread is not None:
            etr = self.acquisition_thread.get_estimated_time_remaining()
            if etr < 120:
                return '{0:.1f} s'.format(etr)
            elif (etr >= 120) and (etr < 3600):
                return '{0:.1f} mins'.format(etr / 60.)
            elif etr >= 3600:
                return '{0:.1f} hours'.format(etr / 3600.)
        else:
            return 'inactive'
