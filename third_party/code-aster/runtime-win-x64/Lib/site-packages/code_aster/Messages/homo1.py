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
Le maillage contient plusieurs ( %(i1)d ) zones non-connectées.
"""
    ),
    2: _(
        """
La dimension du maillage n'est pas 3 : %(i1)d
"""
    ),
    3: _(
        """
La dimension de l'espace n'est pas 3 : %(i1)d
"""
    ),
    4: _(
        """
Le groupe %(k1)s ne fait pas partie du maillage
"""
    ),
    5: _(
        """
L'intersection des groupes n'est pas vide
"""
    ),
    6: _(
        """
Le champ %(k1)s n'existe pas dans le concept résultat %(k2)s.
"""
    ),
    7: _(
        """
On ne peut pas créer le groupe '%(k1)s'.
Le maillage n'est probablement pas inscrit dans un parallélépipède
"""
    ),
    8: _(
        """
Le matériau '%(k1)s' est obligatoire pour '%(k2)s' ( '%(k3)s' )
"""
    ),
    9: _(
        """
Le matériau '%(k1)s' ou '%(k2)s' est obligatoire pour '%(k3)s' ( '%(k4)s' )
"""
    ),
    10: _(
        """
Le paramètre '%(k1)s' est obligatoire pour le matériau '%(k2)s' ( '%(k3)s' )
"""
    ),
    11: _(
        """
Le paramètre '%(k1)s' du matériau '%(k2)s' ( '%(k3)s' ) n'est pas CONSTANT ou FONCTION de '%(k4)s'
"""
    ),
    12: _(
        """
Le paramètre '%(k1)s' n'est pas défini pour tous les matériaux
"""
    ),
    13: _(
        """
Le paramètre '%(k1)s' n'est pas une fonction.
"""
    ),
    14: _(
        """
Le paramètre '%(k1)s' n'est pas identique pour l'ensemble des matériaux affectés.
"""
    ),
    15: _(
        """
L'origine du maillage ('%(r1)f', '%(r2)f', '%(r3)f') ne coïncide pas avec l'origine de l'espace cartésien.
"""
    ),
    16: _(
        """
Les correcteurs fournis ne respectent pas le type d'homogénéisation '%(k1)s'.
"""
    ),
    17: _(
        """
Le fichier fourni ne contient pas de correcteurs.
"""
    ),
    18: _(
        """
Le point demandé est partagé par plusieurs (%(i1)d) domaines du calcul distribué et cela peut avoir une influence sur les valeurs interpolées.

Conseil :
Vous pouvez sauvegarder le résultat dans un fichier unique puis le recharger en séquentiel.
"""
    ),
    19: _(
        """
Le maillage fourni %(k1)s est de type parallèle et n'est pas supporté par cette fonctionnalité.
"""
    ),
    20: _(
        """
La pression fournie n'est pas une fonction du temps.
"""
    ),
    21: _(
        """
Le maillage fourni, %(k1)s, est linéaire. Il est recommandé d'utiliser un maillage quadratique pour cette application.
"""
    ),
    22: _(
        """
Le point demandé est hors du domaine.
"""
    ),
}
