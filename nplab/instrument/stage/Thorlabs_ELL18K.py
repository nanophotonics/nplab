"""
Author: jpg66

Class to control the Thorlabs Elliptical Motor Rotation Stages. Optimised to work with revised stage from 2019.

Does backlash correction.

"""

from builtins import str
from builtins import hex
from builtins import range
from builtins import object
import struct
from nplab.instrument import serial_instrument as serial
import numpy as np



class ELL18K(object):

	def __init__(self,Port=None,Backlash_Correct=True):
		"""
		Class for Thorlabs Ellipical Motor Rotation Stage.

		Inputs:
		Port = COM Port (String)
		Counts_per_Rev = Number of intervals a 360 degree is split into.
						 This varies between iterations of the device
		Backlash_Correct = Bool

		"""

		self.Port=serial.SerialInstrument(Port)
		self.Port.open()
		self.Counts_per_Rev=int('0x'+self.Write_Hex('0in')[-9:-2],0) #Cuts off return characters
		self.Backlash_Correct=Backlash_Correct

		self.Calibrate_Motors() #Calibrates motor resonance frequencies to account for load etc.

	#------Utility functions----------

	def Number_to_Hex(self,Input,Min_Digits=8):
		"""
		Takes an Input integer and returns the corresponding hex as a string.
		If resulting string has less than Min_Digits digits, zeros are added to the front
		"""
		Hex=str(hex(Input))[2:].upper() #All letters should be upper case

		while len(Hex)<Min_Digits:
			Hex='0'+Hex
		return Hex


	def Convert_Status(self,Code):
		"""
		Converts integer Code into a status string
		"""
		Responses=['No Error', 'Communication time out', 'Mechanical time out', 'Command error', 'Value out of range', 'Module isolated']
		Responses+=['Module out of isolation', 'Initializing error', 'Thermal error', 'Busy', 'Sensor Error', 'Initializing error', 'Thermal error', 'Busy']
		Responses+=['Sensor Error', 'Motor Error', 'Out of Range']

		if Code>=14:
			return 'Reserved Response Code'
		else:
			return Responses[Code]

	def Write_Hex(self,String):
		"""
		Writes Hex string to port. Reads following line from port and returns string.
		"""

		Seperate=[]
		Format=''
		for i in String:
			Seperate.append(i)
			Format+='c'
		Packer=struct.Struct(format=Format)
		self.Port.write(Packer.pack(*Seperate))

		Response=self.Port.readline()
		return Response

	def Two_Compliment(self,Integer,Bits=32):
		"""
		Converts an integer into its 2s compliment with respect to a certain number of bits
		"""
		String=bin(Integer)[2:]
		while len(String)<Bits:
			String='0'+String
		New=[]
		for i in range(len(String)):
			New.append((-1*(int(String[i])-1)))
		n=len(New)-1
		New[-1]+=1
		while n>=0:
			if New[n]==2:
				New[n]=0
				if n>0:
					New[n-1]+=1
			else:
				n=0
			n-=1
		String_New='0b'
		for i in New:
			String_New+=str(i)
		return int(String_New,0)

	#------Stage Commands----------

	def Calibrate_Motors(self):
		"""
		Causes both motors to do a frequency sweep to find optimal resonance frequency
		"""
		self.Write_Hex('0s1')
		self.Write_Hex('0s2')
		self.Write_Hex('0us')

	def Get_Status(self):
		"""
		Requests a status message
		"""
		Status=self.Write_Hex('0gs')
		Code=int('0x'+Status[3:],0)
		return self.Convert_Status(Code)

	def Read_Position(self,Integer=None):
		"""
		Returns current stage angle. Can also take in a motor step Integer instead of requesting one from the device
		"""
		if Integer is None:
			Pos=self.Write_Hex('0gp')
			if Pos[:3]=='0PO': #Position_Returned
				Integer=int('0x'+Pos[3:],0)
			else:
				Code=int('0x'+Pos[3:],0) #Status returned
				return self.Convert_Status(Code)
		
		if Integer>2147483647: #Negative Number
			Integer=-self.Two_Compliment(Integer)
		Integer=360.*float(Integer)/self.Counts_per_Rev
		return Integer

	def Rotate_To(self,Angle):
		"""
		Rotates the stage to a given angle. Returns final angle or status report
		"""

		Angle=(Angle%360)

		Current_Angle=self.Read_Position()
		if isinstance(Current_Angle,str)==True: #Check is status returned
			return Current_Angle

		if abs(Current_Angle-Angle)>=360./self.Counts_per_Rev: #Is it worth rotating?

			if self.Backlash_Correct==True:
				Initial_Angle=(Angle-5)
			else:
				Initial_Angle=Angle

			Pulses=float(Initial_Angle)*self.Counts_per_Rev/360.
			Pulses=int(np.round(Pulses)) #Closest to requested

			Pos=self.Write_Hex('0ma'+self.Number_to_Hex(Pulses))

			if self.Backlash_Correct==True:
				Pulses=float(Angle)*self.Counts_per_Rev/360.
				Pulses=int(np.round(Pulses)) #Closest to requested

				Pos=self.Write_Hex('0ma'+self.Number_to_Hex(Pulses))

			if Pos[:3]=='0PO': #Position_Returned
				Pos=int('0x'+Pos[3:],0)
				return self.Read_Position(Pos)
			else:
				Code=int('0x'+Pos[3:],0) #Status returned
				return self.Convert_Status(Code)

		else:
			return Current_Angle

	def Rotate(self,Angle):
		Current_Angle=self.Read_Position()
		if isinstance(Current_Angle,str)==True: #Check is status returned
			return Current_Angle
		else:
			return self.Rotate_To(Current_Angle+Angle)

			
			










