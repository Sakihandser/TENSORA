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
    1: _("""Liste des comportements métallurgiques."""),
    2: _("""Liste des comportements métallurgiques pour la phase de revenu."""),
    4: _("""Affecté sur %(i1)d éléments"""),
    5: _("""  Type de phases                       : %(k1)s"""),
    6: _("""  Modèle métallurgique                 : %(k1)s"""),
    8: _("""  Nombre de phases                     : %(i1)d"""),
    9: _("""  Nombre total de variables internes   : %(i1)d"""),
    10: _("""Le résultat thermique doit contenir au moins deux pas de temps."""),
    11: _(
        """Le résultat thermique donné pour l'état initial doit être le même que le résultat de CALC_META."""
    ),
    51: _(
        """Pour l'initialisation du calcul métallurgique dans CALC_META, on n'a pas pu trouver un et un seul instant dans la structure de données résultat pour l'instant demandé %(r1)f."""
    ),
    52: _(
        """Pour l'initialisation du calcul métallurgique dans CALC_META, on n'a pas trouvé de champ META_ELNO dans la structure de données résultat pour l'état initial."""
    ),
    73: _(
        """
Le paramètre matériau taille limite D10 n'est pas défini.
"""
    ),
    74: _(
        """
Au moins un des paramètres matériau relatifs au revenu (K et M) n'est pas défini.
Vérifiez les paramètres matériau donnés.
"""
    ),
    96: _(
        """
Échec de l'algorithme de Newton lors du calcul des phases pour le zirconium.
"""
    ),
}
