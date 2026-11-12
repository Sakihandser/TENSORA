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
 Le champ %(k1)s est déjà présent dans la structure de données
 à tous les instants demandés.
 Aucun calcul ne sera donc réalisé pour cette option.

Conseil :
 Si vous souhaitez réellement calculer à nouveau cette option,
 créez une nouvelle structure de données.
"""
    ),
    2: _(
        """
 L'option %(k1)s nécessaire au calcul de l'option %(k2)s est
 manquante dans les structures de données résultat pour le numéro d'ordre %(i1)d.

 Le calcul de cette option n'est donc pas possible.
 L'option demandée n'est calculable sur les éléments du modèle.
"""
    ),
    4: _(
        """
Les contributions de l'amortissement liées à la vitesse pour les
réactions nodales sont négligées dans la version actuelle du code.
"""
    ),
    7: _(
        """
Le champ STRX_ELGA n'est pas possible sur une modélisation XFEM.
"""
    ),
    8: _(
        """Il y a des chargements pilotées dans le résultat, mais on ne peut pas récupérer la valeur du coefficient de pilotage."""
    ),
    19: _(
        """
Problème lors de l'appel de l'option %(k1)s.

Contactez le support technique.
"""
    ),
    23: _(
        """Le modèle doit être le même sur tous les pas de temps pour ce post-traitement.
      Conseil : il faut séparer le post-traitement en le découpant pour garder le même modèle"""
    ),
    24: _(
        """Le chargement doit être le même sur tous les pas de temps pour ce post-traitement.
      Conseil : il faut séparer le post-traitement en le découpant pour garder le même chargement"""
    ),
    52: _(
        """
 La commande CALC_CHAMP a besoin de calculer le champ de type %(k1)s mais elle ne peut pas. Or ce champ est nécessaire au calcul du champ %(k2)s.
"""
    ),
    54: _(
        """Il n'y a aucun chargement défini pour ce post-traitement. Si le résultat est issu d'un calcul dynamique, pensez à renseigner les chargements dans la commande de post-traitement."""
    ),
    89: _(
        """
 Le champ  %(k1)s  n'a pas pu être calculé.
 Risques & conseils :
   * Si le champ est un champ par éléments, c'est que le calcul élémentaire n'est pas disponible
     pour les éléments finis utilisés. Cela peut se produire soit parce que ce
     calcul n'a pas été encore programmé, soit parce que ce calcul n'a pas de sens.
     Par exemple, le champ EFGE_ELNO n'a pas de sens pour les éléments de la modélisation '3D'.
   * Si le champ est un champ aux noeuds (XXXX_NOEU), cela veut dire que le champ XXXX_ELNO
     n'existe pas sur les éléments spécifiés.
     Par exemple, le calcul de SIGM_NOEU sur les éléments de bord est impossible.

"""
    ),
}
