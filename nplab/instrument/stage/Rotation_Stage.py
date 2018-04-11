import struct
from nplab.instrument import serial_instrument as serial

class Rotation_Stage:

	def __init__(self,Port=None):

		self.Port=serial.SerialInstrument()
		self.Port.open()

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
			return 'Reserved Response Code'
		else:
			return Responses[Code]

	def Get_Status(self):
		Packer=struct.Struct(format='ccc')
		Message=Packer.pack(*['0','g','s'])
		self.Port.write(Message)
		Response=self.Port.readline()

		Code=int('0x'+Response[3:],0)

		return self.Convert_Status(Code)

	def Rotate(self,Angle):

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
			return 'Position: '+str(Position*360)
		else:
			return self.Convert_Status(Code)

	def Rotate_To(self,Angle):

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
			return 'Position: '+str(Position*360)
		else:
			return self.Convert_Status(Code)

	def Get_Position(self):
		Packer=struct.Struct(format='ccc')
		Message=Packer.pack(*['0','g','p'])

		self.Port.write(Message)
		Response=self.Port.readline()
		

		Code=int('0x'+Response[3:],0)

		if Response[:3]=='0PO':
			Position=float(Code)/262144
			return 'Position: '+str(Position*360)
		else:
			return self.Convert_Status(Code)









		

		


