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


from ..Objects import EmpiricalModeResult
from ..Supervis import ExecuteCommand
from ..Utilities import force_list


class ReducedBaseDefinition(ExecuteCommand):
    """Command that creates the :class:`~code_aster.Objects.Mesh`"""

    command_name = "DEFI_BASE_REDUITE"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        if "reuse" in keywords:
            self._result = keywords["reuse"]
        else:
            self._result = EmpiricalModeResult()

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        model = None
        if keywords.get("OPERATION") == "TRONCATURE":
            model = keywords["MODELE_REDUIT"]
        else:
            if "reuse" in keywords:
                model = self._result.getModel()
            elif keywords.get("RESULTAT"):
                model = keywords["RESULTAT"].getModel()
            elif keywords.get("BASE"):
                model = keywords["BASE"].getModel()
        if model:
            self._result.setModel(model)
        else:
            matr_asse = keywords.get("MATR_ASSE")
            if matr_asse is not None:
                self._result.setMesh(force_list(matr_asse)[0]["MATRICE"].getMesh())
        self._result.build()


DEFI_BASE_REDUITE = ReducedBaseDefinition.run
