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

from ..CodeCommands import CREA_RESU, DEFI_BASE_MODALE, NUME_DDL_GENE, PROJ_VECT_BASE
from ..Objects import FieldOnNodesReal, GeneralizedLoad


def affe_char_gene_ops(self, **args):
    """
    Macro AFFE_CHAR_GENE implementation
    return a GeneralizedLoad with linear relations between generalized dofs
    """

    nume_ddl_gene = args["NUME_DDL_GENE"]
    liaisons = args["LIAISON"]

    basis = nume_ddl_gene.getModalBasis()
    dof_num = basis.getDOFNumbering()
    vect_null = FieldOnNodesReal(dof_num)
    nb_modes = basis.getNumberOfIndexes()

    # check consistency
    for i_lagr, liaison in enumerate(liaisons):
        assert len(liaison["NUME_MODE"]) == len(liaison["COEF_MULT"])
        for nume_mode in liaison["NUME_MODE"]:
            assert nume_mode > 0 and nume_mode <= nb_modes

    # create new basis with Lagrange multipliers
    nb_lagr = len(liaisons)
    modes_lagr = CREA_RESU(
        OPERATION="AFFE",
        TYPE_RESU="MODE_MECA",
        AFFE=[
            {"CHAM_GD": vect_null, "NOM_CHAM": "DEPL", "NUME_MODE": nume_mode}
            for nume_mode in range(1, nb_lagr + 1)
        ],
    )

    basis = DEFI_BASE_MODALE(RITZ=(_F(MODE_MECA=basis), _F(MODE_INTF=modes_lagr)))

    # create new dofNumbering
    nume_gene = NUME_DDL_GENE(BASE=basis, STOCKAGE="PLEIN")

    # create char_gene
    char_gene = GeneralizedLoad()
    char_gene.setDOFNumbering(nume_gene)
    char_gene.setMPCs([(l["NUME_MODE"], l["COEF_MULT"], l["COEF_IMPO"]) for l in liaisons])

    return char_gene
