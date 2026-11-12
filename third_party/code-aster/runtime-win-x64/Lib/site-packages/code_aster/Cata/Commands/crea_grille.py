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

CREA_GRILLE = MACRO(
    nom="CREA_GRILLE",
    op=OPS("code_aster.MacroCommands.crea_grille_ops.crea_grille_ops"),
    sd_prod=maillage_sdaster,
    fr=tr("Ajout de noeuds et de mailles à partir d'un radier pour la méthode grille"),
    MAILLAGE=SIMP(statut="o", typ=maillage_sdaster),
    GROUP_MA=SIMP(statut="o", typ=grma),
    DISTANCE=SIMP(statut="o", typ="R", min=1, max=1),
    PREFIXE=SIMP(
        statut="f",
        typ="TXM",
        validators=NoRepeat(),
        min=1,
        max=6,
        defaut=("X", "Y", "Z", "RX", "RY"),
    ),
    COOR_CENTRE=SIMP(statut="f", typ="R", min=3, max=3),
)
