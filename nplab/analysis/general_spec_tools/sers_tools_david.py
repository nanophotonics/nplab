# -*- coding: utf-8 -*-
'''
Created on 2023-02-06
@author: car72

Adaptation of SERS-tools written by David-Benjamin Grys, for use without GUI

'''

import os
import numpy as np 

class Atom:
    def __init__(self, atno, fixed, inp_coords):
        self.atno = atno
        self.inp_coords = inp_coords
        self.opt_coords = (0,0,0) 
        self.opt_coords_steps = [] # list of 3-tuples
        # list of 3-tuple dr = (x,y,z) 
        self.vib_displ = [] 
        self.pol_tensors = []
        
        self.fixed = fixed
        
        # Polarisability Derivatives Tensor 
        self.polar_der_dx = [] #6 axx, axy, ayy, axz, ayz, azz
        self.polar_der_dy = [] #6
        self.polar_der_dz = [] #6
        
    def polTensorDer(self, d): #d=0 dx, d=1, dy, d=2 dz    
        der = [self.polar_der_dx, self.polar_der_dy, self.polar_der_dz]    
        tensor = [[der[d][0], der[d][1], der[d][3]],[der[d][1], der[d][2], der[d][4]],[der[d][3], der[d][4], der[d][5]]]
        return np.matrix(tensor)
              
    def getPos(self):
        return self.opt_coords

    def getPosOpt(self):
        return self.opt_coords_steps[-1]

class Molecule:
    def __init__(self):
        self.atoms = []
        self.current = -1
        self.charge = 0
        self.multiplicity = 0
        self.sers_dipols = []
        
    def __iter__(self):
        return self
    
    def append(self, atom):
        self.atoms.append(atom)
    
    def __next__(self):
        if self.current > len(self.atoms)-2:
            self.current = -1
            raise StopIteration
        else:
            self.current += 1
            return self.atoms[self.current]  
        
    def __getitem__(self, n):
        return self.atoms[n]
    
    def count(self):
        return len(self.atoms)

class GaussianJob:
    def __init__(self):
        self.type = ''
        self.user = ''
        self.computer = ''
        self.functional = ''
        self.rmsd = 0
        self.dipole = [] # 3-tuple
        self.hf = 0
        
        # mode -> (frequency, red masses, frc const, IR, Raman, DepP, DepU)
        self.vibra_modes = []
                
        # Molecule
        self.molecule = Molecule()
        
        # Freq Job
        self.is_freq_job = False
        self.red_mass = []
        self.vib_freq = []
        self.red_mass = []
        self.frc_const = []
        self.ir_int = []
        self.raman_activ = []
        self.depol_p = []
        self.depol_u = []
        self.polar_der = [] # list osf polarization derivatives
        
