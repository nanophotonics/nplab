/*!
 * @file DFRobotOutputVoltage.ino
 * @brief Output a constant voltage value and print through the serial port.
 * @copyright   Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com)
 * @license     The MIT License (MIT)
 * @author [TangJie]](jie.tang@dfrobot.com)
 * @version  V1.0.0
 * @date  2018-01-15
 * @url https://github.com/DFRobot/DFRobot_MCP4725
 */
#include "Wire.h"
#include "DFRobot_MCP4725.h"
#define  REF_VOLTAGE    5000

DFRobot_MCP4725 DAC;

uint16_t OUTPUT_VOLTAGE = 4000;        // unit : mV 

void setup(void) {
  
  Serial.begin(115200);
  /* MCP4725A0_address is 0x60 or 0x61  
   * MCP4725A0_IIC_Address0 -->0x60
   * MCP4725A0_IIC_Address1 -->0x61
   */
  DAC.init(MCP4725A0_IIC_Address0, REF_VOLTAGE);

}

void loop(void) {

  Serial.print("DFRobot_MCP4725 output: ");
  Serial.print(OUTPUT_VOLTAGE); 
  Serial.println(" mV");
  
  DAC.outputVoltage(OUTPUT_VOLTAGE);

  delay(200);
}