from __future__ import division
from __future__ import print_function
from builtins import zip
from builtins import range
from past.utils import old_div
import matplotlib.pyplot as plt 
import numpy as np
from nplab import datafile
from skimage import feature, filters
import cv2
import math
from skimage.filters import gaussian
from skimage.segmentation import active_contour
from scipy.signal import convolve2d, correlate2d
import scipy.misc
from PIL import Image
import re
import sys
import scipy.ndimage as ndimage
import skimage


FILEPATH = "/home/ilya/Desktop/2018-02-17.h5"
FOLDERPATH = "ParticleScannerScan_2"
datafile = datafile.DataFile(FILEPATH,mode="r")
TAG = "Raman_White_Light_0Order.*"

TAGS = ["Infinity3_Bias_Image", "Infinity3_FirstBkgndWhiteLight_Image", "Infinity3_FirstWhiteLight_Image", "Infinity3_SecondWhiteLight_Image", "Infinity3_SecondWhiteLight_atBkgndLoc_Image", "Raman_Bias_0Order_int", "Raman_Bias_Spectrum_int", "Raman_Bias_Spectrum_wl", "Raman_Laser_0Order_atBkgndLoc_int", "Raman_Laser_0Order_int", "Raman_Laser_Spectrum_atBkgndLoc_int", "Raman_Laser_Spectrum_atBkgndLoc_wl", "Raman_Laser_Spectrum_int", "Raman_Laser_Spectrum_wl", "Raman_White_Light_0Order_int", "Raman_White_Light_Bkgnd_0Order_int", "Raman_White_Light_Bkgnd_Spectrum_int", "Raman_White_Light_Bkgnd_Spectrum_wl", "Raman_White_Light_Spectrum_int", "Raman_White_Light_Spectrum_wl"]
TAG = TAGS[10]
TAG = "Raman_Laser_0Order_int.*"
print("TAG",TAG)

# for k in datafile[FOLDERPATH]["Particle_100"].keys():
# 	print k

# import sys
# sys.exit(0)

images = []

x_min = 0
x_max = 200
dx = x_max-x_min

y_min = 700
y_max = 900
dy = y_max-y_min

N_images = 1

feature = np.zeros((21,21))

# from PIL import Image 
# npmask = np.array(Image.open("NPMASK.png"))
# npmask = npmask[:,:,0]
# npmask[npmask == 255] = 1
# npmask  =(2*npmask) -1 

# plt.imshow(npmask,cmap="gray")
# plt.show()
# import sys
# sys.exit(0)
def get_ellipse_contour(input_image):

	output_image = input_image

	# print np.min(output_image)
	# print np.max(output_image)

	output_image = (255*(output_image-np.min(output_image))/float(np.max(output_image)))
	output_image = output_image.astype(np.uint8)
	output_image = cv2.Canny(output_image,30,100)


	# dialation and
	dialate_kernel = np.ones((7,7),np.uint8)
	erode_kernel = np.ones((4,4),np.uint8)

	
	for i in range(0,3):

		output_image = cv2.dilate(output_image,dialate_kernel)
		output_image = cv2.erode(output_image,erode_kernel)
		
	#find contours of each image:
	output_image,contours, hierarchy = cv2.findContours(output_image,cv2.RETR_TREE ,cv2.CHAIN_APPROX_NONE )

	#find areas of the contours:
	contours_area = [(cnt,cv2.contourArea(cnt)) for cnt in contours]
	areas = [x[1] for x in contours_area]
	largest_contour = [cnt for (cnt,area) in contours_area if area == max(areas) ][0]

	# ellipse = cv2.fitEllipse(cnt)
	# print "ELLIPSE:", ellipse
	# cv2.ellipse(img,ellipse,(0,255,0),1)


	hull = cv2.convexHull(largest_contour)
	xs = hull[:,0,0]
	ys = hull[:,0,1]

	return np.asarray([xs,ys]).T



def get_images():
	particles = list(datafile[FOLDERPATH].keys())
	regex = re.compile(TAG)
	#laser zero order
	outp = []
	for particle in particles:
		try:
			measurements= list(datafile[FOLDERPATH][particle].keys())
			for m in measurements:
				if regex.match(m):
					outp.append( datafile[FOLDERPATH][particle][m])
		except Exception as e:
			print(e)
			print("Skipping:", particle)

	return outp

