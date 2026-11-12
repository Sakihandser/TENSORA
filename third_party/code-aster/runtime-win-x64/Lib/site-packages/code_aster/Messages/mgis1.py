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
    1: _("""Les comportements MFront ne fonctionnent qu'en déformation mécanique."""),
    2: _("""On ne peut pas utiliser de matériau anisotrope avec la modélisation %(k1)s."""),
    3: _(
        """Attention, la loi de comportement META_LEMA_ANI utilise les déformations totales et non pas les déformations mécaniques comme variables d'entrée dans MFront. Le calcul en post-traitement des grandeurs de déformation EPVC_* et EPME_* est donc faux."""
    ),
    19: _(
        """Le nom de la variable interne %(k1)s est trop long, il va être tronqué en %(k2)s. Il faudra vérifier qu'il n'y a pas de risque de confusion avec d'autres variables internes."""
    ),
    20: _(
        """Une variable interne de type vectorielle contient plus de composantes que la dimension maximale autorisée."""
    ),
    21: _(
        """Une variable interne de type tensorielle (symétrique) contient plus de composantes que la dimension maximale autorisée."""
    ),
    22: _(
        """Une variable interne de type tensorielle (non symétrique) contient plus de composantes que la dimension maximale autorisée."""
    ),
    23: _(
        """Une variable interne de type quelconque contient plus de composantes que la dimension maximale autorisée."""
    ),
    24: _("""Une variable interne est d'un type inconnu."""),
}
