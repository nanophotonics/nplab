from nplab.instrument import Instrument

'''Class for the sensor - the component that is being controlled

You must override the get_sensor_value method with an implementation suitable for your device
'''
class Sensor(Instrument):

	def __init__(self):
		Instrument.__init__(self)


	def get_sensor_value():
		raise NotImplementedError

'''Class for the actuator - the component that has to control the sensor

You must override the set_actuator_value method with an implementation suitable for your device
'''
class Actuator(Instrument):

	def __init__(self):
		Instrument.__init__(self)

	def set_actuator_value(value):
		raise NotImplementedError 


class Controller(Instrument):


	def __init__(self,sensor,actuator, sensor_bounds, actuator_bounds):

		self.sensor = sensor
		self.actuator = actuator 
		self.sensor_bounds = sensor_bounds
		self.actuator_bounds = actuator_bounds

		self.calibration_data = None
	'''
	Generate datastructure that can later be queried to get the required actuator coordinates for setting the sensor

	'''
	def calibrate(ac0):
		'''
		@param ac0 - initial position of actuator - around which would would like to control
		'''
		raise NotImplementedError

	'''
	Used to update calibration data to incorporate new information at runtime 
	'''
	def update_calibration(sensor_value, actuator_value):
		if self.calibration_data is None:
			raise ValueError("You need to calibrate the controller before you use it!")
		else:
			raise NotImplementedError


	def get_required_actuator_value(sensor_value):
		if self.calibration_data is None:
			raise ValueError("You need to calibrate the controller before you use it!")
		else:
			raise NotImplementedError
	'''
	Use calibration data to set the actuator to level required for desired sensor output value
	'''
	def set_sensor_to(value):
		actuator_value = self.get_required_actuator_value(value)
		self.actuator.set_actuator_value(actuator_value)
		return