import struct,sys
from nplab.instrument import serial_instrument as serial
from nplab.instrument.stage import Stage
from nplab.utils.gui import *
from nplab.ui.ui_tools import *

class Thorlabs_ELL8K(Stage):

	def __init__(self,Port=None):

		Stage.__init__(self,unit="u")
		self.ui = None
		self.Port=serial.SerialInstrument()
		self.Port.open()

	#Overriding methods in Stage class
	def get_position(self,axis=None):
		return self.Get_Position()

	def move(self,pos, axis=None, relative=False):
		#note: this is a rotation stage - multiple axes are not handled
		assert(type(pos)==float)
		if relative == True:
			self.Rotate_Relative(pos)
		else:
			self.Rotate_Absolute(pos)
		return

	def get_qt_ui(self):
		if self.ui is None:
			self.ui = Stage_UI(stage=self) 
		return self.ui

	def Number_to_Hex(self,Input,Min_Size=8):
		Hex=str(hex(Input))[2:].upper()
		Output=[]
		for i in Hex:
			Output.append(i)
		while len(Output)<Min_Size:
			Output=['0']+Output
		return Output


	def Convert_Status(self,Code):
		Responses=['No Error', 'Communication time out', 'Mechanical time out', 'Command error', 'Value out of range', 'Module isolated']
		Responses+=['Module out of isolation', 'Initializing error', 'Thermal error', 'Busy', 'Sensor Error', 'Initializing error', 'Thermal error', 'Busy']
		Responses+=['Sensor Error', 'Motor Error', 'Out of Range']
		if Code>=14:
			self.log('Thorlabs_ELL8K.Convert_Status: Reserved Response Code')
		else:
			self.log('Thorlabs_ELL8K.Convert_Status: {}'.format(Responses[Code]))
			return 

	def Get_Status(self):
		Packer=struct.Struct(format='ccc')
		Message=Packer.pack(*['0','g','s'])
		self.Port.write(Message)
		Response=self.Port.readline()

		Code=int('0x'+Response[3:],0)
		return self.Convert_Status(Code)

	def Rotate_Relative(self,Angle):
		Message=['0','m','r']
		while Angle<0:
			Angle+=360.
		Angle=Angle%360
		Angle=(262144.*Angle)/360
		Angle=int(Angle)
		Angle=self.Number_to_Hex(Angle)
		Message+=Angle
		Packer=struct.Struct(format='ccccccccccc')
		Message=Packer.pack(*Message)
		
		self.Port.write(Message)
		Response=self.Port.readline()
		Code=int('0x'+Response[3:],0)
		if Response[:3]=='0PO':
			Position=float(Code)/262144
			self.log('Position: '+str(Position*360))
		else:
			self.Convert_Status(Code)

		return

	def Rotate_Absolute(self,Angle):
		Message=['0','m','a']
		while Angle<0:
			Angle+=360.
		Angle=Angle%360
		Angle=(262144.*Angle)/360
		Angle=int(Angle)
		Angle=self.Number_to_Hex(Angle)
		Message+=Angle
		Packer=struct.Struct(format='ccccccccccc')
		Message=Packer.pack(*Message)
		self.Port.write(Message)
		Response=self.Port.readline()
		Code=int('0x'+Response[3:],0)
		if Response[:3]=='0PO':
			Position=float(Code)/262144
			self.log('Position: '+str(Position*360))
		else:
			self.Convert_Status(Code)
		
		return

	def Get_Position(self):
		Packer=struct.Struct(format='ccc')
		Message=Packer.pack(*['0','g','p'])
		self.Port.write(Message)
		Response=self.Port.readline()
		Code=int('0x'+Response[3:],0)
		if Response[:3]=='0PO':
			Position=float(Code)/262144
			return 'Position: '+str(Position*360)
			return Position*360.0
		else:
			self.Convert_Status(Code)
			raise ValueError("Thorlabs_ELL8K.Get_Position: Non-positional return code")


class Thorlabs_ELL8K_UI(QtWidgets.QWidget, UiTools):

	#TODO - make UI for this rotation stage and use that instead of the standard stage UI class
	def __init__(self,stage,parent=None,debug=0):
		if not isinstance(stage, Thorlabs_ELL8K):
			raise ValueError("Object is not an instance of the Thorlabs_ELL8K Stage")
		super(Thorlabs_NR360SM_UI, self).__init__()
		self.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
		#set ref to stage object
		self.stage = stage
		self.parent = parent
		self.debug =  debug

		uic.loadUi(os.path.join(os.path.dirname(__file__), 'Thorlabs_ell8k.ui'), self)
		



if __name__ == "__main__":
	print "pass"
	sys.exit(0)
		

		


