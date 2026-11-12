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
        """Pour nommer le nouvel élément, le nom est trop long, il faut changer PREF_NUME ou PREF_MAILLE."""
    ),
    2: _(
        """La commande CREA_MAILLAGE tente de créer une maille appelée %(k1)s mais cette maille existe déjà dans le maillage.
  Pour éviter cette erreur, vous pouvez changer la valeur de PREF_MAILLE ou PREF_NUME.
  """
    ),
    4: _(
        """Vous avez demandé la transformation de certaines mailles de type %(k1)s mais il n'y a aucune maille à transformer."""
    ),
    5: _(
        """Vous avez demandé la transformation de certaines mailles mais il n'y a aucune maille à transformer."""
    ),
    23: _("""Le noeud central d'un élément SEG3 n'est pas au milieu de la maille."""),
}
