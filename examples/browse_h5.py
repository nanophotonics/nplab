# -*- coding: utf-8 -*-
"""
This is a very simple script that pops up a data browser for one file.
"""
from __future__ import print_function

import nplab.datafile
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Browse the contents of an HDF5 file")
    parser.add_argument('filename', help="Path to the HDF5 file you want to browse.")
    args = parser.parse_args()
    try:
        nplab.datafile.set_current(args.filename, mode="r")
    except:
        print("problem opening file from command line, popping up dialogue")
    df = nplab.current_datafile(mode="r")
    df.show_gui()
    nplab.close_current_datafile()