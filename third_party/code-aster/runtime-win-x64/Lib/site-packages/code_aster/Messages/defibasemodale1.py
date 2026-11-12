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
L'unique occurrence de RITZ doit obligatoirement contenir MODE_MECA.
Si BASE_MODALE est utilisée, il faut aussi donner les modes d'interface par MODE_INTF.
Et si on veut MODE_INTF uniquement, il faut quand même ajouter une 2ème occurrence
de RITZ avec MODE_MECA et NMAX_MODE mis à 0.
"""
    ),
    2: _(
        """
La base modale est composée de vecteurs complexes. Pour la projection, seule leur partie réelle
sera utilisée. 
"""
    ),
    9: _("""Le mot-clé NUME_REF est obligatoire quand DEFI_BASE_MODALE n'est pas ré-entrant."""),
    31: _(
        """
Il y a un problème de cohérence entre le nombre de concepts MODE_MECA et la liste
des NMAX_MODE:
 Nombre de concepts MODE_MECA dans la liste MODE_MECA     : %(i1)d
 Nombre de valeurs de la liste NMAX_MODE                  : %(i2)d
 Les deux listes doivent avoir la même taille.
"""
    ),
    50: _("""Le total des modes défini dans RITZ est nul. Il faut au moins un mode."""),
    51: _(
        """
Deux occurrences de RITZ doivent obligatoirement et exactement contenir une fois
le mot-clé MODE_INTF. Les autres possibilités ne sont pas autorisées.
"""
    ),
}
