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

from numpy import array

from ...Messages import UTMESS

from ...Cata.Syntax import _F
from ...CodeCommands import (
    ASSE_VECTEUR,
    CALC_VECT_ELEM,
    COMB_MATR_ASSE,
    CREA_CHAMP,
    CREA_RESU,
    DEFI_BASE_MODALE,
    DYNA_VIBRA,
    MODE_STATIQUE,
    NUME_DDL_GENE,
    PROJ_MATR_BASE,
    PROJ_VECT_BASE,
    REST_GENE_PHYS,
)


def dyna_visco_harm(
    self,
    EXCIT,
    list_FREQ,
    modes,
    MATER_ELAS_FO,
    __asseKg,
    __asseKgr,
    __asseMg,
    __listKv,
    e0,
    eta0,
    __num,
    **args,
):
    """
    Macro-command DYNA_VISCO,
    function to compute the harmonic response of the structure
    """

    if args["NOM_CHAM"] is not None:
        NOM_CHAM = args["NOM_CHAM"]
    if isinstance(NOM_CHAM, str):
        NOM_CHAM = (NOM_CHAM,)  # convert the string into a tuple

    # get the characteristics of the excitation
    l_force_nodale = False  # logical which indicates the presence of nodal forces in the excitation
    charge = []
    for l_char in EXCIT:
        for l_char2 in l_char["CHARGE"]:
            charge.append(l_char2)

    mc_force_nodale = []
    for i in range(0, len(charge)):
        if charge[i].hasLoadField("FORNO"):
            # if no nodal force is found, one does not achieve the following treatment
            l_force_nodale = True
            # if no nodal force is found, one does not achieve the following treatment
            forno = charge[i].getMechanicalLoadDescription().getConstantLoadField("FORNO")
            no_force = charge[i].getFiniteElementDescriptor().getVirtualCellsDescriptor()
            # take imposed nodal force having this shape: (node_number, 1)
            no_force = [x for x in no_force if len(x) == 2 and x[1] == 1]

            model = __num.getModel()
            maillage = None
            if model is not None:
                maillage = model.getMesh()
            else:
                raise NameError("No mesh")

            direction = array(
                [array(forno.getValues(i).getValues()).nonzero()[0] for i in range(forno.size())]
            )

            # array which contains, for each node having an imposed force, the list of the imposed directions
            # (rq : "/12" because each node has 12 DoF)
            # the values are 0 if FX imposed, 1 if FY, and 2 if FZ
            #                3 if MX imposed, 4 if MY, and 5 if MZ
            ddl_phys = [None] * len(no_force)
            for i_nf in range(0, len(no_force)):
                ddl_phys[i_nf] = []
                for j in range(0, len(direction[i_nf])):
                    if direction[i_nf][j] == 0:
                        ddl_phys[i_nf].append("DX")
                    elif direction[i_nf][j] == 1:
                        ddl_phys[i_nf].append("DY")
                    elif direction[i_nf][j] == 2:
                        ddl_phys[i_nf].append("DZ")
                    if direction[i_nf][j] == 3:
                        ddl_phys[i_nf].append("DRX")
                    elif direction[i_nf][j] == 4:
                        ddl_phys[i_nf].append("DRY")
                    elif direction[i_nf][j] == 5:
                        ddl_phys[i_nf].append("DRZ")

            for i in range(len(no_force)):
                mc_composante = {}
                mc_composante["AVEC_CMP"] = tuple(ddl_phys[i])

                mc_force_nodale.append(_F(NOEUD=(str(no_force[i][0])), **mc_composante))

    if not l_force_nodale:
        UTMESS("F", "DYNAVISCO_8")

    __modstat = MODE_STATIQUE(MATR_RIGI=__asseKgr, FORCE_NODALE=mc_force_nodale)

    #################################################################################################

    # PROJECTION OF THE MATRICES K AND M ON A BASE MADE WITH THE REAL EIGENMODES AND THE STATIC MODES

    __modrs = DEFI_BASE_MODALE(DIAG_MASS=_F(MODE_MECA=modes, MODE_STAT=__modstat))

    __ddlplein = NUME_DDL_GENE(BASE=__modrs, STOCKAGE="PLEIN")

    __Mgproj = PROJ_MATR_BASE(BASE=__modrs, NUME_DDL_GENE=__ddlplein, MATR_ASSE=__asseMg)

    __Kgproj = PROJ_MATR_BASE(BASE=__modrs, NUME_DDL_GENE=__ddlplein, MATR_ASSE=__asseKg)

    # ASSEMBLY AND PROJECTION OF THE EXCITATION

    __felem = CALC_VECT_ELEM(OPTION="CHAR_MECA", CHARGE=charge)

    __assef = ASSE_VECTEUR(VECT_ELEM=__felem, NUME_DDL=__num)

    __lfor = PROJ_VECT_BASE(
        BASE=__modrs, NUME_DDL_GENE=__ddlplein, VECT_ASSE=__assef, TYPE_VECT="FORC"
    )

    # PROJECTION OF THE STIFFNESS MATRICE ISOLATED FOR EACH VISCOELASTIC PART
    __lKv = {}
    ny = 0
    for y in MATER_ELAS_FO:
        __lKv[ny] = PROJ_MATR_BASE(BASE=__modrs, NUME_DDL_GENE=__ddlplein, MATR_ASSE=__listKv[ny])
        ny = ny + 1

    ##############################################################
    # HARMONIC RESPONSE COMPUTATION
    ##############################################################

    # compute the response of the projected problem for f=fmin
    __dyngene = (
        DYNA_VIBRA(
            TYPE_CALCUL="HARM",
            BASE_CALCUL="GENE",
            MATR_MASS=__Mgproj,
            MATR_RIGI=__Kgproj,
            FREQ=list_FREQ[0],
            EXCIT=_F(VECT_ASSE_GENE=__lfor, COEF_MULT=1),
        ),
    )

    dyna_harm = REST_GENE_PHYS(RESU_GENE=__dyngene, MODE_MECA=__modrs, NOM_CHAM=NOM_CHAM)

    # compute the response of the projected problem for f>fmin
    for num_freq in range(1, len(list_FREQ)):
        __Kwproj = __Kgproj
        ny = 0
        for y in MATER_ELAS_FO:
            e = y["E"](list_FREQ[num_freq])
            eta = y["AMOR_HYST"](list_FREQ[num_freq])

            __Kwproj = COMB_MATR_ASSE(
                COMB_C=(
                    _F(MATR_ASSE=__Kwproj, COEF_R=1.0),
                    _F(
                        MATR_ASSE=__lKv[ny],
                        COEF_C=("RI", e / e0[ny] - 1, eta * e / e0[ny] - eta0[ny]),
                    ),
                )
            )

            ny = ny + 1

        __dyngene = (
            DYNA_VIBRA(
                TYPE_CALCUL="HARM",
                BASE_CALCUL="GENE",
                MATR_MASS=__Mgproj,
                MATR_RIGI=__Kwproj,
                FREQ=list_FREQ[num_freq],
                EXCIT=_F(VECT_ASSE_GENE=__lfor, COEF_MULT=1.0),
            ),
        )

        __dynphys = REST_GENE_PHYS(
            RESU_GENE=__dyngene, MODE_MECA=__modrs, NUME_DDL=__num, NOM_CHAM=NOM_CHAM
        )

        for champ in NOM_CHAM:
            __resveu = CREA_CHAMP(
                OPERATION="EXTR",
                NOM_CHAM=champ,
                TYPE_CHAM="NOEU_DEPL_C",
                RESULTAT=__dynphys,
                NUME_ORDRE=1,
            )

            dyna_harm = CREA_RESU(
                reuse=dyna_harm,
                RESULTAT=dyna_harm,
                OPERATION="AFFE",
                TYPE_RESU="DYNA_HARMO",
                AFFE=_F(NOM_CHAM=champ, CHAM_GD=__resveu, FREQ=list_FREQ[num_freq]),
            )

    return dyna_harm
