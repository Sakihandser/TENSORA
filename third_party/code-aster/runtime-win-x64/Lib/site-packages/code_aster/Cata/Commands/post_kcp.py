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

POST_KCP = MACRO(
    nom="POST_KCP",
    op=OPS("code_aster.MacroCommands.Kcp.post_kcp_ops.post_kcp_ops"),
    sd_prod=table_sdaster,
    fr=tr("Calcul des facteurs d'intensité de contrainte par la méthode KCP correction BETA"),
    reentrant="n",
    MODELE=SIMP(statut="o", typ=modele_sdaster),
    MATER_MDB=SIMP(statut="o", typ=mater_sdaster),
    EPAIS_MDB=SIMP(statut="o", typ="R"),
    MATER_REV=SIMP(statut="o", typ=mater_sdaster),
    EPAIS_REV=SIMP(statut="o", typ="R"),
    UNITE_LONGUEUR=SIMP(statut="o", typ="TXM", into=("M", "MM")),
    FISSURE=FACT(
        statut="o",
        FORM_FISS=SIMP(statut="o", typ="TXM", into=("SEMI_ELLIPTIQUE", "BANDE")),
        b_defaut_eli=BLOC(
            condition="""(equal_to("FORM_FISS", 'SEMI_ELLIPTIQUE'))""",
            LONGUEUR=SIMP(statut="o", typ="R"),
            CORRECTION=SIMP(statut="f", typ="TXM", defaut="BETA_3D", into=("BETA_2D", "BETA_3D")),
        ),
        PROFONDEUR=SIMP(statut="o", typ="R"),
        ORIENTATION=SIMP(statut="o", typ="TXM", into=("CIRC", "LONGI")),
    ),
    K1D=FACT(
        statut="o",
        max="**",
        TABL_MECA=SIMP(statut="o", typ=(table_sdaster)),
        TABL_THER=SIMP(statut="o", typ=(table_sdaster)),
    ),
)
