from __future__ import print_function
import ctypes
from nplab.instrument import Instrument
from ctypes import CDLL, c_char_p,byref,c_char, POINTER, ARRAY, WinDLL
import os
import numpy as np
import time

FILEPATH = os.path.realpath(__file__)
DIRPATH = os.path.dirname(FILEPATH)

ATTRS_PATH = "{0}\\{1}".format(DIRPATH,"bentham_DTMc300_attributes.atr")
CONFIG_PATH = "{0}\\{1}".format(DIRPATH,"bentham_DTMc300_config.cfg")
DLL_PATH="{0}\\{1}".format(DIRPATH,"bentham_instruments_dlls\\Win32\\benhw32_fastcall.dll") #NOTE: hardcoded to use 64 bit DLL, for 32bit use the ones in Win32

# print DLL_PATH

def read_tokens():
	'''
	Text tokens are mapped to integers in the bentham_dlltokens.h file
	read the file and make the dictionary of tokens 
	'''
	token_map = {}
	import re
	definition_pattern = re.compile("#define.*")
	token_filepath = os.path.normpath(DIRPATH+"/bentham_dlltokens.h")
	with open(token_filepath,"r") as f:
		for line in f.readlines():
			line = line.strip("\n")
			if bool(definition_pattern.match(line))==True:
				line_list = line.split(" ")
				token_map.update({line_list[1]:int(line_list[2])})

	return token_map


class Bentham_DTMc300(Instrument):

	def __init__(self):
		super(Bentham_DTMc300,self).__init__()

		self.dll = WinDLL(DLL_PATH)

		self.token_map = read_tokens()
		error_report = c_char_p("")
		response = self.dll.BI_build_system_model(c_char_p(CONFIG_PATH),error_report)
		print("Error report",error_report)
		print("BI_build_system_model:",response)
		response = self.dll.BI_load_setup(c_char_p(ATTRS_PATH)) 
		print("BI_load_setup:",response)
		response = self.dll.BI_initialise(None)
		print("BI_initialise:",response)
		response = self.dll.BI_park(None)
		print("BI_park:",response)

		self.components = self.get_component_list()

	def get_component_list(self):
		mylist = (ctypes.c_char*100)()
		response = self.dll.BI_get_component_list(ctypes.byref(mylist))
		components = [k for k in ("".join([c for c in mylist if c != '\x00'])).split(",") if k != '']
		print("BI_get_component_list:",response, components)
		return components


	def get(self,item_id,token,index):
		value = ctypes.c_double(0.0)
		print("id:{0}, token:{1}, index:{2}".format(item_id,token,index))
		response = self.dll.BI_get(c_char_p(item_id),ctypes.c_int32(self.token_map[token]),ctypes.c_int32(index),ctypes.byref(value))
		print("BI_get", response)
		return value.value
  
	def get_wavelength(self,token="mono"):
		wavelength = self.get(item_id="mono",token="MonochromatorCurrentWL",index=0)
		return wavelength

	def set_wavelength(self,wavelength):
		
		delay = ctypes.c_double(0.0)
		response = self.dll.BI_select_wavelength(ctypes.c_double(wavelength), ctypes.byref(delay))
		time.sleep(0.3) #sleep for 300ms - ensure everything has moved
		return

if __name__ == "__main__":

	m = Bentham_DTMc300()
	initial =  m.get_wavelength()
	m.set_wavelength(0)
	final = m.get_wavelength()
	print("Initial, Final:", initial, final)
	print("DONE")