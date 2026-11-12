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
:py:class:`ParallelDOFNumbering` --- Parallel DOFNumbering definition
*****************************************
"""

from ..Objects import ParallelDOFNumbering

from ..Utilities import injector, force_list
import functools


@injector(ParallelDOFNumbering)
class ExtendedParallelDOFNumbering:
    cata_sdj = "SD.sd_nume_ddl.sd_nume_ddl"

    def __getinitargs__(self):
        """Returns the argument required to reinitialize a
        ParallelDOFNumbering object during unpickling.
        """
        return (self.getName(), self.getEquationNumbering(), self.getModel())

    def getDOFsAssociatedToComponent(self, component: str, local=True):
        """Return the rows associated to the input component.

        Arguments:
            component (str): the name of the component (aka degree of freedom)
        """
        if component == "LAGR":
            return self.getLagrangeDOFs(local)
        # TODO fix after issue33341
        if component.startswith("LAGR:"):
            ret = []
            for dof in self.getLagrangeDOFs(local):
                if self.getComponentFromDOF(dof, local) == component:
                    ret.append(dof)
            return ret
        available_components = self.getComponents()
        if component not in available_components:
            raise ValueError(f"Component {component} is not in {available_components}")

        return self.getEquationNumbering().getDOFsWithDescription(
            force_list(component), local=local
        )[-1]

    def getDictComponentsToDOFs(self, local=True):
        """Return the dictionary with the available components as keys and the rows as values."""
        ret = {}
        for cmp in self.getComponents():
            ret[cmp] = self.getDOFsAssociatedToComponent(cmp, local)
        return ret
