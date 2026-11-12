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
MODI_REPERE / CHAMP_GD
    Seuls les champs de contraintes à sous-points issus d'une projection sont traités.
"""
    ),
    2: _(
        """
MODI_REPERE / CHAMP_GD
    Le mot clé REPERE est obligatoire et doit valoir GLOBAL_UTIL.
"""
    ),
    3: _(
        """
MODI_REPERE / CHAMP_GD
    Le mot clé REPERE doit valoir GLOBAL_UTIL.
"""
    ),
    4: _(
        """
Le CARA_ELEM doit avoir des caractéristiques de coque.
"""
    ),
    5: _(
        """
Les maillages du champ et du CARA_ELEM doivent être identiques.
"""
    ),
    6: _(
        """
Les modèles du champ et du CARA_ELEM doivent être identiques.
"""
    ),
    7: _(
        """
MODI_REPERE / CHAMP_GD
    Le mot clé CARA_ELEM est obligatoire.
"""
    ),
    9: _(
        """
 le mot clé "TRAN" sous le mot clé facteur %(k1)s  n"admet que 3 valeurs
"""
    ),
    10: _(
        """
 le mot clé "ANGL_NAUT" sous le mot clé facteur %(k1)s  n"admet que 3 valeurs
"""
    ),
    11: _(
        """
 le mot clé "centre" sous le mot clé facteur %(k1)s  n"admet que 3 valeurs
"""
    ),
    12: _(
        """
  Mot clé LIAISON_GROUP : les mots clés %(k1)s et %(k2)s à mettre
  en vis-à-vis n'ont pas le même nombre de noeuds.

   - Nombre de noeuds présent sous le mot clé %(k1)s: %(i1)d
   - Nombre de noeuds présent sous le mot clé %(k2)s: %(i2)d

"""
    ),
    13: _(
        """
 Il n'y a aucun groupe de noeuds ni aucun noeud défini après le mot facteur  %(k1)s
"""
    ),
    14: _(
        """
MODI_REPERE / RESULTAT / concept réentrant
    Le mot clé REPERE est obligatoire et doit valoir "COQUE_INTR_UTIL" ou "COQUE_UTIL_INTR"
"""
    ),
    15: _(
        """
MODI_REPERE / RESULTAT / concept réentrant
    Le mot clé REPERE vaut %(k1)s. Il est interdit d'utiliser le même concept résultat en entrée et en sortie de
    la commande MODI_REPERE pour ce type de changement de repère.

    Conseils : Définissez un concept résultat différent en sortie de la commande.
"""
    ),
    18: _(
        """
 la table "CARA_GEOM" n'existe pas dans le maillage
"""
    ),
    19: _(
        """
 mailles mal orientées
"""
    ),
    20: _(
        """
 pour les segments en 3d, il faut renseigner VECT_ORIE_pou
"""
    ),
    21: _(
        """
 pas de normale pour les tria en 2d
"""
    ),
    22: _(
        """
 pas de normale pour les quadrangles en 2d
"""
    ),
    37: _(
        """
 erreur pour extension de la carte  %(k1)s
Ce message est un message d'erreur développeur.
Contactez le support technique.
"""
    ),
    60: _(
        """
 on ne donne le mot facteur "CONVECTION" qu'une fois au maximum
"""
    ),
    64: _(
        """
 nombre d occurrence du mot clé "SOUR_CALCULEE"  supérieur a 1
"""
    ),
    67: _(
        """
 on doit utiliser obligatoirement le mot-clé DIST pour définir la demi largeur de bande.
"""
    ),
    68: _(
        """
 on doit donner une distance strictement positive pour définir la bande.
"""
    ),
    69: _(
        """
 on doit utiliser obligatoirement le mot-clé ANGL_NAUT ou le mot-clé VECT_NORMALE pour l'option bande de CREA_GROUP_MA. ce mot-clé permet de définir la direction perpendiculaire au plan milieu de la bande.
"""
    ),
    70: _(
        """
 pour l'option bande de CREA_GROUP_MA, il faut  définir les 3 composantes du vecteur perpendiculaire au plan milieu de la  bande quand on est en 3d.
"""
    ),
    71: _(
        """
 pour l'option bande de CREA_GROUP_MA, il faut  définir les 2 composantes du vecteur perpendiculaire au plan milieu de la  bande quand on est en 2d.
"""
    ),
    72: _(
        """
 erreur dans la donnée du vecteur normal au plan milieu de la  bande : ce vecteur est nul.
"""
    ),
    73: _(
        """
 l'option cylindre de CREA_GROUP_MA n'est utilisable qu'en 3d.
"""
    ),
    74: _(
        """
 on doit utiliser obligatoirement le mot-clé rayon pour définir le rayon du cylindre.
