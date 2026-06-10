import numpy as np
import pyjisa.autoload

from typing import Callable, Generic, List, Tuple, TypeVar

from jisa.devices import Instrument
from jisa.results import ResultTable
from java.lang    import Short, Integer, Long, Double, String, Boolean

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QIcon
from qtpy.QtWidgets import QCheckBox, QComboBox, QErrorMessage, QFormLayout, QFrame, QGroupBox, QHBoxLayout, QLineEdit, QPushButton, QScrollArea, QSizePolicy, QSpinBox, QVBoxLayout, QWidget

from nplab.ui.widgets.jisa.widgets import ResultTableWidget, ScientificSpinBox

I = TypeVar("I", bound=Instrument)

class JISAConfigPanel(QWidget, Generic[I]):
    
    warningIcon = QIcon.fromTheme("dialog-warning")
    all         = []

    def __init__(self, instrument: I):

        super().__init__()
        
        self.instrument = instrument
        self.params     = []

        self.scrollArea    = QScrollArea()
        self.buttons       = QHBoxLayout()
        self.applyButton   = QPushButton("Apply All")
        self.refreshButton = QPushButton("Refresh")
        self.errorMessage  = QErrorMessage()
        self.scrollWidget  = QWidget()
        self.scrollLayout  = QVBoxLayout()
        self.mainLayout    = QVBoxLayout()

        self.setLayout(self.mainLayout)

        self.buttons.addWidget(self.refreshButton)
        self.buttons.addWidget(self.applyButton)

        self.mainLayout.addWidget(self.scrollArea)
        self.mainLayout.addLayout(self.buttons)
        self.mainLayout.setContentsMargins(0,0,0,0)
        self.setContentsMargins(0,0,0,0)

        self.scrollWidget.setLayout(self.scrollLayout)
        self.scrollArea.setWidget(self.scrollWidget)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollArea.setContentsMargins(0,0,0,0)
        self.scrollWidget.setContentsMargins(0,0,0,0)
        self.scrollLayout.setContentsMargins(0,0,0,0)
        self.scrollArea.setFrameShape(QFrame.NoFrame)
        self.scrollArea.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Ignored))
        self.setupParameters()
        self.setupConnections()

        JISAConfigPanel.all.append(self)


    def setupConnections(self):

        self.refreshButton.clicked.connect(self.refreshParameters)
        self.applyButton.clicked.connect(self.applyParameters)


    def setupParameters(self):

        forms = {"General": QFormLayout()}

        for param in self.instrument.getAllParameters():

            group = param.getGroup() if param.isGrouped() else "General"

            if group not in forms:
                forms[group] = QFormLayout()

            form = forms[group]

            widget, getter, setter, signal = self.createParameterWidget(param.getDefaultValue(), param.getChoices())

            if widget is None:
                continue

            status = QPushButton("!")
            status.setFixedSize(25, 25)
            status.setVisible(False)
            status.setStyleSheet("color: brown;")

            widget.setContentsMargins(0, 0, 0, 0)
            hbox = QHBoxLayout()
            hbox.addWidget(widget, 1)
            setB = QPushButton("✓")
            setB.setFixedWidth(25)

            form.addRow(param.getName(), hbox)

            try:
                setter(param.getCurrentValue())
            except:
                pass

            if signal is not None:
                signal.connect(lambda v=None, getter=getter, setter=setter, param=param, status=status: self.applyParameter(getter, setter, param, status))
            else:
                setB.clicked.connect(lambda v=None, getter=getter, setter=setter, param=param, status=status: self.applyParameter(getter, setter, param, status))
                hbox.addWidget(setB, 0, Qt.AlignTop)

            hbox.addWidget(status, 0, Qt.AlignTop)
            self.params.append((widget, getter, setter, param, status))
            

        for name, form in forms.items():
            box = QGroupBox(name)
            box.setLayout(form)
            self.scrollLayout.addWidget(box)


    def createParameterWidget(self, defaultValue, choices: List = []) -> Tuple[QWidget, Callable, Callable, Signal]:

        if isinstance(defaultValue, Instrument.AutoQuantity):

            checkBox = QCheckBox("Auto")
            checkBox.setChecked(defaultValue.isAuto())

            widget, getter, setter, signal = self.createParameterWidget(defaultValue.getValue(), choices)

            if widget is None:
                return (None, None, None)

            widget.setDisabled(checkBox.isChecked())

            def updateCheckBox():
                widget.setDisabled(checkBox.isChecked())
                if signal is not None:
                    signal.emit()

            checkBox.stateChanged.connect(updateCheckBox)
            
            hbox = QHBoxLayout() if not isinstance(defaultValue.getValue(), ResultTable) else QVBoxLayout()
            cont = QWidget()
            cont.setLayout(hbox)
            cont.setContentsMargins(0, 0, 0, 0)
            hbox.setContentsMargins(0, 0, 0, 0)

            hbox.addWidget(checkBox, 0)
            hbox.addWidget(widget, 1)

            def autoGetter():
                return Instrument.AutoQuantity(checkBox.isChecked(), getter())
            
            def autoSetter(aq: Instrument.AutoQuantity):
                checkBox.setChecked(aq.isAuto())
                setter(aq.getValue())

            return (cont, autoGetter, autoSetter, signal)
        
        elif isinstance(defaultValue, Instrument.OptionalQuantity):

            checkBox = QCheckBox("Enabled")
            checkBox.setChecked(defaultValue.isUsed())
            
            widget, getter, setter, signal = self.createParameterWidget(defaultValue.getValue(), choices)

            if widget is None:
                return (None, None, None)

            widget.setDisabled(not checkBox.isChecked())

            def updateCheckBox():
                widget.setDisabled(not checkBox.isChecked())
                if signal is not None:
                    signal.emit()

            checkBox.stateChanged.connect(updateCheckBox)
            
            hbox = QHBoxLayout() if not isinstance(defaultValue.getValue(), ResultTable) else QVBoxLayout()
            cont = QWidget()
            cont.setLayout(hbox)
            cont.setContentsMargins(0, 0, 0, 0)
            hbox.setContentsMargins(0, 0, 0, 0)

            hbox.addWidget(checkBox, 0)
            hbox.addWidget(widget, 1)

            def autoGetter():
                return Instrument.OptionalQuantity(checkBox.isChecked(), getter())
            
            def autoSetter(aq: Instrument.OptionalQuantity):
                checkBox.setChecked(aq.isUsed())
                setter(aq.getValue())

            return (cont, autoGetter, autoSetter, signal)
        
        elif len(choices) > 0:

            choiceBox  = QComboBox()
            choiceBox.addItems([str(c) for c in choices])

            def getter(choices=choices, choiceBox=choiceBox):
                return choices[choiceBox.currentIndex()]
            
            def setter(value):
                choiceBox.setCurrentIndex(choices.index(value))

            setter(defaultValue)

            return (choiceBox, getter, setter, choiceBox.currentIndexChanged)
        
        elif isinstance(defaultValue, (bool, Boolean)):

            checkBox = QCheckBox()
            checkBox.setChecked(defaultValue)
            return (checkBox, checkBox.isChecked, checkBox.setChecked, checkBox.stateChanged)
        
        elif isinstance(defaultValue, (Double, float)):

            doubleBox = ScientificSpinBox()
            doubleBox.setValue(defaultValue)

            return (doubleBox, doubleBox.value, doubleBox.setValue, doubleBox.returnPressed)

        elif isinstance(defaultValue, (int, Integer)):

            intBox = QSpinBox()
            intBox.setMinimum(-2147483647)
            intBox.setMaximum(2147483647)
            intBox.setValue(defaultValue)

            return (intBox, lambda: np.int32(intBox.value()), intBox.setValue, intBox.lineEdit().returnPressed)
        
        elif isinstance(defaultValue, (str, String)):

            textBox = QLineEdit()
            textBox.setText(str(defaultValue))

            return (textBox, textBox.text, textBox.setText, textBox.returnPressed)
        
        elif isinstance(defaultValue, ResultTable):

            table = ResultTableWidget()
            table.setResultTable(defaultValue)

            return (table, table.getResultTable, table.setResultTable, None)

        else:
            
            return (None, None, None, None)


    def refreshParameters(self):

        for (w, g, s, p, st) in self.params:

            try:
                s(p.getCurrentValue())
            except Exception as e:
                print(e)


    def applyParameters(self):
        '''Applies all configuration parameters, then updates their displayed values'''

        result = self.instrument.beforeApplyParameters()

        for (w, g, s, p, st) in self.params:
            self.applyParameter(g, s, p, st, False, False)

        for panel in JISAConfigPanel.all:
            panel.refreshParameters()

        self.instrument.afterApplyParameters(result)


    def applyParameter(self, getter: Callable, setter: Callable, param: Instrument.Parameter, status: QPushButton, refresh=True, prepare=True):
        '''Applies one single parameter, optionally can refresh all others afterwards if specified'''

        status.setVisible(False)

        if prepare:
            result = self.instrument.beforeApplyParameters()
        else:
            result = False

        try:
            status.clicked.disconnect()
        except:
            pass

        try:
            param.set(getter())
        except Exception as e:
            status.clicked.connect(lambda v, e=e: self.showException(e))
            status.setVisible(True)

        for panel in JISAConfigPanel.all:
            panel.refreshParameters()

        if prepare:
            self.instrument.afterApplyParameters(result)


    def showException(self, e: Exception):
        self.errorMessage.showMessage(str(e))