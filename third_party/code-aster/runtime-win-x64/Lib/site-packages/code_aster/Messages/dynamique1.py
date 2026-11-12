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
        """On ne peut pas utiliser le mode MULTI_APPUI avec un comportement non-linéaire.
On doit être soit en élasticité, soit utiliser un comportement de type DIS_CONTACT ou DIS_CHOC."""
    ),
    2: _(
        """On ne peut pas utiliser ACCELERATION_MPI en parallélisme distribué : on force
ACCELERATION_MPI='NON'."""
    ),
    3: _(
        """Le nombre maximal d'itérations de l'algorithme d'équilibrage de bandes de fréquence est atteint.
        Il n'a pas été possible d'équilibrer les bandes de fréquence à la tolérance souhaitée."""
    ),
    4: _(
        """Convergence de l'algorithme d'équilibrage de bandes de fréquence atteinte.
    Erreur relative maximale :%(r1)12.5e. Nombre d'itérations : %(i1)i"""
    ),
    5: _(
        """L'algorithme d'équilibrage de bandes de fréquence ne prend en entrée que
    des matrices symétriques réelles."""
    ),
    6: _(
        """
L'incrément de temps est négatif du fait de la reprise du calcul. Cette valeur peut faire échouer certaines lois de comportement, en particulier les lois avec viscosité.
"""
    ),
}
