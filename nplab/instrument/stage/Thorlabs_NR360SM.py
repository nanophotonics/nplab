from __future__ import print_function
from builtins import str
import sys, numpy as np
from nplab.instrument.stage import Stage, StageUI
from nplab.instrument.stage.apt_vcp_motor import APT_VCP_motor
import json,struct
from nplab.utils.gui import *
from nplab.ui.ui_tools import *
import threading
import time
from qtpy import QtCore


DEBUG = False 
class Thorlabs_NR360SM(APT_VCP_motor):

	def __init__(self,port='/dev/ttyUSB1', source=0x01, destination=0x50):
		Stage.__init__(self,unit="u")
		APT_VCP_motor.__init__(self,port=port,destination=destination,source=source)
		self.axis_names=["x"]
		self.set_channel_state(1,1)
		self.zero_pos = 0.0
		self.ui = None
		print("initialized NR360SM")
		self.set_motion_params()
		# self.get_home_parameters()
		self.set_home_parameters()
		self.get_home_parameters()
		
		# self.get_limit_switch_parameters()
		# self.set_limit_switch_parameters()
		# self.get_limit_switch_parameters()
		


	def set_motion_params(self,velocity=10,acceleration=5,channel=1):
		'''
		Set velocity parameters in units of deg/sec [both for velocity and acceleration]
		'''
		chanIdent = channel
		minVel = 0
		acc = self.convert(acceleration,"acceleration","counts")
		maxVel = self.convert(velocity,"velocity","counts")

		bs = [chanIdent,minVel,acc,maxVel]
		ds = bytearray(struct.pack("<HLLL",*bs))
		self.write(0x0413,param1=0x0E,param2=0x00,data=ds)
		return 

	def set_home_parameters(self,velocity=6,homeAngle=0.1,channel=1,debug= False):
		#1 2 1 28160 469
		chanIdent = channel
		homeDirection = {"forward":1, "reverse":2}
		limitSwitch = {"hardwareReverse":1,"hardwareForward":1}
		homeVel = self.convert(velocity,"velocity","counts")
		offsetDistance = self.convert(homeAngle,"position","counts")

		bs = [chanIdent,homeDirection["reverse"],limitSwitch["hardwareReverse"],homeVel,offsetDistance]
		if debug > 0 or DEBUG == True:
			print("set homing parameters:", bs)
		ds = bytearray(struct.pack("<HHHLl",*bs))
		self.write(0x0440,param1=0x0E,param2=0x00,data=ds)
		return 

	def get_home_parameters(self,channel=1):
		'''
		Set velocity parameters in units of deg/sec [both for velocity and acceleration]
		'''

		resp = self.query(0x0441,param1=channel,param2=0x00)
		data = resp["data"]

		chanIdent, homeDir, limSwitch, homeVel, offsetDistance = struct.unpack("<HHHLl",data)
		print("homing parameters:",chanIdent, homeDir, limSwitch, homeVel, offsetDistance)
		return 
		
	def set_limit_switch_parameters(self):
		bs = [1, 3, 1, 14080, 4693, 1] #parameters loaded from kinesis
		ds = bytearray(struct.pack("<HHHLLH",*bs))
		self.write(0x0423,param1=0x10,param2=0x00,data=ds)
		return
	def get_limit_switch_parameters(self,debug = False):
		resp = self.query(0x0424,param1=0x10,param2=0x00)
		data = resp["data"]
		chanIdent, cwHardLimit, ccwHardLimit, cwSoftLimit, ccwSoftLimit, limitMode = struct.unpack("<HHHLLH",data)
		outp = [chanIdent, cwHardLimit, ccwHardLimit, cwSoftLimit, ccwSoftLimit, limitMode]
		if debug > 0 or DEBUG == True:
			print("get_limit_switch_paraters:", outp)
		return outp
	def get_motion_params(self):
		pass

	def home(self,channel=1):
		self.write(0x0443,channel,0)


	def stop(self,channel=1):
		stopMode = {"immediate":0x01, "profiled":0x02}
		self.write(0x0465,channel,stopMode["profiled"])
		return

	def convert(self, value, from_, to_,debug = False):
		'''for NR360SM stage the conversion is:
		25600 microsteps for 5.4546 degrees
		see page 35 of 359 of Thorlabs programming manual
		configuration applicable to BSC10x stage controllers, newer versions BSC20x may be incompatible
		'''
		count_to_deg = (float(5.4546 )/float(25600)) 	
		deg_to_count = 1.0/count_to_deg

		vel_to_count = 4693.0
		count_to_vel = 1.0/vel_to_count

		acc_to_count = 4693.0
		count_to_acc = 1.0/acc_to_count

		if from_ == "counts" and to_ == "position":
			val = value*count_to_deg
		elif from_ == "position" and to_ == "counts":
			val = int(np.round(value*deg_to_count,decimals=0))
		
		elif from_ == "counts" and to_ == "velocity":
			val = value*count_to_vel
		elif from_ == "velocity" and to_ == "counts" :
			val = int(np.round(value*vel_to_count,decimals=0))
		
		elif from_ == "counts" and to_ == "acceleration":
			val = value*count_to_acc
		elif from_ == "acceleration" and to_ == "counts" :
			val = int(np.round(value*acc_to_count,decimals=0))
		
		if debug > 0 or DEBUG == True:
				print("from_({}):".format(from_),value, "to_({}):".format(to_),val)
		return val

