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

# Attention a ne pas faire de retour à la ligne !

from ..Utilities import _

cata_msg = {
    3: _(
        """Il n'est pas possible de calculer la dureté (DURT_ELNO) pour les phases de type %(k1)s."""
    ),
    4: _(
        """L'état initial donné par l'utilisateur dans CALC_META n'est pas de la bonne taille: on attend %(i1)d variables mais on en a seulement %(i2)d."""
    ),
    44: _(
        """L'état métallurgique initial produit par CREA_CHAMP est incomplet. Pour l'acier, il faut renseigner les cinq phases."""
    ),
    45: _(
        """L'état métallurgique initial produit par CREA_CHAMP est incomplet. Pour le Zircaloy, il faut renseigner les trois phases."""
    ),
    46: _(
        """L'état métallurgique initial produit par CREA_CHAMP est incomplet. Pour l'acier, il faut renseigner la taille de grain."""
    ),
    47: _(
        """L'état métallurgique initial produit par CREA_CHAMP est incomplet. Pour le Zircaloy, il faut renseigner l'instant de transition."""
    ),
    48: _("""Erreur dans CALC_META: La somme des phases vaut %(r1)12.4E."""),
    49: _(
        """La somme des phases froides donnée par l'utilisateur n'est pas égale à la somme des phases froides, on met la vraie somme (et pas celle renseignée par l'utilisateur)."""
    ),
    50: _(
        """La différence entre la température de début de transformation des phases froides en austénite dans le diagramme TRC et celle donnée par DEFI_MATERIAU est supérieure de plus de %(r1)12.4E°C."""
    ),
    51: _(
        """Le calcul de transformation de l'austénite pendant le chauffage a échoué malgré la tentative de découpe du pas de temps. Il faut discrétiser plus finement le transitoire thermique ou modifier les valeurs matériaux."""
    ),
    52: _(
        """La phase %(i1)d de l'acier vaut %(r1)12.4E et n'est donc pas dans le domaine admissible."""
    ),
}
