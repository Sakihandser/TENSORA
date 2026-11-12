# coding=utf-8
# --------------------------------------------------------------------
# Copyright (C) 1991 - 2026 - EDF - www.code-aster.org
# This file is part of code_aster.
#
# code_aster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# code_aster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with code_aster.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------


from ..Objects import (
    AssemblyMatrixDisplacementReal,
    FullHarmonicResult,
    FullTransientResult,
    GeneralizedModeResult,
    HarmoGeneralizedResult,
    ModeResult,
    TransientGeneralizedResult,
    PhysicalSolutionRestitutor,
)
from ..Supervis import ExecuteCommand


class RestGenePhys(ExecuteCommand):
    """Command REST_GENE_PHYS"""

    command_name = "REST_GENE_PHYS"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        if isinstance(keywords["RESU_GENE"], TransientGeneralizedResult):
            self._result = FullTransientResult()
        elif isinstance(keywords["RESU_GENE"], HarmoGeneralizedResult):
            self._result = FullHarmonicResult()
        elif isinstance(keywords["RESU_GENE"], GeneralizedModeResult):
            self._result = ModeResult()
        elif isinstance(keywords["RESU_GENE"], ModeResult):
            self._result = ModeResult()
        else:
            raise Exception("Unknown result type")

    def exec_(self, keywords):
        """Override default _exec method."""

        if "ENVELOPPE" in keywords and keywords["ENVELOPPE"]:
            resu_gene = keywords.get("RESU_GENE")
            enveloppe = keywords["ENVELOPPE"]

            if enveloppe == "NORME_MOMENT":
                ar = 1
            if enveloppe == "VALE_ABS":
                ar = 0
            psr = PhysicalSolutionRestitutor(resu_gene, 15, ar)
            node_fields = psr.computeMaxForFieldsOnNodes()
            cell_fields = psr.computeMaxForFieldsOnCells()

            self._result.resize(1)

            # Safely set only existing fields
            if "EFGE_ELNO" in cell_fields:
                self._result.setField(cell_fields["EFGE_ELNO"], "EFGE_ELNO", 1)
            if "EGRU_ELNO" in cell_fields:
                self._result.setField(cell_fields["EGRU_ELNO"], "EGRU_ELNO", 1)

            if "ACCE" in node_fields:
                self._result.setField(node_fields["ACCE"], "ACCE", 1)
            if "DEPL" in node_fields:
                self._result.setField(node_fields["DEPL"], "DEPL", 1)
            if "REAC_NODA" in node_fields:
                self._result.setField(node_fields["REAC_NODA"], "REAC_NODA", 1)

        else:
            super(RestGenePhys, self).exec_(keywords)

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """

        feds = []
        fnds = []

        if "NUME_DDL" in keywords:
            self._result.setDOFNumbering(keywords["NUME_DDL"])

        if "MODE_MECA" in keywords:
            feds += keywords["MODE_MECA"].getFiniteElementDescriptors()
            fnds += keywords["MODE_MECA"].getEquationNumberings()

        resu_gene = keywords["RESU_GENE"]
        if isinstance(
            resu_gene, (TransientGeneralizedResult, HarmoGeneralizedResult, GeneralizedModeResult)
        ):
            dofNum = resu_gene.getDOFNumbering()
            if isinstance(resu_gene, (GeneralizedModeResult)):
                for fED in resu_gene.getFiniteElementDescriptors():
                    self._result.addFiniteElementDescriptor(fED)

            if dofNum:
                self._result.setDOFNumbering(dofNum)
                model = dofNum.getModel()
                if model:
                    self._result.setModel(model)
                for i in dofNum.getFiniteElementDescriptors():
                    self._result.addFiniteElementDescriptor(i)
            else:
                geneDofNum = resu_gene.getGeneralizedDOFNumbering()
                mesh = None
                if geneDofNum:
                    basis = geneDofNum.getModalBasis()
                    if basis:
                        dofNum = basis.getDOFNumbering()
                        if mesh is None:
                            mesh = basis.getMesh()
                        if dofNum:
                            self._result.setDOFNumbering(dofNum)
                            model = dofNum.getModel()
                            if model:
                                self._result.setModel(model)
                            elif not mesh:
                                mesh = dofNum.getMesh()
                            for i in dofNum.getFiniteElementDescriptors():
                                self._result.addFiniteElementDescriptor(i)

                if not mesh:
                    if "MODE_MECA" in keywords:
                        mesh = keywords["MODE_MECA"].getMesh()
                if mesh:
                    self._result.setMesh(mesh)

        elif isinstance(resu_gene, GeneralizedModeResult):
            self._result.setMesh(resu_gene.getMesh())
            matrRigi = resu_gene.getStiffnessMatrix()
            if matrRigi:
                modalBasis = matrRigi.getModalBasis()
                if modalBasis is None:
                    dofNum = matrRigi.getGeneralizedDOFNumbering()
                    if dofNum:
                        modalBasis = dofNum.getModalBasis()
                if modalBasis:
                    dofNum = modalBasis.getDOFNumbering()
                    if dofNum:
                        self._result.setDOFNumbering(dofNum)
            else:
                # resultat issue de proj_mesu_modal
                dofNum = resu_gene.getDOFNumbering()
                if dofNum:
                    self._result.setDOFNumbering(dofNum)

        elif isinstance(resu_gene, ModeResult):
            matrRigiElim = resu_gene.getDependencies()[0]
            assert isinstance(matrRigiElim, AssemblyMatrixDisplacementReal)
            matrRigi = matrRigiElim.getDependencies()[0]
            self._result.setMesh(matrRigi.getMesh())
            dofNum = matrRigi.getDOFNumbering()
            if dofNum:
                self._result.setDOFNumbering(dofNum)
                self._result.setModel(dofNum.getModel())
            feds += resu_gene.getFiniteElementDescriptors()
            fnds += resu_gene.getEquationNumberings()
        else:
            raise Exception("Unknown result type")

        if not self._result.getMesh():
            for fed in feds:
                self._result.setMesh(fed.getMesh())
                break

        if self._result.getMesh():
            self._result.build(feds, fnds)


REST_GENE_PHYS = RestGenePhys.run
