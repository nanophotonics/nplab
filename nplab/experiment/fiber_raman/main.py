from builtins import range
import numpy as np 
import matplotlib.pyplot as plt

from nplab.instrument.spectrometer.acton import Acton
from nplab.instrument.camera.pixis import Pixis

p = Pixis()
p.StartUp()
p.SetExposureTime(50)
initialized = False
tries = 0

# while initialized == False and tries < 50:
# 	try:
a = Acton("COM5")
# 		initialized = True 
# 	except:
# 		tries = tries + 1

wavelengths = list(range(600,610,10))
for wl in wavelengths:
	
	fig, ax = plt.subplots(1)
	# a.set_wavelength(wl,debug=1)
	_,frame = p.raw_snapshot()
	ax.imshow(frame, cmap='gray')
	plt.savefig("images/wl_{}.png".format(wl))
	plt.close(fig)

p.ShutDown()