def get_contour_area(contour):
	return skimage.measure.moments(contour)[0,0]


from matplotlib.path import Path 
def make_vertex_mask(vertices,image_shape):
	polygonPath = Path(vertices)
	mask = np.zeros(image_shape)
	for i in range(image_shape[0]):
		for j in range(image_shape[1]):
			if polygonPath.contains_points([[j,i]]): #ordering of indices is wrong way around to usual, but works!
				mask[i,j] = 1
	return mask

def get_bounding_box(vertices):
	xs = vertices[:,0]
	ys = vertices[:,1]

	xmin,xmax= np.min(xs),np.max(xs)
	ymin,ymax = np.min(ys),np.max(ys)

	outp = np.asarray([[xmin,ymin],[xmin,ymax],[xmax,ymax],[xmax,ymin]])
	return outp,[xmin,ymin,xmax,ymax]

def apply_snake(image,contour):
	#contour - acts as best guess
	contour_xs = contour[:,0]
	contour_ys = contour[:,1]
	init = np.asarray([contour_xs,contour_ys]).T
	snake = skimage.segmentation.active_contour(image, init, alpha=0.005, beta=0.1, w_line=1e6, w_edge=1e7, gamma=0.01, bc='periodic', max_px_move=1.0, max_iterations=2500, convergence=0.1)
	snake_xs,snake_ys = snake[:,0],snake[:,1]
	return snake

def run_watershed(image,markers):
	return skimage.segmentation.watershed(image, markers, connectivity=1, offset=None, mask=None, compactness=0, watershed_line=False)


def kmeans(image,nsegments):
	return skimage.segmentation.slic(image, n_segments=100, compactness=10.0, max_iter=10, sigma=0, spacing=None, multichannel=True, convert2lab=False, enforce_connectivity=False, min_size_factor=0.5, max_size_factor=3, slic_zero=False)


def plot_multiscale(images,figname,valid = None):
	fig, axarr = plt.subplots(2,2*len(images), figsize=(36,4))
	for i,img in enumerate(images):
		axarr[0][2*i].imshow(img,cmap="gray")
		
		for x in range(img.shape[0]):
			xs = img[x,:]
			axarr[1][2*i].plot(xs)
		
		for y in range(img.shape[1]):
			ys = img[:,y]
			axarr[0][2*i+1].plot(ys)
		
	if valid != None:
		fig.suptitle("Matched pattern? : {0}".format(valid))

	plt.savefig("{0}_pyramid".format(figname))
	plt.close(fig)
	
	# fig.close()
	return 


# def circle_detect(edge_segmented, fill_segmented):
# 	from skimage import transform, draw
# 	hspaces = transform.hough_circle(fill_segmented, 10)
# 	accums, cxs,cys, rads = transform.hough_circle_peaks(hspaces,[10,])

# 	img = np.zeros((2*fill_segmented.shape[0],2*fill_segmented.shape[1]))
# 	for (cx,cy,rad) in zip(cxs,cys,rads):
# 		y,x= draw.circle_perimeter(cy,cx,rad)
# 		img[x,y]= 1

# 	fig, axarr = plt.subplots(2)
	
# 	axarr[0].imshow(fill_segmented)
	
# 	axarr[1].imshow(img)
# 	plt.show()


# def feature_extract(image):

# 	surf = cv2.xfeatures2d.SIFT_create()
# 	#compute keypoints and descriptors
# 	kp,des = surf.detectAndCompute(image.astype(np.uint8),None)

# 	# print surf.hessianThreshold
# 	print "KEYPOINTS",kp
# 	if len(kp)== 0:
# 		print "ZERO LENGTH KP - STOP"
# 		return 
# 	img2 = cv2.drawKeypoints(image,kp,None(255,0,0),4)
# 	plt.imshow(img2)
# 	plot.show()

def get_largest_binary_convex_hull(image):
	#assume image is binary
	return skimage.morphology.convex_hull_object(image)

def get_lowest_level_set(image):
	level_set = np.zeros(image.shape)
	level_set[image < 0.25] = 1
	return level_set 
