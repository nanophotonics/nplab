# -*- coding: utf-8 -*-
"""
Auto-aligning spectrometer: centres in on a nanoparticle after a short scan
"""
from __future__ import division
from __future__ import print_function
#import traits
#from traits.api import HasTraits, Property, Instance, Float, Range, Array, Int, String, Button, Bool, on_trait_change
##import traitsui
#from traitsui.api import View, Item, HGroup, VGroup, Tabbed
#from traitsui.table_column import ObjectColumn
#import chaco
#from chaco.api import ArrayPlotData, Plot
#from enable.component_editor import ComponentEditor
from builtins import range
from past.utils import old_div
import threading
import numpy as np
import nplab.instrument.spectrometer
import nplab.instrument.stage
from nplab.instrument import Instrument
from nplab.utils.array_with_attrs import ArrayWithAttrs
import time
#from nplab.utils.traitsui_mpl_qt import MPLFigureEditor
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import scipy.optimize
#from scipy.odr import odrpack as odr

class SpectrometerAligner(Instrument):
#    spectrum_mask=None #a mask to set which pixels to align to
#    align_to_raw_spectra=False
#    spectrometer=None
#    stage=None
#    settling_time=Float(0.3)
#    step_size=Range(0.01,100.,0.5)
#    tolerance=Range(0.01,10.,0.05)
#    number_of_points = Range(2,20,5)
#    do_circle_iteration = Button()
#    do_focus_iteration = Button()
#    do_XY_optimisation = Button()
#    figure = Instance(Figure, ())
#    last_alignment_positions = Array(shape=(3,None),dtype=np.float)
#    last_alignment_powers = Array(shape=(None,),dtype=np.float)
#    
#    traits_view = View(
#                    Tabbed(
#                        VGroup(
#                            Item(name="settling_time"),
#                            Item(name="step_size"),
#                            HGroup(
#                                Item(name="do_circle_iteration",show_label=False),
#                                Item(name="do_focus_iteration",show_label=False),
#                            ),
#                            Item(name="tolerance"),
#                            Item(name="do_XY_optimisation",show_label=False),
#                            label="Controls",
#                        ),
#                        Item('figure', editor=MPLFigureEditor(),
#                               show_label=False, label="Last Alignment"),
#                    ),
#                    resizable=True, title="Spectrometer Aligner",
#                )
    def __init__(self,spectrometer,stage):
        super(SpectrometerAligner,self).__init__()
        self.spectrometer = spectrometer
        self.stage = stage
        self.align_to_raw_spectra=False
        self.settling_time=0.3
        self.spectrum_mask = None
#        self.step_size=Range(0.01,100.,0.5)
#        self.tolerance=Range(0.01,10.,0.05)
#        self.number_of_points = Range(2,20,5)
#        self.figure = 
#        self.figure.add_subplot(111)
        self._action_lock=threading.RLock() #reentrant lock, so that it doesn't matter that both optimise, and iterate_points (which it calls) acquire the lock
