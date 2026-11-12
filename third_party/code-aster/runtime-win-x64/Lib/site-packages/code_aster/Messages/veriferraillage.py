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
 Commande VERI_FERRAILLAGE :
   CHAM_FERR : Le champ de densité de ferraillage entré n'est pas un champ élémentaire constant par élément. Veuillez entrer un champ élémentaire constant par élément.
"""
    ),
    2: _(
        """
 Commande VERI_FERRAILLAGE :
   CHAM_FERR : Le champ entré ne contient pas les densités de ferraillage.
   Conseil : on suggère de créer un champ élémentaire de type ELEM_FER2_R avec la commande CREA_CHAMP.
"""
    ),
    3: _(
        """
 Commande VERI_FERRAILLAGE :
   CHAM_FERR : Le maillage associé à CHAM_FERR est différent de celui associé au modèle de calcul.
"""
    ),
    #     4: _(
    #         """
    #  Commande VERI_FERRAILLAGE :
    #    CHAM_REFE : Le champ des efforts généralisés de reference entré n'est pas un champ élémentaire de type ELNO. Veuillez entrer un champ élémentaire de type ELNO.
    # """
    # ),
    5: _(
        """
 Commande VERI_FERRAILLAGE :
   CHAM_REFE : Le champ des efforts généralisés en entré ne contient pas la grandeur SIEF_R (qui contient les efforts généralisés). Veuillez entrer un champ élémentaire contenant la grandeur ELEM_FER2_R.
"""
    ),
    6: _(
        """
 Commande VERI_FERRAILLAGE :
   CHAM_REFE : Le maillage associé à CHAM_REFE est différent de celui associé au modèle de calcul.
   """
    ),
    #     7: _(
    #         """
    #  Commande VERI_FERRAILLAGE : ATTENTION un champ de marge existe déjà au numéro d'ordre %(i1)d du résultat %(k1)s
    #    Ce champ de marge sera écrasé !
    #    """
    #     ),
    8: _(
        """
 Erreur utilisateur commande VERI_FERRAILLAGE / TYPE_COMB = ELU :
   Certains mots-clé de VERI_FERRAILLAGE / AFFE sont obligatoires pour un calcul à l'ELU :
     pour CODIFICATION = 'BAEL91' : FE, FCJ, GAMMA_S, GAMMA_C, TYPE_DIAGRAMME et EYS
     pour CODIFICATION = 'EC2' : FYK, FCK, GAMMA_S, GAMMA_C, TYPE_DIAGRAMME et EYS
"""
    ),
    9: _(
        """
 Erreur utilisateur commande VERI_FERRAILLAGE / TYPE_COMB = ELS :
   Certains mots-clé de VERI_FERRAILLAGE / AFFE sont obligatoires pour un calcul à l'ELS :
     pour CODIFICATION = 'BAEL91' : N,SIGS_ELS,SIGC_INF_ELS,SIGC_SUP_ELS
     pour CODIFICATION = 'EC2' : ALPHA_E,SIGS_ELS,SIGC_INF_ELS,SIGC_SUP_ELS,EYS
"""
    ),
    10: _(
        """
 Erreur commande VERI_FERRAILLAGE :
   On n'a pas réussi à calculer la carte de marge sur un élément.
   (h/2-c) est négatif ou nul (l'utilisateur a fourni des valeurs d'enrobage incompatibles avec l'épaisseur de l'élément)
"""
    ),
    11: _(
        """
 Commande VERI_FERRAILLAGE :
  Le point correspondant aux efforts généralisés de référence est situé en dehors du diagramme d'interaction sur au moins une facette.
  La marge dans ce cas est fixée égale à 2.0. Les efforts normaux et moments résistants de rupture
  et la distance entre le point correspondant au torseur de référence et celui correspondant au torseur résistant de rupture sont fixés à -1. Les valeurs relatives à l'état de la section sont fixées à -1.
"""
    ),
    12: _(
        """
 Commande POST_VERI_FERRAILLAGE :
  Le groupe de mailles ne fait pas partie du maillage sur lequel le champ de marge s'appuie. Veuillez fournir un autre GROUP_MA.
"""
    ),
    13: _(
        """
 Commande POST_VERI_FERRAILLAGE :
  Aucune maille n'a une marge inférieure au seuil. Veuillez définir un seuil supérieur.
"""
    ),
    14: _(
        """
 Commande POST_VERI_FERRAILLAGE :
  Le nombre de diagrammes demandés est supérieur au nombre total de mailles. Veuillez fournir un nombre NB_DIAG inférieur au nombre total de mailles.
"""
    ),
    15: _(
        """
 Commande POST_VERI_FERRAILLAGE :
  Un seul mot-clé doit être fourni parmi : 'GROUP_MA', 'SEUIL_MIN_MARGE' ou 'NB_DIAG'.
"""
    ),
    16: _(
        """
 Commande POST_VERI_FERRAILLAGE :
  Le calcul des valeurs liées à l'état de la section n'est possible que pour les classes de béton inférieures ou égales à 50 MPa.
"""
    ),
    17: _(
        """
 Commande POST_VERI_FERRAILLAGE :
  La marge est négative pour le torseur d'efforts de calcul. les valeurs de l'état de la section correspondant à l'état limite seront fournies.
"""
    ),
    18: _(
        """
 Commande POST_VERI_FERRAILLAGE :
  Lorsque le torseur des efforts de référence coïncide avec le torseur des efforts de calcul, les efforts normaux et moments résistants de rupture
  et la distance entre le point correspondant au torseur de référence et celui correspondant au torseur résistant de rupture sont fixés à -1.
"""
    ),
    19: _(
        """
 Commande POST_VERI_FERRAILLAGE :
  On ne retrouve aucune solution d'équilibre pour la section et le torseur d'effort donnés aux ELS.
"""
    ),
}
