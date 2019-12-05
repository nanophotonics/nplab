from __future__ import print_function
from builtins import range
import numpy as np 
import nplab.instrument.serial_instrument as serial 
from nplab.ui.ui_tools import *
from nplab.utils.gui import *
import time


class AOTF(serial.SerialInstrument):

	termination_character = "\n"
	termination_line = "\r"

	port_settings = dict(baudrate=38400,bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1, #wait at most one second for a response
                        writeTimeout=1, #similarly, fail if writing takes >1s
                        xonxoff=False, rtscts=False, dsrdtr=False
                    )  

	def __init__(self,port = None):

		#Open communication port
		super(AOTF,self).__init__(port =port)

		'''
		Function AOTF_ModMax()
		AOTF_Write("dau en") # Enable microcontroller to manipulate the Daughter Board controls
		'''
		
		r = self.query("dau en")
		print("Daughter Board control enable, response:",r)
		
		self.set_default_calibration()
		
		# self.aotf_off()
		self.query("dau dac * 16383")


		# Macro AOTF_setup()
		# VDT2/P=COM3 baud=38400, stopbits=1, databits=8, parity=0, echo=0
		# Variable/G AOTFint0=0,AOTFint1=0,AOTFint2=0,AOTFwl0=670,AOTFwl1=570,AOTFwl2=550
		# AOTF_ModMax()
		# AOTF_off()

	
	#TODO:
	''' 
	Function AOTF_chMod(st)
	Variable st
	if (st==1)
		AOTF_Write("dau dis")
		AOTF_Write(dau gain * 72)
	else
		AOTF_Write("dau en")
	endif
	End
	'''

	def set_amplitude(self, channel, amplitude):
		'''
		Function AOTF_Amp(ch,aa)// Sets AOTF channel ch amplitude to aa
			Variable ch, aa
			Nvar AOTFint0,AOTFint1,AOTFint2
			String nm
			aa = (aa>3000? 3000 : aa)
			nm = "dds a "+num2istr(ch)+" "+num2istr(aa)
			if ((ch>=0)&&(ch<8))
			  AOTF_Write(nm)
			  AOTF_Read()
			  if (ch==0)
			    AOTFint0 = aa
			  elseif (ch==1)
			    AOTFint1 = aa
			  elseif (ch==2)
			    AOTFint2 = aa
			  endif
			endif
			End
		'''
		assert(int(channel) >= 0 and int(channel) <= 7), "Channel index in range 0-7"
		assert(int(amplitude) >= 0 and int(amplitude) <= 16383), "Channel amplitude in range 0-16383"
		command = "dds a {0} {1}".format(channel,amplitude)
		response = self.query(command)
		print("AOTF.set_amplitude:", response)
		return

	def set_wavelength(self,channel,wavelength):
		'''
			Function AOTF_Wav(ch,wl)              // Sets AOTF channel ch wavelength to wl
				Variable ch, wl
				Nvar AOTFwl0,AOTFwl1,AOTFwl2
				String nm
				wl = (wl>690? 690 : wl)
				wl = (wl<450? 450 : wl)
				sprintf nm,"dds w %u %3.1f",ch,wl
				if ((ch>=0)&&(ch<8))
				  AOTF_Write(nm)
				  AOTF_Read()

				  if (ch==0)
				    AOTFwl0 = wl
				  elseif (ch==1)
				    AOTFwl1 = wl
				  elseif (ch==2)
				    AOTFwl2 = wl
				  endif
				endif
			End
		'''
		assert(int(channel) >= 0 and int(channel) <= 7), "Channel index in range 0-7"
		assert(float(wavelength) >= 450.0 and float(wavelength) <= 1100.0), "Channel wavelength in range 450.0-690.0"
		command = "dds w {0} {1:.1f}".format(channel,wavelength) #Notation: :.1f - show 'wavelength' to 1 float ('f') point places
		response = self.query(command)
		print("AOTF.set_wavelength:", response)
		return 

	def set_frequency(self,channel,frequency):
		#Note: frequency in MHz?
		assert(int(channel) >= 0 and int(channel) <= 7), "Channel index in range 0-7"
		command = "dds f {0} {1:6f}".format(int(channel),frequency) #Notation: :.6f - show 'frequency' to 6 float ('f') point places
		response = self.query(command)
		print("AOTF.set_frequency:", response)


	def set_default_calibration(self):
		'''
		Function AOTF_Tune()           // sets up tuning parameters for this AOTF
			AOTF_Write("cal tuning 0 397.46"); AOTF_Read()
			AOTF_Write("cal tuning 1 -1.2232"); AOTF_Read()
			AOTF_Write("cal tuning 2 1.46"); AOTF_Read()
			End
		'''

		r = self.query("cal tuning 0 397.46")
		print("Calibration step1:",r)
		r = self.query("cal tuning 1 -1.2232")
		print("Calibration step2:",r)
		r = self.query("cal tuning 2 1.4658e-3")
		print("Calibration step3:",r)
		r = self.query("cal tuning 3 -6.15e-7")
		print("Calibration step4:",r)
		r = self.query("cal save")
		print("Calibration step5:",r)

		return
		#LOADING THIS CALIBRATION MAKES THE AOTF STOP WORKING???? 
		

		'''
		#DEFAULT CALIBRATION FROM AOTF CONTROLLER SOFTWARE
		cal tuning 0 397.46
		* cal tuning 1 -1.2232
		* cal tuning 2 1.4658e-3
		* cal tuning 3 -6.155E-7
		* cal save
		'''
		return 

	def aotf_off(self):
		for c in range(0,8):
			self.set_amplitude(channel=c, amplitude=0)
		return

	def enable_channel_by_frequency(self,channel,frequency,amplitude):
		self.set_frequency(channel,frequency)
		self.set_amplitude(channel,amplitude)

	def enable_channel_by_wavelength(self,channel,wavelength,amplitude):
		self.set_wavelength(channel,wavelength)
		self.set_amplitude(channel,amplitude)

	def disable_channel(self,channel):
		#enabling channel - requires
		self.set_amplitude(channel,0)


