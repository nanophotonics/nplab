# -*- coding: utf-8 -*-
"""
Created on Fri Oct 12 13:17:20 2018

@author: fo263
"""
from __future__ import print_function

# Save as server.py 
# Message Receiver
from builtins import str
import socket 

from nplab.instrument import Instrument





class Talk2Computer(Instrument):
   
    def receive(self):
        host = ""
        port = 65535
        buf = 1024
        addr = (host, port)
        UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        UDPSock.bind(addr)
            
        print("Waiting to receive messages...")
        while True:
            #(data, addr) = UDPSock.recvfrom(buf)
            data = UDPSock.recv(buf)
            print("Received message: " + data)
            if data == "exit":
                break
            if data != " ":
                break
        return data
        UDPSock.close()
        #os._exit(0)
    
#    def send(self, ipadd = "172.24.36.227", displaymsg = " "): # set to IP address of target computer
#        port = 65535
#        addr = (ipadd, port)
#        data = " "
#        UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#        while True:
#            if displaymsg == " ":
#                data = raw_input("Enter message to send or type 'exit': ")
#                UDPSock.sendto(data, addr)
#            else: 
#                UDPSock.sendto(str(displaymsg), addr)
#                break
#            if data == "exit":
#                break
#        UDPSock.close()
  
    def send_particle_number(pretext = "Particle_", offset = 0):
        try:
            current_particle = wizard.current_particle
            particle_name = pretext + str(current_particle + offset)
            send("172.24.36.227",  {'cmd': 'start', 'filename': particle_name} )
        except exception as e:
            print(e)      
        
        
    def send(ipadd = "172.24.36.227",  dict = {'cmd': 'start', 'filename': 'np1'}): # set to IP address of target computer
        port = 65535
        addr = (ipadd, port)
        data = " "
        UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        UDPSock.sendto(str(dict), addr)
        UDPSock.close()
    
    
    def send2(self, ipadd = "172.24.36.227",  dict = {'cmd': 'start', 'filename': 'np1'}): # set to IP address of target computer
        port = 65535
        addr = (ipadd, port)
        data = " "
        UDPSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        while True:
            UDPSock.sendto(str(dict), addr)
            break
            if data == "exit":
                break
        UDPSock.close()
        #os._exit(0)

