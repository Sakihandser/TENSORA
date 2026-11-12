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

"""
:py:class:`GeneralizedModel` --- Generalized Assembly matrix
****************************************************
"""

import aster
from libaster import GeneralizedModel

from ..Utilities import injector


@injector(GeneralizedModel)
class ExtendedGeneralizedModel:
    cata_sdj = "SD.sd_modele_gene.sd_modele_gene"

    def LIST_SOUS_STRUCT(self):
        """retourne la liste des sous structures du modele generalise
        la liste des macro-elements sous-jacents"""

        return [
            (name, self.getDynamicMacroElementFromName(name))
            for name in self.getDynamicMacroElementNames()
        ]

    def LIST_LIAIS_STRUCT(self):
        """retourne la liste des liaisons entre sous structures du modele generalise sous la forme :
        [ (ss1, nom_liais1,  ss2 , nom_liais2), ...]"""

        dynamic_structure_links = self.getDynamicStructureLinks()
        return [
            dynamic_structure_links[4 * i : 4 * (i + 1)]
            for i in range(len(dynamic_structure_links) // 4)
        ]
