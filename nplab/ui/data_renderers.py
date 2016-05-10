__author__ = 'alansanders'

import h5py
from nplab.utils.gui import *
from nplab.utils.array_with_attrs import ArrayWithAttrs
from PyQt4 import uic
import matplotlib

matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pyqtgraph as pg
import numpy as np




# -*- coding: utf-8 -*-
"""
Created on Thu Oct 29 10:36:07 2015

@author: wmd22
"""




class DataRenderer(object):
    def __init__(self, h5object, parent=None):
    #    assert self.is_suitable(h5object) >= 0, "Can't render that object: {0}".format(h5object)
        super(DataRenderer, self).__init__()
        self.parent = parent
        self.h5object = h5object

    @classmethod
    def is_suitable(cls, h5object):
        """Return a score of how well suited this renderer is to the object.
        
        This should be a quick function, as it's called often (every renderer
        gives a score each time we look for a suitable renderer).  Return a
        number < 0 if you can't render the data.
        """
        return -1

renderers = set()

def add_renderer(renderer_class):
    """Add a renderer to the list of available renderers"""
    renderers.add(renderer_class)
    
def suitable_renderers(h5object, return_scores=False):
    """Find renderers that can render a given object, in order of suitability.
    """
    renderers_and_scores = [(r.is_suitable(h5object), r) for r in renderers]
    renderers_and_scores.sort(key=lambda (score, r): score, reverse=True)
    if return_scores:
        return [(score, r) for score, r in renderers_and_scores if score >= 0]
    else:
        return [r for score, r in renderers_and_scores if score >= 0]

hdf5_info_base, hdf5_info_widget = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'hdf5_info_renderer.ui'))


class HDF5InfoRenderer(DataRenderer, hdf5_info_base, hdf5_info_widget):
    """ A renderer returning the basic HDF5 info"""
    def __init__(self, h5object, parent=None):
        super(HDF5InfoRenderer, self).__init__(h5object, parent)
        self.parent = parent
        self.h5object = h5object

        self.setupUi(self)
        if type(h5object)==list:
            self.lineEdit.setText(h5object[0].name)
            self.lineEdit2.setText(h5object[0].parent.name)
        else:
            self.lineEdit.setText(h5object.name)
            self.lineEdit2.setText(h5object.parent.name)
        

    @classmethod
    def is_suitable(cls, h5object):
        return 2

add_renderer(HDF5InfoRenderer)

class TextRenderer(DataRenderer, QtGui.QWidget):
    """A renderer returning the objects name type and shape if a dataset object"""
    def __init__(self, h5object, parent=None):
        super(TextRenderer, self).__init__(h5object, parent)
        
        #our layout is simple - just a single QLabel
        self.label = QtGui.QLabel()
        layout = QtGui.QVBoxLayout(self)
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        self.label.setText(self.text(h5object))
        
    def text(self, h5object):
        """Return the text that is displayed in the label"""
        return str(h5object)

    @classmethod
    def is_suitable(cls, h5object):
        return 0

add_renderer(TextRenderer)


class AttrsRenderer(TextRenderer):
    """ A renderer displaying the Attributes of the HDF5 object selected"""
    def text(self, h5object):
        text = "Attributes:\n"
        for key, value in h5object.attrs.iteritems():
            text += "{0}: {1}\n".format(key, str(value))
        return text
        
    @classmethod
    def is_suitable(cls, h5object):
        return 1
add_renderer(AttrsRenderer)

class FigureRenderer(DataRenderer, QtGui.QWidget):
    """A renderer class which sets up a matplotlib figure for use 
    in more complicated renderers
    """
    def __init__(self, h5object, parent=None):
        super(FigureRenderer, self).__init__(h5object, parent)
        self.fig = Figure()

        layout = QtGui.QVBoxLayout(self)
        self.figureWidget = FigureCanvas(self.fig)
        layout.addWidget(self.figureWidget)
        self.setLayout(layout)

        self.display_data()

    def display_data(self):
        self.fig.canvas.draw()

