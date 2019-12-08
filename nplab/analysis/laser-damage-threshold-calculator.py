# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from past.utils import old_div
import numpy as np 
#Script to get rough estimates of damage thresholds for optics components as specified on Thorlabs

#Source of code is the Thorlabs tutorial on Laser Induced Damage Thresholds:
#https://www.thorlabs.com/tutorials.cfm?tabID=762473B5-84EE-49EB-8E93-375E0AA803FA
#author: im354

########################################
#		YOUR LASER PARAMETERS
########################################
beam_diameter = 1e-3 #[units: m]
laser_output_power = 6 #[units: W]
laser_wavelength =  633e-9 #[units: m]
laser_type = "pulsed"
beam_profile = "gaussian"
laser_pulse_duration = 1e-9 #[units: seconds]
laser_pulse_repetition_rate =  60e6 #[units: Hz]

###################################################
#		YOUR OPTIC DAMAGE (LIDT) PARAMETERS
###################################################
lidt_wavelength = 353e-9 #[units: n]
lidt_maximum_energy_density = 0.075 #[units: J/cm^2]
lidt_pulse_duration = 10e-9
pulse_repetition_rate = 10

###################################################
# PROGRAM START
###################################################
LASER_TYPES = ["cw", "pulsed"]
BEAM_PROFILES = ["tophat", "gaussian"]

#Convert units:
lidt_maximum_energy_density = lidt_maximum_energy_density * 10000 #[units: J/m^2]

#verify user input
assert(beam_profile in BEAM_PROFILES)
assert(laser_type in LASER_TYPES)


#CW regime - Thermal damage
if laser_type == "cw" or (laser_type == "pulsed" and laser_pulse_duration >= 1e-7):
	print("-----CW-----")
	linear_power_density = old_div(laser_output_power,beam_diameter) #[units: W/cm - see Thorlabs LIDT tutorial]

	if beam_profile == "gaussian":
		linear_power_density= linear_power_density*2.0 # adjust for peak power in gaussian beam

	wavelength_adjusted_lidt = linear_power_density * (laser_wavelength/float(lidt_wavelength))

	print("[CW] Wavelength adjusted LIDT for your laser:", wavelength_adjusted_lidt)
	print("[CW] Specified LIDT for Optic", lidt_maximum_energy_density)

	if wavelength_adjusted_lidt > lidt_maximum_energy_density:
		print("[CW] !---WARNING---! : LIDT threshold specification exceeded for optic ")

	else:
		print("[CW] !---DONE---! : LIDT threshold NOT exceeded for optic")


#Pulsed regime - dielectric breakdown damage
if laser_type == "pulsed":
	print("-----PULSED-----")
	beam_area = np.pi*(beam_diameter/2.0)**2
	pulse_energy = old_div(laser_output_power,laser_pulse_repetition_rate)

	print("[Pulsed] Pulse energy: {0} [J]".format(pulse_energy))
	print("[Pulsed] Beam area {0} [m^2]".format(beam_area))
	
	area_energy_density = old_div(pulse_energy,beam_area) 
	if beam_profile == "gaussian":
		area_energy_density = area_energy_density * 2.0 #adjust for peak power in gaussian beam
	print("[Pulsed] Beam Energy Density (Beam Profile Adjusted) [per Pulse] {} [J/m^2]".format(area_energy_density))

	if laser_pulse_duration >= 1e-9 and laser_pulse_duration < 1e-7:
		print("[Pulsed] Damage Mechanism: Dielectric breakdown")
	elif laser_pulse_duration >= 1e-7 and laser_pulse_duration < 1e-4:
		print("[Pulsed] Damage Mechanism: Dielectric breakdown or Thermal")
	elif laser_pulse_duration > 1e-7:
		print("[Pulsed] Damage Mechanism: Thermal")

	elif laser_pulse_duration < 1e-9 : 
		print("[Pulsed] Damage Mechanism: Avalanche Ionization, WARNING - NO comparison for Thorlabs Damage Specs")

	adjusted_lidt = area_energy_density* np.sqrt(old_div(laser_pulse_duration,lidt_pulse_duration))*np.sqrt(laser_wavelength/float(lidt_wavelength))

	print("[Pulsed] Adjusted (wavelength, pulse duration) LIDT for your laser:",adjusted_lidt)
	print("[Pulsed] Specified LIDT for Optic", lidt_maximum_energy_density)
	if adjusted_lidt > lidt_maximum_energy_density:
		print("[Pulsed] !---WARNING---! : LIDT threshold specification exceeded for optic ")

	else:
		print("[Pulsed] !---DONE---! : LIDT threshold NOT exceeded for optic")
