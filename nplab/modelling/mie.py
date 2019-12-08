# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function
from builtins import range
import numpy as np
import requests
import matplotlib.pyplot as plt
from scipy.special import riccati_jn,riccati_yn
from nplab.utils.refractive_index_db import RefractiveIndexInfoDatabase
from mpl_toolkits.mplot3d import Axes3D
from matplotlib import cm

#Initialized after first request
WAVELENGTHS = None
REFRACTIVE_INDEX = None
print("starting")
'''
Adapted from: https://github.com/scottprahl/miepython

'''

rfdb = RefractiveIndexInfoDatabase()
water = "main/H2O/Hale.yml"
gold = "main/Au/Yakubovsky-25nm.yml"
water_refractive_index = rfdb.refractive_index_generator(label=water)
gold_refractive_index = rfdb.refractive_index_generator(label=gold)


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

def calculate_a_b_coefficients(m,x,n_max):
    n = 2*n_max

    def psi(rho):
        outp, _ =riccati_jn(n,rho) 
        return outp 
    def dpsi(rho):
        _,outp = riccati_jn(n,rho)
        return outp
    #Definition:
    #Hankel function of first kind: 
    # Hn = Jn + iYn
    # Jn - bessel function of first kind
    # Yn - bessel function of second kind
    def eps(rho):
        jn = riccati_jn(n,rho)[0]
        yn = riccati_yn(n,rho)[0] 
        hn = jn + 1j*yn
        return hn

    def deps(rho):
        d_jn = riccati_jn(n,rho)[1]
        d_yn = riccati_yn(n,rho)[1] 
        d_hn = d_jn + 1j*d_yn
        return d_hn

    rho = m*x
          
    def a():
        num = m*psi(m*x)*dpsi(x) - psi(x)*dpsi(m*x)
        denom = m*psi(m*x)*deps(x) - eps(x)*dpsi(m*x)
        return (num/denom)[0:n]

    def b():
        num = psi(m*x)*dpsi(x) - m*psi(x)*dpsi(m*x)
        denom = psi(m*x)*deps(x) - m*eps(x)*dpsi(m*x)
        return (num/denom)[0:n]
    return a(), b()

from scipy.special import jv, yv
def Mie_ab(m,x,n_max):
    #  http://pymiescatt.readthedocs.io/en/latest/forward.html#Mie_ab
    mx = m*x
    nmax = np.real(np.round(2+x+4*(x**(1/3))))
    nmx = np.round(max(nmax,np.abs(mx))+16)
    # print "NMAX:", nmax
    n = np.arange(1,np.real(nmax)+1)
    nu = n + 0.5

    sx = np.sqrt(0.5*np.pi*x)
    px = sx*jv(nu,x)

    p1x = np.append(np.sin(x), px[0:int(nmax)-1])
    chx = -sx*yv(nu,x)

    ch1x = np.append(np.cos(x), chx[0:int(nmax)-1])
    gsx = px-(0+1j)*chx
    gs1x = p1x-(0+1j)*ch1x

    # B&H Equation 4.89
    Dn = np.zeros(int(nmx),dtype=complex)
    for i in range(int(nmx)-1,1,-1):
        Dn[i-1] = (i/mx)-(1/(Dn[i]+i/mx))

    D = Dn[1:int(nmax)+1] # Dn(mx), drop terms beyond nMax
    da = D/m+n/x
    db = m*D+n/x

    an = (da*px-p1x)/(da*gsx-gs1x)
    bn = (db*px-p1x)/(db*gsx-gs1x)

    return an, bn

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
    pi_n = np.zeros(n_max+1)
    tau_n = np.zeros(n_max+1)
    pi_n[1] = 1.0
    tau_n[1] = mu*pi_n[1]

    for n in range(2,n_max):
        pi_n[n] = ((2.0*n-1)/(n-1))*mu*pi_n[n-1] - ((n)/(n-1))*pi_n[n-2]
        tau_n[n] = n*mu*pi_n[n] - (n+1)*pi_n[n-1]

    pi_n = np.asarray(pi_n[1:])
    tau_n =  np.asarray(tau_n[1:])

    return pi_n, tau_n

def mie_S1_S2(m,x,mus,n_max):
    a,b = Mie_ab(m, x,n_max)
    S1s = []
    S2s = []
    for mu in mus:
        S1 = 0.0
        S2 = 0.0
        pi,tau = calculate_pi_tau(mu,n_max)
        for n in range(n_max):
            N = n+1
            # print len(a),len(pi), len(b), len(tau)
            S1 = S1+(float(2.0*N+1)/(N**2+N))*(a[n]*pi[n] + b[n]*tau[n])
            S2 = S2+(float(2.0*N+1)/(N**2+N))*(b[n]*pi[n] + a[n]*tau[n])

        S1s.append(S1)
        S2s.append(S2)
    return [S1s,S2s]

