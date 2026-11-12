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


from ..Objects import Mesh, SuperMesh
from ..Supervis import ExecuteCommand


class MeshAssembler(ExecuteCommand):
    """Command that creates the :class:`~code_aster.Objects.Mesh`"""

    command_name = "ASSE_MAILLAGE"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        if keywords["OPERATION"] == "SOUS_STR":
            self._result = SuperMesh()
        else:
            self._result = Mesh()

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """

        self._result.build()
        if keywords["OPERATION"] == "SOUS_STR":
            for mesh in (keywords["MAILLAGE_1"], keywords["MAILLAGE_2"]):
                if type(mesh) == SuperMesh:
                    for macr_elem in mesh.getDynamicMacroElements():
                        self._result.addDynamicMacroElement(macr_elem)
                    for macr_elem in mesh.getStaticMacroElements():
                        self._result.addStaticMacroElement(macr_elem)


ASSE_MAILLAGE = MeshAssembler.run
