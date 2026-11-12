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
from .sd_matr_elem import sd_matr_elem
from .sd_modele import sd_modele


class sd_vect_elem(sd_matr_elem):
    nomj = SDNom(fin=19)
    RERR = AsVK24(lonmax=1)
    RELC = Facultatif(AsColl(acces="NO", stockage="CONTIG", modelong="CONSTANT", type="I"))

    def check_RELC(self, checker):
        if not self.RELC.exists:
            return
        lchar = self.RELC.get()
        for nochar in list(lchar.keys()):
            for k in lchar[nochar]:
                assert k in (0, 1), lchar

    def check_1(self, checker):
        refe = self.RERR.get_stripped()
        assert self.RELR.exists
        sd2 = sd_modele(refe[0])
        sd2.check(checker)
