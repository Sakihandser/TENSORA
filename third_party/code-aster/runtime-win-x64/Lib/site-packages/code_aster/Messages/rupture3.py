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
Vérification des paramètres d'entrée
"""
    ),
    2: _(
        """
Calcul du champ thêta
"""
    ),
    3: _(
        """
Les rayons inférieur et supérieur pour le calcul de thêta ne sont pas valables. Ils doivent être positifs et le rayon inférieur doit être strictement plus petit que le rayon supérieur:
    Rayon inférieur: %(r1)f
    Rayon supérieur: %(r2)f
"""
    ),
    4: _(
        """
Le nombre de couches d'élément inférieur et supérieur pour le calcul de thêta ne sont pas valables. Ils doivent être positifs et le nombre de couches inférieur doit être strictement plus petit que le nombre de couches supérieur:
    Nombre de couches inférieur: %(i1)d
    Nombre de couches supérieur: %(i2)d
"""
    ),
    5: _(
        """
Le champ thêta fourni est de type %(k1)s, au lieu de THET_R.

Conseil : vérifiez le champ thêta.
"""
    ),
    6: _(
        """
Le mot-clé EXCIT n'est pas renseigné alors que la structure de données résultat est de type DYNA_TRANS ou MODE_MECA. Hors, on ne peux pas récupérer les chargements automatiquement.

Conseil: vérifiez que cela est normal.
"""
    ),
    7: _(
        """
Dans le cas d'une structure de données résultat de type EVOL_ELAS ou EVOL_NOLI,
le mot-clé EXCIT est interdit. Le chargement sera directement lu dans las structure de donnée RESULTAT
Veuillez l'enlever.
"""
    ),
    8: _(
        """
La relation suivante n'est pas supportée: %(k1)s. Uniquement les lois basées sur VMIS_ISOT_*** sont prévues pour un calcul élastoplastique,
à l'exception de VMIS_ISOT_NL.
"""
    ),
    9: _(
        """
La déformation suivante n'est pas supportée: %(k1)s. Uniquement PETIT est prévu.
"""
    ),
    11: _(
        """
Seule la relation ELAS du calcul mécanique est supportée avec le mot-clé ETAT_INIT.
"""
    ),
    12: _(
        """
Vous réalisez un calcul de G en grandes transformations (formalisme GREEN_LAGRANGE).

Ce calcul n'est valable qu'en petites déformations.
"""
    ),
    13: _(
        """
Vous réalisez un calcul de G en grandes transformations (formalisme GREEN_LAGRANGE).

Ce calcul n'est pas compatible avec la discrétisation LEGENDRE.
Veuillez utiliser la discrétisation LINEAIRE.
"""
    ),
}
