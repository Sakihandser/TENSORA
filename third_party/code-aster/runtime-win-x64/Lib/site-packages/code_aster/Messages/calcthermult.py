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
Le modèle thermique renseigné dans la commande CALC_THER_MULT est défini sur le maillage %(k1)s qui est un maillage quadratique (d'ordre 2). 
Ce choix entraîne des erreurs de résolution en thermique. Il est vivement conseillé d'utiliser un maillage linéarisé (d'ordre 1) pour les analyses thermiques.
"""
    ),
    2: _(
        """
L'intersection des groupes de mailles renseignés dans le mot-clé GROUP_MA des cas de chargement de type choc unitaire (TYPE_CHARGE="CHOC_UNIT") de la commande CALC_THER_MULT n'est pas nulle.
Il ne doit pas y avoir d'éléments communs entre deux cas de charge de type choc unitaire.
"""
    ),
}
