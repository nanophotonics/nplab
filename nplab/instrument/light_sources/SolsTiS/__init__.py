"""
MSquared SolsTiS laser wrapper
==============================

This module wraps the SolsTiS 3 TCP/IP Protocol from MSquared


Not implemented:
    - Wavemeter commands
    - Report replies for commands that take a while to finish:
        Need to change how the read_message works, since it currently only reads the last full message

__author__: Yago
"""

from nplab.utils.gui import QtWidgets, QtCore, uic
from nplab.instrument import Instrument

import collections
import json
import os
import socket
import time


BUFFER_SIZE = 1000
TIMEOUT = 10.
MAX_MESSAGE_HISTORY = 10


class SolsTiSParseFail(Exception):
    # updateGUI = QtCore.SIGNAL()

    def __init__(self, dicc):
        exceptionstring = ERROR_CODE[dicc['message']['parameters']['protocol_error'][0]] + \
                          '\n at transmission: ' + str(dicc['message']['transmission_id'][0])

        super(SolsTiSParseFail, self).__init__(exceptionstring)


class SolsTiS(Instrument):
    metadata_property_names = ('laser_status', )

    def __init__(self, address, **kwargs):
        """

        :param address: tuple of the SolsTiS (TCP_IP,TCP_PORT)
        """
        Instrument.__init__(self)

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(TIMEOUT)
        self.socket.connect(address)
        self.computerIP = socket.gethostbyname(socket.gethostname())

        self.laser_status = {}
        self._transmission_id = 1
        self.message_out_history = collections.deque(maxlen=MAX_MESSAGE_HISTORY)
        self.message_in_history = collections.deque(maxlen=MAX_MESSAGE_HISTORY)

        self.start_link()
        self.system_status()

    def __del__(self):
        self.socket.close()

    def send_command(self, operation, parameters=None):
        """
        Implementation of the TCP JSON message structure as provided in the SolsTiS manual.
        Also reads back the message from the SolsTiS, and, if verbose, prints out the
        status of the laser after the command.

        :param operation: string containing name of operation
        :param parameters: dictionary of parameters for operation
        """
        if parameters is None:
            self.current_message = {
                "message":
                    {
                        "transmission_id": [self._transmission_id],
                        "op": operation
                    }
            }
        else:
            self.current_message = {
                "message":
                    {
                        "transmission_id": [self._transmission_id],
                        "op": operation,
                        "parameters": parameters
                    }
            }

        self.socket.send(json.dumps(self.current_message))

        self.message_out_history.append(self.current_message)
        self._transmission_id += 1

        self.read_message()

        if 'status' in self.message_in_history[-1]['message']['parameters'].keys():
            status = self.message_in_history[-1]['message']['parameters']['status']

            if isinstance(status, basestring):
                self._logger.debug(operation + ': ' + status)
            else:
                self._logger.debug(operation + ': ' + id_dictionary.get(operation, {})['status'][status[0]])

    def read_message(self):
        """
        Reads BUFFER_SIZE bytes from the laser, and appends the last full message to message_in_history

        """
        self.current_reply = self.socket.recv(BUFFER_SIZE)
        if len(self.current_reply.split('{')) != len(self.current_reply.split('}')):
            self._logger.warn('You have not read a full number of messages')

        self.message_in_history.append(json.loads('{' + self.current_reply.lstrip('{').split('}{')[-1]))

        if self.message_in_history[-1]['message']['op'] == 'parse_fail':
            raise SolsTiSParseFail(self.message_in_history[-1])

    def start_link(self):
        self.send_command("start_link", {"ip_address": self.computerIP})

    def ping(self, text):
        self.send_command("ping", {"text_in": text})

        return self.message_in_history[-1]['message']['parameters']['text_out']

    def change_wavelength(self, l):
        self.send_command("move_wave_t", {"wavelength": [l]})

        time.sleep(1)
        if self.message_in_history[-1]['message']['parameters']['status'][0] == 0:
            self.system_status()

    def check_wavelength(self):
        self.send_command("poll_move_wave_t")

        if self.message_in_history[-1]['message']['parameters']['status'][0] == 0:
            self.laser_status['wavelength'] = \
                self.message_in_history[-1]['message']['parameters']['current_wavelength'][0]

    def stop_tuning(self):
        self.send_command("stop_move_wave_t")

    def tune_etalon(self, val):
        self.send_command("tune_etalon", {"setting": [val]})

    def tune_cavity(self, val):
        self.send_command("tune_cavity", {"setting": [val]})

    def fine_tune_cavity(self, val):
        self.send_command("fine_tune_cavity", {"setting": [val]})

    def tune_resonator(self, val):
        self.send_command("tune_resonator", {"setting": [val]})

    def fine_tune_resonator(self, val):
        self.send_command("fine_tune_resonator", {"setting": [val]})

    def etalon_lock(self, val):
        if val not in ['off', 'on']:
            raise ValueError('Lock can only be set to "off" or "on"')
        else:
            self.send_command("etalon_lock", {"operation": val})

            if self.message_in_history[-1]['message']['parameters']['status'][0] == 0:
                self.laser_status['etalon_lock'] = val

    def etalon_lock_status(self):
        self.send_command("etalon_lock_status")

        if self.message_in_history[-1]['message']['parameters']['status'][0] == 0:
            self.laser_status['etalon_lock'] = self.message_in_history[-1]['message']['parameters']['condition']

    def cavity_lock(self, val):
        if val not in ['off', 'on']:
            self._logger.warn('Lock can only be set to "off" or "on"')
        else:
            self.send_command("cavity_lock", {"operation": val})

            if self.message_in_history[-1]['message']['parameters']['status'][0] == 0:
                self.laser_status['ref_cavity_lock'] = val

    def cavity_lock_status(self):
        self.send_command("cavity_lock_status")

        if self.message_in_history[-1]['message']['parameters']['status'][0] == 0:
            self.laser_status['ref_cavity_lock'] = self.message_in_history[-1]['message']['parameters']['condition']

    def system_status(self):
        self.send_command("get_status")

        if self.message_in_history[-1]['message']['parameters']['status'][0] == 0:
            status = self.message_in_history[-1]['message']['parameters']
            for ii in status:
                if type(status[ii]) == list:
                    self.laser_status[ii] = status[ii][0]
                else:
                    self.laser_status[ii] = status[ii]

        # self.updateGUI.emit()

    def get_qt_ui(self):
        return SolsTiSUI(self)

        # def settings(self, save=False):
        #     path = os.path.dirname(os.path.realpath(__file__))
        #     name = self.id
        #     if save:
        #         dicc = guisettings.guisave2(self, QtCore.QSettings(path + '/instr_settings/%s.ini' %name, QtCore.QSettings.IniFormat))
        #         return dicc
        #     else:
        #         guisettings.guirestore2(self, QtCore.QSettings(path + '/instr_settings/%s.ini' %name, QtCore.QSettings.IniFormat))
        #         self.change_wavelength(self.laser_status['wavelength'])
        #         self.updateGUI.emit()


