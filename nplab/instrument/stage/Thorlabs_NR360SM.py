import sys
from nplab.instrument.stage.PyAPT import APTMotor
from nplab.instrument.stage import Stage, StageUI


class Thorlabs_NR360SM(Stage,APTMotor):

	def __init__(self,SerialNum,HWType=22):
		Stage.__init__(self,unit="u")
		APTMotor.__init__(self,SerialNum=SerialNum, HWTYPE=HWType)
		self.axis_names=["deg"]

	def move(self,pos,axis=None,relative=False):	
		if relative == True:
			print "Relative"

			self.mbRel(pos)
		else:
			self.mbAbs(pos)	
		return

	def __del__(self):
		self.cleanUpAPT()

	def get_position(self,axis=None):
		return [self.getPos()]


if __name__ == "__main__":
	import sys
	from nplab.utils.gui import get_qt_app
	s = Thorlabs_NR360SM(SerialNum=90810016,HWType=22)
	app = get_qt_app()
	ui = s.get_qt_ui()
	ui.show()
	sys.exit(app.exec_())
