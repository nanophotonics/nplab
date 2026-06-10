"""client.py: Socket client for interfacing with Yeti System"""
from __future__ import division
from __future__ import print_function
from past.utils import old_div
from builtins import object
__copyright__ = "Copyright 2020, Cambridge Consultants"

import socket
import time
import os
import errno
from datetime import datetime
from enum import Enum
from queue import Queue, Empty
from select import select
from threading import Thread

import click
import suitcase.fields
import suitcase.protocol
import suitcase.structure

num_ch = 2 # Change this according to you boot file. Total number of timestamps per trigger.


class Message(suitcase.structure.Structure):
    """The binary protocol used on the socket"""
    start = suitcase.fields.Magic(b'\x02')
    message_type = suitcase.fields.ULInt8()
    payload_length = suitcase.fields.LengthField(suitcase.fields.ULInt32())
    payload = suitcase.fields.Payload(payload_length)


class MessageType(Enum):
    MESSAGE_ACK = 0
    MESSAGE_NAK = 1
    MESSAGE_ERROR = 2
    MESSAGE_STATUS_REQ = 3
    MESSAGE_STATUS = 4
    MESSAGE_START = 5
    MESSAGE_STOP = 6
    MESSAGE_DATA = 7


class MessageStatus(suitcase.structure.Structure):
    running = suitcase.fields.ULInt8()
    overflow_count = suitcase.fields.ULInt16()
    bd_used = suitcase.fields.ULInt32()
    bd_total = suitcase.fields.ULInt32()
    bd_size = suitcase.fields.ULInt32()


class MessageStart(suitcase.structure.Structure):
    pass


class TimeTagger(object):
    """Connection to the Yeti System.
    Must be used with the 'with' statement (see PEP 343) to establish a connection.
    Note that the client should only be used from a single thread. A private internal thread is used for the stream
    reading and writing. """

    def __init__(self, ip, port=4406):
        self.ip = ip
        self.port = port
        self._thread = None
        self._connection_running = False
        self._collection_running = False
        self._stream_handler = None
        self._status = None
        self._ack_nak = None
        self._send_queue = Queue()
        self._data_queue = Queue()

    def __enter__(self):
        self._connection_running = True
        self._thread = Thread(target=self._connection_handler)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._collection_running:
            self.stop()

        self._connection_running = False
        self._thread.join()

    def run_acquisition(self, timeout=0.1):
        """Start the data acquisition and returns an iterator of the data.
        The iterator yields the bytes of the acquisition data or or None if the timeout is exceeded. Note that the
        timeout is only between yields of the iterator and thus a small value is recommended to prevent slower
        acquisition from blocking the caller for too long. To stop acquisition call `TimeTagger.stop()`
        (this will also terminate the iterator)."""
        self._start()
        while self._collection_running:
            try:
                yield self._data_queue.get(True, timeout)
            except Empty:
                yield None

    def stop(self):
        """Stop data acquisition"""
        request = Message()
        request.message_type = MessageType.MESSAGE_STOP.value
        request.payload = b""

        while not self._send_and_wait_for_ack_nak(request):
            time.sleep(0)

        self._collection_running = False

    def query_status(self):
        """Get the system status including buffer usage."""
        request = Message()
        request.message_type = MessageType.MESSAGE_STATUS_REQ.value
        request.payload = b""
        return self._send_and_wait_for_status(request)

    def _start(self):
        request = Message()
        request.message_type = MessageType.MESSAGE_START.value
        payload = MessageStart()
        request.payload = payload.pack()

        if not self._send_and_wait_for_ack_nak(request):
            raise Exception("Failed to start time tagger")
        else:
            self._collection_running = True

    def _send_and_wait_for_ack_nak(self, request):
        self._ack_nak = None
        self._send_queue.put(request.pack())

        while self._ack_nak is None:
            # Allow python to switch execute the connection handler thread
            time.sleep(0)

        ret = self._ack_nak
        self._ack_nak = None
        return ret

    def _send_and_wait_for_status(self, request):
        self._status = None
        self._send_queue.put(request.pack())

        while self._status is None:
            # Allow python to execute the connection handler thread
            time.sleep(0)

        ret = self._status
        self._status = None
        return ret

    def _connection_handler(self, timeout=0.1, buffer_size=4096):
        # Run in a dedicated thread so can block
#        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock: # caused errors
        if True:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((self.ip, self.port))
            # Set to be non-blocking and then use select to block with a timeout
            sock.setblocking(False)

            self._stream_handler = suitcase.protocol.StreamProtocolHandler(Message, self._message_handler)
            while self._connection_running:
                # Block until data is received or the timeout is exceeded.
                if select([sock], [], [], timeout)[0]:
                    self._stream_handler.feed(sock.recv(buffer_size))

                # Send all the data in the send queue
                while not self._send_queue.empty():
                    data = self._send_queue.get_nowait()
                    if data:
                        sock.sendall(data)

    def _message_handler(self, message):
        # Python equivalent of a switch statement
        {
            MessageType.MESSAGE_ACK: self._message_handler_ack_nak,
            MessageType.MESSAGE_NAK: self._message_handler_ack_nak,
            MessageType.MESSAGE_ERROR: self._message_handler_error,
            MessageType.MESSAGE_STATUS: self._message_handler_status,
            MessageType.MESSAGE_DATA: self._message_handler_data,
        }[MessageType(message.message_type)](message)

    def _message_handler_ack_nak(self, message):
        self._ack_nak = (message.message_type == MessageType.MESSAGE_ACK.value)

    def _message_handler_error(self, message):
        raise Exception("Got error from device: %s" % str(message.payload)) # caused errors

    def _message_handler_status(self, message):
        self._status = MessageStatus.from_data(message.payload)

    def _message_handler_data(self, message):
        self._data_queue.put(message.payload)


