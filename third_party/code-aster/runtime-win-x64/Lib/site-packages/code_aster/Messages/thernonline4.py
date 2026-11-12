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
Il y a un chargement de type convection dans les chargements appliqués.
Ce n'est possible qu'avec THER_NON_LINE_MO.
"""
    ),
    2: _(
        """
On ne peut pas utiliser d'éléments de structures (coques, plaques, poutres) dans la commande THER_NON_LINE_MO.
"""
    ),
    3: _(
        """
Le modèle contient des éléments spécifiques au traitement du séchage. Ils sont incompatibles avec
la commande THER_NON_LINE.

Conseil : utilisez la commande SECH_NON_LINE.
"""
    ),
    4: _(
        """
La commande SECH_NON_LINE ne fonctionne qu'avec un modèle contenant uniquement
des éléments spécifiques au traitement du séchage.
"""
    ),
    85: _(
        """
   Arrêt : absence de convergence au numéro d'instant : %(i1)d
                                  lors de l'itération : %(i2)d
"""
    ),
}
