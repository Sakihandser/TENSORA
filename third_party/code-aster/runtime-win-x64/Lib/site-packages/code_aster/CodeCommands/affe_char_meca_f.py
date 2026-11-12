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


from ..CodeCommands.defi_constante import DEFI_CONSTANTE
from ..Objects import ConnectionMesh, MechanicalLoadFunction, Model, ParallelMechanicalLoadFunction
from ..Supervis import ExecuteCommand
from ..Utilities import force_list
from .affe_char_meca import MechanicalLoadDefinition, _getGroups


class MechanicalLoadFunctionDefinition(ExecuteCommand):
    """Command that defines :class:`~code_aster.Objects.MechanicalLoadFunc`."""

    command_name = "AFFE_CHAR_MECA_F"

    def adapt_syntax(self, keywords):
        """Hook to adapt syntax *after* syntax checking.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """
        if "PRE_EPSI" not in keywords:
            return
        pre_epsi = force_list(keywords["PRE_EPSI"])
        for fact in pre_epsi:
            vect_n = fact.get("VECT_N", [])
            # Replace a list of real by constant functions
            for ic, value in enumerate(vect_n):
                fact[f"VECT_N{ic+1}"] = DEFI_CONSTANTE(VALE=value)
        # check syntax after changing the keywords
        self.check_syntax(keywords)

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        model = keywords["MODELE"]
        l_neum = MechanicalLoadDefinition._hasNeumannLoadings(keywords)
        l_diri = MechanicalLoadDefinition._hasDirichletLoadings(keywords)
        if not model.getMesh().isParallel():
            self._result = MechanicalLoadFunction(model)
        else:
            if l_neum:
                if l_diri:
                    raise TypeError(
                        "Not allowed to mix up Dirichlet and Neumann loadings in the same parallel AFFE_CHAR_MECA_F"
                    )
                else:
                    self._result = MechanicalLoadFunction(model)
            if MechanicalLoadDefinition._hasOnlyDDL_IMPO(keywords):
                self._result = MechanicalLoadFunction(model)

    def exec_(self, keywords):
        """Override default _exec in case of parallel load"""
        if isinstance(self._result, MechanicalLoadFunction):
            super(MechanicalLoadFunctionDefinition, self).exec_(keywords)
        else:
            model = keywords.pop("MODELE")
            nodeGroups, cellGroups = _getGroups(self._cata, keywords)
            connectionMesh = ConnectionMesh(model.getMesh(), nodeGroups, cellGroups)

            connectionModel = Model(connectionMesh)
            connectionModel.setFrom(model)

            keywords["MODELE"] = connectionModel
            partialMechanicalLoad = AFFE_CHAR_MECA_F(**keywords)
            keywords["MODELE"] = model
            self._result = ParallelMechanicalLoadFunction(partialMechanicalLoad, model)

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


AFFE_CHAR_MECA_F = MechanicalLoadFunctionDefinition.run
