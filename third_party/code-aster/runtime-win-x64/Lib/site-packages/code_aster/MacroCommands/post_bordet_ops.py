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

import numpy as NP

from ..Cata.Syntax import _F
from ..CodeCommands import CALC_CHAM_ELEM, CALC_CHAMP, CALC_TABLE, CREA_CHAMP, CREA_TABLE, FORMULE
from ..Objects import Function as fonction_sdaster
from ..Objects import Function2D as nappe_sdaster
from ..Messages import UTMESS


def post_bordet_ops(
    self,
    RESULTAT,
    PARAM,
    TEMP,
    TOUT=None,
    GROUP_MA=None,
    INST=None,
    PRECISION=None,
    CRITERE=None,
    NUME_ORDRE=None,
    PROBA_NUCL=None,
    COEF_MULT=None,
    **args,
):
    """Corps de POST_BORDET"""

    # On importe les definitions des commandes a utiliser dans la macro
    #
    # Recuperation du modele a partir du resultat
    model = RESULTAT.getModel()
    n_modele = model.getName()
    if model is None or n_modele == "#PLUSIEURS":
        UTMESS("F", "RUPTURE1_58")

    # Dimension du modele
    ndim = model.getMesh().getDimension()

    if ndim == 23:
        UTMESS("F", "RUPTURE1_57")

    #
    # Definition des formules pour le calcul de sigy plus tard
    #

    __MAXI = FORMULE(NOM_PARA=("T1"), VALE="""max(T1,0.)""")

    #
    # Calcul des grandeurs dont on a besoin : contrainte principale, def plastique et volume du pt de gauss
    #

    # Volume point de gauss
    __VOL_PG = CALC_CHAM_ELEM(MODELE=model, TOUT="OUI", OPTION="COOR_ELGA")
    if GROUP_MA:
        GROUP_MA = list(GROUP_MA)
        vol = NP.array(__VOL_PG.getValuesWithDescription("W", GROUP_MA)[0])
    elif TOUT:
        vol = NP.array(__VOL_PG.getValuesWithDescription("W")[0])

    # contrainte principale max et deformation plastique
    __RESU = CALC_CHAMP(RESULTAT=RESULTAT, CRITERES="SIEQ_ELGA", DEFORMATION="EPSP_ELGA")

    # Recuperation de la liste des instants et des ordres de calcul
    list_ordre = __RESU.getAccessParameters()["NUME_ORDRE"]
    list_inst = __RESU.getAccessParameters()["INST"]

    #
    # On va travailler en ordre ; si l'utilisateur entre un instant, on va le
    # transformer en ordre
    entree_instant = None
    if INST:
        if CRITERE == "ABSOLU":
            prec = PRECISION
        elif CRITERE == "RELATIF":
            prec = PRECISION * INST
        entree_instant = True
        n = 0
        trouv = None
        while n < len(list_inst) and not trouv:
            if (list_inst[n] + prec >= INST) and (list_inst[n] - prec <= INST):
                instant = list_inst[n]
                trouv = True
            n = n + 1
        if not trouv:
            UTMESS("F", "RUPTURE1_53", valr=INST, valk="utilise pour le calcul de Bordet")
    if entree_instant:
        index_ordre = list_inst.index(instant)
        nume_ordre = list_ordre[index_ordre]
    elif NUME_ORDRE:
        nume_ordre = NUME_ORDRE
        if nume_ordre not in list_ordre:
            dict_args = dict(vali=int(nume_ordre), valk="utilise pour le calcul de Bordet")
            UTMESS("F", "RUPTURE0_51", **dict_args)
    #
    # Pour Bordet, il nous faut les champs a tous les instants jusqu'a
    # l'instant considere
    EP = [
        [None for j in range(6)] for i in range(nume_ordre + 1)
    ]  # tenseur des deformations plastiques
    EPEQ = [
        [None for j in range(0)] for i in range(nume_ordre + 1)
    ]  # deformation plastique equivalente
    EPEQM = [0.0] * (nume_ordre + 1)
    # deformation plastique equivalente a l'instant precedent
    PRIN = [None] * (nume_ordre + 1)
    EQ_BAR = [None] * (nume_ordre + 1)
    EQ_PT = [None] * (nume_ordre + 1)
    EQ_PT2 = [None] * (nume_ordre + 1)
    PR_BAR = [None] * (nume_ordre + 1)
    DEP = [None] * (nume_ordre + 1)
    BORDTI = 0.0  # valeur sans l'exposant final, sommee sur les instants
    BORDTT = [0.0] * (nume_ordre + 1)
    # valeur avec l'exposant, que l'on stocke dans la table a
    # chaque instant
    PROBA = [0.0] * (nume_ordre + 1)  # Probabilite de rupture par clivage

    # LISTE DES PARAMETRES
    sig0 = PARAM["SEUIL_REFE"]
    sigth = PARAM["SIG_CRIT"]
    sigref = PARAM["SIGM_REFE"]
    m = PARAM["M"]
    V0 = PARAM["VOLU_REFE"]
    if PROBA_NUCL == "OUI":
        ep0 = PARAM["DEF_PLAS_REFE"]
    elif PROBA_NUCL == "NON":
        ep0 = 0
    c_mult = COEF_MULT
    #
    # On va constuire des champs a chaque instant
    #
    if list_ordre[0] == 0:
        fin_ordre = nume_ordre + 1
    elif list_ordre[0] != 0:
        fin_ordre = nume_ordre

    #
    # Temperature a extraire : fonction du temps ou constante
    #
    if TEMP.Parametres()["NOM_PARA"] not in ["INST", "TOUTPARA"]:
        UTMESS("F", "RUPTURE0_3")

    for ordre in range(list_ordre[0], fin_ordre):
        tempe = TEMP(list_inst[ordre])

        def fseuil(epsi):
            return PARAM["SEUIL_CALC"](epsi, tempe)

        # self.update_const_context({'fseuil': fseuil})
        __NPY = FORMULE(NOM_PARA=("EPSI"), VALE="""fseuil(EPSI)""", fseuil=fseuil)

        #
        # On met ces grandeurs dans des champs specifiques
        #
        __S_TOT = CREA_CHAMP(
            TYPE_CHAM="ELGA_SIEF_R",
            RESULTAT=__RESU,
            OPERATION="EXTR",
            NUME_ORDRE=ordre,
            NOM_CHAM="SIEQ_ELGA",
        )

        __EPSP = CREA_CHAMP(
            TYPE_CHAM="ELGA_EPSI_R",
            RESULTAT=__RESU,
            OPERATION="EXTR",
            NUME_ORDRE=ordre,
            NOM_CHAM="EPSP_ELGA",
        )

        # On recupere la valeur des champs au niveau des groupes qui nous
        # interessent
        if GROUP_MA:
            PRIN[ordre] = NP.array(__S_TOT.getValuesWithDescription("PRIN_3", GROUP_MA)[0])

            # Pour la deformation plastique, on construit de quoi calculer sa
            # norme de VMises
            EP[ordre][0] = NP.array(__EPSP.getValuesWithDescription("EPXX", GROUP_MA)[0])
            EP[ordre][1] = NP.array(__EPSP.getValuesWithDescription("EPYY", GROUP_MA)[0])
            EP[ordre][2] = NP.array(__EPSP.getValuesWithDescription("EPZZ", GROUP_MA)[0])
            EP[ordre][3] = NP.array(__EPSP.getValuesWithDescription("EPXY", GROUP_MA)[0])
            if ndim == 3:
                EP[ordre][4] = NP.array(__EPSP[ordre].getValuesWithDescription("EPXZ", GROUP_MA)[0])
                EP[ordre][5] = NP.array(__EPSP[ordre].getValuesWithDescription("EPYZ", GROUP_MA)[0])

        elif TOUT:
            PRIN[ordre] = NP.array(__S_TOT.getValuesWithDescription("PRIN_3")[0])
            EP[ordre][0] = NP.array(__EPSP.getValuesWithDescription("EPXX")[0])
            EP[ordre][1] = NP.array(__EPSP.getValuesWithDescription("EPYY")[0])
            EP[ordre][2] = NP.array(__EPSP.getValuesWithDescription("EPZZ")[0])
            EP[ordre][3] = NP.array(__EPSP.getValuesWithDescription("EPXY")[0])
            if ndim == 3:
                EP[ordre][4] = NP.array(__EPSP.getValuesWithDescription("EPXZ")[0])
                EP[ordre][5] = NP.array(__EPSP.getValuesWithDescription("EPYZ")[0])

        nval = len(PRIN[ordre])
        nval2 = len(EP[ordre][0])
        if nval2 != nval:
            UTMESS("F", "RUPTURE1_54")

        if ndim == 3:
            EPEQ[ordre] = NP.sqrt(
                2.0
                / 3.0
                * (
                    EP[ordre][0] ** 2
                    + EP[ordre][1] ** 2
                    + EP[ordre][2] ** 2
                    + 2.0 * EP[ordre][3] ** 2
                    + 2.0 * EP[ordre][4] ** 2
                    + 2.0 * EP[ordre][5] ** 2
                )
            )
        elif ndim == 2:
            EPEQ[ordre] = NP.sqrt(
                2.0
                / 3.0
                * (
                    EP[ordre][0] ** 2
                    + EP[ordre][1] ** 2
                    + EP[ordre][2] ** 2
                    + 2.0 * EP[ordre][3] ** 2
                )
            )

        # Construction des champs barre et des champs de vitesse
        EQ_PT2[list_ordre[0]] = NP.zeros([nval])
        EPEQ[ordre] = NP.array(EPEQ[ordre])

        if ordre != list_ordre[0]:
            dt = list_inst[ordre] - list_inst[ordre - 1]
            if dt == 0:
                UTMESS("F", "RUPTURE1_55")
            EPEQM[ordre] = EPEQ[ordre - 1]
            EQ_BAR[ordre] = (EPEQ[ordre] + EPEQ[ordre - 1]) / 2.0
            EQ_PT2[ordre] = (EPEQ[ordre] - EPEQ[ordre - 1]) / (2 * dt)
            EQ_PT[ordre] = EQ_PT2[ordre - 1] + EQ_PT2[ordre]
            DEP[ordre] = EPEQ[ordre] - EPEQ[ordre - 1]
            PR_BAR[ordre] = (PRIN[ordre] + PRIN[ordre - 1]) / 2.0

            if type(PARAM["SEUIL_CALC"]) == fonction_sdaster:
                sigy = PARAM["SEUIL_CALC"](tempe)
            elif type(PARAM["SEUIL_CALC"]) == nappe_sdaster:
                EQ_PT[ordre] = list(EQ_PT[ordre])
                __TAB = CREA_TABLE(LISTE=(_F(PARA="EPSI", LISTE_R=EQ_PT[ordre]),))
                __TAB = CALC_TABLE(
                    TABLE=__TAB,
                    reuse=__TAB,
                    ACTION=_F(OPERATION="OPER", FORMULE=__NPY, NOM_PARA="TSIGY"),
                )
                sigy = __TAB.EXTR_TABLE().values()["TSIGY"]
                sigy = NP.array(sigy)

            T1 = sigy / sig0 * (PR_BAR[ordre] ** m - sigth**m)
            T1 = list(T1)
            __TABT1 = CREA_TABLE(LISTE=(_F(PARA="T1", LISTE_R=T1),))
            __TABT1 = CALC_TABLE(
                TABLE=__TABT1,
                reuse=__TABT1,
                ACTION=_F(OPERATION="OPER", FORMULE=__MAXI, NOM_PARA="T1BIS"),
            )

            T1 = __TABT1.EXTR_TABLE().values()["T1BIS"]
            T1 = NP.array(T1)
            if PROBA_NUCL == "OUI":
                T2 = NP.exp(-sigy / sig0 * EQ_BAR[ordre] / ep0)
            elif PROBA_NUCL == "NON":
                T2 = 1.0
            T3 = DEP[ordre]
            T4 = vol / V0
            BORDTI = BORDTI + NP.cumsum(T1 * T2 * T3 * T4)[-1]

        BORDTT[ordre] = (c_mult * BORDTI) ** (1 / m)

        if sigref(tempe) != 0.0:
            PROBA[ordre] = 1 - NP.exp(-((BORDTT[ordre] / sigref(tempe)) ** m))
        elif sigref(tempe) == 0.0:
            UTMESS("F", "RUPTURE1_56", valr=list_inst[ordre])

    tabout = CREA_TABLE(
        LISTE=(
            _F(PARA="INST", LISTE_R=list_inst[0 : nume_ordre + 1]),
            _F(PARA="SIG_BORDET", LISTE_R=BORDTT),
            _F(PARA="PROBA_BORDET", LISTE_R=PROBA),
        )
    )
    return tabout
