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


from ..Objects import Model, getModelings, Physics, SyntaxSaver
from ..Supervis import ExecuteCommand


class ModelAssignment(ExecuteCommand):
    """Command that creates the :class:`~code_aster.Objects.Model` by assigning
    finite elements on a :class:`~code_aster.Objects.Mesh`."""

    command_name = "AFFE_MODELE"

    def adapt_syntax(self, keywords):
        """Hook to adapt syntax *after* syntax checking.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """
        if keywords["MAILLAGE"].isParallel():
            keywords["DISTRIBUTION"] = {"METHODE": "CENTRALISE"}

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        self._result = Model(keywords["MAILLAGE"])

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """

        FED = self._result.getFiniteElementDescriptor()
        FED.build()

        allModelings = getModelings()
        for key in keywords:
            value = keywords[key]
            if key == "AFFE":
                for item in value:
                    phenom = None
                    model = None
                    grpma = []
                    for keyAffe in item:
                        value2 = item[keyAffe]
                        if keyAffe == "PHENOMENE":
                            if value2 == "MECANIQUE":
                                phenom = Physics.Mechanics
                            elif value2 == "THERMIQUE":
                                phenom = Physics.Thermal
                            elif value2 == "ACOUSTIQUE":
                                phenom = Physics.Acoustic
                            else:
                                assert False
                        elif keyAffe == "MODELISATION":
                            model = allModelings[value2]
                        elif keyAffe == "TOUT":
                            grpma = -1
                        elif keyAffe == "GROUP_MA":
                            grpma = value2
                    if grpma == -1:
                        self._result.addModelingOnMesh(phenom, model)
                    else:
                        assert grpma != []
                        for grpName in grpma:
                            try:
                                self._result.addModelingOnGroupOfCells(phenom, model, grpName)
                            except:
                                self._result.banBalancing()
            elif key == "AFFE_SOUS_STRUC":
                self._result.banBalancing()

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Arguments:
            keywords (dict): User's keywords.
        """

        # Add no dependencies since everything is mesh is already added


AFFE_MODELE = ModelAssignment.run
