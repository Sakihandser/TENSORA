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
    1: _("""Le résultat ne stocke aucun champ, on ne peut pas faire de post-traitement."""),
    2: _(
        """Le modèle donné dans la commande n'est pas le même que celui donné dans la structure de données résultat.
         Il ne faut pas le renseigner dans la commande."""
    ),
    3: _(
        """Le champ HYGR_ELGA ne peut pas être calculé si BETON_DESORP est absent du matériau
affecté aux mailles concernées.
Toutes les composantes sont mises à zéro."""
    ),
    4: _(
        """Le champ SIEF_ELGA n'est pas disponible dans le résultat. Pour le non-linéaire, on ne le calcule pas automatiquement.
Il faut soit compléter le résultat en entrée, soit demander explicitement le calcul de SIEF_ELGA dans CALC_CHAMP. Dans ce dernier cas, vous aurez des contraintes calculées avec l'hypothèse de l'élasticité linéaire !"""
    ),
    5: _(
        """La numérotation produite par le modèle (%(i1)d équations) est incohérente avec la dimension des champs nodaux (%(i2)d équations).
    L'erreur provient en général d'un incohérence au niveau d'une commande comme LIRE_RESU ou LIRE_CHAMP."""
    ),
    10: _("""Le modèle est manquant."""),
    18: _(
        """
 Vous utilisez CALC_CHAMP en reuse mais la structure de données en entrée est
 différente de celle en sortie. Ce n'est pas autorisé.
"""
    ),
    44: _(
        """
   Le modèle n'a pas été trouvé dans CALC_CHAMP (ni dans la commande, ni dans la structure de données résultats). Le calcul n'est pas possible.
"""
    ),
    45: _(
        """
Les caractéristiques élémentaires n'ont pas été trouvées dans CALC_CHAMP. Or le modèle contient des éléments de structure.
Il faut renseigner le CARA_ELEM dans CALC_CHAMP.
"""
    ),
}
