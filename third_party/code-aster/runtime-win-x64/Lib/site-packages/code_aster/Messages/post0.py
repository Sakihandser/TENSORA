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

_nota_lign_coupe_axis = """MACR_LIGN_COUPE ne sait pas récupérer le repère dans lequel le champ
fourni en entrée est exprimé et peut donc uniquement réaliser des changements de repère pour
un champ défini initialement dans le repère GLOBAL"""

cata_msg = {
    1: _(
        """
Définition incorrecte de la ligne de coupe.
"""
    ),
    2: _(
        """
Valeurs incorrectes pour VECT_Y.
"""
    ),
    3: _(
        """
Valeurs incorrectes pour VECT_Y: X colinéaire à Y.
"""
    ),
    5: _(
        """
Le type %(k1)s n'est pas cohérent avec le choix du repère (REPERE %(k2)s).
"""
    ),
    6: _(
        """
Définition incorrecte de COOR_ORIG et CENTRE.
"""
    ),
    7: _(
        """
Définition incorrecte de DNOR.
"""
    ),
    8: _(
        """
Attention la ligne de coupe traverse des zones sans matière :
 - Les coordonnées des points sur la ligne de coupe sont :
            %(k1)s
 - Les coordonnées des points éliminés (car hors de la matière) sont:
            %(k2)s
"""
    ),
    9: _(
        """
Nom du modèle absent dans le concept résultat %(k1)s.

Conseils :
  Si le concept résultat provient des opérateurs LIRE_RESU ou CREA_RESU, il est possible
  de renseigner un concept modèle plutôt qu'un concept maillage.
  Il est également possible de renseigner un concept modèle directement dans MACR_LIGN_COUP.
"""
    ),
    10: _(
        """
Veuillez renseigner le MODELE si vous utilisez un CHAM_GD.
"""
    ),
    11: _(
        """
Dimensions de maillage et de coordonnées incohérentes.
"""
    ),
    12: _(
        """
Le mot-clé 'DNOR' est obligatoire en 3D pour le type 'ARC'.
"""
    ),
    13: _(
        """
Le GROUP_NO %(k1)s n'est pas dans le maillage %(k2)s.
"""
    ),
    14: _(
        """
Le GROUP_MA %(k1)s n'est pas dans le maillage %(k2)s.
"""
    ),
    15: _(
        """
le GROUP_MA %(k1)s contient la maille %(k2)s qui n'est pas de type SEG.
"""
    ),
    16: _(
        """
On ne peut pas combiner des lignes de coupes de type ARC
avec des lignes de coupes SEGMENT ou GROUP_NO.
"""
    ),
    17: _(
        """
Le champ %(k1)s n'est pas traité par MACR_LIGNE_COUPE en repère %(k2)s.
Le calcul est effectué en repère global.
"""
    ),
    18: _(
        """
Erreur probable de l'utilisateur :
  Le champ %(k1)s semble être un champ aux points de Gauss.
  La commande MACR_LIGN_COUPE ne sait pas traiter les champs aux points de Gauss.

  Le programme risque donc de s'arrêter en erreur fatale.

  Le seul cas où le programme peut fonctionner est celui d'une structure
  de données résultat obtenue par la commande MACR_ECLA_PG.

Conseil : il faut transformer le champ ELGA en un champ de type ELNO ou NOEU.
"""
    ),
    19: _(
        """
La structure de données RESULTAT ne contient aucun champ pour le numéro d'ordre %(i1)d.
On ne peut pas calculer les efforts.
"""
    ),
    21: _(
        """
Le point à l'occurrence %(i1)d a une cote h= %(r1)f, donc non nulle.
Les efforts étant intégrés sur la section, on n en tient pas compte.
"""
    ),
    22: _(
        """
Le point à l'occurrence %(i1)d n a que 3 coordonnées. Pour le calcul
des déformations on doit rentrer une position dans l'épaisseur.
"""
    ),
    23: _(
        """
Le concept résultat %(k1)s ne contient pas de modèle.
On ne pourra donc pas projeter de champs aux éléments (champs de contraintes, etc.).
Pour projeter des champs aux noeuds, on utilisera directement le maillage.
"""
    ),
    24: _(
        """
Attention la ligne de coupe %(i1)d traverse des zones sans matière :
 - Les coordonnées des points sur la ligne de coupe sont :
            %(k1)s
 - Le nombre de points éliminés (car hors de la matière) est:
            %(i2)d
"""
    ),
    25: _(
        """
La structure de données RESULTAT ne contient aucun champ au numéro d ordre %(i1)d.
"""
    ),
    26: _(
        """
La structure de données RESULTAT ne contient aucun champ à l instant %(r1)f.
"""
    ),
    27: _(
        """
Le GROUP_NO %(k1)s ne doit contenir qu'un seul noeud, il en contient %(i1)d.
"""
    ),
    33: _(
        """
Sur certains points de la fissure %(k1)s le calcul de l'ouverture de fissure n'a pas été possible. Trois situations sont envisageables :
      (1) Le point est sur le bord
      (2) L'endommagement maximal n'a été atteint sur la zone endommagée
      (3) La valeur BORNE_MAX est trop élevée
"""
    ),
    34: _(
        """
Pour la commande POST_ENDO_FISS, le maillage doit être contenu dans un plan parallèle aux plans XY, XZ, YZ.
"""
    ),
    35: _(
        """
Le champ pour la recherche de l'ouverture de fissure doit être un champ aux noeuds.
"""
    ),
    39: _(
        """
En 3D, le mot-clé NORMALE doit être renseigné dans la commande DEFI_FOND_FISS.
"""
    ),
    41: _(
        """
L'instant ou numéro d'ordre demandé n'existe pas dans le résultat et champ renseignés en entrée de la commande.
"""
    ),
    42: _(
        """
Le champ demandé pour la recherche du trajet de fissuration n'existe pas dans le résultat renseigné en entrée de la commande.
"""
    ),
    43: _(
        """
Si OUVERTURE='OUI' il est nécessaire de renseigner un concept RESULTAT en entrée de la commande (et pas un CHAM_GD).
"""
    ),
    44: _(
        """
Si OUVERTURE='OUI' il est nécessaire de renseigner le mot-clé BORNE_MAX.
"""
    ),
    45: _(
        """
Problème dans POST_CZM_FISS, le point de référence P_ORIG n'est pas aligné avec les points de Gauss des éléments cohésifs.

Pour vous aider à déterminer la position du point de référence voici les coordonnées min et max des points de Gauss
du groupe de mailles cohésives %(k1)s :
abscisse minimale = %(r1)f
abscisse maximale = %(r2)f
ordonnée minimale = %(r3)f
ordonnée maximale = %(r4)f
"""
    ),
    46: _(
        """
Problème dans POST_CZM_FISS, le vecteur directeur VECT_TANG n'est pas colinéaire à la droite des points de Gauss.

Pour vous aider à déterminer ce vecteur directeur voici les coordonnées min et max des points de Gauss
du groupe de mailles cohésives %(k1)s :
abscisse minimale = %(r1)f
abscisse maximale = %(r2)f
ordonnée minimale = %(r3)f
ordonnée maximale = %(r4)f
"""
    ),
    47: _(
        """
Problème dans POST_CZM_FISS, aucun point de Gauss ne se trouve sur la demi-droite défini par POINT_ORIG et VECT_TANG.

Pour vous aider à déterminer la demi-droite voici les coordonnées min et max des points de Gauss
du groupe de mailles cohésives %(k1)s :
abscisse minimale = %(r1)f
abscisse maximale = %(r2)f
ordonnée minimale = %(r3)f
ordonnée maximale = %(r4)f
"""
    ),
    48: _(
        """
Attention, dans POST_CZM_FISS la zone cohésive n'est pas connexe (voir documentation d'utilisation).
"""
    ),
    49: _(
        """
Attention, dans POST_CZM_FISS on constate que la zone cohésive n'est portée que par au plus trois points de Gauss.
Le maillage n'est peut être pas suffisamment fin pour décrire cette zone.
"""
    ),
    50: _(
        """
Erreur d'utilisation dans MACR_LIGN_COUPE :
  Il faut renseigner le mot clé VECT_Y en 3D
"""
    ),
    51: _(
        """
CALC_NEWMARK ne sait pas traiter des maillages 3D
"""
    ),
    52: _(
        """
L'option VERIF_MASSE de POST_NEWMARK n'est pas disponible pour un calcul dynamique
réalisé directement avec les matrices de rigidité et masse.
Vous pouvez réaliser le même calcul en fournissant directement le champ matériau
obtenu par AFFE_MATERIAU, via le mot-clé CHAM_MATER.
"""
    ),
    53: _(
        """
Dans l'opérateur MACR_LIGN_COUPE, une seule valeur peut-être pour DISTANCE_MAX.
Plusieurs valeurs ont été détectées. On ne retient que la valeur la plus basse : %(r1)f
"""
    ),
    54: _(
        """
Dans l'opérateur MACR_LIGN_COUPE, une seule valeur peut-être pour DISTANCE_ALARME.
Plusieurs valeurs ont été détectées. On ne retient que la valeur la plus basse : %(r1)f
"""
    ),
    55: _(
        f"""
Pour effectuer l'opération demandée, MACR_LIGN_COUPE a besoin de connaître le repère dans
lequel le champ %(k1)s est défini.
Merci de renseigner le mot clé REPERE_INIT.
À noter que {_nota_lign_coupe_axis}.
"""
    ),
    56: _(
        f"""
Le champ %(k1)s est un champ aux éléments.
Vous avez demandé un changement de repère pour au moins une coupe, et vous avez indiqué que
le champ en entrée est exprimé dans le repère %(k2)s.
Actuellement, {_nota_lign_coupe_axis}.
"""
    ),
    57: _(
        """
La modification de REPERE pour une coupe de type GROUP_MA ou GROUP_NO n'est pas implémentée.
"""
    ),
    58: _(
        """
Erreur d'utilisation dans MACR_LIGN_COUPE :
  Le mot clé VECT_Y en 2D est inutile.
"""
    ),
}
