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
    44: _("""Le chargement de type vent n'est pas utilisable pour les éléments tuyaux."""),
    45: _(
        """Le chargement défini en repère local est interdit pour les tuyaux : utiliser le repère global."""
    ),
    46: _("""Le comportement élastique de type %(k1)s n'est pas autorisé pour un élément tuyau."""),
    50: _(
        """On ne trouve pas de comportement élastique sur le tuyau. C'est nécessaire pour récupérer la masse volumique."""
    ),
    54: _(
        """MODI_METRIQUE ne peut pas s'appliquer à cause des dimensions du tuyau, en effet, le rapport rayon sur épaisseur est supérieur à %(r1)f."""
    ),
}
