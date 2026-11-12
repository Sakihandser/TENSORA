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


from ..Objects import (
    FieldOnCellsReal,
    FieldOnCellsLong,
    FieldOnCellsComplex,
    FieldOnCellsChar8,
    FieldOnNodesReal,
    FieldOnNodesLong,
    FieldOnNodesComplex,
    FieldOnNodesChar8,
    FullResult,
    ModeResult,
    ConstantFieldOnCellsReal,
)
from ..Supervis import ExecuteCommand
from ..Utilities import force_list


class FieldCreator(ExecuteCommand):
    """Command that creates fields that may be
    :class:`~code_aster.Objects.FieldOnNodesReal` or
    :class:`~code_aster.Objects.ConstantFieldOnCellsReal`."""

    command_name = "CREA_CHAMP"

    def _getMesh(self, keywords):
        mesh = keywords.get("MAILLAGE")
        model = keywords.get("MODELE")
        caraElem = keywords.get("CARA_ELEM")
        charge = keywords.get("CHARGE")
        resultat = keywords.get("RESULTAT")
        numeDdl = keywords.get("NUME_DDL")
        chamgd = keywords.get("CHAM_GD")
        fiss = keywords.get("FISSURE")
        chamF = keywords.get("CHAM_F")

        if mesh is None:
            if model is not None:
                mesh = model.getMesh()
            elif caraElem is not None:
                mesh = caraElem.getModel().getMesh()
            elif charge is not None:
                mesh = charge.getModel().getMesh()
            elif resultat is not None:
                mesh = resultat.getMesh()
            elif chamgd is not None:
                mesh = chamgd.getMesh()
            elif fiss is not None:
                mesh = fiss.getMesh()
            elif numeDdl is not None:
                mesh = numeDdl.getMesh()
            elif chamF is not None:
                mesh = chamF.getMesh()

        if mesh is None:
            for comb in force_list(keywords.get("COMB", [])):
                mesh = comb["CHAM_GD"].getMesh()
                if mesh:
                    break
        if mesh is None:
            for comb in force_list(keywords.get("ASSE", [])):
                mesh = comb["CHAM_GD"].getMesh()
                if mesh:
                    break

        return mesh

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        # Analysis of type of field
        location, quantity, typ = keywords["TYPE_CHAM"].split("_")

        mesh = self._getMesh(keywords)
        model = keywords.get("MODELE")
        resultat = keywords.get("RESULTAT")
        caraElem = keywords.get("CARA_ELEM")
        numeDdl = keywords.get("NUME_DDL")
        chamF = keywords.get("CHAM_F")

        if mesh.isParallel() and location == "NOEUD" and numeDdl is None:
            raise NameError("NUME_DDL is mandatory with ParallelMesh")

        if location == "CART":
            if mesh is None:
                raise NotImplementedError("Must have Mesh")
            self._result = ConstantFieldOnCellsReal(mesh)
        elif location == "NOEU":
            if typ == "R":
                self._result = FieldOnNodesReal()
            elif typ == "I":
                self._result = FieldOnNodesLong()
            elif typ == "C":
                self._result = FieldOnNodesComplex()
            elif typ == "F":
                self._result = FieldOnNodesChar8()
            else:
                raise NotImplementedError("Output for CREA_CHAMP not defined")
            if numeDdl is not None:
                self._result.setDescription(numeDdl.getEquationNumbering())
        else:
            if typ == "R":
                self._result = FieldOnCellsReal()
            elif typ == "I":
                self._result = FieldOnCellsLong()
            elif typ == "C":
                self._result = FieldOnCellsComplex()
            elif typ == "F":
                self._result = FieldOnCellsChar8()
            else:
                raise NotImplementedError("Output for CREA_CHAMP not defined")

        if location[:2] == "EL":
            chamF = keywords.get("CHAM_F")

            if model is None:
                if resultat is not None:
                    if isinstance(resultat, (FullResult, ModeResult)):
                        dofNum = resultat.getDOFNumbering()
                        if dofNum is not None:
                            model = dofNum.getModel()
                            if model is not None:
                                self._result.setDescription(model.getFiniteElementDescriptor())
                            fed = dofNum.getFiniteElementDescriptors()
                            self._result.setDescription(fed[0])

                    if resultat.getModel() is not None:
                        model = resultat.getModel()
                elif caraElem is not None:
                    model = caraElem.getModel()

            if model is not None:
                self._result.setDescription(model.getFiniteElementDescriptor())
            elif chamF is not None:
                self._result.setDescription(chamF.getDescription())

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """

        location, quantity, typ = keywords["TYPE_CHAM"].split("_")

        if location == "NOEU":
            if not self._result.getDescription():
                for comb in force_list(keywords.get("COMB", [])):
                    desc = comb["CHAM_GD"].getDescription()
                    if desc:
                        try:
                            self._result.setDescription(desc)
                        except:
                            pass
                        break

            try:
                self._result.build(self._getMesh(keywords))
            except:
                if "FISSURE" in keywords:
                    self._result.setMesh(keywords["FISSURE"].getAuxiliaryGrid())
        elif location[:2] == "EL":
            resultat = keywords.get("RESULTAT")
            fed = []
            if resultat:
                fed = resultat.getFiniteElementDescriptors()

            self._result.build(fed)

        else:
            self._result.build()

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Arguments:
            keywords (dict): User's keywords.
        """
        super().add_dependencies(keywords)
        self.remove_dependencies(keywords, "ASSE", "CHAM_GD")
        self.remove_dependencies(keywords, "COMB", "CHAM_GD")
        self.remove_dependencies(keywords, "MAILLAGE")
        self.remove_dependencies(keywords, "MODELE")

        if keywords["OPERATION"] in ("ASSE_DEPL", "R2C", "C2R", "DISC"):
            self.remove_dependencies(keywords, "CHAM_GD")

        self.remove_dependencies(keywords, "EVAL", ("CHAM_F", "CHAM_PARA"))

        if keywords["OPERATION"] == "EXTR":
            self.remove_dependencies(keywords, "RESULTAT")
            self.remove_dependencies(keywords, "FISSURE")
            self.remove_dependencies(keywords, "TABLE")
            self.remove_dependencies(keywords, "CARA_ELEM")
            self.remove_dependencies(keywords, "CHARGE")

        if keywords["OPERATION"] == "EVAL":
            self.remove_dependencies(keywords, "CHAM_F")
            self.remove_dependencies(keywords, "CHAM_PARA")


CREA_CHAMP = FieldCreator.run
