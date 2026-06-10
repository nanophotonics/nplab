from datetime import datetime
from math import inf
import os
from threading import Lock
from typing import Generic, List, Tuple, TypeVar, Callable, Optional
import sys
import typing

import numpy as np
from qtpy import uic
from qtpy.QtWidgets import *
from qtpy.QtCore    import QModelIndex, Signal

from nplab.instrument import Instrument
from nplab.instrument.camera.fastcamera.widgets import ScientificSpinBox
from nplab.measurement.action import Action, Message, PValue, Parameter, Result, Status, Type

import sys
from PyQt5.QtCore import Qt, pyqtSignal

from nplab.measurement.actionqueue import ActionQueue, AnyActionQueue
import nplab.datafile as df
from nplab.measurement.sweep import Sweep
from nplab.measurement.widgets import ActionWidget, ListWidget, TimeIntervalWidget


A = TypeVar("A", bound=Action)
T = TypeVar("T")

class ActionSetupGUI(Generic[A], QDialog):

    def __init__(self, action: A, classes: List[typing.Type[Action]] = [], equipment: List = []):

        super().__init__()

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.action    = action
        self.classes   = classes
        self.equipment = equipment

        self.callbacks: List[Callable] = []

        self.overall = QVBoxLayout()
        self.cols   = QHBoxLayout()
        self.vbox   = QVBoxLayout()
        self.form   = QFormLayout()

        self.vbox.addLayout(self.form)
        self.cols.addLayout(self.vbox)
        self.overall.addLayout(self.cols)
        self.overall.addWidget(self.buttonBox)

        self.setLayout(self.overall)

        self.createInstrumentFields()
        self.createParameterFields()
        self.createSweepQueue()

        
    def accept(self):

        for callback in self.callbacks:
            callback()

        super().accept()
        

    def createInstrumentFields(self):

        for instrument in self.action.getInstruments():

            names    = []
            filtered = [None] + [e for e in self.equipment if isinstance(e, instrument.type)]

            for eq in filtered:

                if hasattr(eq, "getName"):
                    nm = eq.getName()
                elif hasattr(eq, "name"):
                    nm = eq.name
                else:
                    nm = str(eq)

                names.append(nm)


            widget = QComboBox()
            widget.addItems(names)

            if (instrument.value in filtered):
                widget.setCurrentIndex(filtered.index(instrument.value))

            self.form.addRow(instrument.name + ("\n(Required)" if instrument.required else "\n(Optional)"), widget)
            self.callbacks.append(lambda i=instrument, f=filtered, w=widget: i.set(f[w.currentIndex()]))


    def createParameterFields(self):
        for parameter in self.action.getParameters():
            self.form.addRow(parameter.name, self.generateField(parameter))


    def createSweepQueue(self):

        if isinstance(self.action, Sweep):

            self.subQueue = AnyActionQueue()
            self.subQueue.addActions(*self.action.getActions())

            self.subDisplay = ActionQueueGUI(self.subQueue, self.classes, self.equipment, None)
            self.subDisplay.runButton.setVisible(False)
            self.subDisplay.logTab.setVisible(False)
            self.subDisplay.separator.setVisible(False)
            self.subDisplay.layout().setContentsMargins(0,0,0,0)

            self.cols.addWidget(self.subDisplay)
            self.callbacks.append(lambda: self.action.setActions(*self.subQueue.actions))


    def createAction(self, clss: typing.Type[Action]):
        pass


    def generateField(self, parameter: PValue[T]) -> QWidget:

        widget = None
        signal = None
        val    = parameter.value

        # We need to determine what type of field to create based on the details in the supplied parameter
        if parameter.type == Type.AUTO:

            if len(parameter.options) > 0:
                widget = QComboBox()
                widget.addItems([str(o) for o in parameter.options])
                widget.setCurrentIndex(parameter.options.index(val))

            elif isinstance(val, float):
                widget = QDoubleSpinBox()
                widget.setMinimum(parameter.range[0] if parameter.range[0] is not None else -inf)
                widget.setMaximum(parameter.range[1] if parameter.range[1] is not None else +inf)
                widget.setValue(val)
                self.callbacks.append(lambda: parameter.set(widget.value()))

            elif isinstance(val, bool):
                widget = QCheckBox()
                widget.setChecked(val)
                self.callbacks.append(lambda: parameter.set(widget.isChecked()))

            elif isinstance(val, int):
                widget = QSpinBox()
                widget.setMinimum(parameter.range[0] if parameter.range[0] is not None else -2147483648)
                widget.setMaximum(parameter.range[1] if parameter.range[1] is not None else +2147483647)
                widget.setValue(val)
                self.callbacks.append(lambda: parameter.set(widget.value()))

            elif isinstance(val, str):
                widget = QLineEdit()
                widget.setText(val)
                self.callbacks.append(lambda: parameter.set(widget.text()))

            elif isinstance(val, (list, np.ndarray)) and isinstance(val[0], float):
                widget = ListWidget[float](lambda v : str(v), QInputDialog.getDouble, 0.0)
                widget.setValues(val)
                self.callbacks.append(lambda: parameter.set(widget.getValues()))

            elif isinstance(val, (list, np.ndarray)) and isinstance(val[0], int):
                widget = ListWidget[int](lambda v : str(v), QInputDialog.getInt, 0)
                widget.setValues(val)
                self.callbacks.append(lambda: parameter.set(widget.getValues()))

            elif isinstance(val, (list, np.ndarray)) and isinstance(val[0], str):
                widget = ListWidget[str](lambda v : v, QInputDialog.getText, "")
                widget.setValues(val)
                self.callbacks.append(lambda: parameter.set(widget.getValues()))

        elif parameter.type == Type.TIME and isinstance(val, int):
            widget = TimeIntervalWidget(self)
            widget.setValue(val)
            self.callbacks.append(lambda: parameter.set(widget.value()))

        elif parameter.type == Type.TIME and isinstance(val, float):
            widget = TimeIntervalWidget(self)
            widget.setValue(int(val * 1e3))
            self.callbacks.append(lambda: parameter.set(float(widget.value()) / 1e3))

        elif parameter.type == Type.SCIENTIFIC and isinstance(val, float):
            widget = ScientificSpinBox()
            widget.setValue(val)
            self.callbacks.append(lambda: parameter.set(widget.value()))

        return widget
    

