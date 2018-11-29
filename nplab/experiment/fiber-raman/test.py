from nplab.instrument.spectrometer.acton import Acton
from nplab.instrument.camera.pixis import Pixis
import matplotlib.pyplot as plt

print "Starting.."
p = Pixis()
img = p.get_roi(y_min=300,y_max=400)
spectrum = p.get_spectrum(y_min=300,y_max=400)
fig, axarr = plt.subplots(2)


axarr[0].imshow(img)
axarr[1].plot(spectrum)
print "Showing.."
plt.show()
print "Stopped.."
