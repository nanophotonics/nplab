# -*- coding: utf-8 -*-
"""
Created on Fri Mar 11 13:19:10 2022

@author: Hera
"""

from pylablib.devices import M2
import socket
if __name__ == '__main__':
    
    address = ('172.24.37.153', 39933)
    laser = M2.Solstis(*address)
# laser.close()