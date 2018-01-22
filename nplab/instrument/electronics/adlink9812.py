import math
import os
import ctypes
from ctypes import *
import numpy as np
from nplab.instrument import Instrument
from nplab.instrument.electronics import adlink9812_constants
from nplab.utils.gui import *
from nplab.ui.ui_tools import *

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


class Adlink9812(Instrument):

	def __init__(self, dll_path="C:\ADLINK\PCIS-DASK\Lib\PCI-Dask64.dll"):
		"""Initialize DLL and configure card"""
		# super(Adlink9812,self).__init__()
		if not os.path.exists(dll_path):
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
				c_ushort(self.card_id),								#CardNumber
				c_ushort(adlink9812_constants.AD_B_1_V),		#AdRange
				inputBuffer, 									#DataBuffer   - array storing raw 16bit A/D values
				outputBuffer, 									#VoltageArray - reference to array storing voltages
				c_uint32(buffer_size) 							#Sample count - number of samples to be converted
			))

		if convertErr.value != 0:
			print "AI_ContVScale: Non-zero status code:", convertErr.value
		return 


	def synchronous_analog_input_read(self,sample_freq, read_count):
	
		#register card
		#load default configuration
		configure_card(self.card_id)
		#Initialize Buffers
		#databuffer for holding A/D samples + metadata bits
		dataBuff = (c_ushort*read_count)()
		#voltageArray for holding converted voltage values
		voltageOut = (c_double*read_count)()

		#Sample data, Mode: Synchronous
		readErr = ctypes.c_int16(self.dll.AI_ContReadChannel(
			c_ushort(self.card_id), 								#CardNumber
			c_ushort(channel),       						#Channel
			c_ushort(adlink9812_constants.AD_B_1_V),		#AdRange
			dataBuff,												#Buffer
			c_uint32(read_count),							#ReadCount
			c_double(sample_freq),							#SampleRate (Hz)
			c_ushort(adlink9812_constants.SYNCH_OP)			#SyncMode
		))

		if readErr.value != 0:
			print "AI_ContReadChannel: Non-zero status code:", readErr.value

		#Convert to volts
		convert_to_volts(self.card_id, dataBuff,voltageOut,read_count)
		return np.asarray(voltageOut)

	def asynchronous_double_buffered_analog_input_read(self,sample_freq,read_count,card_buffer_size = 500000,verbose=False, channel = 0):
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
		buffModeErr = ctypes.c_int16(self.dll.AI_AsyncDblBufferMode(c_ushort(self.card_id),ctypes.c_bool(1)))
		if verbose or buffModeErr.value != None:
			print "AI_AsyncDblBufferMode: Non-zero status code",buffModeErr.value

		#card buffer
		cardBuffer = (c_ushort*card_buffer_size)()

		#user buffers
		user_buffer_size = card_buffer_size/2 #half due to being full when buffer is read
		nbuff = int(math.ceil(read_count/float(user_buffer_size)))
		
		uBs = [(c_double*user_buffer_size)()]*nbuff
		if verbose:
			print "Number of user buffers:", nbuff

		#AI_ContReadChannel
		readErr = ctypes.c_int16(self.dll.AI_ContReadChannel(
			c_ushort(self.card_id), 					#CardNumber
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
		halfReady = c_bool(0)
		stopFlag = c_bool(0)

		for count, uB in enumerate(uBs):
			while halfReady.value != True:

				buffReadyErr = ctypes.c_int16(self.dll.AI_AsyncDblBufferHalfReady(
					c_ushort(self.card_id),
					ctypes.byref(halfReady),
					ctypes.byref(stopFlag))
				)
				if verbose:
					print "buffReadErr:",buffReadyErr
					print "HalfReady:",halfReady.value
				
			#AI_AsyncDblBufferTransfer
			#I16 AI_AsyncDblBufferTransfer (U16 CardNumber, U16 *Buffer)
			buffTransferErr = ctypes.c_int16(self.dll.AI_AsyncDblBufferTransfer(c_ushort(self.card_id), uB))
			if verbose:
				print "buffTransferErr:",buffTransferErr

		accessCnt = ctypes.c_int32(0)
		clearErr = ctypes.c_int16(self.dll.AI_AsyncClear(self.card_id, ctypes.byref(accessCnt)))
		if verbose:
			print "AI_AsyncClear,AccessCnt:", accessCnt.value
		
		#concatenate user buffer onto existing numpy array
		#reinitialize user buffer
		oBs = [(c_double*user_buffer_size)() for i in range(nbuff)]
		
		for i in range(nbuff):
			convert_to_volts(self.card_id, uBs[i],oBs[i],user_buffer_size)	
	
		return np.concatenate(oBs)

class Adlink9812UI(QtWidgets.QWidget, UiTools):
	def __init__(self,card, parent=None):
		if not isinstance(card, Adlink9812):
			raise ValueError("Object is not an instnace of the Adlink9812 Daq")
		super(Adlink9812UI, self).__init__()
		self.card = card 
		self.parent = parent

		#TODO - add adlink9812.ui file properly
		# uic.loadUi(os.path.join(os.path.dirname(__file__), 'adlink9812.ui'), self)


if __name__ == "__main__":
	
	card = Adlink9812("C:\ADLINK\PCIS-DASK\Lib\PCI-Dask64.dll") #should error
	print "pass"