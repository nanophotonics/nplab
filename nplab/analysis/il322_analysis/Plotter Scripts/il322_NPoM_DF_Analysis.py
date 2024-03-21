# -*- coding: utf-8 -*-
"""
Created on Mon Apr 17 10:50:52 2023

@author: il322
"""


import numpy as np
import scipy as sp
from matplotlib import pyplot as plt
import matplotlib as mpl
import tkinter as tk
from tkinter import filedialog
import statistics
from scipy.stats import linregress
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter
from pylab import *
import nplab
import h5py
import natsort
import os


from nplab.analysis.general_spec_tools import spectrum_tools as spt
from nplab.analysis.general_spec_tools import npom_df_pl_tools as df


plt.rc('font', size=18, family='sans-serif')
plt.rc('lines', linewidth=3)


h5_60nm = h5py.File(r'C:\Users\il322\Desktop\Offline Data\2023-03-25_M-TAPP-SME_60nm_NPoM_Track_DF_Powerseries.h5')
h5_80nm = h5py.File(r'C:\Users\il322\Desktop\Offline Data\2023-03-31_M-TAPP-SME_80nm_NPoM_Track_DF_Powerseries.h5')
h5_new = h5py.File(r'C:\Users\il322\Desktop\Offline Data\2023-05-12.h5')
#%%
def track_to_critical_wlns(my_h5, particle_scan_list, np_size=80, plot=False):
    
    '''
    Takes particle track scans and outputs array of critical wavelengths
    
    Need to fix centering screening
    '''

    particle_counter = 0
    wln_c_array = []
    rejected = []
    cpu_rejected = []
    # Loop over particle scans
    for particle_scan_name in particle_scan_list:
        print('\n'+ particle_scan_name)
        particle_scan = my_h5[particle_scan_name] 
        all_data_groups = natsort.natsorted(list(particle_scan.keys()))
        all_particle_groups = []
        
        ## Loop over all data groups in particle scan, pick out particle groups
        for data_group in all_data_groups:
            if 'Particle' in str(data_group):
                all_particle_groups.append(data_group)
        
        ## Loop over all particle groups in particle scan         
        for particle_group in all_particle_groups:
            particle_group = particle_scan[particle_group]
            particle_name = str(particle_group)[str(particle_group).find('Particle_'):str(particle_group).rfind('"')]
            print('\n' + particle_name)
            
            ### Find z-scan in particle group
            z_scan = 0
            image = 0
            for item_i, item in enumerate(list(particle_group.items())):
                if 'lab.z_scan' in str(item):    
                    z_scan = particle_group[list(particle_group.items())[item_i][0]]
                if 'CWL' in str(item):
                    image = particle_group[list(particle_group.items())[item_i][0]]
            if z_scan == 0:
                print('No z-scan found, skipping particle')
                cpu_rejected.append(particle_scan_name + ': ' + particle_name)
                break
            
            ### Find sample name from SERS scan attributes
            SERS_scan = 0
            for item_i, item in enumerate(list(particle_group.items())):
                if 'kinetic_SERS' in str(item):    
                    SERS_scan = particle_group[list(particle_group.items())[item_i][0]]
                    sample = str(SERS_scan.attrs['sample'])
            if SERS_scan == 0:
                sample = ''
                print('Sample name unknown')    
            
            ### z_scan analysis
            z_scan = df.NPoM_DF_Z_Scan(z_scan,
                                       z_min = z_scan.attrs['neg'],
                                       z_max = z_scan.attrs['pos'],
                                       z_trim=0,
                                       particle_name = particle_name)
            z_scan.check_centering()
            if plot == True:
                plt.figure(figsize=[7,16])    
                plt.suptitle(sample + '\n' + particle_scan_name + ': ' + particle_name)
                ax1=plt.subplot(3,1,1)
                ax2=plt.subplot(3,1,2, sharex=ax1)
                ax3 = plt.subplot(3,1,3)
                ax1.get_xaxis().set_visible(False)
                ax1.set_title('Z-Scan')
                z_scan.plot_z_scan(ax=ax1)
                ax2.set_title('Stacked Dark-field Spectrum')
                ax3.set_title('Image')
                plt.tight_layout(pad = 2)
       
            #### If centeting is good, condense z_scan into single df_spectrum
            if z_scan.aligned == True:
                z_scan.condense_z_scan()
                
                df_spectrum = df.NPoM_DF_Spectrum(x = z_scan.x,
                                                  y = z_scan.df_spectrum,
                                                  y_smooth = spt.butter_lowpass_filt_filt(z_scan.df_spectrum),
                                                  np_size = np_size)
                
                ''' Thresholding to detect maxima is not perfect'''
                df_spectrum.find_maxima(smooth_first=True, upper_threshold = -1650)
                df_spectrum.test_if_npom()
                if df_spectrum.y.max() < 0:
                    df_spectrum.is_npom = False
                    df_spectrum.not_npom_because = 'intensity below threshold'

                
                if df_spectrum.is_npom == True: 
                    ##### Pick wavelength of maximum intensity in df_spectrum
                    wln_c = df_spectrum.x[np.argmax(df_spectrum.y_smooth)] 
                    print('Critical Wavelength: ' + str(wln_c))
                    
                    
                    particle_counter += 1
                    
                    if plot == True:
                        df_spectrum.plot_df(ax=ax2, smooth = True)
                        ax2.set_yticks(np.around(np.linspace(1600, 2500, 10)))
                        ax2.scatter(wln_c, df_spectrum.y.max(), marker='*', s=500, color='black', zorder=20)
                        for maximum in df_spectrum.maxima:
                            ax2.scatter(df_spectrum.x[maximum], df_spectrum.y[maximum], marker='x', s=250, color='red', zorder=10)
                        
                else:
                    print('NPoM Test failed, skipping particle')
                    if plot == True:
                        df_spectrum.plot_df(ax=ax2, smooth=True)
                        ax2.set_yticks(np.around(np.linspace(1600, 2500, 10)))
                        for maximum in df_spectrum.maxima:
                            ax2.scatter(df_spectrum.x[maximum], df_spectrum.y[maximum], marker='x', s=250, color='red', zorder=10)
                        ax2.text(s='NPoM Test failed: ' + df_spectrum.not_npom_because, x=350, y=(df_spectrum.y.max() + df_spectrum.y.min())/2, fontsize = 20, zorder=20)
                        cpu_rejected.append(particle_scan_name + ': ' + particle_name)
                
            else:
                print('Centering failed, skipping particle')
                if plot == True:
                    ax2.text(s='Centering Failed', x=400, y=0.5, fontsize = 40)
                cpu_rejected.append(particle_scan_name + ': ' + particle_name)
                    
            ## Plot CWL image
            if plot == True and image != 0:
                print(str(image))
                ax3.imshow(image, zorder=500)
                plt.show()
                
            # Manual rejection
            ar = input('a/d = accept/decline: ').strip().lower()
            if ar == 'a':
                wln_c_array.append(wln_c)
                pass
            if ar == 'd':
                rejected.append(particle_scan_name + ': ' + particle_name)
                
    
    return np.array(wln_c_array), rejected, cpu_rejected