def process_image(image,figname):
	contour = get_ellipse_contour(image)
	ellipse = cv2.fitEllipse(contour)

	bbox,boxlims = get_bounding_box(contour)
	mask =make_vertex_mask(bbox,image.shape)
	
	contour_xs = contour[:,0]
	contour_ys = contour[:,1]

	masked_image = mask*image
	masked_image = masked_image[boxlims[1]+1:min(80,boxlims[3]),boxlims[0]+1:min(80,boxlims[2])] 

	k = np.sqrt(2)
	sigma = 1.0
	sigmas = [sigma,sigma*k**2,sigma*k**3,sigma*k**4,sigma*k**5]
	gaussians = [skimage.filters.gaussian(masked_image,s) for s in sigmas]
	DoG = []
	for i in range(1,len(gaussians)):
		DoG.append(gaussians[i]-gaussians[i-1])

	print("DoGs-------------------------", len(DoG))
	for d in DoG:
		print(d)
	DoG = [d + np.min(d) for d in DoG]
	DoG = [d-np.min(d) for d in DoG]
	DoG = [old_div(d,np.max(d)) for d in DoG]

	prod = DoG[1]*DoG[2]*DoG[3]
	prod = prod - np.min(prod)
	prod = old_div(prod,np.max(prod))

	level_set = get_lowest_level_set(prod)
	particle_contour = get_ellipse_contour(level_set)
	particleMask = make_vertex_mask(particle_contour,prod.shape)
	np_only = prod-prod*((get_largest_binary_convex_hull(level_set)-1)*-1)

	convolved = skimage.feature.canny(np_only,1,0.2,0.7)#correlate2d(np_only,npmask)
	
	convolved = skimage.morphology.binary_closing(convolved)
	convolved = skimage.morphology.binary_dilation(convolved)
	

	edge_segmented = skimage.measure.label(convolved)

	fill_segmented = np.zeros(edge_segmented.shape)
	fill_segmented[edge_segmented==0] = 1
	fill_segmented = skimage.measure.label(fill_segmented)

	fill_segments = separate_segments(fill_segmented)

	# edge_segments = separate_segments(edge_segmented)
	# for i in range(len(edge_segments)):
		
	# 	(cx,cy) = CoM_image(edge_segments[i])
	# 	axarr[0][i].imshow(edge_segments[i],cmap="gray")
	# 	cv2.circle(edge_segments[i],(cx,cy),1,(255,255,0),1)
		
	def valid_segment(img, cx,cy,max_radius=5):
		for x in range(img.shape[0]):
			for y in range(img.shape[1]):
				if img[x,y] > 0:
					if  (x - cx)**2 + (y-cy)**2 < max_radius**2:
						pass 
					else:
						return False
		return True

	def nonzero_pixels(image):
		count = 0
		for i in range(image.shape[0]):
			for j in range(image.shape[1]):
				if image[i,j] > 0 :
					count = count + 1
		return count

	def has_valid_segment(image,max_radius = 5):
		separated = separate_segments(image)
		valid_segments = []

		for i in range(len(separated)):
			img = separated[i]
			(cx,cy) = CoM_image(img)
			if valid_segment(img,cx,cy,max_radius) and nonzero_pixels(img)>4:
				ys,xs = draw.circle_perimeter(cy,cx, max_radius)
				for (x,y) in zip(xs,ys):
					if (x >=0 and x < img.shape[0]) and (y >=0 and y < img.shape[1]):
						img[x,y] = 1
				# img[xs,ys] = 1 
				valid_segments.append(img)

		return valid_segments

	filled_valid_segments = has_valid_segment(fill_segmented, 5)
	edge_valid_segments = has_valid_segment(edge_segmented,8)

	if len(filled_valid_segments) > 0:
		filled_valid = np.sum(np.asarray(filled_valid_segments),axis=0)
	else:
		filled_valid = np.zeros(masked_image.shape)

	if len(edge_valid_segments) > 0:
		edge_valid = np.sum(np.asarray(edge_valid_segments),axis=0)
	else:
		edge_valid = np.zeros(masked_image.shape)



	images = [masked_image] + DoG + [prod,np_only,edge_segmented, fill_segmented,filled_valid, edge_valid]
	plot_multiscale(images,figname,valid="Filled: {0},Edge: {1}".format(len(filled_valid_segments) > 0, len(edge_valid_segments) > 0))

	return images

