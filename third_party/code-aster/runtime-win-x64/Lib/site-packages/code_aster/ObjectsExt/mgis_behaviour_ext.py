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
:py:class:`MGISBehaviour` --- MGISBehaviour object
**************************************************
"""


from ..Objects import MGISBehaviour
from ..Objects.Serialization import InternalStateBuilder
from ..Utilities import injector


class MGISBehaviourStateBuilder(InternalStateBuilder):
    """Class that returns the internal state of a *MGISBehaviour*."""

    def save(self, behav):
        """Return the internal state of a *MGISBehaviour* to be pickled.

        Arguments:
            behav (*MGISBehaviour*): The *MGISBehaviour* object to be pickled.

        Returns:
            *InternalStateBuilder*: The internal state itself.
        """
        super().save(behav)
        self._st["internal"] = behav._internal_state()
        return self

    def restore(self, behav):
        """Restore the *DataStructure* content from the previously saved internal
        state.

        Arguments:
            behav (*DataStructure*): The *DataStructure* object to be restored.
        """
        super().restore(behav)
        libpath, bname = self._st["internal"]
        behav.setLibPath(libpath)
        behav.setBehaviourName(bname)


@injector(MGISBehaviour)
class ExtendedMGISBehaviour:
    cata_sdj = "SD.sd_compor_mgis.sd_compor_mgis"
    internalStateBuilder = MGISBehaviourStateBuilder