#%%

def track_to_critical_wlns_manual(my_h5, particle_scan_list, np_size=80, plot=False, rejected = []):
    
    '''
    Takes particle track scans and outputs array of critical wavelengths - excludes manually rejected particles
    
    Need to fix centering screening
    '''
    
    particle_counter = 0
    wln_c_array = []
    
    if len(rejected) > 0:
        with open(rejected, "r") as rejected:
            rejected = rejected.read().splitlines()
           
    # Loop over particle scans
    for particle_scan_name in particle_scan_list:
        print('\n'+ particle_scan_name)
        particle_scan = my_h5[particle_scan_name] 
        all_data_groups = natsort.natsorted(list(particle_scan.keys()))
        all_particle_groups = []
        
        ## Loop over all data groups in particle scan, pick out particle groups
        for data_group in all_data_groups:
            if 'Particle' in str(data_group):
                all_particle_groups.append(data_group)
        
        ## Loop over all particle groups in particle scan         
        for particle_group in all_particle_groups:
            particle_group = particle_scan[particle_group]
            particle_name = str(particle_group)[str(particle_group).find('Particle_'):str(particle_group).rfind('"')]
            print('\n' + particle_name)
            
            ### Find z-scan in particle group
            z_scan = 0
            image = 0
            for item_i, item in enumerate(list(particle_group.items())):
                if 'lab.z_scan' in str(item):    
                    z_scan = particle_group[list(particle_group.items())[item_i][0]]
                if 'CWL' in str(item):
                    image = particle_group[list(particle_group.items())[item_i][0]]
            if z_scan == 0:
                print('No z-scan found, skipping particle')
                break
            
            ### Find sample name from SERS scan attributes
            SERS_scan = 0
            for item_i, item in enumerate(list(particle_group.items())):
                if 'kinetic_SERS' in str(item):    
                    SERS_scan = particle_group[list(particle_group.items())[item_i][0]]
                    sample = str(SERS_scan.attrs['sample'])
            if SERS_scan == 0:
                sample = ''
                print('Sample name unknown')    
            
            ### z_scan analysis
            z_scan = df.NPoM_DF_Z_Scan(z_scan,
                                       z_min = z_scan.attrs['neg'],
                                       z_max = z_scan.attrs['pos'],
                                       z_trim=0,
                                       particle_name = particle_name)
            z_scan.check_centering()
            if plot == True:
                plt.figure(figsize=[7,16])    
                plt.suptitle(sample + '\n' + particle_scan_name + ': ' + particle_name)
                ax1=plt.subplot(3,1,1)
                ax2=plt.subplot(3,1,2, sharex=ax1)
                ax3 = plt.subplot(3,1,3)
                ax1.get_xaxis().set_visible(False)
                ax1.set_title('Z-Scan')
                z_scan.plot_z_scan(ax=ax1)
                ax2.set_title('Stacked Dark-field Spectrum')
                ax3.set_title('Image')
                plt.tight_layout(pad = 2)
       
            #### If centeting is good, condense z_scan into single df_spectrum
            if z_scan.aligned == True:
                z_scan.condense_z_scan()
                
                df_spectrum = df.NPoM_DF_Spectrum(x = z_scan.x,
                                                  y = z_scan.df_spectrum,
                                                  y_smooth = spt.butter_lowpass_filt_filt(z_scan.df_spectrum),
                                                  np_size = np_size)
                
                ''' Thresholding to detect maxima is not perfect'''
                df_spectrum.find_maxima(smooth_first=True, upper_threshold = -1650)
                df_spectrum.test_if_npom()
                    
                if (particle_scan_name + ': ' + particle_name) in rejected:
                    df_spectrum.is_npom = False
                    df_spectrum.not_npom_because = 'manually rejected'
                    print('MANUAL REJECTION')
                    plt.plot(10,10)
                
                if df_spectrum.is_npom == True:
                    
                    ##### Pick wavelength of maximum intensity in df_spectrum
                    wln_c = df_spectrum.x[np.argmax(df_spectrum.y_smooth)] 
                    print('Critical Wavelength: ' + str(wln_c))
                    wln_c_array.append(wln_c)
                    
                    particle_counter += 1
                    
                    if plot == True:
                        df_spectrum.plot_df(ax=ax2, smooth = True)
                        ax2.set_yticks(np.around(np.linspace(1600, 2500, 10)))
                        ax2.scatter(wln_c, df_spectrum.y.max(), marker='*', s=500, color='black', zorder=20)
                        for maximum in df_spectrum.maxima:
                            ax2.scatter(df_spectrum.x[maximum], df_spectrum.y[maximum], marker='x', s=250, color='red', zorder=10)
                        
                else:
                    print('NPoM Test failed: ' + df_spectrum.not_npom_because + '. Skipping particle')
                    if plot == True:
                        df_spectrum.plot_df(ax=ax2, smooth=True)
                        ax2.set_yticks(np.around(np.linspace(1600, 2500, 10)))
                        for maximum in df_spectrum.maxima:
                            ax2.scatter(df_spectrum.x[maximum], df_spectrum.y[maximum], marker='x', s=250, color='red', zorder=10)
                        ax2.text(s='NPoM Test failed: ' + df_spectrum.not_npom_because, x=350, y=(df_spectrum.y.max() + df_spectrum.y.min())/2, fontsize = 20, zorder=20)
                
            else:
                print('Centering failed, skipping particle')
                if plot == True:
                    ax2.text(s='Centering Failed', x=400, y=0.5, fontsize = 40)
                    
            ## Plot CWL image
            if plot == True and image != 0:
                ax3.imshow(image, zorder=500)
                plt.show()
                
    
    return np.array(wln_c_array)

