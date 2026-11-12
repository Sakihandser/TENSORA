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


class ModalBasisDef(ExecuteCommand):
    """Command that creates the :class:`~code_aster.Objects.ModalBasis`"""

    command_name = "DEFI_BASE_MODALE"

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

        classique = keywords.get("CLASSIQUE")
        ritz = keywords.get("RITZ")
        diag = keywords.get("DIAG_MASS")
        ortho = keywords.get("ORTHO_BASE")

        if classique is not None:

            mode_meca = classique[0]["MODE_MECA"][0]
            self._result.setStructureInterface(classique[0]["INTERF_DYNA"])
            self._result.setDOFNumbering(mode_meca.getDOFNumbering())
            model = mode_meca.getModel()
            if model is not None:
                self._result.setModel(model)
            mesh = mode_meca.getMesh()
            if mesh is not None:
                self._result.setMesh(mesh)
            for fED in mode_meca.getFiniteElementDescriptors():
                self._result.addFiniteElementDescriptor(fED)
            for fOND in mode_meca.getEquationNumberings():
                self._result.addEquationNumbering(fOND)

        elif ritz is not None:
            if keywords.get("INTERF_DYNA") is not None:
                self._result.setStructureInterface(keywords.get("INTERF_DYNA"))
            if keywords.get("MATRICE") is not None:
                self._result.setDOFNumbering(keywords.get("MATRICE").getDOFNumbering())
            elif keywords.get("NUME_REF") is not None:
                self._result.setDOFNumbering(keywords.get("NUME_REF"))
            elif "BASE_MODALE" in ritz[0]:
                nume_ddl = ritz[0]["BASE_MODALE"].getDOFNumbering()
                self._result.setDOFNumbering(nume_ddl)

            if "MODE_MECA" in ritz[0]:
                mode_meca = ritz[0]["MODE_MECA"][0]
                model = mode_meca.getModel()
                if model is not None:
                    self._result.setModel(model)
                mesh = mode_meca.getMesh()
                if mesh is not None:
                    self._result.setMesh(mesh)
                else:
                    self._result.setMesh(mode_meca.getMesh())

                for fED in mode_meca.getFiniteElementDescriptors():
                    self._result.addFiniteElementDescriptor(fED)

                for fOND in mode_meca.getEquationNumberings():
                    self._result.addEquationNumbering(fOND)

                # EquationNumberings and DOFNumbering seem unused in this case
                if self._result.getDOFNumbering() is None:
                    self._result.setDOFNumbering(mode_meca.getDOFNumbering())

        elif diag is not None:
            self._result.setMesh(diag[0]["MODE_MECA"][0].getMesh())
            nume_ddl = diag[0]["MODE_MECA"][0].getDOFNumbering()
            self._result.setDOFNumbering(nume_ddl)

        elif ortho is not None:
            self._result.setDOFNumbering(ortho[0]["MATRICE"].getDOFNumbering())
            self._result.setMesh(ortho[0]["BASE"].getMesh())
        self._result.build()

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Arguments:
            keywords (dict): User's keywords.
        """
        super().add_dependencies(keywords)
        self.remove_dependencies(keywords, "RITZ", "MODE_MECA")


DEFI_BASE_MODALE = ModalBasisDef.run
