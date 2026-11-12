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
:py:class:`GeneralizedDOFNumbering` --- GeneralizedDOFNumbering definition
*****************************************
"""

from libaster import GeneralizedDOFNumbering

from ..Utilities import injector
from ..Objects.Serialization import InternalStateBuilder


class GeneralizedDOFNumberingStateBuilder(InternalStateBuilder):
    """Class that returns the internal state of a *GeneralizedDOFNumbering*."""

    def save(self, result):
        """Return the internal state of a *GeneralizedDOFNumbering* to be pickled.

        Arguments:
            result (*GeneralizedDOFNumbering*): The *GeneralizedDOFNumbering* object to be pickled.

        Returns:
            *InternalStateBuilder*: The internal state itself.
        """
        super().save(result)
        self._st["model"] = result.getGeneralizedModel()
        self._st["base"] = result.getModalBasis()

        return self

    def restore(self, result):
        """Restore the *DataStructure* content from the previously saved internal
        state.

        Arguments:
            result (*DataStructure*): The *DataStructure* object to be restored.
        """
        super().restore(result)
        result.setGeneralizedModel(self._st["model"])
        result.setModalBasis(self._st["base"])


@injector(GeneralizedDOFNumbering)
class ExtendedGeneralizedDOFNumbering:
    cata_sdj = "SD.sd_nume_ddl_gene.sd_nume_ddl_gene"
    internalStateBuilder = GeneralizedDOFNumberingStateBuilder
