# -*- coding: utf-8 -*-
"""
Created on Thu Jul 10 17:06:28 2014

@author: Richard
"""

import time
import threading
import functools
import numpy as np

def locked_action_decorator(wait_for_lock=True):
    """This decorates a function, to prevent it being called simultaneously from
    multiple threads.  Only one locked action can happen at any given time on a
    given object.
    
    We use a Reentrant Lock, which means that a single thread can acquire() it
    multiple times.  This is helpful (for example if locked functions call
    other locked functions, this is OK).
    
    If wait_for_lock is false and an action is running, it returns immediately.
    This can be given as an argument to locked_action_decorator (which sets the
    default) or to the function when called (which overrides it).
    """
    def decorator(function):
        def locked_action(self, wait_for_lock=wait_for_lock, *args, **kwargs):
            if not hasattr(self, "_nplab_action_lock"):
                self._nplab_action_lock = threading.RLock()
            try:
                if wait_for_lock:
                    self._nplab_action_lock.acquire() #this will wait until we can lock the device
                else:    #if "wait for lock" is false, just return false if it's busy
                    if not self._nplab_action_lock.acquire(block=False):
                        print "Could not acquire action lock, giving up."
                        return False
                return function(self, *args, **kwargs)
            except Exception as e:
                raise e #don't attempt to handle errors, just pass them on
            finally:
                self._nplab_action_lock.release() #don't leave the thing locked
        return locked_action
    return decorator
locked_action = locked_action_decorator()

def background_action_decorator(background_by_default=True, ):
    """This decorates a function to run it in a background thread.  NB it does
    not lock the function: use @locked_action to do this (the two are compatible
    but you must place background_action *before* locked function, so that the
    lock is acquired by the background thread.).
    
    Arguments:
    * background_by_default sets whether the function runs in the
    background by default or whether it only backgrounds itself when asked.  In
    either case the non-default behaviour can be requested with keyword argument
    run_in_background_thread.
    * 
    """
    def decorator(function):
        def background_action(self, run_in_background_thread=background_by_default, *args, **kwargs):
            if run_in_background_thread:
                if not hasattr(self, "_nplab_background_action_threads"):
                    self._nplab_background_action_threads = set([])
                t = threading.Thread()
                def worker_function():
                    t.returned_value = function(self, *args, **kwargs)
                    self._nplab_background_action_threads.remove(t)
                t.run=worker_function
                t.host_object = self
                self._nplab_background_action_threads.add(t)
                t.start()
                def join_and_return_result(self): #this gets added to a thread so we can extract the return value
                    self.join()
                    return self.returned_value
                t.join_and_return_result = functools.partial(join_and_return_result, t) #add method to the thread
                return t
            else:
                return function(self, *args, **kwargs)
        return background_action #this is the one that replaces the function: same signature but with added kwarg run_in_background_thread
    return decorator #this function *returns* a decorator, i.e. syntax is @background_action()
background_action = background_action_decorator(background_by_default=True)
backgroundable_action = background_action_decorator(background_by_default=False)  
      

if __file__ == "__main__":
    import time
    
    class Foo(object):
        @background_action
        @locked_action
        def sayhello(self):
            time.sleep(1)
            for c in "Hello World!\n":
                time.sleep(0.1)
                print(c),
            return "Return Value"
        @background_action
        def say(self, message):
            time.sleep(1)
            for c in message+"\n":
                time.sleep(0.1)
                print(c),
            return len(message)

    class Bar(object):
        def sayhello(self):
            time.sleep(1)
            for c in "Hello World!\n":
                time.sleep(0.1)
                print(c),
        def say(self, message):
            time.sleep(1)
            for c in message+"\n":
                time.sleep(0.1)
                print(c),
