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
 Pour le chargement thermique ECHANGE_PAROI, le type de maille utilisé n'est pas possible.
 Vérifiez que vous avez correctement défini la paroi.
"""
    ),
    2: _(
        """
 Pour le chargement thermique ECHANGE_PAROI, le modèle fourni doit être homogène
 en dimension : 3D, 2D ou AXIS.
"""
    ),
    5: _(
        """
Erreur lors de l'opération LIAISON_CYCLE.
L'élément %(k1)s n'est pas du bon type.
Si vous êtes en deux dimensions, les éléments doivent être des segments.
Si vous êtes en trois dimensions, les éléments doivent être des triangles ou des quadrangles.
"""
    ),
    6: _(
        """Lors de l'évaluation du chargement VITE_FACE, la normale calculée est nulle. Le maillage est probablement incorrect."""
    ),
    7: _(
        """On ne peut pas donner la direction du chargement VITE_FACE dans le cas d'une formulation de type %(k1)s."""
    ),
    82: _(
        """
Il y a trop de chargements avec l'option %(k1)s pour calculer toutes les matrices élémentaires.
"""
    ),
    84: _(
        """
Vous demandez le calcul de la matrice correspondant à l'option ONDE_FLUI.
Mais on ne peut rien calculer, faute de données.
Il faut fournir en argument du mot clé CHARGE au moins une charge mécanique qui utilise le mot clé ONDE_FLUI.
"""
    ),
    94: _(
        """
On ne peut pas appliquer un cisaillement 2d sur une modélisation 3D.
"""
    ),
}
