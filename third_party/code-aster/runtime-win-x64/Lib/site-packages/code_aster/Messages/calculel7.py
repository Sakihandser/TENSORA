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
Commande CALC_FERRAILLAGE :
    La maille <%(k2)s> du maillage <%(k1)s>, nœuds <%(i1)d> et <%(i2)d>
    n'a pas une section rectangulaire.
    La version actuelle permet seulement une section rectangulaire.
"""
    ),
    2: _(
        """
  option %(k1)s : pour l élément  %(k2)s  il faut ajouter dans le %(k3)s
 le nombre de composante calculées du flux
"""
    ),
    6: _(
        """
Erreur d'utilisation de la commande CREA_RESU / PREP_VARC.
Il n'est pas permis d'utiliser la structure de données résultat existante derrière le mot clé reuse.
"""
    ),
    7: _(
        """
  Erreur développeur : le champ n'a pas été créé car aucun type élément
  ne connaît le paramètre %(k1)s de l'option %(k2)s.
"""
    ),
    8: _(
        """
Erreur utilisateur commande CALC_FERRAILLAGE / TYPE_COMB = ELS_QP :
   Certains mots-clé de CALC_FERRAILLAGE / AFFE sont obligatoires pour un calcul à l'ELS_QP :
     pour CODIFICATION = 'BAEL91': N,FCJ,FE,EYS,WMAX_INF,WMAX_SUP,WMAX_INF_Y,WMAX_SUP_Y,WMAX_INF_Z,WMAX_SUP_Z,
       SIGC_ELS_QP,KT,PHI_INF_X,PHI_SUP_X,PHI_INF_Y,PHI_SUP_Y,PHI_INF_Z,PHI_SUP_Z
     pour CODIFICATION = 'EC2 : ALPHA_E,FCK,FYK,EYS,WMAX_INF,WMAX_SUP,WMAX_INF_Y,WMAX_SUP_Y,WMAX_INF_Z,WMAX_SUP_Z,
       SIGC_ELS_QP,KT,PHI_INF_X,PHI_SUP_X,PHI_INF_Y,PHI_SUP_Y,PHI_INF_Z,PHI_SUP_Z.
"""
    ),
    9: _(
        """
Commande CALC_FERRAILLAGE :
   Le calcul de l'ouverture de fissure (ELS_QP) pour la codification BAEL91 est basé sur le EC2.
"""
    ),
    12: _(
        """
 Commande CALC_FERRAILLAGE :
   ELU : On n'a pas réussi à calculer la densité de ferraillage sur l'élément.
   La section est trop comprimée (PIVOT B avec acier de compression ou PIVOT C).
   ATTENTION : Si vous avez retenu FERR_COMP = 'NON', les aciers en compression ne sont pas calculés !
   La densité de ferraillage est mise à -1.
   Conseil : on suggère soit de reprendre le calcul avec FERR_COMP = 'OUI', soit de changer la classe de béton ou soit de revoir le coffrage.
"""
    ),
    13: _(
        """
 Commande CALC_FERRAILLAGE :
   ELS : On n'a pas réussi à calculer la densité de ferraillage sur l'élément.
   La section est trop comprimée (PIVOT B avec acier de compression).
   ATTENTION : Si vous avez retenu FERR_COMP = 'NON', les aciers en compression ne sont pas calculés !
   La densité de ferraillage est mise à -1.
   Conseil : on suggère soit de reprendre le calcul avec FERR_COMP = 'OUI', soit de changer la classe de béton ou soit de revoir le coffrage.
"""
    ),
    14: _(
        """
 Commande CALC_FERRAILLAGE :
   ELS_QP : On n'a pas réussi à calculer la densité de ferraillage sur l'élément.
   La section est trop comprimée (PIVOT B avec acier de compression).
   ATTENTION : Si vous avez retenu FERR_COMP = 'NON', les aciers en compression ne sont pas calculés !
   La densité de ferraillage est mise à -1.
   Conseil : on suggère soit de reprendre le calcul avec FERR_COMP = 'OUI', soit de changer la classe de béton ou soit de revoir le coffrage.
