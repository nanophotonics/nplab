from __future__ import print_function
from builtins import object
import requests
import yaml
import os, inspect
import numpy as np



class RefractiveIndexInfoDatabase(object):

	def __init__(self):
		#load library:
		dirpath =  os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
		library_path = os.path.normpath(dirpath+"/refractive_index_db_lib.yml")
		#print library_path
		with open(library_path,"r") as file:
			library = yaml.load(file.read())
			#loading library file from online location:
			# library_url = "https://raw.githubusercontent.com/imanyakin/refractiveindex.info-database/master/database/library.yml"
			# response = requests.get(library_url)
			# library = yaml.load(response._content)
			cls = self.__class__
			data = cls.get_data(library)
			data_dict = cls.make_dict(data)

			#self test on start
			cls.test_converse_reversibility(data)
			dataset = cls.fetch_dataset_yaml(data[0])
#			print cls.extract_refractive_indices(dataset)

	@classmethod
	def get_data(cls,it):
		'''
		Extract "data" labels from the library.yml file.
		Each item labelled as "data" is a path that can be accessed through internet
		:param it - iterable (list/dict) of the yaml file
		'''
		
		if type(it) == list:
			outp = []
			for i in it:
				outp = outp + cls.get_data(i)
			return outp
			# return [get_data(i) for i in it]
		elif type(it) == dict:
			outp = []
			if "content" in list(it.keys()):
				outp = outp + cls.get_data(it["content"])
			if "data" in list(it.keys()):
				outp = outp + [it["data"]]
		return outp

	@classmethod
	def make_dict(cls,data):
		'''
		Convert list of labels in A/B/C into a tree structured dict
		Leaf nodes in tree are either lists of labels or are terminated in an empty dict

		'''

		#set up output dict
		outp = dict()
		#leys
		keys = set([d.split("/")[0] for d in data])
		

		for k in keys:
			values = []
			for d in data:
				if k == d.split("/")[0]:
					value = "/".join(d.split("/")[1:])
					if len(value)>0:
						values.append(value)
			outp.update({k:RefractiveIndexInfoDatabase.make_dict(values)})

		#if all values of output dict are empty lists - collapse dict
		if all(len(v)==0 for v in list(outp.values())):
			return list(outp.keys())
		else:
			return outp

	@classmethod
	def make_data(cls,iterable):
		'''
		Inverse of make_dict, converts from a tree structured dictionary to a list of labels in A/B/C format
		'''

		if type(iterable) == list:
			if len(iterable) > 0:
				return iterable
			else:
				return ''
		elif type(iterable) == dict:
			outp = []
			for k in list(iterable.keys()):
				values = RefractiveIndexInfoDatabase.make_data(iterable[k])
				if len(values) > 0:
					for v in values:
						outp = outp + ["/".join([k,v])]
				else:
					outp = outp + [k]
			return outp

	#for testing correct conversion of data --> dict --> data, must preserve all labels
	@classmethod
	def test_converse_reversibility(cls,data):

		'''
		Test code for correct implementation if inverse transformation make_data, make_dict

		performs: data --> make_dict(data) --> make_data(make_dict(data)) --> data2
		if operations are inverse then for all elements d1 in data there is a element d2 in data2 
		'''

		iterable = RefractiveIndexInfoDatabase.make_dict(data)
		data2 = RefractiveIndexInfoDatabase.make_data(iterable)

		for d in data:
			assert (d in data2)
		for d in data2:
			assert(d in data)

	
	@classmethod
	def fetch_dataset_yaml(cls,label):
		'''
		Gets, via HTTP, the yaml file containg hte dataset from the website
		Returns a yaml structured list (yaml is superset of JSON)
		'''
		query_base_url = "https://refractiveindex.info/database/data/{0}"
		url = query_base_url.format(label)
		resp =  requests.get(url)

		response_yaml = yaml.load(resp._content)
		return response_yaml

	@classmethod
	def extract_refractive_indices(cls,response_yaml):
		'''
		Extract the wavelengths and refractive indices from a yaml response
		'''
		data = (response_yaml["DATA"][0]["data"]).split("\n")
		wavelengths = []
		refractive_index = []
		for d in data:
			try:
				[w,n,k] = d.split(" ")
				wavelengths.append(float(w))
				refractive_index.append(float(n) + 1j*float(k))
			except:
				try:
					[w,n] = d.split(" ")
					wavelengths.append(float(w))
					refractive_index.append(float(n))
				except:
					print("failed on: ({})".format(d))
		return {"wavelength":wavelengths, "n": refractive_index}

	@classmethod
	def refractive_index_generator(cls,label):
		'''
		Main method for use. Pulls data from website, transforms it into a dataset
		Returns function that can be queried.
		Function will interpolate between data within a certain range of wavelengths and will crash if required wavelength is outside of this range
		'''

		dataset_yaml = cls.fetch_dataset_yaml(label)
		dataset = cls.extract_refractive_indices(dataset_yaml)

		wavelengths = dataset["wavelength"]
		min_wl = 1e-6*np.min(wavelengths) 
		max_wl = 1e-6*np.max(wavelengths) 
		
#		print "Min Wavelength in dataset:", min_wl
#		print "Max Wavelength in dataset:", max_wl
		def generator(required_wavelength,scale="nm",debug=0):

			assert(scale=="nm") #scale must be in nm - other values may be supported later if required
			#Performs linear interpolation between values in dataset to generate refractive indices over wavelength range spanned by dataset
			if required_wavelength < min_wl:
				raise ValueError("Required wavelength: {0} below minimum in dataset: {1}".format(required_wavelength,min_wl))

			elif required_wavelength > max_wl:
				raise ValueError("Required wavelength: {0} above maximum in dataset: {1}".format(required_wavelength,max_wl))

			else:
				output_n = np.interp(required_wavelength*1e6,xp=dataset["wavelength"],fp=dataset["n"])
				if debug > 0:
					print("--- DEBUG Interpolation---")
					print("Wavelen: {0}, Refractive_index: {1}".format(required_wavelength,output_n))
				return output_n

		return generator





if __name__ == "__main__":
	rfdb = RefractiveIndexInfoDatabase()
	label = "main/Au/Yakubovsky-25nm.yml"
	generator = rfdb.refractive_index_generator(label=label)

	wls = np.linspace(500e-9,800e-9,300)
	for w in wls:
		print(generator(required_wavelength=w,debug = 1))

	print("Passed basic test")