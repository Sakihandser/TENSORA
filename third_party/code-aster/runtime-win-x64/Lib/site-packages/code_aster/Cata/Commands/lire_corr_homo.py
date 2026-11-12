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


def lire_corr_homo_sdprod(self, TYPE_RESU, **kwargs):
    if kwargs.get("__all__"):
        return [evol_elas_dict, evol_ther_dict]
    if TYPE_RESU == "EVOL_THER":
        return evol_ther_dict
    elif TYPE_RESU == "EVOL_ELAS":
        return evol_elas_dict
    else:
        assert False


LIRE_CORR_HOMO = MACRO(
    nom="LIRE_CORR_HOMO",
    op=OPS("code_aster.MacroCommands.MateHomo.io_corr_homo_ops.lire_corr_ops"),
    sd_prod=lire_corr_homo_sdprod,
    reentrant="n",
    fr=tr("Lecture des correcteurs d'homogénéisation au format MED."),
    UNITE=SIMP(statut="o", typ=UnitType("med"), inout="in"),
    TYPE_RESU=SIMP(statut="o", typ="TXM", into=("EVOL_THER", "EVOL_ELAS")),
    MAILLAGE=SIMP(statut="o", typ=maillage_sdaster),
)
