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
Il manque les accélérations.
"""
    ),
    2: _(
        """
 pour une structure de données RESULTAT de type DYNA_TRANS,
 seuls les mots-clés FONC_MULT et COEF_MULT sont autorisés
"""
    ),
    3: _(
        """
 pour une structure de données RESULTAT de type  EVOL_ELAS,
 seul le mot-clé FONC_MULT est autorisé
"""
    ),
    4: _(
        """
 l'utilisation du mot-clé FONC_MULT n'est licite que pour
 les structures de données résultat :  EVOL_ELAS, DYNA_TRANS, DYNA_HARMO
"""
    ),
    5: _(
        """
 Erreur d'utilisation :
   On veut utiliser la commande CALC_ERREUR.
   Il y a %(i1)d processeurs actifs.
 Risques & conseils :
   Cette commande doit être utilisée avec un seul processeur.
"""
    ),
    6: _(
        """
 La composante %(k1)s n'existe pas dans le champ sur la maille spécifiée.
"""
    ),
    7: _(
        """
 Calcul de  %(k1)s  impossible.
"""
    ),
    11: _(
        """
 le résultat  %(k1)s  doit comporter un champ de déplacement au numéro d'ordre  %(k2)s  .
"""
    ),
    12: _(
        """
 Le mot clé PREC_ERR est OBLIGATOIRE avec l'option SING_ELEM.
 Il faut renseigner le mot clé PREC_ERR avec une valeur comprise entre 0 et 1.
"""
    ),
    13: _(
        """
 Le mot clé PREC_ERR doit être strictement positif.
"""
    ),
    14: _(
        """
 Il n'y a pas de champ d'estimateur d'erreur dans la structure de donnée résultat.
 On ne calcule pas l'option SING_ELEM.
 Le calcul préalable d'un estimateur d'erreur est OBLIGATOIRE pour le calcul de cette option.
"""
    ),
    15: _(
        """
 Par défaut on utilise l'estimateur en résidu ERME_ELEM.
"""
    ),
    16: _(
        """
 Par défaut on utilise l'estimateur basé sur les contraintes lissées version 2 ERZ2_ELEM.
"""
    ),
    17: _(
        """
Erreur utilisateur dans la commande CREA_CHAMP / EXTR :
   Le champ que l'on veut extraire (%(k1)s n'existe pas dans la structure
   de donnée CARA_ELEM ou CHAR_MECA.

Conseil :
  Pour "voir" les champs existants dans la structure de donnée XXXX,
  vous pouvez utiliser la commande :
   IMPR_CO(CONCEPT=_F(NOM=XXXX), NIVEAU=-1)

"""
    ),
    18: _(
        """
 Erreur utilisateur :
   Pour les modélisations DKTG et Q4GG, la température doit être
   fournie sous le forme 'TEMP_SUP', 'TEMP_INF', ['TEMP_MIL'] et
   non pas sous la forme 'TEMP'.
"""
    ),
    22: _(
        """
  L'option %(k1)s est inexistante.
"""
    ),
    24: _(
        """
 <I> L'estimateur que vous avez choisi pour le calcul de l'option SING_ELEM est %(k1)s.
"""
    ),
    26: _(
        """
 L'estimateur %(k1)s que vous avez choisi pour le calcul de l'option SING_ELEM
 n'existe pas dans la structure de donnée résultat %(k2)s.
 L'option SING_ELEM n'est pas calculée.
"""
    ),
    27: _(
        """
L'option  %(k2)s est incompatible avec ce type de résultat.
"""
    ),
    28: _(
        """
PROJ_CHAMP / METHODE='ECLA_PG' :
 On va traiter les mailles de dimension :  %(i1)d
 Les autres mailles sont ignorées
"""
    ),
    29: _(
        """
 Il n'y a pas de champ d'énergie dans la structure de donnée résultat.
 On ne calcule pas l'option SING_ELEM.
 Le calcul préalable de l'option  EPOT_ELEM ou ETOT_ELEM est OBLIGATOIRE
 pour le calcul de cette option.
"""
    ),
    35: _(
        """
 le modèle doit contenir des éléments finis ou des sous-structures.
"""
    ),
    36: _(
        """
 A cause des alarmes précédentes, l'option SING_ELEM n'est pas calculée.
"""
    ),
    38: _(
        """
 on ne traite pas le type_scalaire: %(k1)s
"""
    ),
    39: _(
        """
 le modèle contient des éléments de structure
 il faut probablement utiliser le mot-clé CARA_ELEM.
"""
    ),
    40: _(
        """
  -> Le modèle a probablement besoin d'un champ de matériau (mot-clé CHAM_MATER).

  -> Risque & Conseil :
     Ce message peut aider à comprendre un éventuel problème ultérieur lors de calculs élémentaires
     nécessitant des caractéristiques matérielles.
     Vérifiez si votre modélisation nécessite un CHAM_MATER.
"""
    ),
    41: _(
        """
 les charges ne s'appuient pas toutes sur le même modèle.
