import nplab
from nplab.instrument import Instrument
import nplab.datafile
import pytest

class InstrumentA(Instrument):
    def do_something(self):
        self.log("doing something")

def test_datafile_assertion():
    with pytest.raises(IOError):
        #should fail because the datafile isn't open
        nplab.log("Message", assert_datafile=True)

def test_logging(tmpdir):
    nplab.datafile.set_current(str(tmpdir.join("temp.h5")))
    df = nplab.current_datafile()
    assert df, "Error creating datafile!"
    print df

    nplab.log("test log message", assert_datafile=True) #make a log message
    df.flush() #make sure the message makes it to the file...

    print df['nplab_log'].keys()
    entry = df['nplab_log'].numbered_items("entry")[-1]
    assert entry.value == "test log message"
    print entry.attrs.keys()
    assert entry.attrs.get('creation_timestamp') is not None


    nplab.log("test log message 2") #make a log message
    assert len(df['nplab_log'].numbered_items("entry")) == 2

    df.close()

def test_logging_from_instrument(tmpdir):
    nplab.datafile.set_current(str(tmpdir.join("temp.h5")))
    df = nplab.current_datafile()
    assert df, "Error creating datafile!"

    instr = InstrumentA()

    instr.do_something()

    entry = df['nplab_log'].numbered_items("entry")[-1]
    assert entry.value == "doing something"
    assert entry.attrs.get('creation_timestamp') is not None
    assert entry.attrs.get('object') is not None
    assert entry.attrs.get('class') is not None

    df.close()

def test_long_log(tmpdir):
    nplab.datafile.set_current(str(tmpdir.join("temp_long.h5")))
    df = nplab.current_datafile()
    assert df, "Error creating datafile!"

    instr = InstrumentA()

    N = 10000
    for i in range(N):
        instr.do_something()
        print i
    #assert len(df['nplab_log'].keys()) == N #SLOW!
    assert df['nplab_log/entry_%d' % (N-1)], "Last log entry was missing!"
    with pytest.raises(KeyError):
        df['nplab_log/entry_%d' % N] #zero-indexet - this shouldn't exist!

    df.close()

if __name__ == "__main__":
    pass
