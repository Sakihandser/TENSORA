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


CALC_THER_MULT = MACRO(
    nom="CALC_THER_MULT",
    op=OPS("code_aster.MacroCommands.calc_ther_mult_ops.calc_ther_mult_ops"),
    sd_prod=evol_ther,
    fr=tr("Calculer les réponses thermiques linéaires pour de multiple cas de chargements"),
    reentrant="n",
    #  Model:
    #  ----------------------------------------------
    MODELE=SIMP(statut="o", typ=modele_sdaster),
    CHAM_MATER=SIMP(statut="o", typ=cham_mater),
    CARA_ELEM=SIMP(statut="f", typ=cara_elem),
    #  Common thermal loading:
    #  ----------------------------------------------
    CHAR_THER_GLOBAL=SIMP(
        statut="f", typ=(char_ther, char_cine_ther), validators=NoRepeat(), max="**"
    ),
    #  General Timestepping:
    #  ----------------------------------------------
    # LIST_INST=SIMP(statut="o", typ=(listr8_sdaster, list_inst)),
    #  Resolution parameters:
    #  --------------------------------------------------
    PARM_THETA=SIMP(statut="f", typ="R", defaut=1, val_min=0.0, val_max=1.0),
    #  Cases thermal loading:
    #  --------------------------------------------------
    CAS_CHARGE=FACT(
        statut="o",
        max="**",
        COEF_H=SIMP(statut="f", typ="R"),
        GROUP_MA=SIMP(statut="f", typ=grma, validators=NoRepeat(), max="**"),
        DUREE_CHOC=SIMP(statut="f", typ="R"),
        NOM_CAS=SIMP(statut="o", typ="TXM"),
        LIST_INST=SIMP(statut="o", typ=(listr8_sdaster, list_inst)),
        EXCIT=SIMP(statut="f", typ=(char_ther, char_cine_ther)),
        regles=(UN_PARMI("EXCIT", "COEF_H"), ENSEMBLE("COEF_H", "DUREE_CHOC", "GROUP_MA")),
    ),
    CONVERGENCE=C_CONVERGENCE("THER_NON_LINE"),
    SOLVEUR=C_SOLVEUR("THER_NON_LINE"),
    NEWTON=FACT(
        statut="d",
        REAC_ITER=SIMP(statut="f", typ="I", defaut=0, val_min=0),
        REAC_INCR=SIMP(statut="f", typ="I", defaut=1, val_min=0),
        PREDICTION=SIMP(statut="f", typ="TXM", defaut="TANGENTE", into=("TANGENTE",)),
        MATRICE=SIMP(statut="f", typ="TXM", defaut="TANGENTE", into=("TANGENTE",)),
    ),
)