"""
    ),
    15: _(
        """
 Commande CALC_FERRAILLAGE :
   ELU : On n'a pas réussi à calculer la densité de ferraillage sur l'élément.
   Le béton est trop cisaillé.
   La densité d'acier d'effort tranchant est fixé à -1 pour l'élément.
   Conseil : on suggère soit de changer la classe de béton soit de revoir le coffrage.
"""
    ),
    16: _(
        """
 Commande CALC_FERRAILLAGE :
   ELS : On n'a pas réussi à calculer la densité de ferraillage sur l'élément.
   Le béton est trop cisaillé.
   La densité d'acier d'effort tranchant est fixé à -1 pour l'élément.
   Conseil : on suggère soit de changer la classe de béton soit de revoir le coffrage.
"""
    ),
    17: _(
        """
 Commande CALC_FERRAILLAGE :
   ELS_QP : On n'a pas réussi à calculer la densité de ferraillage sur l'élément.
   Le béton est trop cisaillé.
   La densité d'acier d'effort tranchant est fixé à -1 pour l'élément.
   Conseil : on suggère soit de changer la classe de béton soit de revoir le coffrage.
"""
    ),
    18: _(
        """
 Commande CALC_FERRAILLAGE :
   STRUCTURE '1D' : L'un des enrobages suivants n'a pas été défini :
   C_INF_Y / C_SUP_Y / C_INF_Z / C_SUP_Z
   Le calcul ne peut pas être mené!
"""
    ),
    19: _(
        """
 Commande CALC_FERRAILLAGE :
   STRUCTURE '2D' : L'un des enrobages suivants n'a pas été défini :
   C_INF / C_SUP
   Le calcul ne peut pas être mené!
"""
    ),
    20: _(
        """
 Commande CALC_FERRAILLAGE :
   FERR_SYME = 'OUI' : Vous souhaitez réaliser un calcul de ferraillage symétrique.
   Pour ce fait, il est nécessaire que les enrobages de la section 1D soient égaux.
   Conseil : on suggère soit d'imposer FERR_SYME = 'NON', soit de vérifier que l'on ait
   C_INF_Y = C_SUP_Y & C_INF_Z = C_SUP_Z
"""
    ),
    21: _(
        """
 Commande CALC_FERRAILLAGE :
   FERR_SYME = 'OUI' / ELS : Vous souhaitez réaliser un calcul de ferraillage symétrique.
   Pour ce fait, il est nécessaire que les contraintes ultimes de dimensionnement du béton
   aux niveaux des 2 cotés des axes Y et Z de la section 1D soient égaux.
   Conseil : on suggère soit d'imposer FERR_SYME = 'NON', soit de vérifier que l'on ait
   SIGC_INF_Y_ELS = SIGC_SUP_Y_ELS & SIGC_INF_Z_ELS = SIGC_SUP_Z_ELS
"""
    ),
    22: _(
        """
 Commande CALC_FERRAILLAGE :
   FERR_SYME = 'OUI' / ELS_QP : Vous souhaitez réaliser un calcul de ferraillage symétrique.
   Pour ce fait, il est nécessaire que les ouvertures maximales de fissures autorisées
   aux niveaux des 2 cotés des axes Y et Z de la section 1D soient égaux.
   Conseil : on suggère soit d'imposer FERR_SYME = 'NON', soit de vérifier que l'on ait
   WMAX_INF_Y = WMAX_SUP_Y & WMAX_INF_Z = WMAX_SUP_Z
"""
    ),
    23: _(
        """
 Commande CALC_FERRAILLAGE :
   FERR_SYME = 'OUI' / ELS_QP : Vous souhaitez réaliser un calcul de ferraillage symétrique.
   Pour ce fait, il est nécessaire que les diamètres approximatifs des armatures
   aux niveaux des 2 cotés des axes Y et Z de la section 1D soient égaux.
   Conseil : on suggère soit d'imposer FERR_SYME = 'NON', soit de vérifier que l'on ait
   PHI_INF_Y = PHI_SUP_Y & PHI_INF_Z = PHI_SUP_Z
