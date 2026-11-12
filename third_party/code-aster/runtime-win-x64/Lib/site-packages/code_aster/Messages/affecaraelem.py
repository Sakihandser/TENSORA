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
    Si le mot-clé TOUT est donné sous MASSIF, il ne peut y avoir qu'une seule occurrence du mot-clé facteur MASSIF.
"""
    ),
    2: _(
        """AFFE_CARA_ELEM
Au moins un des mot-clés facteur d'AFFE_CARA_ELEM n'a aucune affection sur des GROUP_MA,
des MAILLES ou sur TOUT='OUI'.

Vérifiez vos données.
"""
    ),
    10: _(
        """AFFE_CARA_ELEM / <%(k1)s> / occurrence %(i1)d
Une maille dans le groupe <%(k2)s> n'est pas de la bonne topologique.
Vous êtes en 2D, la topologie des mailles doit être 1.
Les mailles de <%(k2)s> doivent être des segments.

Pour information :
 - nom de la maille incriminée                       : %(k3)s
 - dimension topologique de la maille incriminée     : %(i3)d
 - type de la maille incriminée                      : %(k4)s

Vérifiez vos données.
"""
    ),
    11: _(
        """AFFE_CARA_ELEM / <%(k1)s> / occurrence %(i1)d
Une maille dans le groupe  <%(k2)s> n'a pas la bonne dimension topologique.

Les mailles de <%(k2)s> doivent être des segments ou des éléments de surfaces.
Pour information :
 - maille concernée         : %(k3)s
 - sa dimension topologique : %(i2)d
 - son type                 : %(k4)s

Vérifiez vos données.
"""
    ),
    12: _(
        """AFFE_CARA_ELEM / <%(k1)s> / occurrence %(i1)d
La maille %(k3)s est présente au moins 2 fois dans la définition de la surface.

Les mailles ne doivent être présente qu'une seule fois, en cas de doublon :
- La surface totale de répartition ne peut pas être correctement déterminée.
- La contribution de cette maille n'est pas correcte.

Vérifiez vos données.
"""
    ),
    13: _(
        """AFFE_CARA_ELEM / <%(k1)s> / occurrence %(i1)d
La maille %(k3)s présente dans <%(k2)s> n'a pas le bon nombre de noeuds.
Les mailles gérées doivent avoir %(k5)s noeuds

Pour information :
 - maille concernée              : %(k3)s
 - son type                      : %(k4)s
 - nombre de noeuds de la maille : %(i2)d

Vérifiez vos données.
"""
    ),
    14: _(
        """AFFE_CARA_ELEM / <%(k1)s> / occurrence %(i1)d
Au moins un élément appartenant au GROUP_MA_POI1 <%(k2)s> n'est pas connecté aux mailles
surfaciques du GROUP_MA.

Pour pouvoir calculer la contribution de la maille, il faut que tous les noeuds de <%(k2)s> soient
en relation avec un seul noeud d'une maille surfacique du GROUP_MA.

Pour information :
 - maille détectée : %(k3)s

Vérifiez vos données.
"""
    ),
    15: _(
        """AFFE_CARA_ELEM / <%(k1)s> / occurrence %(i1)d
Au moins un noeud appartenant à un élément du GROUP_MA surfacique n'est pas connecté à une maille du
GROUP_MA_POI1.

Pour pouvoir répartir la contribution des mailles surfaciques, il faut que tous les noeuds
soient en relation avec une et une seule maille de GROUP_MA_POI1.

Pour information :
 - noeud concerné : %(k2)s

Vérifiez vos données.
"""
    ),
    16: _(
        """AFFE_CARA_ELEM / <%(k1)s> / occurrence %(i1)d
Des éléments appartenant au GROUP_MA_POI1 <%(k2)s> n'ont pas le bon nombre de noeuds.
Les mailles doivent être de type POI1 et posséder 1 seul noeud.

Pour information :
 - maille détectée : %(k3)s

Vérifiez vos données.
"""
    ),
    17: _(
        """AFFE_CARA_ELEM / <%(k1)s> / occurrence %(i1)d
Les mailles appartenant au GROUP_MA sont surfaciques. Vous ne devez pas utiliser
TYPE=LINEIQUE mais TYPE=SURFACIQUE ou TOTALE.

Vérifiez vos données.
"""
    ),
    18: _(
        """AFFE_CARA_ELEM / <%(k1)s> / occurrence %(i1)d
Les mailles appartenant au GROUP_MA sont linéiques. Vous ne devez pas utiliser
TYPE=SURFACIQUE mais TYPE=LINEIQUE ou TOTALE.

Vérifiez vos données.
"""
    ),
    19: _(
        """AFFE_CARA_ELEM / <%(k1)s> / occurrence %(i1)d
Le noeud <%(k5)s> de la maille <%(k3)s> appartenant au GROUP_MA_POI1 <%(k2)s> est connecté
avec un noeud d'une maille surfacique du GROUP_MA qui est déjà connecté à la maille
<%(k4)s> du GROUP_MA_POI1.

Les mailles de <%(k2)s> ne doivent être connecté qu'a un seul noeud des mailles de surface.
Les noeuds des mailles de surface ne doivent être connecté qu'a un seul noeud des mailles POI1.
La relation doit être bijective.

Vérifiez vos données.
"""
    ),
    20: _(
        """
AFFE_CARA_ELEM. Il y a %(i1)d occurrences du mot clef facteur <%(k1)s>.
Entre ces différentes occurrences les GROUP_MA_POI1 ont %(i2)d mailles en communs.
La règle de surcharge est donc appliquée %(i2)d fois.
La liste des mailles surchargées est affichée avec INFO=2.
"""
    ),
    21: _(
        """
