"""
This example demonstrates a real experiment using a Keithley SMU. The main focus here is on the
Instrument subclass which allows a user to get a previously created instance of the Keithley
class to use during the experiment.
"""
__author__ = 'alansanders (last modified by alice ye Jan 30, 2020)'

from nplab.instrument.electronics.keithley_2636b_smu import Keithley2636B
import numpy as np
import matplotlib.pyplot as plt
from time import sleep
from threading import Thread


def run_experiment(voltages, currents):
    smu = Keithley2636B.get_instance()
    smu.output = 1

    sleep(0.001)
    for j,v in enumerate(voltages):
        smu.src_voltage = v
        sleep(0.001)
        currents[j] = smu.read_current()
    #    print currents[j]
    smu.output = 0

def run_experiment_bidirectional(voltages, currents, currents_down):
    smu = Keithley2636B.get_instance()
    smu.output = 1

    sleep(0.001)
    for j,v in enumerate(voltages):
        smu.src_voltage = v
        sleep(0.001)
        currents[j] = smu.read_current()
    #    print currents[j]
    
    for j,v in enumerate(reversed(voltages)):
        smu.src_voltage = v
        sleep(0.001)
        currents_down[j] = smu.read_current()
    #    print currents[j]
    smu.output = 0




def single_sweep(start, stop, step):
    voltages = np.linspace(start, stop, step)
    currents = np.zeros_like(voltages)

    plt.ion()
    fig = plt.figure()
    l1, = plt.plot(voltages, currents, 'ko-')
    plt.xlabel('voltage (V)')
    plt.ylabel('current (A)')
#   plt.ylim(-0.0001,0.0001)
#   plt.show()

    thread = Thread(target=run_experiment, args=(voltages, currents))
    thread.start()

    running = True
    while running:
        running = thread.is_alive()
        l1.set_data(voltages, currents)
        for ax in fig.axes:
            ax.relim()
            ax.autoscale_view()
        fig.canvas.draw()
        sleep(0.1)
   # plt.show()
    l1, = plt.plot(voltages, currents, 'ko-')
    
def multiple_sweep(start, stop, step, num_sweeps,bidirection=True):
    voltages = np.linspace(start, stop, step)
    currents = np.zeros((num_sweeps,step))
    if bidirection==True:
        currents_down = np.zeros_like(currents)
    
    for n in range(num_sweeps):
        # sweep up
        if bidirection == True:
            thread = Thread(target=run_experiment_bidirectional, \
                            args =(voltages, currents[n],currents_down[n]))
        else:
            thread = Thread(target=run_experiment, args =(voltages,currents[n]))
        
        thread.start()    
        running = True
        while running:
            running = thread.is_alive()
            sleep(0.1)
            
    print(currents)    
    if bidirection == True: print(currents_down)
    
    for a in range(num_sweeps):
        fig = plt.plot(voltages, currents[a])
        
        if bidirection == True:
            fig = plt.plot(voltages[::-1],currents_down[a])
            
        plt.xlabel('voltage (V)')
        plt.ylabel('current (A)')
        
    plt.show()

if __name__ == '__main__':
    smu = Keithley2636B()
    max_I = 1e-3
    max_V = 1e3 * max_I
    #single_sweep(0, max_V, 50)
    multiple_sweep(0, max_V, 50, 3, True)