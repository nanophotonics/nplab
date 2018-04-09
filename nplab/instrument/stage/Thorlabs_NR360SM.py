import sys, numpy as np
from nplab.instrument.stage.PyAPT import APTMotor
from nplab.instrument.stage import Stage, StageUI
import json
from nplab.utils.gui import *
from nplab.ui.ui_tools import *
import threading
import time
from qtpy import QtCore

class Thorlabs_NR360SM(Stage,APTMotor):

	def __init__(self,SerialNum,HWType=22):
		Stage.__init__(self,unit="u")
		APTMotor.__init__(self,SerialNum=SerialNum, HWTYPE=HWType)
		self.axis_names=["deg"]
		self.zero_pos = 0.0
		self.serial_num = SerialNum



	def __del__(self):
		self.cleanUpAPT()
	
	'''
	@param true_angle - angle reported by the stage itself
	@zero - zero set by this class

	next_angle = (+zero) (+current) + increment
		(+zero) if true_angle == False
		(+current) if relative == True
		increment - input from user   
	'''

	@staticmethod
	def get_qt_ui_cls():
		return Thorlabs_NR360SM_UI
	def move(self,pos,relative=False,axis=None, true_angle = False):
		next_position = self.get_next_position(pos,relative=relative, true_angle=true_angle)
		self.mbAbs(next_position)
		return

	def get_next_position(self,pos,relative=False, true_angle = False):
		next_position = pos
		if relative == True:
			current_pos = self.get_position(true_angle=true_angle)[0]
			next_position = next_position + current_pos
		return next_position

	def get_position(self,axis=None, true_angle=False):
		
		#if interested in true angle reported by the stage
		if true_angle == True:
			return [self.getPos()]
		#if interested in angle relative to current zero of device
		else:
			#subtract zero from the current position
			relative_angle = self.getPos()-self.zero_pos
			while relative_angle < 0.0:
				relative_angle = relative_angle + 360.0
			while relative_angle > 360.0:
				relative_angle = relative_angle - 360.0 
			return [relative_angle]

	def set_zero(self,pos=None):
		if pos == None:
			self.zero_pos = self.get_position(true_angle=True)[0]
		else:
			self.zero_pos = pos
		return

	def get_zero(self):
		return self.zero_pos

	def stop(self):
		self.stopMove()
		return

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
		self.serial_num_textbox.setText(str(self.stage.serial_num))
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
		if self.debug > 0: print "Widget closed - cleaning up threads"
		self.stop_threads_flag.set()
		self.angle_update_thread.join()
		if self.debug > 0: print "Widget closed - clean up DONE!"
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
			self.angle_upper_bound = float(self.angle_lower_bound_textbox.text())
		except: 
			self.log("Unable to set angle UPPER bound",level="error")
		return


	def set_move_type(self):
		self.move_type = self.move_combo_box.currentText()
		assert(self.move_type in ["absolute", "relative"])
		if self.debug > 0: print "Type changed!", self.move_type


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
		#TODO: set current angle textbox to zero
		return 

	def move_stage(self):
		
		#get whether turn is relative
		relative = (self.move_type == "relative")

		#get true angle that we want to rotate to
		true_next_angle = self.stage.get_next_position(self.next_angle,relative=relative, true_angle=True)
		
		#test if angle is below lower bound - error if so
		if true_next_angle < self.angle_lower_bound:
			self.log("Target angle BELOW anglular LOWER bound",level="error")
			return 
		#test if angle is above upper bound - error if so
		elif true_next_angle > self.angle_upper_bound:
			self.log("Target angle ABOVE anglular UPPER bound",level="error")
		#otherwise - move, if not already moving
		else:
			if isinstance(self.move_thread, threading.Thread) and self.move_thread.is_alive():
				self.stage.log(message="Already moving!", level="info")
				return
			self.move_thread = threading.Thread(target=self.stage.move,args=(self.new_angle,relative))
			self.move_thread.start()
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
				print "self.angle_update_thread : Stopping - self.stop_threads_flag is set!"
				return
			else:
				self.current_angle_textbox.setText(str(self.stage.get_position()[0]))
				self.zero_pos_textbox.setText(str(self.stage.zero_pos))
				time.sleep(0.3)
					

if __name__ == "__main__":
	import sys
	from nplab.utils.gui import get_qt_app
	s = Thorlabs_NR360SM(SerialNum=90810016,HWType=22)
	app = get_qt_app()
	ui = Thorlabs_NR360SM_UI(stage=s)
	ui.show()
	sys.exit(app.exec_())