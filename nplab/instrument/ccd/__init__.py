from __future__ import division
from past.utils import old_div
__author__ = 'alansanders'

from nplab.instrument import Instrument
import inspect
import os
import h5py
import datetime
import numpy as np
import numpy.ma as ma


class CCD(Instrument):
    _CONFIG_EXTENSION = '.h5'

    def __init__(self):
        super(CCD, self).__init__()
        self._wavelengths = None
        self.reference = None
        self.background = None
        self.latest_image = None

    def read_image(self):
        raise NotImplementedError

    def read_background(self):
        """Acquire a new spectrum and use it as a background measurement."""
        self.background = self.read_image()
        self.update_config('background', self.background)

    def clear_background(self):
        """Clear the current background reading."""
        self.background = None

    def read_reference(self):
        """Acquire a new spectrum and use it as a reference."""
        self.reference = self.read_image()
        self.update_config('reference', self.reference)

    def clear_reference(self):
        """Clear the current reference spectrum"""
        self.reference = None

    def process_image(self, image):
        """Subtract the background and divide by the reference, if possible"""
        if self.background is not None:
            if self.reference is not None:
                old_error_settings = np.seterr(all='ignore')
                new_image = old_div((image - self.background),(self.reference - self.background))
                np.seterr(**old_error_settings)
                # if the reference is nearly 0, we get infinities - just make them all NaNs.
                new_image[np.isinf(new_image)] = np.nan
            else:
                new_image = image - self.background
        else:
            new_image = image
        return new_image

    def read_processed_image(self):
        """
        Acquire a new image and return a processed (referenced/background-subtracted) image.

        NB if saving data to file, it's best to save raw images along with metadata - this is a
        convenience method for display purposes.
        """
        image = self.read_image()
        self.latest_image = self.process_image(image)
        return self.latest_image

    def mask_image(self, image, threshold=0.05):
        """
        Return a masked array of the image, showing only points where the reference
        is bright enough to be useful.
        """
        if self.reference is not None and self.background is not None:
            reference = self.reference - self.background
            mask = reference < reference.max() * threshold
            return ma.array(image, mask=mask)
        else:
            return image
