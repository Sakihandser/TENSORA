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


from ..Objects import FieldOnNodesReal, FieldOnNodesComplex
from ..Supervis import ExecuteCommand


class SolveLinearSystem(ExecuteCommand):
    """Command that solves :class:`~code_aster.Objects.AssemblyMatrix`."""

    command_name = "RESOUDRE"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """

        if keywords["MATR"].getType().endswith("_R"):
            self._result = FieldOnNodesReal()
        else:
            self._result = FieldOnNodesComplex()

    def post_exec(self, keywords):
        """Post-execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """

        rhs = keywords.get("CHAM_NO")  # Right Hand Side

        mesh = rhs.getMesh()
        desc = rhs.getDescription()
        if desc is not None:
            self._result.setDescription(desc)

        self._result.build(mesh)

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.
        No dependecy here
        Arguments:
            keywords (dict): User's keywords.
        """


RESOUDRE = SolveLinearSystem.run
