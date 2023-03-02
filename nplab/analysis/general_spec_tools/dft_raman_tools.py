# -*- coding: utf-8 -*-
'''
Created on 2023-02-06
@author: car72

Module with specific functions for processing and analysing Gaussian output files
Uses code written by David-Benjamin Grys for extracting and polarising DFT Raman spectra
Bit slow and clunky at the moment but Rakesh says he wrote a smoother verstion; will update with this at some point soon

'''

import os
import numpy as np
import matplotlib.pyplot as plt
from nplab.analysis.general_spec_tools import sers_tools_david as std
from nplab.analysis.general_spec_tools import spectrum_tools as spt
from IPython.utils import io

from nplab.analysis.general_spec_tools import all_rc_params

dft_rc_params = all_rc_params.master_param_dict['DFT Raman']
bbox_params = all_rc_params.bbox_params

def gaussian_from_area(x, area, centre, fwhm):
    '''
    Returns a Gaussian curve defined by curve area, centre and fwhm
    
    Parameters:
    x: array-like
    a (area): float; total integrated area of curve
    c (centre): float; x-coordinate of maximum
    w (width): float; full-width at half maximum (fwhm)

    Output:
    numpy array of same size/shape as x
    '''

    x = np.array(x) # ensures x is treated as numpy array
    height = area/(abs(fwhm)*np.sqrt(2*np.pi)) # calculates height of curve based on area and fwhm

    return height*np.exp(-(((x-centre)**2)/(2*fwhm**2))) # calculates curve based on height, centre and fwhm

def broaden_raman_activities(vib_freqs, raman_activities, scale_factor = 0.9671, fwhm = 2, x_min = 0, 
                             x_max = None, n_points = 5000, plot = False, **kwargs):
    '''
    Processes DFT Raman data into a more useful continuous spectrum

    Inputs:
        vib_freqs: energies of normal modes in cm^-1; 1D numpy array
        raman_activities: corresponding Raman activities of the above; 1D numpy array
        w: float; desired fwhm (in cm^-1) of Raman peaks in output; int or float
        x_min, x_max: x limits of output spectrum; ints or floats
        n_points: length of output spectrum; int

    Output:
        x, y data of processed spectrum as numpy arrays
    '''
    n_points = int(round(n_points))

    x_raw = vib_freqs
    y = raman_activities
    
    x = x_raw * scale_factor # scale peak positions before processing

    if x_max is None:
        x_max = x.max() + 5*fwhm
        x_cont = np.linspace(0, x.max() + 5*fwhm, 5000) #continuous x-axis for output
    else:
        x_cont = np.linspace(x_min, x_max, 5000) #continuous x-axis for output

    y_cont = np.sum(np.array([gaussian_from_area(x_cont, a, c, fwhm) for c, a in zip(x, y)]), axis = 0) # transform each xy pair into gaussian centred at x coordinate, with area equal to y coordinate

    return x_cont, y_cont

def process_all_dft_raman(x_min = 182., x_max = 2616., polarisation = None, data_dir = None, 
                          extension = '.log', filenames = None, plot = False, **kwargs):
    
    if data_dir is not None:
        os.chdir(data_dir)

    print(f'Looking for DFT Raman files in {os.getcwd()}\n')

    output_files = [i for i in os.listdir() if i.endswith(extension)]

    if filenames is not None:
        filenames = [i if i.endswith(extension) else f'{i}{extension}' for i in filenames]
        #print(filenames)
        output_files = [i for i in output_files if i in filenames]

    data_dict = {}

    for output_file in output_files:
        print(output_file)
        gaussian_output = Gaussian_Output(output_file, polarisation_vector = polarisation, x_min = x_min, 
                                          x_max = x_max, **kwargs)
        if gaussian_output.gaussian_file.raman == True:
            print('\tRaman data extracted')
            data_dict[output_file] = gaussian_output

            if plot == True:
                gaussian_output.plot()

        else:
            print('\tNo Raman data found')

    return data_dict

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

