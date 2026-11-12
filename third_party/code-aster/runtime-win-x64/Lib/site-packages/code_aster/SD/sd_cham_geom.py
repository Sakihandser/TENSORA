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
from .sd_titre import sd_titre
from .sd_util import *


class sd_cham_geom(sd_titre):
    nomj = SDNom(fin=19)
    VALE = AsVect(ltyp=Parmi(4, 8, 16, 24), type=Parmi("R"), docu=Parmi("", "2", "3"))
    DESC = AsVI(docu="CHGO")

    def exists(self):
        # retourne "vrai" si la SD semble exister (et donc qu'elle peut etre
        # vérifiée)
        return self.VALE.exists

    def u_desc(self):
        desc = self.DESC.get()
        gd = desc[0]
        num = desc[1]
        return gd, num

    def check_cham_geom_DESC(self, checker):
        if not self.exists():
            return
        if self.DESC in checker.names:
            return

        gd, num = self.u_desc()
        if num < 0:
            nb_ec = sdu_nb_ec(gd)
            assert nb_ec == 1
            assert self.DESC.lonmax == 3
        else:
            assert False
