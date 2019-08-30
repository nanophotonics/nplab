"""
This is a demonstration of a simple live graph during data acquisition and the benefits of threading.
The basic experiment updates the data plot in the same thread as the data is acquired, slowing down
the experiment. By multithreading an experiment to separate data acquisition from its view, an experiment
can run more efficiently.
"""

__author__ = 'alansanders'

import numpy as np, matplotlib.pyplot as plt, threading, timeit
from time import time, sleep


def experiment():
    x = np.linspace(0,2*2*np.pi,100)
    f = lambda i: np.sin(i)
    y = np.zeros_like(x)
    y.fill(np.nan)

    plt.ion()
    fig, ax = plt.subplots(1,1, figsize=(6,4))
    line, = plt.plot(x, y, 'ro')
    plt.xlim(x.min(), x.max())
    plt.xlabel('$x$')
    plt.ylabel('$y$')
    plt.show()

    t0 = time()
    for i,xi in enumerate(x):
        y[i] = f(xi)
        line.set_data(x, y)
        sleep(0.01)
        ax.relim()
        ax.autoscale_view()
        fig.canvas.draw()
    print('experiment took', time() - t0, 's, it should have taken', 0.01*len(x), 's')
    plt.show(block=True)


def worker(x, y, f):
    """
    The actual data acquisition loop of the experiment. the parameter x is iterated over with y
    calculated at each point using a function f.
    :param x:
    :param y:
    :param f:
    :return:
    """
    for i,xi in enumerate(x):
        y[i] = f(xi)
        sleep(0.01)


def threaded_experiment():
    """
    The threaded experiment function separates the experiment into the worker function which runs in
    its own thread. While the thread is running the main (GUI) thread continues updating at a different
    rate.
    :return:
    """
    x = np.linspace(0,2*2*np.pi,100)
    f = lambda i: np.sin(i)
    y = np.zeros_like(x)
    y.fill(np.nan)

    plt.ion()
    fig, ax = plt.subplots(1,1, figsize=(6,4))
    line, = plt.plot(x, y, 'ro')
    plt.xlim(x.min(), x.max())
    plt.xlabel('$x$')
    plt.ylabel('$y$')
    plt.show()

    thread = threading.Thread(target=worker, args=(x,y,f))
    t0 = time()
    thread.start()

    while thread.is_alive():
        sleep(0.01)
        line.set_data(x, y)
        ax.relim()
        ax.autoscale_view()
        fig.canvas.draw()
    print('threaded experiment took', time() - t0, 's, it should have taken', 0.01*len(x), 's')
    plt.show(block=True)

if __name__ == '__main__':
    #print timeit.timeit("experiment()", setup="from __main__ import experiment", number=1)
    experiment()
    threaded_experiment()