class FigureRendererPG(DataRenderer, QtGui.QWidget):
    """A renderer class which sets up a pyqtgraph for use 
    in more complicated renderers
    """
    def __init__(self, h5object, parent=None):
        super(FigureRendererPG, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.figureWidget =  pg.PlotWidget(name='Plot1') 
        self.layout = QtGui.QVBoxLayout(self)
        self.layout.addWidget(self.figureWidget)
        self.setLayout(self.layout)

        self.display_data()

    def display_data(self):
        self.fig.canvas.draw()
#        
#        
class DataRenderer1DPG(FigureRendererPG):
    """ A renderer for 1D datasets experessing them in a line graph using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region or performing transformations of the axis
    """
    def display_data(self):
       # plot = self.figureWidget.plot()
        if type(self.h5object)!= list:
            self.h5object = [self.h5object]
        icolour = 0    
        self.figureWidget.addLegend(offset = (-1,1))
        for h5object in self.h5object:
            try:
                if np.shape(h5object)[0] == 2 or np.shape(h5object)[1] == 2:
                    Xdata = np.array(h5object)[0]
                    Ydata = np.array(h5object)[1]
                else:
                    Ydata = np.array(h5object)
                    Xdata = np.arange(len(Ydata))
            except IndexError:
                Ydata = np.array(h5object)
                Xdata = np.arange(len(Ydata))
            self.figureWidget.plot(x = Xdata, y = Ydata,name = h5object.name, pen =(icolour,len(self.h5object)))
            icolour = icolour + 1
            
        try:
            self.figureWidget.setLabel('bottom', h5object.attrs['X label'])
        except:
            self.figureWidget.setLabel('bottom', 'An X axis')
            
        try:
            self.figureWidget.setLabel('left', h5object.attrs['Y label'])
        except:
            self.figureWidget.setLabel('left', 'An X axis')

        
   
    @classmethod
    def is_suitable(cls, h5object):
        if type(h5object) == list:
            h5object = h5object[0]
        if not isinstance(h5object, h5py.Dataset):
            return -1
        if len(h5object.shape) == 1:
            return 11
        elif np.shape(h5object)[0] == 2 or np.shape(h5object)[1] == 2:
            return 12           

        elif len(h5object.shape) > 1:
            return -1
#            
add_renderer(DataRenderer1DPG)

class Scatter_plot1DPG(FigureRendererPG):
    """ A renderer for 1D datasets experessing them in a scatter graph using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region or performing transformations of the axis
    """

    def display_data(self):
       # plot = self.figureWidget.plot()
        if type(self.h5object)!= list:
            self.h5object = [self.h5object]
        icolour = 0    
        self.figureWidget.addLegend(offset = (-1,1))
        for h5object in self.h5object:
            try:
                if np.shape(h5object)[0] == 2 or np.shape(h5object)[1] == 2:
                    Xdata = np.array(h5object)[0]
                    Ydata = np.array(h5object)[1]
                else:
                    Ydata = np.array(h5object)
                    Xdata = np.arange(len(Ydata))
            except IndexError:
                Ydata = np.array(h5object)
                Xdata = np.arange(len(Ydata))
            self.figureWidget.plot(x = Xdata, y = Ydata,name = h5object.name, pen =None, symbol ='o',symbolPen = (icolour,len(self.h5object)),symbolBrush = (icolour,len(self.h5object)))
            icolour = icolour + 1
            
        try:
            self.figureWidget.setLabel('bottom', h5object.attrs['X label'])
        except:
            self.figureWidget.setLabel('bottom', 'An X axis')
            
        try:
            self.figureWidget.setLabel('left', h5object.attrs['Y label'])
        except:
            self.figureWidget.setLabel('left', 'An X axis')
          
    @classmethod
    def is_suitable(cls, h5object):
        if type(h5object) == list:
            h5object = h5object[0]
        if not isinstance(h5object, h5py.Dataset):
            return -1
        if len(h5object.shape) == 1:
            return 11
        elif np.shape(h5object)[0] == 2 or np.shape(h5object)[1] == 2:
            return 12           

        elif len(h5object.shape) > 1:
            return -1
#            
add_renderer(Scatter_plot1DPG)

class DataRenderer2DPG(DataRenderer, QtGui.QWidget):
    """ A renderer for 2D datasets images experessing them in a colour map using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region and changing the colour scheme through the use of a histogramLUT 
    widget on the right of the image.
    """
    def __init__(self, h5object, parent=None):
        super(DataRenderer2DPG, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.layout = QtGui.QGridLayout()
        self.setLayout(self.layout)
        self.layout.setSpacing(0)

        self.display_data()

    def display_data(self):
        v = pg.GraphicsView()
        vb = pg.ViewBox()

        v.setCentralItem(vb)
        self.layout.addWidget(v, 0, 0)
    
        w = pg.HistogramLUTWidget()
        self.layout.addWidget(w, 0, 1)
        if type(self.h5object)==list:
            for i in range(len(self.h5object)):
                if i == 0:    
                    data = [np.array(self.h5object[i])]
                else:
                    data = np.append(data,[np.array(self.h5object[i])],axis = 0)
        else:
            data = np.array(self.h5object)
     #       vb.setAspectLocked()
        data = np.transpose(data)
        data[np.where(np.isnan(data))] = 0        
        img = pg.ImageItem(data)
        vb.addItem(img)
        vb.autoRange()

        w.setImageItem(img)


   
    @classmethod
    def is_suitable(cls, h5object):
        if type(h5object)==list:
            for i in h5object:
                if not isinstance(i, h5py.Dataset):
                    return -1
                if len(i.shape) != 1:
                    return -1
            return -1
        elif not isinstance(h5object, h5py.Dataset):
            return -1
        else:
            if len(h5object.shape) == 2:
                return 11
            elif len(h5object.shape) > 2:
                return -1

add_renderer(DataRenderer2DPG)

class DataRenderer2DRBGPG(DataRenderer, QtGui.QWidget):
    """ A renderer for 2D pictures/RGB images experessing them in a colour map using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region and changing the colour scheme through the use of a histogramLUT 
    widget on the right of the image.
    """
    def __init__(self, h5object, parent=None):
        super(DataRenderer2DRBGPG, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.layout = QtGui.QGridLayout()
        self.setLayout(self.layout)
        self.layout.setSpacing(0)

        self.display_data()

    def display_data(self):
        v = pg.GraphicsView()
        vb = pg.ViewBox()
        vb.setAspectLocked()
        v.setCentralItem(vb)
        self.layout.addWidget(v, 0, 0)
        img = pg.ImageItem(np.array(self.h5object))
        vb.addItem(img)
        vb.autoRange()



   
    @classmethod
    def is_suitable(cls, h5object):
        if not isinstance(h5object, h5py.Dataset):
            return -1
        if len(h5object.shape) == 3 and h5object.shape[2]==3:
            return 50
        elif len(h5object.shape) > 2:
            return -1

add_renderer(DataRenderer2DRBGPG)


class MultiSpectrum2D(DataRenderer, QtGui.QWidget):
    """ A renderer for large spectral datasets experessing them in a colour map using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region and changing the colour scheme through the use of a histogramLUT 
    widget on the right of the image.
    
    If a background and/or reference are within the attributes for the datafile 
    they will also be applied. If this is the case it will be expressed in the 
    title of the colourmap.
    
    This renderer is also avaible for users attempting to look at multiple spectra 
    in seperate datasets at the same time through selection while pressing
    control/shift as used in most windows apps.
    """
    def __init__(self, h5object, parent=None):
        super(MultiSpectrum2D, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.layout = QtGui.QGridLayout()
        self.setLayout(self.layout)
        self.layout.setSpacing(0)

        self.display_data()

    def display_data(self):
        v = pg.GraphicsView()
        vb = pg.PlotItem()
        v.setCentralItem(vb)
        self.layout.addWidget(v, 0, 0)
    
        w = pg.HistogramLUTWidget()
        self.layout.addWidget(w, 0, 1)
     #   

        
        
        if type(self.h5object)==list:
            for i in range(len(self.h5object)):
                if i == 0:    
                    data = [np.array(self.h5object[i])]
                else:
                    data = np.append(data,[np.array(self.h5object[i])],axis = 0)
                ListData = True
        elif len(self.h5object.shape) == 1 and len(self.h5object.attrs['wavelengths'])<len(self.h5object) and len(self.h5object)%len(self.h5object.attrs['wavelengths']) == 0:
            RawData = np.array(self.h5object)
            Xlen = len(np.array(self.h5object.attrs['wavelengths']))
            Ylen = len(RawData)/Xlen
            data = [RawData.reshape((Ylen,Xlen))]
            self.h5object = [self.h5object]
            ListData = False
        else:
            self.h5object = [self.h5object]
            data = np.array(self.h5object) 
            ListData = False
        
        background_counter = 0
        reference_counter = 0
        i = 0
        for h5object in data:
            Title = "A"
            
            if 'background' in self.h5object[i].attrs.keys():
                if ListData == True:
                    if len(np.array(data[i])) == len(np.array(self.h5object[i].attrs['reference'])):
                        data[i] = data[i] - np.array(self.h5object[i].attrs['background'])     
                else:
                    if len(np.array(data)) == len(np.array(self.h5object[i].attrs['background'])):
                            data = data - np.array(self.h5object[i].attrs['background'])[:,np.newaxis]       
                    Title = Title + " background subtracted"
            else:
                background_counter = background_counter+1
            if 'reference' in self.h5object[i].attrs.keys():
                if ListData == True:
                    if len(np.array(data[i])) == len(np.array(self.h5object[i].attrs['reference'])):
                        data[i] = data[i]/(np.array(self.h5object[i].attrs['reference'])- np.array(self.h5object[i].attrs['background']))   
                else:
                    if len(np.array(data)) == len(np.array(self.h5object[i].attrs['reference'])):
                        data = data/(np.array(self.h5object[i].attrs['reference'])[:,np.newaxis]- np.array(self.h5object[i].attrs['background'])[:,np.newaxis])
                Title = Title + " referenced"
            else:
                reference_counter = reference_counter +1
            i = i +1
            
        if ListData == False:
            data = data[0]            
        data = np.transpose(data)
        
            
        if reference_counter == 0 and background_counter == 0:
            print "All spectrum are referenced and background subtracted"
        else:
            print "Number of spectrum not referenced"+str(reference_counter)
            print "Number of spectrum not background subtracted"+str(background_counter)
        Title = Title + " spectrum"
         
        data[np.where(np.isnan(data))] = 0

      #  plot.plot(x = np.array(self.h5object.attrs['wavelengths']), y = np.array(h5object),name = h5object.name)
        labelStyle = {'font-size': '14pt'}
        vb.setLabel('left', 'Spectrum number',**labelStyle)
        vb.setLabel('bottom', 'Wavelength (nm)',**labelStyle)

        vb.setTitle(Title,**labelStyle)
        print np.shape(data)
        img = pg.ImageItem(data)

        
        ConvertionC= self.h5object[0].attrs['wavelengths'][0]
        ConvertionM = self.h5object[0].attrs['wavelengths'][1] - self.h5object[0].attrs['wavelengths'][0]
        
        print ConvertionC, ConvertionM
        img.translate(ConvertionC,0)
        img.scale(ConvertionM,1)
        vb.addItem(img)
        vb.autoRange(False)


        w.setImageItem(img)


   
    @classmethod
    def is_suitable(cls, h5object):
        suitability = 0
        if type(h5object) == list:
            setshape = np.shape(h5object[0])
            for listitem in h5object:
                if not isinstance(listitem, h5py.Dataset):
                    return -1
                if len(np.shape(listitem)) != 1 :
                    return -1
                if np.shape(listitem) != setshape: # only suitable for spectrum of equal size
                    return -1               
            if 'wavelengths' in h5object[0]:
                suitability = suitability + 9
                if 'background' in h5object[0]:
                    suitability = suitability + 9
                if 'reference' in h5object[0]:
                    suitability = suitability + 9
            return suitability 
        elif not isinstance(h5object, h5py.Dataset):
            return -1
        if 'wavelengths' in h5object.attrs.keys():
            if len(h5object.shape) == 1 and len(np.array(h5object.attrs['wavelengths']))<len(np.array(h5object)) and len(np.array(h5object))%len(np.array(h5object.attrs['wavelengths'])) == 0:          
                suitability = suitability + 30 
                return suitability
        else:
            return -1
        if len(h5object.shape) == 2 :
            suitability = suitability + 11
            if 'background' in h5object.attrs.keys():
                suitability = suitability + 10
            if 'reference' in h5object.attrs.keys():
                suitability = suitability + 10

        else:
            return -1
        return suitability

add_renderer(MultiSpectrum2D)

class DataRenderer3DPG(DataRenderer, QtGui.QWidget):
    """ A renderer for 2D datasets images experessing them in a colour map using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region and changing the colour scheme through the use of a histogramLUT 
    widget on the right of the image while also allowing the user to scroll through the
    frames that make the image 3-d dimensional.
    """
    def __init__(self, h5object, parent=None):
        super(DataRenderer3DPG, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.layout = QtGui.QVBoxLayout()
        self.setLayout(self.layout)
        

        self.display_data()

    def display_data(self):
        data = np.array(self.h5object)
        data[np.where(np.isnan(data))] = 0 
        img = pg.ImageView()
        img.setImage(data)
        img.setMinimumSize(950,750)
        img.view.setAspectLocked(False)
        self.layout.addWidget(img)
        self.setLayout(self.layout)

   
    @classmethod
    def is_suitable(cls, h5object):
        if not isinstance(h5object, h5py.Dataset):
            return -1
        if len(h5object.shape) == 3:
            return 11
        elif len(h5object.shape) > 3:
            return -1

add_renderer(DataRenderer3DPG)

 

   
class DataRenderer1D(FigureRenderer):
    """ A renderer for 1D datasets experessing them in a line graph using
    matplotlib. Allow this does not allow the user to interact with the
    figure it is often found to be more stable.
    """
    def display_data(self):
        ax = self.fig.add_subplot(111)
        ax.plot(self.h5object)
        ax.set_aspect("auto")
        ax.relim()
        ax.autoscale_view()
        self.fig.canvas.draw()

    @classmethod
    def is_suitable(cls, h5object):
        if not isinstance(h5object, h5py.Dataset):
            return -1
        if len(h5object.shape) == 1:
            return 10
        elif len(h5object.shape) > 1:
            return -1
            
add_renderer(DataRenderer1D)


class DataRenderer2D(FigureRenderer):
    """ A renderer for 2D datasets experessing them in a colourmap graph using
    matplotlib. Allow this does not allow the user to interact with the
    figure it is often found to be more stable.
    """
    def display_data(self):
        ax = self.fig.add_subplot(111)
        ax.imshow(self.h5object, aspect="auto", cmap="cubehelix")
        self.fig.canvas.draw()

    @classmethod
    def is_suitable(cls, h5object):
        if not isinstance(h5object, h5py.Dataset):
            return -1
        if len(h5object.shape) == 2:
            return 10
        elif len(h5object.shape) < 2:
            return -1
            
add_renderer(DataRenderer2D)


class DataRendererRGB(FigureRenderer):
    """ A renderer for RGB images/datasets experessing them in a colourmap graph using
    matplotlib. Allow this does not allow the user to interact with the
    figure it is often found to be more stable.
    """
    def display_data(self):
        ax = self.fig.add_subplot(111)
        ax.imshow(self.h5object)
        self.fig.canvas.draw()

    @classmethod
    def is_suitable(cls, h5object):
        if not isinstance(h5object, h5py.Dataset):
            return -1
        if len(h5object.shape) == 3 and h5object.shape[2]==3:
            return 15
        elif len(h5object.shape) != 3:
            return -1
            
add_renderer(DataRendererRGB)

class SpectrumRenderer(FigureRendererPG):
    """ A renderer for  spectral datasets experessing them in a line graph using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region or performing mathematical transfomations on the axis
    
    If a background and/or reference are within the attributes for the datafile 
    they will also be applied. If this is the case it will be expressed in the 
    title of the graph.
    
    This renderer is also avaible for users attempting to look at multiple spectra 
    in seperate datasets at the same time through selection while pressing
    control/shift as used in most windows apps.
    """
    def display_data(self):
        if type(self.h5object)==list:
            print "Merging multiple datasets"
        elif len(self.h5object.shape)==2:
            h5list = []
            for line in range(len(self.h5object[:,0])):
                ldata = np.array(self.h5object)[line]
                linedata = ArrayWithAttrs(ldata,attrs = self.h5object.attrs)
                linedata.name = self.h5object.name+"_"+str(line)
                h5list.append(linedata)
            self.h5object = h5list
        elif type(self.h5object)!=list:
            self.h5object = [self.h5object]
        plot = self.figureWidget
        plot.addLegend(offset = (-1,1))
        icolour = 0
        for h5object in self.h5object:
            icolour = icolour+1
            Data = np.array(h5object)
            Title = "A"
            if 'background' in h5object.attrs.keys():
                if len(np.array(h5object)) == len(np.array(h5object.attrs['background'])):
                    Data = Data - np.array(h5object.attrs['background'])
                    Title = Title + " background subtracted"
                if 'reference' in h5object.attrs.keys():
                    if len(np.array(h5object)) == len(np.array(h5object.attrs['reference'])):
                        Data = Data/(np.array(h5object.attrs['reference'])- np.array(h5object.attrs['background']))
                        Title = Title + " referenced"
    
            plot.plot(x = np.array(h5object.attrs['wavelengths']), y = np.array(Data),name = h5object.name, pen =(icolour,len(self.h5object)) )
            Title = Title + " spectrum"
                
            labelStyle = {'font-size': '14pt'}
            self.figureWidget.setLabel('left', 'Intensity',**labelStyle)
            self.figureWidget.setLabel('bottom', 'Wavelength (nm)',**labelStyle)
            self.figureWidget.setTitle(Title,**labelStyle)
        
   
    @classmethod
    def is_suitable(cls, h5object):
        suitability = 0
        if type(h5object)==list:
            for i in h5object:
                if not isinstance(i, h5py.Dataset):
                    return -1
            h5object = h5object[0]
        elif not isinstance(h5object, h5py.Dataset):
            return -1
        if len(h5object.shape) == 1:
            suitability = suitability + 10
                
        if len(h5object.shape) > 2:
            return -1
  
        if 'wavelengths' in h5object.attrs.keys():#
            if len(h5object.shape) == 2:
                if len(np.array(h5object)[:,0])<20:
                    suitability = suitability + len(h5object)-20
                else:
                    return -1
            elif len(h5object.attrs['wavelengths']) != len(np.array(h5object)):
                print "the number of bins does not equal the number of wavelengths!"
                return -1
            suitability = suitability + 10
        else:
            return -1
         
        if 'background' in h5object.attrs.keys():
            suitability = suitability + 10
        if 'reference' in h5object.attrs.keys():
            suitability = suitability + 10                
        return suitability    
#            
add_renderer(SpectrumRenderer)    


class HyperSpec(DataRenderer, QtGui.QWidget):
    """ A renderer for large hyper spectral datasets experessing them in a colour map using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region and changing the colour scheme through the use of a histogramLUT 
    widget on the right of the image. A slider is also available to change the current
    wavelength shown in the image.
    
    X/y/z attributes will be used as axis on the plots if available.

    """
    def __init__(self, h5object, parent=None):
        super(HyperSpec, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.layout = QtGui.QGridLayout()
        self.setLayout(self.layout)
        self.display_data()

    def display_data(self):
        data = np.array(self.h5object)
        data[np.where(np.isnan(data))] = 0 
        
        dims = len(np.shape(data))
        
        Images = []
        midpoints = []
        
        for dim in range(dims-1):
            Images.append(pg.ImageView(view=pg.PlotItem()))
            midpoints.append(int(np.shape(data)[dim]/2))

     
        Imagedata = []
        
        Imagedata.append(np.transpose(data[:,:,midpoints[2],:]))
        Imagedata.append(np.transpose(data[:,midpoints[1],:,:]))
        Imagedata.append(np.transpose(data[midpoints[0],:,:,:]))
        
        XConvertionM = 1
        YConvertionM = 1        
        ZConvertionM = 1
        
        if len(self.h5object.attrs['x']) > 1:
           XConvertionM = self.h5object.attrs['x'][1] - self.h5object.attrs['x'][0]
        if len(self.h5object.attrs['y']) > 1:
            YConvertionM = self.h5object.attrs['y'][1] - self.h5object.attrs['y'][0]                    
        if len(self.h5object.attrs['z']) > 1:
            ZConvertionM = self.h5object.attrs['z'][1] - self.h5object.attrs['z'][0]
            
        convertionfactors = [[YConvertionM,XConvertionM],[ZConvertionM,XConvertionM],[ZConvertionM,YConvertionM]]
        
        labels = [["X","Y"],["X","Z"],["Y","Z"]]
                
        for imgNum in range(len(Imagedata)):
            if len(Imagedata[imgNum][0,0,:]) == 1:
                Imagedata[imgNum] = np.swapaxes(Imagedata[imgNum],1,2)
                con = convertionfactors[imgNum][1]
                convertionfactors[imgNum][1] = convertionfactors[imgNum][0]
                convertionfactors[imgNum][0] = con
                
                conlabel = labels[imgNum][0]
                labels[imgNum][0] = labels[imgNum][1]
                labels[imgNum][1] = conlabel

  
        
        for imgNom in range(len(Images)):
            Images[imgNom].setImage(Imagedata[imgNom],xvals = np.array(self.h5object.attrs['wavelengths']),autoHistogramRange = True)
      

        
 
       
    
        Images[0].getImageItem().scale(convertionfactors[0][0],convertionfactors[0][1])
       # XYimg.getImageItem().translate(YConvertionC,XConvertionC)
        
        Images[1].getImageItem().scale(convertionfactors[1][0],convertionfactors[1][1])
       # XZimg.getImageItem().translate(ZConvertionC,XConvertionC)
        
        Images[2].getImageItem().scale(convertionfactors[2][0], convertionfactors[2][1])
      #  YZimg.getImageItem().translate(ZConvertionC,YConvertionC)
        
        
               
        
   #     Images[0].getView().setTitle("X(Y)")
    #    Images[1].getView().setTitle("X(Z)")
     #   Images[2].getView().setTitle("Y(Z)")  

        for imgNom in range(len(Images)): 
            Images[imgNom].autoLevels()
            Images[imgNom].autoRange()
            Images[imgNom].ui.roiBtn.hide()
            Images[imgNom].ui.menuBtn.hide() 
            Images[imgNom].setMinimumSize(550,350)
            Images[imgNom].view.setAspectLocked(False)
            
            Images[imgNom].getView().setTitle(labels[imgNom][0]+"("+labels[imgNom][1]+")")
            Images[imgNom].getView().setLabel("left" , labels[imgNom][0])
            Images[imgNom].getView().setLabel("bottom" , labels[imgNom][1])
      
        self.layout.addWidget(Images[0],0,0)
        self.layout.addWidget(Images[1],0,1)
        self.layout.addWidget(Images[2],1,0)
        
        
        self.setLayout(self.layout)

   
    @classmethod
    def is_suitable(cls, h5object):
        if not isinstance(h5object, h5py.Dataset):
            return -1
        if len(h5object.shape) == 4 and 'z' in h5object.attrs.keys() and 'y' in h5object.attrs.keys() and 'x' in h5object.attrs.keys():
            return 30
        elif len(h5object.shape) > 4:
            return -1

add_renderer(HyperSpec)


class PumpProbeRaw(DataRenderer, QtGui.QWidget):
    ''' A renderer for Pump probe experiments, leaving the data un changed'''
    """ A renderer for 1D datasets experessing them in a line graph using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region or performing transformations of the axis
    """
    def __init__(self, h5object, parent=None):
        super(PumpProbeRaw, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.layout = QtGui.QGridLayout()
        self.setLayout(self.layout)
        self.display_data()
        
    def display_data(self):
       # plot = self.figureWidget.plot()
        if type(self.h5object)!= list:
            self.h5object = [self.h5object]
        icolour = 0    
        Plots = []
        axes ={0 : 'X',1 : 'Y', 2 : 'R'}
        
    #    self.Spinbox = QtGui.QSpinBox()
   #     self.Spinbox.setValue(stepperoffset)
     #   self.Spinbox.valueChanged.connect(self.change_in_stepperoffset())
        for axis in axes:
            Plots.append(pg.PlotWidget())
       
        for plot in Plots:
            plot.addLegend(offset = (-1,1))
        
        for h5object in self.h5object:
            for axis in axes.keys():
                data = np.array(h5object)
             #   print np.where(data[:,7]%2 != 0)
                Plots[axis].plot(x = data[:,5], y = data[:,axis],name = h5object.name,pen =(icolour,len(self.h5object)))
                Plots[axis].setLabel('left',axes[axis]+" (V)")
                Plots[axis].setLabel('bottom', 'Time (ps)')
            icolour = icolour + 1        
        
        
 #       print self.Spinbox.value
        self.layout.addWidget(Plots[0],0,0)
        self.layout.addWidget(Plots[1],0,1)
        self.layout.addWidget(Plots[2],1,0)
    #    self.layout.addWidget(self.Spinbox,1,1)
        
    def change_in_stepperoffset(self):
     #   self.display_data(stepperoffset = self.Spinbox.value())
        print "HI"
        
        
    @classmethod
    def is_suitable(cls, h5object):
        suitability = 0
        if type(h5object) == list:
            h5object = h5object[0]
        if not isinstance(h5object, h5py.Dataset):
            return -1
        if len(h5object.shape) == 2:
            if h5object.shape[1] == 8:
                suitability = suitability + 11
            else:
                return -1
        else:
            return -1
        if 'repeats' in h5object.attrs.keys():
            suitability = suitability + 50
        if 'start' in h5object.attrs.keys():
            suitability = suitability + 50
        if 'finish' in h5object.attrs.keys():
            suitability = suitability + 50
        if 'stepsize' in h5object.attrs.keys():
            suitability = suitability + 20
        if 'velocity' in h5object.attrs.keys():
            suitability = suitability + 20      
        if 'acceleration' in h5object.attrs.keys():
            suitability = suitability + 20    
        if 'filter' in h5object.attrs.keys():
            suitability = suitability + 20      
        if 'sensitivity' in h5object.attrs.keys():
            suitability = suitability + 20    
        return suitability
            
#            
add_renderer(PumpProbeRaw)
    
class PumpProbeShifted(DataRenderer, QtGui.QWidget):
    ''' A renderer for Pump probe experiments, leaving the data un changed'''
    """ A renderer for 1D datasets experessing them in a line graph using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region or performing transformations of the axis
    """
    def __init__(self, h5object, parent=None):
        super(PumpProbeShifted, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.layout = QtGui.QGridLayout()
        self.setLayout(self.layout)
        self.display_data()
        
    def display_data(self):
       # plot = self.figureWidget.plot()
        if type(self.h5object)!= list:
            self.h5object = [self.h5object]
        icolour = 0    
        Plots = []
        axes ={0 : 'X',1 : 'Y', 2 : 'R'}
        
    #    self.Spinbox = QtGui.QSpinBox()
   #     self.Spinbox.setValue(stepperoffset)
     #   self.Spinbox.valueChanged.connect(self.change_in_stepperoffset())
        for axis in axes:
            Plots.append(pg.PlotWidget())
       
        for plot in Plots:
            plot.addLegend(offset = (-1,1))
        
        stepperoffset = -2.0
        
        for h5object in self.h5object:
            for axis in axes.keys():
                data = np.array(h5object)
                data[np.where(data[:,7]%2 != 0),5] +=  stepperoffset
                data[:,5] = -1*(data[:,5]-(884.0))
             #   print np.where(data[:,7]%2 != 0)
                Plots[axis].plot(x = data[:,5], y = data[:,axis],name = h5object.name,pen =(icolour,len(self.h5object)))
                Plots[axis].setLabel('left',axes[axis]+" (V)")
                Plots[axis].setLabel('bottom', 'Time (ps)')
            icolour = icolour + 1        
        
        
 #       print self.Spinbox.value
        self.layout.addWidget(Plots[0],0,0)
        self.layout.addWidget(Plots[1],0,1)
        self.layout.addWidget(Plots[2],1,0)
    #    self.layout.addWidget(self.Spinbox,1,1)
        
    def change_in_stepperoffset(self):
     #   self.display_data(stepperoffset = self.Spinbox.value())
        print "HI"
        
        
    @classmethod
    def is_suitable(cls, h5object):
        suitability = 0
        if type(h5object) == list:
            h5object = h5object[0]
        if not isinstance(h5object, h5py.Dataset):
            return -1
        if len(h5object.shape) == 2:
            if h5object.shape[1] == 8:
                suitability = suitability + 11
            else:
                return -1
        else:
            return -1
        if 'repeats' in h5object.attrs.keys():
            suitability = suitability + 50
        if 'start' in h5object.attrs.keys():
            suitability = suitability + 50
        if 'finish' in h5object.attrs.keys():
            suitability = suitability + 50
        if 'stepsize' in h5object.attrs.keys():
            suitability = suitability + 20
        if 'velocity' in h5object.attrs.keys():
            suitability = suitability + 20      
        if 'acceleration' in h5object.attrs.keys():
            suitability = suitability + 20    
        if 'filter' in h5object.attrs.keys():
            suitability = suitability + 20      
        if 'sensitivity' in h5object.attrs.keys():
            suitability = suitability + 20    
        return suitability
            
#            
add_renderer(PumpProbeShifted)
class PumpProbeRawXOnly(DataRenderer, QtGui.QWidget):
    ''' A renderer for Pump probe experiments, leaving the data un changed'''
    """ A renderer for 1D datasets experessing them in a line graph using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region or performing transformations of the axis
    """
    def __init__(self, h5object, parent=None):
        super(PumpProbeRawXOnly, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.layout = QtGui.QGridLayout()
        self.setLayout(self.layout)
        self.display_data()
        
    def display_data(self):
       # plot = self.figureWidget.plot()
        if type(self.h5object)!= list:
            self.h5object = [self.h5object]
        icolour = 0    
        Plots = []
        axes ={0 : 'X'}
        
    #    self.Spinbox = QtGui.QSpinBox()
   #     self.Spinbox.setValue(stepperoffset)
     #   self.Spinbox.valueChanged.connect(self.change_in_stepperoffset())
        for axis in axes:
            Plots.append(pg.PlotWidget())
       
        for plot in Plots:
            plot.addLegend(offset = (-1,1))
        
        stepperoffset = -2.0
        
        for h5object in self.h5object:
            for axis in axes.keys():
                data = np.array(h5object)
                data[np.where(data[:,7]%2 != 0),5] +=  stepperoffset
                data[:,5] = -1*(data[:,5]-(884.0))
                data[:,0] = data[:,0]/4.0
             #   print np.where(data[:,7]%2 != 0)
                Plots[axis].plot(x = data[:,5], y = data[:,axis],name = h5object.name,pen =(icolour,len(self.h5object)))
                Plots[axis].setLabel('left',"dV/V")
                Plots[axis].setLabel('bottom', 'Time (ps)')
            icolour = icolour + 1        
        
        
 #       print self.Spinbox.value
        self.layout.addWidget(Plots[0],0,0)
    #    self.layout.addWidget(self.Spinbox,1,1)
        

        
        
    @classmethod
    def is_suitable(cls, h5object):
        suitability = 0
        if type(h5object) == list:
            h5object = h5object[0]
        if not isinstance(h5object, h5py.Dataset):
            return -1
        if len(h5object.shape) == 2:
            if h5object.shape[1] == 8:
                suitability = suitability + 11
            else:
                return -1
        else:
            return -1
        if 'repeats' in h5object.attrs.keys():
            suitability = suitability + 50
        if 'start' in h5object.attrs.keys():
            suitability = suitability + 50
        if 'finish' in h5object.attrs.keys():
            suitability = suitability + 50
        if 'stepsize' in h5object.attrs.keys():
            suitability = suitability + 20
        if 'velocity' in h5object.attrs.keys():
            suitability = suitability + 20      
        if 'acceleration' in h5object.attrs.keys():
            suitability = suitability + 20    
        if 'filter' in h5object.attrs.keys():
            suitability = suitability + 20      
        if 'sensitivity' in h5object.attrs.keys():
            suitability = suitability + 20    
        return suitability
            
#            
add_renderer(PumpProbeRawXOnly)    
if __name__ == '__main__':
    import sys, h5py, os, numpy as np

    print os.getcwd()
    app = get_qt_app()
    f = h5py.File('test.h5', 'w')
    dset = f.create_dataset('dset1', data=np.linspace(-1, 1, 100))
    ui = HDF5InfoRenderer(dset)
    ui.show()
    sys.exit(app.exec_())
    f.close()
