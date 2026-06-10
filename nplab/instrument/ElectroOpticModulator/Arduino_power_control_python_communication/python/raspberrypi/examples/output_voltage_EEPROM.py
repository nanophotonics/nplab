'''!
	@file output_voltage_EEPROM.py
	@brief Output a constant voltage value and write to the internal EEPROM.
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
OUTPUT_VOLTAGE = 1000
#Set the MCP225's i2c address
mcp4725.setAddr_MCP4725(MCP4725A0_IIC_Address0)
#Setting the base voltage of DAC must equal the power supply voltage, and the unit is millivolt
mcp4725.set_ref_voltage(REF_VOLTAGE)
while True :
'''Output voltage value OUTPUT_VOLTAGE mv and write to the EEPROM,
    meaning that the DAC will retain the current voltage output
    after power-down or reset'''
	mcp4725.outputVoltageEEPROM(OUTPUT_VOLTAGE)
	time.sleep(0.1)
	print "DFRobot_MCP4725 write to EEPROM and output: %d mV"%OUTPUT_VOLTAGE
	print " ********************************************* "
	time.sleep(0.8)