class SolsTiSUI(QtWidgets.QWidget):
    def __init__(self, solstis):
        assert isinstance(solstis, SolsTiS), "instrument must be a SolsTiS"
        super(SolsTiSUI, self).__init__()

        self.SolsTiS = solstis
        self.signal = QtCore.SIGNAL('SolsTiSGUIupdate')
        self.SolsTiSMonitorThread = None

        uic.loadUi(os.path.join(os.path.dirname(__file__), 'SolsTiS.ui'), self)

        self.checkBoxSolsTiSLockMonitor.stateChanged.connect(self.SolsTiSLockMonitor)
        self.checkBoxSolsTiSEtalonLock.stateChanged.connect(self.SolsTiSLockEtalon)
        self.checkBoxSolsTiSCavityLock.stateChanged.connect(self.SolsTiSLockCavity)
        self.lineEditSolsTiSWL.returnPressed.connect(self.SolsTiSWL)
        self.pushButtonSolsTiSstatusMonitor.clicked.connect(self.SolsTiSMonitor)
        self.pushButtonSolsTiSstopMonitor.clicked.connect(self.SolsTiSMonitorStop)

        # self.SolsTiS.updateGUI.connect(self.updateGUI)

    def SolsTiSLockMonitor(self):
        # ADD A SEcTION THAT CHECKS THAT THE ETALON VOLTAGE DOESN'T GO TOO FAR AWAY
        if self.checkBoxSolsTiSEtalonLock.isChecked():
            self.SolsTisLockThread = SolsTiSLockThread(self.SolsTiS)
            self.SolsTisLockThread.connect(self.SolsTisLockThread, self.SolsTisLockThread.signal, self.SolsTiSReLock)
            self.SolsTisLockThread.start()

    def SolsTiSReLock(self):
        progress = QtWidgets.QProgressDialog("Re-locking etalon", "Abort", 0, 5, self)
        progress.show()
        i = 0
        self.SolsTiS.system_status()

        while self.SolsTiS.laser_status['etalon_lock'] != 'on' and i < 5:
            progress.setValue(i)
            self.SolsTiS.etalon_lock('on')
            time.sleep(0.5)
            self.SolsTiS.system_status()
            time.sleep(0.1)
            i += 1
        progress.close()
        if i < 5:
            self.SolsTiSLockMonitor()
        else:
            popup = QtWidgets.QMessageBox()
            popup.setText("Re-locking the etalon failed")
            popup.exec_()

    def SolsTiSLockEtalon(self):
        if self.checkBoxSolsTiSEtalonLock.isChecked():
            self.SolsTiS.etalon_lock("on")
        else:
            self.SolsTiS.etalon_lock("off")

    def SolsTiSLockCavity(self):
        if self.checkBoxSolsTiSCavityLock.isChecked():
            self.SolsTiS.cavity_lock("on")
        else:
            self.SolsTiS.cavity_lock("off")

    def SolsTiSWL(self):
        wl = float(self.lineEditSolsTiSWL.text())
        self.SolsTiS.change_wavelength(wl)

    def updateGUI(self):
        self.lineEditSolsTiSWL.setText(str(self.SolsTiS.laser_status['wavelength']))
        self.checkBoxSolsTiSCavityLock.setChecked(self.SolsTiS.laser_status['cavity_lock'] in ['on'])
        self.checkBoxSolsTiSEtalonLock.setChecked(self.SolsTiS.laser_status['etalon_lock'] in ['on'])

    def SolsTiSMonitor(self):
        '''
        Starts a monitoring thread that returns the system_status of the laser every 10s
        :return:
        '''
        if self.SolsTiSMonitorThread is None:
            self.SolsTiSMonitorThread = SolsTiSStatusThread(self.SolsTiS)
            self.SolsTiSMonitorThread.connect(self.SolsTiSMonitorThread, self.SolsTiSMonitorThread.signal,
                                              self.SolsTiSupdatestatus)
            self.SolsTiSMonitorThread.start()
        elif not self.SolsTiSMonitorThread.isRunning():
            self.SolsTiSMonitorThread.start()

    def SolsTiSMonitorStop(self):
        '''
        Terminates the monitor thread if it exists
        :return:
        '''
        if self.SolsTiSMonitorThread is not None and self.SolsTiSMonitorThread.isRunning():
            self.SolsTiSMonitorThread.terminate()

    def SolsTiSupdatestatus(self):
        '''
        relevant_properties is a dictionary of labels to display (keys) and names of the properties to display as returned
        by the laser
        We then create a dictionary with the labels and the values of the properties (display_dicc)
        And display that dictionary as a table
        :return:
        '''
        relevant_properties = {'C. lock': 'cavity_lock', 'E. lock': 'etalon_lock', 'T': 'temperature',
                               'R. volt.': 'resonator_voltage', 'E. volt.': 'etalon_voltage',
                               'wvl': 'wavelength', 'Out': 'output_monitor'}
        display_dicc = {new_key: self.SolsTiS.laser_status[relevant_properties[new_key]] for new_key in
                        relevant_properties.keys()}
        self.tableWidget.setRowCount(len(relevant_properties))
        row = 0
        for key in display_dicc.keys():
            item_key = QtWidgets.QTableWidgetItem(key)
            item_value = QtWidgets.QTableWidgetItem(str(display_dicc[key]))
            self.tableWidget.setItem(row, 0, item_key)
            self.tableWidget.setItem(row, 1, item_value)
            row = row + 1
        self.tableWidget.resizeColumnsToContents()


