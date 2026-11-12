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

DEFI_PRES_EC8 = MACRO(
    nom="DEFI_PRES_EC8",
    op=OPS("code_aster.MacroCommands.defi_pres_ec8_ops.defi_pres_ec8_ops"),
    sd_prod=formule,
    fr=tr("Création d'un formule de pression pour réservoir (EC8)"),
    reentrant="n",
    #
    Z_FOND=SIMP(statut="o", typ="R", min=1, max=1),
    RAYON=SIMP(statut="o", typ="R", min=1, max=1),
    HAUT_EAU=SIMP(statut="o", typ="R", min=1, max=1),
    RHO_EAU=SIMP(statut="o", typ="R", min=1, max=1),
    #
    ACCE_SP_H=SIMP(statut="o", typ="R", min=1, max=1),
    ACCE_FLEX_H_N=SIMP(statut="o", typ="R", min=1, max=1),
    ACCE_FLEX_V=SIMP(statut="o", typ="R", min=1, max=1),
    ACCE_SP_V=SIMP(statut="o", typ="R", min=1, max=1),
    ACCE_CONV_H=SIMP(statut="o", typ="R", min=1, max=1),
    #
    GRAVITE=SIMP(statut="f", typ="R", min=1, max=1, defaut=0.0, val_min=0.0),
    PRES_SURF_LIBR=SIMP(statut="f", typ="R", min=1, max=1, defaut=0.0),
    NEWMARK=SIMP(statut="f", typ="TXM", into=("PC+", "PC-"), defaut="PC+"),
    EVAL=FACT(
        regles=(UN_PARMI("LIST_H", "LIST_R_FOND")),
        statut="f",
        max="**",
        RHO=SIMP(statut="o", typ=("R")),
        LIST_H=SIMP(statut="f", typ="R", val_min=0.0, max="**"),
        LIST_R_FOND=SIMP(statut="f", typ="R", val_min=0.0, max="**"),
        LIST_EPAIS=SIMP(statut="o", typ="R", max="**"),
        THETA=SIMP(statut="f", typ=("R"), defaut=0.0),
        TABLE=SIMP(statut="o", typ=CO),
    ),
)
