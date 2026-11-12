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
    1: (
        """
        Les vecteurs X et Y du repère local renseigné ne sont pas orthogonaux :
        Le produit scalaire des deux vecteurs est égal à %(r1)f.        
    """
    ),
    2: (
        """
        Les vecteurs X et Z du repère local renseigné ne sont pas orthogonaux.
        Le produit scalaire des deux vecteurs est égal à %(r1)f.
    """
    ),
    3: (
        """
        Les vecteurs Y et Z du repère local renseigné ne sont pas orthogonaux.
        Le produit scalaire des deux vecteurs est égal à %(r1)f.
    """
    ),
    4: (
        """
        Le nombre d'amortissement renseigné doit  être égal à 1 ou correspondre au nombre de 
        modes dans la base modale fournie.
        
        Vous avez fourni %(i1)i amortissement alors que la base modale contient %(i2)i modes.
    """
    ),
    6: (
        """
        Les coupures doivent avoir des noms différents.
    """
    ),
    7: (
        """
        Si MODAL_SPECTRAL = 'OUI', RESULTAT doit être un concept de type MODE_MECA.
    """
    ),
}
