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

POST_MAC3COEUR = MACRO(
    nom="POST_MAC3COEUR",
    sd_prod=table_sdaster,
    op=OPS("code_aster.MacroCommands.Mac3Coeur.post_mac3coeur_ops.post_mac3coeur_ops"),
    TYPE_COEUR=SIMP(
        statut="o",
        typ="TXM",
        into=(
            "MONO",
            "MONO_FROID",
            "TEST",
            "900",
            "1300",
            "N4",
            "EPR",
            "LIGNE900",
            "LIGNE1300",
            "LIGNEN4",
            "LIGNEEPR",
        ),
    ),
    b_type_ligne=BLOC(
        condition="""is_in("TYPE_COEUR", ("LIGNE900","LIGNE1300","LIGNEN4","LIGNEEPR"))""",
        NB_ASSEMBLAGE=SIMP(statut="o", typ="I", max=1),
    ),
    RESULTAT=SIMP(statut="o", typ=evol_noli),  # SD_RESULTAT
    TABLE=SIMP(statut="o", typ=table_sdaster),  # TABLE DES DAMAC A L INSTANT N
    INST=SIMP(statut="o", typ="R", max=1),  # INSTANT
    TYPE_CALCUL=SIMP(statut="o", typ="TXM", into=("LAME", "DEFORMATION", "FORCE_CONTACT")),
    OPERATION=SIMP(statut="f", typ="TXM", into=("EXTRACTION", "ANALYSE"), defaut="EXTRACTION"),
    b_lame=BLOC(
        condition="""equal_to("TYPE_CALCUL", "LAME") and equal_to("OPERATION", "EXTRACTION")""",
        FORMAT=SIMP(statut="f", typ="TXM", into=("DAMAC", "ASTER"), defaut="DAMAC"),
    ),
)
