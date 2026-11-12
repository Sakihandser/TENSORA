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
from .sd_maillage import sd_maillage
from .sd_util import *


class sd_nume_equa(AsBase):
    nomj = SDNom(fin=19)
    NEQU = AsVI(lonmax=2)
    DELG = AsVI()
    REFN = AsVK24(lonmax=5)
    PRNO = AsColl(acces="NU", stockage="CONTIG", modelong=Parmi("CONSTANT", "VARIABLE"), type="I")
    LILI = AsObject(genr="N", xous="S", type="K", ltyp=24)
    NUEQ = AsVI()
    DEEQ = AsVI()

    def exists(self):
        # retourne "vrai" si la SD semble exister (et donc qu'elle peut etre
        # vérifiée)
        return self.PRNO.exists

    def check_REFN(self, checker):
        assert self.REFN.exists
        refn = self.REFN.get_stripped()

        # nom du maillage :
        assert refn[0] != ""
        sd2 = sd_maillage(refn[0])
        sd2.check(checker)

        # nom de la grandeur :
        assert refn[1] != ""
        assert sdu_verif_nom_gd(refn[1]), refn[1] + " n'est pas un nom de grandeur."

        # Cas ELIM_LAGR :
        assert refn[3] in ("", "ELIM_LAGR", "SIMPLE_LAGRANGE")

    def check_1(self, checker):
        if not self.exists():
            return
        nueq = self.NUEQ.get()
        deeq = self.DEEQ.get()
        neq = len(deeq) // 2
        for x in nueq:
            assert 0 <= x and x <= neq

        for k in range(neq):
            nuno = deeq[2 * k]
            nucmp = deeq[2 * k + 1]
            if nuno == 0:
                assert nucmp == 0
            else:
                assert nucmp != 0

        nequ = self.NEQU.get()
        delg = self.DELG.get()
        neq = nequ[0]
        assert neq >= 0
        assert nequ[1] >= 0
        assert len(delg) >= neq
        for x in delg:
            assert x in (-2, -1, 0)