def get_refractive_index(target_wavelength, url):
    #pull in globals
    global WAVELENGTHS
    global REFRACTIVE_INDEX
    if WAVELENGTHS == None or REFRACTIVE_INDEX == None:

        import csv
        response = requests.get(url)
        reader = csv.reader(response._content)
        # for row in reader:
        #     print row
        print(response._content)
        # content = ((response._content).replace('\r','\n')).replace('\n\n\n',"\n").replace('\t',",").replace("\n\n","\n")
        print(content)
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
            WAVELENGTHS = wavelengths
            REFRACTIVE_INDEX = ns
    print(target_wavelength)
    print(WAVELENGTHS)
    print(REFRACTIVE_INDEX)
    return np.interp(target_wavelength,WAVELENGTHS,REFRACTIVE_INDEX)

def get_refractive_index_Au(target_wavelength):
    url = "https://refractiveindex.info/data_csv.php?datafile=data/main/Au/Johnson.yml"
    return get_refractive_index(target_wavelength,url=url)

def get_refractive_index_Ag(target_wavelength):
    url = "https://refractiveindex.info/data_csv.php?datafile=data/main/Ag/Johnson.yml"
    return get_refractive_index(target_wavelength,url=url)

def get_refractive_index_water(target_wavelength):
    url = "https://refractiveindex.info/data_csv.php?datafile=data/main/H2O/Hale.yml"
    return get_refractive_index(target_wavelength,url=url)

def calculate_scattering_cross_section(m,x,r,n_max):
    k = x/r
    a,b = Mie_ab(m, x,n_max)
    a2 = np.abs(a)**2
    b2 = np.abs(b)**2
   
    # n = np.arange(1,n_max+1)
    # 2n1 = 2.0*n+1.0

    total = 0.0
    for n in range(len(a2)):
        N = n+1
        total = total + (2*N+1)*(a2[n]+b2[n])
    return ((2*np.pi)/k**2)*total



def calculate_extinction_cross_section(m,x,r,n_max):
    k = x/r
    a,b = Mie_ab(m, x, n_max)
    

    a2,b2 = np.absolute(a)**2,np.absolute(b)**2
    
    total = 0.0
    for n in range(len(a)):
        N = n+1
        real_ab = a[n].real+b[n].real
        # if real_ab < 0:
        #     print "a",a
        #     print "b",b
        total = total + (2*N+1)*real_ab
    return ((2*np.pi)/k**2)*total
    

def main3():
    n_medium = 1.3325
    theta = np.pi/2.0
   
    rs = np.linspace(1e-9,500e-9,50)
    rs = [20e-9,40e-9,]
    wavelengths = np.linspace(400e-9,1000e-9,600)
    for r in rs:
        print("r",r)
        Xs_sca = []
        Xs_ext = []
        for wavelength in wavelengths:
            n_particle = get_refractive_index_Au(wavelength/1e-9)
            print("N:",n_particle)
            x,m = make_rescaled_parameters(n_med=n_medium,n_particle=n_particle,r=r,wavelength=wavelength)
            
            print("X:{0},M:{1}".format(x,m))
            n_max = 20
            scatteringXc = calculate_scattering_cross_section(m,x,r,n_max)
            extinctionXc = calculate_extinction_cross_section(m,x,r,n_max)

            # [scatteringXc,extinctionXc,_,_] = small_mie(m,x)
            Xs_sca.append(scatteringXc)
            Xs_ext.append(extinctionXc)
          
        fig, ax1 = plt.subplots(1,figsize=(8,8))

        Xs_sca = np.asarray(Xs_sca)/(np.pi*r**2)
        Xs_ext = np.asarray(Xs_ext)/(np.pi*r**2)
        Xs_abs = Xs_ext - Xs_sca

        # wavelengths = wavelengths/1e-9
        ax1.plot(wavelengths/1e-9,Xs_sca, label="Scattering efficiency $Q_{sca} = \sigma_{sca}/\pi r^2$")
        ax1.plot(wavelengths/1e-9,Xs_ext, label="Extinction efficiency $Q_{ext} = \sigma_{ext}/\pi r^2$")
        ax1.plot(wavelengths/1e-9,Xs_abs, label="Absorption efficiency $Q_{abs} = \sigma_{abs}/\pi r^2$")
        
        ext_max =np.max(Xs_ext)
        lambda_max = wavelengths[np.where(np.abs(Xs_ext==ext_max))][0] 
        ax1.set_xlabel("Size[nm]")
        ax1.set_ylabel("Amplitude")
        ax1.legend()
        plt.title("Radius [nm]: {0}, $\lambda$: {1}".format(r/1e-9, lambda_max/1e-9))
        # plt.savefig("C:\Users\im354\Pictures\Mie\SEA\particle_{0}.png".format(r/1e-9))
        
        plt.show()

