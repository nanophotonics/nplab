import sys
from nplab.instrument.stage.PyAPT import APTMotor
from nplab.instrument.stage import Stage, StageUI
import json

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
			self.mbAbs(pos-self.zero_pos)	
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

	def set_zero(pos=None):
		if pos == None:
			self.zero_pos = self.getPos(true_angle=True)
		else:
			self.zero_pos = pos
		return

	def get_zero():
		return self.zero_pos


class Thorlabs_NR360SM_UI(QtWidgets.QWidget, UiTools):

	def __init__(self,stage, parent=None,debug = False, verbose = False):
		if not isinstance(card, Thorlabs_NR360SM):
			raise ValueError("Object is not an instnace of the Thorlabs_NR360SM Stage")
		super(Thorlabs_NR360SM_UI, self).__init__()
		self.stage = stage
		self.parent = parent
		self.debug = debug
		self.verbose = verbose

		#TODO - make .ui file
		uic.loadUi(os.path.join(os.path.dirname(__file__), 'thorlabs_nr360sm.ui'), self)

		self.new_angle_textbox.textChanged.connect(self.set_new_angle)
		self.rotation_speed_textbox.textChanged.connect(self.set_rotation_speed)
		self.save_config_textbox.textChanged.connect(self.set_save_config_path)
		self.load_config_textbox.textChanged.connect(self.set_load_config_path)
		#TODO - direction - bind to dropdown
		self.zero_button.clicked.connect(self.set_zero)
		self.move_button.clicked.connect(self.move)
		self.save_config_button.clicked.connect(self.save_config)
		self.load_config_button.clicked.connect(self.load_config)
		
		self.set_rotation_speed()
		self.set_new_angle()
		self.set_save_config_path()
		self.set_load_config_path()
		self.set_direction()

	def set_new_angle(self):

		try:
			self.new_angle = float(self.new_angle_textbox.text())
		except:
			print "Unable to set new angle"
		return 

	def set_rotation_speed(self):
		try:
			self.rotation_speed = float(self.rotation_speed_textbox.text())
		except:
			print "Unable to set new rotation speed"
		return 

	def set_direction(self):
		#TODO - set rotation direction
		pass 

	def set_zero(self):
		self.stage.set_zero()
		#TODO: set current angle textbox to zero
		return 

	def move(self):
		self.stage.move(self.new_angle)
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
		try:
			with open(self.save_path,'r') as f:
				config = self.get_config()
				json.dumps(config)
		except, Exception e:
			print "Failed saving config to {}".format(self.save_path)
			print e

		return 

	def load_config(self):
		try:
			with open(self.load_path,'r') as f:
				config = json.loads(f.read())
				self.set_config(config)
		except, Exception e:
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


if __name__ == "__main__":
	import sys
	from nplab.utils.gui import get_qt_app
	s = Thorlabs_NR360SM(SerialNum=90810016,HWType=22)
	app = get_qt_app()
	ui = s.get_qt_ui()
	ui.show()
	sys.exit(app.exec_())
