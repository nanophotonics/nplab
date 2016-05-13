# -*- coding: utf-8 -*-
"""
This is a very simple script that pops up a data browser for one file.
"""

import nplab.datafile
import nplab.ui.hdf5_browser as browser
from nplab.utils.gui import get_qt_app

if __name__ == "__main__":
    nplab.datafile.set_current(r"/Users/rwb27/np/projects/reflective_rig/20150825_tao/2015-08-25.h5", mode="r")
    app = get_qt_app()
    v = browser.HDF5ItemViewer()
    v.show()
    df = nplab.current_datafile()
    v.data = df['SpectrometerSaver/measurement_0/image']
    nplab.current_datafile().show_gui()
    
    #nplab.current_datafile().close()