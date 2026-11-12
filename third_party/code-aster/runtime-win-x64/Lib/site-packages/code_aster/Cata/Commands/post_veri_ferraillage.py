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


POST_VERI_FERRAILLAGE = MACRO(
    nom="POST_VERI_FERRAILLAGE",
    op=("code_aster.MacroCommands.post_veri_ferraillage_ops.post_veri_ferraillage_ops"),
    sd_prod=table_sdaster,
    reentrant="n",
    fr=tr("calcul du diagramme d'interaction N-M sur sur tout ou partie du maillage"),
    CHAM_VFER=SIMP(statut="o", typ=cham_elem),
    GROUP_MA=SIMP(statut="f", typ=grma, validators=NoRepeat(), max="**"),
    SEUIL_MIN_MARGE=SIMP(statut="f", typ="R"),
    NB_DIAG=SIMP(statut="f", typ="I"),
)
