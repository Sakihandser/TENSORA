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

import numpy as np

from ..Objects import (
    AssemblyMatrixPressureComplex,
    FullHarmonicAcousticResult,
    FullHarmonicResult,
    FullTransientResult,
    HarmoGeneralizedResult,
    TransientGeneralizedResult,
    Function,
)
from ..Supervis import ExecuteCommand

from ..Helpers import check_dis_choc_elas


class VibrationDynamics(ExecuteCommand):
    """Command to solve linear vibration dynamics problem, on physical or modal bases,
    for harmonic or transient analysis.
    """

    command_name = "DYNA_VIBRA"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        if keywords.get("reuse") != None:
            self._result = keywords["reuse"]
        else:
            base = keywords["BASE_CALCUL"]
            typ = keywords["TYPE_CALCUL"]
            matrRigi = keywords["MATR_RIGI"]
            if base == "PHYS":
                if typ == "TRAN":
                    self._result = FullTransientResult()
                    return
                if isinstance(matrRigi, AssemblyMatrixPressureComplex):
                    self._result = FullHarmonicAcousticResult()
                    return
                self._result = FullHarmonicResult()
            else:
                if typ == "TRAN":
                    self._result = TransientGeneralizedResult()
                else:
                    self._result = HarmoGeneralizedResult()

    def exec_(self, keywords):
        base = keywords["BASE_CALCUL"]
        typ = keywords["TYPE_CALCUL"]
        if "CHAR_GENE" in keywords.keys():
            char_gene = keywords.pop("CHAR_GENE")
            nume_gene = char_gene.getDOFNumbering()
            # add of linear relations between modes
            basis = nume_gene.getModalBasis()
            liaisons = char_gene.getMPCs()
            nb_modes_with_lagr = basis.getNumberOfIndexes()
            nb_lagr = len(liaisons)
            nb_modes = nb_modes_with_lagr - nb_lagr

            # modification of stiffness matrix
            matr_rigi = keywords["MATR_RIGI"]
            values = np.zeros((nb_modes_with_lagr, nb_modes_with_lagr))
            values[:-nb_lagr, :-nb_lagr] = matr_rigi.toNumpy()
            for i_lagr, liaison in enumerate(liaisons):
                nume_mode_lagr = nb_modes + i_lagr + 1
                for nume_mode, coef_mult in zip(liaison[0], liaison[1]):
                    values[nume_mode_lagr - 1, nume_mode - 1] = coef_mult
                    values[nume_mode - 1, nume_mode_lagr - 1] = coef_mult

            is_symmetric = matr_rigi.isSymmetric()
            matr_rigi = type(matr_rigi)()
            matr_rigi.setGeneralizedDOFNumbering(nume_gene)
            matr_rigi.setModalBasis(basis)
            matr_rigi.allocate(is_symmetric)
            matr_rigi.fromNumpy(values)
            keywords["MATR_RIGI"] = matr_rigi

            # copy of mass matrix
            matr_mass = keywords["MATR_MASS"]
            values = np.zeros((nb_modes_with_lagr, nb_modes_with_lagr))
            values[:-nb_lagr, :-nb_lagr] = matr_mass.toNumpy()

            is_symmetric = matr_mass.isSymmetric()
            matr_mass = type(matr_mass)()
            matr_mass.setGeneralizedDOFNumbering(nume_gene)
            matr_mass.setModalBasis(basis)
            matr_mass.allocate(is_symmetric)
            matr_mass.fromNumpy(values)
            keywords["MATR_MASS"] = matr_mass

            # on verra plus tard pour MATR_AMOR, faire comme pour MATR_MASS
            assert "MATR_AMOR" not in keywords

            # RHS with Lagrange values
            vect_gen = char_gene.getAssemblyVector()
            vect_gen_values = vect_gen.getValues()
            for i_lagr, liaison in enumerate(liaisons):
                coef_impo = liaison[2]
                vect_gen_values[nb_modes + i_lagr] = coef_impo
            vect_gen.setValues(vect_gen_values)

            keywords["EXCIT"] = {"VECT_ASSE_GENE": vect_gen, "COEF_MULT": 1}

        super().exec_(keywords)

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        if keywords["BASE_CALCUL"] == "PHYS":
            massMatrix = keywords["MATR_MASS"]
            dofNum = massMatrix.getDOFNumbering()
            self._result.setModel(dofNum.getModel())
            self._result.setDOFNumbering(dofNum)
            for i in dofNum.getFiniteElementDescriptors():
                self._result.addFiniteElementDescriptor(i)
            self._result.setDOFNumbering(dofNum)
            self._result.setModel(dofNum.getModel())
            mesh = massMatrix.getMesh()
            if mesh is not None:
                self._result.setMesh(mesh)
            self._result.build()
        if keywords["BASE_CALCUL"] == "GENE":
            stiffnessMatrix = keywords["MATR_RIGI"]
            dofGeneNum = stiffnessMatrix.getGeneralizedDOFNumbering()
            if isinstance(self._result, (HarmoGeneralizedResult, TransientGeneralizedResult)):
                self._result.setGeneralizedDOFNumbering(dofGeneNum)
            else:
                raise Exception("Unknown result type")
            if keywords["TYPE_CALCUL"] == "TRAN":
                self._result.build()

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Arguments:
            keywords (dict): User's keywords.
        """
        self._result.resetDependencies()
        for key in ("MATR_MASS", "MATR_RIGI", "MATR_AMOR"):
            if keywords.get(key):
                self._result.addDependency(keywords[key])

    def adapt_syntax(self, keywords):
        """Adapt syntax *after* syntax checking.

        Arguments:
            keywords (dict): User's keywords. Changed in place
        """
        LstComportement = keywords.get("COMPORTEMENT", None)
        if not LstComportement is None:
            for UnComportement in LstComportement:
                if UnComportement.get("RELATION") == "CHOC_ELAS_TRAC":
                    tmp = check_dis_choc_elas(UnComportement)


DYNA_VIBRA = VibrationDynamics.run
