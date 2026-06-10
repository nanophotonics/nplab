
from threading import Lock

from qtpy.QtWidgets import *
from qtpy.QtCore import QItemSelectionModel, Qt, Signal
from typing import Generic, TypeVar, List, Callable, Tuple

from nplab.measurement.action import Action, Message, Status
from nplab.measurement.sweep import Sweep

A = TypeVar("A", bound=Action)

class ActionWidget(Generic[A], QWidget):

    statusChanged   = Signal(Status)
    messageReceived = Signal(Message)
    actionsChanged  = Signal(list)
    resized         = Signal()

    def __init__(self, action: A):

        super().__init__()

        self._action  = action
        self._vbox    = QVBoxLayout()
        self._hbox    = QHBoxLayout()
        self._box     = QLabel()
        self._title   = QLabel("%s (%s)" % (action.name, action.description))
        self._status  = QLabel(action.status.name)
        self._message = QLabel("")
        self._setup   = None

        self._box.setFixedSize(25, 25)
        self._box.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
        self._title.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        self._status.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum))

        self._hbox.addWidget(self._box)
        self._hbox.addWidget(self._title)
        self._hbox.addWidget(self._status)
        self._vbox.addLayout(self._hbox)
        self._vbox.addWidget(self._message)
        self.setLayout(self._vbox)
        self.updateStatus(action.status)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        if isinstance(action, Sweep):

            self._sideBorder = QLabel()
            self._subActions = QVBoxLayout()
            self._subLayout  = QHBoxLayout()

            self._sideBorder.setMinimumWidth(10)
            self._sideBorder.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.MinimumExpanding))
            self._sideBorder.setStyleSheet("background-color: gray;")

            self._subActions.setContentsMargins(0,0,0,0)
            self._subLayout.setContentsMargins(0,0,0,0)

            self._subLayout.addWidget(self._sideBorder)
            self._subLayout.addLayout(self._subActions)
            self._subLayout.setStretch(0, 0)
            self._subLayout.setStretch(1, 1)

            self._vbox.addLayout(self._subLayout)

            values = action.getValues()

            self.updateActions(list(action.generate(values[0], action.getActions()) if len(values) > 0 else action.getActions()))


        self.setupConnections()

        lastMessage = action.getLastMessage()

        if lastMessage is not None:
            self.updateMessage(action.getLastMessage())

            
    def updateActions(self, actions: List[Action]):

        if hasattr(self, "_subActions"):
            
            widgets: List[ActionWidget] = [self._subActions.itemAt(i).widget() for i in range(self._subActions.count())]

            for widget in widgets:
                self._subActions.removeWidget(widget)
                widget.destoryListeners()
                widget.deleteLater()

            for sub in actions:
                widget = ActionWidget(sub)
                widget.layout().setContentsMargins(0,0,0,0)
                self._subActions.addWidget(widget)


            self.resized.emit()
            


    def getAction(self) -> A:
        return self._action
    

    def getSetupWidget(self, actions = [], equipment = []):

        if self._setup is None:
            from nplab.measurement.gui import ActionSetupGUI
            self._setup = ActionSetupGUI(self._action, actions, equipment)

        return self._setup
    

    def setupConnections(self):

        self._statusListener  = self._action.addStatusListener(lambda status: self.statusChanged.emit(status))
        self._messageListener = self._action.addMessageListener(lambda message: self.messageReceived.emit(message))

        self.statusChanged.connect(self.updateStatus)
        self.messageReceived.connect(self.updateMessage)

        if isinstance(self._action, Sweep):
            self._actionListener = self._action.addActionListener(lambda actions: self.actionsChanged.emit(list(actions)))
            self.actionsChanged.connect(self.updateActions)


    def destoryListeners(self):

        self._action.removeStatusListener(self._statusListener)
        self._action.removeMessageListener(self._messageListener)

        if isinstance(self._action, Sweep) and hasattr(self, "_actionListener"):

            self._action.removeActionListener(self._actionListener)

            widgets = [self._subActions.itemAt(i).widget() for i in range(self._subActions.count())]

            for widget in widgets:
                if hasattr(widget, "destroyListeners"):
                    widget.destroyListeners()
        
    
    def updateStatus(self, status: Status):

        self._status.setText(status.name)

        if status == Status.QUEUED:
            self._box.setStyleSheet("background-color: gray;")
            self._message.setText("")
        elif status == Status.RUNNING:
            self._box.setStyleSheet("background-color: orange;")
        elif status == Status.SUCCESS:
            self._box.setStyleSheet("background-color: teal;")
        elif status == Status.INTERRUPTED:
            self._box.setStyleSheet("background-color: purple;")
        elif status == Status.ERROR:
            self._box.setStyleSheet("background-color: brown;")


    def updateMessage(self, message: Message):
        if message.path[-1].part == self._action:
            self._message.setText(message.message)


T = TypeVar("T")

