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
        Le champ %(k1)s que l'on souhaite combiner n'est pas présent
        dans l'occurrence %(i1)d du résultat.

        Veuillez calculer ce champ au préalable à l'aide de la commande
        CALC_CHAMP.
    """
    ),
    2: _(
        """
        Les maillages sur lesquels sont définis les résultats ne sont
        pas identiques.
    """
    ),
    3: _(
        """
        Les colonnes de la table de l'occurrence %(i1)d de AFFE sont
        différentes des colonnes de la table de l'occurrence 1.
    """
    ),
    4: _(
        """
        Erreur dans l'occurrence %(i1)d de AFFE :
        Le nom du cas %(k1)s ne correspond à aucune colonne du tableau de
        coefficients.
    """
    ),
    5: _(
        """
        Erreur dans le tableau de coefficients:
        La colonne %(k1)s ne correspond à aucun NOM_CAS de AFFE .
    """
    ),
    6: _(
        """
        La coupure %(k1)s n'est pas présente dans la table de l'occurrence %(i1)d
        de AFFE.
    """
    ),
    10: _(
        """
        Le maillage ne contient pas le GROUP_MA :  %(k1)s  
    """
    ),
    11: _(
        """
        Le nombre de noeuds de la coupure %(k1)s est différent selon les ordres
    """
    ),
}
