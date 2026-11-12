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
:py:class:`DynamicMacroElement` --- Assignment of material properties on mesh
************************************************************************
"""

import numpy

from libaster import DynamicMacroElement

from ..Utilities import injector


def VALE_triang2array(dict_VALM):
    # stockage symetrique ou non (triang inf+sup)
    sym = len(dict_VALM) == 1
    triang_sup = numpy.array(dict_VALM[0])
    dim = round((1 + 8 * len(triang_sup)) ** 0.5 - 1) // 2
    if sym:
        triang_inf = triang_sup
    else:
        triang_inf = numpy.array(dict_VALM[1])
    valeur = numpy.zeros([dim, dim])
    for i in range(1, dim + 1):
        for j in range(1, i + 1):
            k = i * (i - 1) // 2 + j
            valeur[i - 1, j - 1] = triang_inf[k - 1]
            valeur[j - 1, i - 1] = triang_sup[k - 1]
    return valeur


@injector(DynamicMacroElement)
class ExtendedDynamicMacroElement:
    cata_sdj = "SD.sd_macr_elem_dyna.sd_macr_elem_dyna"

    def EXTR_MATR_GENE(self, typmat):
        if typmat == "MASS_GENE":
            matrix = self.getGeneralizedMassMatrix()
        elif typmat == "RIGI_GENE":
            matrix = self.getGeneralizedStiffnessMatrix()
        elif typmat == "AMOR_GENE":
            matrix = self.getGeneralizedDampingMatrix()
        else:
            raise TypeError("Le type de la matrice est incorrect")

        return VALE_triang2array(matrix)