class ListWidget(QWidget, Generic[T]):

    def __init__(self, display: Callable[[T], str], dialog: Callable[[QWidget, str, str, T], Tuple[T, bool]], defValue: T):

        super().__init__()

        self.display          = display
        self.dialog           = dialog
        self.defValue         = defValue
        self._values: List[T] = []

        self.lyt        = QVBoxLayout(self)
        self.listWidget = QListWidget()
        buttonLayout    = QHBoxLayout()

        self.addBtn  = QPushButton("+")
        self.remBtn  = QPushButton("-")
        self.upBtn   = QPushButton("▲")
        self.downBtn = QPushButton("▼")

        buttonLayout.addWidget(self.addBtn)
        buttonLayout.addWidget(self.remBtn)
        buttonLayout.addWidget(self.upBtn)
        buttonLayout.addWidget(self.downBtn)

        self.lyt.addLayout(buttonLayout)
        self.lyt.addWidget(self.listWidget)
        self.lyt.setContentsMargins(0,0,0,0)

        self.setLayout(self.lyt)

        self.listWidget.setMinimumWidth(100)
        self.listWidget.doubleClicked.connect(self.editItem)

        # Connect signals
        self.addBtn.clicked.connect(self.addItem)
        self.remBtn.clicked.connect(self.removeItem)
        self.upBtn.clicked.connect(self.moveUp)
        self.downBtn.clicked.connect(self.moveDown)
    
    def add(self, value: T):
        """Add value of type T."""
        self.listWidget.addItem(self.display(value))
        self._values.append(value)


    def addItem(self):

        value, ok = self.dialog(self, "Add Item", "Enter Value...", self.defValue)

        if ok:
            self.add(value)


    def editItem(self):

        row = self.listWidget.currentRow()

        if row < 0:
            QMessageBox.warning(self, "No Selection", "Select an item to edit.")
            return

        item  = self.listWidget.item(row)
        value = self._values[row]

        value, ok = self.dialog(self, "Edit Item", "Enter Value...", value)

        if ok:
            item.setText(self.display(value))
            self._values[row] = value


    def removeItem(self):

        row = self.listWidget.currentRow()

        if row >= 0:
            self.listWidget.takeItem(row)
            self._values.pop(row)


    def moveUp(self):

        row = self.listWidget.currentRow()

        if row > 0:

            item = self.listWidget.takeItem(row)
            self.listWidget.insertItem(row - 1, item)
            self.listWidget.setCurrentRow(row - 1)

            self._values[row], self._values[row - 1] = (self._values[row - 1], self._values[row])


    def moveDown(self):

        row = self.listWidget.currentRow()

        if 0 <= row < self.listWidget.count() - 1:

            item = self.listWidget.takeItem(row)

            self.listWidget.insertItem(row + 1, item)
            self.listWidget.setCurrentRow(row + 1)

            self._values[row], self._values[row + 1] = (
                self._values[row + 1],
                self._values[row],
            )


    def getValues(self) -> List[T]:
        """Return list contents preserving original type."""
        return list(self._values)
    
    def setValues(self, values: List[T]):

        self._values.clear()
        self.listWidget.clear()

        for value in values:
            self.add(value)


class TimeIntervalWidget(QWidget):

    valueChanged  = Signal(int)  # milliseconds
    returnPressed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)

        self.hours = QSpinBox()
        self.hours.setRange(0, 9999)
        self.hours.setButtonSymbols(QSpinBox.NoButtons)
        self.hours.setMinimumWidth(60)
        self.hours.setAlignment(Qt.AlignRight)
        self.hours.setSuffix(" h")

        self.minutes = QSpinBox()
        self.minutes.setRange(0, 59)
        self.minutes.setButtonSymbols(QSpinBox.NoButtons)
        self.minutes.setFixedWidth(40)
        self.minutes.setAlignment(Qt.AlignRight)
        self.minutes.setSuffix(" m")

        self.seconds = QSpinBox()
        self.seconds.setRange(0, 59)
        self.seconds.setButtonSymbols(QSpinBox.NoButtons)
        self.seconds.setFixedWidth(40)
        self.seconds.setAlignment(Qt.AlignRight)
        self.seconds.setSuffix(" s")

        self.milliseconds = QSpinBox()
        self.milliseconds.setRange(0, 999)
        self.milliseconds.setButtonSymbols(QSpinBox.NoButtons)
        self.milliseconds.setFixedWidth(60)
        self.milliseconds.setAlignment(Qt.AlignRight)
        self.milliseconds.setSuffix(" ms")

        layout.addWidget(self.hours)
        layout.addWidget(QLabel(":"))
        layout.addWidget(self.minutes)
        layout.addWidget(QLabel(":"))
        layout.addWidget(self.seconds)
        layout.addWidget(QLabel(":"))
        layout.addWidget(self.milliseconds)

        for spin in (self.hours, self.minutes, self.seconds, self.milliseconds):
            spin.valueChanged.connect(self._valueChanged)
            spin.lineEdit().returnPressed.connect(self.returnPressed.emit)


    def _valueChanged(self):
        self.valueChanged.emit(self.value())

    def value(self) -> int:
        """Return interval in milliseconds"""
        return (
            self.hours.value() * 3600000
            + self.minutes.value() * 60000
            + self.seconds.value() * 1000
            + self.milliseconds.value()
        )

    def setValue(self, ms: int):
        """Set interval from milliseconds"""

        hours = ms // 3600000
        ms %= 3600000

        minutes = ms // 60000
        ms %= 60000

        seconds = ms // 1000
        ms %= 1000

        milliseconds = ms

        self.hours.setValue(hours)
        self.minutes.setValue(minutes)
        self.seconds.setValue(seconds)
        self.milliseconds.setValue(milliseconds)
