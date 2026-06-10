# DFRobot_MCP4725 

* [English Version](./README.md)
  
MCP4725是一个12位ic驱动的高精度DAC模块。 它内部有EEPROM，  
意味着在掉电或复位后DAC将保留当前电压输出。

![产品效果图](./resources/images/DFR0552.png)

## 产品链接 (https://www.dfrobot.com.cn/goods-1728.html)
    SKU: DFR0552

## 目录
  - [概述](#概述)
  - [库安装](#库安装)
  - [方法](#方法)
  - [兼容性](#兼容性)
  - [版本](#版本)
  - [创作者](#创作者)

## 概述

提供Arduino库读取和解释博世的MCP4725的I2C数据。  

## 库安装

要使用此库，请先下载库文件，并将其粘贴到\Arduino\libraries目录中，然后打开示例文件夹并在该文件夹中运行demo。

## 方法

```C++
  /**
   * @fn init
   * @brief 初始化MCP4725设备
   * @param addr I2C设备地址
   * @param vRef 设置DAC的基准电压必须等于电源电压，单位为毫伏。  
   * @return None
   */
  void init(uint8_t addr, uint16_t vRef);

  /**
   * @fn setMode
   * @brief 设置电源模式 
   * @param powerMode 设置电源模式，三种是正常模式和关机模式。  
   * @n               以下是三种断电模式。
   * @n               MCP4725_POWER_DOWN_1KRES      1 kΩ 对地电阻
   * @n               MCP4725_POWER_DOWN_100KRES    100 kΩ 对地电阻
   * @n               MCP4725_POWER_DOWN_500KRES    500 kΩ 对地电阻
   * @return None
   */
  void setMode(uint8_t powerMode);
  
  /** 
   * @fn outputVoltage
   * @brief  输出电压值范围0-5000mv。
   * @param  voltage 电压值，量程0-5000，单位毫伏。
   * @return None
   */
  void outputVoltage(uint16_t voltage);

  /**
   * @fn  outputVoltageEEPROM
   * @brief  输出电压值范围0-5000mv，写入EEPROM，  
   * @n      这意味着DAC将保留当前电压输出  
   * @n      关机或复位后。
   * @param  voltage 电压值，量程0-5000，单位毫伏。
   * @return None
   */
  void outputVoltageEEPROM(uint16_t voltage);

  /**
   * @fn outputSin
   * @brief  输出一个正弦波
   * @param  amp 放大器值，输出正弦波振幅范围0-5000mv  
   * @param  freq frequency值，输出正弦波频率
   * @param  offset 输出正弦波直流偏置
   * @return None
   */
  void outputSin(uint16_t amp, uint16_t freq, uint16_t offset);

  /**
   * @fn outputTriangle
   * @brief  输出一个三角波    
   * @param  amp 输出三角波振幅范围0-5000mv  
   * @param  freq freq值，输出三角波频率
   * @param  offset 输出三角波的直流偏移量  
   * @param  dutyCycle dutyCycle值，设置三角波上升的百分比占整个周期的百分比。  
   * @n      取值范围0-100(0为只下降100，只上升段落)  
   * @return None
   */
  void outputTriangle(uint16_t amp, uint16_t freq, uint16_t offset, uint8_t dutyCycle);

```

## 兼容性

MCU                | Work Well | Work Wrong | Untested  | Remarks
------------------ | :----------: | :----------: | :---------: | -----
FireBeetle-ESP32   |      √       |             |            | 
FireBeetle-ESP8266 |      √       |             |            | 
Arduino uno        |       √      |             |            | 

## 版本

- 2018/01/15 1.0.0 版本.
- 2022/03/23 1.0.1 版本.

## 创作者

Written by DFRobot_xiaowu (xiao.wu@dfrobot.com), 2022. (Welcome to our [website](https://www.dfrobot.com/))
