# -*- coding: utf-8 -*-
"""
Created on Wed Jun 23 12:37:43 2021

@author: Eoin
"""
import numpy as np
from PyQt5 import QtGui, QtWidgets, QtCore

import pyqtgraph as pg
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


class DoubleSlider(QtWidgets.QSlider):
    '''' A Qt slider that works with floats (doubles) - taken from
    https://stackoverflow.com/questions/42820380/use-float-for-qslider'''
    # create our our signal that we can connect to if necessary
    doubleValueChanged = QtCore.pyqtSignal(float)

    def __init__(self, *args, decimals=3, **kwargs):
        super().__init__(*args, **kwargs)
        self._multi = 10 ** decimals

        self.valueChanged.connect(self.emitDoubleValueChanged)

    def emitDoubleValueChanged(self):
        value = float(super().value())/self._multi
        self.doubleValueChanged.emit(value)

    def value(self):
        return float(super().value()) / self._multi

    def setMinimum(self, value):
        return super().setMinimum(int(value * self._multi))

    def setMaximum(self, value):
        return super().setMaximum(int(value * self._multi))

    def setSingleStep(self, value):
        return super().setSingleStep(int(value * self._multi))

    def singleStep(self):
        return float(super().singleStep()) / self._multi

    def setValue(self, value):
        super().setValue(int(value * self._multi))


class LorentzGraphWidget(pg.PlotWidget):
    '''
    template for an interactive Lorentian graph
    
    Input: 
        modes: a dict with two functions, a Lorentzian and 'annotate',
            which returns the spectral position and efficiency of the mode.
            
       xlim_func: when called provides an appropriate xlim. 
        
    '''

    def __init__(self, modes, xlim_func,
                 title='Efficiencies',
                 xlabel='wavelength (nm)',
                 ylabel='radiative efficiency',
                 resolution=100):
        super().__init__(title=title)
        self.modes = modes
        self.xlim_func = xlim_func
        self.setTitle(title)
        self.setLabel('bottom', xlabel)
        self.setLabel('left', ylabel)
        self.hasLegend = False
        self.addLegend()
        self.resolution = resolution
        self.plot_item = self.getPlotItem()
        self.plots_to_remove = []

    def _plot(self, *args, remove=True, **kwargs):
        p = self.plot(*args, **kwargs)  # pyqtgraph
        if remove:  # keep track of it if we want to remove it every update
            self.plots_to_remove.append(p)

    def update(self, remove=True):
        while self.plots_to_remove:  # remove all the stored plots
            self.plot_item.removeItem(self.plots_to_remove.pop())

        _sum = np.zeros(self.resolution)
        xs = np.linspace(*self.xlim_func(), self.resolution)  # x axis changes
        for i, (name, mode) in enumerate(self.modes.items()):
            y = mode['Lorentz'](xs)
            _sum += y

            wl, eff = mode['annotate']()
            label = f'{name}, wl={round(wl)}nm, efficiency={np.around(eff, 2)}'

            self._plot(xs, y,
                       pen=pg.mkPen(pg.intColor(i,
                                                len(self.modes),
                                                alpha=100+155*remove),
                                    width=5),
                       name=label, remove=remove)
        self._plot(xs, _sum,
                   pen=pg.mkPen(color=pg.mkColor((0, 0, 0, 100+155*remove)),
                                width=5,
                                style=QtCore.Qt.DotLine),
                   name='sum', remove=remove)

    def pin_plot(self):
       self.update(False)

    def _clear(self):
        self.clear()
        self.update()


class PinAndClearButtons(QtWidgets.QGroupBox):
    def __init__(self, graph):
        super().__init__('graph pinning buttons')
        self.setLayout(QtWidgets.QHBoxLayout())
        pin = QtWidgets.QPushButton('pin')
        pin.clicked.connect(graph.pin_plot)
        self.layout().addWidget(pin)
        clear = QtWidgets.QPushButton('clear')
        clear.clicked.connect(graph._clear)
        self.layout().addWidget(clear)