AFFE_CARA_ELEM / MASS_REP. Occurrence %(i1)d.

Le nombre des mailles POI1 affectées lors des différentes occurrences de MASS_REP dépasse
le nombre de DIS_T/DIS_TR présent dans le modèle : %(i3)d

Pour information :
- le nombre de maille de type POI1 précédemment affecté par MASS_REP est de %(i4)d
- le nombre de maille de type POI1 dans %(k1)s est %(i2)d

Conseils : Vérifiez que lors de votre AFFE_MODELE, vous n'avez pas oublié d'affecter des
           DIS_T ou DIS_TR.
"""
    ),
    22: _(
        """AFFE_CARA_ELEM / <%(k1)s> / occurrence %(i1)d
Des éléments appartenant au GROUP_MA_POI1 <%(k2)s> ne sont pas dans le modèle.

Pour information :
 - maille détectée : %(k3)s

Vérifiez vos données.
"""
    ),
    23: _(
        """AFFE_CARA_ELEM / <%(k1)s> / occurrence %(i1)d
Une maille dans le groupe <%(k2)s> n'est pas de la bonne topologique.
Vous êtes en 3D, la topologie des mailles dans le groupe doit être identique.

Les mailles de <%(k2)s> doivent être des segments ou des éléments de surfaces.

Pour information :
 - nom de la maille incriminée                       : %(k3)s
 - dimension topologique de la maille incriminée     : %(i3)d
 - type de la maille incriminée                      : %(k4)s

La topologie du groupe est déterminée par la 1ère maille du groupe.
 - nom de la 1ère maille du groupe                   : %(k5)s
 - dimension topologique du groupe                   : %(i2)d
 - type de la 1ère maille du groupe                  : %(k6)s

Vérifiez vos données.
"""
    ),
    24: _(
        """AFFE_CARA_ELEM / RIGI_PARASOL
Pour l'occurrence %(i1)d de RIGI_PARASOL, GROUP_MA = %(k1)s.
La maille %(k2)s est présente plusieurs fois.
Elle n'est prise en compte qu'une seule fois.
"""
    ),
    25: _(
        """AFFE_CARA_ELEM / RIGI_PARASOL
Pour l'occurrence %(i1)d de RIGI_PARASOL, GROUP_MA[_POI1|_SEG2] = %(k1)s.
La maille %(k2)s ne fait pas partie du modèle.

Vérifier l'affection du modèle.
"""
    ),
    26: _(
        """AFFE_CARA_ELEM / RIGI_GRILLE
Pour l'occurrence %(i1)d de RIGI_GRILLE, GROUP_MA = %(k1)s.
La maille %(i2)d n'a pas la dimension topologique égale à 2.
"""
    ),
    27: _(
        """AFFE_CARA_ELEM / RIGI_GRILLE
Pour l'occurrence %(i1)d de RIGI_GRILLE, GROUP_MA_SEG2 = %(k1)s.
Ce groupe contient %(i2)d mailles, mais la dalle est composée de %(i3)d noeuds.

Il faut avoir autant de mailles que de noeuds.
"""
    ),
    28: _(
        """AFFE_CARA_ELEM / RIGI_GRILLE
Pour l'occurrence %(i1)d de RIGI_GRILLE, GROUP_MA_SEG2 = %(k1)s.
La maille %(i2)d n'est pas un SEG2.
"""
    ),
    29: _(
        """AFFE_CARA_ELEM / RIGI_GRILLE
Pour l'occurrence %(i1)d de RIGI_GRILLE, GROUP_MA_SEG2 = %(k1)s.
On a trouvé deux mailles (%(i2)d et %(i3)d) connectés au noeud %(i4)d de la dalle.

Il faut avoir une seule maille SEG2 connecté à chaque noeud de la dalle.
"""
    ),
    30: _(
        """AFFE_CARA_ELEM / RIGI_GRILLE
Pour l'occurrence %(i1)d de RIGI_GRILLE, GROUP_MA_SEG2 = %(k1)s.
La maille %(i2)d n'a aucun noeud commun avec la dalle.
"""
    ),
    31: _(
        """
AFFE_CARA_ELEM. Vous ne pouvez pas affecter des valeurs de type "%(k2)s" au modèle %(k1)s
qui ne contient aucun élément %(k3)s.
"""
    ),
    32: _(
        """
AFFE_CARA_ELEM. Des éléments de type "%(k1)s" sont présents dans le modèle.
Ces éléments n'ont pas été affecté par des caractéristiques de type %(k1)s.
"""
    ),
    33: _(
        """
AFFE_CARA_ELEM.  Erreur(s) rencontrée(s) lors de la vérification des affectations.
"""
    ),
    34: _(
        """
AFFE_CARA_ELEM. Dans le modèle, il y a des éléments de type %(k1)s.
Ces éléments ne peuvent pas être surchargé par une autre forme de
section ou une variation de section le long de leur axe.
    Déjà affecté par : %(k2)s, %(k3)s
    Surchargé par    : %(k4)s, %(k5)s
"""
    ),
    99: _(
        """AFFE_CARA_ELEM / %(k1)s
Il n'est actuellement pas possible d'utiliser un maillage partitionné pour un calcul parallèle.

Vous avez utilisé PARTITIONNEUR="PTSCOTCH", lors du LIRE_MAILLAGE
"""
    ),
}
