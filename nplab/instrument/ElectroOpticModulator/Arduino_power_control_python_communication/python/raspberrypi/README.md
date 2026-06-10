# DFRobot_MCP4725

* [中文版](./README_CN.md)

MCP4725 is a 12-bit iic-driven high precision DAC module. It has an EEPROM inside, means that the DAC will retain the current voltage output after power-down or reset.


![Product Image](../../resources/images/DFR0552.png) 

## Product Link(https://www.dfrobot.com.cn/goods-1728.html)
    SKU: DFR0552 

## Table of Contents
  - [Summary](#summary)
  - [Installation](#installation)
  - [Methods](#methods)
  - [Compatibility](#compatibility)
  - [History](#history)
  - [Credits](#credits)

## Summary
Provides an Arduino library for reading and interpreting Bosch MCP4725 data over I2C.

## Installation
1. To use this library, first download the library file<br>
```python
sudo git clone https://github.com/DFRobot/DFRobot_MCP4725
```
2. Open and run the routine. To execute a routine demo_x.py, enter python demo_x.py in the command line. For example, to execute the demo_set_current.py routine, you need to enter :<br>

```python
python demo_set_current.py 
or
python2 demo_set_current.py 
or 
python3 demo_set_current.py
```

## Methods

```python
  def setAddr_MCP4725(self,addr):
    '''!
      @fn setAddr_MCP4725
      @brief init MCP4725
      @param addr Init the IIC address.
    '''
  
  def set_ref_voltage(self,vol):
    '''!
      @fn set_ref_voltage
      @brief Setting the base voltage of DAC must equal the power supply voltage, and the unit is millivolt
      @param  vol Voltage value, range 0-5000, unit millivolt.
    '''
      
  def output_voltage(self,vol):
    '''!
      @fn output_voltage
      @brief Output voltage value range 0-5000mv.
      @param  vol Voltage value, range 0-5000, unit millivolt.
    '''

  def output_voltage_EEPROM(self,vol):
    '''!
      @fn output_voltage_EEPROM
      @brief  Output voltage value range 0-5000mv and write to the EEPROM,
      @n      meaning that the DAC will retain the current voltage output
      @n      after power-down or reset.
      @param  vol Voltage value, range 0-5000, unit millivolt.
    '''
      
  def input_voltage(self):
    '''!
      @fn input_voltage
      @brief Get the input voltage value
    '''
  
  def output_sin(self,amp,freq,offset):
    '''!
      @fn outputSin
      @brief  Output a sine wave.
      @param  amp amp value, output sine wave amplitude range 0-5000mv
      @param  freq freq value, output sine wave frequency
      @param  offset offset value, output sine wave DC offset 
    '''

  def output_triangle(self,amp,freq,offset,dutyCycle):
    '''!
      @fn outputTriangle
      @brief  Output a sine wave.    
      @param  amp amp value, output triangular wave amplitude range 0-5000mv
      @param  freq freq value, output the triangle wave frequency
      @param  offset offset value, output the DC offset of the triangle wave
      @param  dutyCycle dutyCycle value, set the rising percentage of the triangle wave as a percentage of the entire cycle.
      @n      Value range 0-100 (0 for only the decline of 100, only the rise of paragraph)
    '''
  
```
## Compatibility

| MCU         | Work Well | Work Wrong | Untested | Remarks |
| ------------ | :--: | :----: | :----: | :--: |
| RaspberryPi2 |      |        |   √    |      |
| RaspberryPi3 |      |        |   √    |      |
| RaspberryPi4 |  √   |        |        |      |

* Python Version

| Python  | Work Well | Work Wrong | Untested | Remarks |
| ------- | :--: | :----: | :----: | ---- |
| Python2 |  √   |        |        |      |
| Python3 |  √   |        |        |      |


## History

- 2018/01/15 Version 1.0.0 released.
- 2022/03/23 Version 1.0.1 released.
- 
## Credits

Written by DFRobot_xiaowu (xiao.wu@dfrobot.com), 2022. (Welcome to our [website](https://www.dfrobot.com/))
