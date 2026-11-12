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
    74: _(
        """
  valeur de D_SIGM_EPSI non trouvée
"""
    ),
    75: _(
        """
  valeur de SY non trouvée
"""
    ),
    76: _(
        """
 développement non implanté
"""
    ),
    80: _(
        """
 loi de comportement avec irradiation, le paramètre PHI_ZERO doit être supérieur à 0
"""
    ),
    81: _(
        """
 loi de comportement avec irradiation, le paramètre phi/K.PHI_ZERO+L doit être supérieur ou égal à 0
"""
    ),
    82: _(
        """
 loi de comportement avec irradiation, le paramètre phi/K.PHI_ZERO+L vaut 0. Dans ces conditions le paramètre BETA doit être positif ou nul
"""
    ),
    83: _(
        """
Loi de comportement avec grandissement, le repère d'anisotropie doit être défini.
"""
    ),
    97: _(
        """
 il faut fournir le mot-clé BETON_DESORP à DEFI_MATERIAU pour le fluage de dessiccation
 intrinsèque
"""
    ),
    98: _(
        """
 il faut obligatoirement déclarer FONC_DESORP sous BETON_DESORP pour le fluage de dessiccation
 intrinsèque avec SECH comme paramètre
"""
    ),
}
