# -*- coding: utf-8 -*-
'''
Created on 2023-02-10
@author: car72

Module with basic functions for file & folder navigation and manipulation

'''

import os
import re
from IPython.utils import io
from random import randint
import time
import h5py
import numpy as np

from nplab.analysis.general_spec_tools import spectrum_tools as spt
from nplab.analysis.general_spec_tools import npom_df_pl_tools as dpt
from nplab.analysis.general_spec_tools import all_rc_params as arp

df_rc_params = arp.master_param_dict['DF Spectrum']

class FileNotFoundError(Exception):
    pass

def find_h5_file(root_dir = None, most_recent = True, name_format = 'date', extension = 'h5', exclude = None, 
                 print_progress = True, **kwargs):
    '''
    Finds either oldest or most recent file in a folder using specified name format and extension, using format_matches() function (see above)
    Default name format ('date') is yyyy-mm-dd, default extension is .h5
    Variables:
        root_dir: string; directory to look in. Defaults to current working directory.
        most_recent: bool; finds most recent instance of file type if True, oldest if False
        name_format: string;
            if name_format == 'date', looks for filename starting with a string matching the format 'yyyy-mm-dd'
            otherwise, looks for filename starting with name_format
        extension: string or list of strings; default = 'h5' (obviously)
        exclude: string which filename must not include
        print_progress: bool; prints name of discovered file to console if True; suppresses if False

    '''
    if root_dir is not None:
        os.chdir(root_dir)

    with io.capture_output(not print_progress):#suppresses console printing if print_progress == False
        print(f'Searching for {"most recent" if most_recent == True else "oldest"} instance of {"yyyy-mm-dd" if name_format == "date" else name_format}(...){extension}...')

        if extension in ['h5', 'hdf5']:
            extension = ['h5', 'hdf5']

        h5_filenames = sorted([filename for filename in os.listdir()
                               if format_matches(filename, name_format, extension = extension, exclude = exclude)],#finds list of filenames with yyyy-mm-dd(...).h(df)5 format
                               key = lambda filename: os.path.getmtime(filename))#sorts them by date and picks either oldest or newest depending on value of 'most_recent'

        if len(h5_filenames) > 0:
            h5_file = h5_filenames[-1 if most_recent == True else 0]
            print(f'    H5 file {h5_file} found')
        else:
            raise FileNotFoundError(f'    H5 file with name format "{name_format}" not found in {os.getcwd()}\n')
    
    return h5_file

def format_matches(filename, name_format, extension = ['h5', 'hdf5'], exclude = None, **kwargs):
    '''
    Checks if a filename format matches {name_format}[...]{extension}

    Variables:
        filename: string; filename (including extension)
        name_format: string;
            if name_format == 'date', checks if filename starts with a string matching the format 'yyyy-mm-dd'
            otherwise, checks if filename starts with name_format
        extension: string or list of strings
    '''
    if type(extension) == str:
        extension = [extension]
    if filename.split('.')[-1] not in extension:
        return False
    if name_format == 'date':
        matches = bool(re.match('\d\d\d\d-[01]\d-[0123]\d', filename[:10])) 

        if exclude is not None:
            matches = matches and exclude not in filename

        return matches
    
    else:
        matches = filename.startswith(name_format) or filename.split('.')[0].endswith(name_format)

        if exclude is not None:
            matches = matches and exclude not in filename

        return matches

def generate_filename(filename, extension = '.h5', print_progress = True, overwrite = False, **kwargs):
    '''Auto-increments new filename if file exists in current directory'''
    with io.capture_output(not print_progress):#suppresses console printing if print_progress == False
        print('\nDeciding filename...')
        output_filename = filename

        if not extension.startswith('.'):
            extension = '.' + extension

        if not filename.endswith(extension):
            output_filename = f'{filename}{extension}'

        assert type(overwrite) == bool, 'overwrite must be True or False'

        if overwrite == False:
            n = 0
            while output_filename in os.listdir('.'):
                n += 1
                output_filename = f'{filename}_{n}{extension}'
                
                print(f'  {filename}_{n - 1}{extension} already exists')
            print(f'    New file will be called {output_filename}\n')

        elif overwrite == True:
            if output_filename in os.listdir('.'):
                print(f'    WARNING: {output_filename} already exists and will be overwritten!')

    return output_filename

