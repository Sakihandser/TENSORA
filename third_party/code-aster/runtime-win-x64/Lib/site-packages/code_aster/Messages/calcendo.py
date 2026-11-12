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
 Des valeurs incohérentes de temps caractéristiques de viscosité ont été renseignées dans la définition des paramètres matériaux.
 Ce temps caractéristique de viscosité doit nécessairement valoir 1.0 ou 0.0, et une des valeurs doit être non nulle. Vérifier la mise en donnée.
"""
    ),
    2: _(
        """
 Aucune valeur de temps caractéristique de viscosité n'a été détectée dans la définition des paramètres matériaux.
 Vérifier la mise en données.
 """
    ),
    3: _(
        """
 Erreur pour OBSERVATION_VISC = "%(k1)s".
 Vérifier la mise en données.
"""
    ),
    4: _(
        """
 CALC_ENDO ne sait pas traiter un chargement AFFE_CHAR_MECA_F ou AFFE_CHAR_CINE_F fonction du temps.
 Il est recommandé d'utiliser FONC_MULT.
"""
    ),
    5: _(
        """
 L'OBSERVATION %(k1)s porte sur le(s) groupe(s) de mailles %(k2)s.
"""
    ),
    6: _(
        """
 Le critère de stabilisation n'est pas vérifié au dernier instant de la séquence de chargement.
 On poursuit tout de même le calcul (ARRET = "NON").
"""
    ),
    7: _(
        """
 CALC_ENDO est incompatible avec l'usage de FONC_INST dans AFFE_VARC.
"""
    ),
    8: _(
        """
 Dans ETAT_INIT, les mots-clés NUME_ORDRE, INST_INIT et NUME_DIDI sont interdits.
 La poursuite d'un calcul se fait nécessairement à partir du dernier instant.
"""
    ),
    9: _(
        """
 LIST_INST_VISC attend en entrée une liste de trois instants permettant de définir le
 nombre de TAU pendant la rampe de chargement, pendant une séquence de stabilisation, et
 le nombre maximal de séquence de stabilisation.
 Vérifier la mise en données.
"""
    ),
    10: _(
        """
 Le nombre d'observations OBSERVATION_VISC doit être égal au nombre de critères de stabilisation CRIT_STAB_VISC.
"""
    ),
    11: _(
        """
 Dans le cas où l'utilisateur ne fournit pas de critère de stabilisation (OBSERVATION_VISC et CRIT_STAB_VISC non définis),
 CALC_ENDO ne peut être utilisé qu'avec un critère de convergence de type RESI_REFE_RELA.
"""
    ),
    13: _(
        """
CALC_ENDO a traité la variable de commande %(k1)s comme %(k2)s .
"""
    ),
    14: _(
        """
On a retenu TAU = %(r1)f
"""
    ),
    15: _(
        """
Une séquence de chargement fictive (rampe et stabilisation) sera calculée pour chacun des instants physiques suivants : %(k1)s
"""
    ),
    16: _(
        """
Une séquence de chargement fictive (rampe et stabilisation) sera discrétisée par la liste d'instants suivante : %(k1)s
"""
    ),
    17: _(
        """
On a trouvé %(i1)d chargement(s) fonction du temps, et %(i2)d chargement(s) indépendant(s) du temps
"""
    ),
    18: _(
        """
Séquence de chargement : %(i1)d
Instant physique initial de cette séquence de chargement : %(r1)f
Instant physique final de cette séquence de chargement : %(r2)f
"""
    ),
    19: _(
        """
Instant courant de la séquence de stabilisation : %(r1)f
"""
    ),
    20: _(
        """
%(k1)s courant : %(r1)f
Variation de %(k1)s courante : %(r2)f
"""
    ),
    21: _(
        """
Critère de stabilisation pour %(k1)s
%(k1)s courant : %(r1)f
Ratio %(k1)s sur seuil de stabilité : %(r2)f
"""
    ),
    22: _(
        """
Erreur de syntaxe dans CALC_ENDO
ARCHIVAGE_VISC et RESULTAT sous ENDO_VISC doivent être tous les deux définis ou indéfinis.
"""
    ),
}
