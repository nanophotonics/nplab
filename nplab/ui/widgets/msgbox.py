# -*- coding: utf-8 -*-

from nplab.utils.gui import QtWidgets, get_qt_app
from functools import reduce
import numpy as np


def button_box(text="Message box pop up window", title="NpLab button_box", buttons=('Ok', 'Cancel')):
    app = get_qt_app()
    msgBox = QtWidgets.QMessageBox()
    msgBox.setIcon(QtWidgets.QMessageBox.Information)
    msgBox.setText(text)
    msgBox.setWindowTitle(title)
    bttns = [getattr(QtWidgets.QMessageBox, b) for b in buttons]
    msgBox.setStandardButtons(reduce(lambda x, y: x | y, bttns))

    return_button = msgBox.exec()
    button_index = np.argwhere(return_button == np.array(bttns))[0][0]
    return button_index


def prompt_box(text='Enter text:', title="NpLab prompt_box", default='', widget=None, ):
    app = get_qt_app()
    if widget is None:
        widget = QtWidgets.QInputDialog()
        widget.setInputMode(QtWidgets.QInputDialog.TextInput)
        widget.setWindowTitle(title)
        widget.setLabelText(text)
        widget.setTextValue(default)
        if widget.exec_() == QtWidgets.QDialog.Accepted:
            returnValue = widget.textValue()
        else:
            returnValue = False
        widget.deleteLater()
        return returnValue
    else:
        text, ok = QtWidgets.QInputDialog().getText(widget, title, text, text=default)
        if ok:
            return text
        else:
            return ok
