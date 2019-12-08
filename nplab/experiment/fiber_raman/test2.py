from __future__ import print_function
from nplab.instrument.light_sources.SolsTiS import SolsTiS
import time
import numpy as np 
def get_wavelength(laser):
	laser.system_status()
	wl = laser.message_in_history[-1]["message"]["parameters"]["wavelength"]
	return wl[0]

def tune(wl,laser):
	laser.change_wavelength(wl)
	max_tries = 20
	while (np.absolute(wl - get_wavelength(laser)) > 0.05) and max_tries > 0:
		time.sleep(0.5)
		max_tries = max_tries - 1
	return 

if __name__ == "__main__":
	laser_ip = ('172.24.60.15',39933)
	laser = SolsTiS(laser_ip)
	wavelengths = [740,750,760,770,780,790,800]
	for wl in wavelengths:
		
		tune(wl,laser)
		measured = get_wavelength(laser)
		print(wl, measured)

	# laser.show_gui()