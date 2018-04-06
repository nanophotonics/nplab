import sys, numpy as np
from nplab.instrument.stage.PyAPT import APTMotor
from nplab.instrument.stage import Stage, StageUI
import json
from nplab.utils.gui import *
from nplab.ui.ui_tools import *

class Thorlabs_NR360SM(Stage,APTMotor):


	def __init__(self,SerialNum,HWType=22):
		Stage.__init__(self,unit="u")
		APTMotor.__init__(self,SerialNum=SerialNum, HWTYPE=HWType)
		self.axis_names=["deg"]
		self.zero_pos = 0.0
		self.serial_num = SerialNum

	def move(self,pos,axis=None,relative=False):

		if relative == True:
			print "Relative"
			self.mbRel(pos)
		else:
			if abs(pos) > 360.0:
				pos = pos - 360.0*(int(pos)/360) #floating point modulo arithmetic, mod 360.0
			self.mbAbs(pos+self.zero_pos)	
		return

	def __del__(self):
		self.cleanUpAPT()

	def get_position(self,axis=None,true_angle=False):
		
		#if interested in true angle reported by the stage
		if true_angle == True:
			return [self.getPos()]
		#if interested in angle relative to current zero of device
		else:
			return [self.getPos()-self.zero_pos]

	def set_zero(self,pos=None):
		if pos == None:
			self.zero_pos = self.get_position(true_angle=True)[0]
		else:
			self.zero_pos = pos
		return

	def get_zero(self):
		return self.zero_pos

	def stop(self):
		


class Thorlabs_NR360SM_UI(QtWidgets.QWidget, UiTools):


	def __init__(self,stage, parent=None,debug = False, verbose = False):
		if not isinstance(stage, Thorlabs_NR360SM):
			raise ValueError("Object is not an instance of the Thorlabs_NR360SM Stage")
		super(Thorlabs_NR360SM_UI, self).__init__()
		self.stage = stage
		self.parent = parent
		self.debug = debug
		self.verbose = verbose

		#TODO - make .ui file
		uic.loadUi(os.path.join(os.path.dirname(__file__), 'thorlabs_nr360sm.ui'), self)


		print self.__dict__.keys()
		
		#set values in the textboxes - for user information
		self.serial_num_textbox.setText(str(self.stage.serial_num))
		self.set_current_angle()

		self.new_angle_textbox.textChanged.connect(self.set_new_angle)
		self.rotation_speed_textbox.textChanged.connect(self.set_rotation_speed)
		self.save_config_textbox.textChanged.connect(self.set_save_config_path)
		self.load_config_textbox.textChanged.connect(self.set_load_config_path)
		self.zero_button.clicked.connect(self.set_zero)
		self.move_button.clicked.connect(self.move)
		self.save_config_button.clicked.connect(self.save_config)
		self.load_config_button.clicked.connect(self.load_config)
		
		self.stop_button.clicked.connect(self.stop)

		self.set_rotation_speed()
		self.set_new_angle()
		self.set_save_config_path()
		self.set_load_config_path()

	def set_new_angle(self):

		try:
			self.new_angle = float(self.new_angle_textbox.text())
		except:
			print "Unable to set new angle"
		return 

	def set_rotation_speed(self):
		try:
			self.rotation_speed = float(self.rotation_speed_textbox.text())
			if self.rotation_speed > 20.0:
				print "Thorlabs_NR360SM_UI.set_rotation_speed says: Rotating speed too high - wouldn't want to break the stage? - Not changing velocity"
				return
			else:
				self.stage.setVel(self.rotation_speed)
				return
		except:
			print "Thorlabs_NR360SM_UI.set_rotation_speed: Unable to set new rotation speed"
		return 

	def set_zero(self):
		self.stage.set_zero()
		self.set_current_angle() #update current angle textbox
		#TODO: set current angle textbox to zero
		return 

	def move(self):
		self.stage.move(self.new_angle)
		self.set_current_angle()
		return

	def stop(self):
		self.stage.stop()
		self.set_current_angle()
		return 		

	def set_save_config_path(self):
		rel_path = self.save_config_textbox.text()
		self.save_path = os.path.abspath(rel_path)
		return 

	def set_load_config_path(self):
		rel_path = self.load_config_textbox.text()
		self.load_path = os.path.abspath(rel_path)
 		return 

	def save_config(self):
		print "Saving CONFIG!"
		return 
		try:
			with open(self.save_path,'r') as f:
				config = self.get_config()
				json.dumps(config)
		except Exception, e:
			print "Failed saving config to {}".format(self.save_path)
			print e

		return 

	def load_config(self):
		print "Loading CONFIG!"
		return 
		try:
			with open(self.load_path,'r') as f:
				config = json.loads(f.read())
				self.set_config(config)
		except Exception, e:
			print "Failed loading config from {}".format(self.load_path)
			print e
		return  

	def get_config(self):

		config = dict()
		config.update({"zero":float(self.stage.zero_pos)})
		config.update({"current_angle":float(self.stage.getPos())})
		config.update({"rotation_speed":float(self.rotation_speed)})
		config.update({"direction":"TODO"})
		config.update({"save_path":self.save_path})
		config.update({"load_path":self.load_path})

		#get configuration for the stage and the parameters, return as JSON
		return config
	
	def set_config(self,config):

		self.stage.zero_pos = config["zero"]
		self.stage.move(float(config["current_angle"]))
		#set rotation speed textbox
		#set direction dropdown 
		#set save_path_textbox
		#set load_path_textbox
		return 

	def set_current_angle(self):
		self.current_angle_textbox.setText(str(self.stage.get_position()[0]))


if __name__ == "__main__":
	import sys
	from nplab.utils.gui import get_qt_app
	s = Thorlabs_NR360SM(SerialNum=90810016,HWType=22)
	# s.move(,relative=True)
	app = get_qt_app()
	ui = Thorlabs_NR360SM_UI(stage=s)

	ui.show()
	sys.exit(app.exec_())