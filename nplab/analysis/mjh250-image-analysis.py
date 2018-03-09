import matplotlib.pyplot as plt 
import numpy as np
from nplab import datafile
from skimage import feature, filters
import cv2
import math
FILEPATH = "R:\\3-Temporary\im354\mjh250\\2018-02-17.h5"

FOLDERPATH = "ParticleScannerScan_2"
datafile = datafile.DataFile(FILEPATH,mode="r")
from scipy.signal import convolve2d
images = []

x_min = 0
x_max = 200
dx = x_max-x_min

y_min = 700
y_max = 900
dy = y_max-y_min

N_images = 1

circle_mask = np.zeros((50,50))
r = 50; center = (25,25)
for i in range(circle_mask.shape[0]):
	for j in range(circle_mask.shape[1]):
		if (i-center[0])**2 + (j-center[1])**2 < r^2:
			circle_mask[i][j] ==1

import scipy.misc
from PIL import Image

def process(input_image):

	output_image = input_image

	print np.min(output_image)
	print np.max(output_image)

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
	
	# hull = cv2.convexHull(largest_contour)

	# drawing = np.zeros(input_image.shape, np.uint8)

	# cv2.drawContours(drawing,[hull],0,(255,255,255),2)


	# M = cv2.moments(hull)

	# #centroid:
	# cx = int(M['m10']/M['m00'])
	# cy = int(M['m01']/M['m00'])

	# output_image = drawing

	# return output_image[0:dx,0:dy],(cx,cy), largest_contour

	return largest_contour

from skimage.filters import gaussian
from skimage.segmentation import active_contour

def main():
	particles = datafile[FOLDERPATH].keys()
	import re
	import sys
	regex = re.compile("Raman_White_Light_0Order.*")
	count = 0
	images = []
	for particle in particles:
		try:
			measurements= datafile[FOLDERPATH][particle].keys()
			for m in measurements:
				if regex.match(m):
					image = datafile[FOLDERPATH][particle][m]
					image = image[x_min:x_max,y_min:y_max]
					count = count + 1
					if count > N_images:
						break
						pass
					images.append(image)

		except Exception as e:
			print e
			# return
			print "Skipping:", particle
		if count > N_images:
			break
			pass

	#get the largest contour of each image
	# images = [images[5]]

	
	
	contours = [process(image) for image in images]
	
	#get length of square that bound ALL images
	side_length = 0
	for cnt in contours:
		x,y,w,h = cv2.boundingRect(cnt)
		side_length = max(side_length,w,h)
	
	
	#make linear image

	output_images = []
	
	cut_images = []
	smoothed_images = []
	circle_images = []
	snakes = []
	output_image_cut = np.zeros((side_length,len(images)*side_length))
	for i,image in enumerate(images):

		cnt = contours[i]

		#bounding rectangle:
		x,y,_,_ = cv2.boundingRect(cnt)
		#bounding ellipsoid
		ellipse = cv2.fitEllipse(cnt)


		img = image[0:dx,0:dy]
		cut_image = img[y:y+side_length,x:x+side_length]



		#draw rectanlge and circle
		# cv2.rectangle(img,(x,y),(x+side_length,y+side_length),(0,255,0),1)
		# cv2.ellipse(img,ellipse,(0,255,0),1)


		output_images.append(img)
		f = 1.0/9
		cut_images.append(cut_image)
		


		smoothed_image = convolve2d(cut_image,np.array([[f,f,f],[f,f,f],[f,f,f]]))
		smoothed_images.append(smoothed_image)
		
		#-----Active contour methods-----
		# s = np.linspace(0,2*np.pi,10)
		# x = np.asarray([0]*10) + np.linspace(0,smoothed_image.shape[0],10) + np.asarray([smoothed_image.shape[0]]*10) 
		# y = np.linspace(0,smoothed_image.shape[1],10)+np.asarray([smoothed_image.shape[1]*10])+np.linspace(smoothed_image.shape[1],0,10)
		# init = np.array([x,y]).T 

		N = 20
		xs = ([0]*N)+list(np.linspace(0,smoothed_image.shape[0],N))+([smoothed_image.shape[0]]*N)+list(np.linspace(smoothed_image.shape[0],0,N))
		ys = list(np.linspace(0,smoothed_image.shape[1],N))+(N*[smoothed_image.shape[1]])+list(np.linspace(smoothed_image.shape[1],0,N)) + ([0]*N)
 
 		xs = xs[5:]
 		ys = ys[5:]
		init = np.array([xs, ys]).T

		snake = active_contour(smoothed_image,init, alpha=1, beta=10,w_edge=1,bc="periodic")
		snakes.append(snake)
	
		# hull= hull.reshape(hull.shape[2],hull.shape[0])
		# snake = active_contour(gaussian(img, 3),init, alpha=0.15, beta=10, gamma=0.001,bc="periodic")



		#------Hough transform method------
		# smoothed_image = smoothed_image-np.min(smoothed_image)
		# smoothed_image = 255*(smoothed_image/np.max(smoothed_image))
		# smoothed_image = smoothed_image.astype(np.uint8)
		# cut_image = cut_image.astype(np.uint8)
		# try:
		# 	ccs = cv2.HoughCircles(smoothed_image,cv2.HOUGH_GRADIENT,dp=1,min_dist=0,param1=200,param2=100,minRadius=0,maxRadius=0)
		# 	circles = np.uint16(np.around(ccs))
		# 	for i in circles[0,:]:
		# 	    # draw the outer circle
		# 	    cv2.circle(smoothed_image,(i[0],i[1]),i[2],(0,255,0),1)
		# 	    # draw the center of the circle
		# 	    cv2.circle(smoothed_image,(i[0],i[1]),2,(0,0,255),1)
		# 	circle_images.append(smoothed_image)
		# except:
		# 	print "Failed in",i
		


	fig,[ax1,ax2,ax3,ax4] = plt.subplots(4)
	ax1.imshow(np.concatenate(output_images,axis=1))
	ax2.imshow(np.concatenate(cut_images,axis=1))
	ax3.imshow(np.concatenate(smoothed_images,axis=1))
	ax3.plot(xs,ys,'rx')
	ax3.plot(snakes[0][:, 0], snakes[0][:, 1], '-b', lw=3)
	
	plt.show()

	# xs,ys = [],[]
	# for i in range(dim):
	# 		if i*dim + j < len(images):
	# 			index = i*dim+j
	# 			# print "INDEX",index, len(centroids)
	# 			x0,y0 = side_length*i,side_length*j
	# 			x1,y1 = side_length*(i+1),side_length*(j+1)
	# 			img = cutouts[index]
	# 			cnt = contours[index]

	# 			#get bounding rectangle, make it into square
				
	# 			w,h = max(w,h),max(w,h)
	# 			# cv2.rectangle(img,(x,y),(x+w,y+h),(0,255,0),2)
				


	# 			output_image[x0:x1,y0:y1] = img

	# 			cx,cy = y0+centroids[index][0],x0+centroids[index][1]

	# 			xs.append(cx)
	# 			ys.append(cy)

	# fig, ax = plt.subplots(1,figsize=(20,20))
	# plt.imshow(output_image,cmap="gray")

	# plt.plot(xs,ys,'rx')

	# print "Max image value:", np.max(output_image)
	# print "Min image value:", np.min(output_image)

	# plt.show()

	# xs,ys = np.mgrid[0:output_image.shape[0],0:output_image.shape[1]]

	# from mpl_toolkits.mplot3d import Axes3D
	# fig = plt.figure()
	# ax = fig.gca(projection='3d')
	# ax.plot_surface(xs,ys,output_image)
	# plt.show()


main()