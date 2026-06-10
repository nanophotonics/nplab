/*!
 * @file DFRobotJustableOutput.ino
 * @brief Set DAC voltage value by serial port and print it. 
 * @copyright   Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com)
 * @license     The MIT License (MIT)
 * @author [TangJie]](jie.tang@dfrobot.com)
 * @version  V1.0.0
 * @date  2018-01-15
 * @url https://github.com/DFRobot/DFRobot_MCP4725
 */
#include "Wire.h"
#include "DFRobot_MCP4725.h"
#include <stdlib.h>

#define  REF_VOLTAGE    5000

DFRobot_MCP4725 DAC;

char dtaUart[] = "5000";
uint8_t dtaLen = 0;
uint16_t OUTPUT_VOLTAGE;        // unit : mV 

void setup(void) {
  
  Serial.begin(115200);
  /* MCP4725A0_address is 0x60 or 0x61  
   * MCP4725A0_IIC_Address0 -->0x60
   * MCP4725A0_IIC_Address1 -->0x61
   */
  DAC.init(MCP4725A0_IIC_Address0, REF_VOLTAGE);
  Serial.println("Please input voltage...");
  
  /* If you don't set it, the default is normal mode. */
  //DAC.setMode(MCP4725_POWER_DOWN_100KRES); 
  //DAC.setMode(MCP4725_NORMAL_MODE);
}

inline void clearBuf(char *str)
{
   while(*str)
     *str++ = 0;
}

void loop(void) {
    clearBuf(dtaUart);
    while(Serial.available()) 
    {
        dtaUart[dtaLen++] = Serial.read();
    }
    if(dtaLen > 0)
    {
      OUTPUT_VOLTAGE = atoi(dtaUart);
      Serial.print("DFRobot_MCP4725 output: ");
      Serial.print(OUTPUT_VOLTAGE); 
      Serial.println(" mV");
      dtaLen= 0 ;
      DAC.outputVoltage(OUTPUT_VOLTAGE);
    }
    delay(100);
}