class Thorlabs_NR360SM_UI(QtWidgets.QWidget, UiTools):

	def __init__(self,stage, parent=None,debug = 0):
		if not isinstance(stage, Thorlabs_NR360SM):
			raise ValueError("Object is not an instance of the Thorlabs_NR360SM Stage")
		super(Thorlabs_NR360SM_UI, self).__init__()
		self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)

		self.stage = stage #this is the actual rotation stage
		self.parent = parent
		self.debug =  debug

		uic.loadUi(os.path.join(os.path.dirname(__file__), 'thorlabs_nr360sm.ui'), self)
		self.stop_threads_flag = threading.Event()
		
		self.thread_lock = threading.RLock()
		self.move_thread = None
		self.angle_update_thread = threading.Thread(target=self.set_current_angle)
		self.angle_update_thread.start()


		#Bind GUI widgets to functions
		self.serial_num_textbox.setText(str(self.stage.serial_number))
		self.new_angle_textbox.textChanged.connect(self.set_new_angle)
		self.rotation_speed_textbox.textChanged.connect(self.set_rotation_speed)
		self.angle_lower_bound_textbox.textChanged.connect(self.set_angle_lower_bound)
		self.angle_upper_bound_textbox.textChanged.connect(self.set_angle_upper_bound)

		self.zero_button.clicked.connect(self.set_zero)
		self.move_button.clicked.connect(self.move_stage)
		self.save_config_button.clicked.connect(self.save_config)
		self.load_config_button.clicked.connect(self.load_config)
		self.move_combo_box.currentIndexChanged.connect(self.set_move_type)
		self.stop_button.clicked.connect(self.stop_stage)



		#initialize values
		self.set_rotation_speed()
		self.set_new_angle()
		self.set_move_type()
		self.set_angle_lower_bound()
		self.set_angle_upper_bound()

	#What to do on close
	def closeEvent(self,event):
		if self.debug > 0 or DEBUG == True: print("Widget closed - cleaning up threads")
		self.stop_threads_flag.set()
		self.angle_update_thread.join()
		if self.debug > 0 or DEBUG == True: print("Widget closed - clean up DONE!")
		event.accept()
		return

	def set_angle_lower_bound(self):
		try:
			self.angle_lower_bound = float(self.angle_lower_bound_textbox.text())
		except: 
			self.log("Unable to set angle LOWER bound",level="error")
		return  

	def set_angle_upper_bound(self):
		try:
			self.angle_upper_bound = float(self.angle_upper_bound_textbox.text())
		except: 
			self.log("Unable to set angle UPPER bound",level="error")
		return


	def set_move_type(self):
		self.move_type = self.move_combo_box.currentText()
		assert(self.move_type in ["absolute", "relative"])
		if self.debug > 0 or DEBUG == True: print("Type changed!", self.move_type)


	def set_new_angle(self):
		try:
			self.new_angle = float(self.new_angle_textbox.text())
		except:
			print("Unable to set new angle")
		return 

	def set_rotation_speed(self):
		try:
			self.rotation_speed = float(self.rotation_speed_textbox.text())
			if self.rotation_speed > 20.0:
				print("Thorlabs_NR360SM_UI.set_rotation_speed says: Rotating speed too high - wouldn't want to break the stage? - Not changing velocity")
				return
			else:
				# self.stage.setVel(self.rotation_speed)
				return
		except:
			print("Thorlabs_NR360SM_UI.set_rotation_speed: Unable to set new rotation speed")
		return 

	def set_zero(self):
		self.stage.home()
		#TODO: set current angle textbox to zero
		return 


	def move_stage(self,blocking = False):
		
		#get whether turn is relative
		print("Moving-1",self.new_angle)
		relative = (self.move_type == "relative")
		self.stage.move(pos=self.new_angle, axis="x", relative=relative,block = blocking)	
		return



	def stop_stage(self):
		self.stage.stop()
		self.move_thread=None
		return 		

	def save_config(self):
		#TODO - save configuration JSON file to a given path
		pass 

	def load_config(self):
		#TODO - load configuration JSON file from given path 
		pass 
	

	def set_save_config_path(self):
		rel_path = self.save_config_textbox.text()
		self.save_path = os.path.abspath(rel_path)
		return 

	def set_load_config_path(self):
		rel_path = self.load_config_textbox.text()
		self.load_path = os.path.abspath(rel_path)
 		return
		
	#Updates GUI, in particular the angle - runs in self.angle_update_thread
	def set_current_angle(self):
		while True:
			if self.stop_threads_flag.isSet(): 
				print("self.angle_update_thread : Stopping - self.stop_threads_flag is set!")
				return
			else:
				try:

					pos = float(self.stage.get_position()[0])
					self.current_angle_textbox.setText("{0:4g}".format(pos))
					self.zero_pos_textbox.setText(str(self.stage.zero_pos))
					time.sleep(0.3)
				except:
					pass		

if __name__ == "__main__":
	import sys
	from nplab.utils.gui import get_qt_app
	s = Thorlabs_NR360SM(port='/dev/ttyUSB0', source=0x01, destination=0x11)
	# s.set_limswitchparams()
	# s.set_jog_params()
	# s.move(10,block=True)
	s.home()

	# s.get_motion_parameters()
	# s.identify()
	# print s.destination.keys()
	# s.move(-5.0,relative=True)
	app = get_qt_app()
	ui = Thorlabs_NR360SM_UI(stage=s)
	ui.show()
	sys.exit(app.exec_())