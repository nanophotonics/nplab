__author__ = 'alansanders'

from nplab.utils.gui import *


class UiTools(object):
    """Methods useful to inherit when creating Qt user interfaces."""
    def replace_widget(self, layout, old_widget, new_widget, **kwargs):
        if isinstance(layout, QtGui.QGridLayout):
            index = layout.indexOf(old_widget)
            position = layout.getItemPosition(index)
            layout.removeWidget(old_widget)
            old_widget.setParent(None)
            layout.addWidget(new_widget, *position, **kwargs)
            #new_widget.setParent(self)
        else:
            index = layout.indexOf(old_widget)
            layout.removeWidget(old_widget)
            old_widget.setParent(None)
            layout.insertWidget(index, new_widget, **kwargs)
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

    def on_text_change(self, text):
        sender = self.sender()
        if sender.validator() is not None:
            state = sender.validator().validate(text, 0)[0]
            if state != QtGui.QValidator.Acceptable:
                return False
        return sender