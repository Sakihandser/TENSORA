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
from .sd_proj_mesu import sd_proj_mesu
from .sd_resu_dyna import sd_resu_dyna
from .sd_titre import sd_titre
from .sd_util import *


class sd_dyna_gene_common(AsBase):
    # --------------------------------------
    nomj = SDNom(fin=19)

    # Ces trois objets sont facultatifs car dans le cas d'un calcul HARM, seul
    # un parmi les trois est obligatoire.
    ACCE = Facultatif(OJBVect(type=Parmi("C", "R")))
    VITE = Facultatif(OJBVect(type=Parmi("C", "R")))
    # peuvent etre des gros objets. Contienent des reels si
    # calcul TRAN et des complexes si HARM
    DEPL = Facultatif(OJBVect(type=Parmi("C", "R")))

    PTEM = Facultatif(AsVR())
    # Pas de temps d'integration sauvegardés aux instants
    # d'archivage

    DISC = Facultatif(AsVR())
    # gros objet. contient la liste des instants du calcul
    # sauvegardes si TRANS et les frequences si HARM
    ORDR = Facultatif(AsVI())  # gros objet.

    DESC = AsVI(lonmax=6)

    # si nbexcit > 0 :
    FACC = Facultatif(AsVK8())
    FDEP = Facultatif(AsVK8())
    FVIT = Facultatif(AsVK8())
    IPSD = Facultatif(AsVR())

    BLOC = Facultatif(AsVR())
    BLO2 = Facultatif(AsVI())

    def u_dime(self):  # --> ok

        desc = self.DESC.get()
        indic = desc[0]

        assert indic in (1, 2, 3, 4)

        if indic in (1, 2, 3):
            type_calcul = "TRAN"
        elif indic == 4:
            type_calcul = "HARM"

        nbmode = desc[1]
        assert nbmode > 0
        nbnoli = desc[2]
        assert nbnoli >= 0
        nbvint = desc[3]
        assert nbvint >= 0

        if self.ORDR.exists:
            nbsauv = self.ORDR.lonmax
        else:
            nb_bloc = self.BLOC.lonmax
            self.ordr = []
            for i_bloc in range(1, nb_bloc + 1):
                self.ordr.append(AsVI(self.nomj()[:8] + ".%07d   " % i_bloc + ".ORDR"))
            nbsauv = sum(ordr.lonmax - 1 for ordr in self.ordr) + 1
        assert nbsauv > 0

        if self.FACC.exists:
            nbexcit = self.FACC.lonmax / 2
            assert nbexcit >= 0
        else:
            nbexcit = 0

        return (type_calcul, nbmode, nbnoli, nbsauv, nbexcit, nbvint)

    def check_DESC(self, checker):  # --> ok
        desc = self.DESC.get()

        # on verifie que le .DESC est rempli avec des valeurs autorisees
        assert desc[0] in (1, 2, 3, 4), desc

        # on verifie que dans le cas d'un calcul harmonique, il n'y a pas de
        # presence de non linearites
        if desc[0] == 4:
            assert desc[2] == 0  # pas de nonlinearie si HARM
            assert desc[3] == 0  # pas de correction statique ou multi appui si HARM

    def check_ORDR_DISC(self, checker):
        type_calcul, nbmode, nbnoli, nbsauv, nbexcit, nbvint = self.u_dime()

        if self.ORDR.exists:
            assert self.ORDR.lonmax == nbsauv  # verification de la longueur
            sdu_tous_differents(self.ORDR, checker)

            ## verification de tous les elements differents
            if nbsauv > 1:
                assert sdu_monotone(self.ORDR.get()) == 1  # test de monotonie croissante

            assert self.DISC.lonmax == nbsauv  # verification de la longueur
            sdu_tous_differents(self.DISC, checker)
            ## verification de tous les elements differents

            if type_calcul == "TRAN" and nbsauv > 1:
                assert sdu_monotone(self.DISC.get()) == 1  # test de monotonie croissante
                assert self.PTEM.lonmax == nbsauv

        else:
            for i_bloc, ordr in enumerate(self.ordr, 1):
                disc = AsVR(self.nomj()[:8] + ".%07d   " % i_bloc + ".DISC")
                ptem = AsVR(self.nomj()[:8] + ".%07d   " % i_bloc + ".PTEM")
                assert ordr.lonmax == disc.lonmax
                assert ordr.lonmax == ptem.lonmax
                assert sdu_monotone(ordr.get()) == 1
                assert sdu_monotone(disc.get()) == 1
                sdu_tous_differents(ordr, checker)
                sdu_tous_differents(disc, checker)

    def check_DEPL_VITE_ACCE(self, checker):
        type_calcul, nbmode, nbnoli, nbsauv, nbexcit, nbvint = self.u_dime()

        if type_calcul == "TRAN":
            if self.ORDR.exists:
                assert (
                    self.DEPL.lonmax == nbsauv * nbmode
                    and self.VITE.lonmax == nbsauv * nbmode
                    and self.ACCE.lonmax == nbsauv * nbmode
                )
                # on verifie que les trois objets existent et sont de
                # la bonne longueur
                assert self.DEPL.type == "R" and self.VITE.type == "R" and self.ACCE.type == "R"
                ## on verifie que les valeurs sont reelles
            else:
                for i_bloc, ordr in enumerate(self.ordr, 1):
                    nbsauv = ordr.lonmax
                    depl = AsVR(self.nomj()[:8] + ".%07d   " % i_bloc + ".DEPL")
                    vite = AsVR(self.nomj()[:8] + ".%07d   " % i_bloc + ".VITE")
                    acce = AsVR(self.nomj()[:8] + ".%07d   " % i_bloc + ".ACCE")
                    assert (
                        depl.lonmax == nbsauv * nbmode
                        and vite.lonmax == nbsauv * nbmode
                        and acce.lonmax == nbsauv * nbmode
                    )

        elif type_calcul == "HARM":
            # on verifie qu'au moins un des trois objets existe et qu'il
            # est de type complexe
            assert self.DEPL.exists or self.VITE.exists or self.ACCE.exists
            if self.DEPL.exists:
                assert self.DEPL.lonmax == nbsauv * nbmode and self.DEPL.type == "C"
            if self.VITE.exists:
                assert self.VITE.lonmax == nbsauv * nbmode and self.VITE.type == "C"
            if self.ACCE.exists:
                assert self.ACCE.lonmax == nbsauv * nbmode and self.ACCE.type == "C"

    def check_EXCIT(self, checker):
        type_calcul, nbmode, nbnoli, nbsauv, nbexcit, nbvint = self.u_dime()
        if nbexcit == 0:
            return
        assert self.FACC.lonmax == 2 * nbexcit
        assert self.FDEP.lonmax == 2 * nbexcit
        assert self.FVIT.lonmax == 2 * nbexcit
        # assert self.IPSD.lonmax == nbexcit*neq # JP : neq != nbmode. Que vaut
        # neq ??


