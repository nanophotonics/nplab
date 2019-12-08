from __future__ import print_function
from __future__ import absolute_import
from builtins import range
import matplotlib.pyplot as plt
import numpy as np

from nplab import datafile as df 
from nplab.analysis.smoothing import convex_smooth

from nplab.instrument.spectrometer.acton_2300i import Acton
from nplab.instrument.camera.Picam.pixis import Pixis
from .Pacton import Pacton


print("Starting..")
print("Pixis...")
p = Pixis(debug=0)
p.StartUp()
print("Acton...")
act = Acton("COM6",debug=0)
print("Done...")

pacton = Pacton(pixis=p,acton=act,debug=0)

print("Measuring...")
from nplab import datafile as df 
output_file = df.DataFile("measured_spectrum.hdf5","w")
dg = output_file.require_group("spectra")
fig,axarr = plt.subplots(3)
p.SetExposureTime(500)
pacton.get_pixel_response_calibration_spectrum()
measured_ys = []
measured_xs = []
from nplab.analysis.signal_alignment import correlation_align

for wl in range(400,800,4):
	
	print(p.GetExposureTime())
	spectrum,wavelengths = pacton.get_spectrum(wl,subtract_background=True,roi=[0,1024,600,800],debug=1)
	measured_ys = measured_ys + [spectrum]
	measured_xs = measured_xs + [wavelengths] 
	dg.create_dataset("spectrum_%d",data=[wavelengths,spectrum], attrs = {"center_wavelength":wl, "roi":[0,1024,600,800]})
	# axarr[0].plot(wavelengths,spectrum)

# shifts = []
# for i in range(1,len(measured_ys)):
# 	y0 = measured_ys[i-1]
# 	y1 = measured_ys[i]

# 	shift, xcorr = correlation_align(y0,y1,upsampling=1.0)

# 	xs1 = measured_xs[i]
# 	dxs1 = (xs1[1]-xs1[0])
# 	xs1 = xs1[0]+dxs1*np.array(range(-shift, len(y1)-shift))

# 	axarr[1].plot(xs1,y1)

p.ShutDown()
plt.show()