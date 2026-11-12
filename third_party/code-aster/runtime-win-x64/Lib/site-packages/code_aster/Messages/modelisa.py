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
        """
Problème à la relecture du fichier de maillage.

Conseil : Il se peut que votre fichier de maillage ne soit pas au format Aster.
 Vérifiez que le format de relecture est bien cohérent avec le format du fichier.
"""
    ),
    2: _(
        """
Erreur utilisateur dans MODI_MAILLAGE / ABSC_CURV :
 il est possible de définir une abscisse curviligne uniquement
 pour des mailles de type: POI1, SEG2, SEG3 et SEG4
"""
    ),
    3: _(
        """
Erreur utilisateur dans MODI_MAILLAGE / ABSC_CURV :
 La maille POI1 %(k1)s n'est pas associée à un noeud "sommet" des segments
 de la ligne de segments.
"""
    ),
    4: _(
        """
Erreur utilisateur dans MODI_MAILLAGE / ABSC_CURV :
 Un segment du maillage a %(i1)d noeuds.
 Ces noeuds ne sont pas placés sur un arc de cercle (à 1%% près).
 Coordonnées des noeuds de l'extrémité 1 du segment : %(r1)f %(r2)f %(r3)f
 Coordonnées des noeuds de l'extrémité 2 du segment : %(r4)f %(r5)f %(r6)f

Risques et conseils :
 On ne peut pas utiliser la fonctionnalité ABSC_CURV sur de tels
 segments.

"""
    ),
    5: _(
        """
Erreur utilisateur dans MODI_MAILLAGE / ABSC_CURV :
Le groupe de noeuds fourni via le mot-clé GROUP_NO_ORIG comporte plusieurs noeuds.
"""
    ),
    8: _(
        """
 Vous affectez des caractéristiques de type %(k1)s à la maille %(k2)s qui est pas de ce type.

 Conseil :
   Vérifier le résultat de la commande AFFE_MODELE pour la maille %(k2)s.
"""
    ),
    10: _(
        """
 la norme de l'axe AXE définie sous le mot clé facteur GRILLE ou MEMBRANE est nul.
"""
    ),
    11: _(
        """
 L'axe AXE est colinéaire à la normale de l'élément. On ne peut pas définir
 l'orientation des armatures.
"""
    ),
    12: _(
        """
 Il n'est pas possible de construire une normale à la maille. Celle-ci est dégénérée.
"""
    ),
    13: _(
        """
 Il n'est pas possible de construire un repère cylindrique : le barycentre de la maille
 est trop proche de l'axe.
"""
    ),
    14: _(
        """
 POUTRE : une erreur a été détectée lors de l'affectation des valeurs dans le tampon
"""
    ),
    15: _(
        """
 poutre : une  erreur a été détectée lors des vérifications des valeurs entrées
"""
    ),
    16: _(
        """
 Vous fournissez deux caractéristiques élémentaires.
 - Les caractéristiques doivent concerner l'amortissement et la rigidité.
 - Les caractéristiques doivent être sur le même type de discret (TR_D_N ou TR_D_L).
"""
    ),
    17: _(
        """
 caractéristique  %(k1)s  non admise actuellement
"""
    ),
    20: _(
        """
 le discret  %(k1)s  n'a pas le bon nombre de noeuds.
"""
    ),
    21: _(
        """
 le noeud  %(k1)s  extrémité d'un des discrets n'existe pas dans la surface donnée par GROUP_MA.
"""
    ),
    23: _(
        """
AFFE_CARA_ELEM :
La caractéristique %(k1)s, coefficient de cisaillement, pour les poutres doit toujours être >=1.0
   Valeur donnée : %(r1)f
"""
    ),
    24: _(
        """
  GENE_TUYAU : préciser un seul noeud par tuyau
"""
    ),
    25: _(
        """
 ORIENTATION : GENE_TUYAU
 le noeud doit être une des extrémités
"""
    ),
    26: _(
        """
La maille %(k1)s est affectée d'une modélisation de type tuyau. La valeur du mot-clé SECTION
doit nécessairement être CERCLE.
"""
    ),
    27: _(
        """
 on ne peut pas mélanger des tuyaux à 3 et 4 noeuds pour le moment
"""
    ),
    28: _(
        """
 ORIENTATION : GENE_TUYAU
 un seul noeud doit être affecté
"""
    ),
    56: _(
        """
 impossibilité, la maille  %(k1)s  doit être une maille de type  %(k2)s , et elle est de type :  %(k3)s  pour la caractéristique  %(k4)s
"""
    ),
    77: _(
        """
 poutre :
 maille  %(k1)s
 section GENERALE
 il manque la caractéristique  %(k2)s
"""
    ),
    78: _(
        """
 poutre :
 maille  %(k1)s
 section GENERALE
 élément poutre : il manque la caractéristique  %(k2)s
"""
    ),
    79: _(
        """
 poutre :
 maille  %(k1)s
 section rectangle
 il manque  la caractéristique  %(k2)s
"""
    ),
    80: _(
        """
 poutre :
 maille  %(k1)s
 section cercle
 il manque la caractéristique  %(k2)s
"""
    ),
    81: _(
        """
 poutre :
 maille  %(k1)s
 section générale
 la valeur de  %(k2)s  doit être strictement positive
"""
    ),
    82: _(
        """
 poutre :
 maille  %(k1)s
 section rectangle
 la valeur de  %(k2)s  doit être strictement positive
"""
    ),
    83: _(
        """
 poutre :
 maille  %(k1)s
 section cercle
 la valeur de  %(k2)s  doit être strictement positive
"""
    ),
    84: _(
        """
 poutre :
 maille  %(k1)s
 section rectangle
 la valeur de  %(k2)s  ne doit pas dépasser  %(k3)s /2
"""
    ),
    85: _(
        """
 poutre :
 maille  %(k1)s
 section cercle
 la valeur de  %(k2)s  ne doit pas dépasser celle de  %(k3)s
"""
    ),
    86: _(
        """
 section CIRCULAIRE/RECTANGULAIRE non supportée par POUTRE/TUYAU/FAISCEAU
"""
    ),
    87: _(
        """
AFFE_CARA_ELEM / ORIENTATION :
  Pas d'affectation d'orientation du type %(k1)s sur la maille %(k2)s qui n'est pas un SEG2.
"""
    ),
    88: _(
        """
AFFE_CARA_ELEM / ORIENTATION :
  Pas d'affectation d'orientation du type %(k1)s sur la maille %(k2)s de longueur nulle.
"""
    ),
    89: _(
        """
AFFE_CARA_ELEM / ORIENTATION :
  Pas d affectation d'orientation du type %(k1)s sur le noeud %(k2)s.
"""
    ),
    90: _(
        """
Erreur d'utilisation pour le mot clé AFFE_CARA_ELEM / ORIENTATION
  Il ne faut pas utiliser le type %(k1)s  sur la maille  %(k2)s
  qui est de longueur non nulle : %(r1)f.
"""
    ),
    91: _(
        """
 orientation :
 pas d'affectation d'orientation du type %(k1)s sur la maille %(k2)s qui n'est pas SEG2.
"""
    ),
    92: _(
        """
 occurrence  %(k1)s de "poutre" (maille  %(k2)s)
 écrasement d'un type de variation de section par un autre
"""
    ),
    93: _(
        """
 occurrence  %(k1)s de "poutre" (maille  %(k2)s)
 écrasement d'un type de géométrie de section par un autre.
"""
    ),
    94: _(
        """
 le DESCRIPTEUR_GRANDEUR des déplacements ne tient pas sur 11 entiers codés
"""
    ),
    95: _(
        """
AFFE_CARA_ELEM / ORIENTATION
  Il y a %(i1)d maille(s) de type SEG2 dont la longueur est considérée comme nulle car
  inférieure à %(r1)f donnée par le mot clef PRECISION.
"""
    ),
}
