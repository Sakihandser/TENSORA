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


from ..Objects import FullHarmonicResult, FullTransientResult, ModeResult, NonLinearResult
from ..Objects import DOFNumbering
from ..Supervis import ExecuteCommand


class RestSousStrucOper(ExecuteCommand):
    """Command that allows to project fields."""

    command_name = "REST_SOUS_STRUC"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        resu_gene = keywords.get("RESU_GENE")
        resultat = keywords.get("RESULTAT")
        if resu_gene is not None:
            if resu_gene.getType() == "TRAN_GENE":
                self._result = FullTransientResult()
            if resu_gene.getType() == "MODE_GENE":
                self._result = ModeResult()
            if resu_gene.getType() == "MODE_CYCL":
                self._result = ModeResult()
            if resu_gene.getType() == "HARM_GENE":
                self._result = FullHarmonicResult()

        if resultat is not None:
            if resultat.getType() == "EVOL_NOLI":
                self._result = NonLinearResult()
            if resultat.getType() == "DYNA_TRANS":
                self._result = FullTransientResult()
            if resultat.getType() == "MODE_MECA":
                self._result = ModeResult()

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        sousStruc = keywords.get("SOUS_STRUC")
        resuGene = keywords.get("RESU_GENE")
        squelette = keywords.get("SQUELETTE")
        modeMeca = keywords.get("MODE_MECA")

        fnds = []
        if sousStruc is not None:
            if resuGene is not None:
                geneDofNum = resuGene.getGeneralizedDOFNumbering()
                modeleGene = geneDofNum.getGeneralizedModel()
                mesh = None
                if modeleGene is not None:
                    macroElem = modeleGene.getDynamicMacroElementFromName(sousStruc)
                    modeMeca = macroElem.getMechanicalMode()
                    self._result.setDOFNumbering(modeMeca.getDOFNumbering())
                    mat = macroElem.getDampingMatrix()
                    if mat is None:
                        mat = macroElem.getImpedanceDampingMatrix()
                    if mat is None:
                        mat = macroElem.getImpedanceMatrix()
                    if mat is None:
                        mat = macroElem.getImpedanceMassMatrix()
                    if mat is None:
                        mat = macroElem.getImpedanceStiffnessMatrix()
                    if mat is None:
                        mat = macroElem.getMassMatrix()
                    if mat is None:
                        mat = macroElem.getStiffnessMatrixComplex()
                    if mat is None:
                        mat = macroElem.getStiffnessMatrixReal()
                    if mat is not None:
                        dofNum = mat.getDOFNumbering()
                        modele = dofNum.getModel()
                        if modele is not None:
                            mesh = modele.getMesh()
                            self._result.setModel(modele)
                        else:
                            mesh = mat.getMesh()
                            self._result.setMesh(mat.getMesh())
                        mesh = mat.getMesh()
                        self._result.setMesh(mat.getMesh())
                        dofNum = mat.getDOFNumbering()
                        for fed in dofNum.getFiniteElementDescriptors():
                            self._result.addFiniteElementDescriptor(fed)

                if mesh is None:
                    if geneDofNum is not None:
                        basis = geneDofNum.getModalBasis()
                        if basis is not None:
                            dofNum = basis.getDOFNumbering()
                            mesh = basis.getMesh()
                            if dofNum is not None:
                                for i in dofNum.getFiniteElementDescriptors():
                                    self._result.addFiniteElementDescriptor(i)
                                self._result.setDOFNumbering(dofNum)
                                modele = dofNum.getModel()
                                if modele is not None:
                                    self._result.setModel(modele)
                                elif mesh is None:
                                    mesh = dofNum.getMesh()

                    if mesh is not None:
                        self._result.setMesh(mesh)

        elif squelette is not None:
            dofNum = DOFNumbering(self._result.getName() + ".PROFC")
            self._result.setDOFNumbering(dofNum)
            if modeMeca is not None:
                dofNum = modeMeca.getDOFNumbering()
                if dofNum:
                    fnds.append(dofNum.getEquationNumbering())
            self._result.setMesh(squelette)

        if self._result.getMesh():
            self._result.build(fnds=fnds)


REST_SOUS_STRUC = RestSousStrucOper.run
