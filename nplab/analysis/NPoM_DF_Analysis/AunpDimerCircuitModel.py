'''
Author: car72
Date: 2020-12-09

Uses Felix Benz's circuit model combined with some of jjb's Igor code for combining cavity and antenna modes
Just call VirtualDimer() with appropriate parameters for your model system (see comments in VirtualDimer.__init__() for details)
This returns a dimer Object with attributes relating to the dimer's physical properties

VirtualDimer.antenna_wl is the "coupled mode" for a spherical dimer using Felix's circuit model
VirtualDimer.cavity_wl is the cavity mode
VirtualDimer.coupled_wl is the final coupled mode taking antenna/cavity mixing into account

All output values are in nm

'''

import numpy as np

class VirtualDimer:
    def __init__(self, np_size, gap_size, gap_ri, env_ri = 1, conductance = 0, inductance = None, facet_width = None):
        self.np_size = np_size #AuNP diameter in nm
        self.gap_size = gap_size #Gap size in nm
        self.gap_ri = gap_ri #RI of nanocavity
        self.env_ri = env_ri #RI of surrounding medium
        self.conductance = conductance #in G0
        self.inductance = inductance # some integer value; don't ask me, I'm not a physicist
        self.facet_width = facet_width if facet_width is not None else np_size/4#in nm

        self.initialize_constants()
        self.calc_chi()
        self.calc_theta()
        self.calc_eta()
        self.calc_eps_inf()
        self.calc_cavity_wl()
        self.calc_antenna_wl()
        self.calc_mixing()
    
    def initialize_constants(self):
        self.c = 2.99792458e8 # in m/s
        self.plasma_wl = 146 # in nm, Constant for Au
        self.plasma_freq = 2 * np.pi * 2.99792458e8 / (self.plasma_wl * 1e-9) #radial frequency, Constant for Au
        self.eps_0 = pow((pow(2.9979e8, 2) * 4 * np.pi * 1e-7), -1) #Constant in F/m (SI units)
        self.cond_quant = 7.74809173e-5 #Constant
    
    def calc_chi(self):
        self.chi = 1.0242 + self.np_size*0.012785 - 0.0001375*pow(self.np_size, 2)

    def wl_to_ev(self, wl):
        return 1239.8419745831507/wl#converts between eV and nm

    def calc_theta(self):
        theta_degrees = 27.171 - 0.091802*self.np_size + 0.00096972*pow(self.np_size, 2) + 1.8442e-5*pow(self.np_size, 3)
        self.theta = theta_degrees*(np.pi/180)

    def calc_eta(self):
        self.eta = (pow(self.gap_ri, self.chi)/self.env_ri)*np.log(1 + ((self.np_size/2)*pow(self.theta, 2)/(2*self.gap_size)))

    def calc_eps_inf(self):
        "calculates the correct eps_inf for a given NP size"
        self.eps_inf = 9.38 - 0.00339*self.np_size + 0.00021*pow(self.np_size, 2)
    
    def calc_cavity_wl(self): # calculates energies of lowest mode
        wp = self.wl_to_ev(self.plasma_wl)
        en = wp/np.sqrt(self.eps_inf + self.facet_width*(self.gap_ri**2)/(self.gap_size * 4.2)) # alpha antinodes: in NPoMv2 {4.2,9.4,15} to fit better?
        
        self.cavity_wl = self.wl_to_ev(en)

    def calc_antenna_wl(self):#calculates coupled mode for spherical dimer using Felix Benz's circuit model
        wd = 1/np.sqrt(4*self.eta*self.gap_ri + 2*self.gap_ri + self.eps_inf)
        
        if self.conductance == 0:
            self.antenna_wl = self.plasma_wl/wd
        
        else:            
            Cs = 2*np.pi*(self.np_size/2)*self.eps_0*self.gap_ri*1e-9
            induct_fh = self.inductance*1e-15
            gam = -induct_fh*Cs*pow(self.plasma_freq, 2)

            condS = np.multiply(self.cond_quant, self.conductance)
            de = 1/pow((condS*induct_fh*self.plasma_freq), 2)

            bq = de + pow(wd, 2)*(4*self.env_ri/gam - 1)
            cq = -de * pow(wd, 2)
            sqt = np.sqrt(pow(bq, 2) - 4*cq)
            self.antenna_wl = self.plasma_wl*np.sqrt(2/(sqt - bq))

    def calc_mixing(self): # calculates coupled plasmon from cavity mode coupled to antenna mode
        e1 = self.wl_to_ev(self.antenna_wl) # antenna mode, around 746nm
        e2 = self.wl_to_ev(self.cavity_wl) # cavity mode
        eo = 0.5*(e1 + e2) - np.sqrt(0.25*(e2 - e1)**2 + 0.11**2) # V=0.09 in NPoMv2 for 5 modes, increase to match
        
        self.coupled_wl = self.wl_to_ev(eo)
