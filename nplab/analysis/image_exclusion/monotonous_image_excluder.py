# -*- coding: utf-8 -*-
"""
Created on Sat Sep 11 11:25:52 2021

@author: Eoin
"""
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from nplab.analysis import latest_scan, load_h5
from nplab.analysis.image_exclusion.utils import save_rejected
from scipy import ndimage, signal
from tqdm import tqdm


def center_of_mass(grey_image, circle_position, radius):
    '''given an image, get the center of mass of a circle in that image'''
    YY, XX = np.meshgrid(*list(map(range, grey_image.shape)),
                         indexing='ij')  # np coords
    dist_from_center = np.sqrt((XX - circle_position[0])**2 +
                               (YY - circle_position[1])**2)
    mask = dist_from_center <= radius
    com = lambda coords: int(np.average(coords, weights=mask * grey_image))
    return com(XX), com(YY)


class MonotonousImageExcluder():
    '''the idea is that if a particle is isolated, a plot of image intensity vs.
    radius should decrease monotonously. This rejects a particle if it doesn't'''
    def __init__(self,
                 scan,
                 image_name='CWL.thumb_image_0',
                 exclusion_radius=13,
                 sigma=2):
        self.scan = scan
        self.image_name = image_name
        self.exclusion_radius = exclusion_radius  # radius over which intensity should always decrease
        self.sigma = sigma  # smoothing weight
        self.fig_dir = Path() / 'figures'  # may not exist yet

    def run(self, plot=False):
        if plot:
            if not self.fig_dir.exists(
            ):  # make the folder if it doesn't exist
                self.fig_dir.mkdir()

        rejected = set()
        for name, group in tqdm(list(scan.items())):
            if not name.startswith('Particle'): continue
            im = group[self.image_name]
            im_center = tuple(np.array(im.shape)[:2] // 2)
            grey_image = im[()].sum(axis=-1)

            com = center_of_mass(grey_image, im_center, self.exclusion_radius)
            YY, XX = np.meshgrid(*list(map(range, grey_image.shape)),
                                 indexing='ij')  # np coords
            dist_from_center = np.sqrt((XX - com[0])**2 + (YY - com[1])**2)

            radially_averaged = []
            radii = np.arange(self.exclusion_radius)
            for inner, outer in zip(radii, radii[1:]):
                mask = np.logical_and(dist_from_center <= outer,
                                      dist_from_center > inner)
                radially_averaged.append(grey_image[mask].mean())
            radially_averaged.append(0)
            # so if the intensity was increasing at the edge of the plot,
            # it's recognized as a local maximum, and rejected.

            maxima = signal.argrelextrema(
                np.array(radially_averaged),
                np.greater,
            )[0]
            if len(maxima):
                rejected.add(name)

            if plot:
                fig, axs = plt.subplots(1, 3)
                status = 'rejected' if len(maxima) else 'accepted'
                fig.suptitle(f'{name}, {status}')
                axs[0].imshow(cv2.circle(im[()], com, 13, (255, 255, 255), 1))
                axs[1].plot(radii, radially_averaged)
                axs[2].imshow(ndimage.gaussian_filter(grey_image, self.sigma))
                fig.savefig(self.fig_dir / f'{name}.png')
                plt.close(fig)
        save_rejected(rejected)


if __name__ == '__main__':
    scan = latest_scan(load_h5())
    mie = MonotonousImageExcluder(scan)
    mie.run()