def percent_progress(n, total, resolution = 10, indent = 0, start_time = None):
    '''
    Displays the percentage completion of a for loop
    
    arguments:
        n: index of item in the loop; loop must be performed using enumerate()
        total: length of iterable upon which the for loop is acting
        resolution: resolution with which the percentage progress is displayed
    '''
    
    import numpy as np
    
    progress = None

    if start_time is not None:
        current_time = time.time()
        time_elapsed = f' ({time_elapsed_str(start_time, current_time)})'
    else:
        time_elapsed = ''
    
    if n == 0:
        progress = 0 #prints 0% at start
        time_elapsed = ''
    
    if n == total - 1:
        progress = 100

    int_percent = int(100*n/total)
    
    if int(100*(n - 1)/total) != int_percent:
        if int_percent in np.arange(resolution, 100, resolution):
            progress = int_percent
    
    if progress is not None:
        indent = '  '*indent
        print(f'{indent}{progress}%{time_elapsed}')

def print_end():
    rand_t = '\t' * randint(0, 12)
    rand_n = '\n' * randint(1, 5)

    print(f"{rand_t}{rand_n}{' ' * randint(0, 4)}v gud")
    print(f"{rand_n}{' ' * randint(5, 55)}wow")
    print(f"{rand_n}{' ' * randint(0, 55)}such python")
    print(f"{rand_n}{' ' * randint(5, 55)}wow")
    print(f"{rand_n}{' ' * randint(10, 55)}many spectra")
    print(f"{rand_n}{' ' * randint(5, 55)}wow")
    print(f"{rand_n}{' ' * randint(8, 55)}much calculation")
    print(f"{rand_n}{' ' * randint(5, 55)}wow")
    print('\n' * randint(0, 7))
    print('congration you done it')

