import os
import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve
from functools import wraps, partial
from multiprocessing import Pool
from concurrent.futures import ProcessPoolExecutor as Executor
import nplab.analysis.utils

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
    return baseline_als(np.asarray(y), lam, p, niter=niter)


@wraps(baseline_als)
def als_with_notch(y, notch=(-200,200), **kwargs):
    assert isinstance(y, nplab.analysis.utils.Spectrum), 'must have a split method'
    
    a = y.split(upper=notch[0])
    b = y.split(*notch)
    c = y.split(lower=notch[1])
    a = a - als(a, **kwargs)
    c = c - als(c, **kwargs)
    return y.__class__(np.concatenate((a, b, c), axis=0), y.x)


def als_mp(y_list, lam=10**3, p=0.01, niter=10):
    # y_list = [(np.asarray(y), lam, p, niter) for y in y_list]
    a = partial(baseline_als, lam=lam, p=p, niter=niter)
    with Pool(os.cpu_count() - 1) as p:
        results = p.map(a, y_list)
    return results

if __name__ == '__main__':
    y_list = 100*np.random.rand(1000, 1600)
    res = als_mp(y_list)
    list(res)