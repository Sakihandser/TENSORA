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
Problème lors du traitement du chargement de type EVOL_CHAR.
On a trouvé aucun chargement utilisable pour l'instant %(r1)f.
"""
    ),
    2: _(
        """
Problème lors du traitement du chargement de type EVOL_CHAR.
L'extraction du chargement de type %(k1)s a échoué pour l'instant %(r1)f.
Le chargement n'a pas été trouvé pour cet instant.
"""
    ),
    3: _(
        """
Un chargement de type %(k1)s a été déclaré comme étant suiveur alors que ce n'est pas possible.
Si votre chargement contient plusieurs types dont certains ne peuvent être suiveurs, il faut les séparer.
Certains chargements ne peuvent être suiveurs s'ils sont dépendants du temps.
"""
    ),
    4: _(
        """
Un chargement de type %(k1)s a été déclaré comme étant pilotable alors que ce n'est pas possible.
Si votre chargement contient plusieurs types dont certains ne peuvent être pilotables, il faut les séparer.
"""
    ),
    5: _(
        """
Pour un chargement de convection, il ne faut pas définir plus d"un champ de vitesse.
"""
    ),
    10: _("""Les composantes dans le champ de vent doivent être exactement DX, DY et DZ."""),
    12: _(
        """
Problème lors du traitement du chargement de type EVOL_CHAR.
L'extraction du chargement a échoué pour l'instant %(r1)f.
Le chargement est mal défini:
- soit il n'est pas indexé par l'instant;
- soit le chargement n'a pas été trouvé pour cet instant;
- soit il manque un champ nécessaire :
    - COEF_H et (simultanément) T_EXT pour ECHANGE
    - FLUN pour FLUX_REP
"""
    ),
    13: _(
        """
Le chargement EVOL_CHAR contient des chargements s'appliquant simultanément sur des modèles de dimensions différentes. Ce n'est pas possible.
"""
    ),
    14: _(
        """
Le chargement EVOL_CHAR contient un chargement déclaré suiveur. Or ce chargement ne peut pas être suiveur.
"""
    ),
}
