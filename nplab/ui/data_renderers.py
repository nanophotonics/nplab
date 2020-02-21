# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from builtins import str
from builtins import range
from past.utils import old_div
from builtins import object

from nplab.utils.gui import QtGui, QtWidgets, get_qt_app, uic
from nplab.utils.array_with_attrs import ArrayWithAttrs
import matplotlib

try:
    from matplotlib.backends.qt_compat import is_pyqt5
except (AttributeError, ImportError): 
    from matplotlib.backends.qt_compat import QT_API
    def is_pyqt5():
        return (QT_API[:5] == 'PyQt5')
    
if is_pyqt5():
    matplotlib.use('Qt5Agg')
else:
    matplotlib.use('Qt4Agg')
    from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import pyqtgraph as pg
import numpy as np
import nplab.datafile as df
import operator
import h5py
import os


"""
Created on Thu Oct 29 10:36:07 2015

@author: wmd22

"""
__author__ = 'alansanders, Will Deacon'


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
    
group_renders = set()

def add_group_renderer(renderer_class):
    """Add a renderer to the list of available renderers"""
    group_renders.add(renderer_class)
    
def suitable_renderers(h5object, return_scores=False):
    """Find renderers that can render a given object, in order of suitability.
    If the selected group contains more than 100 elements, consider only the
    group_renderers and not the rest, which are very time consuming.
    """
    renderers_and_scores = []
    if isinstance(h5object, h5py.Group) and len(list(h5object.values()))>100:
        for r in group_renders:
            try:
                renderers_and_scores.append((r.is_suitable(h5object), r))
            except:
      #          print "renderer {0} failed when checking suitability for {1}".format(r, h5object)
                pass # renderers that cause exceptions shouldn't be used!

    else:    
        for r in renderers:
            try:
                renderers_and_scores.append((r.is_suitable(h5object), r))
            except:
                # print("renderer {0} failed when checking suitability for {1}".format(r, h5object))
                pass # renderers that cause exceptions shouldn't be used!
    renderers_and_scores.sort(key=lambda score_r: score_r[0], reverse=True)
    if return_scores:
        return [(score, r) for score, r in renderers_and_scores if score >= 0]
    else:
        return [r for score, r in renderers_and_scores if score >= 0]

#hdf5_info_base,
#hdf5_info_widget = uic.loadUi(os.path.join(os.path.dirname(__file__), 'hdf5_info_renderer.ui'))
#Had to change load Ui Type to Load Ui
class HDF5InfoRenderer(DataRenderer, QtWidgets.QWidget):
    """ A renderer returning the basic HDF5 info"""
    def __init__(self, h5object, parent=None):
        super(HDF5InfoRenderer, self).__init__(h5object, parent)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'hdf5_info_renderer.ui'),self)
        self.parent = parent
        self.h5object = h5object


        self.lineEdit.setText(self.h5object.name)
        self.lineEdit2.setText(self.h5object.parent.name)
        self.lineEdit3.setText(self.h5object.file.filename)
        

    @classmethod
    def is_suitable(cls, h5object):
        # Retrieve the things we're going to display to check that they exist (if an exception occurs, the renderer
        # will be deemed unsuitable)
        name = h5object.name
        parentname = h5object.parent.name
        filename = h5object.file.filename
        return 2

add_renderer(HDF5InfoRenderer)
add_group_renderer(HDF5InfoRenderer)

class ValueRenderer(DataRenderer, QtWidgets.QWidget):
    """A renderer returning the objects name type and shape if a dataset object"""
    def __init__(self, h5object, parent=None):
        super(ValueRenderer, self).__init__(h5object, parent)
        
        #our layout is simple - just a single QLabel
        self.label = QtWidgets.QLabel()
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        self.label.setText(self.text(h5object))
        
    def text(self, h5object):
        """Return the text that is displayed in the label"""
        return str(h5object.value)

    @classmethod
    def is_suitable(cls, h5object):
        try:
            if len(h5object.shape)==0:
                return 10
            else:
                return -1
        except:
            return -1

add_renderer(ValueRenderer)

class TextRenderer(DataRenderer, QtWidgets.QWidget):
    """A renderer returning the objects name type and shape if a dataset object"""
    def __init__(self, h5object, parent=None):
        super(TextRenderer, self).__init__(h5object, parent)
        
        #our layout is simple - just a single QLineEdit
        self.label = QtWidgets.QLineEdit()
        layout = QtWidgets.QFormLayout(self)
        layout.addWidget(self.label)
        self.setLayout(layout)
        
        self.label.setText(self.text(h5object))
        
    def text(self, h5object):
        """Return the text that is displayed in the label"""
        return str(h5object)

    @classmethod
    def is_suitable(cls, h5object):
        return 1

add_renderer(TextRenderer)
add_group_renderer(TextRenderer)

#hdf5_attrs_base, hdf5_attrs_widget = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'hdf5_attrs_renderer.ui'))
#, hdf5_attrs_base, hdf5_attrs_widget
class AttrsRenderer(DataRenderer, QtWidgets.QWidget):
    """ A renderer displaying a table with the Attributes of the HDF5 object selected"""
    
    def __init__(self, h5object, parent=None):
        super(AttrsRenderer, self).__init__(h5object)
        uic.loadUi(os.path.join(os.path.join(os.path.dirname(__file__), 'hdf5_attrs_renderer.ui')),self)
        
        self.h5object = h5object
        
        if type(h5object)==list:
            item_info = QtWidgets.QTableWidgetItem("Choose a single element to display its attributes!")
            self.tableWidget.setItem(0,0,item_info)
            self.tableWidget.resizeColumnsToContents()
        else:
            self.tableWidget.setRowCount(len(self.h5object.attrs))
            row = 0
            for key, value in sorted(h5object.attrs.items()):
                item_key = QtWidgets.QTableWidgetItem(key)
                item_value = QtWidgets.QTableWidgetItem(str(value))
                self.tableWidget.setItem(row,0,item_key)
                self.tableWidget.setItem(row,1,item_value)
                row = row + 1
            self.tableWidget.resizeColumnsToContents()
        
        
# PREVIOUS ATTRIBUTES RENDERER
#class AttrsRenderer(TextRenderer):
#    """ A renderer displaying the Attributes of the HDF5 object selected"""
#    def text(self, h5object):
#        text = "Attributes:\n"
#        for key, value in h5object.attrs.iteritems():
#            text += "{0}: {1}\n".format(key, str(value))
#        return text
        
    @classmethod
    def is_suitable(cls, h5object):
        if isinstance(h5object,h5py.Group):
            if len(list(h5object.keys())) > 10:
                return 5000
        return 1
add_renderer(AttrsRenderer)
add_group_renderer(AttrsRenderer)