"""
    ),
    24: _(
        """
 Commande CALC_FERRAILLAGE :
   FERR_SYME = 'OUI' : Vous souhaitez réaliser un calcul de ferraillage symétrique.
   Pour ce fait, il est nécessaire que les enrobages de la section 2D soient égaux.
   Conseil : on suggère soit d'imposer FERR_SYME = 'NON', soit de vérifier que l'on ait
   C_INF = C_SUP
"""
    ),
    25: _(
        """
 Commande CALC_FERRAILLAGE :
   FERR_SYME = 'OUI' / ELS : Vous souhaitez réaliser un calcul de ferraillage symétrique.
   Pour ce fait, il est nécessaire que les contraintes ultimes de dimensionnement du béton
   aux niveaux des 2 cotés de la section 2D soient égaux.
   Conseil : on suggère soit d'imposer FERR_SYME = 'NON', soit de vérifier que l'on ait
   SIGC_INF_ELS = SIGC_SUP_ELS
"""
    ),
    26: _(
        """
 Commande CALC_FERRAILLAGE :
   FERR_SYME = 'OUI' / ELS_QP : Vous souhaitez réaliser un calcul de ferraillage symétrique.
   Pour ce fait, il est nécessaire que les ouvertures maximales de fissures autorisées
   aux niveaux des 2 cotés de la section 2D soient égaux.
   Conseil : on suggère soit d'imposer FERR_SYME = 'NON', soit de vérifier que l'on ait
   WMAX_INF = WMAX_SUP
"""
    ),
    27: _(
        """
 Commande CALC_FERRAILLAGE :
   FERR_SYME = 'OUI' / ELS_QP : Vous souhaitez réaliser un calcul de ferraillage symétrique.
   Pour ce fait, il est nécessaire que les diamètres approximatifs des armatures
   aux niveaux des 2 cotés de la section 2D soient égaux.
   Conseil : on suggère soit d'imposer FERR_SYME = 'NON', soit de vérifier que l'on ait
   PHI_INF_ = PHI_SUP_X & PHI_INF_Y = PHI_SUP_Y
"""
    ),
    28: _(
        """
 Commande CALC_FERRAILLAGE :
   FERR_SYME = 'OUI' : On n'a pas réussi à calculer une densité de ferraillage symétrique sur l'élément.
   Conseil : on suggère de reprendre le calcul soit en augmentant la valeur de la section seuil de tolérance
   SEUIL_SYME, soit en considérant FERR_SYME = 'NON'
"""
    ),
    29: _(
        """
 Commande CALC_FERRAILLAGE :
   Flexion Déviée / TYPE_STRUCTURE = 1D : On n'a pas réussi à calculer une densité de ferraillage en flexion déviée (MFY et MFZ).
   La méthode actuellement implémentée est une résolution itérative.
   L'algorithme rencontre un dépassement de capacité (beaucoup d'itérations tentées).
"""
    ),
    30: _(
        """
 Commande CALC_FERRAILLAGE :
   FERR_SYME = 'OUI' : Vous souhaitez réaliser un calcul de ferraillage symétrique.
   Pour ce fait, il est nécessaire de renseigner le seuil de tolérance SEUIL_SYME pour le calcul d'un ferraillage symétrique en faces SUP et INF.
   Conseil : on suggère soit de renseigner la valeur de la section SEUIL_SYME, soit de reprendre le calcul avec FERR_SYME = 'NON'
"""
    ),
    31: _(
        """
 Commande CALC_FERRAILLAGE :
   PAS_THETA : Vous souhaitez réaliser un calcul de ferraillage de plaques (2D).
   Les algorithmes implémentés se basent sur des méthodes itératives pour la recherche du ferraillage de dimensionnement.
   Pour ce fait, la valeur de l'angle d'itération à renseigner doit être strictement supérieure à 0° et inférieure à 10°.
