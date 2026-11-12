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
  Une divergence a été détectée à l'instant %(r1)f, inutile de poursuivre avec
  l'intégration temporelle.

  Conseil : réduire le pas de temps du schéma d'intégration ou choisir un schéma
  adaptatif avec une valeur de tolérance adaptée à la raideur du système dynamique
  aussi bien en vol libre qu'en état de choc.
"""
    ),
    5: _(
        """
  Le champ post-traité est un CHAM_ELEM, le calcul de moyenne ne fonctionne que
 sur les CHAM_NO. Pour les CHAM_ELEM utiliser POST_ELEM mot-clé INTEGRALE.
"""
    ),
    6: _(
        """
  Le calcul de la racine numéro %(i1)d par la méthode de la matrice compagnon a échoué.
"""
    ),
    8: _(
        """
  Il manque le NUME_DDL dans le concept %(k1)s.
  Propositions :
   - Si ce concept est issu de l'opérateur DEFI_BASE_MODALE, renseigner le mot-clé NUME_REF dans DEFI_BASE_MODALE.
   - Si ce concept est issu de l'opérateur CREA_RESU, utiliser les mots-clés MATR_RIGI et MATR_MASS dans CREA_RESU.
"""
    ),
    10: _(
        """
  La loi de comportement mécanique %(k1)s n'est pas compatible avec les
  éléments de joint avec couplage hydro-mécanique.
"""
    ),
    11: _(
        """
  La fermeture du joint sort des bornes [0,fermeture maximale].
  fermeture du joint = %(r1)f
  fermeture maximale = %(r2)f
  Vérifier la cohérence chargement mécanique, fermeture asymptotique et ouverture
  initiale.
"""
    ),
    14: _(
        """
  Les mots clés PRES_FLUIDE et PRES_CLAVAGE/SCIAGE sont incompatibles avec les modélisations xxx_JOINT_HYME
"""
    ),
    15: _(
        """
  Les données matériau RHO_FLUIDE, VISC_FLUIDE et OUV_MIN sont obligatoires avec les modélisations xxx_JOINT_HYME
"""
    ),
    16: _(
        """
  Les données matériau RHO_FLUIDE, VISC_FLUIDE et OUV_MIN sont incompatibles avec les modélisations xxx_JOINT
"""
    ),
    18: _(
        """
  La base de modes associée au résultat généralisé sous le mot-clé
  EXCIT_RESU %(i1)d n'est pas la même que celle utilisée pour la
  fabrication des matrices généralisées.
"""
    ),
    19: _(
        """
  La projection d'un résultat non réel sur une base de mode (de type
  résultat harmonique) n'est pas possible. Vous pouvez demander
  l'évolution.
"""
    ),
    22: _(
        """
  Il y a %(i1)d points de Gauss sur l'axe de rotation. En ces points les axes Or et suivant thêta ne sont pas définis. On prend
   un axe Or quelconque normal à Oz pour continuer le changement de repère mais seules les composantes suivant z ont un sens en ces points.
"""
    ),
    23: _(
        """
    Vous effectuez un changement de repère %(k1)s. Le repère est défini par %(i1)d occurrences du mot-clé AFFE : or une seule occurrence de ce mot-clé est autorisée pour ce type de changement de repère.
"""
    ),
    25: _(
        """
  Lors de la reprise du calcul, la liste des champs calculés (DEPL, VITE, ACCE) doit être la même
  pour le concept entrant et sortant.
"""
    ),
    26: _(
        """
  La structure de données résultat est corrompue. Elle ne contient pas d'objet avec la liste des numéros d'ordre.
"""
    ),
    27: _(
        """
  La structure de données résultat est corrompue. La liste des numéros d'ordres ne correspond pas
  à la liste des discrétisations temporelles ou fréquentielles.
"""
    ),
    28: _(
        """
  La structure de données en entrée ne contient aucun des champs requis pour la restitution temporelle.
  Conseil: vérifiez la liste des champs renseignée sous NOM_CHAM, ou bien testez l'option TOUT_CHAM='OUI'.
"""
    ),
    29: _(
        """
  Erreur dans l'allocation de la structure de données dynamique. La liste des champs à allouer n'est pas valide.
"""
    ),
    31: _(
        """
  Il faut donner autant de coefficients pour le paramètre %(k1)s
  qu'il y a de modes propres dans la base sur laquelle est fabriquée
  le macro-élément.
   - Nombre de modes de la base : %(i1)d
   - Nombre de coefficients donnés : %(i2)d.
"""
    ),
    32: _(
        """
  Le macro-élément est assemblé à partir de données mesurées.
  Le calcul des masses effectives est impossible. Ne pas en tenir
  compte dans les calculs postérieurs.
"""
    ),
    33: _(
        """
  Le paramètre PENA_RUPTURE doit être strictement supérieur à une valeur minimale
  selon les paramètres de la loi de comportement.
   - Valeur de PENA_RUPTURE : %(r1)f
   - Valeur minimale: %(r2)f
"""
    ),
    34: _(
        """
  La cohésion C doit être dans l'intervalle : MU*T < C < sqrt(2)*MU*T
  Où MU est le coefficient de frottement et T la résistance à la traction.
  Pour modifier C, il faut modifier Bn, Bt ou encore PENA_RUPTURE.
   - Valeur de MU*T : %(r1)f
   - Valeur de C : %(r2)f
   - Valeur de sqrt(2)*MU*T : %(r3)f
"""
    ),
    35: _(
        """
  Le paramètre K_N doit être strictement supérieur à : Bn*R_max
   - Valeur de K_N : %(r1)f
   - Valeur de B_N*R_max : %(r2)f
   - Valeur de R_max : %(r3)f
"""
    ),
    36: _(
        """
  Le paramètre K_T doit être strictement supérieur à : (mu**2*Bn+Bt)*R_max
   - Valeur de K_T : %(r1)f
   - Valeur de (mu**2*Bn+Bt)*R_max : %(r2)f
   - Valeur de R_max : %(r3)f
"""
    ),
    37: _(
        """
  Les paramètres Bn et Bn doivent être tous deux strictement positifs.
   - Valeur de Bn : %(r1)f
   - Valeur de Bt : %(r2)f
"""
    ),
    41: _(
        """
   Le type de résultat %(k1)s (mot clé TYPE_RESU) n'est pas autorisé pour le mot clé facteur %(k2)s (mot clé OPERATION)
"""
    ),
}
