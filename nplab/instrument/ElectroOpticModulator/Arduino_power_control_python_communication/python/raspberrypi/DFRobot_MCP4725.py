
'''!
  @file DFRobot_MCP4725.py
  @brief This is a base library for DAC modules
  @copyright Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com)
  @license The MIT License (MIT)
  @author Tangjie(jie.tang@dfrobot.com)
  @version V1.0.1
  @date 2018-01-15
  @url https://github.com/DFRobot/DFRobot_MCP4725
'''
import smbus
import time
import datetime
# Get I2C bus
bus = smbus.SMBus(1)

# I2C address of the device
MCP4725A0_IIC_Address0              = 0x60
MCP4725A0_IIC_Address1              = 0x61
MCP4725_Write_CMD             = 0x40
MCP4725_WriteEEPROM_CMD       = 0X60
MCP4725_NORMAL_MODE               = 0X00 
MCP4725_POWER_DOWN_1KRES            = 0X01 
MCP4725_POWER_DOWN_100KRES      = 0X02
MCP4725_POWER_DOWN_500KRES      = 0X03 

addr_G=MCP4725A0_IIC_Address0
OutVol_G=1000
FullSine5Bit = [
  2048,2447,2831,3185,3495,3750,3939,4056,
  4095,4056,3939,3750,3495,3185,2831,2447,
  2048,1648,1264, 910, 600, 345, 156,  39,
     0,  39, 156, 345, 600, 910,1264,1648]

FullSine6Bit = [
  2048, 2248, 2447, 2642, 2831, 3013, 3185, 3346,
  3495, 3630, 3750, 3853, 3939, 4007, 4056, 4085,
  4095, 4085, 4056, 4007, 3939, 3853, 3750, 3630,
  3495, 3346, 3185, 3013, 2831, 2642, 2447, 2248,
  2048, 1847, 1648, 1453, 1264, 1082,  910,  749,
   600,  465,  345,  242,  156,   88,   39,   10,
     0,   10,   39,   88,  156,  242,  345,  465,
   600,  749,  910, 1082, 1264, 1453, 1648, 1847]

FullSine7Bit = [
  2048, 2148, 2248, 2348, 2447, 2545, 2642, 2737,
  2831, 2923, 3013, 3100, 3185, 3267, 3346, 3423,
  3495, 3565, 3630, 3692, 3750, 3804, 3853, 3898,
  3939, 3975, 4007, 4034, 4056, 4073, 4085, 4093,
  4095, 4093, 4085, 4073, 4056, 4034, 4007, 3975,
  3939, 3898, 3853, 3804, 3750, 3692, 3630, 3565,
  3495, 3423, 3346, 3267, 3185, 3100, 3013, 2923,
  2831, 2737, 2642, 2545, 2447, 2348, 2248, 2148,
  2048, 1947, 1847, 1747, 1648, 1550, 1453, 1358,
  1264, 1172, 1082,  995,  910,  828,  749,  672,
   600,  530,  465,  403,  345,  291,  242,  197,
   156,  120,   88,   61,   39,   22,   10,    2,
     0,    2,   10,   22,   39,   61,   88,  120,
   156,  197,  242,  291,  345,  403,  465,  530,
   600,  672,  749,  828,  910,  995, 1082, 1172,
  1264, 1358, 1453, 1550, 1648, 1747, 1847, 1947]

FullSine8Bit = [
  2048, 2098, 2148, 2198, 2248, 2298, 2348, 2398,
  2447, 2496, 2545, 2594, 2642, 2690, 2737, 2784,
  2831, 2877, 2923, 2968, 3013, 3057, 3100, 3143,
  3185, 3226, 3267, 3307, 3346, 3385, 3423, 3459,
  3495, 3530, 3565, 3598, 3630, 3662, 3692, 3722,
  3750, 3777, 3804, 3829, 3853, 3876, 3898, 3919,
  3939, 3958, 3975, 3992, 4007, 4021, 4034, 4045,
  4056, 4065, 4073, 4080, 4085, 4089, 4093, 4094,
  4095, 4094, 4093, 4089, 4085, 4080, 4073, 4065,
  4056, 4045, 4034, 4021, 4007, 3992, 3975, 3958,
  3939, 3919, 3898, 3876, 3853, 3829, 3804, 3777,
  3750, 3722, 3692, 3662, 3630, 3598, 3565, 3530,
  3495, 3459, 3423, 3385, 3346, 3307, 3267, 3226,
  3185, 3143, 3100, 3057, 3013, 2968, 2923, 2877,
  2831, 2784, 2737, 2690, 2642, 2594, 2545, 2496,
  2447, 2398, 2348, 2298, 2248, 2198, 2148, 2098,
  2048, 1997, 1947, 1897, 1847, 1797, 1747, 1697,
  1648, 1599, 1550, 1501, 1453, 1405, 1358, 1311,
  1264, 1218, 1172, 1127, 1082, 1038,  995,  952,
   910,  869,  828,  788,  749,  710,  672,  636,
   600,  565,  530,  497,  465,  433,  403,  373,
   345,  318,  291,  266,  242,  219,  197,  176,
   156,  137,  120,  103,   88,   74,   61,   50,
    39,   30,   22,   15,   10,    6,    2,    1,
     0,    1,    2,    6,   10,   15,   22,   30,
    39,   50,   61,   74,   88,  103,  120,  137,
   156,  176,  197,  219,  242,  266,  291,  318,
   345,  373,  403,  433,  465,  497,  530,  565,
   600,  636,  672,  710,  749,  788,  828,  869,
   910,  952,  995, 1038, 1082, 1127, 1172, 1218,
  1264, 1311, 1358, 1405, 1453, 1501, 1550, 1599,
  1648, 1697, 1747, 1797, 1847, 1897, 1947, 1997]
