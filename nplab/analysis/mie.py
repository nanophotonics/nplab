from __future__ import division
import numpy as np

'''
Adapted from: https://github.com/scottprahl/miepython

'''

def Lentz_Dn(z, N):
    """ Compute the logarithmic derivative of the Ricatti-Bessel function

        This returns the Ricatti-Bessel function of order N with argument z
        using the continued fraction technique of Lentz, Appl. Opt., 15,
        668-671, (1976).
    """
    zinv     =  2.0/z
    alpha    =  (N+0.5) * zinv
    aj       = -(N+1.5) * zinv
    alpha_j1 = aj+1/alpha
    alpha_j2 = aj
    ratio    = alpha_j1/alpha_j2
    runratio = alpha*ratio

    while abs(abs(ratio)-1.0) > 1e-12:
        aj = zinv - aj
        alpha_j1 = 1.0/alpha_j1 + aj
        alpha_j2 = 1.0/alpha_j2 + aj
        ratio = alpha_j1/alpha_j2
        zinv  *= -1
        runratio = ratio*runratio

    return -N/z+runratio


def D_downwards(z, N):
    """ Compute the logarithmic derivative of all Ricatti-Bessel functions

        This returns the Ricatti-Bessel function of orders 0 to N for an
        argument z using the downwards recurrence relations.

        Source: Borhen & Huffman, page 205, equation 8.39,page 127, equation 4.89
    """
    D = np.zeros(N, dtype=complex)
    last_D = Lentz_Dn(z, N)
    for n in range(N, 0, -1):
        last_D =  n/z - 1.0/(last_D+n/z)
        D[n-1] = last_D
    return D


def D_upwards(z, N):
    """ Compute the logarithmic derivative of all Ricatti-Bessel functions

        This returns the Ricatti-Bessel function of orders 0 to N for an
        argument z using the upwards recurrence relations.

        Source: Borhen & Huffman, page 205, equation 8.39,page 127, equation 4.89
    """
    D = np.zeros(N, dtype=complex)
    exp = np.exp(-2j*z)
    D[1] = -1/z + (1-exp)/((1-exp)/z-1j*(1+exp))
    for n in range(2, N):
        D[n] = 1/(n/z-D[n-1])-n/z
    return D


def D_calc(m, x, N):
    """ Compute the logarithmic derivative of the Ricatti-Bessel function at all
        orders (from 0 to N) with argument z
    """
    z = m * x
    if abs(z.imag) > 13.78*m.real**2 - 10.8*m.real + 3.9:
        return D_upwards(z, N)
    else:
        return D_downwards(z, N)


def mie_An_Bn(m, x,n_max):
    """ Compute the Mie coefficients A and B at all orders (from 0 to N)

        A list of Mie coefficents An and Bn are returned for orders 0 to N for
        a sphere with complex index m and non-dimensional size x.  The length
        of the returned arrays is chosen so that the error when the series are
        summed is around 1e-6.
    """

    nstop = n_max #int(x + 4.05 * x**0.33333 + 2.0)+1

    if m.real > 0.0:
        D = D_calc(m, x, nstop+1)

    a = np.zeros(nstop-1, dtype=complex)
    b = np.zeros(nstop-1, dtype=complex)

    psi_nm1 = np.sin(x)                   # nm1 = n-1 = 0
    psi_n   = psi_nm1/x - np.cos(x)       # n = 1
    xi_nm1  = complex(psi_nm1, np.cos(x))
    xi_n    = complex(psi_n,   np.cos(x)/x+np.sin(x))

    for n in range(1, nstop):
        if m.real == 0.0:
            a[n-1] = (n*psi_n/x - psi_nm1) / (n*xi_n/x - xi_nm1)
            b[n-1] = psi_n/xi_n
        else:
            temp = D[n]/m+n/x
            a[n-1] = (temp*psi_n-psi_nm1)/(temp*xi_n-xi_nm1)
            temp = D[n]*m+n/x
            b[n-1] = (temp*psi_n-psi_nm1)/(temp*xi_n-xi_nm1)

        xi      = (2*n+1)*xi_n/x - xi_nm1
        xi_nm1  = xi_n
        xi_n    = xi
        psi_nm1 = psi_n
        psi_n   = xi_n.real

    return [a, b]

import requests
import matplotlib.pyplot as plt


import numpy as np

