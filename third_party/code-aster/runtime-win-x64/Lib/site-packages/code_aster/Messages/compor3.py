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
        """RGI_BETON_BA : les paramètres %(k1)s, %(k2)s et %(k3)s sont tous nuls.
 Ils engendrent un vecteur nul."""
    ),
    2: _("""Dans le KIT_DDI, on ne peut pas coupler GRANGER avec %(k1)s."""),
    3: _("""Dans le KIT_DDI, on ne peut pas coupler BETON_UMLV avec %(k1)s."""),
    4: _("""Dans le KIT_DDI, on ne peut pas coupler GLRC avec %(k1)s."""),
    6: _("""Dans le KIT_DDI, la loi de fluage %(k1)s n'est pas autorisée."""),
    8: _(
        """Vous avez demandé à utiliser un comportement avec des phases métallurgiques de type %(k1)s, mais le matériau est défini avec des variables de commande de type %(k2)s."""
    ),
    9: _(
        """La valeur du séchage de référence doit être nulle pour la loi de comportement %(k1)s."""
    ),
    10: _(
        """RGI_BETON_BA : Le taux d'armature est inférieur ou égal à 1.
 La somme des paramètres %(k1)s à %(k2)s doit être supérieure à 1."""
    ),
    12: _(
        """
 Erreur lors de la diagonalisation de la matrice :
                %(r1)f, %(r2)f, %(r3)f
                %(r4)f, %(r5)f, %(r6)f
                %(r7)f, %(r8)f, %(r9)f
"""
    ),
    14: _(
        """
 Ne devrait pas être nul
 mise à zéro de la pression capillaire
"""
    ),
    15: _(
        """
 Attention  %(r1)f
"""
    ),
    17: _(
        """
 Cas de pression intraporeuse imprévue : %(r1)f %(r2)f
"""
    ),
    18: _(
        """
 Delta plus grand que la racine carrée de 3 : impossible
"""
    ),
    19: _(
        """
 DP atteignable par traction tri-axiale
 Augmenter RC ou diminuer RT effective
                RT = %(r1)f
                RC = %(r2)f
                RC minimum = %(r3)f
"""
    ),
    20: _(
        """
 Sous itération radiale désactivée
 contrôler direction écoulement
"""
    ),
    21: _(
        """
 TAU < TAU limite/1000
 Atteinte du critère DP sans cisaillement
                valeur réelle = %(r1)f
                valeur adoptée = %(r2)f
"""
    ),
    22: _(
        """
 critère DP annulé alors que %(r1)f >%(r2)f
"""
    ),
    23: _(
        """
 Dilatance excessive > %(r1)f
"""
    ),
    26: _(
        """
 Problème lors du tir viscoélastique dans FLUA_ENDO_PORO
"""
    ),
    27: _(
        """
 Nombre d'itération maximum atteint :  %(i1)d
"""
    ),
    28: _(
        """
 FLUA_ENDO_PORO : cas élasticité anisotrope
 Changement de base pour la loi de comportement non programmé
"""
    ),
    29: _(
        """
 FLUA_ENDO_PORO : cas élasticité anisotrope
 Changement de base résistances non programmé
"""
    ),
    30: _(
        """
  FLUA_ENDO_PORO : problème dans la résolution du retour radial
"""
    ),
    31: _(
        """
 FLUA_ENDO_PORO : nombre maximum de sous itération atteint : %(i1)d
"""
    ),
    32: _(
        """
 Critère non prévu dans fluage3d
"""
    ),
    33: _(
        """
 FLUA_ENDO_PORO : nombre d'itération maximum %(i1)d atteint :
             compteur de sous itération plastique = %(i2)d
             nombre d'itération multiplicateur < 0 = %(i3)d

 Essayez de réduire la vitesse de chargement ou augmentez le nombre d'itérations maximum

"""
    ),
    34: _(
        """
 FLUA_ENDO_PORO : erreur
"""
    ),
    35: _(
        """
 Taille du problème trop grand %(i1)d et %(i1)d
"""
    ),
    36: _(
        """
 FLUA_ENDO_PORO : pivot nul dans gauss_3d :
            pivot maximum = %(r1)f
            ligne = %(i1)d
"""
    ),
    37: _(
        """
 Matrices d'élasticité anisotropes non programmées
"""
    ),
    38: _(
        """
 Données incohérentes pour l'hydratation
 0<HYDR<1  0<HYDR_S<1
"""
    ),
    39: _(
        """
 calcul de 1-DT non vérifié
"""
    ),
    40: _(
        """
 Avec la loi de comportement %(k1)s, le paramètre %(k2)s de ELAS doit être nul.
"""
    ),
    50: _(
        """
Loi de comportement BETON_RAG :
Au temps %(r1)f, une grandeur liée au séchage est inférieure à %(r2)f, ce qui n'a pas de sens physique.
    Séchage au temps précédent : %(r3)f
    Séchage au temps actuel    : %(r4)f
 """
    ),
    51: _(
        """
Loi de comportement BETON_RAG :
Vous avez activé le phénomène de RAG lors d'un précédent calcul.
Vous ne pouvez pas poursuivre avec un calcul sans RAG.
 """
    ),
    52: _(
        """
Loi de comportement BETON_RAG :
Vous voulez activer le phénomène de RAG, il faut donner un champ de séchage ET de température.
 """
    ),
    53: _(
        """
Loi de comportement BETON_RAG :
Le coefficient %(k1)s vaut %(r1)f. Il doit être dans l'intervalle [%(r2)f , %(r3)f]
 """
    ),
    54: _(
        """
Loi de comportement BETON_RAG :
Le(s) paramètre(s) %(k1)s est/sont hors du domaine de validité.
 """
    ),
    55: _(
        """
Loi de comportement BETON_RAG :
Vous ne pouvez pas activer ou désactiver la non-linéarité visqueuse en cours de calcul.
Soit le paramètre FLUA_KAPPAI a été précisé alors qu'il ne devait pas l'être, soit il n'a pas été précisé alors qu'il devait l'être."""
    ),
    83: _(
        """
 Vous utilisez le modèle BETON_UMLV avec un modèle d'endommagement.
 La mise à jour des contraintes sera faite suivant les déformations totales et non pas suivant un schéma incrémental.
"""
    ),
}
