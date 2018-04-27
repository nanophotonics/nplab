import numpy as np 
import nplab.instrument.serial_instrument as serial 

class AOTF(serial.SerialInstrument):

	port_settings = dict(baudrate=38400,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1, #wait at most one second for a response
                        writeTimeout=1, #similarly, fail if writing takes >1s
                        xonxoff=False, rtscts=False, dsrdtr=False,
                    )
    termination_character = "\n" #: All messages to or from the instrument end with this character.
    termination_line = "END" #: If multi-line responses are recieved, they must end with this string
#


	def __init__(self,port = None):

		#Open communication port
		super(self).__init__(port =port)


		# Macro AOTF_setup()
		# VDT2/P=COM3 baud=38400, stopbits=1, databits=8, parity=0, echo=0
		# Variable/G AOTFint0=0,AOTFint1=0,AOTFint2=0,AOTFwl0=670,AOTFwl1=570,AOTFwl2=550
		# AOTF_ModMax()
		# AOTF_off()

	
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
		assert(int(channel) >= 0 and int(channel) <= 7, "Channel index in range 0-7")
		assert(int(ampltiude) >= 0 and int(amplitude) <= 16383, "Channel amplitude in range 0-16383")
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
		assert(int(channel) >= 0 and int(channel) <= 7, "Channel index in range 0-7")
		assert(float(wavelength) >= 450.0 and float(wavelength) <= 690.0, "Channel wavelength in range 450.0-690.0")
		command = "dds w {0} {1:.1g}}".format(channel,wavelength)
		response - self.query(command)
		print "AOTF.set_wavelength:", response
		return 

	def set_calibration(self):
		'''
		Function AOTF_Tune()           // sets up tuning parameters for this AOTF
			AOTF_Write("cal tuning 0 397.46"); AOTF_Read()
			AOTF_Write("cal tuning 1 -1.2232"); AOTF_Read()
			AOTF_Write("cal tuning 2 1.46"); AOTF_Read()
			End
		'''
		
		r = self.query("cal tuning 0 397.46")
		print "Calibration step1:",r
		r = self.query("cal tuning 1 -1.2232")
		print "Calibration step2:",r
		r = self.query("cal tuning 2 1.46")
		print "Calibration step3:",r
		return 

