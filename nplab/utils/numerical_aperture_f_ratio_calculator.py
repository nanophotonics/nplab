from __future__ import division
from __future__ import print_function
from past.utils import old_div
import numpy as np 
import cmath

#definitions
#	Numerical Aperture: NA = n*sin(alpha) = n*(r/x)
#	f-ratio: f/# = f/d

# n - refractive index of medium
# r - radius of beam hitting lens
# f - focal length of lens
# d - diameter of beam hitting lens
#	d = 2*r
# x - cone side length of ray coming into focus
#	x^2 = r^2+f^2 

def f_ratio(f,d):
	return float(f)/d 

def numerical_aperture(alpha,n=1.0):
	return n*np.sin(alpha)

def numerical_aperture(r,x,n=1.0):
	return n*(float(r)/x)

def x_from_radius(f,r):
	return np.sqrt(r**2 + f**2)

def x_from_diameter(f,d):
	return 	x_from_radius(f,d/2.0)

def alpha_from_radius(f,r):
	x = x_from_radius(f,r)
	return cmath.asin(old_div(np.float(r),x))%(2*np.pi)

def alpha_from_diameter(f,d):
	r = d/2.0
	return alpha_from_radius(f,r)


if __name__ == "__main__":
	
	f = 75e-3
	d = 13.14e-3
	fratio = f/d

	print(fratio)
	# telescope_lens_1 = 50e-3 
	# telescope_lens_2 = 250e-3 
	# d0 = 2e-3 

	# d1 = d0*(telescope_lens_2/telescope_lens_1)

	# focusing_f = 50e-3

	# print "telescope_lenses:({0}mm,{1}mm), initial_diameter:{2}mm, final_diameter:{3}mm, focusing_f:{4}m".format(telescope_lens_1/1e-3, telescope_lens_2/1e-3, d0/1e-3,d1/1e-3,focusing_f/1e-3)

	# incoming_alpha = alpha_from_diameter(f=focusing_f, d = d1)

	# print "Incomking alpha:",180*incoming_alpha/np.pi
	# # grating_min = 68e-3
	# # grating_max = 84e-3 

	# mono_f_ratio = 4.1 
	# mono_f = 300e-3
	# mono_d = 60e-3
	
	# mono_alpha = alpha_from_diameter(f=mono_f,d = mono_d)
	# print "Monochromator alpha:", 180*mono_alpha/np.pi


