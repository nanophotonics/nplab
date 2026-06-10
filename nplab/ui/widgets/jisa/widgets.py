import numpy as np
import pyjisa.autoload

from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QImage, QPixmap
from qtpy.QtWidgets import *
from jisa.results import ResultTable, ResultList
from java.lang import Integer, Long, Double, Boolean, String


class ScientificSpinBox(QWidget):

    valueChanged  = Signal(float)
    returnPressed = Signal()

    def __init__(self, parent=None, value=0.0):

        super().__init__(parent)

        # Mantissa input
        self.mantissaSpin = QDoubleSpinBox(self)

        # Exponent input
        self.exponentSpin = QSpinBox(self)
        self.exponentSpin.setMinimum(-2147483647)
        self.exponentSpin.setMaximum(2147483647)
        self.exponentSpin.setFixedWidth(50)

        self.mantissaSpin.setMaximum(+np.inf)
        self.mantissaSpin.setMinimum(-np.inf)
        self.mantissaSpin.setDecimals(5)

        # Layout: mantissa × 10 ^ exponent
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.mantissaSpin, 1)
        layout.addWidget(QLabel("×10^"), 0)
        layout.addWidget(self.exponentSpin, 0)

        self.setValue(value)

        # Signals
        self.mantissaSpin.valueChanged.connect(self.onChange)
        self.exponentSpin.valueChanged.connect(self.onChange)

        self.mantissaSpin.lineEdit().returnPressed.connect(self.returnPressed.emit)
        self.exponentSpin.lineEdit().returnPressed.connect(self.returnPressed.emit)


    def splitValue(self, value: float):

        if (value == 0.0):
            return 0.0, 0

        exponent = int(np.floor(np.log10(np.abs(value))) / 3) * 3
        mantissa = value / (10 ** exponent)
        return mantissa, exponent
    

    def onChange(self):
        self.valueChanged.emit(self.value())


    def value(self) -> float:
        return self.mantissaSpin.value() * (10 ** self.exponentSpin.value())
    

    def setValue(self, value: float):

        mantissa, exponent = self.splitValue(value)
        self.mantissaSpin.setValue(mantissa)
        self.exponentSpin.setValue(exponent)

class RowEditDialog(QDialog):

    def __init__(self, columns, values=None, parent=None):

        super().__init__(parent)

        self.setWindowTitle("Edit Row")
        self.columns = columns
        self.editors = {}

        layout = QFormLayout()

        for i, col in enumerate(columns):

            editor = self.createEditor(col)

            if values:
                self.setEditorValue(editor, values[i])

            layout.addRow(col.getTitle(), editor)
            self.editors[col] = editor


        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)

        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout.addWidget(self.buttons)
        self.setLayout(layout)


    def setValues(self, values):

        for i, val in enumerate(values):
            col = self.columns[i]
            edt = self.editors[col]
            self.setEditorValue(edt, val)

    def clearValues(self):

        for edt in self.editors.values():

            if type(edt) is QSpinBox:
                edt.setValue(0)
            elif type(edt) is ScientificSpinBox:
                edt.setValue(0.0)
            elif type(edt) is QCheckBox:
                edt.setChecked(False)
            elif type(edt) is QLineEdit:
                edt.setText("")


    def createEditor(self, col):

        colType = col.getType().getSimpleName()

        if colType in ["Integer", "Long"]:
            editor = QSpinBox()
            editor.setRange(-10**9, 10**9)
            return editor

        elif colType == "Double":
            editor = ScientificSpinBox()
            return editor

        elif colType == "Boolean":
            return QCheckBox()

        else:
            return QLineEdit()


    def setEditorValue(self, editor, value):

        if isinstance(editor, QSpinBox):
            editor.setValue(int(value))

        elif isinstance(editor, ScientificSpinBox):
            editor.setValue(float(value))

        elif isinstance(editor, QCheckBox):
            editor.setChecked(bool(value))

        elif isinstance(editor, QLineEdit):
            editor.setText(str(value))



    def getValues(self):

        result = []

        for col in self.columns:
            editor = self.editors[col]
            result.append(self.getEditorValue(editor))

        return result

    def getEditorValue(self, editor):

        if isinstance(editor, QSpinBox):
            return np.int32(editor.value())

        elif isinstance(editor, ScientificSpinBox):
            return float(editor.value())

        elif isinstance(editor, QCheckBox):
            return bool(editor.isChecked())

        elif isinstance(editor, QLineEdit):
            text = editor.text()
            return text


