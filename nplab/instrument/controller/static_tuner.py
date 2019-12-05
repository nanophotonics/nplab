from __future__ import print_function
from builtins import range
import numpy as np
from nplab.instrument.controller import Controller

class StaticTuner(Controller):
	#Control the output of one intrument using another instrument

	def __init__(self, sensor,actuator, sensor_bounds, actuator_bounds, ac0=None):

		'''
		@param sensor - the device returning the parameter that we wish to tune
		
			This controller will assume that the sensor has method .get_output_state_value() method implemented

		@param actuator - the device, typically a stage whose setting we change to affect the output of the sensor
	

	
		@param sensor_bounds - specifies lower and upper bound on acceptable values of the sensor output
			useful for constraining the acutator to prevent damage to the sensor

		@param actuator_bounds - bounds on the actuator parameters.
			Example: linear stage will have a minimum and maximum displacement from zero in either direction

		@param ac0 - initial position of the actuator from which we start the tuning stage
		


		'''

		Controller.__init__(self,sensor = sensor, actuator = actuator, sensor_bounds = sensor_bounds, actuator_bounds = actuator_bounds)
		


	def calibrate(self,ac0):

		#min and max sensor values
		sensor_min = self.sensor_bounds[0]
		sensor_max = self.sensor_bounds[1]

		actuator_min = self.actuator_bounds[0]
		actuator_max = self.actuator_bounds[1]


		calibration_samples = 10


		self.calibration = np.zeros((calibration_samples,2))
		size_step = (actuator_max-actuator_min)/float(calibration_samples)
		
		actuator_positions = [ac0] 
		for i in range(1,calibration_samples,2):
			actuator_positions = actuator_positions + [ac0+i*size_step, ac0-i*size_step]
			print(actuator_positions)

		pass

	def update_calibration(self,sensor_value, actuator_value):
		pass

	def get_required_actuator_value(self,sensor_value):
		if self.calibration_data is None:
			raise ValueError("You need to calibrate the controller before you use it!")
		else:
			raise NotImplementedError




if __name__ == "__main__":

	tuner = StaticTuner(None,None,(0,100),(0,270))
	tuner.calibrate(np.asarray([100]))