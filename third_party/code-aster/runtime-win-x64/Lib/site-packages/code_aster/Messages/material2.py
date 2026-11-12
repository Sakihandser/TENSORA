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
    4: _("""Paramètres des propriétés %(k1)s:"""),
    5: _(
        """
Les caractéristiques élastiques de MFront sont anisotropes, mais pas celles du mot-clef ELAS.
Il n'est pas possible de vérifier la cohérence des caractéristiques.
"""
    ),
    6: _(
        """
Les caractéristiques élastiques de MFront sont isotropes, mais pas celles du mot-clef ELAS.
Il n'est pas possible de vérifier la cohérence des caractéristiques.
"""
    ),
    7: _(
        """
Les caractéristiques élastiques de MFront sont des fonctions, mais pas celles du mot-clef ELAS.
Il n'est pas possible de vérifier la cohérence des caractéristiques.
"""
    ),
    8: _(
        """
Les caractéristiques élastiques de MFront sont des scalaires, mais pas celles du mot-clef ELAS.
Il n'est pas possible de vérifier la cohérence des caractéristiques.
"""
    ),
    10: _(
        """
Vérification de la positivité de la matrice d'élasticité. Il faut renseigner le coefficient E_N dans les cas des déformations planes et de l'axisymétrie.
On ne regarde donc que le cas des contraintes planes.
"""
    ),
    12: _(
        """
Les caractéristiques élastiques de MFront sont différentes de celles du mot-clef ELAS.
MFront - Caractéristique: %(k1)s utilisant la fonction %(k3)s.
ELAS   - Caractéristique: %(k2)s utilisant la fonction %(k4)s.
On ne peut vérifier que la cohérence que si les deux fonctions ont le même nom.
"""
    ),
    14: _(
        """
Les caractéristiques élastiques de MFront sont différentes de celles du mot-clef ELAS.
MFront - Caractéristique: %(k1)s utilisant la valeur %(r1)19.12e.
ELAS   - Caractéristique: %(k2)s utilisant la valeur %(r2)19.12e.
"""
    ),
    15: _(
        """On ajoute les propriétés inexistantes dans le mot-clef facteur ELAS à partir des données de MFront."""
    ),
    16: _(
        """On ne sait pas gérer le cas de l'élasticité orthotrope quand il y a un coefficient de dilatation thermique."""
    ),
    20: _(
        """
La matrice d'élasticité orthotrope ou isotrope transverse est non définie positive
(au moins une valeur propre négative). Si vous êtes sur une modélisation
isoparamétrique (pas d'éléments de structure), vous avez probablement fait une erreur.

Conseil :
    Vérifiez vos données matériau.
"""
    ),
    51: _(
        """
 Vous utilisez la variable de commande de température alors que votre problème est couplé.
 Ce n'est pas possible.
"""
    ),
    52: _(
        """
 Vous utilisez la variable de commande de pression capillaire alors que votre problème est couplé.
 Ce n'est pas possible.
"""
    ),
    60: _(
        """
Erreur utilisateur dans la commande AFFE_MATERIAU / CHAM_MATER
  Le maillage %(k1)s sur lequel repose le champ matériau %(k2)s est différent du maillage
  %(k3)s transmis dans AFFE_MATERIAU
"""
    ),
    61: _(
        """
  Attention : le champ matériau %(k1)s renseigné sous le mot-clé CHAM_MATER contient des variables de
  commande. Elles ne seront pas prises en compte ; seules les matériaux le seront.
"""
    ),
}
