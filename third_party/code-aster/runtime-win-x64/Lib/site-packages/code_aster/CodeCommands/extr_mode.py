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


class ExtrMode(ExecuteCommand):
    """EXTR_MODE command"""

    command_name = "EXTR_MODE"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        mode = keywords["FILTRE_MODE"][0]["MODE"]
        if mode.getType() == "MODE_MECA":
            self._result = ModeResult()
        else:
            self._result = type(mode)()

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        mode = keywords["FILTRE_MODE"][0]["MODE"]
        try:
            self._result.setDOFNumbering(mode.getDOFNumbering())
        except:
            pass
        if isinstance(mode, ModeResult):
            self._result.setMesh(mode.getMesh())
            model = mode.getModel()
            if model is not None:
                self._result.setModel(model)
            stiffMat = mode.getStiffnessMatrix()
            if stiffMat is not None:
                self._result.setStiffnessMatrix(stiffMat)
            for fED in mode.getFiniteElementDescriptors():
                self._result.addFiniteElementDescriptor(fED)
            for fOND in mode.getEquationNumberings():
                self._result.addEquationNumbering(fOND)
            self._result.setDOFNumbering(mode.getDOFNumbering())
            self._result.build()


EXTR_MODE = ExtrMode.run
