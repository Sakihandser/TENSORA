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
        """La relation linéaire destinée à éliminer un des noeuds esclaves est une tautologie car la maille maître en vis à vis de ce noeud possède ce même noeud dans sa connectivité. On ne l'écrit donc pas."""
    ),
    2: _("""La composante normale (DNOR) doit être la seule des composantes de la liste."""),
    4: _(
        """Un des éléments esclave n'est pas du bon type.
 Pour le calcul de la normale, il faut que les éléments soient de la bonne dimension: des segments en 2D ou des faces en 3D."""
    ),
    6: _(
        """ Le modèle contient un mélange d'éléments 2D (vivant dans le plan Oxy) et 3D.
 Il n'est pas possible de réaliser une liaison dans cette configuration."""
    ),
    9: _(
        """Il est interdit d'avoir deux mailles de type POI1 simultanément sur les deux surfaces en vis-à-vis."""
    ),
    11: _("""Tous les maillages doivent être identiques entre le chargement et la projection."""),
    12: _(
        """Avec l'option TYPE='EXCENTREMENT' les seules mailles disponibles sont TRIA3 et QUAD4."""
    ),
    13: _("""La relation linéaire pour un des noeuds est une tautologie. On ne l'écrit pas."""),
    14: _("""Une des composantes n'existe pas sur l'un des noeuds à relier."""),
    15: _("""L'excentrement ne fonctionne qu'avec des modélisations 3D."""),
    16: _(
        """L'excentrement ne fonctionne pas car un des noeuds n'a pas tous les degrés de liberté de rotation."""
    ),
    17: _(
        """Vous cherchez à évaluer une formule issue de DEFI_PRES_EC8. 
La coordonnée Z en entrée est inférieure à Z_FOND.
Si vous évaluez cette fonction dans AFFE_CHAR_MECA/FORCE_COQUE_FO, vérifiez la cohérence du groupe de maille fourni.

    Z      = %(r1)f
    Z_FOND = %(r2)f
    """
    ),
    18: _(
        """DEFI_PRES_EC8 : dans l'occurrence %(i1)d de EVAL, LIST_EPAIS n'a pas la même longueur que LIST_H."""
    ),
    19: _(
        """Vous cherchez à évaluer une formule issue de DEFI_PRES_EC8. 
Les coordonnées X et Y fournies correspondent à un point plus éloigné de l'axe Z que le rayon du réservoir déclaré par le mot-clé RAYON.
Si vous évaluez cette fonction dans AFFE_CHAR_MECA/FORCE_COQUE_FO, vérifiez la cohérence du groupe de maille fourni.

    Distance à l'axe Z = %(r1)f
    Rayon du réservoir = %(r2)f
    Tolérance acceptée = %(r3)f
    """
    ),
    48: _(
        """Il n'y a aucun noeud esclave à lier pour l'occurrence %(i1)d du mot clé LIAISON_MAIL.
   Peut-être que tous les noeuds esclaves ont déjà été éliminés dans des occurrences précédentes."""
    ),
    49: _(
        """ Pour le calcul de la normale sur le côté esclave, il faut donner des éléments de facette."""
    ),
}
