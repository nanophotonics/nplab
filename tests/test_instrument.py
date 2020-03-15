"""
Instrument Tests
================

This uses some trivial dummy classes to test the auto-finding features of
the instrument class.
"""
from __future__ import print_function
from builtins import str
from builtins import range
import pytest
import os

import nplab
import nplab.datafile
import nplab.instrument
import numpy as np

from nplab.instrument import Instrument

class InstrumentA(Instrument):
    integration_time = 42.3
    gain = 2
    description = "Test metadata"
    empty_property = None
    bad_property = object()
    metadata_property_names = ('integration_time','gain','description','empty_property')
    def __init__(self):
        print("An instance of instrument A is being created")
        super(InstrumentA, self).__init__()
    def save_reading(self):
        self.create_data_group("reading", attrs={'creator':'InstrumentA'})

class InstrumentB(Instrument):
    def __init__(self):
        print("An instance of instrument B is being created")
        super(InstrumentB, self).__init__()

##################### Test the instance-tracking code #########################
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
    instruments = InstrumentA.get_instances()
    assert len(instruments) == 2, "Got %d InstrumentAs, not 2" % len(instruments)

    assert InstrumentB.get_instance() == b, "Second class didn't return the right instance."
    
def test_instance_deletion():
    class InstrumentC(Instrument):
        def __del__(self):
            print("deleted")
    assert len(InstrumentC.get_instances()) == 0, "An instance of a not-yet-created instrument existed"
    c = InstrumentC()
    assert len(InstrumentC.get_instances()) == 1, "The created instrument wasn't in the list"
    del c
    assert len(InstrumentC.get_instances()) == 0, "The instrument wasn't properly removed on deletion"
        
def test_instance_deletion_2():
    class InstrumentC(Instrument):
        pass
    assert len(InstrumentC.get_instances()) == 0, "An instance of a not-yet-created instrument existed"
    c = InstrumentC()
    assert len(InstrumentC.get_instances()) == 1, "The created instrument wasn't in the list"
    del c
    assert len(InstrumentC.get_instances()) == 0, "The instrument wasn't properly removed on deletion"
    
############### Test the data-saving stuff, incl. metadata ####################

instrumentA_default_metadata = {'integration_time':42.3,'gain':2,'description':"Test metadata",'empty_property':None}

def test_get_metadata():
    a = InstrumentA()
    
    # test that metadata is correctly retrieved
    md = a.get_metadata()
    assert md == instrumentA_default_metadata, "Error getting metadata: {0}".format(md)
    
    md = a.get_metadata(include_default_names=False)
    assert md == {}, "Error getting metadata (should be empty): {0}".format(md)
    
    md = a.get_metadata(property_names=['gain'], include_default_names=False)
    assert md == {'gain':2}, "Error getting metadata (should be just gain): {0}".format(md)
    
    md = a.get_metadata(exclude=['integration_time','gain','description'])
    assert md == {'empty_property':None}, "Error getting metadata (should be just gain): {0}".format(md)

def test_metadata_bundling(capsys):
    # check the metadata is correctly bundled with the data
    a = InstrumentA()
    d = a.bundle_metadata(np.zeros(100))
    assert hasattr(d, "attrs"), "Dataset was missing attrs dictionary!"
    for k, v in list(instrumentA_default_metadata.items()):
        assert d.attrs[k] == v
    assert list(d.attrs.keys()) == list(instrumentA_default_metadata.keys()), "Extraneous metadata bundled? {0}".format(list(d.attrs.keys()))


def test_saving(capsys, tmpdir):
    # test the auto-saving capabilities
    a = InstrumentA.get_instance() #should create/get a valid instance
    nplab.datafile.set_current(str(tmpdir.join("temp.h5")), mode="w")
    df = nplab.current_datafile()
    for i in range(10):
        a.create_data_group('test',attrs={'creator':'instrumentA','serial':i})
    assert df['InstrumentA/test_9'].attrs.get('serial')==9, "data saving didn't work as expected"

    # test the bundled metadata is correctly saved
    data = a.bundle_metadata(np.zeros(100))
    d = a.create_dataset("test_bundled_metadata", data=a.bundle_metadata(np.zeros(100)))
    for k, v in list(instrumentA_default_metadata.items()):
        assert v is None or d.attrs[k] == v

    out, err = capsys.readouterr() #make sure this is clear
    d = a.create_dataset("test_bundled_metadata_bad", 
                         data=a.bundle_metadata(np.zeros(100), 
                                                property_names=['bad_property']))
    assert "object" in d.attrs['bad_property'], "Fallback to str() failed for bad metadata"
    out, err = capsys.readouterr()
    assert "Warning, metadata bad_property" in out, "Didn't get warning about bad_property: \n{}".format(out)
    
    df.close()

