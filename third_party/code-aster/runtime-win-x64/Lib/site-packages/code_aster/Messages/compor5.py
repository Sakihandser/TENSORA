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
On ne trouve pas la courbe de traction (mot-clef %(k1)s) dans le matériau fourni.
"""
    ),
    2: _(
        """
La courbe de traction est une fonction du paramètre %(k1)s alors qu'on attend le paramètre EPSI.
"""
    ),
    4: _(
        """
La courbe de traction est une nappe dont le paramètre n'est pas EPSI. Ce cas n'est pas traité
dans la loi de comportement.
"""
    ),
    5: _(
        """
La courbe de traction est une nappe qui dépend de %(k1)s mais la variable de commande est
absente ou mal définie dans le matériau (AFFE_VARC).
"""
    ),
    6: _(
        """
On ne peut pas calculer de déformation thermique pour les matériaux de type ELAS_HYPER.
"""
    ),
    8: _(
        """
Erreur utilisateur :
    - Sur la maille %(k1)s le calcul est thermo mécanique. Mais il manque la température
      de référence.
    - On ne peut donc pas calculer de déformation thermique.
"""
    ),
    9: _(
        """
Sur la maille %(k1)s le calcul est thermo-mécanique mais non isotrope.
Le comportement ou l'élément concerné ne savent pas gérer ce cas.
"""
    ),
    10: _(
        """
Sur la maille %(k1)s le calcul est thermo-mécanique de type métallurgique (avec deux
coefficients de dilatation). Le comportement ou l'élément concerné ne savent pas gérer ce cas.
"""
    ),
    11: _(
        """
L'indicateur INDL_ELGA n'est pas possible avec le comportement %(k1)s.
"""
    ),
    15: _(
        """
La nature du matériau élastique %(k1)s n'est pas traitée pour cet élément ou ce comportement. Soit vous n'avez pas renseigné les bons paramètres élastiques, soit il s'agit d'une erreur de programmation.
"""
    ),
    19: _(
        """
Le groupe de fibre %(k1)s à déjà été affecté par :
- le matériau %(k2)s
- la relation %(k3)s
La règle de surcharge est appliquée. Avec :
- le matériau %(k4)s
- la relation %(k5)s
"""
    ),
    20: _(
        """
Sur certaines mailles, la modélisation est incompatible avec le comportement.
Pour modéliser des contraintes planes (sur des coques) ou des contraintes 1D (barres, poutres)
avec ce comportement, on va utiliser l'algorithme %(k1)s.
"""
    ),
    21: _(
        """
Sur certaines mailles, aucun comportement n'a été donné, on a défini par défaut
un comportement élastique en petites déformations.
"""
    ),
    22: _(
        """
L'occurrence numéro %(i1)d du mot-clé COMPORTEMENT affecte le modèle de
déformation GROT_GDEP sur une modélisation %(k1)s. Ce n'est pas possible.
Vous pouvez essayer avec le modèle de déformation GREEN_LAGRANGE.
"""
    ),
    23: _(
        """
L'occurrence numéro %(i1)d du mot-clé COMPORTEMENT affecte le modèle de
déformation %(k1)s sur une modélisation %(k2)s. Ce n'est pas possible.
"""
    ),
    24: _(
        """
Le calcul prend en compte le séchage. Mais il manque la valeur de référence.
On ne peut donc pas calculer la déformation de dessication associée.
"""
    ),
    25: _(
        """
Vous utilisez le comportement ENDO_HETEROGENE mais seul le parallélisme de type centralisé
est autorisé pour ce comportement.
"""
    ),
    32: _(
        """
La variable de commande %(k1)s est définie mais il manque le paramètre matériau %(k2)s.
On ne peut donc pas calculer la déformation générée par la variable de commande %(k1)s.
"""
    ),
    40: _(
        """
Les caractéristiques matériaux dans %(k1)s dépendent de la température mais elle n'est
pas renseignée. Il faut une température dans AFFE_MATERIAU/AFFE_VARC.
"""
    ),
    42: _(
        """
Il existe un champ de température mais vous n'avez pas renseigné le paramètre ALPHA
dans DEFI_MATERIAU ou la température de référence dans AFFE_MATERIAU/AFFE_VARC.
On ne peut pas calculer la déformation thermique.
"""
    ),
    43: _(
        """
Il existe un champ de température mais il manque la température de référence
dans AFFE_MATERIAU/AFFE_VARC.
"""
    ),
    44: _(
        """
Il existe un champ de température mais vous n'avez pas renseigné le
paramètre ALPHA dans DEFI_MATERIAU.
"""
    ),
    51: _(
        """
BETON_DOUBLE_DP:
Le cas des contraintes planes n'est pas traité pour ce modèle.
"""
    ),
    52: _(
        """
ROUSSELIER:
La version PETIT_REAC n'est pas disponible en contraintes planes.
"""
    ),
    56: _(
        """
Plusieurs matériaux de type %(k1)s ont été trouvés.
Vous avez sans doute enrichi votre matériau. Vous ne pouvez pas avoir en même temps
les mots clés 'ELAS', 'ELAS_FO', 'ELAS_xxx', ...
"""
    ),
    57: _(
        """
Le matériau de type %(k1)s n'a pas été trouvé.
"""
    ),
    59: _(
        """
La déformation plastique cumulée est négative.
"""
    ),
    60: _(
        """
Le prolongement à droite étant exclu pour la fonction %(k1)s, il n'est pas possible
d'extrapoler la fonction R(p) au delà de p = %(r1)f
"""
    ),
    76: _(
        """
Couplage fluage/fissuration :
La loi BETON_DOUBLE_DP ne peut être couplée qu'avec une loi de fluage de GRANGER
"""
    ),
    81: _(
        """
Pour %(k2)s et le comportement %(k1)s, l'intégration par la
méthode %(k3)s n'est pas disponible.
"""
    ),
}
