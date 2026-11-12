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

from ..Utilities import _

cata_msg = {
    1: _(
        """Le déplacement fourni est associé à un maillage différent du maillage à déformer.
Il faut que ces deux maillages soient les mêmes.
Pour créer un champ de déplacement adapté au maillage, on peut utiliser la commande PROJ_CHAMP.
"""
    ),
    2: _(
        """Opération DECOUPE_LAC :
pour au moins une maille surfacique déclarée dans GROUP_MA_ESCL,
on ne trouve pas de maille volumique dont cette maille serait une des faces."""
    ),
    3: _("""Pour l'opération DECOUPE_LAC. Groupe de mailles %(i1)d - Nombre de mailles %(i2)d."""),
    4: _(
        """Pour le mot clé facteur %(k1)s, vous nous modifiez qu'une partie des mailles du maillage.
Ceci est dangereux car cela peut produire un maillage non conforme."""
    ),
    5: _("""Le segment %(i1)d de type %(k1)s crée une non-conformité du maillage."""),
    6: _("""La face %(i1)d de type %(k1)s crée une non-conformité du maillage."""),
    7: _("""L'opération ne traite pas les macro-éléments."""),
    8: _("""L'opération ne traite pas les ABSC_CURV."""),
    9: _("""L'opération MODI_MAILLE ne peut traiter qu'une seule occurrence de QUAD_TRIA3."""),
    10: _(
        """Pour le mot clé facteur QUAD_TRIA3, vous voulez modifier certains quadrangles en TRIA3, mais il existe des TRIA6 dans le maillage.
Ceci est dangereux car cela peut produire un maillage non conforme."""
    ),
    11: _(
        """Pour le mot clé facteur %(k1)s, vous voulez transformer certaines mailles en ajoutant des noeuds au centre des faces quadrangulaires.
Mais il existe d'autres mailles ayant des faces quadrangulaires à 8 noeuds qui ne sont pas modifiées.
Ceci est dangereux car cela peut produire un maillage non conforme."""
    ),
    12: _(
        """Vous essayez de modifier la topologie du maillage après avoir fait CREA_MAILLAGE/DECOUPE_LAC sur ce même maillage.
C'est interdit, vous ne pouvez modifier que les coordonnées des noeuds comme dans les mots clés DEFORME et TRANSLATION.
Effectuez toutes les opérations MODI_MAILLAGE avant d'effectuer CREA_MAILLAGE/DECOUPE_LAC sur votre maillage."""
    ),
    13: _(
        """Les volumes %(i1)d de type %(k1)s et %(i2)d de type %(k2)s sont connectés par une face non-conforme.
          Cela crée une non-conformité dans le maillage."""
    ),
    15: _("""Le mot-clef MAILLAGE est obligatoire."""),
    20: _(
        """Échec lors de la création du GROUP_MA (%(k1)s), il existe déjà.
Conseil :
    Si vous souhaitez utiliser un nom de groupe existant, il suffit
    de le détruire avec DEFI_GROUP / DETR_GROUP_MA."""
    ),
    22: _(
        """Le maillage utilisé dans la commande CREA_MAILLAGE est de type MAILLAGE_P (maillage parallèle), ce n'est pas possible pour cette commande."""
    ),
    62: _(
        """Erreur utilisateur dans SYMETRIE : la dimension de POINT et AXE_1 doit être identique."""
    ),
    63: _("""Erreur utilisateur dans SYMETRIE : l'AXE_2 est inutile en 2D, il est ignoré."""),
    64: _(
        """Erreur utilisateur dans SYMETRIE : la dimension de POINT et AXE_2 doit être identique."""
    ),
}
