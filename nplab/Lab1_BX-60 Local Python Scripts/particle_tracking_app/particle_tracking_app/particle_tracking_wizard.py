# -*- coding: utf-8 -*-
"""
Created on Wed Feb 10 17:47:09 2016

Run a "wizard"-based particle tracking app.

@author: rwb27, wmd22
"""

from nplab.instrument.spectrometer import spectrometer_aligner
from nplab.instrument.camera.camera_with_location import AcquireGridOfImages
from nplab.utils.image_filter_box import Image_Filter_box
from nplab.utils.image_with_location import ImageWithLocation
from nplab.utils.notified_property import DumbNotifiedProperty, NotifiedProperty, register_for_property_changes
import nplab.datafile as df
from nplab.utils.gui import QtWidgets, QtCore, QtGui, uic, get_qt_app
from nplab.ui.ui_tools import UiTools
from itertools import cycle
import threading
import cv2
from nplab.utils.array_with_attrs import ArrayWithAttrs
import os
import pyqtgraph as pg
import numpy as np
from random import choice
from .reconstruct_tiled_image import reconstruct_tiled_image

def distance(p1, p2):
        '''distance between two points'''
        return ((p1[0] - p2[0])**2 + (p1[1]-p2[1])**2)**0.5
        
def sort_centers(centers, starting_point=None):
    path = []
    points = list(centers)
    
    def update(current_point):
        path.append(current_point)
        points.remove(current_point)
        
        
    if starting_point is None:
        cp = choice(points)
        update(cp)
    else:
        cp = starting_point
    while points:
        update(min(points,
                    key=lambda p: distance(p, cp)))
    return path
def transform_for_view(image):
    if len(image.shape)==2:
            image = image.transpose()
    elif len(image.shape)==3:
        image = image.transpose((1,0,2))
    return image

def center_of_mass(grey_image, circle_position, radius):
    '''given an image, get the center of mass of a circle in that image'''
    YY, XX = np.meshgrid(*list(map(range, grey_image.shape))[::-1])
    dist_from_center = np.sqrt((XX - circle_position[0])**2 + (YY-circle_position[1])**2)
    mask = dist_from_center <= radius
    com = lambda coords: int(np.average(coords, weights=mask*grey_image))
    return com(XX), com(YY)
 

class TrackingWizard(QtWidgets.QWizard, UiTools):
    """ The tracking wizard is a helpful guide for setting up a particle tracking
    experiement. The wizard will lead the user through the process required to 
    setup the experiemnt in the following order; calibrating the camera with location, 
    creating a tiled image of the sample, altering image filtering paramters to
    maximise the number of detected particles, using the intuitive task manager to 
    select what functions are performed upon each particle and finally starting
    the measurement!
    """
    tiles_x = DumbNotifiedProperty(1)
    tiles_y = DumbNotifiedProperty(1)
    current_particle = DumbNotifiedProperty()
    total_particles = DumbNotifiedProperty()
    autofocus = DumbNotifiedProperty()
    task_list = ['CWL.autofocus']# 'alinger.optimise_2D', 'aligner.z_scan','CWL.create_dataset']
    scanner_status = DumbNotifiedProperty('Not yet Started')
    def __init__(self, CWL,equipment_dict=dict(), task_list=[]):
        """
        Args:
            CWL(CameraWithLocation):    A camera with location object connecting
                                        the stage and the camera
            equipment_dict(dict):       A dictionary containing additional equipment
                                        required within the experiment.
            task_list(list):            A list of additional functions the user may
                                        wish to perform upon each particle
        """
        super(TrackingWizard, self).__init__()
        uic.loadUi(os.path.dirname(__file__)+'\\wizard.ui', self)
        self.auto_connect_by_name(controlled_object = self)
