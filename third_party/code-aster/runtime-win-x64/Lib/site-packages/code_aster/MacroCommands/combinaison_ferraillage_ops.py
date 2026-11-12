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

from ..Cata.Syntax import _F
from ..CodeCommands import CALC_FERRAILLAGE, CREA_CHAMP, CREA_RESU
from ..Messages import UTMESS


def combinaison_ferraillage_ops(self, **args):
    """Command to combine results to estimate reinforcement of the structure."""

    resu = args.get("RESULTAT")
    combinaison = args.get("COMBINAISON")
    affe = args.get("AFFE")
    codification = args.get("CODIFICATION")
    meth2D = args.get("METHODE_2D")
    ptheta = args.get("PAS_THETA")
    pepai = args.get("PAS_EPAI")
    psigm = args.get("PAS_SIGM")
    cond109 = args.get("COND_109")
    uc = args.get("UNITE_CONTRAINTE")

    # Retriving from RESULTAT
    modele = resu.getModel()
    maillage = resu.getMesh()
    caraelem = args.get("CARA_ELEM")

    # Counting numbers of load combinations.
    nmb_cas = countCase(combinaison)
    UTMESS("I", "COMBFERR_10", vali=nmb_cas)

    # Build instant list (lst_inst_value of float) and instant index
    # and control about existing or duplicates NUM_CAS and NUME_ORDRE.
    #
    lst_inst_index, lst_inst_value, resu_nom_cas, resu_num_ord, lst_type_combo = lstInst(
        nmb_cas, combinaison, resu
    )

    valk = (
        "-".join([str(i) for i in lst_inst_value]),
        "*".join([str(i) for i in resu_nom_cas]),
        "*".join([str(i) for i in resu_num_ord]),
    )
    UTMESS("I", "COMBFERR_11", valk=valk)

    # Controlling overwriting results
    if "COMB_DIME_ORDRE" in resu_nom_cas:
        UTMESS("A", "COMBFERR_9", valk="COMB_DIME_ORDRE")

    if "COMB_DIME_ACIER" in resu_nom_cas:
        UTMESS("A", "COMBFERR_9", valk="COMB_DIME_ACIER")

    UTMESS("I", "COMBFERR_12", valk="\n    ".join(lst_type_combo))

    meth2D = args.get("METHODE_2D")
    ptheta = args.get("PAS_THETA")
    pepai = args.get("PAS_EPAI")
    psigm = args.get("PAS_SIGM")
    cond109 = args.get("COND_109")
    uc = args.get("UNITE_CONTRAINTE")

    l_info = []
    l_info.append(codification)
    l_info.append(meth2D)
    l_info.append(ptheta)
    l_info.append(pepai)
    l_info.append(psigm)
    l_info.append(cond109)
    l_info.append(uc)

    resu = algo_ferr(resu, affe, lst_inst_index, l_info, lst_type_combo, caraelem)

    # - Build result type EVOL_ELAS from MULTI_ELAS and combo type list in order
    #   to select the right verify. This because CREA_CHAMP doesn't EXTR the
    #   MAXI from multi_elas

    resferr = evolElasFromMulti(nmb_cas, combinaison, lst_inst_value, resu, caraelem)

    # Maximum reinforcement field (elementwise, component by component)
    maxiferr = CREA_CHAMP(
        RESULTAT=resferr,
        NOM_CHAM="FERR_ELEM",
        TYPE_CHAM="ELEM_FER2_R",
        OPERATION="EXTR",
        TYPE_MAXI="MAXI",
        TYPE_RESU="VALE",
        TOUT_ORDRE="OUI",
    )

    # Instant for which maximum reinforcement field is retrieved (elementwise,
    # component by component)
    instferr = CREA_CHAMP(
        RESULTAT=resferr,
        NOM_CHAM="FERR_ELEM",
        TYPE_CHAM="ELEM_FER2_R",
        OPERATION="EXTR",
        TYPE_MAXI="MAXI",
        TYPE_RESU="INST",
        TOUT_ORDRE="OUI",
    )

    resu = CREA_RESU(
        reuse=resu,
        RESULTAT=resu,
        OPERATION="AFFE",
        TYPE_RESU="MULT_ELAS",
        AFFE=(
            _F(NOM_CHAM="FERR_ELEM", NOM_CAS="COMB_DIME_ACIER", CHAM_GD=maxiferr, MODELE=modele),
        ),
    )

    resu = CREA_RESU(
        reuse=resu,
        RESULTAT=resu,
        OPERATION="AFFE",
        TYPE_RESU="MULT_ELAS",
        AFFE=(
            _F(NOM_CHAM="FERR_ELEM", NOM_CAS="COMB_DIME_ORDRE", CHAM_GD=instferr, MODELE=modele),
        ),
    )

    nc = resu.getAccessParameters()["NOM_CAS"]
    UTMESS("I", "COMBFERR_13", valk="\n    ".join(nc))

    return resu


