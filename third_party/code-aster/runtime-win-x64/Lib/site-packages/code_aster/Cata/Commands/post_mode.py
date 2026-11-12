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

POST_MODE = MACRO(
    nom="POST_MODE",
    op=OPS("code_aster.MacroCommands.Modal.post_mode_ops.post_mode_ops"),
    sd_prod=table_sdaster,
    reentrant="n",
    fr=tr("Calculer des paramètres modaux (masses et inertie effective) sur une partie du modèle"),
    MODE=SIMP(statut="o", typ=(mode_meca,)),
    GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
    CARA_ELEM=SIMP(statut="f", typ=cara_elem),
    MATR_MASS=SIMP(statut="o", typ=matr_asse_depl_r),
)
