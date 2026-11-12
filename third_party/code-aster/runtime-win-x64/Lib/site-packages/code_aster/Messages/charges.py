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
Le pilotage est interdit avec un maillage parallèle découpé
"""
    ),
    2: _(
        """
On ne peut pas appliquer dans la même occurrence des conditions aux ddls HHO et non-HHO.
Il faut le faire dans des occurrences séparées.
"""
    ),
    3: _(
        """
La charge %(k1)s n'a pu être identifiée. Cette erreur est probablement due à l'utilisation d'un
mot-clef facteur vide dans l'opérateur AFFE_CHAR_MECA, AFFE_CHAR_THER ou AFFE_CHAR_ACOU.
"""
    ),
    4: _(
        """
Le type de chargement PRE_EPSI doit avoir la même valeur aux deux noeuds d'un même élément de poutre.
S'il est appliqué sur des poutres homothétiques, les valeurs des paramètres de sections doivent être telles que :
    - A1  = A2
    - IY1 = IY2
    - IZ1 = IZ2

Pour les poutres, le code ne sait pas encore traiter ce type de chargement variable sur l'élément.
"""
    ),
    5: _(
        """
Il ne peut y avoir qu'une seule occurrence du chargement PRE_EPSI quand le mot-clé EPSI
est présent.
"""
    ),
    6: _(
        """
Le champ fourni à PRE_EPSI via la mot-clé EPSI contient une composante non autorisée : %(k1)s.
"""
    ),
    7: _(
        """Il n'est pas possible d'affecter une pression sur un élément de coque solide avec des fissures."""
    ),
    8: _(
        """
Le champ fourni à PRE_EPSI via la mot-clé EPSI doit être de type CARTE ou ELGA, or il est de type : %(k1)s.
"""
    ),
    9: _(
        """
La liaison 3D_POU_ARLEQUIN n'est pas disponible avec les mailles de type %(k1)s.
"""
    ),
    10: _(
        """On n'a pas trouvé l'élément volumique rattaché à la maille de surface sur laquelle on veut appliquer une pression."""
    ),
    11: _(
        """
Pour FORCE_COQUE, seule la composante PRES est compatible avec les charges suiveuses"""
    ),
    29: _(
        """
Il y a trop de chargements de type Dirichlet suiveur.
"""
    ),
    30: _(
        """
Erreur utilisateur :
  Le chargement contient des relations cinématiques qui sont non-linéaires
  lorsque l'on utilise EXCIT / TYPE_CHARGE='SUIV'.
  Mais le code ne sait pas encore traiter ces relations non linéaires.
"""
    ),
    35: _(
        """
Erreur utilisateur :
  Le chargement contient des relations cinématiques LIAISON_SOLIDE qui sont non-linéaires lorsque l'on utilise EXCIT / TYPE_CHARGE='SUIV'.
  Mais ce cas n'est pas traité car il y a au moins un noeud qui porte le degré de liberté DRZ.
"""
    ),
    36: _(
        """
Erreur utilisateur :
  Le chargement contient des relations cinématiques LIAISON_SOLIDE qui sont non-linéaires lorsque l'on utilise EXCIT / TYPE_CHARGE='SUIV'.
  Mais ce cas n'est pas traité car il y a au moins un noeud qui porte les degrés de liberté DRX, DRY et DRZ.
"""
    ),
    57: _(
        """
    AFFE_CHAR_CINE:
Vous essayez d'appliquer un déplacement selon DZ à une modélisation qui n'est pas 3D.

Conseil: Vérifié vos conditions aux limites.
"""
    ),
    58: _(
        """
    AFFE_CHAR_CINE:
Aucune maille de dimension %(i1)d n'a pu être trouvée pour le noeud %(i2)d.


Conseil: Vérifié vos conditions aux limites. En effet, pour les modèles HHO, il est nécessaire d'avoir un volume rattaché à un bord.
"""
    ),
}
