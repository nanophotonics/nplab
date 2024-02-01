import time

class Timer():
    """docstring for CounterThread."""

    def __init__(self):
        super(Timer, self).__init__()
        self.t0 = 0


    def start(self):
        self.t0 = time.time()

    def stop(self):
        self.running = 0

    def seconds(self):
        return time.time()-self.t0

    def wait(self, time, seconds):
        while(self.seconds() < (time + seconds)):
            pass

    def delay(self, seconds):
        ts = time.time()
        while(time.time() < (ts + seconds)):
            pass