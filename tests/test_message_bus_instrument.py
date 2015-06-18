# -*- coding: utf-8 -*-
"""
Created on Thu Apr 09 22:37:15 2015

@author: rwb27
"""


from nplab.instrument.message_bus_instrument import EchoInstrument

def test_parsing():
    e = EchoInstrument()
    assert e.int_query("number 483 is the answer") == 483
    assert e.float_query("quotient is 485.24") == 485.24
    assert e.parsed_query("result was 49.56 on attempt number 7","%f on attempt number %d") == [49.56, 7]
    assert e.parsed_query("tell me 0x17","%i") == 23
    assert e.parsed_query("tell me 0x17","tell me %x") == 23
    assert e.parsed_query("tell me 010","%i") == 8
    assert e.parsed_query("tell me 010","%o") == 8
    