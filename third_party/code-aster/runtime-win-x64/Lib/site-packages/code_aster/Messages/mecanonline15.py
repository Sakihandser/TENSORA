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

# For DEBUG (INFO=2)

from ..Utilities import _

cata_msg = {
    1: _("""Création de la structure de données pour la dynamique."""),
    2: _("""Lecture des paramètres pour la dynamique."""),
    3: _("""Initialisations pour la dynamique."""),
    10: _("""Fonctionnalités activées en dynamique."""),
    11: _("""Utilisation d'un schéma implicite."""),
    12: _("""Utilisation d'un schéma explicite."""),
    13: _("""Présence d'appuis multiples."""),
    14: _("""Utilisation d'une matrice masse diagonale."""),
    15: _("""Utilisation de la projection modale."""),
    17: _("""Présence d'un chargement de type ONDE_PLANE."""),
    18: _("""Utilisation d'un schéma explicite en modal."""),
    19: _("""Utilisation d'un décalage de masse."""),
    20: _("""Présence d'un chargement de type FORCE_SOL."""),
    29: _("""Pas d'amortissement dans le modèle."""),
    30: _("""Présence d'amortissement dans le modèle."""),
    31: _("""Présence d'amortissement sous forme de matrice au premier membre."""),
    32: _("""Présence d'amortissement sous forme de vecteur au second membre."""),
    33: _("""Amortissement de type Rayleigh avec matrice élastique."""),
    34: _("""Amortissement de type Rayleigh avec matrice tangente."""),
    35: _("""Amortissement provenant d'éléments de type DIS_CONTACT ou JOINT."""),
    36: _("""Amortissement provenant d'éléments de type absorbant ou de macro-éléments."""),
    37: _("""Amortissement provenant d'éléments de type DIS_TR."""),
    38: _("""Amortissement modal."""),
}
