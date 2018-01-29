import math
import os
import ctypes
from ctypes import *
import numpy as np
from nplab.instrument import Instrument
from nplab.instrument.electronics import adlink9812_constants
from nplab.utils.gui import *
from nplab.ui.ui_tools import *
import nplab
import datetime
import matplotlib 
import matplotlib.pyplot as plt 
### Steps of PCI-DASK applications:
#
# Full documentation: ADLINK PCIS-DASK User's Manual
# Function reference: http://www.adlinktech.com/publications/manual/Software/PCIS-DASK-X/PSDASKFR.pdf

#	1. Register card
#	2. Configuration function
#	3. AI/AO/DI/DO Operation function
#		AI: analog input
#			non-buffered single-point AI: poll device for data
#			buffered: interrupt transfer/DMA (direct memory access) to transfer data from device to user buffer
#		AO: analog output
#		DI: digital input
#		DO: digital output
#		3.1 ---- Configuration ---
#			Must configure your card (our case: AI_9812_Config, passing card_id (from registration and parameters for registering))
#	4. Release card


DATATYPE = c_ushort

VERSION = 0.01


class Adlink9812(Instrument):

	def __init__(self, dll_path="C:\ADLINK\PCIS-DASK\Lib\PCI-Dask64.dll",debug=False):
		"""Initialize DLL and configure card"""
		# super(Adlink9812,self).__init__()
		self.debug = debug
		if not os.path.exists(dll_path):
			if self.debug != True:
				raise ValueError("Adlink DLL not found: {}".format(dll_path))
		else:
			self.dll = CDLL(dll_path)
			self.card_id = self.register_card()
			self.configure_card()

	def __del__(self):
		'''Deregister the card on object deletion'''
		self.release_card()


	def register_card(self,channel = 0):
		outp = ctypes.c_int16(self.dll.Register_Card(adlink9812_constants.PCI_9812,c_ushort(channel)))
		if outp.value < 0:
			print "Register_Card: nonpositive value -> error code:", outp
		return outp.value

	def release_card(self):
		releaseErr = ctypes.c_int16(self.dll.Release_Card(self.card_id))
		if releaseErr.value != 0:
			print "Release_Card: Non-zero status code:", releaseErr.value
		return

	def get_card_sample_rate(self,sampling_freq):
		actual = c_double()
		statusCode = ctypes.c_int16(DLL.GetActualRate(self.card_id,c_double(sampling_freq), byref(actual)))

		if statusCode.value != 0:
			print "GetActualRate: Non-zero status code:", statusCode.value
		return actual.value

	def get_qt_ui(self):
		return Adlink9812UI(card=self,debug = self.debug)

	@staticmethod
	def get_qt_ui_cls():
		return Adlink9812UI

	def configure_card(self):
		#Configure card for recording
		configErr = ctypes.c_int16(self.dkk.AI_9812_Config(
			c_ushort(self.card_id),
			c_ushort(adlink9812_constants.P9812_TRGMOD_SOFT), #Software trigger mode
			c_ushort(adlink9812_constants.P9812_TRGSRC_CH0),  #Channel 0 
			c_ushort(adlink9812_constants.P9812_TRGSLP_POS),  #Positive edge trigger
			c_ushort(adlink9812_constants.P9812_CLKSRC_INT),  #Internal clock
			c_ushort(0x80), 								  #Trigger threshold = 0.00V
			c_ushort(0),										#Postcount - setting for Middle/Delay Trigger
			))

		if configErr.value != 0:
			print "AI_9812_Config: Non-zero status code:", configErr.value
		return


	def convert_to_volts(self,inputBuffer, outputBuffer, buffer_size):
		convertErr = ctypes.c_int16(self.dll.AI_ContVScale(
				c_ushort(self.card_id),							#CardNumber
				c_ushort(adlink9812_constants.AD_B_1_V),		#AdRange
				inputBuffer, 									#DataBuffer   - array storing raw 16bit A/D values
				outputBuffer, 									#VoltageArray - reference to array storing voltages
				c_uint32(buffer_size) 							#Sample count - number of samples to be converted
			))

		if convertErr.value != 0:
			print "AI_ContVScale: Non-zero status code:", convertErr.value
		return 


	def synchronous_analog_input_read(self,sample_freq, sample_count,verbose = False):
		#Initialize Buffers
		#databuffer for holding A/D samples + metadata bits
		dataBuff = (c_ushort*sample_count)()
		#voltageArray for holding converted voltage values
		voltageOut = (c_double*sample_count)()

		#Sample data, Mode: Synchronous
		readErr = ctypes.c_int16(self.dll.AI_ContReadChannel(
			c_ushort(self.card_id), 								#CardNumber
			c_ushort(channel),       						#Channel
			c_ushort(adlink9812_constants.AD_B_1_V),		#AdRange
			dataBuff,												#Buffer
			c_uint32(sample_count),							#ReadCount
			c_double(sample_freq),							#SampleRate (Hz)
			c_ushort(adlink9812_constants.SYNCH_OP)			#SyncMode
		))

		if readErr.value != 0:
			print "AI_ContReadChannel: Non-zero status code:", readErr.value

		#Convert to volts
		convert_to_volts(self.card_id, dataBuff,voltageOut,sample_count)
		return np.asarray(voltageOut)

	def asynchronous_double_buffered_analog_input_read(self,sample_freq,sample_count,card_buffer_size = 500000,verbose=False, channel = 0):
		'''
		Non-Triggered Double-Buffered Asynchronous  Analog Input Continuous Read
		Steps: [Adlink PCIS-DASK manual,page 47]

		1. AI_XXXX_Config
			Configure the card for the asynchronous mode

		2. AI_AsyncDblBufferMode 
			Enable double buffered mode

		3. AI_ContReadChannel
			Read from a single channel (=0)

		4. while not stop:

			4.1 if (AI_AsyncDblBufferHaldReady):   #Check if buffer is half full]
				
				4.1.1 AI_AsyncDblBufferTransfer	   #Transfer data from card buffer into user buffer
			
		5. AI_AsyncClear
		6. Convert all data to volts and return

		'''
		
		#AI_AsyncDblBufferMode - initialize Double Buffer Mode
		buffModeErr = ctypes.c_int16(self.dll.AI_AsyncDblBufferMode(c_ushort(card_id),ctypes.c_bool(1)))
		if verbose or buffModeErr.value != 0:
			print "AI_AsyncDblBufferMode: Non-zero status code",buffModeErr.value

		#card buffer
		cardBuffer = (c_ushort*card_buffer_size)()

		#user buffers
		user_buffer_size = card_buffer_size/2 #half due to being full when buffer is read
		nbuff = int(math.ceil(sample_count/float(user_buffer_size)))
		
		# uBs = [(c_double*user_buffer_size)()]*nbuff
		uBs = []
		print uBs
		# oBs = [(c_double*user_buffer_size)()]*nbuff
		oBs = []
		if verbose:
			print "Number of user buffers:", nbuff

		#AI_ContReadChanne

		readErr = ctypes.c_int16(self.dll.AI_ContReadChannel(
			c_ushort(card_id), 					#CardNumber
			c_ushort(channel),       			#Channel
			c_ushort(adlink9812_constants.AD_B_1_V),		#AdRange
			cardBuffer,									#Buffer
			c_uint32(card_buffer_size),			#ReadCount
			c_double(sample_freq),				#SampleRate (Hz)
			c_ushort(adlink9812_constants.ASYNCH_OP)		#SyncMode - Asynchronous
		))

		if verbose or readErr.value != 0:
			print "AI_ContReadChannel: Non-zero status code",readErr.value

		#AI_AsyncDblBufferHalfReader
		#I16 AI_AsyncDblBufferHalfReady (U16 CardNumber, BOOLEAN *HalfReady,BOOLEAN *StopFlag)
		
		for i in range(nbuff):
			currentBuffer = (c_double*user_buffer_size)()
			halfReady = c_bool(0)
			stopFlag = c_bool(0)
			while halfReady.value != True:
				buffReadyErr = ctypes.c_int16(self.dll.AI_AsyncDblBufferHalfReady(
					c_ushort(card_id),
					ctypes.byref(halfReady),
					ctypes.byref(stopFlag))
				)
				if buffReadyErr.value!=0:
					print "buffReadErr:",buffReadyErr.value
					print "HalfReady:",halfReady.value
		
			#AI_AsyncDblBufferTransfer
			#I16 AI_AsyncDblBufferTransfer (U16 CardNumber, U16 *Buffer)
			buffTransferErr = ctypes.c_int16(self.dll.AI_AsyncDblBufferTransfer(c_ushort(card_id), ctypes.byref(currentBuffer)))
			uBs.append(currentBuffer)
			if buffTransferErr.value != 0:
				print "buffTransferErr:",buffTransferErr.value

		accessCnt = ctypes.c_int32(0)
		clearErr = ctypes.c_int16(self.dll.AI_AsyncClear(card_id, ctypes.byref(accessCnt)))
		if verbose:
			print "AI_AsyncClear,AccessCnt:", accessCnt.value
		
		#concatenate user buffer onto existing numpy array
		#reinitialize user buffer

		for i in range(nbuff):
			oB = (c_double*user_buffer_size)()
			convertErr = ctypes.c_int16(self.dll.AI_ContVScale(
			c_ushort(card_id),				#CardNumber
			c_ushort(adlink9812_constants.AD_B_1_V),	#AdRange
			uBs[i], 					#DataBuffer   - array storing raw 16bit A/D values
			oB, 					#VoltageArray - reference to array storing voltages
			c_uint32(user_buffer_size) 			#Sample count - number of samples to be converted
			))
			oBs.append(oB)
			if convertErr.value != 0:
				print "AI_ContVScale: Non-zero status code:", convertErr.value
		return np.concatenate(oBs)

	@staticmethod
	def get_times(dt,nsamples):
		return [i*dt for i in range(nsamples)]

	def capture(self,sample_freq, sample_count,verbose = False):
		assert(sample_freq <= int(2e7) and sample_freq > 1)
		dt = 1.0/sample_freq
		if self.debug:
			print "---DEBUG MODE ENABLED---"
			debug_out = (2.0*np.random.rand(sample_count))-1.0 
			return debug_out,dt
		elif sample_count < 200000:
			return self.asynchronous_double_buffered_analog_input_read(sample_freq= sample_freq,sample_count = sample_count,verbose = verbose),dt
		else:
			return self.synchronous_analog_input_read(sample_freq= sample_freq,sample_count = sample_count,verbose = verbose),dt





