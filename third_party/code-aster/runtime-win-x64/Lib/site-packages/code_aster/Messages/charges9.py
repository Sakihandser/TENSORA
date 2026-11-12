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
    1: _("""On ne peut pas piloter le chargement car il dépend du temps."""),
    2: _(
        """
Un chargement a été déclaré comme étant pilotable alors que ce n'est pas possible.
Si votre chargement contient plusieurs types dont certains ne peuvent être pilotables, il faut les séparer.
"""
    ),
    3: _(
        """
Un chargement a été déclaré comme étant suiveur alors que ce n'est pas possible.
Si votre chargement contient plusieurs types dont certains ne peuvent être suiveurs, il faut les séparer.
"""
    ),
    4: _("""Le chargement doit être obligatoirement de type suiveur (par exemple: ECHANGE_THM)."""),
    5: _(
        """Le chargement doit être obligatoirement de type suiveur car il dépend de la vitesse et/ou de l'accélération."""
    ),
    6: _(
        """Le chargement ne peut être utilisé qu'en dynamique car il dépend de la vitesse et/ou de l'accélération."""
    ),
    7: _(
        """Un des chargements est de type cinématique (AFFE_CHAR_CINE): il ne peut pas être piloté."""
    ),
    9: _("""Le chargement est de type force ou flux et ne peut donc pas utiliser DIDI."""),
    10: _("""Un des chargements est spécifié plus d'une fois."""),
    11: _("""Le chargement FORCE_SOL ne peut pas être suiveur."""),
    12: _("""Le chargement FORCE_SOL ne peut pas être de type Dirichlet différentiel."""),
    13: _("""Le chargement FORCE_SOL ne peut pas être piloté."""),
    14: _("""Le chargement FORCE_SOL ne peut pas être piloté et suiveur."""),
    15: _("""Le chargement FORCE_SOL n'est utilisable qu'en dynamique."""),
    16: _("""Le modèle d'un chargement n'est pas le même que celui du calcul."""),
    17: _("""Un des chargements n'est pas mécanique."""),
    18: _(
        """Un des chargements ne peut pas utiliser de fonction multiplicatrice FONC_MULT car il est piloté."""
    ),
    19: _("""Le pilotage est activé mais aucun chargement n'est déclaré comme pilotable"""),
    20: _("""On ne peut pas piloter plus d'un chargement."""),
    21: _("""Le chargement EVOL_CHAR ne peut pas être piloté."""),
    22: _("""Le chargement EVOL_CHAR ne peut pas être piloté et suiveur."""),
    31: _("""Le chargement ONDE_PLANE ne peut pas être piloté."""),
    32: _("""Le chargement ONDE_PLANE ne peut pas être suiveur."""),
    33: _("""Le chargement ONDE_PLANE ne peut pas être piloté et suiveur."""),
    37: _("""Un des chargements n'est pas thermique."""),
    38: _("""Un des chargements n'est pas acoustique."""),
    39: _("""Un chargement de type ECHANGE n'est pas compatible avec FONC_MULT."""),
    40: _(
        """Un des chargements contient une condition de type %(k1)s et elle n'est pas compatible avec FONC_MULT, sauf si PARM_THETA vaut 1."""
    ),
    41: _(
        """Les chargements de type EVOL_CHAR sont interdits avec THER_NON_LINE si PARM_THETA est différent de 1."""
    ),
    42: _(
        """Un des chargements contient une condition de type %(k1)s impossible dans cet opérateur linéaire."""
    ),
    43: _("""Un chargement qui dépend de la température n'est pas compatible avec FONC_MULT."""),
    49: _(
        """
Vous avez fourni %(i1)d charges alors qu'il n'y a %(i2)d dans la structure de données résultat.

Risque & Conseil :
   Vous pouvez obtenir des résultats faux si les charges sont différentes.
   Vérifiez que vous n'avez pas oublié de charge ou que vous n'en avez pas ajouté.
"""
    ),
    50: _(
        """
Le chargement fourni par l'utilisateur est différent de celui présent dans la structure de données résultat.
Risque & Conseil : Vérifiez si le chargement fourni dans la commande est bien celui que vous souhaitez.
Si oui vous allez poursuivre les calculs post-traitement avec un chargement différent de celui utilisé
pour calculer les déplacements, températures,...
"""
    ),
    51: _(
        """
Les fonctions multiplicatrices du chargement (mot clé: FONC_MULT) fournies par l'utilisateur sont
différentes de celles présentes dans la structure de données résultat.

Risque & Conseil : Vérifiez si les fonctions fournies dans la commande sont bien celles que vous souhaitez.
Si oui vous allez poursuivre les calculs de post-traitement avec des fonctions différentes de celles
utilisées pour calculer les déplacements, températures,...
"""
    ),
    52: _(
        """
Le couple (charge, fonction) fourni par l'utilisateur n'est pas présent dans la structure de données résultat.
"""
    ),
    53: _(
        """Les chargements ne sont pas les mêmes entre ceux contenus dans le résultat et ceux données dans le fichier de commande. On prend ces derniers."""
    ),
    61: _("""Les chargements de Dirichlet de type AFFE_CHAR_CINE sont ignorés."""),
    62: _("""Les chargements de Dirichlet de type AFFE_CHAR_MECA sont ignorés."""),
    63: _("""Les chargements de type AFFE_CHAR_MECA / %(k1)s  sont ignorés."""),
}
