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


from ..Objects import ModeResult
from ..Supervis import ExecuteCommand


class CalcErcDyn(ExecuteCommand):
    """Command that creates the :class:`~code_aster.Objects.ModeResult`"""

    command_name = "CALC_ERC_DYN"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """

        self._result = ModeResult()

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        matrRigi = keywords["MATR_RIGI"]
        dofNum = matrRigi.getDOFNumbering()
        self._result.setModel(dofNum.getModel())
        for i in dofNum.getFiniteElementDescriptors():
            self._result.addFiniteElementDescriptor(i)
        mesh = matrRigi.getMesh()
        if mesh is not None:
            self._result.setMesh(mesh)


CALC_ERC_DYN = CalcErcDyn.run
