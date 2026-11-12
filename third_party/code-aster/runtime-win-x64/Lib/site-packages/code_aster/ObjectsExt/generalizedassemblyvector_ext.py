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
:py:class:`GeneralizedAssemblyVectorOnMesh` --- Assignment of material properties on mesh
************************************************************************
"""

import numpy

from libaster import GeneralizedAssemblyVectorComplex, GeneralizedAssemblyVectorReal

from ..Utilities import injector


@injector(GeneralizedAssemblyVectorComplex)
class ExtendedGeneralizedAssemblyVectorComplex:
    cata_sdj = "SD.sd_cham_gene.sd_cham_gene"

    def EXTR_VECT_GENE(self):
        """Return the vector values as `numpy.array`.

        Returns:
           numpy.array: vector values associated at each generalized dof
        """
        return numpy.array(self.getValues())

    def RECU_VECT_GENE(self, vecteur):
        """Set the vector values.

        Arguments:
           vecteur (list[complex]): values associated at each generalized dof"""
        self.setValues(vecteur)


@injector(GeneralizedAssemblyVectorReal)
class ExtendedGeneralizedAssemblyVectorReal:
    cata_sdj = "SD.sd_cham_gene.sd_cham_gene"

    def EXTR_VECT_GENE(self):
        """Return the vector values as `numpy.array`.

        Returns:
           numpy.array: vector values associated at each generalized dof
        """
        return numpy.array(self.getValues())

    def RECU_VECT_GENE(self, vecteur):
        """Set the vector values.

        Arguments:
           vecteur (list[float]): values associated at each generalized dof"""
        self.setValues(vecteur)
