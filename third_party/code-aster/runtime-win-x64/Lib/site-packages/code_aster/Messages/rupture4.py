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
Résultat du test faux pour le produit vectoriel %(r1)f.
Il s'agit d'un test purement informatique.
On continue le calcul.
"""
    ),
    5: _(
        """
La valeur de NUME_ORDRE n'est pas valide.
"""
    ),
    6: _(
        """
La valeur de INST n'est pas valide.
"""
    ),
    7: _(
        """
Seule l'option GROUP_NO ou NB_POINT_FOND peut être sélectionnée.
"""
    ),
    8: _(
        """
Erreur sur le nombre de noeuds de réduction.
"""
    ),
    9: _(
        """
Le nombre de contours (NB_COUCHES) doit  être supérieur ou égal à 4.
"""
    ),
    10: _(
        """
Il est nécessaire de définir au moins une lèvre.
"""
    ),
    11: _(
        """
Le nombre de contours (NB_COUCHES) doit être inférieur à 20.
"""
    ),
    12: _(
        """
Le nombre de contours (NB_COUCHES) doit être inférieur à 10.
"""
    ),
    13: _(
        """
Le nombre de contours (NB_COUCHES) doit  être supérieur ou égal à 2.
"""
    ),
    14: _(
        """
Pour utiliser METHODE_2D, le résultat mécanique donné en entrée
doit être de dimension 3.
"""
    ),
    15: _(
        """
Pour utiliser METHODE_2D, le maillage cible doit être de dimension 2.
"""
    ),
    16: _(
        """
Erreur dans la projection 3D vers 2D : incohérence dans le nombre de mailles.
"""
    ),
    17: _(
        """
Incohérence dans les paramètres d'entrée pour METHODE_2D : il faut donner
autant de MAILLAGE que de NOM_MAIL_MED
"""
    ),
    18: _(
        """
Dans le cas DEFORMATION = "GDEF_LOG", le paramètre LIST_NUME_SIEF doit être
de dimension 4 en 2D ou de dimension 6 en 3D"""
    ),
    19: _(
        """
L'impression d'un résultat n'est pas compatible avec
l'utilisation de plusieurs paramètres matériaux,
ou dans le cas METHODE_2D la projection sur plusieurs plans.
        """
    ),
    20: _(
        """
Incohérence dans les maillages donnés en entrée : si le maillage 3D de la
structure résultat est quadratique (ou linéaire),
alors le maillage 2D pour METHODE_2D doit aussi être quadratique (ou linéaire).
        """
    ),
    21: _(
        """
METHODE_2D doit nécessairement être utilisée avec FILTRE_SIGM = "SIGM_ELMOY"
        """
    ),
    22: _(
        """
Plus de 5 itérations ont été nécessaires pour construire le projecteur
utilisé dans METHODE_2D. Vérifiez la cohérence des maillages 2D et 3D.
        """
    ),
    23: _(
        """
Dans METHODE_2D, la projection a échoué :
    - Vérifier la cohérence des maillages donnés en entrée.
    - Augmenter PRECISION.
        """
    ),
    24: _(
        """
POST_BEREMIN / WEIBULL_FO : il manque la composante X1 dans le champ %(k1)s.

L'utilisation d'un champ scalaire pour définir les paramètres SIGM_REFE ou SIGM_SEUIL
n'est prévue que pour une dépendance de ces paramètres à la position.

Ceci passe par la définition d'un champ de type NOEU_NEUT_R ou ELGA_NEUT_R
dont la composante X1 doit être la valeur de SIGM_REFE ou SIGM_SEUIL.
        """
    ),
    25: _(
        """
POST_BEREMIN / SIGM_CORR : il manque le champ UT01_ELGA et/ou sa composante X1
dans le concept résultat donné sous le mot-clé SIGM_CORR.

Pour utiliser une contrainte effective corrigée dans le calcul de la contrainte de WEIBULL,
l'utilisateur doit donner sous le mot-clé SIGM_CORR un concept résultat
contenant à chaque instant le champ de contrainte corrigée aux points de Gauss.

Ceci passe par la définition d'un champ de type UT01_ELGA dont la composante
X1 doit être la valeur de la contrainte corrigée désirée.
        """
    ),
    26: _(
        """
POST_BEREMIN / SIGM_CORR : le champ de contrainte principale maximale corrigée donné en entrée
sous SIGM_CORR n'est pas défini sur tout ou partie du groupe de mailles
du post-traitement de la contrainte de WEIBULL.

Veillez à définir ce champ sur tous les groupes de mailles utilisés sous le mot-clé WEIBULL(_FO).
        """
    ),
    27: _(
        """
Il n'est pas possible d'utiliser TYPE_SEUIL = "RESTREINT" avec un paramètre SIGM_SEUIL fonction ou champ.
        """
    ),
    28: _(
        """
Le groupe de mailles demandé GROUP_MA = %(k1)s n'existe pas !
        """
    ),
    29: _(
        """
Dans METHODE_2D, le groupe de noeuds demandé GROUP_NO = %(k1)s n'existe pas !
        """
    ),
    30: _(
        """
Dans METHODE_2D, il est nécessaire de renseigner le mot-clé FISSURE si on donne en entrée plus d'un GROUP_NO.
        """
    ),
}
