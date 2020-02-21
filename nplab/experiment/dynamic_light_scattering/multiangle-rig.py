from __future__ import print_function
from builtins import range
from nplab.instrument.stage.Thorlabs_NR360SM import Thorlabs_NR360SM
from nplab.instrument.electronics.gamari_fpga import Timetagger
from nplab.instrument.shutter.thorlabs_sc10 import ThorLabsSC10
from datetime import datetime
PATH_TEMPLATE ="~/dataspace/{}"
s = Thorlabs_NR360SM(port='/dev/ttyUSB0', source=0x01, destination=0x11)
t = Timetagger()
shutter = ThorLabsSC10('/dev/ttyUSB2')

shutter.close_shutter()
s.home()
s._waitFinishMove(axis="x")
import time
angles = list(range(10,50,10))
print(angles)
for angle in angles:
	shutter.close_shutter()
	s.move(angle,axis="x",block=True)
	print("angle@",angle)
	print("starting capture {} ...".format(datetime.now()), end=' ')
	output_file =PATH_TEMPLATE.format("datafile_{}.timetag".format(angle))
	shutter.open_shutter()
	time.sleep(1)
	# t.capture(integration_time=1,output_file=output_file)
	print("...done {}".format(datetime.now()))
	shutter.close_shutter()

shutter.close_shutter()
s.home()
# for angle in angles:

# 	print angle
# 	s.move(pos=angle,axis="x",relative=False,block=False)
	# 
	# s.identify()
	# print "before",s.get_position()
	# s.move(angle,axis="x",block=True)
	# print "after",s.get_position()
	# print "captured@",angle

	# 
# s.home()


