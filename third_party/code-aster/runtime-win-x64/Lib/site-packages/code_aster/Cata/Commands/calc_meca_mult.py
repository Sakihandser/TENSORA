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

from ..Commons import *
from ..Language.DataStructure import *
from ..Language.Syntax import *


CALC_MECA_MULT = MACRO(
    nom="CALC_MECA_MULT",
    op=OPS("code_aster.MacroCommands.calc_meca_mult_ops.calc_meca_mult_ops"),
    sd_prod=evol_noli_dict,
    fr=tr("Obtenir les résultats thermo-mécaniques à partir de champs thermiques"),
    reentrant="n",
    #  Modèle mécanique:
    #  ----------------------------------------------
    MODELE=SIMP(statut="o", typ=modele_sdaster),
    CHAM_MATER=SIMP(statut="o", typ=cham_mater),
    CARA_ELEM=SIMP(statut="f", typ=cara_elem),
    CHAR_MECA_GLOBAL=SIMP(statut="o", typ=(char_meca, char_cine_meca)),
    # liste d'instants:
    #  ----------------------------------------------
    LIST_INST=SIMP(statut="f", typ=(listr8_sdaster, list_inst)),
    #  affectation des variables de commande :
    #  --------------------------------------------------
    #
    CAS_CHARGE=FACT(
        statut="o",
        max="**",
        EVOL_THER=SIMP(statut="o", typ=(evol_ther, evol_ther_dict)),
        b_evol_ther=BLOC(
            condition="""is_type("EVOL_THER") == evol_ther""", NOM_CAS=SIMP(statut="o", typ="TXM")
        ),
        VALE_REF=SIMP(statut="f", typ="R", defaut=0.0),
    ),
    CONVERGENCE=C_CONVERGENCE("MECA_NON_LINE"),
    SOLVEUR=C_SOLVEUR("STAT_NON_LINE"),
    NEWTON=C_NEWTON("STAT_NON_LINE"),
)
