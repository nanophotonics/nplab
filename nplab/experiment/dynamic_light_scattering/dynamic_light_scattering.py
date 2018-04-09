from nplab.utils import gui_generator
import matplotlib 
matplotlib.use('Qt4Agg')
from nplab.instrument import Instrument
from nplab.instrument.electronics.adlink9812 import Adlink9812, Adlink9812UI
from nplab.instrument.light_sources.fianium import Fianium
from nplab import datafile
from nplab.utils.gui_generator import GuiGenerator
from nplab.utils.gui import *
from nplab.ui.ui_tools import UiTools
import nplab.experiment.dynamic_light_scattering as dls
import os
import json

class DynamicLightScattering(Instrument):

	DEVICE_KEYS = ["adc", "sample_rotation_stage"]

	def __init__(self, instruments):
		self.instruments = instruments
		super(DynamicLightScattering,self).__init__()
		self.ui = None
		for k in instruments.keys():
			assert(k in DynamicLightScattering.DEVICE_KEYS)

		self.adc = instruments["adc"]
		self.adc_ui = instruments["adc"].get_qt_ui()
		self.sample_rotation_stage = None
		self.sample_rotation_stage_ui = None

		#check boxes for the settings
		self.checkboxes = {
		"raw":self.adc_ui.raw_checkbox,
		"difference":self.adc_ui.difference_checkbox,
		"binning":self.adc_ui.binning_checkbox,
		"correlate":self.adc_ui.correlate_checkbox,
		"average":self.adc_ui.average_checkbox,
		"save":self.adc_ui.save_checkbox,
		"plot":self.adc_ui.plot_checkbox,
		}

		self.textboxes = {
		"sample_count": self.adc_ui.sample_count_textbox,
		"series_name": self.adc_ui.series_name_textbox,
		"binning_size": self.adc_ui.binning_textbox,
		"average_count": self.adc_ui.average_textbox
		}
		self.fields = dict()

		if "sample_rotation_stage" in instruments.keys():
			self.sample_rotation_stage = instruments["sample_rotation_stage"]
			self.sample_rotation_stage_ui = self.sample_rotation_stage.get_qt_ui()

			self.textboxes.update({"new_angle" : self.sample_rotation_stage_ui.new_angle_textbox})
			# self.textboxes.update({"zero_angle": self.sample_rotation_stage.})
			self.textboxes.update({"rotation_speed": self.sample_rotation_stage_ui.rotation_speed_textbox})
			self.fields.update({"zero_angle",self.sample_rotation_stage.zero})

		checkbox_keys = self.checkboxes.keys()
		textbox_keys = self.textboxes.keys()
		field_keys = self.fields.keys()

		#assert the keys in dict are UNIQUE - otherwise we can't guarantee same parameters are set
		assert(len(list(set(checkbox_keys).intersection(set(textbox_keys))))==0)
		assert(len(list(set(checkbox_keys).intersection(set(field_keys))))==0)
		assert(len(list(set(field_keys).intersection(set(textbox_keys))))==0)
		print "KEYS", checkbox_keys+textbox_keys+field_keys

	#WHY DOES THIS WORK ONLY HERE - ELSEWHERE THIS ISNT NEEDED???
	def get_qt_ui(self):
		if self.ui is None:
			self.ui = DynamicLightScatteringUI(experiment=self)
		return self.ui

	#setters for checkboxes, textboxes, and fields
	def set_checkboxes(self,settings):
		for s in settings.keys():
			if s in self.checkboxes.keys():
				print "set_checkboxes",s
				on = bool(settings[s])
				self.checkboxes[s].setChecked(on)
				
	def set_textboxes(self,settings):
		for s in settings.keys():
			if s in self.textboxes.keys():
				print "set_textboxes",s
				self.textboxes[s].setText(settings[s])
		return

	def set_fields(self,settings):
		for s in settings.keys():
			if s in self.fields.keys():
				print "set_fields",s
				self.fields[s] = settings[s]

	def run_experiment(self,path,debug=False):
		self.log("PATH"+ str(path))
		f = file(path,'r')
		steps = json.loads(f.read())
		self.log("STAGES:"+str(len(steps)))
		for settings in steps:
			self.set_checkboxes(settings)
			self.set_textboxes(settings)
			self.set_fields(settings)

			if self.sample_rotation_stage_ui is not None:
				self.sample_rotation_stage_ui.move()
			
			self.adc_ui.threaded_capture()
			self.adc_ui.capture_thread.join()
		
class DynamicLightScatteringUI(QtWidgets.QWidget, UiTools):
	def __init__(self,experiment, parent=None,debug = False,verbose=False):
		if not isinstance(experiment, DynamicLightScattering):
			raise ValueError("Object is not an instance of the DynamicLightScattering")
		super(DynamicLightScatteringUI, self).__init__()
		self.experiment = experiment
		uic.loadUi(os.path.join(os.path.dirname(__file__), 'dynamic_light_scattering_experiment.ui'), self)
	
		self.run_config_textbox.textChanged.connect(self.set_run_config_path)
		self.run_config_button.clicked.connect(self.run_experiment)


	def run_experiment(self):
		try:
			self.experiment.run_experiment(self.run_path)
		except:
			self.experiment.log("Error when running experiment - have you written the path?",level="error")
		return

	def set_run_config_path(self):
		self.run_path = self.run_config_textbox.text()




app = get_qt_app()
adc = Adlink9812("C:\ADLINK\PCIS-DASK\Lib\PCI-Dask64.dll",debug=True)

experiment = DynamicLightScattering(instruments = {"adc":adc})
instruments = {"adlink9812": adc, "configmanager":experiment}
gui = GuiGenerator(instrument_dict=instruments, dock_settings_path=os.path.join(os.path.dirname(__file__),"experiment_ui.npy"), scripts_path=None, working_directory="~")
app.exec_()