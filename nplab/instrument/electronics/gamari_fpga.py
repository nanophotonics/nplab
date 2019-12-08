from __future__ import print_function
import os
from timetag.capture_pipeline import CapturePipeline
import time
from nplab.instrument import Instrument
import subprocess
class Timetagger(Instrument):

	def __init__(self,verbose=0):

		self.pipeline = CapturePipeline()
		self._out_file_cat = None
		self._out_file = None
		self.readout_running = False

		#default pipeline latency
		self.pipeline.set_send_window(84)

	def get_qt_ui(self):
		raise ValueError("Timetagger UI - Not implemented!")


	def capture(self,integration_time,output_file):

		self.pipeline.start_capture()
		self.start_writeout(filename=output_file)
		time.sleep(integration_time)
		self.pipeline.stop_capture()
		self._out_file_cat.terminate()
		self._out_file.close()
		self._out_file_cat = None
		self._out_file = None
		self.readout_running = False
		return

	def start_writeout(self, filename):
	    if self._out_file_cat is not None:
	            self._out_file_cat.terminate()
	    filename = os.path.normpath(os.path.expanduser(filename))
	    print("Writing captured data to:", filename)
	    dirname = os.path.dirname(filename)
	    if not os.path.exists(dirname) and len(dirname) > 0:
	            os.makedirs(dirname)
	    self._out_file = open(filename, 'w')
	    self._out_file_cat = subprocess.Popen(['timetag-cat'], stdout=self._out_file)
	    return 


if __name__ == "__main__":
	t = Timetagger()
	from datetime import datetime
	print(datetime.now())
	path = "~/Desktop/timetagger-test.timetag"
	# filename = os.path.normpath(os.path.expanduser(path))
	# print filename
	t.capture(integration_time=3,output_file=path)
	print(datetime.now())
	