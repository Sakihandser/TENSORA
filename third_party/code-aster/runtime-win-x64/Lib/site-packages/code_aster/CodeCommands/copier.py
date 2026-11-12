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


from ..Objects import Mesh, Model, PrestressingCable, Result, Table, TimesList
from ..Supervis import ExecuteCommand


class Copier(ExecuteCommand):
    """Command COPIER"""

    command_name = "COPIER"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        other = keywords["CONCEPT"]
        if isinstance(other, PrestressingCable):
            self._result = PrestressingCable(
                other.getModel(), other.getMaterialField(), other.getElementaryCharacteristics()
            )
        elif isinstance(other, Result):
            # do not support several models
            mesh = other.getModel().getMesh()
            self._result = type(other)()
            self._result.setMesh(mesh)
        elif isinstance(other, Model):
            self._result = Model(other.getMesh())
        else:
            self._result = type(other)()

    def post_exec(self, keywords):
        """Post execution the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        other = keywords["CONCEPT"]

        if isinstance(other, Result):
            indexes = other.getIndexes()
            for i in indexes:
                if other.hasModel(i):
                    self._result.setModel(other.getModel(i), i)
                if other.hasMaterialField(i):
                    self._result.setMaterialField(other.getMaterialField(i), i)
                if other.hasElementaryCharacteristics(i):
                    self._result.setElementaryCharacteristics(
                        other.getElementaryCharacteristics(i), i
                    )
                if other.hasListOfLoads(i):
                    self._result.setListOfLoads(other.getListOfLoads(i), i)

        if isinstance(other, (Result, Mesh, PrestressingCable, Table)):
            self._result.build()
        if isinstance(other, TimesList):
            self._result.stepper = other.stepper.copy()

    def add_dependencies(self, keywords):
        """Do not keep any references to original objects.

        Arguments:
            keywords (dict): User's keywords.
        """


COPIER = Copier.run
