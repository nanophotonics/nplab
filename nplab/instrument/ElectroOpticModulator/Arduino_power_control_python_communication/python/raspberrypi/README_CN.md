# DFRobot_MCP4725

* [English Version](./README.md)

MCP4725是一个12位ic驱动的高精度DAC模块。 它内部有一个EEPROM，这意味着DAC在掉电或复位后将保持当前电压输出。  


![产品效果图](../../resources/images/DFR0552.png) 

## Product Link(https://www.dfrobot.com.cn/goods-1728.html)
    SKU: DFR0552 

## Table of Contents
  - [概述](#概述)
  - [库安装](#库安装)
  - [方法](#方法)
  - [兼容性](#兼容性)
  - [历史](#历史)
  - [创作者](#创作者)

## 概述

提供Arduino库读取和解释博世的MCP4725的I2C数据。  

## 库安装
1. 下载库至树莓派，要使用这个库，首先要将库下载到Raspberry Pi，命令下载方法如下:<br>
```python
sudo git clone https://github.com/DFRobot/DFRobot_MCP4725
```
2. 打开并运行例程，要执行一个例程demo_x.py，请在命令行中输入python demo_x.py。例如，要执行 demo_set_current.py例程，你需要输入:<br>

```python
python demo_set_current.py 
或 
python2 demo_set_current.py 
或 
python3 demo_set_current.py
```

## 方法

```python
  def setAddr_MCP4725(self,addr):
    '''!
      @fn setAddr_MCP4725
      @brief 初始化 MCP4725
      @param addr I2C设备地址
    '''
    
  def set_ref_voltage(self,vol):
    '''!
      @fn set_ref_voltage
      @brief 设置DAC的基准电压必须等于电源电压，单位为毫伏  
      @param  vol 电压值，量程0-5000，单位毫伏。
    '''
      
  def output_voltage(self,vol):
    '''!
      @fn output_voltage
      @brief 输出电压值范围0-5000mv。
      @param  vol 电压值，量程0-5000，单位毫伏。
    '''

  def output_voltage_EEPROM(self,vol):
    '''!
      @fn output_voltage_EEPROM
      @brief  输出电压值范围0-5000mv，写入EEPROM，  
      @n      这意味着DAC将保留当前电压输出  
      @n      关机或复位后。
      @param  vol 电压值，量程0-5000，单位毫伏。
    '''
      
  def input_voltage(self):
    '''!
      @fn input_voltage
      @brief 获取输入电压值
    '''
  
  def output_sin(self,amp,freq,offset):
    '''!
      @fn outputSin
      @brief   输出一个正弦波
      @param  amp 放大器值，输出正弦波振幅范围0-5000mv 
      @param  freq frequency值，输出正弦波频率
      @param  offset 输出正弦波直流偏置 
    '''

  def output_triangle(self,amp,freq,offset,dutyCycle):
    '''!
      @fn outputTriangle
      @brief  输出一个三角波       
      @param  amp 输出三角波振幅范围0-5000mv 
      @param  freq freq值，输出三角波频率
      @param  offset 输出三角波的直流偏移量 
      @param  dutyCycle dutyCycle值，设置三角波上升的百分比占整个周期的百分比。
      @n      取值范围0-100(0为只下降100，只上升段落)  
      '''
    
```

## 兼容性

| 主板         | 通过 | 未通过 | 未测试 | 备注 |
| ------------ | :--: | :----: | :----: | :--: |
| RaspberryPi2 |      |        |   √    |      |
| RaspberryPi3 |      |        |   √    |      |
| RaspberryPi4 |  √   |        |        |      |

* Python 版本

| Python  | 通过 | 未通过 | 未测试 | 备注 |
| ------- | :--: | :----: | :----: | ---- |
| Python2 |  √   |        |        |      |
| Python3 |  √   |        |        |      |


## 历史

- 2018/01/15 1.0.0 版本.
- 2022/03/23 1.0.1 版本.

## 创作者

Written by DFRobot_xiaowu (xiao.wu@dfrobot.com), 2022. (Welcome to our [website](https://www.dfrobot.com/))