def time_elapsed_str(start_time, end_time):
    '''
    Converts time value from seconds to h min s
    '''
    time_elapsed = end_time - start_time

    hours = int(time_elapsed//3600)
    mins = int((time_elapsed % 3600)//60)
    secs = round(time_elapsed % 60, 1)

    if hours == 0 and mins == 0:
        return f'{secs} s'

    if hours == 0:
        return f'{mins} min, {secs} s'

    return f'{hours} h, {mins} min, {secs} s'

class Particle_Track_Analyser:
    '''
    Class for extracting and pre-processing raw particle track data, ready for further analyses
    This is effectively the new version of nplab.analysis.NPoM_DF_Analysis.Condense_DF_Spectra
    '''
    def __init__(self, raw_h5_filename = None, output_filename_format = None, output_filename = None, output_group_name = 'All_Particles',
                 scan_name_format = 'ParticleScannerScan_', main_scan_name = None, consolidate_scans = False,
                 particle_name_format = 'Particle_', sers_name_format = 'lab.kinetic_SERS_',
                 z_scan_name_format = 'lab.z_scan_', df_name_format = 'df_spectrum_', pl_name_format = None, 
                 df = True, pl = False, sers = True, imgs = False, 
                 df_x_min = 450, df_x_max = 900, np_size = 80,
                 **kwargs):

        if raw_h5_filename is None:
            print('Locating raw data file')
            raw_h5_filename = find_h5_file(most_recent = False, **kwargs)

        self.raw_h5_filename = raw_h5_filename

        self.scan_name_format = scan_name_format
        self.main_scan_name = main_scan_name
        self.output_group_name = output_group_name

        self.particle_name_format = particle_name_format
        self.consolidate_scans = consolidate_scans

        self.z_scan_name_format = z_scan_name_format
        self.df_name_format = df_name_format

        self.sers_name_format = sers_name_format
        self.pl_name_format = pl_name_format

        self.df = df
        self.pl = pl
        self.sers = sers
        self.imgs = imgs

        self.df_x_min = df_x_min
        self.df_x_max = df_x_max
        self.np_size = np_size

        if consolidate_scans == True and main_scan_name is not None:
            print(f'WARNING: consolidate_scans = True and data from all {scan_name_format} groups will therefore be consolidated')
            print(f'If you want to only extract data from your chosen group ({main_scan_name}) please set consolidate_scans = False (default value) when initialising Particle_Track_Datafile object ')

        self.get_particle_paths()

        if output_filename is None:
            if output_filename_format is None:
                output_filename_format = f'{self.raw_h5_filename.split(".")[0]}_Output'

            self.output_filename = generate_filename(output_filename_format, **kwargs)
        else:
            self.output_filename = output_filename
            with h5py.File(self.output_filename, 'r') as F:
                self.output_particle_numbers = sorted([int(i.split(self.particle_name_format)[-1]) for i in F[self.output_group_name].keys()])               
                self.output_particle_names = [f'{self.particle_name_format}{i}' for i in self.output_particle_numbers]
                self.first_particle = self.output_particle_numbers[0]
                self.last_particle = self.output_particle_numbers[-1]
                df_names = set()

                for particle_name in self.output_particle_names:
                   df_names.update({i for i in F[self.output_group_name][particle_name].keys() if i.startswith(self.df_name_format)})

                self.df_names = sorted(df_names, key = lambda i: int(i.split(self.df_name_format)[-1]))

    def get_particle_paths(self):
        '''
        Collects paths to all particle data groups
        '''
        with h5py.File(self.raw_h5_filename, 'r') as F:
            self.particle_scan_names = [group_name for group_name in F.keys() 
                                        if group_name.startswith(self.scan_name_format)]
            
            assert len(self.particle_scan_names) > 0, f'No groups found with naming format "{self.scan_name_format}" in {self.raw_h5_filename}. Please specify a different name format'
            
            all_particle_paths = []

            if self.consolidate_scans == True:
                self.particle_scan_names = sorted(self.particle_scan_names, 
                                                  key = lambda name: int(name.split(self.scan_name_format)[-1]))
            else:
                if self.main_scan_name is None:
                    self.main_scan_name = sorted(self.particle_scan_names, 
                                                 key = lambda name: len(F[name]))[-1]

                self.particle_scan_names = [self.main_scan_name]

            for scan_name in self.particle_scan_names:
                particle_scan = F[scan_name]
                particle_group_names = sorted([name for name in particle_scan.keys() 
                                               if name.startswith(self.particle_name_format)],
                                              key = lambda name: int(name.split(self.particle_name_format)[-1]))

                if len(particle_group_names) == 0:
                    print(f'No particles found in {scan_name}')

                for group_name in particle_group_names:
                    all_particle_paths.append(f'{scan_name}/{group_name}')

            assert len(all_particle_paths) > 0, f'No {self.particle_name_format} groups found in any {self.scan_name_format} scan group in {self.raw_h5_filename}'
            
            self.all_particle_paths = all_particle_paths

    def condense_z_scans(self, plot = False, print_progress = True, flag_n = 50, first = 0, last = 0, 
                         cosmic_ray_removal = True, **kwargs):
        '''
        Finds all z_scans in the particle groups specified by self.all_particle_paths
        Condenses them into 1D DF spectra
        Writes them to output file for later analysis
        '''
        print(f'Condensing z-scans and exporting to {self.output_filename}')
        start_time = time.time()
        n_misaligned = 0

        if last == 0 or last > len(self.all_particle_paths):
            last = len(self.all_particle_paths)

        self.first_particle = first
        self.last_particle = last

        n_particles = len(self.all_particle_paths[first:last])

        if n_particles > 1000:
            print(f'  About to condense {n_particles} z-scans - this might take a while...')

        self.output_particle_names = []
        self.output_particle_numbers = []
        data_found = False

        with h5py.File(self.raw_h5_filename, 'r') as F:
            with h5py.File(self.output_filename, 'a') as G:
                all_particles_group = G.create_group(self.output_group_name)
                misaligned_particles = []

                self.z_scan_names = set()
                self.df_names = set()

                for n, particle_path in enumerate(self.all_particle_paths[first:last], first):
                    percent_progress(n - first, n_particles, start_time = start_time, indent = 2)

                    old_particle_group = F[particle_path]
                    z_scan_dset_names = [name for name in old_particle_group.keys() 
                                         if name.startswith(self.z_scan_name_format)]
                    
                    if len(z_scan_dset_names) == 0:
                        print(f'No {self.z_scan_name_format} dataset found in {particle_path}')
                        continue

                    new_particle_name = f'{self.particle_name_format}{n}'
                    self.output_particle_names.append(new_particle_name)
                    self.output_particle_numbers.append(n)

                    new_particle_group = all_particles_group.create_group(new_particle_name)
                    new_particle_group.attrs.update(old_particle_group.attrs)
                    new_particle_group.attrs['original_path'] = particle_path

                    for z_scan_dset_name in z_scan_dset_names:
                        self.z_scan_names.add(z_scan_dset_name)

                        spec_n = z_scan_dset_name.split(self.z_scan_name_format)[-1]
                        df_spec_name = f'{self.df_name_format}{spec_n}'
                        self.df_names.add(df_spec_name)

                        z_scan_dset = old_particle_group[z_scan_dset_name]
                        z_scan = dpt.NPoM_DF_Z_Scan(z_scan_dset, plot = plot, particle_name = new_particle_name, **kwargs)

                        if z_scan.aligned == False:
                            misaligned_particles.append(n)
                            n_misaligned += 1
                            if print_progress == True:
                                if n_misaligned <= flag_n:                                 
                                    if self.consolidate_scans == True:
                                        p_name = particle_path
                                    else:
                                        p_name = particle_path.split('/')[-1]
                                    print(f'    Warning: {p_name} not focused/aligned correctly')

                                elif n_misaligned == flag_n + 1:
                                    print(f"\nMore than {flag_n} dodgy z-scans found; assume there are more")

                        z_scan.condense_z_scan(print_progress = print_progress, cosmic_ray_removal = cosmic_ray_removal, **kwargs)

                        x_df = z_scan.x
                        y_df = z_scan.df_spectrum

                        df_dset = new_particle_group.create_dataset(df_spec_name, data = y_df)
                        df_dset.attrs.update(z_scan_dset.attrs)
                        df_dset.attrs['z_stack_centroids'] = z_scan.z_profile
                        df_dset.attrs['aligned'] = z_scan.aligned
                        df_dset.attrs['wavelengths'] = x_df
                        df_dset.attrs['cosmic_rays_removed'] = cosmic_ray_removal

                        if 'wavelengths' not in all_particles_group.attrs.keys():
                            self.x_df = x_df

                        assert all(self.x_df == x_df), f'wavelength axis of {particle_path}/{z_scan_dset_name} does not match those of preceeding datasets'

                assert len(self.output_particle_names) > 0, f'No {self.z_scan_name_format} data found in any {self.particle_name_format} group in any {self.scan_name_format} group in {self.raw_h5_filename}'
                
                misaligned_particles = np.array(misaligned_particles)
                n_misaligned = len(misaligned_particles)

                all_particles_group.attrs['misaligned_particles'] = misaligned_particles
                all_particles_group.attrs['n_misaligned'] = n_misaligned
                all_particles_group.attrs['%_misaligned'] = round(100*n_misaligned/n_particles, 2)
                all_particles_group.attrs['cosmic_rays_removed'] = cosmic_ray_removal   
                all_particles_group.attrs['df_wavelengths'] = self.x_df             

                self.z_scan_names = sorted(self.z_scan_names, key = lambda i: int(i.split(self.z_scan_name_format)[-1]))
                self.df_names = sorted(self.df_names, key = lambda i: int(i.split(self.df_name_format)[-1]))

        end_time = time.time()
        time_elapsed = time_elapsed_str(start_time, end_time)

        if first == 0 and last == len(self.all_particle_paths):
            print(f'\nAll {n_particles} z-scans condensed and exported in {time_elapsed}')
        else:
            print(f'\n{n_particles} z-scans ({first} to {last}) condensed and exported in {time_elapsed}')

    def extract_pl_spectra(self):
        pass

    def plot_init_stack(self, **kwargs):
        assert len(self.df_names) > 0, 'No DF data found'

        with h5py.File(self.output_filename, 'r') as F:
            for df_name in self.df_names:
                x = self.x_df
                spectra = np.array([F[self.output_group_name][group_name].get(df_name, np.zeros(len(x))) for group_name in self.output_particle_names])

                x, Y = spt.truncate_spectrum(self.x_df, spectra, self.df_x_min, self.df_x_max)
                
                stack = spt.Timescan(x, Y)
                title = f'Initial {df_name} stack'
                img_name = f'{title}.png'
                stack.plot_timescan(figsize = (7, 7), title = title, img_name = img_name, **kwargs)

    def fit_all_df(self, first = 0, last = 0, multi_peak_fit = False, **kwargs):
        with h5py.File(self.output_filename, 'a') as F:
            all_particles_group = F[self.output_group_name]

            if first < self.first_particle:
                if first != 0:
                    print(f'Warning: data starts with {self.particle_name_format}{self.first_particle}')

                first = self.first_particle

            if last == 0:
                last = self.last_particle

            elif last > self.last_particle:
                print(f'Warning: data only goes up to {self.particle_name_format}{self.first_particle}')
                last = self.last_particle

            particle_group_names = self.output_particle_names

            if first != self.first_particle:
                start_index = particle_group_names.index(f'{self.particle_name_format}{first}')
                particle_group_names = particle_group_names[start_index:]

            if last != self.last_particle:
                end_index = particle_group_names.index(f'{self.particle_name_format}{last}')
                particle_group_names = particle_group_names[:end_index]

            n_particles = len(particle_group_names)

            if n_particles > 1000:
                print(f'  About to analyse {n_particles} DF spectra - this might take a while...')

            start_time = time.time()

            for n, particle_group_name in enumerate(particle_group_names):
                percent_progress(n, n_particles, start_time = start_time)

                particle_n = int(particle_group_name.split(self.particle_name_format)[-1])
                particle_group = all_particles_group[particle_group_name]

                for df_name in self.df_names:
                    df_dsets = [i for i in particle_group.items() if i[0].startswith(self.df_name_format)]
                    df_dsets = sorted(df_dsets, key = lambda i: int(i[0].split(self.df_name_format)[-1]))

                if len(df_dsets) == 0:
                    print(f'No {self.df_name_format} dataset found in {group_name}')

                for df_name, df_dset in df_dsets:
                    df_spectrum = dpt.NPoM_DF_Spectrum(df_dset, particle_name = particle_group_name, name = df_name, 
                                                       np_size = self.np_size, x_min = self.df_x_min, x_max = self.df_x_max,
                                                       **kwargs)
                    df_spectrum.test_if_npom(**kwargs)
                    df_spectrum.plot_df()

                    if multi_peak_fit == True:
                        df_spectrum.multi_peak_fit(**kwargs)

                    else:
                        '''
                        !!! find_main_peaks function instead
                        '''
                        pass

    def do_stats(self, **kwargs):
        pass

    def plot_histogram(self, **kwargs):
        pass

class NPoM_DF_Histogram:
    def __init__(self, **kwargs):
        pass
