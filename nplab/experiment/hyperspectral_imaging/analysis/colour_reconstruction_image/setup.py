from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize
from Cython.Distutils import build_ext
import numpy as np

#ext  =  [Extension( "afm_mechanical_model", sources=["afm_mechanical_model.pyx"] )]

setup(
   #name = "afm_mechanical_model", 
   #cmdclass={'build_ext' : build_ext}, 
   include_dirs = [np.get_include()],   
   #ext_modules=ext
   cmdclass = {'build_ext': build_ext},
   ext_modules = [Extension("colour_reconstruction", ["reconstruct_colour.pyx"])]
   #ext_modules = cythonize("afm_mechanical_model.pyx")
   )