def zero_pad(img,xdim,ydim):
	if img.shape[0] < xdim or img.shape[1] < ydim:
		outp = np.zeros((xdim,ydim))
		outp[0:img.shape[0],0:img.shape[1]] = img
		return outp
	elif img.shape[0] == xdim and img.shape[1] == ydim:
		return img
	else:
		raise ValueError("Failed!")

def separate_segments(image):
	image = image.astype(int)
	image = image - np.min(image)
	assert(np.min(image)==0)
	segments = []*np.max(image)
	# print segments

	for i in range(np.max(image)+1):
		x = np.zeros(image.shape)
		x[image==i] = 1
		segments.append(x)
	return segments


def CoM_image(image):

	it = 0
	jt = 0
	num = 0
	for i in range(image.shape[0]):
		for j in range(image.shape[1]):
			if image[i,j] > 0:
				it = it + i
				jt = jt + j
				num = num + 1
	# num = float(image.shape[0]*image.shape[1])
	num = float(num)
	cx = int(round(old_div(it,num)))
	cy = int(round(old_div(jt,num)))

	# M = cv2.moments(image)
	# print M
	# cx = int(M['m10']/float(M['m00']))
	# cy = int(M['m01']/float(M['m00']))
	return (cx,cy)


from skimage import draw
def main():
	images = get_images()

	images = [image[50:150,750:850] for image in images]
	
	# i=49
	# image = images[i]
	# test_img = process_image(image,"fig_test",-1,-1)
	# xdim,ydim = test_img[0].shape[0],test_img[0].shape[1]
	# xdim = image.shape[0]
	# ydim = image.shape[1]
	limit = len(images)
	multiscale_images = []
		
	for i,image in enumerate(images):
		if i < 2:
			pass
		elif i < limit:
			output_img =process_image(image,"fig{}".format(i))
			multiscale_images=multiscale_images + [output_img]

	xmax = 0
	ymax = 0
	for imgs in multiscale_images:
		dimx, dimy = imgs[0].shape[0],imgs[0].shape[1]
		xmax,ymax = max(dimx,xmax),max(dimy,ymax)
		for i in imgs:
			assert((i.shape[0],i.shape[1])==(dimx,dimy))


	# segmented = [ (multiscale_images[i][-2][:][:],multiscale_images[i][-1][:][:]) for i in range(len(multiscale_images))]

	# # print segmented
	# for (edge,fill) in segmented:
	# 	edge_segments = separate_segments(edge)
	# 	fill_segments = separate_segments(fill)

	# 	print "LENGTHS",
	# 	print len(edge_segments)
	# 	print len(fill_segments)
	# 	fig, axarr = plt.subplots(2,max(len(edge_segments),len(fill_segments)))

	# 	for i in range(len(edge_segments)):
			
	# 		(cx,cy) = CoM_image(edge_segments[i])
	# 		axarr[0][i].imshow(edge_segments[i],cmap="gray")
	# 		cv2.circle(edge_segments[i],(cx,cy),1,(255,255,0),1)
			
	# 	for i in range(len(fill_segments)):
	# 		(cx,cy) = CoM_image(fill_segments[i])

	# 		img = fill_segments[i]
	# 		max_radius = 5
	# 		valid = True
	# 		for x in range(img.shape[0]):
	# 			for y in range(img.shape[1]):
	# 				if img[x,y] > 0:
	# 					if  (x - cx)**2 + (y-cy)**2 < max_radius**2:
	# 						pass 
	# 					else:
	# 						valid = False



	# 		y,x = draw.circle_perimeter(cy,cx, max_radius)
	# 		img[x,y] = 2 

	# 		axarr[1][i].imshow(img,cmap="gray")
	# 		title = "Valid: {0}".format(valid)
	# 		axarr[1][i].set_title(title)			
	# 		# cv2.circle(fill_segments[i],(cx,cy),1,(255,255,0),1)
	# 	plt.tight_layout()
	# 	plt.show()


main()
# 