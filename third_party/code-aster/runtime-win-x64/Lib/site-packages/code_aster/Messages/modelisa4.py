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
Présence de mailles dégénérées : modifier le maillage du béton.
"""
    ),
    6: _(
        """
  -> Phase de vérification du maillage : présence de noeuds orphelins.
     Les noeuds orphelins sont des noeuds qui n'appartiennent à aucune maille.
"""
    ),
    7: _(
        """
 certains noeuds connectent plus de 200 mailles. ces mailles ne sont pas vérifiées.
"""
    ),
    8: _(
        """
  -> Phase de vérification du maillage : présence de mailles doubles (ou triples, ...)
     Les mailles multiples sont des mailles de noms différents qui ont la même connectivité
     (elles s'appuient sur les mêmes noeuds).

  -> Risque & Conseil :
     Le risque est de modéliser 2 fois (ou plus) l'espace. On peut par exemple avoir
     un modèle 2 fois trop lourd ou 2 fois trop rigide.
     Remarque : les mailles concernées sont imprimées dans le fichier "message".
     Sur ce maillage, il est imprudent d'affecter des quantités avec le mot clé TOUT='OUI'.
"""
    ),
    9: _(
        """
  -> Phase de vérification du maillage : présence de mailles dégénérées.
     Le rapport entre la plus petite arête sur la plus grande est inférieur à %(r1).3e

  -> Risque & Conseil :
     Vérifiez votre maillage. La présence de telles mailles peut conduire à des
     problèmes de convergence et nuire à la qualité des résultats.
"""
    ),
    10: _(
        """
Phase de vérification du maillage - mailles dégénérées

  -> Risque & Conseil :
     Vérifiez votre maillage. La présence de telles mailles peut conduire à des
     problèmes de convergence et nuire à la qualité des résultats.

     Pour détecter les mailles problématiques, il est possible de désactiver
     la vérification. Puis de convertir le maillage en linéaire, afin de trouver
     facilement les arêtes ou faces doubles.
"""
    ),
    11: _(
        """
Deux arêtes partagent les mêmes noeuds sommets (%(i1)d, %(i2)d)
mais présentent des noeuds milieux différents (%(i3)d vs %(i4)d).
"""
    ),
    12: _(
        """
Deux faces partagent les mêmes noeuds sommets (%(i1)d, %(i2)d, %(i3)d, %(i4)d)
mais présentent des noeuds milieux différents. Elles sont en général à l'interface de
deux mailles volumiques.
"""
    ),
    13: _(
        """
 seule la grandeur NEUT_F est traitée actuellement.
"""
    ),
    14: _(
        """
 les champs de CHAM_F et CHAM_PARA n'ont pas la même discrétisation NOEU/CART/ELGA/ELNO/ELEM.
"""
    ),
    16: _(
        """
 avec "NOEUD_CMP", il faut donner un nom et une composante.
"""
    ),
    17: _(
        """
 pour récupérer le champ de géométrie (ou d'abscisse curviligne),
 il faut utiliser le mot clé maillage
"""
    ),
    18: _(
        """
 le mot-clé type_champ =  %(k1)s n'est pas cohérent avec le type
 du champ extrait :  %(k2)s_%(k3)s
"""
    ),
    19: _(
        """
On ne peut pas extraire le champ avec l'accès donné pour la structure de données RESULTAT.
Merci de vérifier si un seul numéro d'ordre est spécifié,
ou si l'instant spécifié existe.
"""
    ),
    24: _(
        """
 arrêt sur erreur(s), normale non sortante
"""
    ),
    28: _(
        """
Le numéro de corrélation et/ou le type de réseau passes dans le fichier de commande ne  sont pas cohérents avec le fichier .70
"""
    ),
    29: _(
        """
Le numéro de corrélation et/ou le type de réseau passes dans le fichier de commande ne  sont pas cohérents avec le fichier .70
"""
    ),
    30: _(
        """
Ce type de réseau n est pas encore implante dans le code
"""
    ),
    31: _(
        """
Le numéro de corrélation et/ou le type de réseau passes dans le fichier de commande ne  sont pas cohérents avec le fichier .71
"""
    ),
    32: _(
        """
Ce type de réseau n'est pas encore implanté dans le code
"""
    ),
    33: _(
        """
Le numéro de corrélation et/ou le type de réseau passes dans le fichier de commande ne  sont pas cohérents avec le fichier .71
"""
    ),
    35: _(
        """
 jacobien négatif
"""
    ),
    36: _(
        """
 La normale de la maille %(k1)s est nulle
"""
    ),
    39: _(
        """
 problème rencontré lors de l interpolation d une des déformées modales
"""
    ),
    40: _(
        """
 problème rencontré lors de l interpolation d une des fonctions
"""
    ),
    50: _(
        """
 la maille :  %(k1)s  n'est pas affectée par un élément fini.
"""
    ),
    51: _(
        """
Aucune des mailles sélectionnées n'est affectée par un élément fini.
"""
    ),
    53: _(
        """
 le noeud d application de l excitation n est pas un noeud du maillage.
"""
    ),
    54: _(
        """
 le noeud d application de l excitation ne doit pas être situe au bord du domaine de définition du maillage.
"""
    ),
    55: _(
        """
 la fenêtre excitée déborde du domaine de définition du maillage.
"""
    ),
    56: _(
        """
 la demi fenêtre excitée en amont du noeud central d'application n'est pas définie.
"""
    ),
    57: _(
        """
 la demi fenêtre excitée en amont du noeud central d'application déborde du domaine de définition du maillage.
"""
    ),
    58: _(
        """
 les demi fenêtres excitées en aval et en amont du noeud central d'application ne sont pas raccordées.
"""
    ),
    59: _(
        """
 la demi fenêtre excitée en aval du noeud central d'application n'est pas définie.
"""
    ),
    60: _(
        """
 la demi fenêtre excitée en aval du noeud central d'application déborde du domaine de définition du maillage.
"""
    ),
    61: _(
        """
 les fonctions interprétées doivent être tabulées auparavant
"""
    ),
    62: _(
        """
 nappe interdite pour définir le flux
"""
    ),
    63: _(
        """
  on déborde a gauche
"""
    ),
    64: _(
        """
 prolongement gauche inconnu
"""
    ),
    65: _(
        """
  on déborde a droite
"""
    ),
    66: _(
        """
 prolongement droite inconnu
"""
    ),
    67: _(
        """
  on est en dehors des bornes
"""
    ),
    68: _(
        """
 les mailles de type  %(k1)s ne sont pas traitées pour la sélection des noeuds
"""
    ),
    69: _(
        """
 Erreur d'utilisation :
   On cherche à nommer un objet en y insérant un numéro.
   Le numéro %(i1)d est trop grand vis à vis de la chaîne de caractère.

 Risque et Conseil :
   Vous avez atteint la limite de ce que sait faire le code
   (trop de poursuites, de pas de temps, de pas d'archivage, ...)
"""
    ),
    70: _(
        """
 erreur : deux noeuds du câble sont confondus on ne peut pas définir le cylindre.
"""
    ),
    71: _(
        """
 immersion du câble no %(k1)s  dans la structure béton : le noeud  %(k2)s  se trouve à l'extérieur de la structure
"""
    ),
    72: _(
        """
    DEFI_CABLE_BP n'a pas réussi à identifier la maille 3D dans laquelle est inclus le noeud de câble de coordonnées (%(r1).3e, %(r2).3e, %(r3).3e).
    Ce problème peut avoir plusieurs sources :
     - Présence de mailles dégénérées dans le maillage 3D.
     - Le noeud de câble est situé à l'interface de plusieurs mailles 3D. Le déplacer d'une petite distance pourrait permettre de régler le problème.
"""
    ),
    76: _(
        """
 le vecteur normal est dans le plan tangent
"""
    ),
    77: _(
        """
  %(k1)s  mot clé lu " %(k2)s " incompatible avec " %(k3)s "
"""
    ),
    78: _(
        """
erreur de lecture pour %(k1)s
"""
    ),
    79: _(
        """
item > 24 car  %(k1)s
Ce message est un message d'erreur développeur.
Contactez le support technique.
"""
    ),
    80: _(
        """
  %(k1)s  le groupe  %(k2)s  est vide. On l'ignore.
"""
    ),
    83: _(
        """
  le vecteur est perpendiculaire à la poutre.
"""
    ),
    84: _(
        """
  La poutre présente une ou plusieurs branches: cas non permis.
  Essayez de créer des groupes de mailles différents pour
  chaque branche et de les orienter indépendemment.
"""
    ),
    89: _(
        """
 mot clé WOHLER non trouvé
"""
    ),
    91: _(
        """
 mot clé MANSON_COFFIN non trouvé
"""
    ),
    92: _(
        """
 lecture 1 : ligne lue trop longue : %(k1)s
"""
    ),
    93: _(
        """
  Problème lors de la lecture du fichier maillage
  numéro de la dernière ligne traitée : %(i1)d

  -> Risque & Conseil :
  Vérifiez que le maillage est au format Aster (.mail).
  Vérifiez que le mot clé FIN est présent à la fin du fichier de maillage.
"""
    ),
    94: _(
        """
  Problème lors de la lecture du fichier maillage
  Le fichier à lire est vide.

  -> Risque & Conseil :
  Vérifiez la valeur mise derrière le mot clé UNITE et
  que cette valeur par défaut correspond au type "mail" dans ASTK
"""
    ),
    97: _(
        """
 le nom du groupe  %(k1)s  est tronque a 8 caractères
"""
    ),
    98: _(
        """
 il faut un nom après "nom="
"""
    ),
}
