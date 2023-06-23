import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from functools import wraps
from nplab.analysis import Spectrum

def baseline_als(y, lam, p, niter=10):
    """
    y is the spectrum
    lam is the smoothness, should be between 10**2 and 10**9
    p is asymmetry, should be between 0.001 and 0.1
    """
    L = len(y)
    D = sparse.diags([1, -2, 1], [0, -1, -2], shape=(L, L - 2))
    w = np.ones(L)
    for _ in range(niter):
        W = sparse.spdiags(w, 0, L, L)
        Z = W + lam * D.dot(D.transpose())
        z = spsolve(Z, w * y)
        w = p * (y > z) + (1 - p) * (y < z)
    return z

@wraps(baseline_als)
def als(y, lam=10**3, p=0.01, niter=10):
    return baseline_als(y, lam, p, niter=niter)