class GaussianFile:        
    def __init__(self, filename):
        self.filename = filename
        
        # 2-tuple [(start,end),..]
        self.line_input_data  = []
        self.line_output_data = []
        self.line_freq_data = []
        self.line_optstep_data = []
        self.raman = False
        self.opt = False
                
        # list of GaussianJob
        self.job = GaussianJob()
        
    def parse(self):
        # open file
        f = open(self.filename)
        lines = f.readlines()
        
        line_input_data  = []
        line_output_data = []
        line_freq_data = []
        line_optstep_data = []
          
        # Seek for input/output data start
        for n, line in enumerate(lines):
            if line[1:19] == 'Symbolic Z-matrix:':
                #print('input data found')
                line_input_data.append((n,-1))
            
            if line[1:5] == '1\\1\\':
                #print('output data found')
                line_output_data.append((n,-1))  
                
            if line[1:24] == 'and normal coordinates:':
                #print('freq data found')
                self.raman = True
                line_freq_data.append((n,-1))
                
            if line[1:67] == 'Number     Number       Type             X           Y           Z':
                #print('steps found')
                self.opt = True
                line_optstep_data.append((n,-1))

        # Seek for input data stop
        for k, n in enumerate(line_input_data):    
            i = n[0]
            while lines[i] != ' \n':
                i+=1
            line_input_data[k] = (line_input_data[k][0], i) 
            
        # Seek for output data stop
        for k, n in enumerate(line_output_data):
            i = n[0]
            while not lines[i][:-1].endswith('\\\\@'):
                i += 1
                
            line_output_data[k] = (line_output_data[k][0], i+1)
            
        # Seek for output data freq stop
        for k, n in enumerate(line_freq_data):    
            i = n[0]
            while lines[i].strip() != '':
                i+=1
            line_freq_data[k] = (line_freq_data[k][0], i+1)      
                    
        self.line_input_data  = line_input_data
        self.line_output_data = line_output_data
        self.line_freq_data = line_freq_data

        if len(self.line_input_data) > 0:        
            ### parse input ### 
            line_start = line_input_data[0][0]
            line_end = line_input_data[0][1]
            
            # charge/multiplicity 
            line = lines[line_start+1]
            self.job.molecule.charge = int(line.split()[2])
            self.job.molecule.multiplicity = int(line.split()[5])
            
            # create atoms from input
            for n in range(line_start+2,line_end): #start from +2 line
                if len(lines[n].split()) > 4:
                    atno = lines[n].split()[0]
                    fixed = True
                    inp_coords = tuple(lines[n].split()[2:5])
                else:
                    atno = lines[n].split()[0]
                    fixed = False
                    inp_coords = tuple(lines[n].split()[1:4])
                atom = Atom(atno, fixed, inp_coords)  
                self.job.molecule.append(atom)
        
        if len(self.line_output_data) > 0:  
            ### parse jobs ###

            for njob in range(0,len(line_output_data)):                
                output_data = []

                for line in lines[line_output_data[njob][0]:line_output_data[njob][1]]:
                    output_data.append(line.strip())
                    
                output_data = ''.join(output_data)
                output_data = output_data.split('\\')
                
                #header
                #print(f'Computer = {output_data[2]}')
                #print(f'Type = {output_data[3]}')
                #print(f'Functional= {output_data[4]}')
                #print(f'User = {output_data[7]}')
                self.job.computer = output_data[2]
                self.job.type = output_data[3]
                self.job.functional = output_data[4]
                self.job.user = output_data[7]
                
                # Extract opt_coords
                for i, line in enumerate(output_data[16:16+self.job.molecule.count()]):
                    line = line.split(',')
                    line = [float(i) for i in line[1:4]] # convert to float
                    self.job.molecule[i].opt_coords = tuple((line[0:3]))
                      
                # Freq specific data such as polar-derivatives
                
                if(self.job.type == 'Freq'):
                    #print('freq')
                    for i, data in enumerate(output_data):
                        if(data[0:11]=='PolarDeriv='):
                            polar_der = (data[11:].split(','))
                            polar_der = [float(i) for i in polar_der] # convert to float
                            self.job.polar_der = polar_der
                    for n in range(0, len(polar_der),18):
                        k = int(n/18)
                        self.job.molecule.atoms[k].polar_der_dx = polar_der[n:n+6]
                        self.job.molecule.atoms[k].polar_der_dy = polar_der[n+6:n+12]
                        self.job.molecule.atoms[k].polar_der_dz = polar_der[n+12:n+18]

        if len(line_optstep_data) > 0:
            ### parse optimization steps (internal coordinates
            for nstep in line_optstep_data:
                line_start = nstep[0]
                natoms = len(self.job.molecule.atoms)
                for i in range(0, natoms):
                    line = lines[line_start+i+2].strip().split() #skiiping two lines
                    x = float(line[3])
                    y = float(line[4])
                    z = float(line[5])
                    self.job.molecule.atoms[i].opt_coords_steps.append((x,y,z)) #3-tuple   
        
        vib_freq = []
        red_mass = []
        frc_const = []
        ir_int = []
        raman_activ = []
        depol_p = []
        depol_u = []

        if self.raman == True:
            ### parse frequencies ###
            #print(line_freq_data)
            line_start = line_freq_data[0][0]
            line_end = line_freq_data[0][1]       

            cols = []
            for i in range(line_start+1,line_end-1):            
                line = lines[i].strip().split()
                if(line[0] == "Frequencies"):
                    for c in range(0,cols[-1]):
                        vib_freq.append(float(line[2+c]))      
                elif(line[0] == "Red."):
                    for c in range(0,cols[-1]):
                        red_mass.append(line[3+c])  
                elif(line[0] == "Frc"):
                    for c in range(0,cols[-1]):
                        frc_const.append(line[3+c])                      
                elif(line[0] == "IR"):
                    for c in range(0,cols[-1]):
                        ir_int.append(line[3+c])    
                elif(line[0] == "Raman"):
                    for c in range(0,cols[-1]):
                        raman_activ.append(line[3+c])                       
                elif(line[0] == "Depolar"):
                    for c in range(0,cols[-1]):
                        if(line[1] == '(P)'):
                            depol_p.append(line[3+c]) 
                        else:
                            depol_u.append(line[3+c]) 
                elif(line[0] == 'Atom'):
                    pass
                elif(len(line) <= 3):
                    if(line[0] != 'A'):
                        cols.append(len(line))
                else: #atom displacement
                    n = int(line[0])-1 # 1 -> 0
                    for c in range(0,cols[-1]):
                        line = [float(i) for i in line] # convert to float
                        self.job.molecule[n].vib_displ.append([line[2+3*c:5+3*c]]) 
             
        self.job.vib_freq = vib_freq
        self.job.red_mass = red_mass
        self.job.frc_const = frc_const
        self.job.ir_int = ir_int
        self.job.raman_activ = [float(s) for s in raman_activ]
        self.job.depol_p = depol_p 
        self.job.depol_u = depol_u

