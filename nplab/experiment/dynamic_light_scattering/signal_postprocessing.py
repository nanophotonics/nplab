import numpy as np
import matplotlib.pyplot as plt 

def signal_diff(voltage):
	d_voltage = voltage[0:-1] - voltage[1:]
	return d_voltage


def count_photons(voltage, count_threshold = 0.5):
	d_voltage = signal_diff(voltage)
	vmin = np.min(voltage)
	vmax = np.max(voltage)
	vspan = abs(vmax-vmin)
	counts = np.sum(np.absolute(d_voltage) > (count_threshold* vspan),axis=0)
	return counts


if __name__ == "__main__":

	#test count_photons - general pulse
	voltage = np.zeros(10000)
	voltage[3000:6000] = 1
	#add gaussian random noise to corrupt data - we want to make it tolerant to noise too!
	voltage = voltage + np.random.normal(0,0.1,voltage.shape)
	counts = count_photons(voltage,count_threshold=0.5)
	plt.plot(voltage)
	plt.xlabel("Simulated Time")
	plt.ylabel("Simulated Voltage")
	plt.title("Simulated time trace, Counts: {}".format(counts))
	plt.show()