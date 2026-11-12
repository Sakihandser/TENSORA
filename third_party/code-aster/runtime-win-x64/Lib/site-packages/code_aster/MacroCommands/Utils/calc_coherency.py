# coding=utf-8
# --------------------------------------------------------------------
# Copyright (C) 1991 - 2026 - EDF - www.code-aster.org
# This file is part of code_aster.
#
# code_aster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# code_aster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with code_aster.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

"""
Maquette calcul de fonctions de coherence

"""

from math import pi

import numpy as np


def calc_cohefromdata(acce1, acce2, dt, Mm):
    # IN : acce1,acce2: accelerograms at station1 and stationa 2 (matrices: nbsignal x nbstep),
    # dt: time step    Mm : points smoothing window
    # OUT : coherency function gam(wm)
    acce_size = np.array(acce1).shape
    nbval = acce_size[0]
    Nf = acce_size[1]
    TT = Nf * dt  # %duree du signal  (5s pour N=1000)
    OM = pi / dt  # % frequence de coupure
    dw = 2.0 * OM / Nf  # % pas de frequence
    # % discretisation freq
    w = np.arange(-OM + 0.5 * dw, OM, dw)
    # %  smoothening parameters and filter
    m = np.arange(-Mm, Mm + 1, 1)
    wm = w[Mm : Nf - Mm]
    N2 = len(wm)
    filt = 0.54 - 0.46 * np.cos(pi * (m + Mm) / Mm)
    dt2 = pi / (w[Nf - Mm - 1] + 0.5 * dw)
    t2 = np.arange(0.0, N2 * dt2, dt2)

    # FFT
    Xw1 = np.fft.fft(np.array(acce1), Nf, 1) * dt
    Xw2 = np.fft.fft(np.array(acce2), Nf, 1) * dt

    SX1 = []
    SX2 = []
    SX12 = []
    # %spectral estimate
    fact = 1.0 / (2.0 * pi) / TT
    for iii in range(nbval):
        SX12.append(fact * Xw1[iii] * np.conj(Xw2[iii]))
        SX1.append(np.real(fact * Xw1[iii] * np.conj(Xw1[iii])))
        SX2.append(np.real(fact * Xw2[iii] * np.conj(Xw2[iii])))

    fact = 1.0 / 1.08 / Mm
    Sxf1 = []
    for line in SX1:
        term = np.fft.fftshift(line)
        out = []
        for ii in range(Mm, Nf - Mm):
            nvale_m = m + ii
            out.append(fact * np.sum(term[nvale_m[0] : nvale_m[-1] + 1] * filt))
        Sxf1.append(out)

    Sxf2 = []
    for line in SX2:
        term = np.fft.fftshift(line)
        out = []
        for ii in range(Mm, Nf - Mm):
            nvale_m = m + ii
            out.append(fact * np.sum(term[nvale_m[0] : nvale_m[-1] + 1] * filt))
        Sxf2.append(out)

    Sxf12 = []
    for line in SX12:
        term = np.fft.fftshift(line)
        out = []
        for ii in range(Mm, Nf - Mm):
            nvale_m = m + ii
            out.append(fact * np.sum(term[nvale_m[0] : nvale_m[-1] + 1] * filt))
        Sxf12.append(out)

    # coherency
    gamw = []
    for i2 in range(nbval):
        gami2 = Sxf12[i2] / np.sqrt(np.array(Sxf1[i2]) * np.array(Sxf2[i2]))
        gamw.append(gami2)
    return wm / 2.0 / pi, (np.mean(gamw, 0))
