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


from ..Objects import FieldOnCellsReal, FieldOnNodesReal, ConstantFieldOnCellsReal
from ..Supervis import ExecuteCommand


class FieldReader(ExecuteCommand):
    """Command that creates fields that may be
    :class:`~code_aster.Objects.FieldOnCellsReal` or
    :class:`~code_aster.Objects.FieldOnNodesReal` or
    :class:`~code_aster.Objects.ConstantFieldOnCellsReal`."""

    command_name = "LIRE_CHAMP"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        # Analysis of type of field
        location, _, typ = keywords["TYPE_CHAM"].split("_")

        if location == "CART":
            if "MAILLAGE" in keywords:
                mesh = keywords["MAILLAGE"]
            else:
                mesh = keywords["MODELE"].getMesh()

            if typ == "R":
                self._result = ConstantFieldOnCellsReal(mesh)
            else:
                raise NotImplementedError("Output for LIRE_CHAMP not defined")

        elif location == "NOEU":
            if typ == "R":
                self._result = FieldOnNodesReal()
            else:
                raise NotImplementedError("Output for LIRE_CHAMP not defined")

        else:
            if typ == "R":
                self._result = FieldOnCellsReal()
            else:
                raise NotImplementedError("Output for LIRE_CHAMP not defined")

    def post_exec(self, keywords):
        """Post-treatments of the command.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        # Analysis of type of field
        location, _, _ = keywords["TYPE_CHAM"].split("_")

        if location == "NOEU":
            self._result.build(keywords["MAILLAGE"])
        elif location[:2] == "EL":
            model = keywords.get("MODELE")
            assert model, "MODELE is required!"
            fed = model.getFiniteElementDescriptor()
            self._result.build([fed])

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Arguments:
            keywords (dict): User's keywords.
        """
        super().add_dependencies(keywords)
        self.remove_dependencies(keywords, "MAILLAGE")
        self.remove_dependencies(keywords, "MODELE")


LIRE_CHAMP = FieldReader.run
