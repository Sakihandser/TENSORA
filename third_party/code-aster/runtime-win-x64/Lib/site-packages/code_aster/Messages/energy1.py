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
Le calcul de ENEL_ELGA n'est pas possible avec le modèle de déformation %(k1)s.
"""
    ),
    2: _(
        """
Le calcul de ENEL_ELGA n'est pas possible avec des paramètres élastiques %(k1)s.
"""
    ),
    3: _(
        """
Le calcul de ENER_TOTALE n'est pas possible avec le modèle de déformation %(k1)s.
"""
    ),
    4: _(
        """
Le calcul de %(k1)s n'est pas possible avec des paramètres élastiques %(k2)s.
"""
    ),
    5: _(
        """
Pour l'option INDIC_SEUIL, les seules relations admises sont VMIS_ISOT_LINE, VMIS_ISOT_TRAC et VMIS_CINE_LINE.
"""
    ),
    6: _(
        """
Pour l'option INDIC_ENER, les seules relations admises sont VMIS_ISOT_LINE et VMIS_ISOT_TRAC.
"""
    ),
    7: _(
        """
Le calcul de ETOT_ELGA n'est pas possible avec le modèle de déformation %(k1)s.
"""
    ),
}
