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
    1: _("""On ne peut pas utiliser le raccord %(k1)s avec des macro-éléments."""),
    2: _(
        """Il faut indiquer le noeud de liaison par 'GROUP_NO_2' après le mot-clé facteur %(k1)s pour l'option %(k2)s"""
    ),
    3: _("""Il ne faut donner qu'un seul GROUP_NO à un noeud à raccorder à la coque."""),
    4: _("""Le GROUP_NO %(k1)s ne doit contenir qu'un seul noeud."""),
    5: _("""Il faut donner un vecteur orientant l'axe de la poutre sous le mot-clé %(k1)s."""),
    6: _(
        """Il faut donner un vecteur non nul orientant l'axe de la poutre sous le mot-clé %(k1)s."""
    ),
    7: _("""Il faut donner un CARA_ELEM pour récupérer l'épaisseur des éléments de bord."""),
    9: _(
        """Un des noeuds donné pour la partie coque ou tuyau ne porte pas le degré de liberté de rotation %(k1)s. Il doit appartenir au modèle.
"""
    ),
    10: _("""Le noeud poutre devrait porter le degré de liberté %(k1)s."""),
    11: _("""Erreur lors du raccord %(k1)s, la surface de raccord de la coque est nulle."""),
    12: _(
        """
Utilisation de LIAISON_ELEM, pour le raccord %(k1)s, à l'occurrence %(i1)d du mot-clé facteur.
Le noeud poutre n'est pas situé géométriquement au même endroit que le centre de gravité de la section.
La distance entre les deux points est supérieure à %(r7)g%% du "rayon" de la section.

   Position du centre de gravité de la section :
      %(r1)g   %(r2)g   %(r3)g
   Position du noeud poutre :
      %(r4)g   %(r5)g   %(r6)g
   Distance : %(r9)g
   Rayon    : %(r8)g

Risque et conseils :
   Vérifiez la position du noeud poutre.
   Rappel : on ne peut pas utiliser ce type de liaison pour relier une poutre avec
   une section qui ne serait que partiellement maillée (symétrie du maillage).
"""
    ),
    13: _(
        """
Erreur utilisateur pour LIAISON_ELEM. Il faut que les mots clés donnant le noeud pour la poutre ne désignent qu'un seul noeud.
"""
    ),
    14: _("""Il faut donner un CARA_ELEM pour récupérer les caractéristiques de tuyau."""),
    15: _(
        """Le noeud de la poutre, de coordonnées <%(r1)g  %(r2)g  %(r3)g>,
 ne doit pas appartenir à des mailles constituant la trace de la poutre sur la coque.
 Le problème vient de l'occurrence %(i1)d de LIAISON_ELEM.

Solution : Il faut dédoubler le noeud.
"""
    ),
    16: _(
        """Un des noeuds donné pour la partie solide porte le degré de liberté de rotation %(k1)s."""
    ),
    17: _(
        """
Utilisation de LIAISON_ELEM, pour le raccord %(k1)s, à l'occurrence %(i1)d du mot-clé facteur.
Le noeud poutre n'est pas situé géométriquement au même endroit que le centre de gravité de la section.
La distance entre les 2 noeuds est supérieure à %(r7)g%% du rayon (Aire/Pi)^0.5 de la section.

   Position du centre de gravité de la section :
      %(r1)g   %(r2)g   %(r3)g
   Position du noeud poutre :
      %(r4)g   %(r5)g   %(r6)g
   Distance : %(r9)g
   Rayon    : %(r8)g
"""
    ),
}
