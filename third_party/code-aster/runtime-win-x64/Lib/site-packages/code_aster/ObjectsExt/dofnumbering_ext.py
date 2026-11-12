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
:py:class:`DOFNumbering` --- DOFNumbering definition
*****************************************
"""

from libaster import DOFNumbering

from ..Utilities import injector
import functools
from ..Objects.Serialization import InternalStateBuilder


class DOFNumberingStateBuilder(InternalStateBuilder):
    """Class that returns the internal state of a *DOFNumbering*."""

    def save(self, obj):
        """Return the internal state of a *DOFNumbering* to be pickled.

        Arguments:
            obj (*DOFNumbering*): The *DOFNumbering* object to be pickled.

        Returns:
            *InternalStateBuilder*: The internal state itself.
        """
        super().save(obj)
        self._st["feds"] = obj.getFiniteElementDescriptors()
        return self

    def restore(self, obj):
        """Restore the *DOFNumbering* content from the previously saved internal
        state.

        Arguments:
            obj (*DOFNumbering*): The *DOFNumbering* object to be restored.
        """
        super().restore(obj)
        if self._st["feds"]:
            obj.setFiniteElementDescriptors(self._st["feds"])


@injector(DOFNumbering)
class ExtendedDOFNumbering:
    cata_sdj = "SD.sd_nume_ddl.sd_nume_ddl"
    internalStateBuilder = DOFNumberingStateBuilder

    def __getinitargs__(self):
        """Returns the argument required to reinitialize a
        DOFNumbering object during unpickling.
        """
        return (self.getName(), self.getEquationNumbering(), self.getModel())

    def getDOFsAssociatedToComponent(self, component: str, local=True):
        """Return the rows associated to the input component.

        Arguments:
            component (str): the name of the component (aka degree of freedom)
        """
        available_components = self.getComponents()
        if component not in available_components:
            raise ValueError(f"Component {component} is not in {available_components}")
        return self.getEquationNumbering().getDOFsWithDescription([component], local=local)[-1]

    def getDictComponentsToDOFs(self, local=True):
        """Return the dictionary with the available components as keys and the associated DOFs as values."""
        ret = {}
        for cmp in self.getComponents():
            ret[cmp] = self.getDOFsAssociatedToComponent(cmp, local)
        return ret
