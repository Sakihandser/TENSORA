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
  Erreur d'utilisation :
    Pour la méthode itérative GCPC, on ne peut pas encore utiliser
    de matrice non-symétrique.

  Conseil : Changer de solveur
"""
    ),
    2: _(
        """On ne peut pas créer la numérotation sur les matrices élémentaires car le maillage n'est pas le même."""
    ),
    3: _(
        """
 Le calcul est séquentiel, on ne peut donc pas utiliser MATR_DISTRIBUEE='OUI'.
 On force MATR_DISTRIBUEE='NON'.
"""
    ),
    4: _(
        """
 L'utilisation de MATR_DISTRIBUEE='OUI' nécessite que chaque processeur ait
 au moins 1 degré de liberté qui lui soit alloué.
 Ici, le processeur %(i1)d ne s'est vu attribué aucun ddl.

 Conseil : Modifiez le partitionnement des mailles de votre modèle dans
           AFFE_MODELE/DISTRIBUTION/METHODE ou diminuez le nombre de processeurs.
"""
    ),
    5: _(
        """
 maillage discordants
"""
    ),
    6: _(
        """
 Il n'est pas possible de mélanger simple et double Lagrange.

 Conseil : Vérifiez le mot-clé DOUBLE_LAGRANGE de vos chargements issus d'AFFE_CHAR_MECA.
"""
    ),
    7: _(
        """
 modèles discordants: %(k1)s vs %(k2)s.
"""
    ),
    8: _(
        """
 le mot-clé %(k1)s  est incorrect.
Ce message est un message d'erreur développeur.
Contactez le support technique.
"""
    ),
    9: _(
        """
À l'issue de l'étape de création de la numérotation, il n'a pas été possible de trouver un
processeur possesseur pour tous les degrés de liberté du problème.

Conseil : Si vous réaliser des manipulations de champs, vérifiez la cohérence des groupes de
noeuds et de mailles.
"""
    ),
    11: _(
        """
 on ne peut assembler que des vecteurs réels ou complexes
"""
    ),
    18: _(
        """
 Erreur développeur dans l'assemblage.
 Les vecteurs élémentaires ou les matrices élémentaires sont incohérentes: ils ne portent pas sur le même modèle
"""
    ),
    19: _(
        """
 Erreur développeur dans l'assemblage.
 Les vecteurs élémentaires ou les matrices élémentaires ne contiennent ni sous-structures, ni objet LISTE_RESU.
"""
    ),
    20: _(
        """
  Erreur programmeur :
    lors d'un assemblage, dans la liste des MATR_ELEM (ou VECT_ELEM) que l'on veut
    assembler, on ne trouve aucun résultat élémentaire
Ce message est un message d'erreur développeur.
Contactez le support technique.
"""
    ),
    21: _(
        """
 modèles différents
"""
    ),
    26: _(
        """
 le noeud:  %(k1)s composante:  %(k2)s  est bloqué plusieurs fois.
"""
    ),
    27: _(
        """
 l'entier décrivant la position du premier Lagrange ne peut être égal qu'à +1 ou -1 .
"""
    ),
    28: _(
        """
 le nombre de noeuds effectivement numérotés ne correspond pas au nombre
 de noeuds à numéroter
"""
    ),
    36: _(
        """
 noeud inexistant
"""
    ),
    37: _(
        """
 méthode :  %(k1)s  inconnue.
"""
    ),
    38: _(
        """
 noeud incorrect
"""
    ),
    41: _(
        """
 le noeud  %(i1)d  du  %(k1)s du VECT_ELEM  : %(k2)s  n'a pas d'adresse dans : %(k3)s
Ce message est un message d'erreur développeur.
Contactez le support technique.
"""
    ),
    42: _(
        """
 le noeud  : %(i1)d  du %(k1)s  du VECT_ELEM  : %(k2)s
   a une adresse  : %(i2)d  supérieur au nombre d'équations : %(i3)d
Ce message est un message d'erreur développeur.
Contactez le support technique.
"""
    ),
    43: _(
        """
Ce message est un message d'erreur développeur.
Contactez le support technique.
"""
    ),
    45: _(
        """Erreur lors de l'assemblage.
Si vous utilisez la commande MACRO_ELAS_MULT :
   S'il y a une charge contenant des conditions aux limites dualisées (DDL_IMPO, ...),
   Êtes-vous sur d'avoir indiqué cette charge derrière le mot clé CHAR_MECA_GLOBAL ?
   En effet, il faut indiquer TOUTES les charges dualisées derrière CHAR_MECA_GLOBAL.
Si vous utilisez directement la commande ASSE_VECTEUR ou la commande DYNA_VIBRA :
   S'il y a une charge contenant des conditions aux limites dualisées (DDL_IMPO, ...),
   Êtes-vous sur d'avoir indiqué cette charge à la commande NUME_DDL ?
      - Soit en utilisant le mot-clé CHARGE (associé à MODELE) de l'opérateur NUME_DDL.
      - Soit en utilisant le mot-clé MATR_RIGI (de NUME_DDL) avec une matrice élémentaire
      issue de la commande CALC_MATR_ELEM/OPTION='RIGI_MECA' à laquelle vous avez indiqué
      cette charge via le mot-clé CHARGE"""
    ),
    63: _(
        """
 erreur sur le premier Lagrange d'une LIAISON_DDL
 on a mis 2 fois le premier  Lagrange :  %(i1)d
 derrière le noeud :  %(i2)d
"""
    ),
    64: _(
        """
 erreur sur le  2ème Lagrange d'une LIAISON_DDL
 on a mis 2 fois le 2ème  Lagrange :  %(i1)d
 derrière le noeud :  %(i2)d
"""
    ),
}
