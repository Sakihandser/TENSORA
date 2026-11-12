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
from .sd_nume_equa import sd_nume_equa
from .sd_maillage import sd_maillage
from .sd_titre import sd_titre
from .sd_util import *


class sd_cham_no(sd_titre):
    nomj = SDNom(fin=19)
    VALE = AsVect(
        ltyp=Parmi(4, 8, 16, 24), type=Parmi("C", "I", "K", "R"), docu=Parmi("", "2", "3")
    )
    REFE = AsVK24(lonmax=4, docu="CHNO")

    def exists(self):
        # retourne "vrai" si la SD semble exister (et donc qu'elle peut etre
        # vérifiée)
        return self.REFE.exists

    def u_refe(self):
        refe = self.REFE.get_stripped()
        assert refe[0] == "", refe
        nume_equa = refe[1]
        assert refe[2] == "", refe
        assert refe[3] == "", refe
        return nume_equa

    def check_cham_no_i_REFE(self, checker):

        if not self.exists():
            return
        if self.REFE in checker.names:
            return

        nume_equa = self.u_refe()

        # maillage vérifié dans le nume_equa
        sd2 = sd_nume_equa(nume_equa)
        sd2.check(checker)
