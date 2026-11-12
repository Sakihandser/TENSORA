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
:py:class:`ElementaryMatrix` --- Elementary Matrix
**************************************************
"""

import aster
from libaster import (
    ElementaryMatrixDisplacementComplex,
    ElementaryMatrixDisplacementReal,
    ElementaryMatrixPressureComplex,
    ElementaryMatrixTemperatureReal,
)

from ..Utilities import injector
from ..Objects.Serialization import InternalStateBuilder


class ElementaryMatrixStateBuilder(InternalStateBuilder):
    """Class that returns the internal state of a *ElementaryMatrix*."""

    def save(self, matr):
        """Return the internal state of a *ElementaryMatrix* to be pickled.

        Arguments:
            matr (*ElementaryMatrix*): The *ElementaryMatrix* object to be pickled.

        Returns:
            *InternalStateBuilder*: The internal state itself.
        """
        super().save(matr)
        self._st["model"] = matr.getModel()

        return self

    def restore(self, matr):
        """Restore the *DataStructure* content from the previously saved internal
        state.

        Arguments:
            matr (*DataStructure*): The *DataStructure* object to be restored.
        """
        super().restore(matr)
        matr.setModel(self._st["model"])
        matr.build()


@injector(ElementaryMatrixDisplacementReal)
class ExtendedElementaryMatrixDisplacementReal:
    cata_sdj = "SD.sd_matr_elem.sd_matr_elem"
    internalStateBuilder = ElementaryMatrixStateBuilder


@injector(ElementaryMatrixDisplacementComplex)
class ExtendedElementaryMatrixDisplacementComplex:
    cata_sdj = "SD.sd_matr_elem.sd_matr_elem"
    internalStateBuilder = ElementaryMatrixStateBuilder


@injector(ElementaryMatrixTemperatureReal)
class ExtendedElementaryMatrixTemperatureReal:
    cata_sdj = "SD.sd_matr_elem.sd_matr_elem"
    internalStateBuilder = ElementaryMatrixStateBuilder


@injector(ElementaryMatrixPressureComplex)
class ExtendedElementaryMatrixPressureComplex:
    cata_sdj = "SD.sd_matr_elem.sd_matr_elem"
    internalStateBuilder = ElementaryMatrixStateBuilder