class SolsTiSLockThread(QtCore.QThread):
    def __init__(self, solstis):
        QtCore.QThread.__init__(self)
        self.SolsTiS = solstis
        self.signal = QtCore.SIGNAL("laser_unlocked")

        self.setTerminationEnabled()

        self.SolsTiS.system_status()
        if self.SolsTiS.laser_status['etalon_lock'] != 'on':
            self.SolsTiS.etalon_lock('on')

    def run(self):
        while self.SolsTiS.laser_status['etalon_lock'] == 'on':
            time.sleep(2)
            self.SolsTiS.system_status()
            time.sleep(0.1)

        self.emit(self.signal)


class SolsTiSStatusThread(QtCore.QThread):
    def __init__(self, solstis):
        QtCore.QThread.__init__(self)
        self.SolsTiS = solstis
        self.signal = QtCore.SIGNAL("SolsTiS_status_update")

        self.setTerminationEnabled()

        self.SolsTiS.system_status()

    def run(self):
        while 1:
            self.SolsTiS.system_status()

            self.emit(self.signal, self.SolsTiS.laser_status)

            time.sleep(1)


def download_logs():
    def perdelta(start, end, delta):
        return_list = []
        curr = start
        while curr < end:
            # yield curr
            return_list.append(curr)
            curr += delta
        return map(lambda x: (int(x.strftime('%d')), int(x.strftime('%m')), int(x.strftime('%y'))), return_list)

    '''NOT GENERAL

    Script that can be used to download the logs created by automatic logging in the laser
    '''
    import urllib2
    # import numpy as np
    from datetime import date, timedelta

    url_name = 'http://172.24.37.153/FS/FLASH0/M_Squared/Logs/log_%d_%d_%d_%d.txt'

    # nums1 = [153, 222]
    # days = np.linspace(1, 32) #[1,2,3,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29]
    # months = np.linspace(1, 13)
    # years = [15, 16]

    # nums = [(153,18,8,16), (222,24,6,16), (222,23,6,16)]


    all_logs = []
    list_dates = perdelta(date(2016, 7, 12), date(2016, 11, 4), timedelta(days=1))
    for datum in list_dates:
        try:
            data = urllib2.urlopen(url_name % ((153,) + datum))
            all_logs.append(data.read())
            print 'Downloaded ', url_name % ((153,) + datum)
        except Exception as e:
            print 'Failed ', url_name % ((153,) + datum), ' because ', e
    list_dates = perdelta(date(2015, 7, 8), date(2016, 7, 11), timedelta(days=1))
    for datum in list_dates:
        try:
            data = urllib2.urlopen(url_name % ((222,) + datum))
            all_logs.append(data.read())
            print 'Downloaded ', url_name % ((222,) + datum)
        except Exception as e:
            print 'Failed ', url_name % ((222,) + datum), ' because ', e

    # for num in nums:
    #     try:
    #         data = urllib2.urlopen(url_name % num)
    #         all_logs.append(data.read())
    #         print 'Downloaded ', url_name % num
    #     except:
    #         print 'Failed ', url_name % num
    #     time.sleep(1)
    # for num1 in nums1:
    #     for day in days:
    #         for month in months:
    #             for year in years:
    #                 try:
    #                     data = urllib2.urlopen(url_name % (num1, day, month, year))
    #                     all_logs.append(data.read())
    #                     print 'Downloaded ', url_name % (num1, day, month, year)
    #                 except:
    #                     print 'Failed ', url_name % (num1, day, month, year)
    #                 time.sleep(1)
    import pickle
    pickle.dump(all_logs, open(r'C:\Users\Hera\Desktop/SolsTiSLogs.p', 'w'))
    return all_logs


