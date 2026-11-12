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

#

from ..Utilities import _

cata_msg = {
    1: _("""Type de maille non-supporté dans la projection. Il faut demander un développement."""),
    2: _(
        """Dans le cadre de la projection ponctuelle, on n'a pas trouvé de maille POI1
suffisamment proche du noeud %(k1)s.

Distance à la maille POI1 la plus proche  : %(r1)f
Distance maximale autorisée (DISTANCE_0D) : %(r2)f
"""
    ),
    3: _(
        """Vous utilisez le mot clef %(k1)s pour faire une projection.
Vous ne devez définir la transformation géométrique %(k2)s que sous le mot clef facteur %(k1)s.
"""
    ),
    4: _(
        """Vous utilisez le mot clef %(k1)s pour faire une projection.
La transformation géométrique %(k2)s est appliquée à des mailles dont
la topologie est %(k3)s.
Vous devez définir les 3 fonctions (FX, FY, FZ).

Remarque : CAS_FIGURE est utilisé pour filtrer les mailles, du MODELE_1 ou du MAILLAGE_1,
qui portent les champs à projeter. Seuls les champs portés par les mailles qui
correspondent à la topologie donnée sous CAS_FIGURE seront projetés sur les mailles
du MODELE_2 ou du MAILLAGE_2.
"""
    ),
    5: _(
        """Vous utilisez une projection parallèle mais un sous-domaine ne possède aucune maille
         à projeter. Vous devriez utiliser le mot-clé DISTRIBUTION."""
    ),
    6: _(
        """
  Attention : %(i1)d mailles de type %(k1)s n'ont pas été projetées car la famille
  de points de Gauss sur le champ en question a une maille support 1D.

  Il s'agit peut-être d'éléments de joint 2D. Vous pouvez utilisez GROUP_MA s'il existe dans la commande.
"""
    ),
    7: _(
        """
  Des mailles n'ont pas été projetées car la famille de points de Gauss sur le champ en question a une maille support 1D.

  Il s'agit peut-être d'éléments de joint 2D. Vous pouvez utilisez GROUP_MA s'il existe dans la commande.
"""
    ),
    54: _("""Il n'y a aucun noeud sur lesquels projeter."""),
    55: _(
        """Il n'y a pas de mailles à projeter ou en correspondance.
 Dans le cas de l'utilisation de AFFE_CHAR_MECA / LIAISON_MAIL, les mailles maîtres
 doivent avoir la même dimension que l'espace de modélisation :
 - mailles volumiques pour un modèle 3D
 - mailles surfaciques pour un modèle 2D
"""
    ),
    56: _("""Le noeud %(k1)s n'a pas été trouvé lors de la projection. """),
}