#%%

H2_new_wln_c =  track_to_critical_wlns(h5_new, ['ParticleScannerScan_2'], plot=True)

#%% Running function & recording manual & cpu rejections

# H2_80nm_wln_c, rejected, cpu_rejected = track_to_critical_wlns(h5_80nm, ['ParticleScannerScan_1', 'ParticleScannerScan_2'], np_size = 80, plot=True)
# with open(r'C:\Users\il322\Desktop\Offline Data\2023-03-31_H2-TAPP-SME_80nm_DF_Rejected.txt', 'w') as fp:
#     fp.write('\n'.join(rejected))
# with open(r'C:\Users\il322\Desktop\Offline Data\2023-03-31_H2-TAPP-SME_80nm_DF_CPU_Rejected.txt', 'w') as fp:
#     fp.write('\n'.join(cpu_rejected))

# Co_80nm_wln_c, rejected, cpu_rejected = track_to_critical_wlns(h5_80nm,['ParticleScannerScan_3', 'ParticleScannerScan_4',
#                                         'ParticleScannerScan_5', 'ParticleScannerScan_6',
#                                         'ParticleScannerScan_7', 'ParticleScannerScan_8',
#                                         'ParticleScannerScan_9'], np_size = 80, plot=True)
# with open(r'C:\Users\il322\Desktop\Offline Data\2023-03-31_Co-TAPP-SME_80nm_DF_Rejected.txt', 'w') as fp:
#     fp.write('\n'.join(rejected))
# with open(r'C:\Users\il322\Desktop\Offline Data\2023-03-31_Co-TAPP-SME_80nm_DF_CPU_Rejected.txt', 'w') as fp:
#     fp.write('\n'.join(cpu_rejected))
    
