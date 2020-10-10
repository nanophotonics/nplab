from builtins import range
__author__ = 'alansanders'

import traits.api
from traits.api import Property
from matplotlib.figure import Figure
from nplab.utils.traitsui_mpl_qt import MPLFigureEditor
from multiprocessing.pool import ThreadPool
from nplab.experiment.gridscanner import *


class GridScannerChild(GridScanner):
    fig = Property(trait=Instance(Figure))
    data = Array(np.float64, comparison_mode=NO_COMPARE)

    traits_view = View(
        HGroup(grid_scanner_group(),
               Item('fig', editor=MPLFigureEditor(), show_label=False),
        ), )

    def __init__(self):
        super(GridScannerChild, self).__init__()
        self.num_axes = 2
        self.axes = ['X', 'Y']
        self.pool = ThreadPool(processes=4)
        self.f = None

    def update(self):
        self._update_plot()

    @traits.api.cached_property  # only draw the graph the first time it's needed
    def _get_fig(self):
        p = Figure()
        return p

    def init_scan(self):
        self._init_grid(self.size, self.step, self.init)

        self.f = h5py.File(os.path.join(os.path.expanduser('~'), 'Desktop', 'Data.hdf5'), 'w')
        #self.data = self.f.create_dataset('data', shape=self.grid_shape)
        self.data = np.zeros(self.grid_shape)
        self.data[:] = np.NAN

        self.fig.clear()
        self.fig.add_subplot(121)
        self.fig.add_subplot(122)
        self.fig.tight_layout()

    def move(self, ax, position):
        #self.scanner.move(position, axis=ax)
        pass

    def target_thread(self, delay, indices):
        sleep(delay)
        if self.num_axes == 2:
            i, j = indices
            return (self.scan_axes[0][i]) ** 2 + (self.scan_axes[1][j]) ** 2
        elif self.num_axes == 3:
            i, j, k = indices
            return (self.scan_axes[0][i]) ** 2 + (self.scan_axes[1][j]) ** 2 + (self.scan_axes[2][k]) ** 2

    def scan_function(self, *indices):
        ts = self.pool.map(lambda x: self.target_thread(x, indices),
                           [0.005, 0.004, 0.003, 0.004])
        self.data[indices] = ts[0]

    def _update_plot(self):
        for i in range(2):
            ax = self.fig.axes[i]
            if self.num_axes == 2:
                data = self.data
            elif self.num_axes == 3:
                data = self.data[:, :, self.indices[-1]]
            if not ax.images:
                img = ax.imshow(data.transpose(), origin='lower', aspect='equal',
                                interpolation='nearest',
                                extent=[-1, 1, -2, 2])
                img.set_cmap('hot')
                self.fig.canvas.draw()
            else:
                img = ax.images[0]
                img.set_data(data)
                img.set_clim(data[np.isfinite(data)].min(),
                             data[np.isfinite(data)].max())
                ax.relim()
                ax.draw_artist(ax.patch)
                ax.draw_artist(img)

        if self.fig.canvas is not None:
            self.fig.canvas.update()
            self.fig.canvas.flush_events()
            #self.fig.canvas.draw()

    def close_scan(self):
        self.f.close()


grid_scanner = GridScannerChild()
scanning = GridScanControl(grid_scanner, gui_update_rate=0.05)
scanning.configure_traits()