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


from ..Language.DataStructure import list_inst, listr8_sdaster
from ..Language.Syntax import EXCLUS, FACT, SIMP, BLOC


def C_INCREMENT():  # COMMUN#
    mcfact = FACT(
        statut="o",
        regles=(EXCLUS("NUME_INST_INIT", "INST_INIT"), EXCLUS("NUME_INST_FIN", "INST_FIN")),
        b_inst=BLOC(
            condition="""exists("INST_INIT") or exists("INST_FIN")""",
            CRITERE=SIMP(statut="f", typ="TXM", defaut="RELATIF", into=("RELATIF",)),
            b_prec_rela=BLOC(
                condition="""(equal_to("CRITERE", 'RELATIF'))""",
                PRECISION=SIMP(statut="f", typ="R", defaut=1.0e-6),
            ),
        ),
        LIST_INST=SIMP(statut="o", typ=(listr8_sdaster, list_inst)),
        NUME_INST_INIT=SIMP(statut="f", typ="I"),
        INST_INIT=SIMP(statut="f", typ="R"),
        NUME_INST_FIN=SIMP(statut="f", typ="I"),
        INST_FIN=SIMP(statut="f", typ="R"),
    )

    return mcfact
