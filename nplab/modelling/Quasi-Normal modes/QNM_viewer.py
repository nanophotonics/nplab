# -*- coding: utf-8 -*-
"""
Created on Tue Jun  8 19:32:29 2021

@author: Eoin
"""
from collections import defaultdict
from functools import cache
from pathlib import Path

import qdarkstyle  # dark theme
from PyQt5.QtWidgets import QApplication

from mim import MIM
from widgets import GraphWithPinAndClearButtons, LivePlotWindow, Parameter

pi = 3.14159265


def ev_to_wl(eV):
    return 1239.8419300923943 / eV


wl_to_ev = ev_to_wl


def wl_to_omega(wl):
    return 2 * pi * 1239.8419300923943 / wl


def Lorentz(wls, center_wl, eff):
    eVs, center_eV = map(wl_to_ev, (wls, center_wl))
    width_2 = MIM(center_eV, n, t) / (1 - eff)  # eV - = Gamma/2
    lor = (width_2 / (width_2**2 + ((eVs - center_eV))**2)) / (2 * pi**2)
    # 2pi times all eVs for angular frequency, then divide by pi for normalizing
    return lor * eff


def file_to_mode_name(file):
    return file.stem.replace('=', '_').split('_')[1]


def func_maker(args, body_lines, return_value):
    ldict = {}
    defline = f"def func({', '.join(args)}):\n\t"
    body = '\n\t'.join(body_lines)
    returnline = '\treturn ' + return_value
    exec(''.join((defline, body, returnline)), globals(), ldict)
    return ldict['func']


def real_factory(s_expression, parsed_txt):
    return func_maker(('f', 'D', 't', 'n'), [s_expression], parsed_txt)


def imag_factory(parsed_txt):
    func = func_maker(('real', 'D'), [], parsed_txt)

    def inner_func(real, D):
        real = wl_to_ev(real)
        out = func(real, D)
        return 0.00001 if out <= 0 else out  # prevent /0 in Lorentz

    return inner_func


def lorentz_factory(real_eq, imag_eq):
    def inner_func(wl):
        real = real_eq(f, D, t, n)
        efficiency = imag_eq(real, D)
        return Lorentz(wl, real, efficiency)

    return inner_func


def annotate_factory(real_eq, imag_eq):
    def inner_func():
        real = real_eq(f, D, t, n)
        efficiency = imag_eq(real, D)
        return real, efficiency

    return inner_func


def make_graph_widget(folder):
    modes = defaultdict(dict)

    for file in (folder / 'real equations').iterdir():
        mode = file_to_mode_name(file)

        with open(file, 'r') as eq_file:
            s_expression = eq_file.readline()
            parsed_txt = ''.join(eq_file.read().splitlines())
            modes[f'{mode} mode']['real'] = real_factory(
                s_expression, parsed_txt)

    for file in (folder / 'imag equations').iterdir():
        mode = file_to_mode_name(file)
        with open(file, 'r') as eq_file:
            parsed_txt = ''.join(eq_file.read().splitlines())
            modes[f'{mode} mode']['imag'] = imag_factory(parsed_txt)

    for mode in modes.values():
        mode['Lorentz'] = lorentz_factory(mode['real'], mode['imag'])
        mode['annotate'] = annotate_factory(mode['real'], mode['imag'])

    def xlim_func():
        reals = [mode['real'](f, D, t, n) for mode in modes.values()]
        return min(reals) * 0.8, max(reals) * 1.1

    return GraphWithPinAndClearButtons(modes,
                                       xlim_func,
                                       title=folder.stem,
                                       resolution=100)


if __name__ == '__main__':

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    app.setStyleSheet(qdarkstyle.load_stylesheet())

    f = Parameter('Facet', 0.3, Min=0.1, Max=0.4)
    D = Parameter('Diameter', 80., Min=40, Max=100, units='nm')
    t = Parameter('gap thickness', 1., Min=0.75, Max=6., units='nm')
    n = Parameter(
        'gap refractive index',
        1.5,
        Min=1.,
        Max=2.,
    )

    root = Path('geometries')
    graphs = []
    for folder in root.iterdir():
        if folder.is_dir():
            graphs.append(make_graph_widget(folder))

    live_plotter = LivePlotWindow(graphs, (f, D, t, n))
    app.exec_()