def algo_ferr(resferr, affe, lst_nume_ordre, l_info, type_combo, cara):
    #   From physical_quantities.py :
    #   FER2_R   = PhysicalQuantity(type='R',
    #   components=(
    #          'DNSXI'    : Ferraillage longitudinal inférieur suivant X (2D)
    #          'DNSXS'    : Ferraillage longitudinal supérieur suivant X (2D)
    #          'DNSYI'    : Ferraillage longitudinal inférieur suivant Y (2D)
    #          'DNSYS'    : Ferraillage longitudinal supérieur suivant Y (2D)
    #          'DNSXT'    : Ferraillage transversal suivant X            (2D)
    #          'DNSYT'    : Ferraillage transversal suivant Y            (2D)
    #          'AYI'      : Ferraillage longitudinal inférieur suivant Y (1D)
    #          'AYS'      : Ferraillage longitudinal supérieur suivant Y (1D)
    #          'AZI'      : Ferraillage longitudinal inférieur suivant Z (1D)
    #          'AZS'      : Ferraillage longitudinal supérieur suivant Z (1D)
    #          'AST'      : Ferraillage transversal                      (1D)
    #          'ATOT'     : Ferraillage longitudinal total               (1D)
    #          'DNSVOL'   : Densité volumique de ferraillage
    #          'CONSTRUC' : Indice de constructibilité
    # ),)

    for idx, nume_ordre in enumerate(lst_nume_ordre):
        dic_type_comb = {}
        if type_combo[idx] == "ELS_CARACTERISTIQUE":
            dic_type_comb["TYPE_COMB"] = "ELS"
        elif type_combo[idx] == "ELS_QUASIPERMANENT":
            dic_type_comb["TYPE_COMB"] = "ELS_QP"
        else:
            dic_type_comb["TYPE_COMB"] = "ELU"

        # l_info.append(codification)
        # l_info.append(meth2D)
        # l_info.append(ptheta)
        # l_info.append(pepai)
        # l_info.append(psigm)
        # l_info.append(cond109)
        # l_info.append(uc)

        dic_type_comb["CODIFICATION"] = l_info[0]
        dic_type_comb["METHODE_2D"] = l_info[1]
        dic_type_comb["PAS_THETA"] = l_info[2]
        dic_type_comb["PAS_EPAI"] = l_info[3]
        dic_type_comb["PAS_SIGM"] = l_info[4]
        dic_type_comb["COND_109"] = l_info[5]
        dic_type_comb["UNITE_CONTRAINTE"] = l_info[6]

        lst_tmp_affe = []

        for i_affe in affe:
            dict_i_affe = i_affe.List_F()[0]
            i_affe_for_cf = dict_i_affe.copy()

            if type_combo[idx] == "ELU_FONDAMENTAL":
                i_affe_for_cf.update({"GAMMA_S": i_affe_for_cf["GAMMA_S_FOND"]})
                i_affe_for_cf.update({"GAMMA_C": i_affe_for_cf["GAMMA_C_FOND"]})
            elif type_combo[idx] == "ELU_ACCIDENTEL":
                i_affe_for_cf.update({"GAMMA_S": i_affe_for_cf["GAMMA_S_ACCI"]})
                i_affe_for_cf.update({"GAMMA_C": i_affe_for_cf["GAMMA_C_ACCI"]})

            # adjusting affe for calc_ferraillage
            i_affe_for_cf.pop("GAMMA_C_FOND")
            i_affe_for_cf.pop("GAMMA_S_FOND")
            i_affe_for_cf.pop("GAMMA_C_ACCI")
            i_affe_for_cf.pop("GAMMA_S_ACCI")

            lst_tmp_affe.append(_F(**i_affe_for_cf))

        dic_type_comb["AFFE"] = tuple(lst_tmp_affe)

        resferr = CALC_FERRAILLAGE(
            reuse=resferr, RESULTAT=resferr, CARA_ELEM=cara, NUME_ORDRE=nume_ordre, **dic_type_comb
        )

    return resferr


