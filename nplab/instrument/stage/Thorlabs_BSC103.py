from __future__ import print_function
import struct,sys,math
import numpy as np 
from nplab.instrument.serial_instrument import SerialInstrument
from nplab.instrument.stage import Stage
from nplab.utils.gui import *
from nplab.ui.ui_tools import *
from nplab.instrument.apt_virtual_com_port import APT_VCP



class Thorlabs_BSC103(APT_VCP):


	def __init__(self,port=None,debug=0):
		
		self.debug = debug
		APT_VCP.__init__(self, port=port,source=0x01,destination={"motherboard":0x11})
        


if __name__ == "__main__":
	import struct
	t = Thorlabs_BSC103("/dev/ttyUSB0")
	
	formated_message = bytearray(struct.pack('BBBBBB', 0x23,0x02, 0x01, 0x00,0x11, 0x01))
	print(formated_message)
	# print t.query(message_id = msg_id,destination_id="motherboard")
	t.ser.write(formated_message)
	# print t.get_hardware_info(destination_id="motherboard")	

