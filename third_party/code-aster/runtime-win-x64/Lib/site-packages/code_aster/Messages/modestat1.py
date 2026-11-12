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
Aucun noeud n'a été sélectionné pour la commande MODE_STATIQUE.
"""
    ),
    2: _(
        """
Pour le mot clé MODE_STAT, le degré de liberté défini ci-dessus n'est pas bloqué.
"""
    ),
    3: _(
        """
Pour le mot clé FORCE_NODALE, le degré de liberté défini ci-dessus n'est pas libre.
"""
    ),
    4: _(
        """
Pour le mot clé PSEUDO_MODE, le degré de liberté défini ci-dessus est de type Lagrange.
"""
    ),
    5: _(
        """
Pour le mot clé MODE_INTERF, le degré de liberté défini ci-dessus n'est pas bloqué.
"""
    ),
    6: _(
        """
Pour le mot clé PSEUDO_MODE avec NOM_APPUI, le degré de liberté défini ci-dessus est présent 
dans 2 occurrences.

Vous utilisez le mot clé NOM_APPUI, un degré de liberté ne peux appartenir qu'à un seul appui.
"""
    ),
    7: _(
        """
NOM_APPUI %(k1)s apparaît dans plusieurs occurrences du mot clé PSEUDO_MODE.
"""
    ),
    8: _(
        """
Arrêt dans MODE_STATIQUE, problème avec au moins un degré de liberté.
"""
    ),
}
