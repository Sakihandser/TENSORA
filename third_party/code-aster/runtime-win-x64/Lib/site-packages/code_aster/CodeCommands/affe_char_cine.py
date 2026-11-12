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


from ..Objects import AcousticDirichletBC, MechanicalDirichletBC, ThermalDirichletBC, SyntaxSaver
from ..Supervis import ExecuteCommand


class DirichletBCDefinition(ExecuteCommand):
    """Command that defines :class:`~code_aster.Objects.DirichletBC`."""

    command_name = "AFFE_CHAR_CINE"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        model = keywords["MODELE"]
        if keywords.get("MECA_IMPO") is not None:
            self._result = MechanicalDirichletBC(model)
        elif keywords.get("THER_IMPO") is not None:
            self._result = ThermalDirichletBC(model)
        elif keywords.get("ACOU_IMPO") is not None:
            self._result = AcousticDirichletBC(model)
        elif keywords.get("EVOL_IMPO") is not None:
            if keywords.get("EVOL_IMPO").getType() in ("EVOL_ELAS", "EVOL_NOLI"):
                self._result = MechanicalDirichletBC(model)
            elif keywords.get("EVOL_IMPO").getType() == "EVOL_THER":
                self._result = ThermalDirichletBC(model)
            elif keywords.get("EVOL_IMPO").getType() == "EVOL_ACOU":
                self._result = AcousticDirichletBC(model)
            else:
                raise NotImplementedError("Must be implemented")
        else:
            raise NotImplementedError("Must be implemented")
        if keywords.get("SYNTAXE") == "OUI":
            toSave = SyntaxSaver(self.command_name, 101, keywords)
            self._result.setSyntax(toSave)

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Arguments:
            keywords (dict): User's keywords.
        """
        super().add_dependencies(keywords)
        self.remove_dependencies(keywords, "MODELE")


AFFE_CHAR_CINE = DirichletBCDefinition.run
