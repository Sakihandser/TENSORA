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


from ...Cata.DataStructure import maillage_sdaster, modele_sdaster, evol_noli
from ...Cata.Syntax import _F, NoRepeat, SIMP, MACRO
from ...CodeCommands import CREA_RESU
from ...Supervis import UserMacro


def mac3coeur_ac_permute(self, **args):
    """Methode corps de la macro MACRO_AC_PERMUTE"""

    # On importe les definitions des commandes a utiliser dans la macro

    POS_INIT = args["POS_INIT"]
    POS_FIN = args["POS_FIN"]
    RESU_INI = args["RESU_INI"]
    RESU_FIN = args["RESU_FIN"]
    INSTANT = args["INSTANT"]
    MA_INI = args["MAILLAGE_INIT"]
    MA_FIN = args["MAILLAGE_FINAL"]
    VECT = args["TRAN"]

    prefix_dil = "DI_CT"
    check_ini = any(g.startswith(prefix_dil) for g in MA_INI.getGroupsOfCells())
    check_fin = any(g.startswith(prefix_dil) for g in MA_FIN.getGroupsOfCells())
    assert not (check_ini ^ check_fin), "Incompatible meshes"
    if not check_ini:
        prefix_dil = "DI"

    CREA_RESU(
        reuse=RESU_FIN,
        OPERATION="PERM_CHAM",
        TYPE_RESU="EVOL_NOLI",
        RESU_INIT=RESU_INI,
        INST_INIT=INSTANT,
        MAILLAGE_INIT=MA_INI,
        NOM_CHAM=("DEPL", "VARI_ELGA", "SIEF_ELGA", "STRX_ELGA"),
        RESU_FINAL=RESU_FIN,
        MAILLAGE_FINAL=MA_FIN,
        PERM_CHAM=(
            _F(
                GROUP_MA_INIT="CR_%s" % POS_INIT,
                GROUP_MA_FINAL="CR_%s" % POS_FIN,
                TRAN=VECT,
                PRECISION=1.0e-10,
            ),
            _F(
                GROUP_MA_INIT="TG_%s" % POS_INIT,
                GROUP_MA_FINAL="TG_%s" % POS_FIN,
                TRAN=VECT,
                PRECISION=1.0e-10,
            ),
            _F(
                GROUP_MA_INIT="ES_%s" % POS_INIT,
                GROUP_MA_FINAL="ES_%s" % POS_FIN,
                TRAN=VECT,
                PRECISION=1.0e-10,
            ),
            _F(
                GROUP_MA_INIT="EI_%s" % POS_INIT,
                GROUP_MA_FINAL="EI_%s" % POS_FIN,
                TRAN=VECT,
                PRECISION=1.0e-10,
            ),
            _F(
                GROUP_MA_INIT="%s_%s" % (prefix_dil, POS_INIT),
                GROUP_MA_FINAL="%s_%s" % (prefix_dil, POS_FIN),
                TRAN=VECT,
                PRECISION=1.0e-10,
            ),
            _F(
                GROUP_MA_INIT="GC_%s_B" % POS_INIT,
                GROUP_MA_FINAL="GC_%s_B" % POS_FIN,
                TRAN=VECT,
                PRECISION=1.0e-10,
            ),
            _F(
                GROUP_MA_INIT="GC_%s_T" % POS_INIT,
                GROUP_MA_FINAL="GC_%s_T" % POS_FIN,
                TRAN=VECT,
                PRECISION=1.0e-10,
            ),
            _F(
                GROUP_MA_INIT="GC_%s_M" % POS_INIT,
                GROUP_MA_FINAL="GC_%s_M" % POS_FIN,
                TRAN=VECT,
                PRECISION=1.0e-10,
            ),
            _F(
                GROUP_MA_INIT="GT_%s_E" % POS_INIT,
                GROUP_MA_FINAL="GT_%s_E" % POS_FIN,
                TRAN=VECT,
                PRECISION=1.0e-10,
            ),
            _F(
                GROUP_MA_INIT="GT_%s_M" % POS_INIT,
                GROUP_MA_FINAL="GT_%s_M" % POS_FIN,
                TRAN=VECT,
                PRECISION=1.0e-10,
            ),
            _F(
                GROUP_MA_INIT="MNT_%s" % POS_INIT,
                GROUP_MA_FINAL="MNT_%s" % POS_FIN,
                TRAN=VECT,
                PRECISION=1.0e-10,
            ),
            _F(
                GROUP_MA_INIT="CREI_%s" % POS_INIT,
                GROUP_MA_FINAL="CREI_%s" % POS_FIN,
                TRAN=VECT,
                PRECISION=1.0e-10,
            ),
        ),
    )

    return RESU_FIN


MACRO_AC_PERMUTE_CATA = MACRO(
    nom="MACRO_AC_PERMUTE",
    sd_prod=evol_noli,
    op=mac3coeur_ac_permute,
    fr="PERMUTATION DES ASSEMBLAGES",
    POS_INIT=SIMP(statut="o", typ="TXM"),
    POS_FIN=SIMP(statut="o", typ="TXM"),
    RESU_INI=SIMP(statut="o", typ=evol_noli),
    RESU_FIN=SIMP(statut="o", typ=evol_noli),
    INSTANT=SIMP(statut="o", typ="R", validators=NoRepeat(), max=1),
    MAILLAGE_INIT=SIMP(statut="o", typ=maillage_sdaster),
    MAILLAGE_FINAL=SIMP(statut="o", typ=maillage_sdaster),
    MODELE_FINAL=SIMP(statut="o", typ=modele_sdaster),
    TRAN=SIMP(statut="o", typ="R", min=3, max=3),
)

MACRO_AC_PERMUTE = UserMacro("MACRO_AC_PERMUTE", MACRO_AC_PERMUTE_CATA, mac3coeur_ac_permute)
