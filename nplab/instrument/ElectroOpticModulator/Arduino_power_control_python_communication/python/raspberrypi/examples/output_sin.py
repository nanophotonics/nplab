'''!
  @file output_sin.py
  @brief Use the DAC module to output sine wave
  @copyright   Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com)
  @license     The MIT License (MIT)
  @author [TangJie]](jie.tang@dfrobot.com)
  @version  V1.0.0
  @date  2018-01-15
  @url https://github.com/DFRobot/DFRobot_MCP4725
'''
import sys
sys.path.append('../')
import time
MCP4725A0_IIC_Address0				= 0x60
MCP4725A0_IIC_Address1				= 0x61
from DFRobot_MCP4725 import MCP4725
mcp4725 = MCP4725()
REF_VOLTAGE   = 5000
#Set the MCP225's i2c address
mcp4725.setAddr_MCP4725(MCP4725A0_IIC_Address0)
#Setting the base voltage of DAC must equal the power supply voltage, and the unit is millivolt
mcp4725.set_ref_voltage(REF_VOLTAGE)
while True :
  #Output a magnitude of 2500mv, the frequency of 10HZ, DC offset 2500mv sine wave
	mcp4725.output_sin(2500,10,2500)
