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
Il y a des noeuds en commun entre les surfaces esclave et maître. Ceci est interdit
"""
    ),
    2: _(
        """
Le modèle n'est pas de type mécanique, ce n'est pas possible.
"""
    ),
    3: _(
        """
Le maillage est incorrect pour la méthode de contact utilisée. On a besoin d'avoir accès aux mailles sous-jacentes aux mailles de contact, ce n'est pas possible sur ce maillage.
Soit il manque les mailles volumiques sous les mailles de peau, soit le groupe de mailles de peau est inséré dans un volume.
"""
    ),
    4: _(
        """
Il y a un problème de dimension lié au modèle.
"""
    ),
    5: _(
        """
La méthode de contact est incompatible avec un maillage parallèle.
"""
    ),
}