"""
    ),
    75: _(
        """
 on doit donner un rayon strictement positif pour définir le cylindre.
"""
    ),
    76: _(
        """
 on doit utiliser obligatoirement le mot-clé ANGL_NAUT ou le mot-clé VECT_NORMALE pour l'option cylindre de CREA_GROUP_MA
"""
    ),
    77: _(
        """
 pour l'option cylindre de CREA_GROUP_MA, il faut  définir les 3 composantes du vecteur orientant l'axe du cylindre quand on utilise le mot-clé VECT_NORMALE.
"""
    ),
    78: _(
        """
 pour l'option cylindre de CREA_GROUP_MA, il faut définir les 2 angles nautiques quand on utilise le mot-clé "ANGL_NAUT".
"""
    ),
    79: _(
        """
 erreur dans la donnée du vecteur orientant l'axe du cylindre,ce vecteur est nul.
"""
    ),
    80: _(
        """
 on doit utiliser obligatoirement le mots-clés ANGL_NAUT ou le mot-clé VECT_NORMALE pour l'option FACE_NORMALE de CREA_GROUP_MA
"""
    ),
    81: _(
        """
 erreur dans la donnée du vecteur normal selon lequel on veut sélectionner des mailles : ce vecteur est nul.
"""
    ),
    82: _(
        """
 on doit utiliser obligatoirement le mot-clé rayon pour définir le rayon de la sphère.
"""
    ),
    83: _(
        """
 on doit donner un rayon strictement positif pour définir la sphère.
"""
    ),
    84: _(
        """
 l'option ENV_CYLINDRE de CREA_GROUP_NO n'est utilisable qu'en 3d.
"""
    ),
    85: _(
        """
 on doit utiliser obligatoirement le mot-clé ANGL_NAUT ou le mot-clé VECT_NORMALE pour l'option ENV_CYLINDRE de CREA_GROUP_NO
"""
    ),
    86: _(
        """
 pour l'option ENV_CYLINDRE de CREA_GROUP_NO, il faut définir les 3 composantes du vecteur orientant l'axe du cylindre quand on utilise le mot clé "VECT_NORMALE".
"""
    ),
    87: _(
        """
 pour l'option ENV_CYLINDRE de CREA_GROUP_NO, il faut définir les 2 angles nautiques quand on utilise le mot clé "ANGL_NAUT".
"""
    ),
    88: _(
        """
 le mot-clé précision est obligatoire après le mot-clé ENV_CYLINDRE pour définir la tolérance (i.e. la distance du point a l'enveloppe du cylindre) acceptée pour déclarer l'appartenance du point a cette enveloppe.
"""
    ),
    89: _(
        """
 on doit donner une demi épaisseur strictement positive définir l'enveloppe du cylindre.
"""
    ),
    90: _(
        """
 le mot-clé précision est obligatoire après le mot-clé ENV_SPHERE pour définir la tolérance (i.e. la distance du point a l'enveloppe de la sphère) acceptée pour déclarer l'appartenance du point a cette enveloppe.
"""
    ),
    91: _(
        """
 on doit donner une demi épaisseur strictement positive définir l'enveloppe de la sphère.
"""
    ),
    92: _(
        """
 erreur dans la donnée du vecteur orientant l'axe d'un segment ,ce vecteur est nul.
"""
    ),
    93: _(
        """
 on doit utiliser obligatoirement le mot-clé ANGL_NAUT ou le mot-clé VECT_NORMALE pour l'option plan de CREA_GROUP_NO. ce mot-clé permet de définir la direction  perpendiculaire au plan ou a la droite.
"""
    ),
    94: _(
        """
 pour l'option plan de CREA_GROUP_NO, il faut  définir les 3 composantes du vecteur perpendiculaire au plan.
"""
    ),
    95: _(
        """
 pour l'option plan de CREA_GROUP_NO, il faut  définir les 2 composantes du vecteur perpendiculaire a la droite.
"""
    ),
    96: _(
        """
 erreur dans la donnée du vecteur normal au plan ou a la droite : ce vecteur est nul.
"""
    ),
    97: _(
        """
 le mot-clé précision est obligatoire après le mot-clé plan  pour définir la tolérance (i.e. la distance du point au plan ou a la droite) acceptée pour déclarer l'appartenance du point a ce plan ou a cette droite.
"""
    ),
    98: _(
        """
 on doit donner une tolérance strictement positive pour vérifier l'appartenance d'un noeud au plan ou a la droite.
"""
    ),
    99: _(
        """
 il manque l'ensemble des noeuds que l'on veut ordonner, mots clés "noeud" et/ou "GROUP_NO"
"""
    ),
}
