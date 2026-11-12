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


from ..Supervis import ExecuteCommand, loop_on_dsdict


@loop_on_dsdict("RESULTAT")
class ComputeAdditionalField(ExecuteCommand):
    """Command that computes additional fields in a
    :class:`~code_aster.Objects.Result`.
    """

    command_name = "CALC_CHAMP"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        if "reuse" in keywords:
            self._result = keywords["reuse"]
        else:
            self._result = type(keywords["RESULTAT"])()

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        new_model = keywords.get("MODELE")
        if not new_model:
            previous = keywords["RESULTAT"].getModels()
            new_model = previous[-1] if previous else None
        if not new_model:
            try:
                new_model = keywords["RESULTAT"].getDOFNumbering().getModel()
            except AttributeError:
                pass
        if new_model:
            self._result.setModel(new_model, exists_ok=True)

        if "reuse" not in keywords:
            try:
                dofNume = keywords["RESULTAT"].getDOFNumbering()
                self._result.setDOFNumbering(dofNume)
            except AttributeError:
                pass

            for rank in self._result.getIndexes():
                if keywords["RESULTAT"].hasListOfLoads(rank):
                    list_of_load = keywords["RESULTAT"].getListOfLoads(rank)
                    self._result.setListOfLoads(list_of_load, rank)

            for fED in keywords["RESULTAT"].getFiniteElementDescriptors():
                self._result.addFiniteElementDescriptor(fED)
            for fOND in keywords["RESULTAT"].getEquationNumberings():
                self._result.addEquationNumbering(fOND)
            mesh = keywords["RESULTAT"].getMesh()
            if mesh:
                self._result.setMesh(mesh)

        self._result.build()

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Do not keep reference to RESULTAT (if not reused).

        Arguments:
            keywords (dict): User's keywords.
        """
        super().add_dependencies(keywords)
        self.remove_dependencies(keywords, "RESULTAT")
        self.remove_dependencies(keywords, "CHAM_UTIL", "FORMULE")
        if "reuse" not in keywords:
            # only if there is only one model, fieldmat...
            try:
                models = keywords["RESULTAT"].getModels()
                for model in models:
                    self._result.addDependency(model)
            except RuntimeError:
                pass
            try:
                fieldmats = keywords["RESULTAT"].getMaterialFields()
                for fieldmat in fieldmats:
                    self._result.addDependency(fieldmat)
            except RuntimeError:
                pass
            try:
                elems = keywords["RESULTAT"].getAllElementaryCharacteristics()
                for elem in elems:
                    self._result.addDependency(elem)
            except RuntimeError:
                pass


CALC_CHAMP = ComputeAdditionalField.run