# Ni_80nm_wln_c, rejected, cpu_rejected = track_to_critical_wlns(h5_80nm, ['ParticleScannerScan_10', 'ParticleScannerScan_11'],
#                                        np_size = 80, plot = True)
# with open(r'C:\Users\il322\Desktop\Offline Data\2023-03-31_Ni-TAPP-SME_80nm_DF_Rejected.txt', 'w') as fp:
#     fp.write('\n'.join(rejected))
# with open(r'C:\Users\il322\Desktop\Offline Data\2023-03-31_Ni-TAPP-SME_80nm_DF_CPU_Rejected.txt', 'w') as fp:
#     fp.write('\n'.join(cpu_rejected))

# H2_60nm_wln_c, rejected, cpu_rejected = track_to_critical_wlns(h5_60nm, ['ParticleScannerScan_2'], np_size = 60, plot = True)
# with open(r'C:\Users\il322\Desktop\Offline Data\2023-03-25_H2-TAPP-SME_60nm_DF_Rejected.txt', 'w') as fp:
#     fp.write('\n'.join(rejected))
# with open(r'C:\Users\il322\Desktop\Offline Data\2023-03-25_H2-TAPP-SME_60nm_DF_CPU_Rejected.txt', 'w') as fp:
#     fp.write('\n'.join(cpu_rejected))
    
