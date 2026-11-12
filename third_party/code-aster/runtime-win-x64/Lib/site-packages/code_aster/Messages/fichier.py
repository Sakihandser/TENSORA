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
Fichier inexistant : '%(k1)s'
"""
    ),
    2: _(
        """
L'exécution du fichier '%(k1)s' a échoué.

Détails :

    %(k2)s
"""
    ),
    3: _(
        """
L'exécution du fichier '%(k1)s' a échoué.

Risques & conseils :
  Si l'erreur indique qu'une commande n'est pas trouvée, vérifiez que le fichier
  à inclure importe les commandes avec :

    %(k3)s

Détails :

    %(k2)s
"""
    ),
}
