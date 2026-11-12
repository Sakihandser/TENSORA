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
        """L'utilisation des chargements cinématiques par CHAM_CINE n'est pas possible avec ce schéma d'intégration temporelle. """
    ),
    2: _("""Les maillages ne sont pas les mêmes entre les différentes matrices."""),
    3: _("""Les matrices ne sont pas toutes de la même taille."""),
    4: _(
        """Les chargements cinématiques sont incohérents entre l'assemblage des matrices et leur utilisation dans DYNA_VIBRA."""
    ),
    5: _("""Les chargements cinématiques sont incohérents entre les matrices."""),
    6: _("""Les chargements cinématiques doivent être appliqués sur toutes les matrices."""),
    7: _("""Le maillage du chargement cinématique n'est pas cohérent avec celui de la matrice."""),
    9: _(
        """La matrice a un chargement cinématique mais vous n'avez pas donné ce chargement dans DYNA_VIBRA."""
    ),
    10: _(
        """Vous avez donné un chargement cinématique dans DYNA_VIBRA, mais la matrice n'a pas été préparée avec ce chargement."""
    ),
    11: _(
        """Le calcul de l'énergie n'est pas possible avec un chargement cinématique dans DYNA_VIBRA."""
    ),
    12: _(
        """L'utilisation des chargements cinématiques par CHAM_CINE n'est pas possible dans un calcul sur coordonnées généralisées. """
    ),
    13: _("""Il ne peut y avoir qu'un seul chargement cinématique."""),
}