class Adlink9812UI(QtWidgets.QWidget, UiTools):
	def __init__(self,card, parent=None,debug = False):
		if not isinstance(card, Adlink9812):
			raise ValueError("Object is not an instnace of the Adlink9812 Daq")
		super(Adlink9812UI, self).__init__()
		self.card = card 
		self.parent = parent
		self.debug = debug

		#TODO - add adlink9812.ui file properly
		uic.loadUi(os.path.join(os.path.dirname(__file__), 'adlink9812.ui'), self)

		#bind widgets to functions
		self.capture_button.clicked.connect(self.capture)
		self.sample_freq_textbox.textChanged.connect(self.set_sample_freq)
		self.sample_count_textbox.textChanged.connect(self.set_sample_count)
		self.series_name_textbox.textChanged.connect(self.set_series_name)
		self.series_key_textbox.textChanged.connect(self.set_series_key)


		self.set_sample_freq()
		self.set_sample_count()
		self.set_series_name()
		self.set_series_key()
		

	def set_sample_freq(self):
		MHz = 1e6
		try:
			self.sample_freq = int(float(self.sample_freq_textbox.text())*MHz)
		except Exception,e:
			print "Failed parsing sampling frequency to float:",self.sample_freq_w.text()
		return

	def set_sample_count(self):
		try:
			self.sample_count = int(float(self.sample_count_textbox.text())*1000)
		except Exception,e:
			print "Failed parsing sample count to int:",self.sample_freq_textbox.text()
		return

	def set_series_name(self):
		self.series_group = self.series_name_textbox.text()
		return

	def set_series_key(self):
		self.series_key = self.series_key_textbox.text()
		return
	

	def plot_series(self,voltages, dt, timestamp):
		print voltages[0:10]
		times = self.card.get_times(dt, len(voltages))
		fig,ax = plt.subplots(1)
		ax.plot(times, voltages)
		ax.set_xlabel("Time [s]")
		ax.set_ylabel("Voltage [V]")
		ax.set_title("Adlink9812 Capture, Timestamp: {0}".format(timestamp))
		plt.show()
		return

	def capture(self):
		
		save = self.save_checkbox.isChecked()
		plot = self.plot_checkbox.isChecked()

		print "-"*5+"Adlink 9812: Capture" + "-"*5
		print "SamplingFreq (Hz):", self.sample_freq
		print "SampleCount (counts):", self.sample_count
		print "SeriesName: ", self.series_group
		print "Serieskey: ", self.series_key
		print "Plot trace:", plot
		print "Save trace:", save
		if save:
			try:
				self.datafile
			except AttributeError:
				self.datafile = nplab.datafile.current()
			dg = self.datafile.require_group(self.series_group)

		
		voltages, dt = self.card.capture(sample_freq=self.sample_freq, sample_count=self.sample_count)
		vmean = np.mean(voltages)
		vmax = np.max(voltages)
		vmin = np.min(voltages)
		vstd = np.std(voltages)
		vpp = np.abs(vmax-vmin)

		timestamp = str(datetime.datetime.now()).replace(' ', 'T')
		attrs = {
			
			"device": "adlink9812",
			"description": "Analog to digital converter",
			"_units": "volts",
			"sample_count": self.sample_count,
			"frequency":self.sample_freq,
			"dt": dt,
			"vmean":vmean,
			"vstdev": vstd,
			"vmax":vmax,
			"vmin":vmin,
			"vpp":vpp,
			"X label": "Sample Index",
			"Y label": "Voltage [V]"
			}

		if save:
			dg.create_dataset(self.series_key,data=voltages, attrs = attrs)
			dg.file.flush()

		#plot measurement on graph
		if plot:
			print voltages
			self.plot_series(voltages=voltages, dt=dt, timestamp=timestamp)
		
		return

if __name__ == "__main__":
	
	#debug mode enabled - won't try to picj up card - will generate data
	card = Adlink9812("C:\ADLINK\PCIS-DASK\Lib\PCI-Dask64.dll",debug=True)
	app = get_qt_app()
	ui = Adlink9812UI(card=card,debug =True)
	ui.show()
	sys.exit(app.exec_())