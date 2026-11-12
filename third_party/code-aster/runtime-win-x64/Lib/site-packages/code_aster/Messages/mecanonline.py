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
 Le CARA_ELEM de l'évolution sous ETAT_INIT/EVOL_NOLI est différent du CARA_ELEM courant.
 """
    ),
    3: _(
        """
Erreur utilisateur :
  Vous essayez de faire un calcul non-linéaire mécanique ou un post-traitement sur un modèle dont les éléments
  ne sont pas programmés pour cela.
  On arrête le calcul.
Risques & conseils :
  Vous devriez changer de modélisation.
"""
    ),
    4: _(
        """
Erreur utilisateur :
  Vous essayez de faire un calcul non-linéaire mécanique en utilisant un concept résultat sans préciser l'état
  initial (mot clé ETAT_INIT).
  On arrête le calcul.
"""
    ),
    5: _(
        """
Erreur utilisateur :
  L'utilisation de simple Lagrange est interdite dans STAT_NON_LINE.
"""
    ),
    6: _(
        """
L'option MATR_DISTRIBUEE='OUI' est interdite avec le contact continu.
"""
    ),
    7: _(
        """
Le MODELE fourni par l'utilisateur sous le mot-clé MODELE est différent de celui présent dans la structure
de données renseignée sous le mot-clé INCREMENT/LIST_INST et construite par l'opérateur DEFI_LIST_INST.
"""
    ),
    8: _(
        """
Erreur utilisateur :
  L'élimination des doubles Lagrange (SOLVEUR/ELIM_LAGR='LAGR2') dans STAT_NON_LINE n'est pas
  compatible avec les simples Lagrange (AFFE_CHAR_MECA / DOUBLE_LAGRANGE='NON'):
  il faut passer à ELIM_LAGR='NON' sous le mot-clé facteur SOLVEUR.
"""
    ),
    9: _(
        """
Vous voulez poursuivre un calcul non-linéaire et vous précisez un état initial (mot clé ETAT_INIT).
Le champ %(k1)s fourni comme état initial a un modèle sous-jacent qui est différent du modèle pour le calcul sur les mailles communes.
"""
    ),
    23: _(
        """
 Le calcul de l'accélération initiale a ignoré les chargements de type:
 - ONDE_PLANE
 - GRAPPE_FLUIDE
"""
    ),
    24: _(
        """
 L'état initial n'a pas d'accélération donnée.
 On la calcule.
 """
    ),
    43: _(
        """
 Contact et pilotage sont des fonctionnalités incompatibles
"""
    ),
    59: _(
        """
 Cette loi de comportement n'est pas disponible pour le pilotage de type PRED_ELAS
"""
    ),
    60: _(
        """
 Le pilotage de type PRED_ELAS nécessite ETA_PILO_R_MIN et ETA_PILO_R_MAX pour la loi %(k1)s
"""
    ),
    69: _(
        """
 Problème rencontré :
   la matrice de masse est non inversible.
   On ne peut donc pas s'en servir pour calculer l'accélération initiale.
   => on initialise l'accélération à zéro.

 Conseils :
   Avez-vous bien affecté une masse sur tous les éléments ?

 Certains éléments ne peuvent évaluer de matrice masse.
 Dans ce cas, vous pouvez donner un champ d'accélération explicitement nul dans ETAT_INIT pour supprimer l'alarme.
"""
    ),
    70: _(
        """
 Problème rencontré :
   Le calcul de l'accélération initiale a échoué lors de la phase de résolution.
   => on initialise l'accélération à zéro.

 Conseils :
   Avez-vous bien affecté une masse sur tous les éléments ?

 Certains éléments ne peuvent évaluer de matrice masse.
 Dans ce cas, vous pouvez donner un champ d'accélération explicitement nul dans ETAT_INIT pour supprimer l'alarme.
"""
    ),
    78: _(
        """
 Problème rencontré :
   la matrice de masse est quasi singulière.
   On se sert de cette matrice pour calculer l'accélération initiale.
   => l'accélération initiale calculée est peut être excessive en quelques noeuds.

 Conseils :
   Ces éventuelles perturbations initiales sont en général sans influence sur
   la suite du calcul car elles sont localisées.
   Néanmoins, il peut être bénéfique de laisser ces perturbations s'amortir au
   début du calcul en faisant plusieurs pas avec chargement transitoire nul,
   avec, éventuellement, un schéma d'intégration choisi volontairement très
   dissipatif (par exemple HHT avec alpha=-0.3).
   On peut ensuite reprendre en poursuite avec un schéma moins dissipatif si besoin est.
"""
    ),
    80: _(
        """
 Les matrices d'amortissement élémentaires sont spécifiées par l'utilisateur. Il
 n'est actuellement pas possible de calculer les forces d'amortissement dans le
 cadre du calcul de l'accélération initiale.
"""
    ),
}