#        self._plot_data = ArrayPlotData(xpos=[],ypos=[])
#        self.plot = Plot(self._plot_data)
#        self.plot.plot("xpos","ypos",type="scatter",color="red")
#        self.plot.plot(("across","middle"),color="yellow")
#        self.plot.plot(("middle","across"),color="yellow")
    def merit_function(self):
        """this is what we optimise"""
        spectrum = self.spectrometer.read_spectrum()
        if not self.align_to_raw_spectra and self.spectrometer.background.shape == spectrum.shape:
            spectrum -= self.spectrometer.background
        if self.spectrum_mask is None:
            return np.nansum(spectrum)
        else:
            return np.nansum(spectrum[self.spectrum_mask])
    def _do_circle_iteration_fired(self):
        threading.Thread(target=self.iterate_circle,
                         kwargs=dict(radius=self.step_size,npoints=self.number_of_points)).start()
    def iterate_circle(self,radius,npoints=3,print_move=True,**kwargs):
        """Move the stage in a circle, taking spectra.  Refine the position."""
        angles = [2*np.pi/float(npoints) * float(i) for i in range(npoints)]
        points = [np.array([np.cos(a),np.sin(a),0])*radius for a in angles]
        return self.iterate_on_points(points, include_here=True, print_move=print_move, **kwargs)
    def iterate_grid(self,stepsize,**kwargs):
        """Move the stage in a 9-point grid and then find the maximum."""
        points = [np.array([i,j,0])*stepsize for i in [-1,0,1] for j in [-1,0,1] if not (i==0 and j==0)]
        return self.iterate_on_points(points, include_here=True, fit_method="maximum", **kwargs)
    def _do_focus_iteration_fired(self):
        threading.Thread(target=self.iterate_z, args=[self.step_size]).start()
    def iterate_z(self,dz,print_move=True):
        """Move the stage up and down to optimise focus"""
        return self.iterate_on_points([np.array([0,0,z]) for z in [-dz,dz]],print_move=print_move)
    def iterate_on_points(self,points,include_here=True,print_move=True,plot_args={},fit_method="centroid"):
        """Visit the points supplied, and refine our position.
        
        The merit function will be evaluated at each point (given in stage
        units, relative to the current position) and then the stage moved to
        the centre of mass.  The minimum reading is subtracted to avoid
        negative values (which mess things up) and speed up convergence.
        
        include_here adds the present position as one of the points.  This can
        help stability if the points passed in are e.g. a circle."""
        #NB we're not bothering with sample coordinates here...
        self._action_lock.acquire()
        here = np.array(self.stage.position)
        positions = [here]
        powers = [self.merit_function()]
        for p in points: #iterate through the points and measure the merit function
            self.stage.move(here+p)
            time.sleep(self.settling_time)
            positions.append(self.stage.position)
            powers.append(self.merit_function())
        if fit_method=="parabola": #parabolic fit: fit a 2D parabola to the data.  More responsive but less stable than centre of mass.
            try:
                pos = np.array(positions) - np.mean(positions,axis=0)
                powers = np.array(powers)
                mean_position = np.mean(pos, axis=0) #default to no motion, (as the polyfit will fail if there's no motion in one axis) ??should this be positions (measured) or points (specified)?
                axes_with_motion = np.where(np.std(np.array(points),axis=0)>0)[0] #don't try to fit axes where there's no motion (nb the [0] is necessary because the return value from np.where is a tuple)
                #model: power = a +b.x + c.<crossterms>
                N = len(axes_with_motion) #number of axes
                quadratic = np.ones((powers.shape[0], 2*N + 1))
                for i, a in enumerate(axes_with_motion):
                    quadratic[:,i+1] = pos[:,a] #put linear terms in the matrix
                for i, a in enumerate(axes_with_motion):
                    quadratic[:,i+1+N] = pos[:,a] #put quadratic terms in the matrix (ignore cross terms for now...)
                p = np.linalg.lstsq(quadratic, powers)[0] #use least squares to fast-fit a 2D parabola
                print("quadratic fit: ", p)
                for i, a in enumerate(axes_with_motion):
                    if p[i+1+N] > 0:
                        mean_position[a] = np.Inf * p[i+1] #if the parabola is happy/flat, assume we are moving the maximum step
                        print("warning: there is no maximum on axis %d" % a)
                    else:
                        mean_position[a] = old_div(-p[i+1],(2*p[i+N+1])) #if there's a maximum in the fitted curve, assume that's where we should be
                        print("axis %d has a maximum at %.2f" % (a, mean_position[a]))
                for i in range(mean_position.shape[0]):
                    if mean_position[i] > old_div(np.max(pos[:,i]),2): mean_position[i] = old_div(np.max(pos[:,i]),2) #constrain to lie within the positions supplied
                    if mean_position[i] < old_div(np.min(pos[:,i]),2): mean_position[i] = old_div(np.min(pos[:,i]),2) #so we don't move too far
                mean_position += np.mean(positions,axis=0)
            except:
                print("Quadratic fit failed, falling back to centroid.")
                fit_method="centroid"
        if fit_method=="gaussian":
            try:
                pos = np.array(positions)
                powers = np.array(powers)
                mean_position = np.mean(pos, axis=0) #default to no motion, (as the polyfit will fail if there's no motion in one axis) ??should this be positions (measured) or points (specified)?
                axes_with_motion = np.where(np.std(np.array(points),axis=0)>0)[0] #don't try to fit axes where there's no motion (nb the [0] is necessary because the return value from np.where is a tuple)
                N = len(axes_with_motion)
                def error_from_gaussian(p):
                    gaussian = p[0] + p[1] * np.exp(-np.sum(old_div((pos-p[2:2+N])**2,(2*p[2+N:2+2*N]**2)),axis=1))
                    return np.mean((powers-gaussian)**2)
                ret = scipy.optimize.minimize(error_from_gaussian, [0,np.max(powers)]+list(mean_position)+list(np.ones(N)*0.3))
                print(ret)
                assert ret.success
                for i, a in enumerate(axes_with_motion):
                    mean_position[a] = ret.x[i+2]
            except:
                print("Gaussian fit failed, falling back to centroid.")
                fit_method="centroid"
        if fit_method=="centroid":
            powers = np.array(powers) - np.min(powers)*1.1+np.max(powers)*0.1 #make sure no powers are <0
            mean_position = old_div(np.dot(powers, positions),np.sum(powers))
        if fit_method=="maximum":           #go to the brightest point
            powers = np.array(powers)
            mean_position = np.array(positions)[powers.argmax(),:]
                    
        if print_move:
            print("moving %.3f, %.3f, %.3f" % tuple(mean_position - here))
        try:
            self.stage.move(mean_position)
        except:
            print("Positions:\n",positions)
            print("Powers: ",powers)
            print("Mean Position: ",mean_position)
        self._action_lock.release()
        self.plot_alignment(positions, powers, mean_position, **plot_args)
        return positions, powers, mean_position
    def optimise(self,tolerance, max_steps=10, stepsize=0.5, npoints=3, dz=0.5,verbose=False):
        """Repeatedly move and take spectra to find the peak.
        
        
        WARNING: it seems a bit unstable at the moment, best consider this 
        "experimental" code! The focus has a tendency to wander!
        
        Each iteration, we perform iterate_circle(stepsize, npoints) then
        iterate_z(dz).  The algorithm stops when the distance moved is less
        than tolerance.  If tolerance is a 3-element numpy array, then a
        different tolerance is applied to x, y, z: [1,1,1] is equivalent to a 
        tolerance of 1, as the comparison is sum(dx**2/tolerance**2) < 1.0
        """
        self._action_lock.acquire()
        positions = [np.array(self.stage.position)]
        powers = [self.merit_function()]
        for i in range(max_steps):
            pos = self.iterate_circle(stepsize,npoints, print_move=verbose)[2]
            pos = self.iterate_z(dz, print_move=verbose)[2]
            positions.append(pos)
            powers.append(self.merit_function())
            if np.sum(old_div((positions[-1] - positions[-2])**2, tolerance**2)) <= 1.0:
                break
            else:
                time.sleep(self.settling_time)
        if verbose: print("performed %d iterations" % (len(positions)-1))
        self._action_lock.release()
        self.plot_alignment(positions, powers, [np.NaN,np.NaN])
        return positions, powers
    def _do_XY_optimisation_fired(self):
        threading.Thread(target=self.optimise_2D,args=[self.tolerance], kwargs=dict(stepsize=self.step_size, npoints = self.number_of_points)).start()
    def optimise_2D(self, tolerance=0.03, max_steps=10, stepsize=0.2, npoints=3, print_move=True,reduce_integration_time = True):
        """repeatedly move and take spectra to find the peak
        
        we run iterate_circle until the movement produced is small enough."""
        if reduce_integration_time == True:
            start_expo =self.spectrometer.integration_time
            self.spectrometer.integration_time = start_expo/3.0
        self._action_lock.acquire()
        positions = [np.array(self.stage.position)]
        powers = [self.merit_function()]
        for i in range(max_steps):
            #pos = self.iterate_circle(stepsize,npoints,print_move,plot_args={'color':"blue",'cla':(i==0)})[2]
            pos = self.iterate_grid(stepsize,print_move=print_move,plot_args={'color':"blue",'cla':(i==0)})[2]
            positions.append(pos)
            powers.append(self.merit_function())
            if np.sqrt(np.sum((positions[-1] - positions[-2])**2)) < tolerance:
                break
        print("performed %d iterations" % (len(positions)-1))
        self._action_lock.release()
        self.plot_alignment(positions, powers, [np.NaN,np.NaN], cla=False, fade=False, color="green")
        if reduce_integration_time == True:
            self.spectrometer.integration_time = start_expo
        return positions, powers
    def z_scan(self, dz = np.arange(-4,4,0.4)):
        """Take spectra at (relative) z positions dz and return as a 2D array"""
        spectra = []
        here = self.stage.position
        for z in dz:
            self.stage.move(np.array([0,0,z])+here)
            time.sleep(self.settling_time)
            spectra.append(self.spectrometer.read_spectrum())
        self.stage.move(here)
        return ArrayWithAttrs(spectra, attrs=self.spectrometer.metadata)
    def plot_alignment(self,positions, powers, mean_position, cla=True, fade=True, **kwargs):
        """plot an alignment so we can see how it went"""
        pass
