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
:py:class:`EquationNumbering` --- Numbering of equation
********************************************************************
"""

from libaster import EquationNumbering
from ..Objects.Serialization import InternalStateBuilder
from ..Utilities import injector


class EquationNumberingStateBuilder(InternalStateBuilder):
    """Class that returns the internal state of a *EquationNumbering*."""

    def save(self, nume):
        """Return the internal state of a *Result* to be pickled.

        Arguments:
            nume (*EquationNumbering*): The *EquationNumbering* object to be pickled.

        Returns:
            *InternalStateBuilder*: The internal state itself.
        """
        super().save(nume)
        self._st["model"] = nume.getModel()
        self._st["mesh"] = nume.getMesh()
        return self

    def restore(self, nume):
        """Restore the *DataStructure* content from the previously saved internal
        state.

        Arguments:
            nume (*DataStructure*): The *DataStructure* object to be restored.
        """
        super().restore(nume)
        if self._st["model"]:
            nume.setModel(self._st["model"])
        if self._st["mesh"]:
            nume.setMesh(self._st["mesh"])


@injector(EquationNumbering)
class ExtendedEquationNumbering:
    cata_sdj = "SD.sd_nume_equa.sd_nume_equa"
    internalStateBuilder = EquationNumberingStateBuilder