class ResultTableWidget(QWidget):

    def __init__(self):

        super().__init__()

        self.table   = QTableWidget()
        self.columns = []
        self.editor  = RowEditDialog(self.columns)

        layout    = QVBoxLayout()
        btnLayout = QHBoxLayout()

        self.addBtn = QPushButton("+")
        self.remBtn = QPushButton("-")
        self.upBtn  = QPushButton("▲")
        self.dnBtn  = QPushButton("▼")
        self.okBtn  = QPushButton("Close")

        btnLayout.addWidget(self.addBtn)
        btnLayout.addWidget(self.remBtn)
        btnLayout.addWidget(self.upBtn)
        btnLayout.addWidget(self.dnBtn)

        layout.addLayout(btnLayout)
        layout.addWidget(self.table)
        self.setLayout(layout)

        self.addBtn.clicked.connect(self.addRow)
        self.remBtn.clicked.connect(self.removeRow)
        self.upBtn.clicked.connect(self.moveRowUp)
        self.dnBtn.clicked.connect(self.moveRowDown)
        self.okBtn.clicked.connect(self.close)
        self.table.cellDoubleClicked.connect(self.editRow)

        self.setContentsMargins(0,0,0,0)
        self.layout().setContentsMargins(0,0,0,0)

        self.table.setMinimumWidth(100)
        self.table.setMinimumHeight(150)
        self.addBtn.setMinimumWidth(25)
        self.remBtn.setMinimumWidth(25)
        self.upBtn.setMinimumWidth(25)
        self.dnBtn.setMinimumWidth(25)


    def setResultTable(self, table: ResultTable):
        
        self.columns.clear()
        self.columns += table.getColumns()
        self.editor    = RowEditDialog(self.columns)

        self.table.clear()
        self.table.setColumnCount(table.getColumnCount())
        self.table.setHorizontalHeaderLabels([ c.getTitle() for c in table.getColumns() ])
        self.table.setRowCount(table.getRowCount())
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setMinimumWidth(0)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)

        for rowIdx, row in enumerate(table):
            values = [row.get(col) for col in self.columns]
            self.setRowData(rowIdx, values)


    def getResultTable(self) -> ResultTable:

        table = ResultList(*self.columns)

        for row in range(self.table.rowCount()):
            table.mapRow({col: self.table.item(row, idx).data(1) for idx, col in enumerate(self.columns)})

        return table


    def addRow(self):

        dialog = self.editor
        dialog.clearValues()

        if dialog.exec() == QDialog.Accepted:

            values = dialog.getValues()

            row_pos = self.table.rowCount()
            self.table.insertRow(row_pos)
            self.setRowData(row_pos, values)


    def editRow(self, row, _col):

        current_values = []

        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            current_values.append(item.data(1) if item else None)

        dialog = self.editor
        dialog.setValues(current_values)

        if dialog.exec_() == QDialog.Accepted:
            values = dialog.getValues()
            self.setRowData(row, values)


    def setRowData(self, rowIdx, values):

        for colIdx, val in enumerate(values):

            if type(val) in [bool, Boolean]:
                text = "YES" if val else "NO"
            elif type(val) in [int, Integer, Long]:
                text = "%d" % val
            elif type(val) in [float, Double]:
                text = "%.04g" % val
            else:
                text = str(val)

            item = QTableWidgetItem(text)
            item.setData(1, val)

            self.table.setItem(rowIdx, colIdx, item)


    def removeRow(self):

        row = self.table.currentRow()

        if row >= 0:
            self.table.removeRow(row)
        else:
            QMessageBox.warning(self, "Warning", "No row selected")


    def moveRowUp(self):

        row = self.table.currentRow()

        if row <= 0:
            return
        
        self.swapRows(row, row - 1)
        self.table.selectRow(row - 1)


    def moveRowDown(self):

        row = self.table.currentRow()

        if row < 0 or row >= self.table.rowCount() - 1:
            return
        
        self.swapRows(row, row + 1)
        self.table.selectRow(row + 1)


    def swapRows(self, row1, row2):
        
        for col in range(self.table.columnCount()):

            item1 = self.table.takeItem(row1, col)
            item2 = self.table.takeItem(row2, col)

            self.table.setItem(row1, col, item2)
            self.table.setItem(row2, col, item1)


class ImageListWidget(QWidget):

    def __init__(self, parent=None, thumbnail_size=120):
        
        super().__init__(parent)

        self._images = []
        self._thumbnail_size = thumbnail_size

        # Scroll area setup
        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Container inside scroll area
        self.container = QWidget()
        self.layout = QHBoxLayout(self.container)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(5)
        self.layout.setAlignment(Qt.AlignLeft)

        # Stretch to keep items left-aligned
        self.layout.addStretch()

        self.scrollArea.setWidget(self.container)

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(self.scrollArea)

    def _create_label(self, image: QImage) -> QLabel:
        
        label = QLabel()

        pixmap = QPixmap.fromImage(image).scaled(
            self._thumbnail_size,
            self._thumbnail_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        label.setPixmap(pixmap)
        label.setAlignment(Qt.AlignCenter)

        return label
    

    def addImage(self, image: QImage):

        self._images.append(image)

        label = self._create_label(image)

        self.layout.insertWidget(self.layout.count() - 1, label)


    def clearImages(self):

        self._images.clear()

        # Remove all widgets except the final stretch
        while self.layout.count() > 1:
            item = self.layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()


    def getImages(self):
        return list(self._images)
    