# Counting numbers of load combinations.
def countCase(comb):
    nmb_cas = 0
    for idx_i_combo, i_combo in enumerate(comb):
        # Case number from MULTI_ELAS
        lst_nomcas = i_combo.get("NOM_CAS")
        lst_numord = i_combo.get("NUME_ORDRE")
        if lst_nomcas is None:
            nmb_cas = nmb_cas + len(lst_numord)  # combinations number
        else:
            nmb_cas = nmb_cas + len(lst_nomcas)
    return nmb_cas


def lstInst(ncas, comb, resultat):
    lst_inst_value = [None] * ncas  # list of float value as time for AFFE
    lst_inst_index = [None] * ncas  # list of int value as index
    type_combo = [None] * ncas  # list of string as type of combo

    # Recuperer les numéros d'ordre et les noms des cas de chargement associés
    resu_nume_ordre = resultat.getAccessParameters()["NUME_ORDRE"]
    resu_nom_cas = resultat.getAccessParameters()["NOM_CAS"]

    # Elimination du vide dans [resu_nom_cas]
    for idx, val in enumerate(resu_nom_cas):
        resu_nom_cas[idx] = val.strip()

    idx_shift = 0
    for idx_i_combo, i_combo in enumerate(comb):
        # Case number from MULTI_ELAS
        lst_nomcas = i_combo.get("NOM_CAS")
        lst_numord = i_combo.get("NUME_ORDRE")
        if lst_nomcas is None:
            lst_combo = lst_numord
            key_name_combo = "NUME_ORDRE"
        else:
            lst_combo = lst_nomcas
            key_name_combo = "NOM_CAS"

        for idx_combo, val_combo in enumerate(lst_combo):
            # type combo list couple with instant
            type_combo[idx_shift] = i_combo.get("TYPE")

            if key_name_combo == "NUME_ORDRE":
                inst = val_combo
                if inst not in resu_nume_ordre:
                    # le cas de charge renseigné dans COMBINAISON_FERRAILLAGE n'a pas un équivalent dans RESULTAT (issu de MACRO_ELAS_MULT)
                    UTMESS("F", "COMBFERR_7")
                if inst in lst_inst_index:
                    # le cas de charge renseigné dans COMBINAISON_FERRAILLAGE a déjà été renseigné
                    UTMESS("F", "COMBFERR_4")
            else:
                if val_combo not in resu_nom_cas:
                    UTMESS("F", "COMBFERR_6")
                # Index needs to be [inst_index + 1] because MUME_ORDRE is index + 1
                inst = resu_nom_cas.index(val_combo) + 1
                if inst in lst_inst_index:
                    UTMESS("F", "COMBFERR_5")

            lst_inst_index[idx_shift] = inst
            lst_inst_value[idx_shift] = float(inst)
            idx_shift = idx_shift + 1

    return lst_inst_index, lst_inst_value, resu_nom_cas, resu_nume_ordre, type_combo


# Build result type EVOL_ELAS from MULTI_ELAS
def evolElasFromMulti(ncas, comb, lst_inst_value, resu, cara):
    modele = resu.getModel()
    caraelem = cara

    __EFGE = [None] * ncas
    lst_AFFE_EFGE = [None] * ncas

    idx_shift = 0
    for idx_i_combo, i_combo in enumerate(comb):
        # Case number from MULTI_ELAS
        lst_nomcas = i_combo.get("NOM_CAS")
        lst_numord = i_combo.get("NUME_ORDRE")
        if lst_nomcas is None:
            lst_combo = lst_numord  # list with combinations
            key_name_combo = "NUME_ORDRE"
        else:
            lst_combo = lst_nomcas
            key_name_combo = "NOM_CAS"

        for idx_combo, val_combo in enumerate(lst_combo):
            dic_idx_combo = {key_name_combo: val_combo}

            __EFGE[idx_shift] = CREA_CHAMP(
                OPERATION="EXTR",
                RESULTAT=resu,
                TYPE_CHAM="ELEM_FER2_R",
                NOM_CHAM="FERR_ELEM",
                **dic_idx_combo,
            )

            lst_AFFE_EFGE[idx_shift] = _F(
                NOM_CHAM="FERR_ELEM",
                INST=lst_inst_value[idx_shift],
                CHAM_GD=__EFGE[idx_shift],
                MODELE=modele,
                CARA_ELEM=caraelem,
            )

            idx_shift = idx_shift + 1

    resferr = CREA_RESU(OPERATION="AFFE", TYPE_RESU="EVOL_ELAS", AFFE=lst_AFFE_EFGE)

    return resferr