#        self.tracking_wizard = tracking_wizard
        for task in task_list:
            self.task_list+=[task]
        self.data_file = df.current()
        self.CWL = CWL
        self.white_shutter = None
        for equipment in equipment_dict:
            setattr(self, equipment, equipment_dict[equipment])
       # uic.loadUi(r'C:\Users\Hera\Documents\GitHub\particle_tracking_app\wizard.ui', self)
        
        self._scan_lock = threading.Lock()
        self._abort_scan_event = threading.Event()
        
        self.cam_pushButton.clicked.connect(self.CWL.show_gui)
        self.spec_pushButton.clicked.connect(self.spectrometer.show_gui)
        self.replace_widget(self.display_layout,
                            self.camdisplay_widget,
                            self.CWL.camera.get_preview_widget())
        self.tiled_image_widget_view = pg.GraphicsLayoutWidget()
        vb = self.tiled_image_widget_view.addViewBox(row=1, col=1)
        self.tiled_image_item = pg.ImageItem()
        vb.addItem(self.tiled_image_item)
        vb.setAspectLocked(True)
        self.replace_widget(self.display_layout,
                            self.tileddisplay_widget,
                            self.tiled_image_widget_view)

        self.filter_box = Image_Filter_box()
        self.replace_widget(self.verticalLayout_2,
                            self.image_filter_widget,
                            self.filter_box.get_qt_ui())
        self.filter_box.connect_function_to_property_changes(self.update_tiled_image)
                            
        self.tiled_image_widget_analysis = pg.ImageView()
        self.replace_widget(self.find_particles_page.layout(),
                            self.overview_image_graph_findparticlespage,
                            self.tiled_image_widget_analysis)
        self.acquire_image_pushbutton.clicked.connect(self.create_and_stitch_tiles)

        self.task_manager = Task_Manager(self.task_list,self)
        self.replace_widget(self.verticalLayout_3,
                            self.task_manager_widget,
                            self.task_manager)
        
        self.current_particle_lineEdit.setReadOnly(True)
        self.total_particles_lineEdit.setReadOnly(True)
        self.scanner_status_lineEdit.setReadOnly(True)
        self.tile_edge = 110

        self.insist_particle_name = False
    
    def create_and_stitch_tiles(self):
        """creates a h5group before taking a grid of images using the 
        AcquireGridOfImages class and stitchting them together to form a tiled
        image."""
        assert self.CWL.pixel_to_sample_displacement is not None, 'The camera is not calibrated!'
        self.scan_group = self.data_file.create_group('ParticleScannerScan_%d')
        self.tile_group = self.scan_group.create_group('Tiles')
        self.tiler = AcquireGridOfImages(self.CWL,
                                         completion_function=self.complete_stitching)
        self.tiler.prepare_to_run(n_tiles=(self.tiles_x, self.tiles_y),
                                  data_group = self.tile_group)
        if self.autofocus: autofocus_args = {'use_thumbnail' : False}
        else: autofocus_args = None
        self.tiler.run_modally(n_tiles=(self.tiles_x, self.tiles_y), autofocus_args=autofocus_args)
  #      run_function_modally()

    def complete_stitching(self):
        """Once the grid of images has been taken they are stitched together 
        from the hdf5 group """
        self.tiled_group = self.tiler.dest
        self.tiled_image = reconstruct_tiled_image(list(self.tiled_group.values()))
        self.scan_group.create_dataset('reconstructed_tiles',
                                       data=self.tiled_image,
                                       attrs=self.tiled_image.attrs)
        # self.tiled_image_widget_analysis.setImage(self.tiled_image)
     #   self.tiled_image_widget_analysis.setDownsampling(self.tiles_x)
        self.tiled_image_widget_analysis.imageItem.setAutoDownsample(True)
        self.tiled_image_item.setImage(transform_for_view(self.tiled_image))

    def update_tiled_image(self,value):
        """ Apply live updates to the tiled images as the image filtering properties are changed
        """
        try:
            
            filtered_tile = self.filter_box.current_filter(self.tiled_image)
            print('shape', np.shape(filtered_tile))
            self.tiled_image_widget_analysis.setImage(transform_for_view(filtered_tile))
        except Exception as e:
            print('Tiled image not yet taken!')
            print(e)

    
    def start_tracking_func(self):
        """ The function used to begin particle tracking. Firstly it constructs 
        the payload function from the task manager, gets the particle centeres 
        from the latest tiled image filtering settings prior using the
        CWL to move to and center each particle before runnign the payload.
        """
        self.scanner_status = 'Scanning!'
        tiles = self.tiled_image
        # self.payload = self.task_manager.construct_payload()
        centers = self.filter_box.STBOC_with_size_filter(self.tiled_image,return_centers=True)
        tile_edge = self.tile_edge # number of pixels from the edge to ignore a particle
        centers = centers[np.logical_and(centers[:,0]>(tile_edge),
                                         centers[:,0]<(tiles.shape[0]-tile_edge))]
        centers = centers[np.logical_and(centers[:,1]>(tile_edge),
                                         centers[:,1]<(tiles.shape[1]-tile_edge))]
        path = sort_centers(centers.tolist(), starting_point=(0, self.tiled_image.shape[0]))
        self.total_particles = len(centers)
        for p_number, particle_center in enumerate(path):
            self.payload = self.task_manager.construct_payload()
            
            if self.white_shutter is not None:
                self.white_shutter.open_shutter()
            self.current_particle = p_number
        
            #Move to and center the particle
            feature = tiles.feature_at(particle_center,size = (80,80))
            if self.CWL.filter_images == True and self.CWL.camera.filter_function is not None:
                attrs = feature.attrs
                feature = self.CWL.camera.filter_function(feature)
                feature = ImageWithLocation(feature,attrs = attrs)
            self.current_feature = feature
            
            if self.autofocus: 
                autofocus_args = {'use_thumbnail': False}
                autofocus_first = True
            else: 
                autofocus_args = None
                autofocus_first = False
                
            self.CWL.stage.move(tiles.pixel_to_location(particle_center))
            # to_save = self.CWL.move_to_feature(feature, 
                                     # ignore_z_pos=True,
                                     # autofocus_first=autofocus_first, 
                                     # autofocus_args=autofocus_args)
            
         #   feature = self.tiled_image.feature_at(particle_center,size = (20,20))
        #    feature = self.CWL.thumb_image(size = (20,20))
        #    feature = image.feature_at((image.shape[0]/2,image.shape[1]/2),size = (20,20))
        #    self.CWL.move_to_feature(feature,ignore_position= True,margin=1,tolerance = 0.1)
            
        #create particle group and run payload

            if self.insist_particle_name is True:
                if 'Particle_%d'%p_number in list(self.scan_group.keys()):
                    self.particle_group = self.scan_group['Particle_%d'%p_number]
                else:
                    self.particle_group = self.scan_group.create_group('Particle_%d'%p_number)
            else:
                self.particle_group = self.scan_group.create_group('Particle_%d')
            try: # Allows the use of Particle exceptions to skip particles
                # for name, dataset in to_save.items():
                #     self.particle_group.create_dataset(name, data=dataset)
                self.payload(self.particle_group)
            except ParticleException as e:
                print('Particle '+str(self.current_particle)+' has failed due to:')
                print(e)
            except Exception as e:
                print(e)
                self.scanner_status ='Error! Scan Failed!'
                break
            if self._abort_scan_event.is_set(): #this event lets us abort a scan
                self.scanner_status="Scan Aborted!"
                self._abort_scan_event.clear()
                break
        if self.scanner_status == 'Scanning!':
            self.scanner_status = 'Finished!'
    def start(self):
        """A function that threads the  'start_tracking_func' function"""
        def worker_function():
            self.start_tracking_func()
        self._scan_thread = threading.Thread(target=worker_function)
        self._scan_thread.start()
    def stop(self):
        """Abort a currently-running scan in a background thread."""
        if self._scan_thread is not None and self._scan_thread.is_alive():
            self._abort_scan_event.set()
    def skip_particle(self):
        self.task_manager.abort_tasks = True
        
