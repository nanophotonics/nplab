# -*- coding: utf-8 -*-
__author__ = 'Eoin Elliott'
"""
A utility for adding any number of graphs,
plotting any number of equations on each, and varying
any number of parameters in these equations through
a gui.
"""

import numpy as np
import pyqtgraph as pg
from qtpy import QtGui, QtWidgets, QtCore

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')

def remove_inf_and_nan(array_to_test, array_to_remove_from=None):
    '''removes inf and nans from an array'''
    if array_to_remove_from is None: array_to_remove_from = array_to_test
    return np.array(array_to_remove_from)[~np.logical_or(np.isnan(list(array_to_test)),np.isinf(list(array_to_test)))]

Graphs = []
class GraphWidget(pg.PlotWidget):
    '''
    template for an interactive graph
    
    Input: 
        equation: should be a function of only 1 variable (x). 
            Parameters to be varied should be a Parameter object.
        xlim: interval over which the function will be plotted
        ylim: currently does nothing
        
    make use of xlabel and ylabel methods!
        
    '''
    def __init__(self, *args, 
                 xlim=(-10,10),
                 ylim=(0,100),
                 title='graph',
                 xlabel = 'X axis',
                 ylabel = 'Y axis'):
        super().__init__(title=title)
        self.equations = args
        self.xlim = xlim
        self.ylim = ylim
        self.title(title)
        self.xlabel(xlabel)
        self.ylabel(ylabel)
        self.hasLegend=False
        self.addLegend()
        Graphs.append(self)
    @property
    def xs(self):
        return [remove_inf_and_nan(y, self.x) for y in self.ys]
    @property
    def x(self):
        return np.linspace(*self.xlim, num=100)
    @property
    def ys(self):
        return [remove_inf_and_nan(equation(self.x)) for equation in self.equations]
        
    def update(self):
        def name(eq): # takes the name of the function the first time,
        #and returns none after to stop the legend from exploding
            if self.hasLegend: return None
            return str(eq).split(' ')[1]
            
        self.clearPlots() 
        for i,(x, y, eq) in enumerate(zip(self.xs, self.ys, self.equations)): 
            self.plot(x, y, pen=(i,len(self.ys)),name=name(eq))

    def xlabel(self, label):
        self.setLabel('bottom', label)
    def ylabel(self, label):
        self.setLabel('left', label)
    def title(self, title):
        self._title = title
        self.setTitle(title)
    def export(self):
        print('x, y(s):',self.x, self.ys, sep='\n')


