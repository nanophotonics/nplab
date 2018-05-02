import ctypes
from ctypes import CDLL, c_char_p,byref,c_char, POINTER
import os

FILEPATH = os.path.realpath(__file__)
DIRPATH = os.path.dirname(FILEPATH)

ATTRS_PATH = "{0}\\{1}".format(DIRPATH,"bentham_DTMc300_attributes.atr")
CONFIG_PATH = "{0}\\{1}".format(DIRPATH,"bentham_DTMc300_config.cfg")
DLL_PATH="{0}\\{1}".format(DIRPATH,"bentham_instruments_dlls\\Win64\\benhw64.dll") #NOTE: hardcoded to use 64 bit DLL, for 32bit use the ones in Win32

# print DLL_PATH
dll = CDLL(DLL_PATH)

# print dll.__dict__
error_report = ""
response = dll.BI_build_system_model(c_char_p(CONFIG_PATH),c_char_p(error_report))

print "BI_build_system_model:",response

response = dll.BI_initialise(None)

print "BI_initialise:",response


response = dll.BI_load_setup(c_char_p(ATTRS_PATH)) 

print "BI_load_setup:",response