from .infinite_spiral import spiral

class InfiniteTrackingWizard(TrackingWizard):
    image_exclusion_fraction = DumbNotifiedProperty(0)
    image_size=DumbNotifiedProperty(800)
    maximum_particles = DumbNotifiedProperty('Infinite!')
    autofocus_tile = DumbNotifiedProperty(False)
    autofocus_particle = DumbNotifiedProperty(False)
    skip_if_centering_fails = DumbNotifiedProperty(False)
    max_autofocus_fails = DumbNotifiedProperty(20)
    task_list = ['CWL.thumb_image']
    
    def __init__(self, CWL, equipment_dict=dict(), task_list=[]):
        """
        Args:
            CWL(CameraWithLocation):    A camera with location object connecting
                                        the stage and the camera
            equipment_dict(dict):       A dictionary containing additional equipment
                                        required within the experiment.
            task_list(list):            A list of additional functions the user may
                                        wish to perform upon each particle
        """
        super(TrackingWizard, self).__init__()
        uic.loadUi(os.path.dirname(__file__)+'\\infinite_wizard.ui', self)
        self.auto_connect_by_name(controlled_object=self)
        for task in task_list:
            self.task_list+=[task]
        self.data_file = df.current()
        self.CWL = CWL
        self.white_shutter = None
        for equipment in equipment_dict:
            setattr(self, equipment, equipment_dict[equipment])
        
        self._scan_lock = threading.Lock()
        self._abort_scan_event = threading.Event()
        
        self.cam_pushButton.clicked.connect(self.CWL.show_gui)
        self.spec_pushButton.clicked.connect(self.spectrometer.show_gui)
        self.image_exclusion_fraction_doubleSpinBox.valueChanged.connect(self.update_example_image)

        self.filter_box = Image_Filter_box()
        self.replace_widget(self.verticalLayout_2,
                            self.image_filter_widget,
                            self.filter_box.get_qt_ui())
        self.filter_box.connect_function_to_property_changes(self.update_example_image)
                            
        self.example_image_widget_analysis = pg.ImageView()
        self.replace_widget(self.find_particles_page.layout(),
                            self.overview_image_graph_findparticlespage,
                            self.example_image_widget_analysis)
        self.acquire_image_pushbutton.clicked.connect(self.image_and_update_widget)

        self.task_manager = Task_Manager(self.task_list,self)
        self.replace_widget(self.verticalLayout_3,
                            self.task_manager_widget,
                            self.task_manager)
        
        self.current_particle_lineEdit.setReadOnly(True)
        self.scanner_status_lineEdit.setReadOnly(True)
        self.tile_edge = 110

        self.insist_particle_name = False
    
    def image_and_update_widget(self):
        self.example_image = np.array(self.take_image())
        self.example_image_widget_analysis.setImage(transform_for_view(self.example_image)) 
        self.example_image_widget_analysis.imageItem.setAutoDownsample(True)
        
    def update_example_image(self, value):
        """ 
        Apply live updates to the example image as the image filtering properties are changed
        """
        try:
            
            filtered_image = self.filter_box.current_filter(self.example_image)
            im = np.copy(filtered_image)
            s = np.array(im.shape)[:2][::-1]
            topleft = tuple((self.image_exclusion_fraction*s).astype(int))
            bottomright = tuple(((1-self.image_exclusion_fraction)*s).astype(int))
            cv2.rectangle(im, topleft, bottomright, (255,255,0), 3)
            self.example_image_widget_analysis.setImage(transform_for_view(im))
        except Exception as e:
            print('Example image not yet taken!')
            print(e)

    
    def take_image(self):
        ''' take a square image of a given size and update its pixel-to-sample matrix '''
        image = self.CWL.raw_image(update_latest_frame=True)
        
        image = self.CWL.crop_centered(image, (self.image_size, self.image_size))
        centre = image.attrs['stage_position']
        image.attrs['datum_pixel'] = [image.shape[0]/2,
                                                image.shape[1]/2]

        p2s = np.zeros((4,4))
        p2s[:2,:2] = image.attrs['pixel_to_sample_matrix'][:2,:2]
        p2s[2,2] = 1
        theory_centre =np.dot(image.attrs['datum_pixel'], p2s[:2,:2])
        offset = centre[:2] - theory_centre
        p2s[3,:2] = offset 
        p2s[3,2] = centre[2] 
        image.attrs['pixel_to_sample_matrix'] = p2s 
        return image
        
    def start_tracking_func(self):
        """ 
        An image is taken, and the particles in it identified according to 
        the parameters entered in the wizard. The scanner then goes to 
        each particle, centers according to the centering function. The 
        order is determined by a simple 'traveling salesman' algorithm to 
        roughly minimise the path taken between the particles. 
        (smaller movements = less drift in z)

        The payload is constructed at each particle, meaning you can edit it 
        during the track's run.
        When all the particles are measured in a given tile, the scanner 
        moves to another in an anti-clockwise spiral pattern, and repeats.
        This can continue until it reaches the edge of your sample. 
    
        """
        
        self.scanner_status = 'Scanning!'
        self.scan_group = self.data_file.create_group('ParticleScannerScan_%d')    
        failures = 0
        topright = np.dot(np.array([self.image_size, self.image_size, 0, 1]), self.CWL.pixel_to_sample_matrix)[:2]
        bottomleft = np.dot(np.array([0, 0, 0, 1]), self.CWL.pixel_to_sample_matrix)[:2]
        moves = np.abs(topright-bottomleft)
        *xy, z = self.CWL.stage.position
        p_number = -1
        self.tile_group = self.scan_group.create_group('Tiles')
        try:
            for i, position in enumerate(spiral(xy, moves)):
                
                print('spiral tile:', i )    
                
                self.CWL.stage.move(position)
                if self.autofocus_tile: self.CWL.autofocus()
                image = self.take_image()
                self.tile_group.create_dataset("tile_%d", data=image)
                centers = self.filter_box.STBOC_with_size_filter(image,
                                                                return_centers=True)
                tile_with_centers = self.filter_box.STBOC_with_size_filter(image,
                                                                return_original_with_particles=True)
                self.tile_group.create_dataset('tile_with_centers_%d', data=tile_with_centers)
                
                assert centers is not None, 'no particles found'
                frac = self.image_exclusion_fraction # excluding the particles within frac*image length of the edge
                centers  = [center for center in centers.tolist() if all([(frac*s < c < (1-frac)*s) for c, s in zip(center, image.shape[:2])])]
                assert len(centers) > 0, 'all particles excluded'
                path = sort_centers(centers, starting_point=(0, 0)) # (0,0) is the top left
              
                for particle_center in path:                    
                    p_number += 1
                    if self.maximum_particles.isdigit() and int(p_number) > int(self.maximum_particles):
                        raise AbortionException('maximum particles reached!')
                    self.CWL.stage.move(image.pixel_to_location(particle_center))
                    self.payload = self.task_manager.construct_payload()
                    if self.white_shutter is not None:
                        self.white_shutter.open_shutter()
                    self.current_particle = p_number
                
                    
                    if self.autofocus_particle: 
                        success, *_ = self.CWL.autofocus(use_thumbnail=True)
                        if sum(success):
                           failures = 0
                        else:
                            failures += 1
                    if failures == self.max_autofocus_fails: # in a row
                        raise AbortionException(f'autofocusing failed {failures} times in a row')
                   
                    if not self.center_on_particle():
                        print('centering failed')
                        if self.skip_if_centering_fails:
                            print('therefore skipping particle')
                            continue
                        
                    if self.insist_particle_name is True:
                        if f'Particle_{self.current_particle}' in list(self.scan_group.keys()):
                            self.particle_group = self.scan_group[f'Particle_{self.current_particle}']
                        else:
                            self.particle_group = self.scan_group.create_group(f'Particle_{self.current_particle}')
                    else:
                        self.particle_group = self.scan_group.create_group('Particle_%d')
                    try: # Allows the use of Particle exceptions to skip particles
                        self.payload(self.particle_group)
                   
                    except ParticleException as e:
                        print('Particle '+str(self.current_particle)+' has failed due to:')
                        print(e)
                    
                    except Exception as e:
                        print(e)
                        raise AbortionException('Error! Scan Failed!')
                    
                    if self._abort_scan_event.is_set(): #this event lets us abort a scan
                        raise AbortionException('Scan Aborted!')
                        
        except AbortionException as e:
            print(e)
            self.scanner_status = e
            self._abort_scan_event.clear()
        
    def center_on_particle(self, tolerance=0.1, max_allowed_movement=2, max_iterations=10):
        ''' this function finds the particle closest to the image centre by the parameters 
        entered in the wizard. It keeps to the center of this particle until the movement is 
        below the tolerance (um), or max_iterations is reached. 

        Returns True if successful, False otherwise. 

        this function doesn't allow the stage to move more than max_allowed_movement.
        '''
        initial_position = self.CWL.stage.position 
        for i in range(max_iterations):
            image = self.take_image() # grey_image
            centers, radii = self.filter_box.STBOC_with_size_filter(image,
                                                                    return_centers_and_radii=True)
            if centers is None or len(centers) == 0:
                print('no particle found here')
                break
            center, radius = min(zip(centers,radii), key=lambda c: distance(c[0], image.datum_pixel))
            pixel = center_of_mass(image.sum(axis=2), center, radius)
            new_position = image.pixel_to_location(pixel)
            movement = distance(image.datum_location, new_position)
            travel = distance(new_position, initial_position)

            if travel > max_allowed_movement:
                return False
            self.CWL.stage.move(new_position)
            self.CWL.settle()
            if movement < tolerance:
                return True
        return False
    