@click.command()
@click.option('--ip', type=str, default="192.168.2.99")
@click.option('--duration', type=float, default=1)
@click.option('--out', type=str, default="{:%Y-%m-%dT%H%M%S}.dat".format(datetime.now()))
def main(ip, duration, out):
    with TimeTagger(ip) as tt, open(out, "wb") as fh:
        print("Starting")
        t_start = time.time()
        t_status = time.time()
        
        counts = 0
        count_rate = 0
        for results in tt.run_acquisition(timeout=0.1):
            # result is None when the timeout is exceeded between messages. This helps to keep everything
            # flowing even if the message rate is low.
            if results is not None:
                fh.write(results)
                counts = counts + len(results)*8/(2*21)/32.0
                count_rate = count_rate + len(results)*8/(2*21)/32.0

            if time.time() - t_status > 1:
                print("Rate: {:.0f} counts/s".format(count_rate))
                count_rate = 0
                status = tt.query_status()
                print("DRAM buffer: {:3.0f} MB / {:3.0f} MB {:3.0f}%;\t FIFO: {:d} overflows".format(
                    (status.bd_used * status.bd_size) * 2**-20,
                    (status.bd_total * status.bd_size) * 2**-20,
                    old_div(status.bd_used, status.bd_total * 100),
                    status.overflow_count
                ))
                t_status = time.time()
                

            if time.time() - t_start > duration:
                tt.stop()

#        print("Wrote %s MB to %s" % str(fh.tell()*2**-20),str(out))
#        print("Wrote {fh.tell()*2**-20:7,.3f} MB to {out}")
        print("Wrote {:.3f} MB to {}".format(fh.tell()*2**-20,out))
        print("{:.0f} total counts recorded".format(counts))
        
def print_countrate(duration=1,ip="192.168.2.99"):
    """ Prints count rate of trigger channel until ctrl+c pressed """
    """ DON'T USE IN GUI """
    # int_time: integration time in s
    with TimeTagger(ip) as tt:
        print("Starting")
#        t_start = time.time()
        t_status = time.time()
        count_rate = 0
        try:
            while True:
                for results in tt.run_acquisition(timeout=0.1):
                    if results is not None:
                        count_rate = count_rate + len(results)*8/(2*num_ch)/32.0
                    if time.time() - t_status > duration:
                        print("Rate: {:.1f} counts/s".format(count_rate/duration))
                        count_rate = 0
                        t_status = time.time()
#                if time.time() - t_start > 20:
#                    tt.stop()
#                    break
        except KeyboardInterrupt:
            tt.stop()
            print('Interrupted!')
            
def get_countrate_timetrace(duration, int_time = 1, ip = "192.168.2.99"):
    """ Returns array of count rates of trigger channel until ctrl+c pressed or duration has passed"""
    """ DON'T USE IN GUI """
    count_rate = 0
    count_rates = []
    times = []
    
    print("Starting")
    t_start = time.time()
    t_status = time.time()
    with TimeTagger(ip) as tt:
        try:
            for results in tt.run_acquisition(timeout=0.1):
                t_current = time.time()
                if results is not None:
                    count_rate = count_rate + len(results)*8/(2*num_ch)/32.0
                if t_current - t_status > int_time:
                    count_rates.append(count_rate/int_time)
                    times.append(t_current - t_start)
                    count_rate = 0
                    t_status = t_current
                    if (time.time() - t_start > duration):
                        break
        except KeyboardInterrupt:
            tt.stop()
            print('Interrupted!')
    print("Finished!")
    return count_rates, times
        
    
            
            
def save_timestamps(out,duration,ip="192.168.2.99"):
    """ Saves timestamps in out file for duration in s """
    delay = 0.5 # delay in recording data to make sure acquisition is running
    
    if not os.path.exists(os.path.dirname(out)):
        try:
            os.makedirs(os.path.dirname(out))
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
    
    with TimeTagger(ip) as tt, open(out, "wb") as fh:
        print("Starting")
        t_start = time.time()
        counts = 0
        for results in tt.run_acquisition(timeout=0.1):
            if results is not None and time.time() - t_start > delay:
                fh.write(results)
                counts = counts + len(results)*8/(2*num_ch)/32.0

            if time.time() - t_start - delay > duration:
                t_stop = time.time()
                tt.stop()

        print("Wrote {:.3f} MB to {}.".format(fh.tell()*2**-20,out))
        print("Recorded {:.0f} total counts in {:.1f} s. Average rate {:.1f} counts/s.".format(counts,t_stop-t_start-delay,counts/(t_stop-t_start-delay)))



def get_countrate(duration,ip="192.168.2.99"):
    """ Returns countrate averaged over duration (in s) """
    delay = 0.5 # delay in recording data to make sure acquisition is running
    with TimeTagger(ip) as tt:
        t_start = time.time()
        counts = 0
        for results in tt.run_acquisition(timeout=0.1):
            if results is not None and time.time() - t_start > delay:
                counts = counts + len(results)*8/(2*num_ch)/32.0

            if time.time() - t_start - delay > duration:
                t_stop = time.time()
                tt.stop()

    return counts/(t_stop-t_start-delay)


if __name__ == "__main__":
#    main()
    print("Yeti ready.")