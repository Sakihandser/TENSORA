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
        """La table n'a pas le bon format :
    La colonne %(i1)d doit contenir le label %(k1)s et vous avez renseigné %(k2)s.
    Les mots clés disponibles sont %(k3)s"""
    ),
    2: _(
        """La surface %(k1)s nommée "%(k2)s" de la coupe appelée %(k3)s n'appartient pas au maillage considéré."""
    ),
    3: _("""La coupe appelée %(k2)s traverse plusieurs fois la surface %(k1)s."""),
    4: _("""Les éléments de type %(k1)s ne sont pas supportés en tant qu'éléments de peau."""),
    5: _(
        """La table ne contient pas le bons types de données :
    La colonne %(i1)d doit contenir le type %(k1)s et vous avez renseigné une donnée de type %(k2)s"""
    ),
    6: _(
        """Aucune intersection n'a été trouvée entre la coupe %(k2)s et le groupe de maille %(k1)s !"""
    ),
    7: _("""Le nom de coupe %(k1)s est utilisé plusieurs fois dans le tableau d'entrée."""),
    8: _(
        """La coupe %(k1)s que vous essayez de générer est de longueur nulle. Peut-être que vous avez spécifié deux fois la même surface d'entrée et de sortie. Il se pourrait aussi que ces surfaces ne soient pas disjointes."""
    ),
    9: _(
        """La surface nommée "%(k1)s" utilisée dans le mot clé REVOLUTION n'appartient pas au maillage considéré."""
    ),
    10: _(
        """La coupe appelée "%(k1)s" utilisée dans le mot clé REVOLUTION n'a pas été trouvé dans le tableau d'entrée."""
    ),
    11: _(
        """Le groupe appelé "%(k1)s" utilisé dans le mot clé REVOLUTION n'a pas été trouvé dans le tableau d'entrée."""
    ),
    12: _(
        """Le nom de coupe %(k1)s générée par le mot clé REVOLUTION, est présent plusieurs fois dans le tableau de sortie."""
    ),
    13: _("""0° n'est pas un angle valide pour l'opérande %(k1)s du mot clé REVOLUTION."""),
    14: _("""Il n'y a pas assez de point sur la coupe %(k1)s. Il en faut au minimum 2."""),
}
