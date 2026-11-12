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


class sd_partition(AsBase):
    """Included in sd_modele"""

    nomj = SDNom(fin=8)
    PRTI = AsVI(lonmax=1)
    PRTK = AsVK24(lonmax=1)

    # si PRTK(1) in ('MAIL_DISPERSE', 'MAIL_CONTIGU') :
    NUPR = Facultatif(AsVI())

    def check_1(self, checker):
        if not self.PRTI.exists:
            return
        prti = self.PRTI.get()
        assert prti[0] > 0, prti

        prtk = self.PRTK.get_stripped()
        assert prtk[0] in ("GROUP_ELEM", "SOUS_DOMAINE", "MAIL_DISPERSE", "MAIL_CONTIGU"), prtk

        if prtk[0] == "SOUS_DOMAINE":
            sd2 = sd_partit_domain(self.nomj())
            sd2.check(checker)

        if prtk[0] in ("MAIL_DISPERSE", "MAIL_CONTIGU"):
            assert self.NUPR.exists


class sd_partit_domain(AsBase):
    """Objects that only exist for SOUS_DOMAINE"""

    nomj = SDNom(fin=8)
    FDIM = AsVI(lonmax=1)
    FREF = AsVK8(lonmax=1)
    FETA = AsColl(acces="NO", stockage="DISPERSE", modelong="VARIABLE", type="I")
