"""
Logging support functions

It's useful for experiments (and items of equipment) to be able to log what's
happening.  This module provides some support functions to help with that.
Note that these usually won't be called directly - anything inheriting from
Instrument (or possibly Experiment) should call self.log instead.
"""

import nplab
import numpy as np
import sys
import os
import logging
if 'PYCHARM_HOSTED' not in os.environ:
    import colorama
    colorama.init()

print_logs_to_console = False

def log(message, from_class=None, from_object=None,
        create_datafile=False, assert_datafile=False, level= 'info'):
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
        @param: level: This can either be used to add a value of 'importance' 
        to the log, the default is 'info'. The other options are 'debug',
        'warn'(as in warning) and 'error', and 'critical'.

        Note that if you are calling this from an `Instrument` subclass you
        should consider using `self.log()` which automatically fills in the
        object and class fields.
        """
        try:
            df = nplab.current_datafile(create_if_none=create_datafile,
                                        create_if_closed=create_datafile)
            logs = df.require_group("nplab_log")
            logs.attrs['log_group'] = True 
            dset = logs.create_dataset("entry_%d",
                                       data=np.string_(message),
                                       timestamp=True)
            #save the object and class if supplied.
            if from_object is not None:
                dset.attrs.create("object",np.string_("%x" % id(from_object)))
                dset.attrs['log_dset'] = True
                dset.attrs['level'] = level
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
            if hasattr(from_object,'_logger'):
                getattr(from_object._logger,level)(message)

        except Exception as e:
            print "Couldn't log to file: " + message
            print 'due to error', e
            if assert_datafile:
                print "Error saving log message - raising exception."
                raise e


'''COLORED LOGGING'''
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

# These are the sequences need to get colored ouput
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"

def formatter_message(message, use_color = True):
    if use_color:
        message = message.replace("$RESET", RESET_SEQ).replace("$BOLD", BOLD_SEQ)
    else:
        message = message.replace("$RESET", "").replace("$BOLD", "")
    return message

COLORS = {
    'WARNING': YELLOW,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': YELLOW,
    'ERROR': RED
}


class ColoredFormatter(logging.Formatter):
    def format(self, record):
        levelname = record.levelname
        if levelname in COLORS:
            levelname_color = COLOR_SEQ % (30 + COLORS[levelname]) + levelname + RESET_SEQ
            record.levelname = levelname_color
        return logging.Formatter.format(self, record)


def create_logger(name='Experiment', **kwargs):
    '''This functions defines the Logger called Experiment, with the relevant colored formatting'''
    if 'level' in kwargs:
        LOGGER_LEVEL = kwargs['level']
    else:
        LOGGER_LEVEL = 'INFO'
    if 'filename' in kwargs:
        LOGGER_FILE = kwargs['filename']
    else:
        LOGGER_FILE = None
    fh = logging.StreamHandler(sys.stdout)
    f = ColoredFormatter('[%(name)s] - %(levelname)s: %(message)s - %(asctime)s ', '%H:%M')
    fh.setFormatter(f)
    test = logging.getLogger(name)
    test.propagate = False
    test.setLevel(LOGGER_LEVEL)
    test.addHandler(fh)

    if LOGGER_FILE is not None:
        fh = logging.FileHandler(LOGGER_FILE)
        fh.setFormatter(logging.Formatter('[%(name)s] - %(levelname)s: %(message)s - %(asctime)s ', datefmt='%H:%M'))
        fh.setLevel(LOGGER_LEVEL)
        test.addHandler(fh)

    return test


if __name__ == '__main__':
    logger = create_logger()
    for ii in ['debug','info','warn','error']:
        getattr(logger,ii)(ii)