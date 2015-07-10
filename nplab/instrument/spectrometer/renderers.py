__author__ = 'alansanders'

from nplab.ui.data_renderers import FigureRenderer


class SpectrumRenderer(FigureRenderer):
    def __init__(self, h5group, parent=None):
        super(SpectrumRenderer, self).__init__(h5group, parent)
        self.wavelength = h5group['wavelength']
        self.spectrum = h5group['spectrum']

    def display_data(self):
        ax = self.fig.add_subplot(111)
        ax.plot(self.wavelength, self.spectrum)
        ax.set_xlabel('wavelength (nm)')
        self.fig.canvas.draw()

    @classmethod
    def is_suitable(cls, h5object):
        if not isinstance(h5object, h5py.Group):
            return -1
        if 'wavelength' in h5object and 'spectrum' in h5object:
            if len(h5object['spectrum'].shape == 1):
                return 3
            elif len(h5object['spectrum'].shape > 1):
                return 2


class MultiSpectrumRenderer(FigureRenderer):
    def __init__(self, h5group, parent=None):
        super(MultiSpectrumRenderer, self).__init__(h5group, parent)
        self.wavelength = h5group['wavelength']
        self.spectrum = h5group['spectrum']
        self.wavelength2 = h5group['wavelength2']
        self.spectrum2 = h5group['spectrum2']

    def display_data(self):
        ax = self.fig.add_subplot(111)
        ax.plot(self.wavelength, self.spectrum)
        ax = ax.twinx()
        ax.plot(self.wavelength2, self.spectrum2)
        ax.set_xlabel('wavelength (nm)')
        self.fig.canvas.draw()

    @classmethod
    def is_suitable(cls, h5object):
        if not isinstance(h5object, h5py.Group):
            return -1
        if 'wavelength2' in h5object and 'spectrum2' in h5object:
            if len(h5object['spectrum2'].shape == 1):
                return 5
            elif len(h5object['spectrum2'].shape > 1):
                return 4
        elif 'wavelength' in h5object and 'spectrum' in h5object:
            if len(h5object['spectrum'].shape == 1):
                return 3
            elif len(h5object['spectrum'].shape > 1):
                return 2