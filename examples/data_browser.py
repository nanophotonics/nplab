# -*- coding: utf-8 -*-
"""
This is a very simple script that pops up a data browser for one file.
"""

import nplab.datafile
import nplab.ui.hdf5_browser as browser
from nplab.utils.gui import get_qt_app

if __name__ == "__main__":
    df = nplab.current_datafile()
    df.show_gui(blocking=True)
    nplab.current_datafile().close()