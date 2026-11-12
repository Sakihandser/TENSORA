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

from . import *
from .sd_l_table import sd_l_table
from .sd_ligrel import sd_ligrel
from .sd_xfem import sd_modele_xfem


class sd_modele(AsBase):
    # -----------------------------
    nomj = SDNom(fin=8)

    MODELE = sd_ligrel()

    # une sd_modele peut avoir une "sd_l_table" contenant des grandeurs
    # caractéristiques de l'étude :
    lt = Facultatif(sd_l_table(SDNom(nomj="")))

    # Si le modèle vient de MODI_MODELE_XFEM :
    xfem = Facultatif(sd_modele_xfem(SDNom(nomj="")))

    # def check_debug(self, _):
    #     print("DEBUG: model.nomj:", self.nomj())
    #     from ..Commands import IMPR_CO
    #     IMPR_CO(UNITE=6, CHAINE=self.nomj().strip())
