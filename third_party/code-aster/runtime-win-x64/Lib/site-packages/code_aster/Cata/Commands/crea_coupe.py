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


CREA_COUPE = MACRO(
    nom="CREA_COUPE",
    op=OPS("code_aster.MacroCommands.crea_coupe_ops.crea_coupe_ops"),
    sd_prod=table_sdaster,
    fr=tr(
        """Création d'une table de coupes avec
                          des noeuds projetés sur la peau du maillage"""
    ),
    COUPE=SIMP(statut="o", typ=table_sdaster),
    MAILLAGE=SIMP(statut="o", typ=(maillage_sdaster, maillage_p)),
    # Nommage automatique des coupes
    NOM_AUTO=SIMP(statut="f", typ="TXM", defaut="NON", into=("OUI", "NON")),
    b_nom_auto=BLOC(
        condition="""(equal_to("NOM_AUTO", 'OUI'))""",
        PREFIXE=SIMP(
            statut="f", typ="TXM", defaut="", fr=tr("préfixe à ajouter au début du nom des coupes")
        ),
        NUME_INIT=SIMP(
            statut="f", typ="I", defaut=1, fr=tr("numéro à partir duquel la numérotation commence")
        ),
        PAS=SIMP(
            statut="f",
            typ="I",
            defaut=1,
            fr=tr("incrément de numérotation entre deux coupes successives"),
        ),
    ),  # fin bloc b_nom_auto
    REVOLUTION=FACT(
        statut="f",
        max="**",
        fr=tr(
            """Création d'une table de coupes par revolution des coupes
                                    définies dans le tableau d'entrée autour d'un axe et un 
                                    centre de rotation"""
        ),
        AXE=SIMP(statut="o", typ="R", min=3, max=3),
        CENTRE=SIMP(statut="o", typ="R", min=3, max=3),
        ANGLE_AUTO=SIMP(statut="f", typ="TXM", defaut="OUI", into=("OUI", "NON")),
        b_angle_auto_oui=BLOC(
            condition="""(equal_to("ANGLE_AUTO", 'OUI'))""",
            NOMBRE=SIMP(statut="o", typ="I", max=1, val_min=2),
            ANGLE_MAX=SIMP(statut="o", typ="R", max=1, val_min=-360, val_max=360),
        ),  # fin bloc b_angle_auto_oui
        b_angle_auto_non=BLOC(
            condition="""(equal_to("ANGLE_AUTO", 'NON'))""",
            ANGLE=SIMP(statut="o", typ="R", max="**", val_min=-360, val_max=360),
        ),  # fin bloc b_angle_auto_non
        GROUP_MA_ORIG=SIMP(statut="o", typ=grma, max=1),
        GROUP_MA_EXTR=SIMP(statut="o", typ=grma, max=1),
        regles=(EXCLUS("NOM_COUPE", "GROUP_COUPE"),),
        NOM_COUPE=SIMP(
            statut="f", typ="TXM", max="**", fr=tr("liste contentant les noms des coupes à traiter")
        ),
        GROUP_COUPE=SIMP(
            statut="f",
            typ="TXM",
            max="**",
            fr=tr("liste contentant les groupes des coupes à traiter"),
        ),
        PREFIXE=SIMP(
            statut="f",
            typ="TXM",
            defaut="",
            fr=tr("préfixe à ajouter au début du nom des coupes en revolution"),
        ),
    ),
)  # fin MACRO
