'''
Author: car72
Date: 2020-12-09

Uses Felix Benz's circuit model combined with some of jjb's Igor code for combining cavity and antenna modes
Just call VirtualDimer() with appropriate parameters for your model system (see comments in VirtualDimer.__init__() for details)
This returns a dimer Object with attributes relating to the dimer's physical properties

VirtualDimer.antennaWl is the "coupled mode" for a spherical dimer using Felix's circuit model
VirtualDimer.cavityWl is the cavity mode
VirtualDimer.coupledWl is the final coupled mode taking antenna/cavity mixing into account

All output values are in nm

'''

import numpy as np

class VirtualDimer:
    def __init__(self, npSize, gapSize, gapRI, envRI = 1, conductance = 0, inductance = None, facetWidth = None):
        self.npSize = npSize #AuNP diameter in nm
        self.gapSize = gapSize #Gap size in nm
        self.gapRI = gapRI #RI of nanocavity
        self.envRI = envRI #RI of surrounding medium
        self.conductance = conductance #in G0
        self.inductance = inductance # some integer value; don't ask me, I'm not a physicist
        self.facetWidth = facetWidth if facetWidth is not None else npSize/4#in nm

        self.initializeConstants()
        self.calcChi()
        self.calcTheta()
        self.calcEta()
        self.calcEpsInf()
        self.calcCavityWl()
        self.calcAntennaWl()
        self.calcMixing()
    
    def initializeConstants(self):
        self.c = 2.99792458e8 # in m/s
        self.plasmaWl = 146 # in nm, Constant for Au
        self.plasmaFreq = 2 * np.pi * 2.99792458e8 / (self.plasmaWl * 1e-9) #radial frequency, Constant for Au
        self.eps0 = pow((pow(2.9979e8, 2) * 4 * np.pi * 1e-7), -1) #Constant in F/m (SI units)
        self.condQuant = 7.74809173e-5 #Constant
    
    def calcChi(self):
        self.chi = 1.0242 + self.npSize*0.012785 - 0.0001375*pow(self.npSize, 2)

    def wlEv(self, wl):
        return 1239.8419745831507/wl#converts between eV and nm

    def calcTheta(self):
        thetDeg = 27.171 - 0.091802*self.npSize + 0.00096972*pow(self.npSize, 2) + 1.8442e-5*pow(self.npSize, 3)
        self.theta = thetDeg*(np.pi/180)

    def calcEta(self):
        self.eta = (pow(self.gapRI, self.chi)/self.envRI)*np.log(1 + ((self.npSize/2)*pow(self.theta, 2)/(2*self.gapSize)))

    def calcEpsInf(self):
        "calculates the correct eps_inf for a given NP size"
        self.epsInf = 9.38 - 0.00339*self.npSize + 0.00021*pow(self.npSize, 2)
    
    def calcCavityWl(self): # calculates energies of lowest mode
        wp = self.wlEv(self.plasmaWl)
        en = wp/np.sqrt(self.epsInf + self.facetWidth*(self.gapRI**2)/(self.gapSize * 4.2)) # alpha antinodes: in NPoMv2 {4.2,9.4,15} to fit better?
        
        self.cavityWl = self.wlEv(en)

    def calcAntennaWl(self): #calculates coupled mode for spherical dimer using Felix Benz's circuit model
        wd = 1/np.sqrt(4*self.eta*self.gapRI + 2*self.gapRI + self.epsInf)
        
        if self.conductance == 0:
            self.antennaWl = self.plasmaWl/wd
        
        else:            
            Cs = 2*np.pi*(self.npSize/2)*self.eps0*self.gapRI*1e-9
            inductFh = self.inductance*1e-15
            gam = -inductFh*Cs*pow(self.plasmaFreq, 2)

            condS = np.multiply(self.condQuant, self.conductance)
            de = 1/pow((condS*inductFh*self.plasmaFreq), 2)

            bq = de + pow(wd, 2)*(4*self.envRI/gam - 1)
            cq = -de * pow(wd, 2)
            sqt = np.sqrt(pow(bq, 2) - 4*cq)
            self.antennaWl = self.plasmaWl*np.sqrt(2/(sqt - bq))

    def calcMixing(self): # calculates coupled plasmon from cavity mode coupled to antenna mode
        e1 = self.wlEv(self.antennaWl) # antenna mode, around 746nm
        e2 = self.wlEv(self.cavityWl) # cavity mode
        eo = 0.5*(e1 + e2) - np.sqrt(0.25*(e2 - e1)**2 + 0.11**2) # V=0.09 in NPoMv2 for 5 modes, increase to match
        
        self.coupledWl = self.wlEv(eo)
