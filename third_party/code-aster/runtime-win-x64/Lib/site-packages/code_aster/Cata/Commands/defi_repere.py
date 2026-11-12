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

DEFI_REPERE = MACRO(
    nom="DEFI_REPERE",
    op=OPS("code_aster.MacroCommands.defi_repere_ops.defi_repere_ops"),
    sd_prod=cham_elem,
    fr=tr("Définition d'un repère"),
    MODELE=SIMP(statut="o", typ=modele_sdaster),
    DEFI=FACT(
        statut="o",
        max="**",
        regles=(UN_PARMI("TOUT", "GROUP_MA"),),
        TOUT=SIMP(statut="f", typ="TXM", validators=NoRepeat(), into=("OUI",)),
        GROUP_MA=SIMP(
            statut="f",
            typ=grma,
            validators=NoRepeat(),
            max="**",
            fr=tr("le calcul ne sera effectué que sur ces mailles"),
        ),
        SYST_COOR=SIMP(statut="o", typ="TXM", into=("CARTESIEN", "CYLINDRIQUE")),
        b_SYST_CART=BLOC(
            condition="""equal_to("SYST_COOR", 'CARTESIEN')""",
            regles=(UN_PARMI("ANGL_EULER", "ANGL_NAUT"),),
            ANGL_EULER=SIMP(statut="f", typ="R", min=3, max=3),
            ANGL_NAUT=SIMP(statut="f", typ="R", min=3, max=3),
        ),
        b_SYST_CYLI=BLOC(
            condition="""equal_to("SYST_COOR", 'CYLINDRIQUE')""",
            regles=(PRESENT_PRESENT("ORIG_AXE", "ANGL_AXE"),),
            ORIG_AXE=SIMP(statut="o", typ="R", min=2, max=3),
            ANGL_AXE=SIMP(statut="o", typ="R", min=2, max=2),
        ),
    ),
)
