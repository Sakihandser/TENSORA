# coding: utf-8

# Copyright (C) 1991 - 2026  EDF www.code-aster.org
#
# This file is part of Code_Aster.
#
# Code_Aster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Code_Aster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Code_Aster.  If not, see <http://www.gnu.org/licenses/>.


from ..Objects import ThermalLoadFunction, ParallelThermalLoadFunction, ConnectionMesh, Model
from ..Supervis import ExecuteCommand
from .affe_char_ther import ThermalLoadDefinition, _getGroups


class ThermalLoadFunctionDefinition(ExecuteCommand):
    """Command that creates the :class:`~code_aster.Objects.ThermalLoadFunction`"""

    command_name = "AFFE_CHAR_THER_F"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        model = keywords["MODELE"]
        l_neum = ThermalLoadDefinition._hasNeumannLoadings(keywords)
        l_diri = ThermalLoadDefinition._hasDirichletLoadings(keywords)
        if not model.getMesh().isParallel():
            self._result = ThermalLoadFunction(model)
        else:
            if l_neum:
                if l_diri:
                    raise TypeError(
                        "Not allowed to mix up Dirichlet and Neumann \
                        loadings in the same parallel AFFE_CHAR_THER_F"
                    )
                else:
                    self._result = ThermalLoadFunction(model)

    def exec_(self, keywords):
        """Override default _exec in case of parallel load"""
        if isinstance(self._result, ThermalLoadFunction):
            super(ThermalLoadFunctionDefinition, self).exec_(keywords)
        else:
            model = keywords.pop("MODELE")
            nodeGroups, cellGroups = _getGroups(self._cata, keywords)
            connectionMesh = ConnectionMesh(model.getMesh(), nodeGroups, cellGroups)

            connectionModel = Model(connectionMesh)
            connectionModel.setFrom(model)

            keywords["MODELE"] = connectionModel
            partialThermalLoad = AFFE_CHAR_THER_F(**keywords)
            keywords["MODELE"] = model
            self._result = ParallelThermalLoadFunction(partialThermalLoad, model)

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """

        self._result.build()

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Arguments:
            keywords (dict): User's keywords.
        """
        super().add_dependencies(keywords)
        self.remove_dependencies(keywords, "MODELE")


AFFE_CHAR_THER_F = ThermalLoadFunctionDefinition.run