class MCP4725():
  def setAddr_MCP4725(self,addr):
    '''!
      @fn setAddr_MCP4725
      @brief init MCP4725
      @param addr Init the IIC address.
    '''
    global addr_G
    addr_G = addr   
  def set_ref_voltage(self,vol):
    '''!
      @fn set_ref_voltage
      @brief Setting the base voltage of DAC must equal the power supply voltage, and the unit is millivolt
      @param  vol Voltage value, range 0-5000, unit millivolt.
    '''
    global voltage_G
    voltage_G = vol 
  def output_voltage(self,vol):
    '''!
      @fn output_voltage
      @brief Output voltage value range 0-5000mv.
      @param  vol Voltage value, range 0-5000, unit millivolt.
    '''
    global addr_G   
    global voltage_G
    bus.write_word_data(addr_G,MCP4725_Write_CMD | (MCP4725_NORMAL_MODE<<1) ,int((vol/float(voltage_G))*255))
  def output_voltage_EEPROM(self,vol):
    '''!
      @fn output_voltage_EEPROM
      @brief  Output voltage value range 0-5000mv and write to the EEPROM,
      @n      meaning that the DAC will retain the current voltage output
      @n      after power-down or reset.
      @param  vol Voltage value, range 0-5000, unit millivolt.
    '''
    global addr_G
    global voltage_G
    bus.write_word_data(addr_G,MCP4725_WriteEEPROM_CMD | (MCP4725_NORMAL_MODE<<1) ,int((vol/float(voltage_G))*255))
  def input_voltage(self):
    '''!
      @fn input_voltage
      @brief Get the input voltage value
    '''
    global OutVol_G
    OutVol_G = int(input("Please input voltage = "))
    while OutVol_G > 5000 :
      OutVol_G = int(input("Please input voltage = "))
    return OutVol_G
  def output_sin(self,amp,freq,offset):
    '''!
      @fn outputSin
      @brief  Output a sine wave.
      @param  amp amp value, output sine wave amplitude range 0-5000mv
      @param  freq freq value, output sine wave frequency
      @param  offset offset value, output sine wave DC offset 
    '''
    global addr_G
    global voltage_G
    if(freq < 6):
      num = 256
    elif( 6 <= freq and freq <= 10):
      num = 128
    elif(10 < freq and freq <22):
      num = 64
    elif(22 <= freq and freq <= 42):
      num = 32
    else:
      num = 32
    if(freq > 42):
      freq = 42
    frame = int(1000000/(freq*(num+1)))
    for i in range(0,num-1):
      start = datetime.datetime.now()
      if num == 256:
        data = (FullSine8Bit[i] - 2047) * (amp/float(4096)) *2
      elif num == 128:
        data = (FullSine7Bit[i] - 2047) * (amp/float(4096)) *2
      elif num == 64:
        data = (FullSine6Bit[i] - 2047) * (amp/float(4096)) *2
      elif num == 32:
        data = (FullSine5Bit[i] - 2047) * (amp/float(4096)) *2
      else:
        data = (FullSine5Bit[i] - 2047) * (amp/float(4096)) *2
      data = int(data + offset)
      if data <= 0:
        data = 0
      if data >= voltage_G:
        data = voltage_G
      bus.write_word_data(addr_G,MCP4725_Write_CMD | (MCP4725_NORMAL_MODE<<1) ,int((data/float(voltage_G))*255))
      endtime = datetime.datetime.now()
      looptime = (endtime - start).microseconds
      while looptime <= frame:
        endtime = datetime.datetime.now()
        looptime = (endtime - start).microseconds
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
    maxV = amp
    if freq > 20:
      num = 16
    elif freq >= 11 and freq<=20:
      num = 32
    else:
      num = 64
    frame = 1000000/(freq*num*2);
    if dutyCycle > 100:
      dutyCycle = 100
    if dutyCycle < 0:
      dutyCycle = 0
    up_num = (2*num)*(float(dutyCycle)/100)
    down_num = ((2*num) - up_num)
    if up_num  == 0:
      up_num = 1
    for i in range(0,(maxV-int(maxV/up_num)-1),int(maxV/up_num)):
      starttime = datetime.datetime.now()
      enterV = i + offset
      if enterV > voltage_G:
        enterV = voltage_G
      elif enterV < 0:
        enterV = 0
      bus.write_word_data(addr_G,MCP4725_Write_CMD | (MCP4725_NORMAL_MODE<<1) ,int((enterV/float(voltage_G))*255))
      endtime = datetime.datetime.now()
      looptime = (endtime - starttime).microseconds
      while looptime <= frame:
        endtime = datetime.datetime.now()
        looptime = (endtime - starttime).microseconds
    for i in range(0,int(down_num-1)):
      starttime = datetime.datetime.now()
      enterV = maxV-1-(i*int(maxV/down_num))+offset
      if enterV > voltage_G:
        enterV = voltage_G
      elif enterV < 0:
        enterV = 0
      bus.write_word_data(addr_G,MCP4725_Write_CMD | (MCP4725_NORMAL_MODE<<1) ,int((enterV/float(voltage_G))*255))
      endtime = datetime.datetime.now()
      looptime = (endtime - starttime).microseconds
      while looptime <= frame:
        endtime = datetime.datetime.now()
        looptime = (endtime - starttime).microseconds