#        x = [p[0] for p in positions]
#        y = [p[1] for p in positions]
#        powers = np.array(powers)
#        s = powers/powers.max() * 200
#        ax = self.figure.axes[0]
#        if cla:
#            ax.cla()
#        elif fade: #fade out existing plots
#            for c in ax.collections:
#                c.set_color(tuple(np.array(c.get_facecolor())*0.5+np.array([1,1,1,1])*0.5))
#        ax.scatter(x,y,s=s,**kwargs)
#        ax.plot([mean_position[0]],[mean_position[1]], 'r+')         
#        canvas = self.figure.canvas
#        if canvas is not None:
#            canvas.draw()
            
def fit_parabola(positions, powers, *args):
    positions = np.array(positions)
    powers = np.array(powers)
    mean_position = np.mean(positions,axis=0) #default to no motion, (as the polyfit will fail if there's no motion in one axis) ??should this be positions (measured) or points (specified)?
    axes_with_motion = np.where(np.std(positions,axis=0)>0)[0] #don't try to fit axes where there's no motion (nb the [0] is necessary because the return value from np.where is a tuple)
    #model: power = a +b.x + c.<crossterms>
    N = len(axes_with_motion) #number of axes
    quadratic = np.ones((powers.shape[0], 2*N + 1))
    for i, a in enumerate(axes_with_motion):
        quadratic[:,i+1] = positions[:,a] #put linear terms in the matrix
    for i, a in enumerate(axes_with_motion):
        quadratic[:,i+1+N] = positions[:,a] #put quadratic terms in the matrix (ignore cross terms for now...)
    p = np.linalg.lstsq(quadratic, powers)[0] #use least squares to fast-fit a 2D parabola
    for i, a in enumerate(axes_with_motion):
        if p[i+1+N] > 0:
            mean_position[a] = np.Inf * p[i+1] #if the parabola is happy/flat, assume we are moving the maximum step
        else:
            mean_position[a] = old_div(-p[i+1],(2*p[i+N+1])) #if there's a maximum in the fitted curve, assume that's where we should be
    for i in range(mean_position.shape[0]):
        if mean_position[i] > np.max(positions[:,i]): mean_position[i] = np.max(positions[:,i]) #constrain to lie within the positions supplied
        if mean_position[i] < np.min(positions[:,i]): mean_position[i] = np.min(positions[:,i]) #so we don't move too far
    return mean_position - np.mean(positions,axis=0)      
        
def plot_alignment(positions, powers, mean_position):
    x = [p[0] for p in positions]
    y = [p[1] for p in positions]
    powers = np.array(powers)
    s = old_div(powers,powers.max()) * 20
    plt.scatter(x,y,s=s)
    plt.plot([mean_position[0]],[mean_position[1]], 'r+')
    plt.show(block=False)
    
if __name__ == "__main__":
    import nplab.instrument.spectrometer.seabreeze as seabreeze
    seabreeze.shutdown_seabreeze() #just in case...
    import nplab.instrument.stage.prior as prior_stage
    stage = prior_stage.ProScan("COM3")
    spectrometer = seabreeze.OceanOpticsSpectrometer(0)
    aligner = SpectrometerAligner(spectrometer,stage)
    spectrometer.edit_traits()
    aligner.edit_traits()
