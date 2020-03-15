from __future__ import print_function
from builtins import str
import timeit


def timed_execution(f,*args,**kwargs):

	'''
	Timed execution of function 'f' taking arguments

	@param: f: the function whose execution you want to time
	@param: *args: the non-keyword arguments of the function
	@param: *kwargs: the keyword arguments of the function

	@return: output of function (out), execution time (dt) [in seconds]
	'''

	full_name = str(inspect.getmodule(f))+"."+f.__name__
	start_time = timeit.default_timer()
	print(("-"*5+"Start timing"+"-"*5+"\n"+full_name+"\n"+"-"*20))
	
	out = f(*args,**kwargs)
	
	dt =timeit.default_timer() - start_time
	print(("-"*20))
	print(("Executed in: {1}\n[{0}]".format(full_name,dt)))
	print(("-"*20))
	return out,dt