class Gaussian_Output:
    '''
    Object for handling Gaussian output files
    Currently contains functions for extracting and processing calculated Raman activities
    '''
    def __init__(self, filename, scale_factor = 0.9671, process_data = True, x_min = None, x_max = None,
                 write_csv = False, csv_filename = None, polarisation_vector = None, fwhm = 5,
                 **kwargs):

        self.filename = filename
        self.scale_factor = scale_factor

        if csv_filename is None:
            csv_filename = filename
            if csv_filename[-4] == '.':
                csv_filename = csv_filename[:-4]
                csv_filename += '.csv'

        self.csv_filename = csv_filename        
        self.x_cont = None
        self.y_cont = None

        self.x_min = x_min
        self.x_max = x_max
        self.fwhm = fwhm

        self.vector_dict = {
                              'x' : (1, 0, 0),
                              'y' : (0, 1, 0),
                              'z' : (0, 0, 1),
                             'xy' : (1, 1, 0),
                             'xz' : (1, 0, 1),
                             'yz' : (0, 1, 1),
                            'xyz' : (1, 1, 1),
                            'iso' : None
                            }

        self.sers_activities_dict = {}
        self.polarised_spectrum_dict = {}

        gaussian_file = GaussianFile(self.filename)#create instance of GaussianFile object from David's code
        gaussian_file.parse()#extract relevant info from Gaussian output
        self.gaussian_file = gaussian_file

        if self.gaussian_file.raman == True:
            self.calculator = CalculatorMaster(gaussian_file)#create instance of SERS calculator object

            if process_data == True:

                if polarisation_vector == 'all':
                    polarisation_vector = self.vector_dict.keys()

                if polarisation_vector is None:
                    self.extract_sers_activities(polarisation_vector = polarisation_vector, **kwargs)

                elif type(polarisation_vector == list) and len(polarisation_vector) > 0 and type(polarisation_vector[0]) not in [int, float]:
                    print(f'Polarisations: {polarisation_vector}')
                    for v in polarisation_vector:
                        self.extract_sers_activities(polarisation_vector = v, **kwargs)
                else:
                    self.extract_sers_activities(polarisation_vector = polarisation_vector, **kwargs)

                if polarisation_vector is not None:
                    self.extract_raman_activities()

            if write_csv == True:
                if self.csv_filename is None:
                    self.csv_filename = f'{self.filename[:-4]}.csv'
                    
                self.write_to_csv()

    def extract_raman_activities(self, **kwargs):
        '''
        Extracts isotropic Raman activities from Gaussian output file (.com or .log extension)
        Only extracts raw values; does not scale
        '''
        #print(self.filename)
        print(f'Extracting isotropic Raman activities')
        with open(self.filename, 'r') as F:
            F_lines = F.readlines()

        self.vib_freqs = np.array([i.split()[-3:] for i in F_lines if 'Frequencies' in i]).flatten().astype(float)
        self.raman_activities = np.array([i.split()[-3:] for i in F_lines if 'Raman Activ' in i]).flatten().astype(float)    

        self.x_cont, self.y_cont = broaden_raman_activities(self.vib_freqs, self.raman_activities, 
                                                            scale_factor = self.scale_factor,
                                                            x_min = self.x_min, x_max = self.x_max,
                                                            **kwargs)

        self.sers_activities_dict['iso'] = np.array([self.vib_freqs, self.raman_activities])
        self.polarised_spectrum_dict['iso'] = np.array([self.x_cont, self.y_cont])
        
    def extract_sers_activities(self, polarisation_vector = 'x', **kwargs):
        '''
        Calculates SERS activities based on polarised excitation field.
        Uses code written by David-Benjamin Grys
        Will update with Rakesh's code soon
        polarisation_vector can be 'x', 'y', 'z', 'xz' etc; defaults to x
        alternatively, can input vector as tuple/list/array with relative components of x, y, z
        if polarisation vector is 'iso' or None, isotropic Raman activities are extracted
        '''

        if polarisation_vector == 'iso':
            polarisation_vector = None

        if polarisation_vector is None:
            self.extract_raman_activities(**kwargs)
            return

        if type(polarisation_vector) != str and len(polarisation_vector) == 3:
            polarisation_tuple = polarisation_vector = tuple(polarisation_vector)

        if type(polarisation_vector) == str:
            polarisation_tuple = self.vector_dict[polarisation_vector]

        print(f'Calculating SERS with polarisation: {polarisation_vector}')

        freqs, activities = self.calculator.calcSERS(polarisation_tuple)#calculate the SERS
        self.sers_activities_dict[polarisation_vector] = np.array([freqs, activities])
        self.polarised_spectrum_dict[polarisation_vector] = broaden_raman_activities(freqs, activities, x_min = self.x_min, x_max = self.x_max,
                                                                                     scale_factor = self.scale_factor, 
                                                                                     **kwargs)

    def extract_all_sers(self, **kwargs):
        print('Extracting all polarised SERS')
        for polarisation_vector in self.vector_dict:
            print(f'{polarisation_vector}')
            self.extract_sers_activities(polarisation_vector = polarisation_vector, **kwargs)

    def write_to_csv(self, write_spectrum = True, write_activities = False, polarisations = None, **kwargs):
        if 'csv' not in os.listdir():
            os.mkdir('csv')

        print(f'Writing to csv')

        if polarisations is None:
            polarisations = ['iso']

        elif polarisations == 'all':
            polarisations = list(self.sers_activities_dict.keys())

        elif type(polarisations) in (str, tuple):
            polarisations = [polarisations]

        for polarisation in polarisations:
            if polarisation not in self.sers_activities_dict.keys():
                self.extract_sers_activities(polarisation_vector = polarisation, **kwargs)        

            if write_activities == True:
                print(f'Writing csv/{self.csv_filename}_activities_{polarisation}')
                freqs, activities = self.sers_activities_dict[polarisation]
                with open(f'csv/{self.csv_filename[:-4]}_activities_{polarisation}.csv', 'w') as G:
                    for x, y in zip(freqs, activities):
                        G.write(f'{x},{y}\n')

            if write_spectrum == True:
                print(f'Writing csv/{self.csv_filename}_spectrum_{polarisation}')
                x_cont, y_cont = self.polarised_spectrum_dict[polarisation]
                with open(f'csv/{self.csv_filename[:-4]}_spectrum_{polarisation}.csv', 'w') as G:
                    for x, y in zip(x_cont, y_cont):
                        G.write(f'{x},{y}\n')

    def plot(self, ax = None, polarisation = None, rc_params = dft_rc_params, **kwargs):
    
        old_rc_params = plt.rcParams.copy()

        if ax is None:
            external_ax = False
            if rc_params is not None:
                plt.rcParams.update(rc_params)

            fig, ax = plt.subplots()

        else:
            external_ax = True        

        if polarisation is None:
            x, y = self.x_cont, self.y_cont
        else:
            if polarisation not in self.polarised_spectrum_dict.keys():
                self.extract_sers_activities(polarisation_vector = polarisation, **kwargs)

            x, y = self.polarised_spectrum_dict[polarisation]   
        
        ax.plot(x, y)
        ax.set_xlim(x.min(), x.max())
        ax.set_yticks([])
        ax.set_xlabel('Raman Shift (cm$^{-1}$)')
        ax.set_ylabel('Raman Activity')

        if external_ax == False:
            plt.show()
            plt.rcParams.update(old_rc_params)

