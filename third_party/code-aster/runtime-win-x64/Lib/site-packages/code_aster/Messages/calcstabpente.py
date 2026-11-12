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
Les maillages dans le champ des matériaux et le modèle ne sont pas les mêmes. 
"""
    ),
    2: _(
        """
RESI_MAXI ne peut pas dépasser INCR_INIT !
Au cas contraire, RESI_MAXI est considéré égale à INCR_INIT, 
soit RESI_MAXI = %(r1)f. 
"""
    ),
    3: _(
        """
L'algorithme n'a pas convergé alors qu'on atteint le nombre maximum d'itération imposé.
Veuillez examiner les propriétés des matériaux, et augmenter le FS_INIT ou le ITER_MAXI.     
"""
    ),
    4: _(
        """
Le FS_INIT est probablement supérieure au vraie facteur de sécurité. 
Veuillez diminuer le FS_INIT.      

Il est également probable que le calcul non-linéaire a été mal configuré de sorte que le calcul diverge à 
la première itération. Il est donc favorable d'effectuer l'analyse statique non-linéaire via STAT_NON_LINE avant l'usage de la 
macro-commande. 
"""
    ),
    5: _(
        """
La loi de comportement %(k1)s n'est pas autorisée.  
"""
    ),
    6: _(
        """
Le mot clé MAILLE n'est pas autorisé, veuillez remplacer par GROUP_MA.     
"""
    ),
    7: _(
        """
Exactement un comportement dans la zone d'analyse autorisé !!
Non existence ou coexistence des comportements détectée.    
"""
    ),
    8: _(
        """
Le nom du group_ma %(k1)s est trop long, ce qui rend impossible le traitement du maillage dans la zone d'analyse.     
"""
    ),
    9: _(
        """
Le group_ma %(k1)s ne fait pas partie dans le maillage.    
"""
    ),
    10: _(
        """
La loi de comportement indiquée dans l'algorithme ne se trouve pas parmi les propriétés des matériaux affectant la zone d'analyse.     
"""
    ),
    11: _(
        """
Pour la loi MOHR_COULOMB, seule la loi d'écoulement plastique associée est autorisée, soit ANGDIL = PHI.
Systématiquement ANGDIL prend la valeur de PHI lorsqu'ils ne sont pas égaux.     
"""
    ),
    12: _(
        """
Un groupe_ma ne peut être affecté par qu'un seul matériau. 
"""
    ),
    13: _(
        """
Le FS initial doit être strictement positif.     
"""
    ),
    14: _(
        """
X1_MINI, X1_MAXI, X2_MINI, X2_MAXI doivent prendre les valeurs d'ordre croissante.     
"""
    ),
    16: _(
        """
Les zones des points d'extrémité sont en dehors du profil de la pente. 
"""
    ),
    17: _(
        """
La résolution du FS selon la procédure MORGENSTERN_PRICE diverge. 
"""
    ),
    19: _(
        """
La valeur de Y_MINI est trop grande.   
"""
    ),
    20: _(
        """
La population des feux d'artifices doit être strictement positive.    
"""
    ),
    22: _(
        """
La direction d'accélération doit être un vecteur non nul.  
"""
    ),
    23: _(
        """
Le résultat de pression hydraulique doit provenir du modèle D_PLAN_H/HH*.
"""
    ),
    24: _(
        """
Matériau non défini sur la maille M%(i1)d.
"""
    ),
    25: _(
        """
On se propose d'utiliser PHI_B (angle de succion) pour calculer la résistance due à la succion.
Cependant, on ne l'a pas affecté à la maille M%(i1)d.
"""
    ),
    26: _(
        """
Afin de calculer la résistance due à la succion, en l'absence de PHI_B,
le comportement hydraulique du matériau doit être défini par le modèle Van-Genuchten ou par la courbe saturation / pression capillaire. 
"""
    ),
    27: _(
        """
Impossible de trouver une surface de rupture circulaire sur le maillage entré à l'issue de 100 fois d'ajustement. 
Code retour : %(i1)d
"""
    ),
    28: _(
        """
Une surface de rupture seule à tester : x_enter=%(r1)f, x_exit=%(r2)f, Rayon=%(r3)f.
Cependant, cette surface se situe en dehors du modèle. 
"""
    ),
    29: _(
        """
Fondation de taille insuffisante.
"""
    ),
    30: _(
        """
Impossible de trouve une surface de rupture circulaire valide. 
Code retour : %(i1)d
"""
    ),
    31: _(
        """
Impossible d'initialiser l'algorithme EFWA suite à l'échec de générer les surfaces ruptures non-circulaires. 
Veuillez vérifier et ajuster le maillage et les paramètres EFWA. 
"""
    ),
    32: _(
        """
Échec de résoudre l'équations des cercles. 
Cela est probablement à cause du rayon trop faible (%(r1)f) et inférieure à 1/2 du segment X1-X2 (%(r2)f)
pour les abscisses X1 = %(r3)f, X2 = %(r4)f.

On propose les solutions suivantes :
-   Raffinement du maillage autour de la pente. 
-   Ajuster NB_POINT_1 et NB_POINT_2 afin d'éviter que les points d'extrémité soient trop proches des points aigus convexes sur la pente.   
"""
    ),
}
