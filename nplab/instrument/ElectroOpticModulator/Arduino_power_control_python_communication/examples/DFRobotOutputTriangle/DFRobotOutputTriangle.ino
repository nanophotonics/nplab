/*!
 * @file DFRobotOutputTriangle.ino
 * @brief Use the DAC module to output triangle wave
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

int i =0;
void setup(void) {
  Serial.begin(115200);
  /* MCP4725A0_address is 0x60 or 0x61  
   * MCP4725A0_IIC_Address0 -->0x60
   * MCP4725A0_IIC_Address1 -->0x61
   */
  DAC.init(MCP4725A0_IIC_Address0, REF_VOLTAGE);
}

void loop(void) {
  /*Output amplitude 5000mv, frequency 10HZ, 
   *the rise of the entire cycle accounted for 50% of the DC offset 0mv triangular wave.
   */
  DAC.outputTriangle(5000,10,0,50);
}
