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
from nplab.analysis.particle_exclusion.utils import load_rejected, save_rejected
from scipy import ndimage, signal
from tqdm import tqdm


def center_of_mass(grey_image, circle_position, radius):
    '''given an image, get the center of mass of a circle in that image'''
    YY, XX = np.meshgrid(*list(map(range, grey_image.shape)),
                         indexing='ij')  # np coords
    dist_from_center = np.sqrt((XX - circle_position[0])**2 +
                               (YY - circle_position[1])**2)
    mask = dist_from_center <= radius
    def com(coords): return int(np.average(coords, weights=mask * grey_image))
    return com(XX), com(YY)


class MonotonousImageExcluder():
    '''the idea is that if a particle is isolated, a plot of image intensity vs.
    radius should decrease monotonously. This rejects a particle if it doesn't'''

    def __init__(self,
                 scan,
                 image_name='CWL.thumb_image_0',
                 exclusion_radius=13,  # pixels
                 maxima_region_fraction=0.5,
                 sigma=2):
        self.scan = scan
        self.image_name = image_name
        # radius over which intensity should always decrease
        self.exclusion_radius = exclusion_radius
        # only look for maxima after this fraction of the exclusion radius. This helps with ring-like DF images
        self.maxima_region_fraction = maxima_region_fraction
        self.sigma = sigma  # smoothing weight
        self.fig_dir = Path() / 'exclusion figures'  # may not exist yet

    def run(self, plot=False, overwrite=True):
        if plot:
            if not self.fig_dir.exists(
            ):  # make the folder if it doesn't exist
                self.fig_dir.mkdir()

        rejected = set() if overwrite else load_rejected()
        total = len(self.scan)
        for name, group in tqdm(list(self.scan.items())):
            if not name.startswith('Particle'):
                continue
            im = group[self.image_name]
            im_center = tuple(np.array(im.shape)[:2] // 2)
            grey_image = im[()].sum(axis=-1)
            smoothed_image = ndimage.gaussian_filter(grey_image, self.sigma)

            com = center_of_mass(grey_image, im_center, self.exclusion_radius)
            YY, XX = np.meshgrid(*list(map(range, grey_image.shape)),
                                 indexing='ij')  # np coords
            dist_from_center = np.sqrt((XX - com[0])**2 + (YY - com[1])**2)

            radially_averaged = []
            radii = np.arange(self.exclusion_radius)
            for inner, outer in zip(radii, radii[1:]):
                mask = np.logical_and(dist_from_center <= outer,
                                      dist_from_center > inner)
                radially_averaged.append(
                    np.percentile(smoothed_image[mask], 95))
            radially_averaged.append(0)
            # so if the intensity was increasing at the edge of the plot,
            # it's recognized as a local maximum, and rejected.

            maxima = signal.argrelextrema(
                np.array(radially_averaged)[
                    int(self.exclusion_radius*self.maxima_region_fraction):],
                np.greater,
            )[0]
            if len(maxima):
                rejected.add(name)

            if plot:
                fig, axs = plt.subplots(1, 3, figsize=(9, 3), dpi=80)
                status = 'rejected' if len(maxima) else 'accepted'
                fig.suptitle(f'{name}, {status}')
                axs[0].imshow(cv2.circle(
                    im[()], com, self.exclusion_radius, (255, 255, 255), 1))
                axs[0].plot(*com, 'ko')
                axs[1].plot(radii, radially_averaged)
                axs[2].imshow(smoothed_image)
                fig.savefig(self.fig_dir / f'{name}.png')
                plt.close(fig)
        save_rejected(rejected)
        print(f'{(len(rejected) / total)*100}% rejected')


if __name__ == '__main__':
    scan = latest_scan(load_h5())
    mie = MonotonousImageExcluder(scan)
    mie.run()
