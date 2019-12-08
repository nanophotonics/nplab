# -*- coding: utf-8 -*-
"""
Created on Fri Oct 12 13:17:20 2018

@author: fo263
"""
from __future__ import print_function

# Save as server.py 
# Message Receiver
import os
import socket 

host = ""
port = 13000
buf = 1024
addr = (host, port)
UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
UDPSock.bind(addr)
print("Waiting to receive messages...")
while True:
    (data, addr) = UDPSock.recvfrom(buf)
    print("Received message: " + data)
    if data == "exit":
        break
UDPSock.close()
os._exit(0)