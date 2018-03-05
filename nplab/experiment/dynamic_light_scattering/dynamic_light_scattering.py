from nplab.utils import gui_generator
import matplotlib 
matplotlib.use('Qt4Agg')
from nplab.instrument.electronics.adlink9812 import Adlink9812, Adlink9812UI
from nplab import datafile
from nplab.utils.gui_generator import GuiGenerator
from nplab.utils.gui import *
from nplab.ui.ui_tools import UiTools
import nplab.experiment.dynamic_light_scattering as dls
import os
app = get_qt_app()
daq_card = Adlink9812("C:\ADLINK\PCIS-DASK\Lib\PCI-Dask64.dll",debug=False)
daq_card_ui = Adlink9812UI(card=daq_card,debug = False)

instruments = {"adlink9812": daq_card}
gui = GuiGenerator(instrument_dict=instruments, dock_settings_path=os.path.dirname(dls.__file__)+"/experiment_ui.npy", scripts_path=None, working_directory="~")
app.exec_()