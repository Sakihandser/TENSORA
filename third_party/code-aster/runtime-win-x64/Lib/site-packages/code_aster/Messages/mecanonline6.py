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

# Attention a ne pas faire de retour à la ligne !

from ..Utilities import _

cata_msg = {
    1: _(
        """
Instant de calcul: %(r1)19.12e - Niveau de découpe: %(i1)d
"""
    ),
    2: _(
        """
Post-traitement: calcul d'un mode de flambement
"""
    ),
    3: _(
        """
Post-traitement: calcul d'un mode vibratoire
"""
    ),
    4: _(
        """
La gestion automatique du pas de temps (DEFI_LIST_INST/METHODE='AUTO')
avec le schéma IMPLEX (DEFI_LIST_INST/MODE_CALCUL_TPLUS='IMPLEX') nécessite
de traiter la résolution par la méthode IMPLEX (STAT/DYNA_NON_LINE/METHODE='IMPLEX').
Conseil :
   - Choisissez STAT/DYNA_NON_LINE/METHODE='IMPLEX'
   - ou bien choisissez un autre schéma d'adaptation du pas de temps (DEFI_LIST_INST/MODE_CALCUL_TPLUS).
 """
    ),
    5: _(
        """
---------------------------------------------------------------------
Instant de calcul: %(r1)19.12e - Niveau de découpe: %(i1)d
"""
    ),
    6: _(
        """
Instant de calcul: %(r1)19.12e
"""
    ),
    7: _(
        """
---------------------------------------------------------------------
Instant de calcul: %(r1)19.12e
"""
    ),
    10: _("""  Le mode vibratoire de numéro d'ordre %(i1)d a pour fréquence %(r1)19.12e."""),
    11: _(
        """  Le mode de flambement de numéro d'ordre %(i1)d a pour charge critique %(r1)19.12e."""
    ),
    12: _(
        """  Le mode de stabilité de numéro d'ordre %(i1)d a pour charge critique %(r1)19.12e."""
    ),
    13: _(
        """
 On ne peut pas utiliser CRIT_STAB en calcul parallèle
"""
    ),
    60: _(
        """
  Critère(s) de convergence atteint(s)
"""
    ),
    70: _(
        """    Le résidu de type <%(k1)s> vaut %(r1)19.12e au noeud et degré de liberté <%(k2)s>"""
    ),
}
