import numpy as np 
import nplab.instrument.serial_instrument as serial 

class AOTF(serial.SerialInstrument):

	termination_character = "\n"
	termination_line = "END"

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
		self.set_default_calibration()
		
		# self.aotf_off()
		r = self.query("dau en")
		print "Daughter Board control enable, response:",r
		# self.query("dau dac * 16383")


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
		print "AOTF.set_amplitude:", response
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
		assert(float(wavelength) >= 450.0 and float(wavelength) <= 690.0), "Channel wavelength in range 450.0-690.0"
		command = "dds w {0} {1:.1f}".format(channel,wavelength) #Notation: :.1f - show 'wavelength' to 1 float ('f') point places
		response = self.query(command)
		print "AOTF.set_wavelength:", response
		return 

	def set_frequency(self,channel,frequency):
		#Note: frequency in MHz?
		assert(int(channel) >= 0 and int(channel) <= 7), "Channel index in range 0-7"
		command = "dds f {0} {1:6f}".format(int(channel),frequency) #Notation: :.6f - show 'frequency' to 6 float ('f') point places


	def set_default_calibration(self):
		'''
		Function AOTF_Tune()           // sets up tuning parameters for this AOTF
			AOTF_Write("cal tuning 0 397.46"); AOTF_Read()
			AOTF_Write("cal tuning 1 -1.2232"); AOTF_Read()
			AOTF_Write("cal tuning 2 1.46"); AOTF_Read()
			End
		'''
		return
		#LOADING THIS CALIBRATION MAKES THE AOTF STOP WORKING???? 
		r = self.query("cal tuning 0 397.46")
		print "Calibration step1:",r
		r = self.query("cal tuning 1 -1.2232")
		print "Calibration step2:",r
		r = self.query("cal tuning 2 1.46")
		print "Calibration step3:",r
		r = self.query("cal save")
		print "Calibration step4:",r


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

#SuperContinuum Color Modulation:
#	MIN: mod dac * 0
#	MAX: mod dac * 16383


if __name__ == "__main__":
	from nplab.instrument.light_sources.fianium import Fianium
	f = Fianium("COM4")

	f.get_dac()
	f.set_dac(600)

	from nplab.instrument.filters.aotf import AOTF
	a = AOTF("COM7")
	a.enable_channel_by_wavelength(1,633.0,16383)
	