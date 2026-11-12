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

import numpy as np

from ...Messages import ASSERT
from ...Objects import SimpleFieldOnNodesReal, ThermalResult, ElasticResult


def createLocalTherResult(rmanager, resuglob):
    """Create the local relocalised thermal solution on the VER mesh.

    The local result is build by combining the global (homogeneus) solution
    at point P0 with the corrector fields.
    Point P0 is a point on the global mesh where the center of the VER is located.

    Args:
        rmanager (RelocManager): Object containing user's settings and correctors.
        resuglob (ThermalResult): The global solution.


    Returns:
        resuloc (ThermalResult): The local thermal solution.

    """
    ASSERT(resuglob is not None)
    ASSERT(isinstance(resuglob, ThermalResult))
    ASSERT(rmanager.corr_ther is not None)

    xyz_ver = rmanager.ver_mesh.getCoordinates().toNumpy().copy()

    evol_tp0, evol_gratp0 = rmanager.getP0TherGlobalEvol(resuglob)

    indexes = rmanager.getReducedIndexes(resuglob)

    resuloc = ThermalResult()
    resuloc.allocate(len(indexes))
    shiftidx = 0
    for i, no in enumerate(indexes):
        time = resuglob.getTime(no)
        idxresu = i + shiftidx

        arrays = rmanager.getThermalBulkArrays(evol_tp0[no])
        chi_1, chi_2, chi_3 = arrays
        dot_p_xyz = np.dot((xyz_ver - rmanager.shift), evol_gratp0[no]).reshape(-1, 1)
        dot_p_c1 = evol_gratp0[no][0] * chi_1
        dot_p_c2 = evol_gratp0[no][1] * chi_2
        dot_p_c3 = evol_gratp0[no][2] * chi_3
        treloc = evol_tp0[no] + dot_p_xyz + dot_p_c1 + dot_p_c2 + dot_p_c3

        sfreloc = SimpleFieldOnNodesReal(rmanager.ver_mesh, "TEMP_R", ["TEMP"], True)
        values, mask = sfreloc.toNumpy()
        mask[:, :] = True
        values[:, :] = treloc
        freloc = sfreloc.toFieldOnNodes()
        resuloc.setField(freloc, "TEMP", idxresu)
        resuloc.setTime(time, idxresu)

    return resuloc


def createLocalElasResult(rmanager, resuglob):
    """Create the local relocalised elastic solution on the VER mesh.

    The local result is built by combining the global (homogeneus) solution
    at point P0 with the corrector fields.
    Point P0 is a point on the global mesh where the center of the VER is located.

    The internal pressure must be given by user.

    Args:
        rmanager (RelocManager): Object containing user's settings and correctors.
        resuglob (ElasticResult): The global elastic solution.


    Returns:
        resuloc (ElasticResult): The local elastic solution.

    """
    ASSERT(resuglob is not None)
    ASSERT(isinstance(resuglob, ElasticResult))
    ASSERT(rmanager.corr_meca is not None)

    xyz_ver = rmanager.ver_mesh.getCoordinates().toNumpy().copy()

    evol_dp0, evol_epsip0 = rmanager.getP0ElasGlobalEvol(resuglob)

    indexes = rmanager.getReducedIndexes(resuglob)

    resuloc = ElasticResult()
    resuloc.allocate(len(indexes))
    shiftidx = 1
    for i, no in enumerate(indexes):
        time = resuglob.getTime(no)
        idxresu = i + shiftidx

        tp0 = rmanager.evalTP0(time)

        arrays = rmanager.getElasticBulkArrays(tp0)
        chi_11, chi_22, chi_33, chi_12, chi_23, chi_31, chi_di, chi_pi = arrays

        dot_p_xyz = np.dot((xyz_ver - rmanager.shift), evol_epsip0[no])
        dot_p_c11 = evol_epsip0[no][0, 0] * chi_11
        dot_p_c22 = evol_epsip0[no][1, 1] * chi_22
        dot_p_c33 = evol_epsip0[no][2, 2] * chi_33
        # Le coefficient 2.0 car la déformation imposée dans CALC_MATE_HOMO est 0.5
        dot_p_c12 = 2.0 * evol_epsip0[no][0, 1] * chi_12
        dot_p_c23 = 2.0 * evol_epsip0[no][1, 2] * chi_23
        dot_p_c31 = 2.0 * evol_epsip0[no][0, 2] * chi_31
        dot_p_dil = -1.0 * (tp0 - rmanager.temp_ref) * chi_di
        dot_p_pin = rmanager.pres_int(time) * chi_pi

        dreloc = (
            evol_dp0[no]
            + dot_p_xyz
            + dot_p_c11
            + dot_p_c22
            + dot_p_c33
            + dot_p_c12
            + dot_p_c23
            + dot_p_c31
            + dot_p_dil
            + dot_p_pin
        )

        sfreloc = SimpleFieldOnNodesReal(rmanager.ver_mesh, "DEPL_R", ["DX", "DY", "DZ"], True)
        values, mask = sfreloc.toNumpy()
        mask[:, :] = True
        values[:, :] = dreloc
        freloc = sfreloc.toFieldOnNodes()
        resuloc.setField(freloc, "DEPL", idxresu)
        resuloc.setTime(time, idxresu)

    return resuloc
