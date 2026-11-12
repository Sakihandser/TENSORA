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
    1: {
        "message": _(
            """
Le maillage indiqué par mot-clé MAILLAGE_N n'est pas utilisé. 
Le maillage considéré est celui provenant de RESU_INIT.
"""
        ),
        "flags": "DECORATED",
    },
    2: _(
        """
Assemblage des %(i1)d permutations
"""
    ),
    3: _(
        """
Permutation de l'assemblage %(k1)s en position %(k2)s
"""
    ),
    4: _(
        """
Il faut renseigner au moins un des mots-clés MAILLAGE_N ou RESU_INIT.
"""
    ),
    5: _(
        """
Le maillage est obsolète : les groupes %(k1)s ne sont pas conformes aux orientations de la cuve.
"""
    ),
    6: _(
        """
Le fichier THYC est invalide : il n'y a pas de cohérence entre le barycentre et l'épaisseur des mailles.
"""
    ),
    7: _(
        """
On ne trouve que %(i1)d mailles THYC associées aux %(i2)d grilles.
"""
    ),
    8: {
        "message": _(
            """
La masse de l'assemblage %(k1)s en position %(k2)s est %(r1)1.1f kg (%(r2)1.1f daN)
"""
        ),
        "flags": "DECORATED",
    },
    9: {
        "message": _(
            """
La masse totale des assemblages en coeur est %(r1)1.1f kg
"""
        ),
        "flags": "DECORATED",
    },
}
