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
On n'a pas trouvé d'élément fini pour le raccord MASSIF. Ce cas n'est pas disponible pour le moment.
"""
    ),
    2: _(
        """
Les mailles portant une modélisation HHO doivent être uniquement utilisées uniquement dans GROUP_MA_MAIT.
"""
    ),
    3: _(
        """
Le raccord massif avec la méthode NITSCHE est pour l'instant limité à utiliser une modélisation HHO dans GROUP_MA_MAIT.
"""
    ),
    4: _(
        """
Aucun modèle n'est affecté à la maille esclave %(i1)d.
"""
    ),
    5: _(
        """
Aucun modèle n'est affecté à la maille maître %(i1)d.
"""
    ),
}
