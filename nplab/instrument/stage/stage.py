# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'stage.ui'
#
# Created by: PyQt5 UI code generator 5.6
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_Stage(object):
    def setupUi(self, Stage):
        Stage.setObjectName("Stage")
        Stage.resize(349, 372)
        self.verticalLayout = QtWidgets.QVBoxLayout(Stage)
        self.verticalLayout.setContentsMargins(5, 5, 5, 5)
        self.verticalLayout.setSpacing(6)
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtWidgets.QSpacerItem(40, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        #update position button
        self.update_pos_button = QtWidgets.QPushButton(Stage)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.update_pos_button.sizePolicy().hasHeightForWidth())
        self.update_pos_button.setSizePolicy(sizePolicy)
        self.update_pos_button.setObjectName("update_pos_button")
        self.horizontalLayout.addWidget(self.update_pos_button)
        #update position button end
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.info_group = QtWidgets.QGroupBox(Stage)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.info_group.sizePolicy().hasHeightForWidth())
        self.info_group.setSizePolicy(sizePolicy)
        self.info_group.setObjectName("info_group")
        self.info_layout = QtWidgets.QGridLayout(self.info_group)
        self.info_layout.setObjectName("info_layout")
        self.verticalLayout.addWidget(self.info_group)
        self.axes_group = QtWidgets.QGroupBox(Stage)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.axes_group.sizePolicy().hasHeightForWidth())
        self.axes_group.setSizePolicy(sizePolicy)
        self.axes_group.setMinimumSize(QtCore.QSize(0, 0))
        self.axes_group.setObjectName("axes_group")
        self.axes_layout = QtWidgets.QGridLayout(self.axes_group)
        self.axes_layout.setObjectName("axes_layout")
        self.verticalLayout.addWidget(self.axes_group)
        self.verticalLayout_2 = QtWidgets.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        #init button
        self.initialise_button = QtWidgets.QPushButton(Stage)
        font = QtGui.QFont()
        font.setPointSize(11)
        self.initialise_button.setFont(font)
        self.initialise_button.setObjectName("initialise_button")
        self.verticalLayout_2.addWidget(self.initialise_button)
        #move to (6,6)
        self.xy_middle_button = QtWidgets.QPushButton(Stage)
        self.xy_middle_button.setObjectName("xy_middle_button")
        self.verticalLayout_2.addWidget(self.xy_middle_button)
        self.verticalLayout.addLayout(self.verticalLayout_2)
        #move to 15.5 for z axis
        self.z_focus_button = QtWidgets.QPushButton(Stage)
        self.z_focus_button.setObjectName("z_focus_button")
        self.verticalLayout_2.addWidget(self.z_focus_button)
        self.verticalLayout.addLayout(self.verticalLayout_2)
        
        self.retranslateUi(Stage)
        QtCore.QMetaObject.connectSlotsByName(Stage)

    def retranslateUi(self, Stage):
        _translate = QtCore.QCoreApplication.translate
        Stage.setWindowTitle(_translate("Stage", "Form"))
        self.update_pos_button.setText(_translate("Stage", "Update Positions"))
        self.info_group.setTitle(_translate("Stage", "Axes Positions"))
        self.axes_group.setTitle(_translate("Stage", "Axes Relative Movement Controls"))
        self.initialise_button.setText(_translate("Stage", "Initialise (20 seconds)"))
        self.xy_middle_button.setText(_translate("Stage", "Move XY to the middle of travel range"))
        self.z_focus_button.setText(_translate("Stage", "Move Z near focus for 100x Olympus objective - NOT ZEISS"))

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    Stage = QtWidgets.QWidget()
    ui = Ui_Stage()
    ui.setupUi(Stage)
    Stage.show()
    sys.exit(app.exec_())

