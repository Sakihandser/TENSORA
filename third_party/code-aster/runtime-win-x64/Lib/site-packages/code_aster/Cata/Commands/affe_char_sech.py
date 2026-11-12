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

AFFE_CHAR_SECH = OPER(
    nom="AFFE_CHAR_SECH",
    op=34,
    sd_prod=char_ther,
    fr=tr("Affectation de charges et conditions aux limites constantes pour le séchage"),
    reentrant="n",
    regles=(AU_MOINS_UN("SECH_IMPO"),),
    MODELE=SIMP(statut="o", typ=(modele_sdaster)),
    DOUBLE_LAGRANGE=SIMP(statut="f", typ="TXM", into=("OUI", "NON"), defaut="OUI"),
    SECH_IMPO=FACT(
        statut="f",
        max="**",
        regles=(AU_MOINS_UN("TOUT", "GROUP_MA", "GROUP_NO", TOUT="OUI"),),
        TOUT=SIMP(statut="f", typ="TXM", into=("OUI",)),
        GROUP_NO=SIMP(statut="f", typ=grno, validators=NoRepeat(), max="**"),
        GROUP_MA=SIMP(statut="f", typ=grma, validators=NoRepeat(), max="**"),
        SANS_GROUP_MA=SIMP(statut="f", typ=grma, validators=NoRepeat(), max="**"),
        SANS_GROUP_NO=SIMP(statut="f", typ=grno, validators=NoRepeat(), max="**"),
        SECH=SIMP(statut="o", typ="R"),
    ),
    INFO=SIMP(statut="f", typ="I", defaut=1, into=(1, 2)),
    translation={"AFFE_CHAR_SECH": "Assign drying load"},
)
