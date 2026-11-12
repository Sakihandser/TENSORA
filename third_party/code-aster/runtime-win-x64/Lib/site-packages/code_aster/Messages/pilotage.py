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
 Le pilotage de type PRED_ELAS n'est pas possible en modélisation C_PLAN.
"""
    ),
    2: _(
        """
 Pour le cas de l'endommagement saturé dans ENDO_ISOT_BETON, on ne pilote pas.
"""
    ),
    3: _(
        """
 Le paramètre COEF_MULT pour le pilotage ne doit pas valoir zéro.
"""
    ),
    4: _(
        """
 La recherche linéaire en pilotage n'est possible qu'avec l'option PILOTAGE dans RECH_LINEAIRE  (sauf pour le cas DDL_IMPO).
"""
    ),
    48: _(
        """
 ETA_PILO_MAX doit être inférieur à ETA_PILO_R_MAX
"""
    ),
    49: _(
        """
 ETA_PILO_MIN doit être supérieur à ETA_PILO_R_MIN
"""
    ),
    50: _(
        """
 Il ne faut pas plus d'un noeud pour le pilotage DDL_IMPO.
"""
    ),
    55: _(
        """
 La liste des directions est vide pour le mot-clef %(k1)s pour le pilotage %(k2)s.
"""
    ),
    56: _(
        """
 Il faut une et une seule direction pour le mot-clef %(k1)s pour le pilotage de type %(k2)s.
"""
    ),
    57: _(
        """
 Il faut plus d'un noeud pour le pilotage LONG_ARC.
"""
    ),
    83: _(
        """
 Problème lors du pilotage.
 Nombre maximum d'itérations atteint.
"""
    ),
    84: _(
        """
 Problème lors du pilotage.
 Précision machine dépassée.
"""
    ),
    87: _(
        """
 Problème lors du pilotage.
"""
    ),
}
