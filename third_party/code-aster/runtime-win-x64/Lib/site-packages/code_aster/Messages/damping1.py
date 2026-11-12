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
    1: _("""Échec dans le calcul des matrices élastiques pour l'amortissement."""),
    19: _("""Il y a plus d'amortissements modaux (AMOR_MODAL) que de modes."""),
    20: _(
        """La prise en compte d'un amortissement équivalent a un amortissement modal par le mot-clé AMOR_MODAL nécessite
  une base de modes pré calculée sur laquelle est décomposé l'amortissement.
  Vérifiez qu'une base de modes est bien renseignée sous le mot-clé MODE_MECA."""
    ),
    21: _(
        """Aucune valeur d'amortissement modal n'a été trouvée sous le mot-clé AMOR_MODAL.
  Cette information est nécessaire pour la prise en compte d'un amortissement de type modal."""
    ),
    30: _(
        """Vous faites de l'amortissement modal.
Il y a %(i1)d  modes dans la structure MODE_MECA.
Le nombre de modes (mot-clef NB_MODE dans AMOR_MODAL) vaut %(i2)d.
On prend donc %(i3)d modes."""
    ),
}
