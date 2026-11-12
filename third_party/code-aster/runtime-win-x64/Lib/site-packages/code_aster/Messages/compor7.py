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
        """Problème lors du calcul des déformations dues à la pression du fluide. Seul un matériau élastique isotrope est autorisé."""
    ),
    2: _(
        """Problème lors du calcul des déformations anélastiques avec des variables de commande. Il manque la variable %(k1)s à l'instant précédent ou à l'instant suivant."""
    ),
    3: _(
        """La loi ELAS en 1D est appelée avec COMP_ELAS mais elle reste malgré tout incrémentale (par souci de compatibilité avec le chargement de précontrainte)."""
    ),
    8: _(
        """
Le calcul est thermo mécanique. Mais il manque la température de référence. On ne peut donc pas calculer de déformation thermique.
"""
    ),
}