class GraphGroup(QtGui.QGroupBox):
    '''
    feed me GraphWidget objects and 
    I'll lay them out horizontally
    '''
    def __init__(self, graphs):
        super().__init__('Graphs')
        self.setLayout(QtWidgets.QGridLayout())
        self.graphs = graphs
        graphs_per_row = 5 if len(graphs)>12 else 4
        for i,g in enumerate(graphs):    
            self.layout().addWidget(graphs[i], i//graphs_per_row, i%graphs_per_row)

    def update_graphs(self):
        for g in self.graphs:
            g.update()
            g.hasLegend = True
    def export(self):
        for g in self.graphs:
            print('Graph:', g._title)
            g.export()
            
            
class FloatMathMixin():
    '''allows any class to be used like a float,
    assuming it has a __float__ method.
    '''
    def __add__(self, other):
        return float(self) + np.array(other)
    def __sub__(self, other):
        return float(self) - np.array(other)
    def __mul__(self, other):
        return float(self)*np.array(other)
    def __truediv__(self,other):
        return float(self)/np.array(other)
    def __pow__(self, other):
        return float(self)**np.array(other)
    
    def __radd__(self,other):
        return self.__add__(other)
    def __rsub__(self,other):
        return self.__sub__(other)
    def __rmul__(self,other):
        return self.__mul__(other)
    def __rtruediv__(self,other):
        return self.__truediv__(other)
    def __rpow__(self, other):
        return self.__pow__(other)
    
Parameters = []                
class Parameter(QtWidgets.QWidget, FloatMathMixin):
    '''
    Representation of a parameter to be varied in an equation.
    Takes its value from the Gui.
    Supports basic array math.
    
    Inputs:
        name: the label the parameter will have in the gui
        Default: its initial value
        Min: minimum value allowed to be entered in the gui
        Max: maximum...
        
    '''
    
    param_changed = QtCore.Signal(int)
    def __init__(self, name, Default=1, Min=-100_000, Max=100_000,units=None, slider=False):
        super().__init__()
        self.name = name
        self.slider = slider
        self.units = f' ({units})' if units is not None else ''
        self.setLayout(QtWidgets.QFormLayout())
        self.box =  QtGui.QSlider(QtCore.Qt.Horizontal) if slider else QtGui.QDoubleSpinBox()
        self.label = QtGui.QLabel(self.name+self.units)
        self.layout().addWidget(self.label)
        self.box.setMinimum(Min)
        self.box.setMaximum(Max)
        self.layout().addWidget(self.box)
        self.box.setValue(Default)
        self.box.valueChanged.connect(self.changed)
        self.changed()
        Parameters.append(self)
        
    def changed(self):
        if self.slider:
            self.label.setText(str(self))
        self.param_changed.emit(1)
        
    def __float__(self):
        return float(self.box.value())
    def __repr__(self):
        return str(float(self))
    def __str__(self):
        return f'{self.name}: {float(self)} {self.units}'
      
class ParameterGroupBox(QtGui.QGroupBox):
    '''
    feed me parameters and i'll add spinBoxes for them, and 
    emit a signal when they're changed to update the graphs. 
    '''
    param_changed = QtCore.Signal(int)
    def __init__(self, parameters):
        super().__init__('Parameter controls')
        self.parameters = parameters
        self.setLayout(QtWidgets.QHBoxLayout())
        for p in self.parameters:
            self.layout().addWidget(p)
            p.param_changed.connect(self.param_changed.emit)
    def export(self):
        for p in self.parameters:
            print(p)
            
class LivePlotWindow(QtWidgets.QMainWindow):
    '''Puts the graphing and parameter widgets together'''
    def __init__(self, style='Fusion'):
        app = QtGui.QApplication.instance()
        if app is None: app = QtGui.QApplication([])
        app.setStyle(style)
        super().__init__()
        layout = QtWidgets.QVBoxLayout()
        self.resize(1500,1500)
        self.graphing_group = GraphGroup(Graphs)#graphing_group
        self.parameter_widget = ParameterGroupBox(Parameters)
        layout.addWidget(self.graphing_group)
        # export_button = QtGui.QPushButton('Export values')
        # export_button.clicked.connect(self.export)
        # layout.addWidget(export_button)
        layout.addWidget(self.parameter_widget)
        self.setWindowTitle('Live Plotting')
        # self.setWindowIcon(QtGui.QIcon('bessel.png'))
        self.setWindowIcon(QtGui.QIcon('maxwell.png'))
        self.widget = QtGui.QWidget()
        self.widget.setLayout(layout)
        self.setCentralWidget(self.widget)
        self.parameter_widget.param_changed.connect(self.update_graphs)
        self.update_graphs()
        self.show()
    
    def update_graphs(self):
        self.graphing_group.update_graphs()        
    
    def export(self):
        self.graphing_group.export()
        self.parameter_widget.export()

if __name__ == '__main__':

    #Initialize all parameters
    A = Parameter('Alpha', 15, Min=0, Max=10, units= 'm')
    B =  Parameter('Bravo', 6, slider=True, Min=-10, Max=10)
    C = Parameter('Charlie', 15)
    D = Parameter('Demelza', 6)

    
    #define the equations to be plotted
    def equation1(x):
        return A*x**2 + B*x**2 - C*x + D
    def equation2(x):
        return A*x**3 - (B/C)*x**2 + D
    def eq3(x):
        return A**np.sin(C*x)/D*x
    def eq4(x):
        return (np.sin(A*x)/B*x) +D
    def eq5(x):
        return eq3(x)[::-1]#reversed
    
    #create the graphs
    GraphWidget(equation1, equation2, title='1st')
    GraphWidget(equation2, xlim=(-5,5), title='2nd')
    GraphWidget(eq3, eq5, title='etc,', xlabel = ':)')
    GraphWidget(eq4, title='etc.')
    #x2 more of the same
    GraphWidget(equation1, equation2, title='1st')
    GraphWidget(equation2, xlim=(-5,5), title='2nd')
    GraphWidget(eq3, eq5, title='etc,', xlabel = ':)')
    GraphWidget(eq4, title='etc.')
    
    GraphWidget(equation1, equation2, title='1st')
    GraphWidget(equation2, xlim=(-5,5), title='2nd')
    GraphWidget(eq3, eq5, title='etc,', xlabel = ':)')
    GraphWidget(eq4, title='etc.')
 
    #and then the window!
    live_plotter = LivePlotWindow()
   