class AOTF_UI(QtWidgets.QWidget, UiTools):
	def __init__(self,device, parent=None,debug = False, verbose = False):
		if not isinstance(device, AOTF):
			raise ValueError("Object is not an instance of the AOTF Class")
		super(AOTF_UI, self).__init__()
		
		uic.loadUi(os.path.join(os.path.dirname(__file__), 'aotf.ui'), self)

		#aotf:
		self.aotf = device 
		
		self.wavelength_textboxes = [self.chn1_wl,self.chn2_wl,self.chn3_wl,self.chn4_wl,self.chn5_wl,self.chn6_wl,self.chn7_wl,self.chn8_wl]
		self.power_textboxes = [self.chn1_pwr,self.chn2_pwr,self.chn3_pwr,self.chn4_pwr,self.chn5_pwr,self.chn6_pwr,self.chn7_pwr,self.chn8_pwr]
		self.active = [self.chn1_toggle,self.chn2_toggle,self.chn3_toggle,self.chn4_toggle,self.chn5_toggle,self.chn6_toggle,self.chn7_toggle,self.chn8_toggle]

		for wl in self.wavelength_textboxes:
			wl.textChanged.connect(self.set_wavelength)

		for pwr in self.power_textboxes:
			pwr.textChanged.connect(self.set_power)

		
		self.off_btn.clicked.connect(self.set_off)
		self.on_btn.clicked.connect(self.set_on)
		self.settings = [[0,0],[0,0],[0,0],[0,0],[0,0],[0,0],[0,0],[0,0]]

		self.set_wavelength()
		self.set_power()

	def set_wavelength(self):
		try:
			for i in range(len(self.wavelength_textboxes)):
				wavelength = float(self.wavelength_textboxes[i].text())
				self.settings[i][0] = wavelength
			print(self.settings)
		except ValueError as e:
			print(e)

		return

	def set_power(self):
		try:
			for i in range(len(self.power_textboxes)):
				power = int(self.power_textboxes[i].text())
				self.settings[i][1] = power
		except ValueError as e:
			print(e)
		return

	def set_on(self):
		print(self.settings)
		channel_is_on = [bool(a.isChecked()) for a in self.active]
		print(channel_is_on)
		for i,is_on in enumerate(channel_is_on):
			if is_on == True:
				wl = self.settings[i][0]
				pwr = self.settings[i][1]
				print("wavelength:", wl)
				aotf.enable_channel_by_wavelength(i,wl,pwr)
			else:
				aotf.disable_channel(i)
		return

	def set_off(self):
		self.aotf.aotf_off()
		return 



def make_gui():
	global aotf 
	aotf = AOTF("/dev/ttyUSB2")
	app = get_qt_app()
	ui = AOTF_UI(device=aotf,debug =False)
	ui.show()
	sys.exit(app.exec_())	

def flash_wavelengths(wavelengths,t_sec):
	aotf = AOTF("/dev/ttyUSB2")
	while True:
		for i in range(len(wavelengths)):
			aotf.enable_channel_by_wavelength(i,wavelengths[i],8000)
		time.sleep(t_sec)
		for i in range(len(wavelengths)):
			aotf.disable_channel(i)
		time.sleep(t_sec)
	return 	


def say(text):
	import pyttsx
	engine = pyttsx.init()
	engine.say(text)
	engine.runAndWait()
	return 
def flash_frequency(f):
	aotf = AOTF("/dev/ttyUSB2")
	while True:
		aotf.enable_channel_by_frequency(1,f,8000)
		time.sleep(0.4)
		aotf.disable_channel(1)
		time.sleep(0.4)


def set_frequency(fs):

	aotf = AOTF("/dev/ttyUSB2")
	for i,f in enumerate(fs):
		# aotf.disable_channel(i)
		aotf.enable_channel_by_frequency(i,f,8000)

def scan_frequency(freqs,t):
	aotf = AOTF("/dev/ttyUSB2")
	for f in freqs:
		print("freq:",f)
		aotf.enable_channel_by_frequency(1,f,8000)
		say("{0:.3g} megahertz".format(f))
		say("measure")
		time.sleep(t)
		
		aotf.disable_channel(1)
		time.sleep(t)
	
	return 	


if __name__ == "__main__":
	# time.sleep(10)

	set_frequency([85])
	# for f in range(60,86):
		# set_frequency(f)
		# time.sleep(1)
		# say("{0:.3g} megahertz".format(f))
	# scan_frequency(range(48,86),1)
	# scan_frequency(range(86,95),1)
	# make_gui()
	# flash_wavelengths([690],1)