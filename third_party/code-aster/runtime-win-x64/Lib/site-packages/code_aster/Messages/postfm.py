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
        """Le groupe de noeud %(k1)s définissant le fond de fissure contient %(i1)d noeuds.
Il devrait contenir un unique noeud."""
    ),
    2: _(
        """Il n'est pas possible de sélectionner un matériau pour le noeud de fond de fissure.
Plusieurs matériaux sont définis sur les éléments connexes. If faut que les éléments connexes soit affecté par le même matériau.
"""
    ),
    3: _(
        """La loi de ténacité %(k1)s n'a pas été trouvé pour le matériau en fond de fissure.

Conseils :
Vérifiez que le matériau utilisé est bien défini avec le mot-clé facteur %(k1)s."""
    ),
    4: _("""Il n'a pas été possible de récupérer le matériau en fond de fissure."""),
    5: _(
        """On ne trouve pas de champ matériau dans le résultat fourni sous le mot clé RESULTAT."""
    ),
}
