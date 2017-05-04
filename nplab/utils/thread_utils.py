# -*- coding: utf-8 -*-
"""
Created on Thu Jul 10 17:06:28 2014

@author: Richard

Function decorators to help writing multi-threaded code:
    
@locked_action
@locked_action_decorator(wait_for_lock=True)

Decorating a function with the @locked_action decorator means that only one such function can be called simultaneously on a given object - it's intended to protect i/o operations and make the object thread safe.  By default, functions block until the lock is available, but the long form of the decorator allows this to be changed, so the function returns immediately if the object is locked.

@background_action

Decorating a function with @background_action means that it will happen in a thread.  Often you should lock the action to stop multiple threads conflicting.  NB that you should put the @background_action decorator *before* the @locked_action decorator, otherwise the lock won't work.  

A function running in the background returns a thread object; to find the return value, you can call t.join_and_return_result() (you may want to check if the thread has finished first with t.is_alive()).
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
        #the decorator is meant to be called as @locked_action_decorator()
        #so we need to return a function, which is what actually gets used
        #to modify the function we're decorating.
        @functools.wraps(function)
        def locked_action(self, *args, **kwargs):
            """Perform an action, but use a lock so only one locked action can
            happen at any time"""
            #First: make sure the lock object exists
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
#you can also use @locked_action as a decorator, which uses default args.
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
        @functools.wraps(function)
        def background_action(self, *args, **kwargs):
            if background_by_default:
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
      
def background_actions_running(obj):
    """Determine whether an object has any currently-active background actions."""
    if not hasattr(obj, "_nplab_background_action_threads"):
        return False
    for t in obj._nplab_background_action_threads:
        if t.is_alive():
            return True
    return False

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


