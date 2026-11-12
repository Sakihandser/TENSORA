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


from ..Language.DataStructure import *
from ..Language.Syntax import *


def C_RECH_LINEAIRE(cmd=None):
    if cmd is None:
        into_meth = ("CORDE", "MIXTE", "PILOTAGE")
    elif cmd == "THER_NON_LINE":
        into_meth = ("CORDE",)

    return FACT(
        statut="f",
        METHODE=SIMP(statut="f", typ="TXM", defaut="CORDE", into=into_meth),
        RESI_LINE_RELA=SIMP(statut="f", typ="R", defaut=0.1, val_min=0.0),
        ITER_LINE_MAXI=SIMP(statut="f", typ="I", defaut=3, val_max=999, val_min=0),
        RHO_MIN=SIMP(statut="f", typ="R", defaut=1.0e-2, val_min=0.0),
        RHO_MAX=SIMP(statut="f", typ="R", defaut=1.0e1, val_min=0.0),
        RHO_EXCL=SIMP(statut="f", typ="R", defaut=0.9e-2, val_min=0.0),
    )
