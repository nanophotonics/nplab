from __future__ import division
from __future__ import print_function
from builtins import hex
from builtins import str
from builtins import object
from past.utils import old_div
import struct
from nplab.instrument import serial_instrument as serial
import numpy as np
import time
import os

class Rotation_Stage_Backend(serial.SerialInstrument):
    
    def __init__(self,port=None):
        super(Rotation_Stage_Backend, self).__init__()
        
    def Number_to_Hex(self,Input,Min_Size=8):
        Hex=hex(Input)[2:]
        Output=[]
        for i in Hex:
            Output.append(i)
        while len(Output)<Min_Size:
            Output=['0']+Output
        Output = list(map(str.encode, Output))
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
        Packer=struct.Struct(format=b'ccc')
        Message=Packer.pack(*[b'0',b'g',b's'])
        self.Port.write(Message)
        Response=self.Port.readline()

        Code=int(b'0x'+Response[3:],0)

        return self.Convert_Status(Code)

    def Rotate(self,Angle):

        Message=[b'0',b'm',b'r']

        while Angle<0:
            Angle+=360.
        Angle=Angle%360

        Angle=old_div((262144.*Angle),360)

        Angle=int(Angle)
        Angle=self.Number_to_Hex(Angle)

        Message+=Angle
        Packer=struct.Struct(format=b'ccccccccccc')
        Message=Packer.pack(*Message)
        
        self.Port.write(Message)
        Response=self.Port.readline()
        

        Code=int(b'0x'+Response[3:],0)

        if Response[:3]==b'0PO':
            Position=float(Code)/262144
            return 'Position: '+str(Position*360)
        else:
            return self.Convert_Status(Code)

    def Rotate_To(self,Angle):

        Message=[b'0', b'm', b'a']

        while Angle<0:
            Angle+=360.
        Angle=Angle%360

        Angle=old_div((262144.*Angle),360)

        Angle=int(Angle)
        Angle=self.Number_to_Hex(Angle)

        Message+=Angle
        Packer=struct.Struct(format=b'ccccccccccc')
        Message=Packer.pack(*Message)
        
        self.Port.write(Message)
        Response=self.Port.readline()
        

        Code=int(b'0x'+Response[3:],0)

        if Response[:3]==b'0PO':
            Position=float(Code)/262144
            return 'Position: '+str(Position*360)
        else:
            return self.Convert_Status(Code)

    def Get_Position(self):
      # This fails for small angles. Also, should return a float
        Packer=struct.Struct(format=b'ccc') 
        Message=Packer.pack(*[b'0',b'g',b'p'])

        self.Port.write(Message)
        Response=self.Port.readline()
        Code=int(b'0x'+Response[3:],0)

        if Response[:3]==b'0PO':
            Position=float(Code)/262144
            return 'Position: '+str(Position*360)
        else:
            return self.Convert_Status(Code)


class Filter_Wheel(object):

    def __init__(self,Port='COM20',Power_Meter=None,Power_Curve_Directory=os.path):
            self.Stage=Rotation_Stage_Backend(Port)
            self.Power_Curve=np.load(Power_Curve_Directory+'Filter_Wheel_Power_Curve.npy')
            self.Power_Curve_Directory=Power_Curve_Directory
            self.Power_Meter=Power_Meter
            self.Angle_Range=[0,360]      #230
            
    def Return_Home(self):
        self.Stage.Rotate_To(180) #100

    def Generate_Power_Curve(self,Number_of_Points=30,Measurements_per_Point=10,Background=0.):
        if self.Power_Meter is None:
            print('No Power Meter Defined!')
            return
        
        Input_Angles=np.linspace(self.Angle_Range[0],self.Angle_Range[1],Number_of_Points)

        Output_Angles=[]
        Output_Powers=[]

        self.Stage.Rotate_To(self.Angle_Range[0]) 
        time.sleep(2)

        for i in Input_Angles:
            Pos=self.Stage.Rotate_To(i)
            time.sleep(0.5)
            Pos=float(Pos[9:])
#            if Pos>295:
#                Pos-=360
            Output_Angles.append(Pos)
            Power=[]
            while len(Power)<Measurements_per_Point:
                Power.append(self.Power_Meter.read)
            Output_Powers.append(np.mean(Power))
            time.sleep(0.5)
            print('Current Angle: '+str(round(Pos,2)))

        self.Stage.Rotate_To(self.Angle_Range[0])#-190

        self.Power_Curve=np.array([Output_Angles,1000.*(np.array(Output_Powers)-Background)])

    def Generate_Power_Curve_v2(self,Number_of_Points=30,Measurements_per_Point=10,Background=0.):
        if self.Power_Meter is None:
            print('No Power Meter Defined!')
            raise Exception('Lacking Power Meter')
        def Measure():
            Power=[]

            while len(Power)<Measurements_per_Point:
                try:
                    Power.append(self.Power_Meter.read)
                except:
                    Dump=1
            return np.median(Power)
        def Rotate_Catch(Angle):
            Pos=None
            while Pos is None:
                try:
                    Pos=self.Stage.Rotate_To(Angle)
                    time.sleep(0.5)
                    Pos=float(Pos[9:])
                except:
                    Pos=None
            return Pos%360

        Angles=[]
        Powers=[]
        for i in [self.Angle_Range[0],self.Angle_Range[1]]:
            Pos=Rotate_Catch(i)
            Angles.append(Pos)
            Powers.append(Measure())

        while len(Powers)<Number_of_Points:
            Diff=[]
            n=1
            while n<len(Powers):
                Diff.append(Powers[n-1]-Powers[n])
                n+=1
            print('Points:'+str(len(Powers))+'. Average Power Seperation: '+str(round(np.mean(Diff)*1000000,2))+'uW')
            Next=np.argmax(Diff)
          #print Next
            Next_Angle=0.5*(Angles[Next]+Angles[Next+1])
            Pos=Rotate_Catch(Next_Angle)
            Angles=Angles[:Next+1]+[Pos]+Angles[Next+1:]
            Powers=Powers[:Next+1]+[Measure()]+Powers[Next+1:]

        self.Return_Home()
        self.Power_Curve=np.array([Angles,1000.*(np.array(Powers)-Background)])

        
    def Save_Power_Curve(self):
        np.save(self.Power_Curve_Directory+'Filter_Wheel_Power_Curve.npy',self.Power_Curve)

    def Set_To_Power(self,Power):
        if Power>np.max(self.Power_Curve[1]) or Power<np.min(self.Power_Curve[1]):
            print('Outside available power limits!')
            print('Please enter a value between '+str(np.min(self.Power_Curve[1]))+' and '+str(np.max(self.Power_Curve[1])))
            return

        Lower_Angle=0
        while self.Power_Curve[1][Lower_Angle]>=Power:
            Lower_Angle+=1
        Lower_Angle-=1

        if Lower_Angle==len(self.Power_Curve[1]):
            Lower_Angle-=1

        Angles=[self.Power_Curve[0][Lower_Angle],self.Power_Curve[0][Lower_Angle+1]]
        Powers=[self.Power_Curve[1][Lower_Angle],self.Power_Curve[1][Lower_Angle+1]]

        m=old_div((Angles[1]-Angles[0]),(Powers[1]-Powers[0]))
        c=Angles[0]-(m*Powers[0])

        Angle=(m*Power)+c

        print('Rotating To: '+str(round(Angle,2)))

        self.Stage.Rotate_To(Angle)
        
        return Angle
      








        

        


