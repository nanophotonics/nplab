# -*- coding: utf-8 -*-
"""
Created on Sat Sep 11 11:25:52 2021

@author: Eoin
"""
import cv2
import numpy as np
import pyqtgraph as pg
import qdarkstyle
from nplab.analysis import latest_scan, load_h5
from nplab.analysis.image_exclusion.utils import distance, save_rejected
from nplab.ui.ui_tools import QuickControlBox
from nplab.utils.image_filter_box import Image_Filter_box
from nplab.utils.notified_property import (DumbNotifiedProperty,
                                           register_for_property_changes)
from PyQt5 import QtWidgets
from tqdm import tqdm


class ParticleProximityExcluder(QtWidgets.QWidget):
    '''the general idea is that this widget identifies the particles in each 
    thumb image, and if any of them are too close to the central particle, 
    it is 'rejected'.'''
    exclusion_radius = DumbNotifiedProperty(13)

    def __init__(self, scan, image_name='CWL.thumb_image_0'):
        super().__init__()
        self.scan = scan
        self.image_name = image_name
        self.image = scan['Tiles']['tile_0'][()]
        # pick a tile to test the filter settings - analysis is done on thumb images though.
        self._construct()  # make the widget
        self.update_image()
        self.show()

    def _construct(self):

        layout = QtWidgets.QHBoxLayout()
        self.resize(1200, 700)
        self.img_widget = pg.ImageView(parent=self)

        layout.addWidget(self.img_widget)
        control_layout = QtWidgets.QVBoxLayout()
        ibox = QuickControlBox('exclusion settings')
        ibox.add_spinbox('exclusion_radius', 0, 100, 1)
        ibox.auto_connect_by_name(controlled_object=self)
        control_layout.addWidget(ibox)
        # ie.valueChanged.connect(lambda x: setattr(self, 'image_exclusion_fraction', x)) # gui to prop
        # register_for_property_changes(self, 'image_exclusion_fraction', ie.setValue)

        register_for_property_changes(self, 'exclusion_radius',
                                      self.update_image)  # prop to image
        self.filter_box = Image_Filter_box()
        control_layout.addWidget(self.filter_box.get_qt_ui())
        self.filter_box.connect_function_to_property_changes(self.update_image)
        self.run_pushButton = QtWidgets.QPushButton('Run')
        self.run_pushButton.clicked.connect(self.run)
        control_layout.addWidget(self.run_pushButton)
        control_box = QtWidgets.QFrame()
        control_box.setLayout(control_layout)
        layout.addWidget(control_box)
        self.setLayout(layout)

    def update_image(self, *value):
        """
        Apply live updates to the example image as the image filtering properties are changed
        """

        filtered_image = self.filter_box.current_filter(self.image)
        im = np.copy(filtered_image)
        if self.filter_box.current_filter_index == 1:
            centers, radii = self.filter_box.STBOC_with_size_filter(
                self.image, return_centers_and_radii=True)
            for c, r in zip(
                    centers, radii
            ):  # draw a white circle, if any red circle overlaps both particles should be discarded

                im = cv2.circle(im, tuple(c[::-1]), self.exclusion_radius + r,
                                (255, 255, 255), 1)
        self.img_widget.setImage(im)

    def run(self, path=None, overwrite=False):
        rejected = set()
        for name, group in tqdm(list(self.scan.items())):
            if not name.startswith('Particle'): continue
            im = group[self.image_name]
            im_center = tuple(np.array(im.shape)[:2] // 2)
            centers_radii = self.filter_box.STBOC_with_size_filter(
                im[()], return_centers_and_radii=True)

            if centers_radii is not None and len(centers_radii) > 1:
                center, radius = min(zip(*centers_radii),
                                     key=lambda c: distance(c[0], im_center))
                within = [
                    distance(c, center) < r + radius + self.exclusion_radius
                    for c, r in zip(*centers_radii)
                ]
                if sum(within) > 1:  # itself is always within radius
                    rejected.add(name)
        save_rejected(rejected, path=path, overwrite=overwrite)


if __name__ == '__main__':
    scan = latest_scan(load_h5())
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet())
    pp = ParticleProximityExcluder(scan)
    app.exec_()
