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

"""
Calcul de KCP
"""
from .post_kcp_utilities import recup_temp
from .post_kcp_beta import calc_sif_beta, calc_kcp_beta

from ...CodeCommands import CREA_TABLE
from ...Objects.table_py import Table


def post_kcp_ops(self, **kwargs):

    # Dimension du modele
    model = kwargs.get("MODELE")
    ndim = model.getGeometricDimension()

    # Parametres materiau
    mater_mdb = kwargs.get("MATER_MDB")
    mater_rev = kwargs.get("MATER_REV")
    epais_mdb = kwargs.get("EPAIS_MDB")
    epais_rev = kwargs.get("EPAIS_REV")

    # Parametre de la fissure
    fissure = kwargs.get("FISSURE")
    defaut = fissure.get("FORM_FISS")
    prof_fiss = fissure.get("PROFONDEUR")
    ori_fiss = fissure.get("ORIENTATION")
    long_fiss = fissure.get("LONGUEUR")
    if fissure.get("CORRECTION") is not None:
        correction = fissure.get("CORRECTION")
    else:
        correction = "BETA_2D"  # cas défaut bande
    UNITE_LONGUEUR = kwargs.get("UNITE_LONGUEUR")
    if UNITE_LONGUEUR == "MM":
        epais_mdb = epais_mdb / 1000.0
        epais_rev = epais_rev / 1000.0
        prof_fiss = prof_fiss / 1000.0
        long_fiss = long_fiss / 1000.0

    # Preparation des parametres de la table
    listdic = []

    # Définir la liste de paramètres de base commune
    listpara = ["INST", "TEMP_A", "TEMP_B", "K1_A", "K1_B", "K2_A", "K2_B"]

    if defaut == "SEMI_ELLIPTIQUE":
        # Cas SEMI_ELLIPTIQUE
        listpara.extend(["K1_C", "K2_C", "K_eq_A", "K_eq_B", "K_eq_C", "KCP_A", "KCP_B", "KCP_C"])
    else:
        # Cas BANDE
        listpara.extend(["K_eq_A", "K_eq_B", "KCP_A", "KCP_B"])

    if ndim == 3:
        listpara.extend(["K3_A", "K3_B"])
        if defaut == "SEMI_ELLIPTIQUE":
            listpara.extend(["K3_C"])

    listtype = ["R"] * len(listpara)

    # ======================================================================
    #   ITERATIONS SUR LES DIFFERENTES OCCURENCES DE K1D
    # ======================================================================
    transitoire = kwargs.get("K1D")

    for item in transitoire:

        meca_mdb = item.get("TABL_MECA")
        table_ther = item.get("TABL_THER")

        # Récupération des températures aux pointes de la fissure
        temp_A, temp_B, table_meca_instant = recup_temp(table_ther, meca_mdb)

        # Calcul des SIF élastiques
        K1_dict, K2_dict, K3_dict, K_eq_dict = calc_sif_beta(
            mater_mdb,
            mater_rev,
            epais_mdb,
            epais_rev,
            prof_fiss,
            long_fiss,
            ori_fiss,
            meca_mdb,
            ndim,
            temp_A,
            temp_B,
            defaut,
        )

        # Calcul de la correction plastique (correction Beta)
        kcp_dict = calc_kcp_beta(
            mater_rev,
            epais_rev,
            prof_fiss,
            long_fiss,
            ori_fiss,
            meca_mdb,
            K_eq_dict,
            temp_A,
            correction,
        )

        # Creation de la table
        for i in range(0, len(table_meca_instant)):
            tabl_dict = {}
            tabl_dict["INST"] = table_meca_instant[i]
            tabl_dict["TEMP_A"] = temp_A[i]
            tabl_dict["TEMP_B"] = temp_B[i]
            tabl_dict["K1_A"] = K1_dict["K1_A"][i]
            tabl_dict["K1_B"] = K1_dict["K1_B"][i]
            tabl_dict["K1_C"] = K1_dict["K1_C"][i]
            tabl_dict["K2_A"] = K2_dict["K2_A"][i]
            tabl_dict["K2_B"] = K2_dict["K2_B"][i]
            tabl_dict["K2_C"] = K2_dict["K2_C"][i]
            tabl_dict["K3_A"] = K3_dict["K3_A"][i]
            tabl_dict["K3_B"] = K3_dict["K3_B"][i]
            tabl_dict["K3_C"] = K3_dict["K3_C"][i]
            tabl_dict["K_eq_A"] = K_eq_dict["K_eq_A"][i]
            tabl_dict["K_eq_B"] = K_eq_dict["K_eq_B"][i]
            tabl_dict["K_eq_C"] = K_eq_dict["K_eq_C"][i]
            tabl_dict["KCP_A"] = kcp_dict["KCP_A"][i]
            tabl_dict["KCP_B"] = kcp_dict["KCP_B"][i]
            tabl_dict["KCP_C"] = kcp_dict["KCP_C"][i]
            listdic.append(tabl_dict)

    table = Table(listdic, listpara, listtype)

    return CREA_TABLE(**table.dict_CREA_TABLE())