"""
    ),
    32: _(
        """
 Commande CALC_FERRAILLAGE :
   PAS_EPAI : Vous souhaitez réaliser un calcul de ferraillage de plaques (2D), avec la méthode SANDWICH.
   L'algorithme implémenté se base sur une méthode itérative pour la recherche des épaisseurs du modèle à 3 couches associé.
   Pour ce fait, la valeur du taux d'itération sur les épaisseurs des couches à renseigner doit être strictement supérieure à 0 et inférieure à 0.1.
"""
    ),
    33: _(
        """
 Commande CALC_FERRAILLAGE :
   PAS_SIGM : Vous souhaitez réaliser un calcul de ferraillage de plaques (2D), avec la méthode SANDWICH.
   L'algorithme implémenté se base sur une méthode itérative pour la recherche de la configuration 'SANDWICH' associée.
   Entre autres, il s'agit de déterminer le ratio des contraintes principales reprises par les bielles de compression aux niveaux des couches périphériques
   Pour ce fait, la valeur du taux d'itération sur ce ratio doit être strictement supérieure à 0 et inférieure à 0.2.
"""
    ),
    34: _(
        """
 Commande CALC_FERRAILLAGE :
   ELU : Vous souhaitez réaliser un calcul de ferraillage de plaques (2D), avec la méthode SANDWICH.
   L'algorithme implémenté se base sur une méthode itérative pour la recherche de la configuration 'SANDWICH' associée.
   Pour le cas demandé, le code rencontre une incapacité à converger vers un ferraillage d'équilibre.
   Conseil : on suggère d'augmenter les critères de précision (THETA_ITER/EP_ITER/ALPHA_ITER)
   Par défaut, pour le cas actuel, on passe, localement, à la méthode de Capra-Maury.
"""
    ),
    35: _(
        """
 Commande CALC_FERRAILLAGE :
   ELU : On n'a pas réussi à calculer la densité de ferraillage sur l'élément.
   Pour au moins une des couches périphériques du modèle 'Sandwich', l'épaisseur est trop comprimée.
   ATTENTION : Si vous avez retenu FERR_COMP = 'NON', les aciers en compression ne sont pas calculés !
   La densité de ferraillage est mise à -1.
   Conseil : on suggère soit de reprendre le calcul avec FERR_COMP = 'OUI', soit de changer la classe de béton ou soit de revoir le coffrage.
"""
    ),
    36: _(
        """
 Commande CALC_FERRAILLAGE :
   ELU : On n'a pas réussi à calculer la densité de ferraillage sur l'élément.
   Pour le modèle 'Sandwich' estimé, le béton de la couche intermédiaire est trop cisaillé.
   La densité d'acier d'effort tranchant est fixé à -1 pour l'élément.
   Conseil : on suggère soit de changer la classe de béton soit de revoir le coffrage.
"""
    ),
    37: _(
        """
 Commande CALC_FERRAILLAGE :
   ELS/ELS_QP : Vous souhaitez réaliser un calcul de ferraillage de plaques (2D), avec la méthode SANDWICH.
   Cependant, cette méthode n'est conçue que pour effectuer un calcul à l'ELU ; une méthode alternative 'Multicouches' devrait être implémentée dans les prochaines versions de l'opérateur.
   """
    ),
    38: _(
        """
 Commande CALC_FERRAILLAGE :
   ELS_QP : L'effet d'échelle n'est pas applicable selon l'annexe du RCC-CW.
   """
    ),
    39: _(
        """
 Commande CALC_FERRAILLAGE :
   ELU/ELS : Le calcul de ferraillage minimal pour la maîtrise de la fissuration n'est possible qu'à l'ELS_QP. Le code retourne des valeurs nulles.
   """
    ),
    40: _(
        """
 Commande CALC_FERRAILLAGE :
   POUTRE : Le calcul de ferraillage minimal pour la maîtrise de la fissuration n'est pas encore possible pour les éléments POUTRE.
   """
    ),
}