R = TypeVar("R")
Q = TypeVar("Q", bound=ActionQueue[R])

class ActionQueueGUI(Generic[Q, R], QWidget):

    actionsChangedSignal = Signal(list)
    messageSignal        = Signal(Message)
    finishedSignal       = Signal(Result)
    widgetSignal         = Signal(Action)

    def __init__(self, queue: Q, classes: List[typing.Type[Action]], equipment: List, data: R):

        super().__init__()

        self._queue     = queue
        self._classes   = classes
        self._equipment = equipment
        self._data      = data
        self._tableLock = Lock()

        self.actionList : QListWidget
        self.buttonBar  : QWidget
        self.addButton  : QToolButton
        self.remButton  : QToolButton
        self.upButton   : QToolButton
        self.dnButton   : QToolButton
        self.runButton  : QPushButton
        self.messages   : QTableWidget
        self.clearLog   : QPushButton
        self.saveLog    : QPushButton
        self.mainTab    : QWidget
        self.logTab     : QWidget
        self.separator  : QWidget
        self.nameRow    : QWidget
        self.h5Name     : QLineEdit

        uic.loadUi(os.path.dirname(__file__) + "/resources/queue.ui", self)

        self.drawActions(queue.actions)

        self.actionList.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.actionList.setResizeMode(QListView.ResizeMode.Adjust)

        self.setupConnections()
        self.setupTable()
        self.setupMenu()

        if not hasattr(queue, "namePattern"):
            self.nameRow.setVisible(False)

    
    def setupConnections(self):

        self._queue.addActionListener(self.actionsChangedSignal.emit)
        self._queue.addMessageListener(self.messageSignal.emit)
        self._queue.addFinishListener(self.finishedSignal.emit)

        self.runButton.clicked.connect(self.runClick)
        self.actionsChangedSignal.connect(self.drawActions)
        self.messageSignal.connect(self.addMessage)
        self.finishedSignal.connect(self.runFinished)
        self.actionList.itemDoubleClicked.connect(self.doubleClick)
        self.widgetSignal.connect(self.doubleClick)
        self.remButton.clicked.connect(self.removeSelected)
        self.upButton.clicked.connect(self.moveSelectedUp)
        self.dnButton.clicked.connect(self.moveSelectedDown)
        self.clearLog.clicked.connect(self.clearLogClick)
        self.saveLog.clicked.connect(self.saveLogClick)


    def setupTable(self):

        self.messages.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.messages.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.messages.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.messages.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)


    def setupMenu(self):

        menu = QMenu("Actions")

        for actionType in self._classes:
            ex   = actionType("")
            item = menu.addAction(ex.name)
            item.triggered.connect(lambda v, s=actionType: self.createAction(s))

        self.addButton.setMenu(menu)


    def clearLogClick(self):

        with self._tableLock:

            self._queue._messages.clear()
            self.messages.model().removeRows(0, self.messages.rowCount())
            self.messages.setRowCount(0)


    def saveLogClick(self):

        import pandas as pd

        file, ok = QFileDialog.getSaveFileName()

        if not ok:
            return
        
        data = np.empty(shape=(len(self._queue._messages), 4), dtype='<U2048')

        for i, message in enumerate(self._queue._messages):
            data[i, 0] = datetime.fromtimestamp(message.timestamp).strftime(r'%Y-%m-%d %H:%M:%S')
            data[i, 1] = message.type.name
            data[i, 2] = message.pathString
            data[i, 3] = message.message

        df = pd.DataFrame(data)
        df.to_csv(file, header=["Timestamp", "Source", "Type", "Message"], index=False)


    def createAction(self, clss: typing.Type[Action]):

        text, ok = QInputDialog.getText(self, "Name", "Please enter a name for this action")

        if not ok:
            return None
        
        action = clss(text)

        setup  = ActionSetupGUI(action, self._classes, self._equipment)
        result = setup.exec()
        
        if result:
            self._queue.addAction(action)


    def removeSelected(self):

        widget = self.actionList.itemWidget(self.actionList.currentItem())

        if isinstance(widget, ActionWidget):
            action = widget.getAction()
            self._queue.removeAction(action)


    def moveSelectedUp(self):

        index = self.actionList.selectedIndexes()[0].row()

        if index <= 0:
            return

        itemA = self.actionList.itemWidget(self.actionList.item(index)).getAction()
        itemB = self.actionList.itemWidget(self.actionList.item(index - 1)).getAction()

        self._queue.swapActions(itemA, itemB)
        

    def moveSelectedDown(self):

        index = self.actionList.selectedIndexes()[0].row()

        if index >= self.actionList.count() - 1:
            return

        itemA = self.actionList.itemWidget(self.actionList.item(index)).getAction()
        itemB = self.actionList.itemWidget(self.actionList.item(index + 1)).getAction()

        self._queue.swapActions(itemA, itemB)


    def drawActions(self, actions: List[Action]):

        widgets = [self.actionList.itemWidget(self.actionList.item(i)) for i in range(self.actionList.count())]

        for i in reversed(range(self.actionList.count())):
            self.actionList.takeItem(i)

        for widget in widgets:
            del widget

        self.actionList.clear()

        for action in actions:
            item   = QListWidgetItem()
            widget = ActionWidget(action)
            item.setSizeHint(widget.sizeHint())
            self.actionList.addItem(item)
            self.actionList.setItemWidget(item, widget)

            def _resized(i=item, w=widget):
                QApplication.processEvents()
                i.setSizeHint(w.sizeHint())

            widget.resized.connect(_resized)
            

    def doubleClick(self, item: QListWidgetItem):

        widget = self.actionList.itemWidget(item)

        if isinstance(widget, ActionWidget):
            setup: ActionSetupGUI = widget.getSetupWidget(self._classes, self._equipment)
            setup.exec()


    def addMessage(self, message: Message):

        with self._tableLock:

            index = self.messages.rowCount()

            self.messages.setRowCount(index + 1)
            self.messages.setItem(index, 0, QTableWidgetItem(datetime.fromtimestamp(message.timestamp).strftime(r'%Y-%m-%d %H:%M:%S')))
            self.messages.setItem(index, 1, QTableWidgetItem(str(message.type.name)))
            self.messages.setItem(index, 2, QTableWidgetItem(message.pathString))
            self.messages.setItem(index, 3, QTableWidgetItem(message.message))


    def runClick(self):

        if self._queue.isRunning:

            self.runButton.setDisabled(True)
            self.runButton.setStyleSheet("color: purple;")
            self.runButton.setText("Interrupting...")
            self._queue.interrupt()

        else:
            
            self.nameRow.setDisabled(True)
            self.actionList.selectionModel().clear()
            self.buttonBar.setDisabled(True)
            self.runButton.setText("Starting...")

            if hasattr(self._queue, "namePattern"):
                self._queue.namePattern = self.h5Name.text()

            self._queue.start(self._data)

            self.runButton.setText("Stop Queue")
            self.runButton.setDisabled(False)
            self.runButton.setStyleSheet("color: brown;")


    def runFinished(self, result: Result):

        self.runButton.setText("Run Queue")
        self.buttonBar.setDisabled(False)
        self.runButton.setDisabled(False)
        self.runButton.setStyleSheet("")
        self.nameRow.setDisabled(False)


class QueueInstrument(Instrument):

    def __init__(self, queue: ActionQueue, actions = [], equipment = [], data = None):
        super().__init__()
        
        self.queue     = queue
        self.actions   = actions
        self.equipment = equipment
        self.data      = data

    def get_qt_ui(self):
        return ActionQueueGUI(self.queue, self.actions, self.equipment, self.data)