def main2():
    wavelength = 633.0e-9
    n_particle = get_refractive_index_Au(wavelength/1e-9)
    n_medium = 1.3325
    theta = np.pi/2.0
    rs = np.linspace(1e-9,5e-7,1000)
    
    Is = []
    Xs_sca = []
    Xs_ext = []
    Qext = []
    Qsca = []
    Qback = []
    G = []
    for r in rs:
        x,m = make_rescaled_parameters(n_med=n_medium,n_particle=n_particle,r=r,wavelength=wavelength)
        n_max = 100 #int(x + 4.05 * x**0.33333 + 2.0)+1
        scatteringXc = calculate_scattering_cross_section(m,x,r,n_max)
        extinctionXc = calculate_extinction_cross_section(m,x,r,n_max)
        i = I(r,np.asarray([theta]),n_medium,n_particle,wavelength)
        Xs_sca.append(scatteringXc)
        Xs_ext.append(extinctionXc)
        Is.append(i)

        [qext, qsca, qback, g] = mie_scalar(m, x,n_max)

        Qext.append(qext)
        Qsca.append(qsca)
        Qback.append(qback)
        G.append(g)
      
    fig, [ax1,ax2] = plt.subplots(2)
    ax1.plot(rs/1e-9,Xs_sca/(np.pi*rs**2), label="Scattering efficiency $Q_{sca} = \sigma_{sca}/\pi r^2$")
    ax1.plot(rs/1e-9,Xs_ext/(np.pi*rs**2), label="Extinction efficiency $Q_{ext} = \sigma_{ext}/\pi r^2$")
    
    ax1.set_xlabel("Size[nm]")
    ax1.set_ylabel("Amplitude")


    ax2.plot(rs/1e-9,Qsca,label="Scattering")
    ax2.plot(rs/1e-9,Qext,label="Extinction")
    # ax2.plot(rs/1e-9,Is, label="Scattering intensity")
    
    ax2.set_xlabel("Size[nm]")
    ax2.set_ylabel("Amplitude")

    ax1.legend()
    ax2.legend()
    plt.show()
    
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

        print("x:",x)
        print("m:",m)
        print("n_max", n_max)
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


        ax1.legend()
        ax2.legend()
        plt.title("Particle radius [nm]:{0},x:{1},\nm:{2}, n_max:{3}".format(r/1e-9,x,m,n_max))
        # plt.show()
        plt.savefig("C:\\Users\im354\Pictures\Mie\particle_{}.png".format(r/1e-9))

def scattering_cross_section(radius,wavelength):

    n_particle = gold_refractive_index(required_wavelength=wavelength)
    n_med = water_refractive_index(required_wavelength=wavelength)
    x,m = make_rescaled_parameters(n_med=n_med,n_particle=n_particle,r=radius,wavelength=wavelength)
    output = calculate_scattering_cross_section(m=np.asarray([m]),x=np.asarray([x]),r=np.asarray([radius]),n_max=40) 
    return output

def main4():
    wavelength_range = np.asarray([1e-9*wl for wl in np.linspace(450,1000,550)])
    radius_range = np.asarray([r*1e-9 for r in np.linspace(50,250,200)])
    x,y= np.meshgrid(radius_range,wavelength_range,indexing="xy")
    f = np.vectorize(scattering_cross_section)
    z = f(x,y)
    fig = plt.figure()
    ax = fig.gca(projection='3d')
    zmin = np.min(z)
    surf = ax.plot_surface(x/1e-9, y/1e-9, z/zmin,cmap=cm.coolwarm)
    plt.xlabel("Radius [nm]")
    plt.ylabel("Wavelength [nm]")
    plt.title("Normalized scattering cross section\n Normalization: z/z_min, z_min = {}".format(zmin))

    ratio_low = scattering_cross_section(radius = 120e-9,wavelength=450e-9)/scattering_cross_section(radius = 100e-9,wavelength=450e-9)
    ratio_high = scattering_cross_section(radius = 120e-9,wavelength=580e-9)/scattering_cross_section(radius = 100e-9,wavelength=580e-9)
    print("RATIO LOW: ", ratio_low)
    print("RATIO High: ", ratio_high)
    plt.show()
if __name__ == "__main__":
    main4()