__author__ = 'alansanders'

from nplab.utils.gui import *


class UiTools(object):

    def replace_widget(self, layout, old_widget, new_widget):
        layout.addWidget(new_widget)
        #new_widget.setParent(self)
        layout.removeWidget(old_widget)
        old_widget.setParent(None)
        return new_widget

    def check_state(self, *args, **kwargs):
        sender = self.sender()
        validator = sender.validator()
        state = validator.validate(sender.text(), 0)[0]
        if state == QtGui.QValidator.Acceptable:
            color = '#c4df9b'  # green
        elif state == QtGui.QValidator.Intermediate:
            color = '#fff79a'  # yellow
        else:
            color = '#f6989d'  # red
        sender.setStyleSheet('QLineEdit { background-color: %s }' % color)
        return True if state == QtGui.QValidator.Acceptable else False