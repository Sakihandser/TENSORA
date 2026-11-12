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
On ne trouve pas les températures alors qu'on a la température de référence.
"""
    ),
    2: _(
        """
On ne prend pas en compte la dilatation thermique orthotrope pour COQUE_3D.
"""
    ),
    3: _(
        """
L'élasticité de type %(k1)s n'est pas traitée.

Conseil :
 Pour définir une COQUE_3D orthotrope, il ne faut pas utiliser
 la commande DEFI_COMPOSITE.
 Seule la définition du comportement ELAS_ORTH est nécessaire.
"""
    ),
    4: _(
        """
On renseigne la température mais on n'a pas le coefficient de dilatation thermique.
"""
    ),
}
