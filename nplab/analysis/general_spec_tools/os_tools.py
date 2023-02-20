# -*- coding: utf-8 -*-
'''
Created on 2023-02-10
@author: car72

Module with basic functions for file & folder navigation and manipulation

'''

import os
import re
from IPython.utils import io

class FileNotFoundError(Exception):
    pass

def format_matches(filename, name_format, extension = ['h5', 'hdf5'], exclude = None):
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
        matches = filename.startswith(name_format) 

        if exclude is not None:
            matches = matches and exclude not in filename

        return matches

def find_h5_file(root_dir = None, most_recent = True, name_format = 'date', extension = 'h5', exclude = None, print_progress = True, **kwargs):
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
            print(f'\tH5 file {h5_file} found\n')
        else:
            raise FileNotFoundError(f'\tH5 file with name format "{name_format}" not found in {os.getcwd()}\n')
    
    return h5_file

def generate_filename(filename, extension = '.h5', print_progress = True, **kwargs):
    '''Auto-increments new filename if file exists in current directory'''
    with io.capture_output(not print_progress):#suppresses console printing if print_progress == False
        print('\nDeciding filename...')
        output_filename = filename

        if not extension.startswith('.'):
            extension = '.' + extension

        if not filename.endswith(extension):
            output_filename = f'{filename}{extension}'

        n = 0
        while output_filename in os.listdir('.'):
            n += 1
            output_filename = f'{filename}_{n}{extension}'
            
            print(f'\t{filename}_{n - 1}{extension} already exists')
        print(f'\tNew file will be called {output_filename}\n')

    return output_filename