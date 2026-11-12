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
:py:class:`ModeResult` --- Modes result
****************************************************
"""

from libaster import ModeResult

from ..Utilities import injector
from ..ObjectsExt.result_ext import ResultStateBuilder


class ModeResultStateBuilder(ResultStateBuilder):
    """Class that returns the internal state of a *ModeResult* to be pickled."""

    def save(self, mode):
        """Return the internal state of a *ModeResult* to be pickled.

        Arguments:
            mode (*ModeResult*): The *ModeResult* object to be pickled.

        Returns:
            *InternalStateBuilder*: The internal state itself.
        """
        self._st["numbering"] = mode.getDOFNumbering()
        self._st["stiff"] = mode.getStiffnessMatrix()
        self._st["mass"] = mode.getMassMatrix()
        super().save(mode)
        return self

    def restore(self, mode):
        """Restore the *ModeResult* content from the previously saved internal
        state.

        Arguments:
            mode (*ModeResult*): The *DataStructure* object to be restored.
        """
        mode.setDOFNumbering(self._st["numbering"])
        mode.setStiffnessMatrix(self._st["stiff"])
        mode.setMassMatrix(self._st["mass"])
        super().restore(mode)


@injector(ModeResult)
class ExtentedModeResult:
    """Object for ModeResult."""

    cata_sdj = "SD.sd_resultat.sd_resultat"
    internalStateBuilder = ModeResultStateBuilder