class DFT_Raman_Collection:
    def __init__(self, dft_dir = None, dft_names = None, polarisations = None, x_min = None, x_max = None, fwhm = 5, **kwargs):
        root_dir = os.getcwd()
        self.dft_dict = process_all_dft_raman(data_dir = dft_dir, filenames = dft_names, fwhm = fwhm,
                                              polarisation = polarisation, x_min = x_min, x_max = x_max, **kwargs)
        os.chdir(root_dir)

        self.x_min = x_min
        self.x_max = x_max
        self.fwhm = fwhm

        if self.x_min is None:
            self.x_min = min([i.x_cont.min() for i in self.dft_dict.values()])

        if self.x_max is None:
            self.x_max = max([i.x_cont.max() for i in self.dft_dict.values()])

        self.x_range = np.array([self.x_min, self.x_max])

    def get_polar_dict(self, polarisations = {}):
        if len(polarisations) == 0:#extracts all gaussian jobs and all polarisations specified when initialising
            polar_dict = {gaussian_filename : list(gaussian_job.sers_activities_dict.keys())
                          for gaussian_filename, gaussian_job in self.dft_dict.items()}

        elif type(polarisations) in (tuple, list):#extracts all gaussian jobs and all polarisations specified when running plot_dft
            polar_dict = {gaussian_filename : list(polarisations)
                          for gaussian_filename in self.dft_dict.keys()}

        else:#uses user-defined gaussian jobs and polarisations specified when running plot_dft
            polar_dict = polarisations

        self.polar_dict = polar_dict
        self.n_spectra = len([polar for polar_list in polar_dict.values() for polar in polar_list])

    def plot_dft(self, polarisations = {}, x_range = None, text_loc = None, text_pad = 0.2,
                 ax = None, y_offset = 0, rc_params = dft_rc_params, fwhm = 5, **kwargs):
        '''
        Plots a selection of DFT Raman spectra on a given axes
        By default, plots Raman of all gaussian files in the collection and any polarisations specified when initialising the instance of DFT_Collection
        Inputs:
            polarisations: dictionary or list/tuple
                if dictionary: in format {filename : [list or tuple of polarisations for each]}
                If list/tuple: list polarisations only and these polarisations will be plotted for all files
                If you input a polarisation that hasn't been calculated yet, it will be calculated and stored
            x_range: xlim within which to plot. If none, uses x_range of parent class
            text_loc: location of spectrum labels
                defaults to upper-left corner, but can be in-line with spectrum if x-position is specified as int or float
                set text_loc = False to disable
            text_pad: distance of text from edge of plot if text_loc = None
            ax: axes on which to plot the data. If None, new fig & ax are created
            y_offset: default = 0; used for plotting on same axes as other spectra
            rc_params: style formatting dictionary (plt.rcParams) for pyplot; set rc_params = None to use current plt.rcParams without modifications

        '''

        if polarisations is not None:
            self.get_polar_dict(polarisations = polarisations)

        if x_range is None:
            x_range = self.x_range

        x_range = np.array(x_range)

        old_rc_params = plt.rcParams.copy()

        if ax is None:
            external_ax = False
            if rc_params is not None:
                plt.rcParams.update(rc_params)

            fig, ax = plt.subplots(figsize = (12, 1*self.n_spectra))

        else:
            external_ax = True

        for n, (gaussian_filename, polarisations) in enumerate(self.polar_dict.items()):
            gaussian_job = self.dft_dict[gaussian_filename]

            if fwhm != self.fwhm:
                print('Re-calculating broadened spectra with new fwhm')

            for m, polarisation in enumerate(polarisations):
                if polarisation not in gaussian_job.polarised_spectrum_dict.keys() or fwhm != self.fwhm:
                    with io.capture_output(fwhm != self.fwhm):
                        gaussian_job.extract_sers_activities(polarisation, fwhm = fwhm)


                x, y = gaussian_job.polarised_spectrum_dict[polarisation]

                y_norm = y - y.min()
                y_norm = y_norm/y_norm.max()
                y_norm += y_offset
                y_offset += 1

                ax.plot(x, y_norm)

                if text_loc is not False:
                    if text_loc == None:
                        x_loc = x_range.min() + text_pad*(x_range.max() - x_range.min())/15
                        y_loc = y_norm.max() - text_pad
                        va = 'top'

                    elif type(text_loc) in [int, float]:
                        x_loc = text_loc
                        y_loc = y_norm.min() + text_pad
                        va = 'bottom'

                    else:
                        print('Text loc not recognised; please specify x-position (int or float), leave blank or set text_loc = False')

                system_name = gaussian_filename[:-4].strip('_Raman').replace('_', ' ')

                ax.text(x_loc, y_loc, f'{system_name} ({polarisation})',
                        transform = ax.transData, ha = 'left', va = va, bbox = bbox_params,
                        fontsize = plt.rcParams['legend.fontsize']
                    )
        if fwhm != self.fwhm:
            print('\tDone')
            self.fwhm = fwhm

        if external_ax == False:
            ax.set_xlabel('Raman Shift (cm$^{-1}$)')
            ax.set_xlim(*x_range)
            ax.set_ylim(-0.05, y_norm.max() + 0.05)
            plt.show()
            plt.rcParams.update(old_rc_params)

        else:
            ax.set_ylim(top = y_norm.max() + 0.15)

    def write_all_csv(self, **kwargs):
        for filename, gaussian_output in self.dft_dict.items():
            gaussian_output.write_to_csv(**kwargs)


        