class GraphWithPinAndClearButtons(QtWidgets.QGroupBox):
    def __init__(self, *args, layout='V', **kwargs):
        super().__init__(kwargs.get('title', ''))
        self.graph = LorentzGraphWidget(*args, **kwargs)
        layout = QtWidgets.QHBoxLayout() if layout == 'H' else QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.layout().addWidget(self.graph)
        buttons = PinAndClearButtons(self.graph)
        self.layout().addWidget(buttons)

    def update(self):
        self.graph.update()


class GraphGroup(QtWidgets.QGroupBox):
    '''
    feed me GraphWidget objects and 
    I'll lay them out horizontally
    '''

    def __init__(self, graphs, layout='H'):
        super().__init__('Graphs')
        layout = QtWidgets.QHBoxLayout() if layout == 'H' else QtWidgets.QVBoxLayout()
        self.setLayout(layout)
        self.graphs = graphs
        for i, g in enumerate(graphs):
            self.layout().addWidget(g)

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
        return float(self) + np.asarray(other)

    def __sub__(self, other):
        return float(self) - np.asarray(other)

    def __mul__(self, other):
        return float(self)*np.asarray(other)

    def __truediv__(self, other):
        return float(self)/np.asarray(other)

    def __pow__(self, other):
        return float(self)**np.asarray(other)

    def __radd__(self, other):
        return self.__add__(other)

    def __rsub__(self, other):
        return self.__sub__(other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __rtruediv__(self, other):
        return self.__truediv__(other)

    def __rpow__(self, other):
        return self.__pow__(other)


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

    param_changed = QtCore.pyqtSignal()

    def __init__(self, name, default=1., Min=-100_000., Max=100_000., units=None, slider=True):

        super().__init__()
        self.name = name
        self.slider = slider
        self.units = f' ({units})' if units is not None else ''
        self.setLayout(QtWidgets.QFormLayout())
        if slider:
            self.box = DoubleSlider(QtCore.Qt.Horizontal)
        else:
            self.box = QtWidgets.QDoubleSpinBox()
        self.box.setSingleStep((Max-Min)/20.)
        self.label = QtWidgets.QLabel(self.name+self.units)
        self.layout().addWidget(self.label)
        self.box.setMinimum(float(Min))
        self.box.setMaximum(float(Max))
        self.layout().addWidget(self.box)
        self.box.setValue(float(default))
        self.box.doubleValueChanged.connect(self.changed)
        self.changed(float(default))

    def changed(self, value):
        self.param_changed.emit()
        self._float = value
        if self.slider:
            self.label.setText(str(self))

    def __float__(self):
        return self._float

    def __repr__(self):
        return str(float(self))

    def __str__(self):
        return f'{self.name}: {float(self)}{self.units}'


class ParameterGroupBox(QtWidgets.QGroupBox):
    '''
    feed me parameters and i'll add spinBoxes for them, and 
    emit a signal when they're changed to update the graphs. 
    '''
    param_changed = QtCore.pyqtSignal()

    def __init__(self, parameters):
        super().__init__('Parameter controls')
        self.parameters = parameters
        self.setLayout(QtWidgets.QHBoxLayout())
        for p in self.parameters:
            self.layout().addWidget(p)
            p.param_changed.connect(self.param_changed.emit)


class LivePlotWindow(QtWidgets.QMainWindow):
    '''Puts the graphing and parameter widgets together'''

    def __init__(self, graphs, parameters, style='Fusion'):

        super().__init__()
        layout = QtWidgets.QVBoxLayout()
        self.resize(2500, 1500)
        self.graphing_group = GraphGroup(graphs)  # graphing_group
        self.parameter_widget = ParameterGroupBox(parameters)
        layout.addWidget(self.graphing_group)
        layout.addWidget(self.parameter_widget)
        self.setWindowTitle('Live Plotting')
        self.setWindowIcon(QtGui.QIcon('maxwell.png'))
        self.widget = QtWidgets.QWidget()
        self.widget.setLayout(layout)
        self.setCentralWidget(self.widget)
        self.parameter_widget.param_changed.connect(self.update_graphs)
        self.update_graphs()
        self.show()

    def update_graphs(self):
        self.graphing_group.update_graphs()
