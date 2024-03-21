# -*- coding: utf-8 -*-
"""
Created on Mon Sep 13 10:05:02 2021

@author: Eoin
"""
from pathlib import Path


def save_rejected(rejected, path=None, overwrite=False):
    '''saves an iterable of particle names. by default it loads the previous .txt
    and saves the union of the new and previous ones'''
    if path is None: path = Path()
    existing = set() if overwrite else load_rejected(path)
    with open(path / 'rejected.txt', 'w') as f:
        f.truncate(0)
        f.write('\n'.join(existing | rejected))


def load_rejected(path=Path()):
    '''returns the contents of rejected.txt if it exists, or an empty set'''
    if (file := path + '/rejected.txt').exists():
        with open(path / file) as f:
            rejected = set(l.strip() for l in f.readlines())
    else:
        rejected = set()
    return rejected


def distance(p1, p2):
    '''distance between two points'''
    return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**0.5