class ParticleException(Exception):
    """A simple exception that the user can raise if they wish to skip a 
    particle for some reason for example if the signal is too low are their
    analysis decides it is not the desired object"""
    pass

class AbortionException(Exception):
    pass 
  
from .task_manager import Task_Manager # sneaky sneaky error dodge - removes import loop error
        
if __name__ == '__main__':
    from nplab.instrument.camera.lumenera import LumeneraCamera
 #   from nplab.instrument.stage.prior import ProScan
    from nplab.instrument.spectrometer.seabreeze import OceanOpticsSpectrometer
    from nplab.instrument.camera.camera_with_location import CameraWithLocation
    
    from UltrafastRig.Equipment.xyzstage_wrapper import piezoconcept_thorlabsMSL02_wrapper
    from UltrafastRig.Equipment.Piezoconcept_micro import Piezoconcept
    from nplab.instrument.stage.apt_vcp_motor import DC_APT
    
    app = get_qt_app()
    cam = LumeneraCamera(1)
#    stage = ProScan("COM1", hardware_version = 2)
    microscope_stage = DC_APT(port='COM12', destination = {'x':0x21,'y':0x22},stage_type = 'MLS',unit = 'u')
    zstage = Piezoconcept(port = 'COM2')
    stages = piezoconcept_thorlabsMSL02_wrapper()    
    
    CWL = CameraWithLocation(cam,stages)
    spec = OceanOpticsSpectrometer(0)
    equipment_dict = {'spectrometer' : spec}
    wizard = TrackingWizard(CWL,equipment_dict,task_list = ['spectrometer.read_spectrum'])
    spec.show_gui(blocking=False)
    CWL.show_gui(blocking=False)
    wizard.show()
    #   ui = wizard.get_qt_ui()
            
#    wizard = TrackingWizard(dummy_CWL(),instr_dict)
 #   ui = wizard.get_qt_ui()
    