"""
Instrument Tests
================

This uses some trivial dummy classes to test the auto-finding features of
the instrument class.
"""
import pytest
import os

import nplab
import nplab.datafile
import nplab.instrument

from nplab.instrument import Instrument

class InstrumentA(Instrument):
    def __init__(self):
        print "An instance of instrument A is being created"
        super(InstrumentA, self).__init__()
    def save_reading(self):
        self.create_data_group("reading", attrs={'creator':'InstrumentA'})

class InstrumentB(Instrument):
    def __init__(self):
        print "An instance of instrument B is being created"
        super(InstrumentB, self).__init__()

def test_get_instances_empty():
    instruments = InstrumentA.get_instances()
    assert len(instruments)==0, "Spurious instrument returned"

def test_get_instance_empty():
    with pytest.raises(IndexError):
        a = InstrumentA.get_instance(create=False) #should fail

def test_get_instances():
    # create some instances and check we can retrieve them correctly
    a = InstrumentA.get_instance() #should create a valid instance
    a2 = InstrumentA.get_instance() #should return the same instance

    assert a==a2, "Should have returned an existing instance but created a new one instead!"

    a3 = InstrumentA() #creates a new instance
    instruments = InstrumentA.get_instances()

    assert len(instruments) == 2, "I made two instruments and got %d" % len(instruments)
    
    b = InstrumentB.get_instance()

    instruments = Instrument.get_instances()
    assert len(instruments) == 3, "Wrong number of instruments present!"

    assert InstrumentB.get_instance() == b, "Second class didn't return the right instance."

def test_saving():
    #test the auto-saving capabilities
    a = InstrumentA.get_instance() #should create/get a valid instance
    nplab.datafile.set_current("temp.h5",mode='w') #use a temporary h5py file
    for i in range(10):
        a.create_data_group('test',attrs={'creator':'instrumentA','serial':i})
    assert nplab.current_datafile()['InstrumentA/test_9'].attrs.get('serial')==9, "data saving didn't work as expected"
    f = nplab.current_datafile()
    f.close()
    os.remove('temp.h5')

