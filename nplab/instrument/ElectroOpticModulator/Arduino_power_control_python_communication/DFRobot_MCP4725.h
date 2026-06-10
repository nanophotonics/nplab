/*!
 * @file DFRobot_MCP4725.h
 * @brief Definition and explanation of the MCP4725 function library class
 * @copyright   Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com)
 * @license     The MIT License (MIT)
 * @author [TangJie]](jie.tang@dfrobot.com)
 * @version  V1.0.0
 * @date  2018-01-15
 * @url https://github.com/DFRobot/DFRobot_MCP4725
 */

#if ARDUINO >= 100
 #include "Arduino.h"
#else
 #include "WProgram.h"
#endif

#include <Wire.h>

#define MCP4725_Write_CMD            0x40     ///< Write data to the DAC address.
#define MCP4725_WriteEEPROM_CMD      0x60     ///< Write data to the DAC EEPROM address.

///< The IIC address of MCP4725A0 may be 0x60 or 0x61, depending on the location of the dial code switch on the sensor. 
#define MCP4725A0_IIC_Address0       0x60   
#define MCP4725A0_IIC_Address1       0x61

#define MCP4725_NORMAL_MODE          0
#define MCP4725_POWER_DOWN_1KRES     1
#define MCP4725_POWER_DOWN_100KRES   2
#define MCP4725_POWER_DOWN_500KRES   3

class DFRobot_MCP4725{
public:
  /**
   * @fn init
   * @brief init MCP4725 device
   * @param addr Init the IIC address.
   * @param vRefSetting the base voltage of DAC must equal the power supply voltage, and the unit is millivolt.
   * @return None
   */
  void init(uint8_t addr, uint16_t vRef);

  /**
   * @fn setMode
   * @brief set power mode 
   * @param powerMode Set power mode,three are normal mode and power down mode.
   * @n               The following are three modes of power down.
   * @n               MCP4725_POWER_DOWN_1KRES      1 kΩ resistor to ground
   * @n               MCP4725_POWER_DOWN_100KRES    100 kΩ resistor to ground
   * @n               MCP4725_POWER_DOWN_500KRES    500 kΩ resistor to ground
   * @return None
   */
  void setMode(uint8_t powerMode);
  
  /** 
   * @fn outputVoltage
   * @brief  Output voltage value range 0-5000mv.   
   * @param  voltage Voltage value, range 0-5000, unit millivolt.
   * @return None
   */
  void outputVoltage(uint16_t voltage);

  /**
   * @fn  outputVoltageEEPROM
   * @brief  Output voltage value range 0-5000mv and write to the EEPROM,
   * @n      meaning that the DAC will retain the current voltage output
   * @n      after power-down or reset.
   * @param  voltage Voltage value, range 0-5000, unit millivolt.
   * @return None
   */
  void outputVoltageEEPROM(uint16_t voltage);

  /**
   * @fn outputSin
   * @brief  Output a sine wave.
   * @param  amp amp value, output sine wave amplitude range 0-5000mv
   * @param  freq freq value, output sine wave frequency
   * @param  offset offset value, output sine wave DC offset
   * @return None
   */
  void outputSin(uint16_t amp, uint16_t freq, uint16_t offset);

  /**
   * @fn outputTriangle
   * @brief  Output a sine wave.    
   * @param  amp amp value, output triangular wave amplitude range 0-5000mv
   * @param  freq freq value, output the triangle wave frequency
   * @param  offset offset value, output the DC offset of the triangle wave
   * @param  dutyCycle dutyCycle value, set the rising percentage of the triangle wave as a percentage of the entire cycle.
   * @n      Value range 0-100 (0 for only the decline of 100, only the rise of paragraph)
   * @return None
   */
  void outputTriangle(uint16_t amp, uint16_t freq, uint16_t offset, uint8_t dutyCycle);
  
 private:
  bool check_mcp4725();
  uint8_t  _IIC_addr;
  uint8_t  _PowerMode;
  uint16_t _refVoltage;
  uint16_t _voltage;
};