class RamanCalculator():
    def __init__(self, job):
        self.job = job
        self.vibs = self.job.vib_freq
        self.raman_tensors = []
        self.raman_activities = []
        self.sers_activities = []
    
    def calcRamanTensors(self):
        raman_tensors = [] # list of k Raman tensors, (3x3) matrix each
        
        # Going through all k = 2N vibrations
        for k in range(0, len(self.job.vib_freq)): 
            raman_tensors.append(np.matrix(np.zeros((3,3)))) # each vibration has a 3x3 Raman tensor (RT)  
            
            # adding-up contribution of each atom 
            for atom in self.job.molecule.atoms: 
                if len(atom.vib_displ) > 0: # Fixed atoms (-1) have no displacement
                    phi_x = atom.vib_displ[k][0][0] # phi: normalised displacement
                    phi_y = atom.vib_displ[k][0][1] 
                    phi_z = atom.vib_displ[k][0][2]
    
                    alpha_dx = atom.polTensorDer(0)* 0.279841 # polarisability tensor derivatives 
                    alpha_dy = atom.polTensorDer(1)* 0.279841 # units corrected from B^2 to A^2 (0.279841)
                    alpha_dz = atom.polTensorDer(2)* 0.279841 #
                    
                    atom.pol_tensors.append(phi_x*alpha_dx + phi_y*alpha_dy + phi_z*alpha_dz )
                    
                    raman_tensors[k] += phi_x*alpha_dx + phi_y*alpha_dy + phi_z*alpha_dz # adding up contributions to RT 
            
            raman_tensors[k] /= np.sqrt(float((self.job.red_mass[k]))) # normalising RT to reduced mass
        
        self.raman_tensors = raman_tensors
            
    def calcRamanActivity(self):
        for raman_tensor in self.raman_tensors:
            a = raman_tensor.trace()/3.0
            # Calculation of averaged Raman activity
            g0 = np.square(raman_tensor[0,0]-raman_tensor[1,1])
            g1 = np.square(raman_tensor[1,1]-raman_tensor[2,2])
            g2 = np.square(raman_tensor[2,2]-raman_tensor[0,0])
            g3 = np.square(raman_tensor[0,1]) + np.square(raman_tensor[0,2]) + np.square(raman_tensor[1,2])
            g = (g0+g1+g2)/2.0 + 3.0*g3
            
            activity = 45.0*np.square(a) + 7*(g)
            
            self.raman_activities.append(activity[(0,0)])
    
    def calcSERSActivity(self, r_inc):
        self.sers_activities = []
        self.job.molecule.sers_dipols = []
        r_inc *= 1
        
        for atom in self.job.molecule:
            atom.dipole = []
        
        for k, raman_tensor in enumerate(self.raman_tensors): 
            dipole = raman_tensor*r_inc
            activity = np.abs(np.dot(np.transpose(r_inc), dipole))
            self.sers_activities.append(activity[(0,0)])
            self.job.molecule.sers_dipols.append(dipole)
            
            for atom in self.job.molecule:              
                if len(atom.vib_displ) > 0:
                    atom.dipole.append(atom.pol_tensors[k]*r_inc)

    '''def lorentz(self, x, *p):
                    I, gamma, x0 = p
                    return I * gamma**2 / ((x - x0)**2 + gamma**2)
            
                def getLorentzIntp(self, vib_wn, vib_int, wn_start,wn_end, wn_n, gamma):
                    vib_wn_intp = np.linspace(wn_start,wn_end, wn_n)
                    vib_int_intp = np.zeros(wn_n)
            
                    for wn_k,int_k in zip(vib_wn,vib_int):
                        int_k_intp = self.lorentz(vib_wn_intp, int_k, gamma, wn_k)
                        vib_int_intp += int_k_intp
                    return [vib_wn_intp, vib_int_intp]'''

class CalculatorMaster:
    def __init__(self, gaussianFile):
        self.gaussianFile = gaussianFile # instance of GaussianFile class
        
        self.RotPhi = 0
        self.RotTheta = 0    
        
        ### Calculate Raman tensor and Raman aactivities ###
        self.ramanCalculator = RamanCalculator(self.gaussianFile.job)
        self.ramanCalculator.calcRamanTensors()
        self.ramanCalculator.calcRamanActivity()        
        
    def calcSERS(self, excitation_vector):
        '''
        Excitation vector: 1D array/list/tuple of length 3 [x, y, z]

        '''
        x, y, z = excitation_vector

        excitation_vector = np.array([[x],[y],[z]])
        excitation_vector = excitation_vector/np.linalg.norm(excitation_vector)
        
        self.ramanCalculator.calcSERSActivity(excitation_vector) 

        vibs = np.array(self.ramanCalculator.vibs)
        sers_activities = np.array(self.ramanCalculator.sers_activities)
        
        return vibs, sers_activities