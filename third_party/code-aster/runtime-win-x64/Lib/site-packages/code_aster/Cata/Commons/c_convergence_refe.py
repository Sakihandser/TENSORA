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


def C_CONVERGENCE_REFE(command):
    assert command == "MECA_NON_LINE"
    mcfact = FACT(
        statut="f",
        max="**",
        regles=(UN_PARMI("TOUT", "GROUP_MA")),
        TOUT=SIMP(statut="f", typ="TXM", into=("OUI",)),
        GROUP_MA=SIMP(statut="f", typ=grma, validators=NoRepeat(), max="**"),
        SIGM=SIMP(statut="f", typ="R"),
        EPSI=SIMP(statut="f", typ="R"),
        FLUXTHER=SIMP(statut="f", typ="R"),
        FLUXHYD1=SIMP(statut="f", typ="R"),
        FLUXHYD2=SIMP(statut="f", typ="R"),
        EFFORT=SIMP(statut="f", typ="R"),
        MOMENT=SIMP(statut="f", typ="R"),
        VARI=SIMP(statut="f", typ="R"),
        DEPL=SIMP(statut="f", typ="R"),
        LAGR=SIMP(statut="f", typ="R"),
        PI=SIMP(statut="f", typ="R"),
    )
    return mcfact