class FigureRenderer(DataRenderer, QtWidgets.QWidget):
    """A renderer class which sets up a matplotlib figure for use 
    in more complicated renderers
    """
    def __init__(self, h5object, parent=None):
        super(FigureRenderer, self).__init__(h5object, parent)
        self.fig = Figure()

        layout = QtWidgets.QVBoxLayout(self)
        self.figureWidget = FigureCanvas(self.fig)
        layout.addWidget(self.figureWidget)
        self.setLayout(layout)

        self.display_data()

    def display_data(self):
        self.fig.canvas.draw()

class FigureRendererPG(DataRenderer, QtWidgets.QWidget):
    """A renderer class which sets up a pyqtgraph for use 
    in more complicated renderers
    """
    def __init__(self, h5object, parent=None):
        super(FigureRendererPG, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.figureWidget =  pg.PlotWidget(name='Plot1') 
        self.layout = QtWidgets.QVBoxLayout(self)
        self.layout.addWidget(self.figureWidget)
        self.setLayout(self.layout)

        self.display_data()

    def display_data(self):
        self.fig.canvas.draw()

     
class DataRenderer1DPG(FigureRendererPG):
    """ A renderer for 1D datasets experessing them in a line graph using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region or performing transformations of the axis
    """
    def display_data(self):
        if not hasattr(self.h5object, "values"):
            # If we have only one item, treat it as a group containing that item.
            self.h5object = {self.h5object.name: self.h5object}
        icolour = 0    
        self.figureWidget.addLegend(offset = (-1,1))
        for h5object in list(self.h5object.values()):
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
            
        labelStyle = {'font-size': '24pt'}
        try:
            self.figureWidget.setLabel('bottom', h5object.attrs['X label'], **labelStyle)
        except:
            self.figureWidget.setLabel('bottom', 'An X axis', **labelStyle)
            
        try:
            self.figureWidget.setLabel('left', h5object.attrs['Y label'], **labelStyle)
        except:
            self.figureWidget.setLabel('left', 'An Y axis', **labelStyle)

    @classmethod
    def is_suitable(cls, h5object):
        if not hasattr(h5object, "values"):
            # If we have only one item, treat it as a group containing that item.
            h5object = {h5object.name: h5object}

        for dataset in list(h5object.values()):
            # Check that all datasets selected are either 1D or Nx2 or 2xN
            assert isinstance(dataset, h5py.Dataset) #we can only render datasets
            try:
                assert len(dataset.shape) == 1
            except:
                assert len(dataset.shape) == 2
                assert np.any(np.array(dataset.shape) == 2)
        return 14
            
add_renderer(DataRenderer1DPG)

class Scatter_plot1DPG(FigureRendererPG):
    """ A renderer for 1D datasets experessing them in a scatter graph using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region or performing transformations of the axis
    """

    def display_data(self):
        if not hasattr(self.h5object, "values"):
            # If we have only one item, treat it as a group containing that item.
            self.h5object = {self.h5object.name: self.h5object}
        icolour = 0    
        self.figureWidget.addLegend(offset = (-1,1))
        for h5object in list(self.h5object.values()): 
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
            
        labelStyle = {'font-size': '24pt'}
        try:
            self.figureWidget.setLabel('bottom', h5object.attrs['X label'], **labelStyle)
        except:
            self.figureWidget.setLabel('bottom', 'An X axis', **labelStyle)
            
        try:
            self.figureWidget.setLabel('left', h5object.attrs['Y label'], **labelStyle)
        except:
            self.figureWidget.setLabel('left', 'An Y axis', **labelStyle)
          
    @classmethod
    def is_suitable(cls, h5object):
        return DataRenderer1DPG.is_suitable(h5object) - 2

add_renderer(Scatter_plot1DPG)


class Normalised_Parameter_renderer(FigureRendererPG):
    """ A renderer for multiple parameters plotted agains the same x-axis, normalised for easy comparison
        author: ee306
    """

    def display_data(self):
        if not hasattr(self.h5object, "values"):
            # If we have only one item, treat it as a group containing that item.
            self.h5object = {self.h5object.name: self.h5object}
       
        self.figureWidget.addLegend(offset = (-1,1))
        icolor = 0
        for h5object in list(self.h5object.values()): 
            icolor+=1
            try: x_axis = h5object.attrs['x_axis']
            except: print('x-axis not found')
            for index, Ydata in enumerate(h5object):
                try:    
                    Max = float(np.max(Ydata))
                    
                    self.figureWidget.plot(x = x_axis,
                                           y = old_div(Ydata,Max),
                                           pen = (icolor,len(self.h5object)),
                                           name = h5object.name)
                    icolor+=1
                
                except: print('failed')
            
            
        labelStyle = {'font-size': '24pt'}
        try:
            self.figureWidget.setLabel('bottom', h5object.attrs['x-axis'], **labelStyle)
        except:
            self.figureWidget.setLabel('bottom', 'An X axis', **labelStyle)
            
        try:
            self.figureWidget.setLabel('left', h5object.attrs['Y label'], **labelStyle)
        except:
            self.figureWidget.setLabel('left', 'Normalised y-axis', **labelStyle)
          
    @classmethod
    def is_suitable(cls, h5object):
        if len(h5object)>1:
            if h5object.hasattr('parameter_renderer') and h5object.hasattr('x-axis'):
                return 5
        else:
            return -1

add_renderer(Normalised_Parameter_renderer)

class Parameter_renderer(FigureRendererPG):
    """ A renderer for multiple parameters plotted agains the same x-axis
        author: ee306
    """

    def display_data(self):
        if not hasattr(self.h5object, "values"):
            # If we have only one item, treat it as a group containing that item.
            self.h5object = {self.h5object.name: self.h5object}
       
        self.figureWidget.addLegend(offset = (-1,1))
        icolor = 0
        for h5object in list(self.h5object.values()): 
            icolor+=1
            try: x_axis = h5object.attrs['x_axis']
            except: print('x-axis not found')
            for index, Ydata in enumerate(h5object):
                try:    
                
                    
                    self.figureWidget.plot(x = x_axis,
                                           y = Ydata,
                                           pen = (icolor,len(self.h5object)),
                                           name = h5object.name)
                    icolor+=1
                
                except: print('failed')
            
            
        labelStyle = {'font-size': '24pt'}
        try:
            self.figureWidget.setLabel('bottom', h5object.attrs['x-axis'], **labelStyle)
        except:
            self.figureWidget.setLabel('bottom', 'An X axis', **labelStyle)
            
        try:
            self.figureWidget.setLabel('left', h5object.attrs['Y label'], **labelStyle)
        except:
            self.figureWidget.setLabel('left', 'Normalised y-axis', **labelStyle)
          
    @classmethod
    def is_suitable(cls, h5object):
        if len(h5object)>1:
            if h5object.hasattr('parameter_renderer') and h5object.hasattr('x-axis'):
                return 5
        else:
            return -1


add_renderer(Parameter_renderer)

class MultiSpectrum2D(DataRenderer, QtWidgets.QWidget):
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
    
    It should be noted when using this renderer that all infs and NaNs will be shown as 0!!!
    """
    def __init__(self, h5object, parent=None):
        super(MultiSpectrum2D, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.layout = QtWidgets.QGridLayout()
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
        
        if isinstance(self.h5object,dict) or isinstance(self.h5object,h5py.Group):
#            for i in range(len(self.h5object.values())):
#                if i == 0:    
#                    data = np.array(self.h5object.values()[i])
#                else:
#                    data = np.append(data,np.array(self.h5object.values()[i]),axis = 0)
 #           sorted_values = 
            data = np.array(list(self.h5object.values()))
            dict_of_times = {}
            for h5object in list(self.h5object.values()):
                dict_of_times[h5object.attrs['creation_timestamp']]=h5object
            data = np.array(list(dict_of_times.values()))
            for i,h5object_time in enumerate(sorted(dict_of_times.keys())):
                if i == 0:    
                    data = np.array([dict_of_times[h5object_time]])
                else:
                    data = np.append(data,np.array([dict_of_times[h5object_time]]),axis = 0)

                
            ListData = True
            print(np.shape(data),np.shape(list(self.h5object.values())))
        elif len(self.h5object.shape) == 1 and len(self.h5object.attrs['wavelengths'])<len(self.h5object) and len(self.h5object)%len(self.h5object.attrs['wavelengths']) == 0:
            RawData = np.array(self.h5object,dtype = float)
            Xlen = len(np.array(self.h5object.attrs['wavelengths']))
            Ylen = old_div(len(RawData),Xlen)
            data = [RawData.reshape((Ylen,Xlen))]
            self.h5object = {self.h5object.name : self.h5object}
            ListData = False
            
        else:
            data = [np.array(self.h5object)]
            self.h5object = {self.h5object.name : self.h5object}
            ListData = False

        background_counter = 0
        reference_counter = 0
        i = 0
        j = 0
        for h5object in data:
            Title = "A"
            variable_int = False

            if 'variable_int_enabled' in list(list(self.h5object.values())[i].attrs.keys()):
                variable_int = list(self.h5object.values())[i].attrs['variable_int_enabled']
            if ((variable_int == True) and #Check for variable integration time and that the background_int and reference_int are not none
                        ((list(self.h5object.values())[i].attrs['background_int'] != list(self.h5object.values())[i].attrs['integration_time'] 
                            and (list(self.h5object.values())[i].attrs['background_int'] != None))
                        or (list(self.h5object.values())[i].attrs['reference_int'] != list(self.h5object.values())[i].attrs['integration_time'] 
                            and (list(self.h5object.values())[i].attrs['reference_int'] != None)))):
                if list(self.h5object.values())[i].attrs['background_int'] != None:
                    if list(self.h5object.values())[i].attrs['reference_int'] != None:
                        data[i] = (old_div((data[i]-(list(self.h5object.values())[i].attrs['background_constant']+list(self.h5object.values())[i].attrs['background_gradient']*list(self.h5object.values())[i].attrs['integration_time'])),
                                        (old_div((list(self.h5object.values())[i].attrs['reference']-(list(self.h5object.values())[i].attrs['background_constant']+list(self.h5object.values())[i].attrs['background_gradient']*list(self.h5object.values())[i].attrs['reference_int']))
                                        *list(self.h5object.values())[i].attrs['integration_time'],list(self.h5object.values())[i].attrs['reference_int']))))
                    else:
                        data[i] = data[i]-(list(self.h5object.values())[i].attrs['background_constant']+list(self.h5object.values())[i].attrs['background_gradient']*list(self.h5object.values())[i].attrs['integration_time'])
                        reference_counter = reference_counter +1
                
            else:
                if 'background' in list(list(self.h5object.values())[i].attrs.keys()):
                    if ListData == True:
                        if len(np.array(data[i])) == len(np.array(list(self.h5object.values())[i].attrs['reference'])):
                            data[i] = data[i] - np.array(list(self.h5object.values())[i].attrs['background'])     
                    else:
                        if len(np.array(data)) == len(np.array(list(self.h5object.values())[i].attrs['background'])):
                                data = data - np.array(list(self.h5object.values())[i].attrs['background'])[:,np.newaxis]       
                        Title = Title + " background subtracted"
                else:
                    background_counter = background_counter+1
                if 'reference' in list(list(self.h5object.values())[i].attrs.keys()):
                    if ListData == True:
                        if len(np.array(data[i])) == len(np.array(list(self.h5object.values())[i].attrs['reference'])):
                            data[i] = old_div(data[i],(np.array(list(self.h5object.values())[i].attrs['reference'])- np.array(list(self.h5object.values())[i].attrs['background'])))   
                    else:
                        if len(np.array(data)) == len(np.array(list(self.h5object.values())[i].attrs['reference'])):
                            data = old_div(data,(np.array(list(self.h5object.values())[i].attrs['reference'])[:,np.newaxis]- np.array(list(self.h5object.values())[i].attrs['background'])[:,np.newaxis]))
                    Title = Title + " referenced"
                else:
                    reference_counter = reference_counter +1
   #         print i,j,np.max(data) ,self.h5object.values()[i].attrs.keys()
            if len(list(self.h5object.values())) != len(data):
                i = int((float(len(list(self.h5object.values())))/len(data))*j)
                j=j+1
            else:
                i = i +1
            
        if ListData == False:
            data = data[0]            
        data = np.transpose(data)
        
            
        if reference_counter == 0 and background_counter == 0:
            print("All spectrum are referenced and background subtracted")
        else:
            print("Number of spectrum not referenced "+str(reference_counter))
            print("Number of spectrum not background subtracted "+str(background_counter))
        Title = Title + " spectrum"
         
        data[np.where(np.isnan(data))] = 0
        data[np.where(np.isinf(data))] = 0



      #  plot.plot(x = np.array(self.h5object.attrs['wavelengths']), y = np.array(h5object),name = h5object.name)
        labelStyle = {'font-size': '24pt'}
        vb.setLabel('left', 'Spectrum number',**labelStyle)
        vb.setLabel('bottom', 'Wavelength (nm)',**labelStyle)

        vb.setTitle(Title,**labelStyle)
        

        img = pg.ImageItem(data)

        ConvertionC= list(self.h5object.values())[0].attrs['wavelengths'][0]
        ConvertionM = old_div((list(self.h5object.values())[0].attrs['wavelengths'][-1] - list(self.h5object.values())[0].attrs['wavelengths'][0]),len(list(self.h5object.values())[0].attrs['wavelengths']))



        img.translate(ConvertionC,0)
        img.scale(ConvertionM,1)
        vb.addItem(img)
        vb.autoRange(False)


        w.setImageItem(img)


   
    @classmethod
    def is_suitable(cls, h5object):
        suitability = 0
        if isinstance(h5object,dict) == False and isinstance(h5object,h5py.Group) == False:
            try:
                if len(h5object.shape) == 1 and old_div(len(h5object),len(h5object.attrs['wavelengths'])) == 1:
                    return -1
            except:
                return -1
            h5object = {h5object.name : h5object}
        
        for dataset in list(h5object.values()):
            if not isinstance(dataset, h5py.Dataset):
                return -1
            if len(dataset.shape) == 1:
                suitability = suitability + 10
                    
            if len(dataset.shape) > 2:
                return -1
      
            if 'wavelengths' in list(dataset.attrs.keys()):
                if len(dataset.shape) == 2:
                    if len(np.array(dataset)[:,0])<100:
                        suitability = suitability + len(h5object)-20
                    else:
                        return 1
                elif (old_div(len(np.array(dataset)),len(dataset.attrs['wavelengths'])))>1 and (len(np.array(dataset))%len(dataset.attrs['wavelengths'])) == 0 :           
                    suitability = suitability + 50
                elif len(dataset.attrs['wavelengths']) != len(np.array(dataset)):
                    print("the number of bins does not equal the number of wavelengths!")
                    return -1
                suitability = suitability + 11
            else:
                return -1
             
            if 'background' in list(dataset.attrs.keys()):
                suitability = suitability + 10
            if 'reference' in list(dataset.attrs.keys()):
                suitability = suitability + 10
             
        return suitability    

add_renderer(MultiSpectrum2D)

class DataRenderer2or3DPG(DataRenderer, QtWidgets.QWidget):
    """ A renderer for 2D datasets images experessing them in a colour map using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region and changing the colour scheme through the use of a histogramLUT 
    widget on the right of the image while also allowing the user to scroll through the
    frames that make the image 3-d dimensional.
    """
    def __init__(self, h5object, parent=None):
        super(DataRenderer2or3DPG, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)
        

        self.display_data()

    def display_data(self, data=None, lock_aspect=False):
        if data is None:
            data = np.array(self.h5object)
        data[np.where(np.isnan(data))] = 0 
        img = pg.ImageView()
        if len(data.shape)==3 and data.shape[2]==3:
            data = np.transpose(data,axes = (1,0,2))
        elif len(data.shape)==2:
            data = np.transpose(data)
            
        img.setImage(data)
        #img.setMinimumSize(950,750) #This seems unhelpful to me - RWB
        img.view.setAspectLocked(lock_aspect)
        self.layout.addWidget(img)
        self.setLayout(self.layout)

   
    @classmethod
    def is_suitable(cls, h5object):
        if not isinstance(h5object, h5py.Dataset):
            return -1
        elif len(h5object.shape) == 3:
            return 31
        elif len(h5object.shape) == 4 and h5object.shape[3] == 3:
            return 31
        elif len(h5object.shape) == 2:
            return 21
        elif len(h5object.shape) > 3:
            return -1
        else:
            return -1

add_renderer(DataRenderer2or3DPG)


class JPEGRenderer(DataRenderer2or3DPG):
    """Renders a 1D array holding JPEG data as a 2D image."""
    def __init__(self, h5object, parent=None):
        super(JPEGRenderer, self).__init__(h5object, parent)

    def display_data(self):
        import cv2
        data = cv2.imdecode(np.array(self.h5object), cv2.CV_LOAD_IMAGE_UNCHANGED)
        DataRenderer2or3DPG.display_data(self, data=data.transpose((1,0,2)), lock_aspect=True)

    @classmethod
    def is_suitable(cls, h5object):
        if h5object.attrs['compressed_image_format'] in ['JPEG', 'PNG', ]:
            return 50
        if len(h5object.shape)==1:
            # Detect the JPEG header directly.  NB this is a work in progress, I don't think it works currently.
            if h5object[:4] == np.array([255,216,255,224],dtype=np.uint8):
                return 50
        return -1

add_renderer(JPEGRenderer)

   
class DataRenderer1D(FigureRenderer):
    """ A renderer for 1D datasets experessing them in a line graph using
    matplotlib. Although this does not allow the user to interact with the
    figure it is often found to be more stable.
    """
    def display_data(self):
        matplotlib.rc('xtick', labelsize=24) 
        matplotlib.rc('ytick', labelsize=24) 
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
    matplotlib. Although this does not allow the user to interact with the
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
        else:
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
        else:
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
        if type(self.h5object) == h5py.Dataset:
            self.h5object = {self.h5object.name : self.h5object}
        #Perform averaging
        h5list = {}
        for h5object in list(self.h5object.values()):  
            if 'averaging_enabled' in list(h5object.attrs.keys()):
                if h5object.attrs['averaging_enabled']==True:
                    ldata = np.average(np.array(h5object)[...],axis = 0)
                    linedata = ArrayWithAttrs(ldata,attrs = h5object.attrs)
                    linedata.name = h5object.name
                    h5list[linedata.name] =linedata
                else:
                    h5list[h5object.name] = h5object
            else:
                h5list[h5object.name] = h5object
        self.h5object = h5list


   #     if isinstance(self.h5object,dict) or isinstance(self.h5object,h5py.Group):
   #         pass
        #take 2D or one datasets and combine them
        h5list = {}
        for h5object in list(self.h5object.values()):
            if len(h5object.shape)==2:
                for line in range(len(h5object[:,0])):
                    ldata = np.array(h5object)[line]
                    linedata = ArrayWithAttrs(ldata,attrs = h5object.attrs)
                    linedata.name = h5object.name+"_"+str(line)
                    h5list[linedata.name] =linedata
            else:
                h5list[h5object.name] = h5object
        self.h5object = h5list
   #     elif type(self.h5object) != dict or type(self.h5object) != df.Group or type(self.h5object) != h5py.Group:
  #      elif type(self.h5object) == h5py.Dataset
 #           self.h5object = {self.h5object.name : self.h5object}
        #Deal with averaging of spectra
        plot = self.figureWidget
        plot.addLegend(offset = (-1,1))
        icolour = 0
        for h5object in list(self.h5object.values()):
            icolour = icolour+1
            Data = np.array(h5object)
            Title = "A"
            if 'variable_int_enabled' in list(h5object.attrs.keys()):
                variable_int = h5object.attrs['variable_int_enabled']
            else:
                variable_int =False
            if ((variable_int == True) and #Check for variable integration time and that the background_int and reference_int are not none
                        ((h5object.attrs['background_int'] != h5object.attrs['integration_time'] 
                            and (h5object.attrs['background_int'] != None))
                        or (h5object.attrs['reference_int'] != h5object.attrs['integration_time'] 
                            and (h5object.attrs['reference_int'] != None)))):
                Title = Title + " variable"
                if h5object.attrs['background_int'] != None:
                    if h5object.attrs['reference_int'] != None:
                        Data = (old_div((Data-(h5object.attrs['background_constant']+h5object.attrs['background_gradient']*h5object.attrs['integration_time'])), 
                                        (old_div((h5object.attrs['reference']-(h5object.attrs['background_constant']+h5object.attrs['background_gradient']*h5object.attrs['reference_int']))
                                        *h5object.attrs['integration_time'],h5object.attrs['reference_int']))))
                        Title = Title + " referenced and background subtracted"
                    else:
                        Data = Data-(h5object.attrs['background_constant']+h5object.attrs['background_gradient']*h5object.attrs['integration_time'])
                        Title = Title + " background subtracted"
            else:
                if 'background' in list(h5object.attrs.keys()):
                    if len(np.array(h5object)) == len(np.array(h5object.attrs['background'])):
                        Data = Data - np.array(h5object.attrs['background'])
                        Title = Title + " background subtracted"
                    if 'reference' in list(h5object.attrs.keys()):
                        if len(np.array(h5object)) == len(np.array(h5object.attrs['reference'])):
                            Data = old_div(Data,(np.array(h5object.attrs['reference'])- np.array(h5object.attrs['background'])))
                            Title = Title + " referenced"
            if 'absorption_enabled' in list(h5object.attrs.keys()):
                if h5object.attrs['absorption_enabled']:
                    Data = np.log10(old_div(1,np.array(Data)))
            plot.plot(x = np.array(h5object.attrs['wavelengths']), y = np.array(Data),name = h5object.name, pen =(icolour,len(self.h5object)) )
            Title = Title + " spectrum"
                
            labelStyle = {'font-size': '24pt'}
            self.figureWidget.setLabel('left', 'Intensity',**labelStyle)
            self.figureWidget.setLabel('bottom', 'Wavelength (nm)',**labelStyle)
            self.figureWidget.setTitle(Title,**labelStyle) # displays too small
            
        
   
    @classmethod
    def is_suitable(cls, h5object):
        suitability = 0
        if isinstance(h5object,dict) == False and isinstance(h5object,h5py.Group) == False:
            h5object = {h5object.name : h5object}
        for dataset in list(h5object.values()):
            if not isinstance(dataset, h5py.Dataset):
                return -1
            if len(dataset.shape) == 1:
                suitability = suitability + 10
                    
            if len(dataset.shape) > 2:
                return -1
      
            if 'wavelengths' in list(dataset.attrs.keys()):
                if len(dataset.shape) == 2:
                    if len(np.array(dataset)[:,0])<20:
                        suitability = suitability + len(h5object)-20
                    else:
                        return 1
                elif len(dataset.attrs['wavelengths']) != len(np.array(dataset)):
                    print("the number of bins does not equal the number of wavelengths!")
                    return -1
                suitability = suitability + 10
            else:
                return -1
             
            if 'background' in list(dataset.attrs.keys()):
                suitability = suitability + 10
            if 'reference' in list(dataset.attrs.keys()):
                suitability = suitability + 10 
        suitability = suitability + 10
        return suitability    
            
add_renderer(SpectrumRenderer)    


class HyperSpec(DataRenderer, QtWidgets.QWidget):
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
        self.layout = QtWidgets.QGridLayout()
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
            midpoints.append(int(old_div(np.shape(data)[dim],2)))

     
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

        
        Images[1].getImageItem().scale(convertionfactors[1][0],convertionfactors[1][1])
        
        Images[2].getImageItem().scale(convertionfactors[2][0], convertionfactors[2][1])

        
        
               


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
        elif len(h5object.shape) == 4 and 'z' in list(h5object.attrs.keys()) and 'y' in list(h5object.attrs.keys()) and 'x' in list(h5object.attrs.keys()):
            return 30
        elif len(h5object.shape) > 4:
            return -1
        else:
            return -1


add_renderer(HyperSpec)


class HyperSpec_Alan(DataRenderer, QtWidgets.QWidget):
    """ A Renderer similar to HyperSpec however written to match Alan's style of 
    writting hyperspec images with the x,y and wavelengths being in different dataset within one group. 
    Currently only capable of displaying Hyperspec images from two spectromters in two dimensions.
    
    If you need to do 3D grid scans feel free to update me!

    """
    def __init__(self, h5object, parent=None):
        super(HyperSpec_Alan, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)
        self.display_data()

    def display_data(self):
        # A try and except loop to determine the number of hyperspectral image avaible
        try:
            original_string = 'hs_image'
            test_string = original_string
            num_hyperspec = 1
            Fail = False
            while Fail == False:
                self.h5object[test_string]
                num_hyperspec = num_hyperspec + 1
                test_string = original_string+str(num_hyperspec)
        except KeyError:
            pass
        #Creating a list of hyperspec images to put into a the layout
        Images = []
        #Calculate the X,Y scales for the images
        XConvertionM = old_div((self.h5object['x'][-1] - self.h5object['x'][0]),len(self.h5object['x']))
        YConvertionM = old_div((self.h5object['y'][-1] - self.h5object['y'][0]),len(self.h5object['y']))
        #creating an iterator for the number of hyperspectral images
        for hyperspec_nom in range(1,num_hyperspec):
            if hyperspec_nom == 1:
                hyperspec_nom_str = ''
            else:
                hyperspec_nom_str = str(hyperspec_nom)
                
            #Grab the correct hyperspec data
            data = np.transpose(np.array(self.h5object['hs_image'+hyperspec_nom_str]))
            #Change NaNs to zeros (prevents error)
            data[0][np.where(np.isnan(data[0]))] = 0 
        
            #create image item for current image                 
            Images.append(pg.ImageView(view=pg.PlotItem()))
            #Set image
            Images[hyperspec_nom-1].setImage(data,xvals = np.array(self.h5object['wavelength2']),autoHistogramRange = True)
            
     
            # Formating of the Image
            Images[hyperspec_nom-1].getImageItem().scale(XConvertionM,YConvertionM)
            Images[hyperspec_nom-1].autoRange()
            Images[hyperspec_nom-1].autoLevels()
            Images[hyperspec_nom-1].ui.roiBtn.hide()
            Images[hyperspec_nom-1].ui.menuBtn.hide()
            Images[hyperspec_nom-1].setMinimumSize(550,350)
        
       #Image postion within a grid, (with need updating if using mroe than 4 spectrometers)
        positions = [[0,0],[0,1],[1,0],[1,1]]    
        #Add Images to layout
        for hyperspec_nom in range(num_hyperspec-1): 
            self.layout.addWidget(Images[hyperspec_nom],positions[hyperspec_nom][0],positions[hyperspec_nom][1])

        
        self.setLayout(self.layout)

   
    @classmethod
    def is_suitable(cls, h5object):
        suitability = 0
        try:
            h5object['hs_image']
            suitability = suitability + 10
        except KeyError:
            return -1
            
        try:
            h5object['wavelength']
            suitability = suitability + 10
        except KeyError:
            return -1
            
        try:
            h5object['y']
            suitability = suitability + 10
        except KeyError:
            return -1
            
        try:
            h5object['x']
            suitability = suitability + 10
        except KeyError:
            return -1  
            
        return suitability

add_renderer(HyperSpec_Alan)

class ScannedParticle(FigureRenderer):
    """A renderer for individual particles from a particle scan."""
    def display_data(self):
        g = self.h5object
        zscan = g['z_scan']
        dz = g['z_scan'].attrs.get('dz', np.arange(zscan.shape[0]))
        spectrum = np.mean(zscan, axis=0)
        wavelengths = zscan.attrs.get("wavelengths")
        spectrum_range = slice(None)
        try:
            background = zscan.attrs.get("background")
            spectrum -= background #we'll fail here if there was no background recorded
            reference = zscan.attrs.get("reference")
            spectrum /= (reference - background) #if there's a reference, apply it
            spectrum_range = reference > old_div(np.max(reference),10)
        except:
            pass # if reference/background are missing, ignore them.
        import matplotlib.gridspec as gridspec
        gs = gridspec.GridSpec(2,2)
        ax0 = self.fig.add_subplot(gs[0,0])  # plot the overview image
        ax0.imshow(g['camera_image'], extent=(0, 1, 0, 1), aspect="equal")
        ax0.plot([0.5, 0.5], [0.2, 0.8], "w-") #crosshair
        ax0.plot([0.2, 0.8], [0.5, 0.5], "w-")
        ax0.get_xaxis().set_visible(False)
        ax0.get_yaxis().set_visible(False)
        ax0.set_title("Particle Image")

        ax1 = self.fig.add_subplot(gs[0,1])  # plot the z stack
        ax1.imshow(zscan, extent=(wavelengths.min(), wavelengths.max(), dz.min(), dz.max()), aspect="auto", cmap="cubehelix")
        ax1.set_xlabel("Wavelength/nm")
        ax1.set_ylabel("Z/um")

        ax2 = self.fig.add_subplot(gs[1,0:2])  # plot the spectrum
        ax2.plot(wavelengths[spectrum_range], spectrum[spectrum_range])
        ax2.set_xlabel("Wavelength/nm")
        ax2.set_ylabel("Z-averaged Spectrum")
        self.fig.canvas.draw()

    @classmethod
    def is_suitable(cls, h5object):
        # This relies on sensible exception handling: if an exception occurs here, the renderer
        # will be deemed unsuitable (!)

        # First, make sure we've got the right datasets (NB this also raises an exception if it's not a group)
        g = h5object
        keys = list(g.keys())
        for k in ['camera_image', 'z_scan']:
            assert k in keys, "missing dataset {}, can't be a particle...".format(k)
        assert g['camera_image'].shape[0] > 10
        assert g['camera_image'].shape[1] > 10
        assert len(g['z_scan'].shape) == 2
        return 500
add_renderer(ScannedParticle)

class PumpProbeShifted(DataRenderer, QtWidgets.QWidget):
    ''' A renderer for Pump probe experiments, leaving the data un changed'''
    """ A renderer for 1D datasets experessing them in a line graph using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region or performing transformations of the axis
    """
    def __init__(self, h5object, parent=None):
        super(PumpProbeShifted, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)
        self.display_data()
        
    def display_data(self):
        if isinstance(self.h5object,dict) == False and isinstance(self.h5object,h5py.Group) == False:
            self.h5object = {self.h5object.name : self.h5object}
        icolour = 0    
        Plots = []
        axes ={0 : 'X',1 : 'Y', 2 : 'R'}
        

        for axis in axes:
            Plots.append(pg.PlotWidget())
       
        for plot in Plots:
            plot.addLegend(offset = (-1,1))
        
        stepperoffset = -5.0
        
        for h5object in list(self.h5object.values()):
            for axis in list(axes.keys()):
                data = np.array(h5object)
                data[np.where(data[:,7]%2 != 0),5] +=  stepperoffset
                data[:,5] = -1*(data[:,5]-(864.0))
     
                Plots[axis].plot(x = data[:,5], y = data[:,axis],name = h5object.name,pen =(icolour,len(self.h5object)))
                Plots[axis].setLabel('left',axes[axis]+" (V)")
                Plots[axis].setLabel('bottom', 'Time (ps)')
            icolour = icolour + 1        
        
        

        self.layout.addWidget(Plots[0],0,0)
        self.layout.addWidget(Plots[1],0,1)
        self.layout.addWidget(Plots[2],1,0)

        
    def change_in_stepperoffset(self):
        print("HI")
        
        
    @classmethod
    def is_suitable(cls, h5object):
        suitability = 0
        if isinstance(h5object,dict) == False and isinstance(h5object,h5py.Group) == False:
            h5object = {h5object.name : h5object}
            
        for dataset in list(h5object.values()):
            if not isinstance(dataset, h5py.Dataset):
                return -1
            if len(dataset.shape) == 2:
                if dataset.shape[1] == 8:
                    suitability = suitability + 11
                else:
                    return -1
            else:
                return -1
            if 'repeats' in list(dataset.attrs.keys()):
                suitability = suitability + 50
            if 'start' in list(dataset.attrs.keys()):
                suitability = suitability + 50
            if 'finish' in list(dataset.attrs.keys()):
                suitability = suitability + 50
            if 'stepsize' in list(dataset.attrs.keys()):
                suitability = suitability + 20
            if 'velocity' in list(dataset.attrs.keys()):
                suitability = suitability + 20      
            if 'acceleration' in list(dataset.attrs.keys()):
                suitability = suitability + 20    
            if 'filter' in list(dataset.attrs.keys()):
                suitability = suitability + 20      
            if 'sensitivity' in list(dataset.attrs.keys()):
                suitability = suitability + 20    
        return suitability
            
            
add_renderer(PumpProbeShifted)
class PumpProbeRaw(DataRenderer, QtWidgets.QWidget):
    ''' A renderer for Pump probe experiments, leaving the data un changed'''
    """ A renderer for 1D datasets experessing them in a line graph using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region or performing transformations of the axis
    """
    def __init__(self, h5object, parent=None):
        super(PumpProbeRaw, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)
        self.display_data()
        
    def display_data(self):
        if isinstance(self.h5object,dict) == False and isinstance(self.h5object,h5py.Group) == False:
            self.h5object = {self.h5object.name : self.h5object}
        icolour = 0    
        Plots = []
        axes ={0 : 'X',1 : 'Y', 2 : 'R'}
        

        for axis in axes:
            Plots.append(pg.PlotWidget())
       
        for plot in Plots:
            plot.addLegend(offset = (-1,1))
        
   #     stepperoffset = -5.0
        
        for h5object in list(self.h5object.values()):
            for axis in list(axes.keys()):
                data = np.array(h5object)
          #      data[np.where(data[:,7]%2 != 0),5] +=  stepperoffset
        #        data[:,5] = -1*(data[:,5]-(864.0))

                Plots[axis].plot(x = data[:,6], y = data[:,axis],name = h5object.name,pen =(icolour,len(self.h5object)))
                Plots[axis].setLabel('left',axes[axis]+" (V)")
                Plots[axis].setLabel('bottom', 'Time (ps)')
            icolour = icolour + 1        
        
        

        self.layout.addWidget(Plots[0],0,0)
        self.layout.addWidget(Plots[1],0,1)
        self.layout.addWidget(Plots[2],1,0)
             
                
    @classmethod
    def is_suitable(cls, h5object):
        suitability = 0
        if isinstance(h5object,dict) == False and isinstance(h5object,h5py.Group) == False:
            h5object = {h5object.name : h5object}
           
        for dataset in list(h5object.values()):
            if not isinstance(dataset, h5py.Dataset):
                return -1
            if len(dataset.shape) == 2:
                if dataset.shape[1] == 8:
                    suitability = suitability + 11
                else:
                    return -1
            else:
                return -1
            if 'repeats' in list(dataset.attrs.keys()):
                suitability = suitability + 50
            if 'start' in list(dataset.attrs.keys()):
                suitability = suitability + 50
            if 'finish' in list(dataset.attrs.keys()):
                suitability = suitability + 50
            if 'stepsize' in list(dataset.attrs.keys()):
                suitability = suitability + 20
            if 'velocity' in list(dataset.attrs.keys()):
                suitability = suitability + 20      
            if 'acceleration' in list(dataset.attrs.keys()):
                suitability = suitability + 20    
            if 'filter' in list(dataset.attrs.keys()):
                suitability = suitability + 20      
            if 'sensitivity' in list(dataset.attrs.keys()):
                suitability = suitability + 20    
        return suitability
add_renderer(PumpProbeRaw)
    

class PumpProbeRawXOnly(DataRenderer, QtWidgets.QWidget):
    ''' A renderer for Pump probe experiments, leaving the data un changed'''
    """ A renderer for 1D datasets experessing them in a line graph using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region or performing transformations of the axis
    """
    def __init__(self, h5object, parent=None):
        super(PumpProbeRawXOnly, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)
        self.display_data()
        
    def display_data(self):
        if isinstance(self.h5object,dict) == False and isinstance(self.h5object,h5py.Group) == False:
            self.h5object = {self.h5object.name : self.h5object}
        icolour = 0    
        Plots = []
        axes ={0 : 'X'}
        

        for axis in axes:
            Plots.append(pg.PlotWidget())
       
        for plot in Plots:
            plot.addLegend(offset = (-1,1))
        
        stepperoffset = -5.0
        
        for h5object in list(self.h5object.values()):
            for axis in list(axes.keys()):
                data = np.array(h5object)
                data[np.where(data[:,7]%2 != 0),5] +=  stepperoffset
                data[:,5] = -1*(data[:,5]-(864.0))
                data[:,0] = data[:,0]/8.0

                Plots[axis].plot(x = data[:,5], y = data[:,axis],name = h5object.name,pen =(icolour,len(self.h5object)))
                Plots[axis].setLabel('left',"dV/V")
                Plots[axis].setLabel('bottom', 'Time (ps)')
            icolour = icolour + 1        
        
        
        self.layout.addWidget(Plots[0],0,0)
        

        
        
    @classmethod
    def is_suitable(cls, h5object):
        suitability = 0
        if isinstance(h5object,dict) == False and isinstance(h5object,h5py.Group) == False:
            h5object = {h5object.name : h5object}       
            
        for dataset in list(h5object.values()):
            if not isinstance(dataset, h5py.Dataset):
                return -1
            if len(dataset.shape) == 2:
                if dataset.shape[1] == 8:
                    suitability = suitability + 11
                else:
                    return -1
            else:
                return -1
            if 'repeats' in list(dataset.attrs.keys()):
                suitability = suitability + 50
            if 'start' in list(dataset.attrs.keys()):
                suitability = suitability + 50
            if 'finish' in list(dataset.attrs.keys()):
                suitability = suitability + 50
            if 'stepsize' in list(dataset.attrs.keys()):
                suitability = suitability + 20
            if 'velocity' in list(dataset.attrs.keys()):
                suitability = suitability + 20      
            if 'acceleration' in list(dataset.attrs.keys()):
                suitability = suitability + 20    
            if 'filter' in list(dataset.attrs.keys()):
                suitability = suitability + 20      
            if 'sensitivity' in list(dataset.attrs.keys()):
                suitability = suitability + 20    
        return suitability

add_renderer(PumpProbeRawXOnly)
        
class PumpProbeX_loops(DataRenderer, QtWidgets.QWidget):
    ''' A renderer for Pump probe experiments, leaving the data un changed'''
    """ A renderer for 1D datasets experessing them in a line graph using
    pyqt graph. Allowing the user to interact with the graph i.e. zooming into 
    selected region or performing transformations of the axis
    """
    def __init__(self, h5object, parent=None):
        super(PumpProbeX_loops, self).__init__(h5object, parent)
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        self.layout = QtWidgets.QGridLayout()
        self.setLayout(self.layout)
        self.display_data()
        
    def display_data(self):
        if isinstance(self.h5object,dict) == False and isinstance(self.h5object,h5py.Group) == False:
            self.h5object = {self.h5object.name : self.h5object}
        icolour = 0    
        Plots = []
        axes ={0 : 'X'}
        

        for axis in axes:
            Plots.append(pg.PlotWidget())
       
        for plot in Plots:
            plot.addLegend(offset = (-1,1))
        
        stepperoffset = -5.0
        
        for h5object in list(self.h5object.values()):
            for axis in list(axes.keys()):
                data = np.array(h5object)
                data[np.where(data[:,7]%2 != 0),5] +=  stepperoffset
                data[:,5] = -1*(data[:,5]-(864.0))
                data[:,0] = data[:,0]/8.0
             
                for icolour in range(int(np.max(data[:,7])+1)):
                    Plots[axis].plot(x = data[np.where(data[:,7]==icolour)[0],5], y = data[np.where(data[:,7]==icolour)[0],axis],name = h5object.name,pen =(icolour,np.max(data[:,7])+1))
                Plots[axis].setLabel('left',"dV/V")
                Plots[axis].setLabel('bottom', 'Time (ps)')
            icolour = icolour + 1        
        
        

        self.layout.addWidget(Plots[0],0,0)

    @classmethod
    def is_suitable(cls, h5object):
        suitability = 0
        if isinstance(h5object,dict) == False and isinstance(h5object,h5py.Group) == False:
            h5object = {h5object.name : h5object}
            
        for dataset in list(h5object.values()):
            if not isinstance(dataset, h5py.Dataset):
                return -1
            if len(dataset.shape) == 2:
                if dataset.shape[1] == 8:
                    suitability = suitability + 11
                else:
                    return -1
            else:
                return -1
            if 'repeats' in list(dataset.attrs.keys()):
                suitability = suitability + 50
            if 'start' in list(dataset.attrs.keys()):
                suitability = suitability + 50
            if 'finish' in list(dataset.attrs.keys()):
                suitability = suitability + 50
            if 'stepsize' in list(dataset.attrs.keys()):
                suitability = suitability + 20
            if 'velocity' in list(dataset.attrs.keys()):
                suitability = suitability + 20      
            if 'acceleration' in list(dataset.attrs.keys()):
                suitability = suitability + 20    
            if 'filter' in list(dataset.attrs.keys()):
                suitability = suitability + 20      
            if 'sensitivity' in list(dataset.attrs.keys()):
                suitability = suitability + 20    
        return suitability
            
add_renderer(PumpProbeX_loops)


class AutocorrelationRenderer(FigureRendererPG):
    """ A renderer for 1D datasets pushing them through the autocorrelation function prior to plotting. 
    Also looks for metadata annotations in each dataset. In the case when the dataset attributes include field:
        dt
        frequency
    The make_Xdata generates converts the 1D dataset into a 2D dataset by reconstructing the times at which the data was sampled and 
    relabels the X-axis with the time. Lastly, before plotting the data is transformed to an equivalent of "semilogx" format in matplotlib
    """

    #Computes autocorrelation of the data using FFT: O(nlogn). Direct computation of correlation is O(n^2) and so is slower
    @staticmethod
    def autocorrelation(x,mode="fft"):
        import scipy.signal
        x=np.asarray(x)
        n = len(x)
        mean = x.mean()
        if mode == "fft":
            r = scipy.signal.correlate(x,x,mode="full",method="fft")[-n:]
            outp = np.divide(r,np.multiply(mean**2,np.arange(n,0,-1)))
            return outp
        elif mode == "direct":
            r = np.correlate(x, x, mode = 'full')[-n:]
            outp =  np.divide(r,np.multiply(mean**2,np.arange(n,0,-1)))
            return outp

    #Tries to convert the array of indices on the X axis into time sample points by checking if dataset contains "dt" or "frequency" metadata annotations
    @staticmethod
    def make_Xdata(dataset,N):
        #Pulls out metadata from the datasets in the case when the dataset is 1D
        # reconstructs the sampling times, assuming equidistant - halves space requirements
        Xdata = np.arange(N)
        keys = ["dt", "frequency"]
        for k in keys:
            if k in list(dataset.attrs.keys()):
                if k == "dt":
                    try:
                        dt = float(dataset.attrs[k])
                        return dt*Xdata,"Log10(Time) [s]"
                    except: pass
                elif k == "frequency":
                    try:
                        dt = 1.0/float(dataset.attrs[k])
                        return dt*Xdata,"Log10(Time) [s]"
                    except: pass
            else:
                return Xdata,"Log10(ArrayIndex)"
        
    def display_data(self):
        if not hasattr(self.h5object, "values"):
            # If we have only one item, treat it as a group containing that item.
            self.h5object = {self.h5object.name: self.h5object}
        icolour = 0    
        self.figureWidget.addLegend(offset = (-1,1))

        #Default X and Y labels
        Xlabel = 'Log10(X axis)'
        Ylabel = 'ACF(Y axis)'
        for dataset in list(self.h5object.values()):

            #Try to pull out axes label annotations from metadata + reformat them
            try:
                Xlabel = "Log10({0})".format(dataset.attrs['X label'])
            except:
                pass
            try:
                Ylabel = "ACF({0})".format(dataset.attrs['Y label'])
            except:
                pass
            #Pull out data
            try:
                if np.shape(dataset)[0] == 2 or np.shape(dataset)[1] == 2:
                    Xdata = np.array(dataset)[0]
                    Ydata = np.array(dataset)[1] 
                else:
                    Ydata = np.array(dataset)
                    #no xdata stores - generate our own
                    Xdata,Xlabel = AutocorrelationRenderer.make_Xdata(dataset, len(Ydata))
            except IndexError:
                #no xdata stores - generate our own
                Ydata = np.array(dataset)
                Xdata,Xlabel = AutocorrelationRenderer.make_Xdata(dataset, len(Ydata))

            #Final transform prior to plotting:
            xs = np.log10(Xdata[1:])
            ys = AutocorrelationRenderer.autocorrelation(Ydata)[1:]
            #plot
            self.figureWidget.plot(x = xs, y = ys,name = dataset.name, pen =(icolour,len(self.h5object)))
            icolour = icolour + 1
            
        labelStyle = {'font-size': '24pt'}
        #set axes labels
        self.figureWidget.setLabel('bottom', Xlabel, **labelStyle)
        self.figureWidget.setLabel('left', Ylabel, **labelStyle)
       

    @classmethod
    def is_suitable(cls, h5object):
        if not hasattr(h5object, "values"):
            # If we have only one item, treat it as a group containing that item.
            h5object = {h5object.name: h5object}

        for dataset in list(h5object.values()):
            # Check that all datasets selected are either 1D or Nx2 or 2xN
            assert isinstance(dataset, h5py.Dataset)
            #autocorrelation functions are only for the adlink9812 card
            assert(dataset.attrs["device"]=="adlink9812") 
            try:
                assert len(dataset.shape) == 1
            except:
                assert len(dataset.shape) == 2
                assert np.any(np.array(dataset.shape) == 2)

        return 14
        
add_renderer(AutocorrelationRenderer)

if __name__ == '__main__':
    import sys

    print(os.getcwd())
    app = get_qt_app()
    f = h5py.File('test.h5', 'w')
    dset = f.create_dataset('dset1', data=np.linspace(-1, 1, 100))
    ui = HDF5InfoRenderer(dset)
    ui.show()
    sys.exit(app.exec_())
    f.close()
