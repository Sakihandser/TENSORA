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
    2: _(
        """
La méthode de Newmark est programmée sous sa forme implicite: le paramètre BETA ne doit pas être nul.
 """
    ),
    3: _(
        """
DYNA_VIBRA : Vous n'avez pas fourni le champs de matériau (mot-clé CHAM_MATER).
Cette information n'est donc pas stockée dans le concept résultat.
Aucun post-traitement lié à CHAM_MATER ne sera possible.
 """
    ),
    4: _(
        """
DYNA_VIBRA : Vous n'avez pas fourni le champs de matériau (mot-clé CHAM_MATER)
or il est obligatoire en présence de chargements de type onde plane.
 """
    ),
    11: _(
        """
Vous utilisez une méthode à pas adaptatif: la donnée du pas est obligatoire.
"""
    ),
    12: _(
        """
Vous utilisez une méthode à pas adaptatif: le pas de temps ne peut pas être nul.
"""
    ),
    13: _(
        """
Les matrices de masse élémentaires doivent obligatoirement avoir été  calculées avec l'option MASS_MECA_DIAG.
"""
    ),
    16: _(
        """
A l'instant %(r1)f, l'erreur vaut %(r2)f
Cette erreur est supérieure à un.
Le pas de temps vaut %(r3)f
On arrête de le réduire, car le nombre de réductions a atteint %(i1)d, qui est le maximum possible.
"""
    ),
    17: _(
        """
Vous utilisez une méthode à pas adaptatif: le pas de temps minimal a été atteint.
"""
    ),
    20: _(
        """
Un chargement de type Dirichlet non homogène nécessite la résolution par le schéma de NEWMARK.
"""
    ),
    21: _(
        """
Nombre de pas de calcul : %(i1)d
Nombre d'itérations     : %(i2)d
"""
    ),
    24: _(
        """
Avec les chargements sélectionnés, le modèle est obligatoire.
"""
    ),
    25: _(
        """
Le champ "DEPL" n'est pas trouvé dans le concept résultat de l'état initial.
"""
    ),
    26: _(
        """
Le champ "VITE" n'est pas trouvé dans le concept résultat de l'état initial.
"""
    ),
    27: _(
        """
Le champ "ACCE" n'est pas trouve dans le concept résultat de l'état initial.
"""
    ),
    28: _(
        """
La commande DYNA_VIBRA avec TYPE_CALCUL="HARM" utilise un concept ré-entrant : le concept dans le mot-clé "RESULTAT" doit avoir le même nom que la sortie.
"""
    ),
    29: _(
        """
La commande DYNA_VIBRA avec TYPE_CALCUL="HARM" utilise un concept ré-entrant : le concept dans le mot-clé "RESULTAT" est d'un type différent.
"""
    ),
    31: _(
        """
La commande DYNA_VIBRA avec TYPE_CALCUL="HARM" utilise un concept ré-entrant : le mot-clé "RESULTAT" est obligatoire.
"""
    ),
    34: _(
        """
Les matrices ne possèdent pas toutes la même numérotation.
"""
    ),
    46: _(
        """
 Il manque les modes statiques. Vérifiez que MODE_STAT est bien renseigné.
"""
    ),
    89: _(
        """
L'instant de reprise est supérieur au dernier instant dans la liste.
Instant de reprise :  %(r1)f
Dernier instant    :  %(r2)f
"""
    ),
    90: _(
        """
On n'a pas trouvé l'instant de reprise.
Instant de reprise:  %(r1)f
Pas de temps      :  %(r2)f
Borne min         :  %(r3)f
Borne max         :  %(r4)f
"""
    ),
    91: _(
        """
L'instant final est inférieur au premier instant dans la liste.
Instant final:  %(r1)f
Instant min  :  %(r2)f
"""
    ),
    92: _(
        """
On n'a pas trouvé l'instant dans la liste.
Instant final:  %(r1)f
Pas de temps :  %(r2)f
Borne min    :  %(r3)f
Borne max    :  %(r4)f
"""
    ),
    95: _(
        """
L'entrée d'amortissements réduits est incompatible avec le type de la matrice de rigidité.
Il faut des matrices de type MATR_ASSE_GENE.
"""
    ),
    96: _(
        """
Le nombre de coefficients d'amortissement réduit est trop grand.
Il y a %(i1)d modes propres et %(i2)d coefficients.
On ne garde donc que les  %(i3)d premiers coefficients.
"""
    ),
    97: _(
        """
Le nombre de coefficients d'amortissement réduit est trop petit, il en manque %(i1)d car il y a %(i2)d modes propres.
On rajoute  %(i3)d amortissements réduits avec la valeur de celui du dernier mode propre.
"""
    ),
    98: _(
        """
Vous utilisez MATR_AMOR et MATR_IMPE_PHI au même temps. Si vous n'avez pas désactivé le calcul de l'amortissement
des éléments absorbants fluides dans l'option AMOR_MECA, vous prenez en compte l'amortissement deux fois. Pour désactiver
cet alarme, il suffit de donner AMOR_FLUI = "NON" dans DYNA_VIBRA.
"""
    ),
}
