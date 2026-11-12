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
Le fichier de sortie de IMPR_OAR est manquant.
"""
    ),
    2: _(
        """
IMPR_OAR prend au choix soit des résultats thermo-mécaniques, soit des résultats mécaniques.
"""
    ),
    3: _(
        """
Le modèle choisi pour l'opérande MODELE de la commande IMPR_OAR doit être un modèle de type mécanique.
"""
    ),
    4: _(
        """
Les instants thermiques suivants n'ont pas été imprimés, faute d'instants mécaniques correspondants : %(k1)s.
"""
    ),
}
