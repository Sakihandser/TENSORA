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

# Messages pour les éléments discrets non-linéaires
from ..Utilities import _

cata_msg = {
    1: _(
        """
Pour l'élément discret %(k1)s .
Il n'y a pas de rotation non-linéaire possible.
"""
    ),
    2: _(
        """
Pour l'élément discret %(k1)s .
Il n'y a pas de comportement non-linéaire possible suivant Z
ou en rotation autour de X,Y en 2D.
"""
    ),
    3: _(
        """
Pour l'élément discret %(k1)s .
Il n'y a pas de comportement non-linéaire possible en rotation
ou suivant Z en 2D.
"""
    ),
    4: _(
        """
Pour l'élément discret %(k5)s .
La raideur tangente est nulle ou trop petite.
Vérifier les caractéristiques : K1 K2 K3 UNSUR_K1 UNSUR_K2 UNSUR_K3

La raideur tangente : 1/K1 + 1/K3 + K2/(K1*K3) ne doit pas être nulle ou trop petite.

Pour information :
   Modèle   : <%(k1)s>, Option   : <%(k2)s>
   Comportement : <%(k3)s>, Matériau : <%(k4)s>
   Maille   : <%(k5)s>
"""
    ),
    5: _(
        """
Pour l'élément discret %(k5)s .
Les caractéristiques sont obligatoirement données dans le repère local du discret.

Pour information :
   Modèle   : <%(k1)s>, Option   : <%(k2)s>
   Comportement : <%(k3)s>, Relation : <%(k4)s>
   Maille   : <%(k5)s>
"""
    ),
    6: _(
        """
Pour les éléments discrets il faut définir un repère dans AFFE_CARA_ELEM

Pour information :
   Modèle   : <%(k1)s>, Option   : <%(k2)s>
   Comportement : <%(k3)s>, Relation : <%(k4)s>
   Maille   : <%(k5)s>
"""
    ),
    7: _(
        """
La relation <%(k4)s> affectée à un DISCRET est non valide.

Pour information :
   Modèle   : <%(k1)s>, Option   : <%(k2)s>
   Comportement : <%(k3)s>, Relation : <%(k4)s>
   Maille   : <%(k5)s>
"""
    ),
    8: _(
        """
Pour les discrets, le seul comportement élastique valide est ELAS.

Pour information :
   Modèle   : <%(k1)s>, Option   : <%(k2)s>
   Comportement : <%(k3)s>, Relation : <%(k4)s>
   Maille   : <%(k5)s>
"""
    ),
    10: _(
        """
Pour l'élément DISCRET de modèle <%(k1)s> la matrice de décharge est non développée.

Pour information :
   Modèle   : <%(k1)s>, Option   : <%(k2)s>
   Comportement : <%(k3)s>, Relation : <%(k4)s>
   Maille   : <%(k5)s>
"""
    ),
    11: _(
        """
La loi <%(k4)s> doit être utilisée avec des éléments du type DIS_TR_L :
   élément SEG2 + modélisation DIS_TR

Pour information :
   Modèle   : <%(k1)s>, Option   : <%(k2)s>
   Comportement : <%(k3)s>, Relation : <%(k4)s>
   Maille   : <%(k5)s>
"""
    ),
    12: _(
        """
La commande %(k4)s ne sait pas traiter les matrices non-symétriques, pour l'option %(k1)s.
Message de la routine %(k3)s, pour l'élément %(k2)s.
"""
    ),
    13: _(
        """
L'élément %(k1)s est inconnu pour la maille %(k3)s.
Message de la routine %(k2)s.
"""
    ),
    14: _(
        """
L'option %(k1)s est inconnue pour l'élément %(k2)s.
Message de la routine %(k3)s.
"""
    ),
    15: _(
        """
L'option %(k1)s ne sait pas traiter l'élément %(k2)s.
Message de la routine %(k3)s.
"""
    ),
    18: _(
        """
Seul DEFORMATION ='PETIT' est possible pour les éléments discrets.
"""
    ),
    21: _(
        """
AFFE_CARA_ELEM/RIGI_PARASOL
  Le nombre de valeurs fournies sous VALE ne correspond pas au nombre attendu.
  Vous devez vérifier l'adéquation des dimensions des éléments sous CARA avec le
  nombre de valeur sous VALE.
"""
    ),
    22: _(
        """
Pour l'élément discret %(k5)s .
Pour ce comportement la modélisation doit être 3D.

Pour information :
   Modèle   : <%(k1)s>, Option   : <%(k2)s>
   Comportement : <%(k3)s>, Matériau : <%(k4)s>
   Maille   : <%(k5)s>
"""
    ),
    23: _(
        """
Pour l'élément discret %(k4)s.
Pour ce comportement la modélisation doit être soit :
-  DIS_T_L : élément SEG2 et modélisation DIS_T
-  DIS_T_N : élément POI1 et modélisation DIS_T
Pour information :
- Modèle   : <%(k1)s>, Option   : non-linéaire
- Comportement : <%(k2)s>, Relation : <%(k3)s>
   Maille   : <%(k4)s>
"""
    ),
    24: _(
        """
Attention, la loi DIS_ECRO_CINE donne des résultats faux en chargement cyclique.
"""
    ),
    25: _(
        """
Vous utilisez des discrets %(k1)s alors que vous n'avez pas affecté ses caractéristiques.
Il faut vérifier les affectations sous AFFE_CARA_ELEM/DISCRET OU DISCRET_2D.
"""
    ),
    26: _(
        """
Vous utilisez la matrice de MASSE pour un discret %(k1)s alors que vous n'avez pas affecté
les caractéristiques de masses. Par défaut la masse est nulle.
Il faut vérifier les affectations sous AFFE_CARA_ELEM/DISCRET.
"""
    ),
    27: _(
        """
Vous utilisez la matrice de RAIDEUR pour un discret %(k1)s alors que vous n'avez pas affecté
les caractéristiques de raideurs. Par défaut la raideur est nulle.
Il faut vérifier les affectations sous AFFE_CARA_ELEM/DISCRET.
"""
    ),
    28: _(
        """
Vous utilisez la matrice d'amortissement pour un discret %(k1)s alors que vous n'avez pas affecté
les caractéristiques d'amortissements. Par défaut l'amortissement est nul.
Il faut vérifier les affectations sous AFFE_CARA_ELEM/DISCRET.
"""
    ),
    30: _(
        """Informations :
   Maille de nom %(k1)s, de %(i1)d noeud(s).
   Nom et coordonnées des noeuds :
"""
    ),
    31: _(
        """      %(k1)8s   %(r1)12.5E   %(r2)12.5E   %(r3)12.5E
"""
    ),
    32: _(
        """
Erreur d'utilisation :
  Pour l'option %(k1)s, l'élément %(k2)s doit avoir des caractéristiques symétriques.
Risques et conseils :
  Dans la commande AFFE_CARA_ELEM, il ne faut pas utiliser le mot-clé DISCRET/SYME='NON'
  pour ces éléments.
"""
    ),
    33: _(
        """
Le discret avec le matériau %(k1)s/CONTACT="COIN_2D" et le comportement %(k2)s n'est pas dans un des plans XY, XZ ou YZ.

Informations:
    Noeud 1 (%(r1)f, %(r2)f, %(r3)f)
    Noeud 2 (%(r4)f, %(r5)f, %(r6)f)
    Delta  (%(r7)f, %(r8)f, %(r9)f)
    Précision (%(r10)f, %(r11)f, %(r12)f)
"""
    ),
    34: _(
        """
Le discret avec le matériau %(k1)s/CONTACT="COIN_2D" et le comportement %(k2)s est soit :
-   Sur un des axes X, Y ou Z.
        Dans ce cas, il faut utiliser CONTACT="1D" (option par défaut)
-   Dans plusieurs plans.
        Dans ce cas il faut adapter PRECISION.

Informations:
    Noeud 1 (%(r1)f, %(r2)f, %(r3)f)
    Noeud 2 (%(r4)f, %(r5)f, %(r6)f)
    Delta  (%(r7)f, %(r8)f, %(r9)f)
    Précision (%(r10)f, %(r11)f, %(r12)f)
    Nombre de plans %(i1)d
    Axes  (%(i2)d, %(i3)d, %(i4)d)
"""
    ),
    35: _(
        """
Le discret avec le matériau %(k1)s et le comportement %(k2)s
gère seulement CONTACT=%(k3)s.
"""
    ),
    36: _(
        """
Pour le discret avec le matériau %(k1)s, le comportement %(k2)s, de CONTACT=%(k3)s.
Les paramètres suivant ne sont pas pris en compte :
    DIST_1, DIST_2, JEU, RIGI_TAN, AMOR_NOR, AMOR_TAN, COULOMB
"""
    ),
    37: _(
        """
Pour le discret avec le matériau %(k1)s et le comportement %(k2)s, le type d'élément DIS_TR n'est pas autorisé dans le cas avec frottement de Coulomb (c'est-à-dire dans le 
cas où le paramètre COULOMB est strictement positif). Seul le type %(k3)s est autorisé.
"""
    ),
    38: _(
        """
Pour le discret avec le matériau %(k1)s, il n'est pas possible de spécifier à la fois le paramètre KT et les paramètres (KT1, KT2).
"""
    ),
    40: _(
        """
L'utilisation des discrets non-symétriques n'est actuellement pas possible pour
des calculs non-linéaires.
"""
    ),
    41: _(
        """
DYNA_VIBRA : Pour l'élément discret de type DIS_VISC.
La raideur tangente est nulle ou trop petite.
Vérifier les caractéristiques : K1 K2 K3 UNSUR_K1 UNSUR_K2 UNSUR_K3

La raideur tangente : 1/K1 + 1/K3 + K2/(K1*K3) ne doit pas être nulle ou trop petite.
"""
    ),
    42: _(
        """
DYNA_VIBRA : Pour l'élément discret de type DIS_VISC ou DIS_ECRO_TRAC

L'intégration de la loi de comportement du discret pose problème.
L'erreur est supérieure à RESI_INTE=%(r1)12.5E pour un nombre
d'itération maximum de ITER_INTE_MAXI=%(i1)d.

Conseils :
  Augmenter ITER_INTE_MAXI
  Augmenter le nombre de pas d'intégration.
  Modifier votre liste d'instant
"""
    ),
    43: _(
        """
DYNA_VIBRA : Pour l'élément discret de type :
    DIS_VISC ou DIS_ECRO_TRAC ou CHOC_ELAS_TRAC

Sa longueur est nulle ou trop petite.
Il n'est pas possible de calculer le vecteur directeur de l'élément.
"""
    ),
    44: _(
        """
Pour l'élément discret de type %(k4)s.

Sa longueur selon x ou y est nulle ou trop petite.
Il n'est pas possible de calculer les variations géométriques de l'élément.

Pour information :
   Modèle   : <%(k1)s>, Option   : <%(k2)s>
   Comportement : <%(k3)s>, Matériau : <%(k4)s>
   Maille   : <%(k5)s>
"""
    ),
    45: _(
        """
Pour l'élément discret de type %(k4)s.

Les capacités portante élastique et ultime sont nulles.
La fondation ne peut pas reprendre d'effort.

Pour information :
   Modèle   : <%(k1)s>, Option   : <%(k2)s>
   Comportement : <%(k3)s>, Matériau : <%(k4)s>
   Maille   : <%(k5)s>
"""
    ),
    46: _(
        """
DYNA_VIBRA, comportement DIS_ECRO_CINE :
  Vous avez fourni le paramètre %(k1)s qui est associé à un degré de liberté de rotation.
  Or au moins un des noeuds sur lesquels ce comportement doit s'appliquer ne possède pas
  de degré de liberté de rotation.
"""
    ),
    61: _(
        """
Le prolongement à droite étant exclu pour la fonction %(k1)s, il n'est pas
possible d'extrapoler la fonction au delà de %(r1)f
"""
    ),
    62: _(
        """
Le Comportement %(k1)s est non valide.
La définition de la fonction %(k2)s est incorrecte.
    1)  FX ou FTAN non définie
    2)  Elle doit être définie avec DEFI_FONCTION
        Le nom du paramètre est 'DX' pour 'FX' ou 'DTAN' pour 'FTAN'
        L'interpolation doit être linéaire entre les points
        Elle ne peut pas être :
            - une constante
            - une nappe
            - prolongée à gauche ou à droite
    3)  Si FX  la fonction est définie par au moins 3 points
        Si FTAN la fonction est définie par :
            - au moins   3 points, dans le cas isotrope
            - exactement 3 points, dans le cas cinématique
    4)  Le premier point doit être (0.0, 0.0)
    5)  La fonction doit être monotone croissante
    6)  La tangente à la fonction doit être toujours inférieure ou égale à la pente initiale
----------------------------------------------------------
Condition non respectée :: <%(i1)d>
    %(k3)s
"""
    ),
    63: _(
        """
Le Comportement %(k1)s est non valide.
La définition d'une des fonctions %(k2)s est incorrecte.
    1)  CRIT_AMOR non définie
    2)  Elles doivent être définie avec DEFI_FONCTION
        Le nom du paramètre est 'DX'
        L'interpolation doit être linéaire entre les points
        Elles ne peuvent pas :
            - Être une constante ou une nappe
            - Prolongée linéairement à gauche ou à gauche
    3)  Les fonctions sont définies par au moins 5 points
    4)  La première abscisses doit être est 0.0
    5)  Les abscisses des fonctions doivent être identiques
    6)  Les abscisses des fonctions doivent être strictement croissantes
    7)  Pour FX, les 2ères ordonnées doivent être identiques
    8)  Pour RIGI_NOR, les 2ères ordonnées doivent être identiques
    9)  Pour RIGI_NOR, la fonction doit être décroissante
   10)  Le paramètre plastique doit être strictement croissant
----------------------------------------------------------
Condition non respectée :: <%(i1)d>
    %(k3)s
"""
    ),
    64: _(
        """
Le matériau <%(k1)s> est non valide.
Les définitions des fonctions <%(k2)s> sont incorrectes.

Le paramètre plastique doit être strictement croissant.

Vérifiez les messages d'alarme de DEFI_MATERIAU
"""
    ),
    65: _(
        """
Le comportement %(k1)s est non valide.
Les valeurs des paramètres ne respectent pas les conditions imposées.
Les conditions à respecter sont :
    1)  KE doit être supérieur ou égal à KP
    2)  KDP doit être compris dans l'intervalle [KP, KE]
    3)  KDM doit être compris dans l'intervalle [KP, KE]
    4)  MYP doit être supérieur ou égal au produit de KE par RDP
    5)  MYM doit être inférieur ou égal au produit de KE par RDM
----------------------------------------------------------
Condition non respectée :: <%(i1)d>
"""
    ),
    66: _(
        """
Le Comportement %(k1)s est non valide.
La définition de la fonction %(k2)s est incorrecte.
    1)  Elle doit être définie avec DEFI_FONCTION
        Le nom du paramètre est 'DX'
        L'interpolation doit être linéaire entre les points
        Elle ne peut pas être une constante ou une nappe
        Prolongation à gauche, seulement EXCLU
        Prolongation à droite, soit EXCLU ou LINEAIRE et pas CONSTANT
    2)  La fonction est définie par au moins 2 points
    3)  Le premier point doit être (0.0, 0.0)
    4)  Abscisses et ordonnées doivent être strictement croissantes et >= 0
----------------------------------------------------------
Condition non respectée :: <%(i1)d>
    %(k3)s
"""
    ),
    67: _(
        """
La dilatation n'est pas prise en compte sur les éléments discrets en linéaire.

Conseil:
    Vous pouvez utiliser STAT_NON_LINE avec un comportement élastique.
"""
    ),
}
