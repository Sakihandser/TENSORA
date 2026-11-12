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

# imports
from ..Cata.Syntax import _F

# commandes utilisees dans la macro
from ..CodeCommands import CREA_CHAMP, CREA_RESU


def calc_thermeca_mult_ops(self, TEMP_FIN, TEMP_INIT, RESU_MECA_UNIT, RESU_SUPL_THER, **args):
    # debut macro

    if RESU_SUPL_THER == "OUI":
        RESU_THER_UNIT = args["RESU_THER_UNIT"]
        # instants et numero d'ordre de calcul pour la thermique
        list_instant = RESU_THER_UNIT.getAccessParameters()["INST"]
        nbinst = len(list_instant)
        lnume_ordre = RESU_THER_UNIT.getAccessParameters()["NUME_ORDRE"]
        final = [None] * nbinst
        arguments_affe = ()
        for i in range(nbinst):
            inst = list_instant[i]
            nume_ordre = lnume_ordre[i]

            # Modele du resultat thermique unitaire a ce numero d ordre
            modele_ther = RESU_THER_UNIT.getModel(nume_ordre)
            # extraction champ materiau a ce numero d ordre dans le resu_meca_unit
            cham_mater_ther = RESU_THER_UNIT.getMaterialField(nume_ordre)

            cst = CREA_CHAMP(
                OPERATION="AFFE",
                MODELE=modele_ther,
                AFFE=_F(TOUT="OUI", NOM_CMP="TEMP", VALE=TEMP_INIT),
                TYPE_CHAM="NOEU_TEMP_R",
            )

            chamuthe = CREA_CHAMP(
                NOM_CHAM="TEMP",
                OPERATION="EXTR",
                RESULTAT=RESU_THER_UNIT,
                INST=inst,
                TYPE_CHAM="NOEU_TEMP_R",
            )

            pourmul = CREA_CHAMP(
                OPERATION="ASSE",
                MODELE=modele_ther,
                TYPE_CHAM="NOEU_TEMP_R",
                ASSE=(
                    _F(CHAM_GD=chamuthe, COEF_R=1.0, TOUT="OUI", CUMUL="OUI"),
                    _F(CHAM_GD=cst, COEF_R=-1.0, TOUT="OUI", CUMUL="OUI"),
                ),
            )

            chamTmul = CREA_CHAMP(
                ASSE=_F(CHAM_GD=pourmul, COEF_R=TEMP_FIN, TOUT="OUI"),
                MODELE=modele_ther,
                OPERATION="ASSE",
                TYPE_CHAM="NOEU_TEMP_R",
            )

            final[i] = CREA_CHAMP(
                OPERATION="ASSE",
                MODELE=modele_ther,
                TYPE_CHAM="NOEU_TEMP_R",
                ASSE=(
                    _F(CHAM_GD=chamTmul, COEF_R=1.0, TOUT="OUI", CUMUL="OUI"),
                    _F(CHAM_GD=cst, COEF_R=1.0, TOUT="OUI", CUMUL="OUI"),
                ),
            )

            arguments_affe += (
                _F(
                    NOM_CHAM="TEMP",
                    CHAM_GD=final[i],
                    CHAM_MATER=cham_mater_ther,
                    INST=(inst,),
                    MODELE=modele_ther,
                ),
            )

        resTmult = CREA_RESU(AFFE=arguments_affe, OPERATION="AFFE", TYPE_RESU="EVOL_THER")

        RESU_THER = args.get("RESU_THER")
        self.register_result(resTmult, RESU_THER)

    ############## Calcul du resultat mecanique ########################################
    # liste des instants et numeros d'ordre de calcul
    list_instant = RESU_MECA_UNIT.getAccessParameters()["INST"]
    nbinst = len(list_instant)
    lnume_ordre = RESU_MECA_UNIT.getAccessParameters()["NUME_ORDRE"]

    # recuperation des champs en entree - on recupere tous les champs
    # mais la macro n'agit que sur DEPL, SIEF_ELGA et TEMP
    nomschamps = []
    for field_name in RESU_MECA_UNIT.getFieldsNames():
        if RESU_MECA_UNIT.getIndexesForFieldName(field_name):
            nomschamps.append(field_name)

    nbchamps = len(nomschamps)

    # Initialisation listes des champs dans le resultat unitaire et dans le resultat final
    chamu = [[None] * nbinst] * nbchamps
    chamm = [[None] * nbinst] * nbchamps

    # dictionnaire donnant l'equivalence entre le nom et le type d'un champ
    dico_equivalence_NOM_TYPE_CHAM = {
        "SIGM_NOEU": "NOEU_SIEF_R",
        "SIPM_ELNO": "ELNO_SIEF_R",
        "HYDR_ELNO": "ELNO_HYDR_R",
        "SIGM_ELGA": "ELGA_SIEF_R",
        "EPME_ELNO": "ELNO_EPSI_R",
        "MODE_FLAMB": "NOEU_DEPL_R",
        "EPSG_ELGA": "ELGA_EPSI_R",
        "QIRE_NOEU": "NOEU_ERRE_R",
        "EPMQ_ELGA": "ELGA_EPSI_R",
        "DEPL": "NOEU_DEPL_R",
        "INTE_NOEU": "NOEU_INTE_R",
        "DEGE_ELNO": "ELNO_EPSI_R",
        "EPSA_ELNO": "ELNO_EPSI_R",
        "EPVC_NOEU": "NOEU_EPSI_R",
        "SIPO_ELNO": "ELNO_SIEF_R",
        "DISS_ELGA": "ELGA_DISS_R",
        "SIEQ_ELNO": "ELNO_SIEF_R",
        "EPFD_NOEU": "NOEU_EPSI_R",
        "ERTH_NOEU": "NOEU_ERRE_R",
        "EPSP_ELGA": "ELGA_EPSI_R",
        "PDIL_ELGA": "ELGA_PDIL_R",
        "META_ELNO": "ELNO_VARI_R",
        "EPFP_ELNO": "ELNO_EPSI_R",
        "EPME_ELGA": "ELGA_EPSI_R",
        "SIGM_ELNO": "ELNO_SIEF_R",
        "VARC_ELGA": "ELGA_VARC_R",
        "HYDR_NOEU": "NOEU_HYDR_R",
        "DEGE_ELGA": "ELGA_EPSI_R",
        "EPSP_NOEU": "NOEU_EPSI_R",
        "EPMG_ELNO": "ELNO_EPSI_R",
        "SIEF_ELGA": "ELGA_SIEF_R",
        "ERZ2_ELEM": "ELEM_ERRE_R",
        "DURT_ELNO": "ELNO_DURT_R",
        "ENDO_ELNO": "NOEU_SIEF_R",
        "DISS_ELNO": "ELNO_DISS_R",
        "EPFP_NOEU": "NOEU_EPSI_R",
        "EPVC_ELNO": "ELNO_EPSI_R",
        "DEPL_ABSOLU": "NOEU_DEPL_R",
        "EFGE_ELNO": "ELNO_SIEF_R",
        "GEOMETRIE": "NOEU_GEOM_R",
        "TEMP": "NOEU_TEMP_R",
        "CONT_NOEU": "NOEU_INFC_R",
        "EPSI_NOEU": "NOEU_EPSI_R",
        "DISS_ELEM": "ELEM_DISS_R",
        "EFGE_ELGA": "ELGA_SIEF_R",
        "EPVC_ELGA": "ELGA_EPSI_R",
        "MODE_STAB": "NOEU_DEPL_R",
        "REAC_NODA": "NOEU_DEPL_R",
        "ETHE_ELEM": "ELEM_ENER_R",
        "SIEF_NOEU": "NOEU_SIEF_R",
        "SIEF_ELNO": "ELNO_SIEF_R",
        "DERA_NOEU": "NOEU_DERA_R",
        "DURT_NOEU": "NOEU_DURT_R",
        "FLUX_NOEU": "NOEU_FLUX_R",
        "ERME_NOEU": "NOEU_ERRE_R",
        "SIEQ_ELGA": "ELGA_SIEF_R",
        "ERTH_ELEM": "ELEM_ERRE_R",
        "QIZ2_ELEM": "ELEM_ERRE_R",
        "FORC_LIAI": "NOEU_DEPL_R",
        "PRME_ELNO": "ELNO_PRME_R",
        "DEGE_NOEU": "NOEU_EPSI_R",
        "EPEQ_NOEU": "NOEU_EPSI_R",
        "EPMQ_NOEU": "NOEU_EPSI_R",
        "SING_ELEM": "ELEM_SING_R",
        "PTOT": "NOEU_DEPL_R",
        "UTXX_NOEU": "RIEN",
        "EPOT_ELEM": "ELEM_ENER_R",
        "FORC_EXTE": "NOEU_DEPL_R",
        "ERZ1_ELEM": "ELEM_ERRE_R",
        "PRAC_ELNO": "ELNO_PRAC_R",
        "ETOT_ELGA": "ELGA_ENER_R",
        "SIZ1_NOEU": "NOEU_SIEF_R",
        "ERME_ELNO": "ELNO_ERRE_R",
        "NEUT": "NOEU_NEUT_R",
        "ENEL_ELGA": "ELGA_ENER_R",
        "EPEQ_ELGA": "ELGA_EPSI_R",
        "ERTH_ELNO": "ELNO_ERRE_R",
        "FLUX_ELGA": "ELGA_FLUX_R",
        "META_NOEU": "NOEU_VARI_R",
        "VARI_NOEU": "NOEU_VAR2_R",
        "INDL_ELGA": "ELGA_INDL_R",
        "EPSA_NOEU": "NOEU_EPSI_R",
        "VITE": "NOEU_DEPL_R",
        "SISE_ELNO": "ELNO_SIEF_R",
        "FORC_NODA": "NOEU_DEPL_R",
        "ENEL_NOEU": "NOEU_ENER_R",
        "VITE_ABSOLU": "NOEU_DEPL_R",
        "FLHN_ELGA": "ELGA_FLHN_R",
        "ECIN_ELEM": "ELEM_ENER_R",
        "QIZ1_ELEM": "ELEM_ERRE_R",
        "COMPORTEMENT": "CART_COMPOR",
        "THETA": "NOEU_DEPL_R",
        "DIVU": "NOEU_EPSI_R",
        "ETOT_ELNO": "ELGA_ENER_R",
        "PRAC_NOEU": "NOEU_PRAC_R",
        "UTXX_ELGA": "RIEN",
        "ENEL_ELNO": "ELNO_ENER_R",
        "ENDO_ELGA": "ELGA_SIEF_R",
        "EPMQ_ELNO": "ELNO_EPSI_R",
        "PRES": "NOEU_PRES_C",
        "EPFD_ELGA": "ELGA_EPSI_R",
        "EPSG_ELNO": "ELNO_EPSI_R",
        "SIRO_ELEM": "ELEM_SIEF_R",
        "SIZ2_NOEU": "NOEU_SIEF_R",
        "ACCE": "NOEU_DEPL_R",
        "ETOT_ELEM": "ELEM_ENER_R",
        "FORC_AMOR": "NOEU_DEPL_R",
        "ENDO_NOEU": "ELNO_SIEF_R",
        "ENEL_ELEM": "ELEM_ENER_R",
        "VARI_ELGA": "ELGA_VARI_R",
        "EPFP_ELGA": "ELGA_EPSI_R",
        "EPMG_ELGA": "ELGA_EPSI_R",
        "QIRE_ELEM": "ELEM_ERRE_R",
        "DEPL_VIBR": "NOEU_DEPL_R",
        "DERA_ELGA": "ELGA_DERA_R",
        "EPFD_ELNO": "ELNO_EPSI_R",
        "INTE_ELNO": "ELNO_INTE_R",
        "DISS_NOEU": "NOEU_DISS_R",
        "EFGE_NOEU": "NOEU_SIEF_R",
        "EPMG_NOEU": "NOEU_EPSI_R",
        "ERME_ELEM": "ELEM_ERRE_R",
        "FERRAILLAGE": "ELEM_FER2_R",
        "MARG_ELEM": "ELEM_VFER2_R",
        "DERA_ELNO": "ELNO_DERA_R",
        "EPSI_ELGA": "ELGA_EPSI_R",
        "QIRE_ELNO": "ELNO_ERRE_R",
        "FLUX_ELNO": "ELNO_FLUX_R",
        "STRX_ELGA": "ELGA_STRX_R",
        "UTXX_ELNO": "RIEN",
        "ACCE_ABSOLU": "NOEU_DEPL_R",
        "SING_ELNO": "ELNO_SING_R",
        "IRRA": "NOEU_IRRA_R",
        "SOUR_ELGA": "ELGA_SOUR_R",
        "EPSI_ELNO": "ELNO_EPSI_R",
        "EPSP_ELNO": "ELNO_EPSI_R",
        "SIPO_NOEU": "NOEU_SIEF_R",
        "COMPORTHER": "CART_COMPOR",
        "SIEQ_NOEU": "NOEU_SIEF_R",
        "EPEQ_ELNO": "ELNO_EPSI_R",
        "VARI_ELNO": "ELNO_VARI_R",
        "EPSG_NOEU": "NOEU_EPSI_R",
    }

    liste_noms_champs_contraintes = []
    liste_noms_champs_criteres = []

    # boucle sur les champs du maillage d'entree pour enrichir la SD resultat avec des reuse de crea_resu
    for i in range(nbchamps):
        nom = nomschamps[i]

        # champs a calculer en fin de macro avec calc_champ
        # if nom not in ['DEPL','SIEF_ELGA']:
        #        if nom in ['EFGE_ELGA','EFGE_ELNO','EFGE_NOEU','SIEF_ELNO','SIEF_NOEU','SIGM_ELGA','SIGM_ELNO','SIGM_NOEU','SIPM_ELNO','SIPO_ELNO','SIPO_NOEU','SIRO_ELEM']:
        #                liste_noms_champs_contraintes.append(nom)
        #        if nom in ['EPEQ_ELGA','EPEQ_ELNO','EPEQ_NOEU','EPMQ_ELGA','EPMQ_ELNO','EPMQ_NOEU','SIEQ_ELGA','SIEQ_ELNO','SIEQ_NOEU']:
        #                liste_noms_champs_criteres.append(nom)
        #        continue

        typeCham = dico_equivalence_NOM_TYPE_CHAM[nomschamps[i]]
        arguments_affe = ()
        # boucle sur les instants
        for j in range(nbinst):
            inst = list_instant[j]
            # NUME_ORDRE actuel
            nume_ordre = lnume_ordre[j]
            # extraction modele a cet instant dans le resu_meca_unit
            modele = RESU_MECA_UNIT.getModel(nume_ordre)
            # extraction champ materiau a cet instant dans le resu_meca_unit
            cham_mater = RESU_MECA_UNIT.getMaterialField(nume_ordre)

            chamu[i][j] = CREA_CHAMP(
                NOM_CHAM=nom,
                OPERATION="EXTR",
                RESULTAT=RESU_MECA_UNIT,
                INST=inst,
                TYPE_CHAM=typeCham,
            )

            chamm[i][j] = CREA_CHAMP(
                ASSE=_F(CHAM_GD=chamu[i][j], COEF_R=TEMP_FIN, TOUT="OUI"),
                MODELE=modele,
                OPERATION="ASSE",
                TYPE_CHAM=typeCham,
            )

            arguments_affe += (
                _F(
                    NOM_CHAM=nom,
                    CHAM_GD=chamm[i][j],
                    CHAM_MATER=cham_mater,
                    INST=(inst,),
                    MODELE=modele,
                ),
            )

        if i == 0:
            resMmult = CREA_RESU(AFFE=arguments_affe, OPERATION="AFFE", TYPE_RESU="EVOL_ELAS")

        else:
            resMmult = CREA_RESU(
                reuse=resMmult,
                RESULTAT=resMmult,
                AFFE=arguments_affe,
                OPERATION="AFFE",
                TYPE_RESU="EVOL_ELAS",
            )

    # resMmult = CALC_CHAMP(reuse=resMmult,
    #                RESULTAT=resMmult,
    #                CONTRAINTE = liste_noms_champs_contraintes,
    #                CRITERES = liste_noms_champs_criteres,
    #                )
    # V15, le resultat est retourne par ops
    return resMmult
