"""
Instrument Tests
================

This uses some trivial dummy classes to test the auto-finding features of
the instrument class.
"""
import sys
sys.path.append("../")
sys.path.append("./")
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

if __name__ == '__main__':
    test_ok = True

    instruments = InstrumentA.get_instances()
    assert len(instruments)==0, "Spurious instrument returned"

    try:
        a = InstrumentA.get_instance(create=False)
        test_ok = False
    except:
        print "There are still no As, as expected"
    assert test_ok, "Got or created an A when we shouldn't have"


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

    print "Checking save functionality"
    nplab.datafile.set_current("temp.h5",mode='w')
    for i in range(10):
        a.create_data_group('test',attrs={'creator':'instrumentA','serial':i})
    assert nplab.current_datafile()['InstrumentA/test_9'].attrs.get('serial')==9, "data saving didn't work as expected"
    f = nplab.current_datafile()
    f.file.close()
    os.remove('temp.h5')

