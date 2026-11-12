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
Erreur lors de la vérification de la cohérence entre les champs de variables internes.
Le champ des variables internes ne repose pas sur le même maillage que le comportement.
"""
    ),
    2: _(
        """
Lors de la vérification des champs de variables internes, on a constaté une incohérence.
Un comportement est affecté sur une maille qui n'était pas affectée précédemment.
Pour avoir la liste des mailles concernées, relancer le calcul en utilisant INFO=2.
"""
    ),
    3: _(
        """
Lors de la vérification des champs de variables internes, on a constaté une incohérence.
Le comportement est modifié sur une maille. On ne peut faire ce changement que dans quelques cas très particuliers :
    - LEMAITRE <-> VMIS_ISOT_XXXX
    - ELAS     <-> XXXX
Ce n'est pas le cas ici. Pour avoir la liste des mailles et les relations de comportement concernées, relancer le calcul en utilisant INFO=2.
"""
    ),
    4: _(
        """
Lors de la vérification des champs de variables internes, on a constaté une incohérence.
Le nombre de sous-points d'intégration n'est pas le même.
Pour avoir la liste des mailles concernées, relancer le calcul en utilisant INFO=2.
"""
    ),
    5: _(
        """
Lors de la vérification des champs de variables internes, on a constaté une incohérence.
Le nombre de variables internes n'est pas le même. On ne peut faire ce changement que dans quelques cas très particuliers :
    - LEMAITRE <-> VMIS_ISOT_XXXX
    - ELAS     <-> XXXX
Ce n'est pas le cas ici. Pour avoir la liste des mailles et les relations de comportement concernées, relancer le calcul en utilisant INFO=2.
"""
    ),
    6: _(
        """La présence d'un comportement de type MFront ne permet pas d'utiliser NOM_VARI, utilisez NOM_CMP."""
    ),
    7: _(
        """La présence d'un comportement de type MFront ne permet pas d'utiliser IMPR_NOM_VARI."""
    ),
    8: _("""Un champ de température doit être associé au matériau utilisant BETON_BURGER."""),
    9: _("""Un champ de séchage/humidité doit être associé au matériau utilisant BETON_BURGER."""),
    10: _(
        """Maille: %(k1)-8s - Cette maille appartient aux groupes de mailles suivants : %(k2)s %(k2)s %(k3)s %(k3)s."""
    ),
    11: _("""Comportement précédent: %(k1)-16s - Comportement courant: %(k2)-16s"""),
    12: _("""Nombre de sous-points précédent: %(i1)d - Nombre de sous-points courant: %(i2)d"""),
    13: _(
        """Nombre de variables internes précédent: %(i1)d - Nombre de variables internes courant: %(i2)d"""
    ),
    14: _(
        """
Dans l'occurrence numéro %(i1)d du mot-clé COMPORTEMENT est appelée sur une modélisation type C_PLAN native,
avec un coefficient de Poisson fonction.
Cette combinaison est connue comme donnant des résultats imprécis voir faux, et sera corrigée dans les versions ultérieures.
        """
    ),
    15: _(
        """
        L'intégration locale de loi de comportement DRUCK_PRAG_N_A n'admet pas une unique solution : vérifier les données matériaux.
        """
    ),
    16: _(
        """
La valeur de RESI_INTE est renseignée à <%(r1)19.12e> dans le fichier de commande.
Elle est supérieure à la valeur originelle <%(r2)19.12e> de MFront.
L'intégration de la loi de comportement sera donc moins précise.
        """
    ),
    17: _(
        """
Le nombre maximal d'itérations d'intégration de la loi de comportement
est mis à %(i2)d par le fichier de commande, à la place de la valeur
originelle %(i1)d de MFront.
        """
    ),
}