# Co_60nm_wln_c, rejected, cpu_rejected = track_to_critical_wlns(h5_60nm,['ParticleScannerScan_3'], np_size = 60, plot = True)
# with open(r'C:\Users\il322\Desktop\Offline Data\2023-03-25_Co-TAPP-SME_60nm_DF_Rejected.txt', 'w') as fp:
#     fp.write('\n'.join(rejected))
# with open(r'C:\Users\il322\Desktop\Offline Data\2023-03-25_Co-TAPP-SME_60nm_DF_CPU_Rejected.txt', 'w') as fp:
#     fp.write('\n'.join(cpu_rejected))
    
# Ni_60nm_wln_c, rejected, cpu_rejected = track_to_critical_wlns(h5_60nm, ['ParticleScannerScan_4'], np_size = 60, plot = True)
# with open(r'C:\Users\il322\Desktop\Offline Data\2023-03-25_Ni-TAPP-SME_60nm_DF_Rejected.txt', 'w') as fp:
#     fp.write('\n'.join(rejected))
# with open(r'C:\Users\il322\Desktop\Offline Data\2023-03-25_Ni-TAPP-SME_60nm_DF_CPU_Rejected.txt', 'w') as fp:
#     fp.write('\n'.join(cpu_rejected))
    
# Zn_60nm_wln_c, rejected, cpu_rejected = track_to_critical_wlns(h5_60nm, ['ParticleScannerScan_5'], np_size = 60, plot = True)
# with open(r'C:\Users\il322\Desktop\Offline Data\2023-03-25_Zn-TAPP-SME_60nm_DF_Rejected.txt', 'w') as fp:
#     fp.write('\n'.join(rejected))
# with open(r'C:\Users\il322\Desktop\Offline Data\2023-03-25_Zn-TAPP-SME_60nm_DF_CPU_Rejected.txt', 'w') as fp:
#     fp.write('\n'.join(cpu_rejected))


# #%% Running tracks to critical wlns function while excluding manual rejections

# H2_80nm_wln_c = track_to_critical_wlns_manual(h5_80nm, ['ParticleScannerScan_1', 'ParticleScannerScan_2'], np_size = 80, plot = False,
#                                               rejected = r'C:\Users\il322\Desktop\Offline Data\2023-03-31_H2-TAPP-SME_80nm_DF_Rejected.txt')

# Co_80nm_wln_c = track_to_critical_wlns_manual(h5_80nm,['ParticleScannerScan_3', 'ParticleScannerScan_4',
#                                         'ParticleScannerScan_5', 'ParticleScannerScan_6',
#                                         'ParticleScannerScan_7', 'ParticleScannerScan_8',
#                                         'ParticleScannerScan_9'], np_size = 80, plot = False,
#                                               rejected = r'C:\Users\il322\Desktop\Offline Data\2023-03-31_Co-TAPP-SME_80nm_DF_Rejected.txt')
    
# Ni_80nm_wln_c = track_to_critical_wlns_manual(h5_80nm, ['ParticleScannerScan_10', 'ParticleScannerScan_11'],
#                                         np_size = 80, plot = False,
#                                         rejected = r'C:\Users\il322\Desktop\Offline Data\2023-03-31_Ni-TAPP-SME_80nm_DF_Rejected.txt')

# H2_60nm_wln_c = track_to_critical_wlns_manual(h5_60nm, ['ParticleScannerScan_2'], np_size = 60, plot = False,
#                                               rejected = r'C:\Users\il322\Desktop\Offline Data\2023-03-25_H2-TAPP-SME_60nm_DF_Rejected.txt')
   
# Co_60nm_wln_c = track_to_critical_wlns_manual(h5_60nm,['ParticleScannerScan_3'], np_size = 60, plot = False,
#                                               rejected = r'C:\Users\il322\Desktop\Offline Data\2023-03-25_Co-TAPP-SME_60nm_DF_Rejected.txt')
   