class sd_dyna_gene_nl(AsBase):
    # --------------------------------------
    nomj = SDNom(fin=19)

    VIND = AsVI()
    VINT = AsVR()
    INTI = AsVK24()
    TYPE = AsVI()

    def u_dime_nl(self):

        if self.TYPE.lonmax is None:
            return (0, 0, 0)

        nbnoli = self.TYPE.lonmax
        vindex = self.VIND.get()
        nbvint = vindex[-1] - 1

        if self.VINT.exists:
            lonmax = self.VINT.lonmax
        else:
            lonmax = 0
            bloc = AsVR(self.nomj()[:8] + "           .BLOC")
            for i_bloc in range(1, bloc.lonmax + 1):
                vint = AsVR(self.nomj()[:8] + ".%07d" % i_bloc + self.nomj()[16:19] + ".VINT")
                lonmax += vint.lonmax - 1
            lonmax += 1
        nbsaves = lonmax / nbvint
        return nbnoli, nbvint, nbsaves

    def check_NONL(self, checker):
        nbnoli, nbvint, nbsaves = self.u_dime_nl()
        if nbnoli > 0:
            assert self.VIND.lonmax == nbnoli + 1
            assert self.INTI.lonmax == 5 * nbnoli
            assert self.TYPE.lonmax == nbnoli


class sd_dyna_gene(sd_titre, sd_resu_dyna, sd_dyna_gene_common):
    # --------------------------------------
    nomj = SDNom(fin=19)
    sd_nl = Facultatif(sd_dyna_gene_nl(SDNom(nomj=".NL", debut=16, fin=19)))

    # non linearities
    def check_NONL(self, checker):
        desc = self.DESC.get()
        nbnoli = desc[2]
        if nbnoli > 0:
            assert self.sd_nl is not None
