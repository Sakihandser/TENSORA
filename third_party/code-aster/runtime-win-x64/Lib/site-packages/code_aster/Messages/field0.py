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
        """Le champ nodal de sortie est de type complexe alors que celui d'entrée est de type réel. On ne peut pas le transférer."""
    ),
    2: _(
        """Le champ nodal de sortie ne repose pas sur le même maillage que le champ nodal d'entrée. On ne peut pas le transférer."""
    ),
    3: _(
        """Sur le champ de type %(k1)s extrait de la structure de données résultat, on ne peut pas remplir toutes les composantes car la numérotation fournie ou provenant des matrices n'est pas cohérente avec celle du champ."""
    ),
    4: _(
        """Certaines composantes du déplacement n'ont pas été remplies car la numérotation est incohérente entre DEPL et INCR_DEPL."""
    ),
    5: _(
        """Le vecteur venant du chargement n'a pas pu être assemblé et certaines composantes n'ont pas été remplies. En général le problème vient entre de l'incohérence entre le modèle de calcul et le modèle ayant servi à construire le chargement."""
    ),
    6: _(
        """La numérotation du champ de type %(k1)s de l'état initial n'est pas cohérente avec la numérotation utilisée dans le calcul."""
    ),
    7: _(
        """La numérotation du champ donné par EXCIT_RESU n'est pas cohérente avec la numérotation utilisée dans le calcul."""
    ),
    8: _(
        """La numérotation du champ donné pour le chargement DIDI n'est pas cohérente avec la numérotation utilisée dans le calcul."""
    ),
    9: _(
        """La numérotation des champs donnés dans la structure de données résultat n'est pas cohérente avec la numérotation utilisée dans le calcul."""
    ),
    #     11: _(
    #         """Maille: %(i1)d - Nombre de points précédent: %(i2)d - Nombre de points courant: %(i3)d"""
    #     ),
    #     12: _(
    #         """Maille: %(i1)d - Nombre de composantes précédent: %(i2)d - Nombre de composantes courant: %(i3)d"""
    #     ),
    14: _(
        """Sur le champ de type %(k1)s extrait de la structure de données résultat, la numérotation fournie ou provenant des matrices n'est pas cohérente avec celle du champ."""
    ),
    15: _(
        """La numérotation du champ n'est pas cohérente avec celle de la matrice. On ne peut pas faire la multiplication."""
    ),
    16: _(
        """La numérotation du champ fourni pour le chargement n'est pas cohérente avec celle du calcul. On ne peut pas remplir toutes les composantes."""
    ),
    30: _(
        """Lors de la copie d'un champ nodal, certaines composantes du champ final n'était pas présentes dans le champ initial et ont été mises à zéro."""
    ),
    31: _("""Seuls les champs réels sont traités par la copie."""),
    32: _("""Seuls les champs discrétisés aux points d'intégration sont traités par la copie."""),
    33: _(
        """
La copie du champ en utilisant un champ de référence a échoué car ils ne reposent pas sur le même maillage.
"""
    ),
    34: _(
        """
Échec lors de la copie du champ, la mise à zéro des composantes nécessite de renseigner le type de paramètre.
"""
    ),
    35: _(
        """
Échec lors de la copie du champ.
"""
    ),
    40: _(
        """
Le champ à copier a un nombre différent de composantes avec le champ de référence.
"""
    ),
    41: _(
        """
Le champ à copier a un nombre différent de points d'intégration avec le champ de référence.
"""
    ),
    42: _(
        """
Le champ à copier a a un nombre différent de sous-points avec le champ de référence.
"""
    ),
}
