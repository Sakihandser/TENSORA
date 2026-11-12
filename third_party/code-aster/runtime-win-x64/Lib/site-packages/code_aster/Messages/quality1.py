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
        """La fonctionnalité XFEM n'est pas qualifiée pour les études de sûreté. Il ne faut pas l'utiliser dans ce cadre.
Pour plus de détails, référez-vous à la fiche qualité de la version d’exploitation de code_aster.
"""
    ),
    2: _(
        """L'opérateur %(k1)s n'est pas qualifié pour les études de sûreté. Il ne faut pas l'utiliser dans ce cadre.
Pour plus de détails, référez-vous à la fiche qualité de la version d’exploitation de code_aster.
"""
    ),
    3: _(
        """Vous utilisez une loi de comportement en mode prototype (MFront ou UMAT).
        Ce mode de fonctionnement n'est pas qualifié pour les études de sûreté. Il ne faut pas l'utiliser dans ce cadre sans action de vérification et de validation spécifique. Pour les comportements de type MFront, la qualification est possible en suivant une procédure dédiée.
        Pour plus de détails, référez-vous à la fiche qualité de la version d’exploitation de code_aster.
"""
    ),
}