"""
    ),
    42: _(
        """
 les charges ne s'appuient pas sur le modèle donné en argument.
"""
    ),
    46: _(
        """
La MATR_ASSE et le CHAM_NO ont des numérotations différentes.
Si la MATR_ASSE contient des ddls LAGR, ceux-ci sont mis à zéro.
"""
    ),
    47: _(
        """
Alarme utilisateur pour le calcul de SIRO_ELEM :
  La maille volumique %(k1)s qui borde la maille de peau %(k2)s
  est dégénérée ou bien elle n'est pas du côté "-" de la maille de peau.
  On ne fera donc pas le calcul de SIRO_ELEM sur la maille de peau.

Conseil :
  Le problème vient peut-être du fait que la peau du maillage est mal
  orientée. On peut réorienter les mailles de peau avec la commande
  MODI_MAILLAGE / ORIE_PEAU.
"""
    ),
    48: _(
        """
Erreur utilisateur (EXTR_RESU / RESTREINT) :
 Le concept fourni après le mot clé CARA_ELEM : (%(k1)s) est associé
 au maillage : %(k3)s.
 Mais le maillage associé à la structure de données RESULTAT est différent : %(k2)s.
"""
    ),
    49: _(
        """
Erreur utilisateur (EXTR_RESU / RESTREINT) :
 Le concept fourni après le mot clé CHAM_MATER : (%(k1)s) est associé
 au maillage : %(k3)s.
 Mais le maillage associé à la structure de données RESULTAT est différent : %(k2)s.
"""
    ),
    50: _(
        """
 La commande a besoin d'un nom de modèle.
"""
    ),
    52: _(
        """
 le champ doit être un CHAM_ELEM.
"""
    ),
    53: _(
        """
 ne traite qu'un CHAM_ELEM réel
"""
    ),
    54: _(
        """
 longueurs des modes locaux incompatibles entre eux.
"""
    ),
    57: _(
        """
 on ne sait pas moyenner cette composante négative
"""
    ),
    58: _(
        """
 champs sur des modèles différents
"""
    ),
    59: _(
        """
  %(k1)s  doit être un CHAM_ELEM.
"""
    ),
    60: _(
        """
 longueurs des modes locaux champ1 incompatibles entre eux.
"""
    ),
    61: _(
        """
 longueurs des modes locaux champ2 incompatibles entre eux.
"""
    ),
    62: _(
        """
 composante non définie
"""
    ),
    71: _(
        """
Il faut un chargement de rotation et un seul.
"""
    ),
    72: _(
        """
  il ne faut pas définir plus d"un champ de vitesse
"""
    ),
    73: _(
        """
Le champ %(k1)s n'est ni un CHAM_ELEM ni un résultat élémentaire
Ce message est un message d'erreur développeur.
Contactez le support technique.
"""
    ),
    74: _(
        """
 type scalaire interdit : %(k1)s
"""
    ),
    79: _(
        """
 la matrice A est singulière
"""
    ),
    81: _(
        """
 cette fonction ne marche que pour des modes locaux de type champ aux noeuds, vecteur, ou matrice.
"""
    ),
    82: _(
        """
 le mode local est de type matrice non_carrée
"""
    ),
    84: _(
        """
Il n'y a pas de paramètre '%(k1)s' associé à la grandeur '%(k2)s' dans l'option '%(k3)s'.
"""
    ),
    85: _(
        """
Il y a plusieurs paramètres '%(k1)s' associés à la grandeur '%(k2)s' dans l'option '%(k3)s'.
"""
    ),
    86: _(
        """
CREA_CHAMP ne sait pas créer de champ de type %(k1)s.
"""
    ),
    87: _(
        """
 CREA_CHAMP ne sait créer de champ de type %(k1)s pour aucun des éléments fournis.
"""
    ),
    90: _(
        """
 le champ %(k1)s doit être une CARTE.
"""
    ),
    97: _(
        """
  Erreur d'utilisation :
    Fonctionnalité : projection de maillage
    On cherche à projeter des mailles sur certains noeuds.
    Mais la liste des noeuds que l'on arrive à projeter dans les mailles est vide.

  Conseil :
    Cette erreur peut venir d'une mauvaise utilisation du mot clé
    PROJ_CHAMP/DISTANCE_MAX
"""
    ),
    98: _(
        """
 Le calcul de carte de taille et de détection de singularité n'est pas
 programmé en 3D pour les éléments de type HEXA, PENTA et PYRAM.
"""
    ),
    99: _(
        """
 Problème de convergence pour calculer la nouvelle carte de taille.
"""
    ),
    100: _(
        """
 Problème pour récupérer l'épaisseur de la coque pour la maille  %(i1)d
"""
    ),
    101: _(
        """
Attention : la liaison COQ_3D ne prend actuellement en charge que les
éléments de bord de la partie coque, c’est-à-dire les éléments de type
SEG2 ou SEG3 uniquement.
"""
    ),
}
