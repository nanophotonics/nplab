import numpy as np
from pathlib import Path
regression_folder = Path(__file__).parent / 'regression'
coef = np.load(regression_folder / 'coef.npy', )
intercept = np.load(regression_folder / 'intercept.npy', )
powers = np.load(regression_folder / 'powers.npy', )

def MIM(real, n, t):    
    return np.sum(coef*(np.product(np.array([real, n, t])**powers, axis=1))) + intercept  

# from mpmath import findroot
# def invert_MIM(imag, n, t):
#     def eq(real):
#         return MIM(real, n, t) - imag
#     return float(findroot(eq, 1.7))

# imags = np.linspace(0.02, 0.2)
# import matplotlib.pyplot as plt
# plt.figure()
# for imag in imags:
#     plt.plot(imag, invert_MIM(imag, 1.5, 1.5), '*')

# def invert_MIM_eff(real, eff, n, t):
#     def eq(imag):
#         return eff - (1-(MIM(real, n, t)/imag))
#     return float(findroot(eq, 0.2))   
# plt.figure()
# eff = 0.6
# real = 2.0
# n, t = 1.5, 1.5
# def eq(imag):
#     return eff - (1-(MIM(real, n, t)/imag))

# effs = [(1-(MIM(2.0, 1.5, 1.5)/imag)) for imag in imags]

# plt.plot(imags, effs)