def make_rescaled_parameters(n_med,n_particle,r,wavelength):
 #    :param r: radius of the sphere
 #    :param wavelength: wavelength of illumination
 #    :param n_sph: complex refractive index of the sphere
 #    :param n_med: real refractive index of the dielectric medium
    x=  n_med * (2*np.pi/wavelength) * r
    m = n_particle/n_med
    return x,m

def calculate_pi_tau(mu,n_max):
    #calculates angle-dependent functions
    #see Absorption and scattering by small particles, Bohren & Huffman, page 94
    pi_n = np.zeros(n_max)
    tau_n = np.zeros(n_max)
    pi_n[1] = 1.0
    tau_n[1] = mu*pi_n[1]

    for n in range(2,n_max):
        pi_n[n] = ((2.0*n-1)/(n-1))*mu*pi_n[n-1] - ((n)/(n-1))*pi_n[n-2]
        tau_n[n] = n*mu*pi_n[n] - (n+1)*pi_n[n-1]

    pi_n = np.asarray(pi_n[1:])
    tau_n =  np.asarray(tau_n[1:])

    return pi_n, tau_n

def mie_S1_S2(m,x,mus,n_max):
    a,b = mie_An_Bn(m, x,n_max)
    S1s = []
    S2s = []
    for mu in mus:
        S1 = 0.0
        S2 = 0.0
        pi,tau = calculate_pi_tau(mu,n_max)
        for n in range(1,n_max):
            # print len(a),len(pi), len(b), len(tau)
            S1 = S1 + ((2*n+1)/(n**2+n))*(np.dot(a,pi) + np.dot(b,tau))
            S2 = S2+ ((2*n+1)/(n**2+n))*(np.dot(b,pi) + np.dot(a,tau))

        S1s.append(S1)
        S2s.append(S2)
    return [S1s,S2s]


def get_refractive_index(target_wavelength, url):
    gold_indices = requests.get(url)
    content = ((gold_indices._content).replace('\r','\n')).replace('\n\n\n',"\n").replace('\t',",")
    R = [v.split(",") for v in (content.split("\n"))]
    R=R[1:]

    wavelengths = []
    ns = []
    for row in R:
        try:
            w = float(row[0])
            n = float(row[1])+1j*float(row[2])
            wavelengths.append(w)
            ns.append(n)
        except:
            pass
    return np.interp(target_wavelength,wavelengths,ns)

def get_refractive_index_Au(target_wavelength):
    url = "https://www.filmetrics.com/technology/refractive-index-database/download/Au"
    return get_refractive_index(target_wavelength,url=url)

def get_refractive_index_Ag(target_wavelength):
    url = "https://www.filmetrics.com/technology/refractive-index-database/download/Ag"
    return get_refractive_index(target_wavelength,url=url)

def main():
    wavelength = 633.0e-9
    n_particle = get_refractive_index_Au(wavelength/1e-9)
    n_medium = 1.3325

    for r in np.linspace(1e-9,4e-7,50):
        fig = plt.figure(figsize=(16,8))
        ax1 = fig.add_subplot(121,projection="polar")
        ax2 = fig.add_subplot(122)

        x,m = make_rescaled_parameters(n_med=n_medium,n_particle=n_particle,r=r,wavelength=wavelength)
        n_max = int(x + 4.05 * x**0.33333 + 2.0)+1

        print "x:",x
        print "m:",m
        print "n_max", n_max
        theta = np.linspace(-np.pi,np.pi, 360)
        mu = np.cos(theta)
        [S1,S2] = mie_S1_S2(m,x,mu,n_max)

        S11 = np.abs(S1)**2 + np.abs(S2)**2
        S12 = np.abs(S1)**2 - np.abs(S2)**2

        i_para = S11+S12
        i_perp = S11-S12
        i_total = i_para + i_perp
        ax1.plot(theta,i_para,label="parallel")
        ax1.plot(theta,i_perp,label="perp")
        ax1.plot(theta,i_total,label="total")

        ax2.plot(theta,i_para,label="parallel")
        ax2.plot(theta,i_perp,label="perp")
        ax2.plot(theta,i_total, label="total")

        ax1.set_xlabel("Angle $\\theta$ [rad]")
        ax1.set_ylabel("Amplitude")

        ax2.set_xlabel("Angle $\\theta$ [rad]")
        ax2.set_ylabel("Amplitude")


        plt.title("Particle radius [nm]:{0},x:{1},\nm:{2}, n_max:{3}".format(r/1e-9,x,m,n_max))
        # plt.show()
        plt.savefig("C:\Users\im354\Pictures\Mie\particle_{}.png".format(r/1e-9))

main()