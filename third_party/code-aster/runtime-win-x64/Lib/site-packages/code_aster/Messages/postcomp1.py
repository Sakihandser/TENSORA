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
        """Le modèle fourni par l'utilisateur est différent de celui présent dans la structure de données résultat.
On poursuit les calculs avec le modèle fourni par l'utilisateur."""
    ),
    3: _("""On a besoin d'un modèle pour calculer l'option %(k1)s."""),
    4: _(
        """Il n'a pas été possible d'établir si les champs sont à composantes réelles ou complexes car on ne trouve pas de champ de déplacement ou de mode dans le résultat entrant."""
    ),
    5: _(
        """
Les contributions de l'amortissement liées à la vitesse pour les réactions nodales sont négligées.
"""
    ),
    6: _(
        """
Les caractéristiques élémentaires fournies par l'utilisateur sont différentes de celles présentes dans la structure de données Résultat.
On poursuit les calculs avec celles fournies par l'utilisateur.
"""
    ),
    7: _(
        """
Le matériau fourni par l'utilisateur est différent de celui présent dans la structure de données Résultat.
On poursuit les calculs avec le matériau fourni par l'utilisateur.
"""
    ),
    8: _(
        """On aura peut-être besoin du matériau pour calculer l'option %(k1)s. Cette alarme risque donc de se transformer en erreur."""
    ),
    9: _(
        """On a besoin du champ des déplacements pour le calcul de l'option %(k1)s . Ce champ n'existe pas dans le résultat pour le numéro d'ordre %(i1)d.
"""
    ),
    10: _(
        """On n'a pas réussi à récupérer la numérotation des inconnues pour le calcul de l'option %(k1)s."""
    ),
    11: _(
        """
 L'option %(k1)s est déjà calculée pour le numéro d'ordre %(i1)d.
 On la recalcule car les données peuvent être différentes."""
    ),
    13: _(
        """
 Pour les calculs harmoniques, on ne permet pas de restreindre l'estimation de l'option %(k1)s sur un groupe de mailles.
"""
    ),
    14: _(
        """On aura probablement besoin des caractéristiques élémentaires pour calculer l'option %(k1)s."""
    ),
    15: _(
        """La récupération des chargements n'est actuellement pas possible. Or ils sont nécessaires pour l'option %(k1)s.
        Si le résultat est issu d'un calcul dynamique, pensez à renseigner les chargements dans la commande."""
    ),
    16: _(
        """
 Il n'a pas été possible de récupérer d'information concernant la matrice de masse
 assemblée de la structure. Le calcul de l'option %(k1)s n'est donc pas possible.
 """
    ),
    17: _(
        """On a besoin du champ des accélérations pour le calcul de l'option %(k1)s . Ce champ n'existe pas dans le résultat pour le numéro d'ordre %(i1)d.
"""
    ),
    18: _(
        """Le post-traitement n'est pas possible car on ne trouve pas le mode de Fourier dans le résultat.
"""
    ),
    19: _(
        """On a besoin de la pulsation pour le calcul de l'option %(k1)s . Ce paramètre n'existe pas dans le résultat pour le numéro d'ordre %(i1)d.
"""
    ),
}
