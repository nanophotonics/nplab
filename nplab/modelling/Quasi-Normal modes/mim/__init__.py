from pathlib import Path

import numpy as np

bins = Path(__file__).parent / 'binaries'
coef = np.load(bins / 'coef.npy', )
intercept = np.load(bins / 'intercept.npy', )
powers = np.load(bins / 'powers.npy', )

def MIM(real, n, t):    
    return np.sum(coef*(np.product(np.array([real, n, t])**powers, axis=1))) + intercept  