# Ni_60nm_wln_c = track_to_critical_wlns_manual(h5_60nm, ['ParticleScannerScan_4'], np_size = 60, plot = False,
#                                               rejected = r'C:\Users\il322\Desktop\Offline Data\2023-03-25_Ni-TAPP-SME_60nm_DF_Rejected.txt')
    
# Zn_60nm_wln_c = track_to_critical_wlns_manual(h5_60nm, ['ParticleScannerScan_5'], np_size = 60, plot = False,
#                                               rejected = r'C:\Users\il322\Desktop\Offline Data\2023-03-25_Zn-TAPP-SME_60nm_DF_Rejected.txt')

#%%

#Plot histogram

fig,ax=plt.subplots(4,2,figsize=[14,20], dpi=1000) 
ax1 = ax[0,1]
ax2 = ax[1,1]
ax3 = ax[2,1]
ax4 = ax[3,1]

bx1 = ax[0,0]
bx2 = ax[1,0]
bx3 = ax[2,0]
bx4 = ax[3,0]

fig.suptitle('DF $\lambda_c$ Frequency Distribution', fontsize='x-large',x=0.5, y=0.92)#, labelpad=0)


#ax1.set_xlabel('Wavelength (nm)', size='medium')
#ax1.set_ylabel('H2-TAPP-SMe\n'+'$\lambda_c$ Frequency', size= 'medium')
ax1.set_title('80nm NPoM')
num_bins = 30
hist, bin_edges = np.histogram(H2_80nm_wln_c, bins=num_bins, range=(550,850))
my_cmap = plt.get_cmap("hsv")
colors = (-1*bin_edges/900) + 1
colors = colors - 2.5*min(colors)
colors = colors * (0.9/max(colors))
ax1.bar(bin_edges[:-1], hist, width = ((max(bin_edges)-min(bin_edges))/num_bins), color=my_cmap(colors))
#ax1.xlim(min(bin_edges), max(bin_edges))
#plt.show() 


#ax2.set_xlabel('Wavelength (nm)', size='medium')
#ax2.set_ylabel('Co-TAPP-SMe\n'+'$\lambda_c$ Frequency', size= 'medium')
#ax2.set_title('Co-TAPP-SMe 80nm NPoM')
num_bins = 30
hist, bin_edges = np.histogram(Co_80nm_wln_c, bins=num_bins, range=(550,850))
my_cmap = plt.get_cmap("hsv")
colors = (-1*bin_edges/900) + 1
colors = colors - 2.5*min(colors)
colors = colors * (0.9/max(colors))
ax2.bar(bin_edges[:-1], hist, width = ((max(bin_edges)-min(bin_edges))/num_bins), color=my_cmap(colors))

#ax3.set_xlabel('$\lambda_c$ (nm)', size='medium')
#ax3.set_ylabel('Ni-TAPP-SMe\n'+'$\lambda_c$ Frequency', size= 'medium')
#ax3.set_title('Ni-TAPP-SMe 80nm NPoM')
num_bins = 30
hist, bin_edges = np.histogram(Ni_80nm_wln_c, bins=num_bins, range=(550,850))
my_cmap = plt.get_cmap("hsv")
colors = (-1*bin_edges/900) + 1
colors = colors - 2.5*min(colors)
colors = colors * (0.9/max(colors))
ax3.bar(bin_edges[:-1], hist, width = ((max(bin_edges)-min(bin_edges))/num_bins), color=my_cmap(colors))

ax4.set_xlabel('$\lambda_c$ (nm)', size='medium')
#ax4.set_ylabel('Zn-TAPP-SMe\n'+'$\lambda_c$ Frequency', size= 'medium')


