"""
Logging support functions

It's useful for experiments (and items of equipment) to be able to log what's
happening.  This module provides some support functions to help with that.
Note that these usually won't be called directly - anything inheriting from
Instrument (or possibly Experiment) should call self.log instead.
"""

import nplab
import numpy as np

print_logs_to_console = False

def log(message, from_class=None, from_object=None,
        create_datafile=False, assert_datafile=False):
        """Add a message to the NPLab log, stored in the current datafile.

        This function will put a message in the nplab_log group in the root of
        the current datafile (i.e. the HDF5 file returned by
        `nplab.current_datafile()`).  It is automatically timestamped and named.

        @param: from_class: The class (or a string containing it) relating to
        the message.  Automatically filled in if from_object is supplied.
        @param: from_object: The object originating the log message.  We save a
        string representing the object's ID (allows us to distinguish between
        concurrent instances).
        @param: create_datafile: By default, log messages are discarded before
        the datafile exists - specifying True here will attempt to create a
        new datafile (which may involve popping up a GUI).
        @param: assert_datafile: Set to true to raise an exception if there is
        no current datafile.

        Note that if you are calling this from an `Instrument` subclass you
        should consider using `self.log()` which automatically fills in the
        object and class fields.
        """
        try:
            df = nplab.current_datafile(create_if_none=create_datafile,
                                        create_if_closed=create_datafile)
            logs = df.require_group("nplab_log")
            dset = logs.create_dataset("entry_%d",
                                       data=np.string_(message),
                                       timestamp=True)
            #save the object and class if supplied.
            if from_object is not None:
                dset.attrs.create("object",np.string_("%x" % id(from_object)))
                if from_class is None:
                    #extract the class of the object if it's not specified
                    try:
                        from_class = from_object.__class__
                    except:
                        pass
            if from_class is not None:
                dset.attrs.create("class",np.string_(from_class))

            #if nothing's gone wrong, and we've been asked to, print the message
            if print_logs_to_console:
                print "log: " + message

        except Exception as e:
            print "Couldn't log to file: " + message
            if assert_datafile:
                print "Error saving log message - raising exception."
                raise e
