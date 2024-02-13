# -*- coding: utf-8 -*-
"""
Created on Fri Jan  8 11:47:35 2021

@author: hera
"""


from itertools import cycle

visited = []
def up(pos):
    return (pos[0], pos[1]+1)
def down(pos):
    return (pos[0], pos[1]-1)
def left(pos):
    return (pos[0]-1, pos[1])
def right(pos): 
    return (pos[0]+1, pos[1])

def spiral(start, stepsizes=(1,1)):
    anticlockwise = cycle([down, right, up, left])
    current_direction = down
    next_direction = down
    pos = (0,0)
    while True:
        yield (pos[0]*stepsizes[0] + start[0],
               pos[1]*stepsizes[1] + start[1])
        visited.append(pos)
        if next_direction(pos) not in visited:
            current_direction, next_direction = next_direction, next(anticlockwise)
        pos = current_direction(pos)
        

if __name__ == '__main__':
    
    import matplotlib.pyplot as plt
    plt.figure()
    # for i, c in enumerate(visited):

    for i, pos in enumerate(spiral((25, 25))):
        print(pos)
        plt.text(*pos, i)
        if i == 100: break       
        
            
    