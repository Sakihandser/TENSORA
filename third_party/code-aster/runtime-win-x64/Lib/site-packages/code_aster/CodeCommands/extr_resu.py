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


from ..Supervis import ExecuteCommand


class ExtrResu(ExecuteCommand):
    """Command EXTR_RESU"""

    command_name = "EXTR_RESU"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        self._result = type(keywords["RESULTAT"])()

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        resultat = keywords["RESULTAT"]
        restreint = keywords.get("RESTREINT")
        mesh, model, mate, cara_elem = None, None, None, None
        if restreint:
            if "MODELE" in restreint:
                model = restreint["MODELE"]
                mesh = model.getMesh()
            if "MAILLAGE" in restreint:
                mesh = restreint["MAILLAGE"]
            if "CHAM_MATER" in restreint:
                mate = restreint["CHAM_MATER"]
            if "CARA_ELEM" in restreint:
                cara_elem = restreint["CARA_ELEM"]
        else:
            model = resultat.getModel()
            if model is not None:
                mesh = model.getMesh()
            else:
                mesh = resultat.getMesh()
            mate = resultat.getMaterialField()
            cara_elem = resultat.getElementaryCharacteristics()

        if model is not None:
            self._result.setModel(model)
        if mesh is not None:
            self._result.setMesh(mesh)
        if mate is not None:
            self._result.setMaterialField(mate)
        if cara_elem is not None:
            self._result.setElementaryCharacteristics(cara_elem)

        self._result.build()

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Arguments:
            keywords (dict): User's keywords.
        """
        super().add_dependencies(keywords)
        self.remove_dependencies(keywords, "RESULTAT")


EXTR_RESU = ExtrResu.run