#bx1.set_xlabel('Wavelength (nm)', size='medium')
bx1.set_ylabel('H2-TAPP-SMe\n'+'$\lambda_c$ Frequency', size= 'medium')
bx1.set_title('60nm NPoM')
num_bins = 50
hist, bin_edges = np.histogram(H2_60nm_wln_c, bins=num_bins, range=(550,850))
my_cmap = plt.get_cmap("hsv")
colors = (-1*bin_edges/900) + 1
colors = colors - 2.5*min(colors)
colors = colors * (0.9/max(colors))
bx1.bar(bin_edges[:-1], hist, width = ((max(bin_edges)-min(bin_edges))/num_bins), color=my_cmap(colors))
#bx1.xlim(min(bin_edges), max(bin_edges))
#plt.show() 


#bx2.set_xlabel('Wavelength (nm)', size='medium')
bx2.set_ylabel('Co-TAPP-SMe\n'+'$\lambda_c$ Frequency', size= 'medium')
#bx2.set_title('Co-TAPP-SMe 80nm NPoM')
num_bins = 50
hist, bin_edges = np.histogram(Co_60nm_wln_c, bins=num_bins, range=(550,850))
my_cmap = plt.get_cmap("hsv")
colors = (-1*bin_edges/900) + 1
colors = colors - 2.5*min(colors)
colors = colors * (0.9/max(colors))
bx2.bar(bin_edges[:-1], hist, width = ((max(bin_edges)-min(bin_edges))/num_bins), color=my_cmap(colors))

#bx3.set_xlabel('$\lambda_c$ (nm)', size='medium')
bx3.set_ylabel('Ni-TAPP-SMe\n'+'$\lambda_c$ Frequency', size= 'medium')
#bx3.set_title('Ni-TAPP-SMe 80nm NPoM')
num_bins = 50
hist, bin_edges = np.histogram(Ni_60nm_wln_c, bins=num_bins, range=(550,850))
my_cmap = plt.get_cmap("hsv")
colors = (-1*bin_edges/900) + 1
colors = colors - 2.5*min(colors)
colors = colors * (0.9/max(colors))
bx3.bar(bin_edges[:-1], hist, width = ((max(bin_edges)-min(bin_edges))/num_bins), color=my_cmap(colors))

bx4.set_xlabel('$\lambda_c$ (nm)', size='medium')
bx4.set_ylabel('ZN-TAPP-SMe\n'+'$\lambda_c$ Frequency', size= 'medium')
#bx3.set_title('Ni-TAPP-SMe 80nm NPoM')
num_bins = 50
hist, bin_edges = np.histogram(Zn_60nm_wln_c, bins=num_bins, range=(550,850))
my_cmap = plt.get_cmap("hsv")
colors = (-1*bin_edges/900) + 1
colors = colors - 2.5*min(colors)
colors = colors * (0.9/max(colors))
bx4.bar(bin_edges[:-1], hist, width = ((max(bin_edges)-min(bin_edges))/num_bins), color=my_cmap(colors))


#%% testing
fig,(ax1, ax2) =plt.subplots(2,1,figsize=[10,14], dpi=1000, sharex=True) 

ax1.set_title('Co-TAPP-SMe 80nm NPoM')
ax1.set_ylabel('Frequency')
num_bins = 30
hist, bin_edges = np.histogram(Co_new_wln_c[0], bins=num_bins, range=(550,850))
my_cmap = plt.get_cmap("hsv")
colors = (-1*bin_edges/900) + 1
colors = colors - 2.5*min(colors)
colors = colors * (0.9/max(colors))
ax1.bar(bin_edges[:-1], hist, width = ((max(bin_edges)-min(bin_edges))/num_bins), color=my_cmap(colors))

ax2.set_title('H2-TAPP-SMe 80nm NPoM')
ax2.set_ylabel('Frequency')
ax2.set_xlabel('Wavelength (nm)')
num_bins = 30
hist, bin_edges = np.histogram(H2_new_wln_c[0], bins=num_bins, range=(550,850))
my_cmap = plt.get_cmap("hsv")
colors = (-1*bin_edges/900) + 1
colors = colors - 2.5*min(colors)
colors = colors * (0.9/max(colors))
ax2.bar(bin_edges[:-1], hist, width = ((max(bin_edges)-min(bin_edges))/num_bins), color=my_cmap(colors))