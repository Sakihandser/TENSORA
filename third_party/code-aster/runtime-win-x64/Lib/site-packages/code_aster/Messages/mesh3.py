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
    1: _("""Le groupe de noeuds %(k1)s n'existe pas dans le maillage."""),
    2: _(
        """Le groupe de noeuds %(k1)s contient plus qu'un seul noeud. On a pris le premier dans la liste."""
    ),
    3: _("""Traitement du GROUP_MA: %(k1)s de %(i1)d mailles."""),
    4: _("""%(i1)d mailles ont été orientées."""),
    5: _("""Au total %(i1)d mailles orientées."""),
    6: _(
        """Certaines mailles n'ont pas pu être réorientées. L'ensemble des mailles n'est pas connexe."""
    ),
    7: _("""La maille %(k1)s a été réorientée."""),
    8: _("""La maille %(k1)s est orientée."""),
    9: _("""La maille %(k1)s sert à orienter un nouveau groupe connexe."""),
    10: _(
        """Le type de maille %(k1)s n'est actuellement pas traité pour calculer la longueur des arêtes. Les arêtes sur cette mailles sont toutes supposées nulles, ce qui peut engendrer des effets de bord sur les commandes utilisant ce critère."""
    ),
    11: _("""Le groupe de mailles %(k1)s n'existe pas dans le maillage."""),
    12: _("""Il ne semble y avoir aucun groupe de mailles dans le maillage."""),
    13: _("""Le groupe de mailles %(k1)s est vide."""),
    82: _(
        """L'option ne traite que les mailles HEXA27. Or, d'autres types de mailles volumiques ont été fournis."""
    ),
    84: _(
        """Une des mailles données pour l'orientation des éléments HEXA27 n'est pas une maille volumique. La maille incorrecte est de type :  %(k1)s.
"""
    ),
    92: _(
        """L'option ne traite que les mailles linéiques Or, des mailles surfaciques ont été fournies."""
    ),
    94: _(
        """Une des mailles données pour l'orientation des normales n'est pas une maille de peau, i.e. de type QUAD ou TRIA en 3d ou de type SEG en 2d. La maille incorrecte est de type :  %(k1)s.
"""
    ),
    98: _("""On ne peut pas mélanger des SEG avec des TRIA ou des QUAD."""),
    99: _(
        """
 Lors de la vérification automatique de l'orientation des mailles de bord, une erreur a été rencontrée : les groupes de mailles de bord ne forment pas un ensemble connexe.

 Conseils :
 - Commencez par vérifier que les groupes de mailles de bord fournies sont correctement définis.
 - Si ces groupes de mailles ont des raisons d'être non connexes, vous pouvez désactiver la vérification automatique en renseignant VERI_NORM='NON'.
"""
    ),
}