ERROR_CODE = {1: 'JSON parsing, invalid start, wrong IP',
              2: '"message" string missing',
              3: '"transmission_id" string missing',
              4: 'No transmission id value',
              5: '"op" string missing',
              6: 'No op name',
              7: 'Operation not recognised',
              8: '"parameters" string missing',
              9: 'Invalid parameter tag of value'}
id_dictionary = {'move_wave_t': {'status': {0: 'Successful', 1: 'Failed', 2: 'Out of range'}},
                 'poll_move_wave_t': {'status': {0: 'Tuning completed', 1: 'Tuning in progress', 2: 'Tuning failed'}},
                 'stop_move_wave_t': {'status': {0: 'Completed'}},
                 'tune_etalon': {'status': {0: 'Completed', 1: 'Out of range', 2: 'Failed'}},
                 'tune_cavity': {'status': {0: 'Completed', 1: 'Out of range', 2: 'Failed'}},
                 'fine_tune_cavity': {'status': {0: 'Completed', 1: 'Out of range', 2: 'Failed'}},
                 'tune_resonator': {'status': {0: 'Completed', 1: 'Out of range', 2: 'Failed'}},
                 'fine_tune_resonator': {'status': {0: 'Completed', 1: 'Out of range', 2: 'Failed'}},
                 'etalon_lock': {'status': {0: 'Completed', 1: 'Failed'}},
                 'etalon_lock_status': {'status': {0: 'Completed', 1: 'Failed'}},
                 'cavity_lock': {'status': {0: 'Completed', 1: 'Failed'}},
                 'cavity_lock_status': {'status': {0: 'Completed', 1: 'Failed'}},
                 'get_status': {'status': {0: 'Completed', 1: 'Failed'}}
                 }

if __name__ == '__main__':
    laser = SolsTiS('172.24.37.153')
    laser.show_gui()
    # all_logs = download_logs()
