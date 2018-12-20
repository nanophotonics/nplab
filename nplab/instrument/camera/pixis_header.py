def PI_V(v,c,n):

	return (((c)<<24)+((v)<<16)+(n))

# PicamParameter_ExposureTime = PI_V(FloatingPoint, Range,        23),
if __name__ == "__main__":
	FloatingPoint = 2
	Range = 2
	n = 23
	print PI_V(2,2,23)