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

import numpy as np
from .beta_coef_infl_a import coef_pts_A
from .beta_coef_infl_b1 import coef_pts_B1
from .beta_coef_infl_b2 import coef_pts_B2
from .beta_coef_infl_c1 import coef_pts_C1
from .beta_coef_infl_c2 import coef_pts_C2
from .post_kcp_utilities import *


# ---------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------#


def K_beta(K, beta, ninst):
    """
    CALCUL DE KCP EN PHASE CROISSANTE ET DÉCROISSANTE
    """

    Kmax = dkmax = 0.0

    Kcp = np.zeros_like(K)

    for i in range(ninst):
        if K[i] < Kmax:
            Kcp[i] = K[i] + dkmax
        else:
            val1 = beta[i] * K[i]
            val2 = K[i] + dkmax

            if val1 > val2:
                Kcp[i] = val1
                dkmax = Kcp[i] - K[i]
            else:
                Kcp[i] = K[i] + dkmax
        Kmax = K[i]

    return Kcp


# ---------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------#


def calc_coef_infl_beta(mat_mdb, mat_rev, eps_rev, prof_fiss, long_fiss, temp_A, temp_B, defaut):
    """
    CALCUL DES COEFFICIENTS D INFLUENCE
    RSE-M 2022 ANNEXE 5.4
    """

    # a/c avec a profondeur du defaut et c demi longueur du defaut
    asc = np.array([1.0, 0.5, 0.25, 0.125, 0.0625, 0.0])

    # a/r avec r epaisseur du revetement
    asr = np.array([0.0, 0.125, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0])

    # Fissure reelle
    if defaut == "BANDE":
        x = 0.0
    else:
        x = prof_fiss / long_fiss * 2.0

    y = prof_fiss / eps_rev

    # Data RSEM modume young
    z1 = 1.0
    z2 = 0.7

    # Recherche des bornes x1 et x2 encadrant (x=a/c)
    x1, x2, ix1, ix2 = calc_bornes(asc, x)

    # Recherche des bornes y1 et y2 encadrant (x=a/r)
    y1, y2, iy1, iy2 = calc_bornes(asr, y)

    # Modules de young
    erev = mat_rev.getFunction("ELAS", "E")
    emdb = mat_mdb.getFunction("ELAS", "E")

    erev_values = erev.getValuesAsArray()[:, 1]  # Deuxième colonne de erev
    emdb_values = emdb.getValuesAsArray()[:, 1]  # Deuxième colonne de emdb

    if len(erev_values) != len(emdb_values):
        UTMESS("F", "PREPOST_3")

    # Calcul du rapport
    ratio = erev_values / emdb_values

    # Vérification de la condition 0.7 <= ratio <= 1
    is_valid = np.all((ratio >= 0.7) & (ratio <= 1))

    if not is_valid:
        UTMESS("F", "PREPOST_5")

    if erev is not None:
        erev_vals = erev.getValuesAsArray()
        erev_temp_B = np.interp(temp_B, erev_vals[:, 0], erev_vals[:, 1])
        erev_temp_C = np.interp(temp_A, erev_vals[:, 0], erev_vals[:, 1])
    else:
        erev_temp_B = erev_temp_C = mat_rev.getValueReal("ELAS", "E")

    if emdb is not None:
        emdb_vals = emdb.getValuesAsArray()
        emdb_temp_B = np.interp(temp_B, emdb_vals[:, 0], emdb_vals[:, 1])
        emdb_temp_C = np.interp(temp_A, emdb_vals[:, 0], emdb_vals[:, 1])
    else:
        emdb_temp_B = emdb_temp_C = mat_mdb.getValueReal("ELAS", "E")

    # Calcul des rapports z au point B et C
    zb = erev_temp_B / emdb_temp_B
    zc = erev_temp_C / emdb_temp_C

    # ---------------------------------------------------------#
    # Point A : Calcul des coefficients d'influence 2 variables
    A11, A21, A12, A22 = coef_pts_A(ix1, ix2, iy1, iy2)

    # Coef A : interpolation barycentrique 2 variables
    coeinf_A = (1.0 / ((x2 - x1) * (y2 - y1))) * (
        (x2 - x) * (y2 - y) * A11
        + (x2 - x) * (y - y1) * A12
        + (x - x1) * (y2 - y) * A21
        + (x - x1) * (y - y1) * A22
    )

    # ---------------------------------------------------------#
    # Point B : Calcul des coefficients d'influence 3 variables
    B111, B211, B121, B221 = coef_pts_B1(ix1, ix2, iy1, iy2)
    B112, B212, B122, B222 = coef_pts_B2(ix1, ix2, iy1, iy2)

    # Coef B: interpolation barycentrique 3 variables
    zb = zb[:, np.newaxis]
    coeinf_B = (1.0 / ((x2 - x1) * (y2 - y1) * (z2 - z1))) * (
        (x2 - x) * (y2 - y) * (z2 - zb) * B111
        + (x2 - x) * (y - y1) * (z2 - zb) * B121
        + (x - x1) * (y2 - y) * (z2 - zb) * B211
        + (x - x1) * (y - y1) * (z2 - zb) * B221
        + (x2 - x) * (y2 - y) * (zb - z1) * B112
        + (x2 - x) * (y - y1) * (zb - z1) * B122
        + (x - x1) * (y2 - y) * (zb - z1) * B212
        + (x - x1) * (y - y1) * (zb - z1) * B222
    )

    # ---------------------------------------------------------#
    # si a/c < 1/16, pas d'interpolation pour le point C car la valeur
    # n existe pas pour a/c = 0, on prend la valeur pour a/c = 1/16
    if x2 == asc[-1]:
        ix2 = ix1

    # Point C : Calcul des coefficients d'influence 3 variables
    C111, C211, C121, C221 = coef_pts_C1(ix1, ix2, iy1, iy2)
    C112, C212, C122, C222 = coef_pts_C2(ix1, ix2, iy1, iy2)
    zc = zc[:, np.newaxis]
    # Coef C: interpolation barycentrique 3 variables
    coeinf_C = (1.0 / ((x2 - x1) * (y2 - y1) * (z2 - z1))) * (
        (x2 - x) * (y2 - y) * (z2 - zc) * C111
        + (x2 - x) * (y - y1) * (z2 - zc) * C121
        + (x - x1) * (y2 - y) * (z2 - zc) * C211
        + (x - x1) * (y - y1) * (z2 - zc) * C221
        + (x2 - x) * (y2 - y) * (zc - z1) * C112
        + (x2 - x) * (y - y1) * (zc - z1) * C122
        + (x - x1) * (y2 - y) * (zc - z1) * C212
        + (x - x1) * (y - y1) * (zc - z1) * C222
    )

    return coeinf_A, coeinf_B, coeinf_C


# ---------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------#


def calc_sif_beta(
    mater_mdb,
    mater_rev,
    eps_mdb,
    eps_rev,
    prof_fiss,
    long_fiss,
    ori_fiss,
    table_meca,
    ndim,
    temp_A,
    temp_B,
    defaut,
):
    """
    CALCUL DES FACTEURS D'INTENSITE DE CONTRAINTES ELASTIQUES
    AVEC LA METHODE DES COEFFICIENTS D'INFLUENCE
    """

    ninst, npoints = nbr_inst_pts(table_meca)

    # Calcul des coefficients d'influence aux trois points
    coeinf_points = calc_coef_infl_beta(
        mater_mdb, mater_rev, eps_rev, prof_fiss, long_fiss, temp_A, temp_B, defaut
    )

    # Calcul des coefficients du polynôme pour la contrainte
    coef_poly_dict = calc_coef_poly(eps_mdb, eps_rev, ori_fiss, table_meca, ndim, ninst, npoints)

    # Paramètre pour correction beta
    xl = (prof_fiss + eps_rev) / (eps_mdb + eps_rev)
    xl_power = np.array([xl**i for i in range(npoints)])

    # Dictionnaires pour K1, K2, K3, Keq
    K_dict = {"K1": {}, "K2": {}, "K3": {}}
    K_eq_dict = {}

    # Boucle sur les points A, B, C
    points = ["A", "B", "C"]
    for i, point in enumerate(points):
        coeinf = coeinf_points[i]  # coeinf_A, coeinf_B, coeinf_C

        for k in ["K1", "K2", "K3"]:
            K_dict[k][f"{k}_{point}"] = np.sqrt(np.pi * prof_fiss) * np.sum(
                coef_poly_dict[f"sigma_{k}"] * coeinf * xl_power, axis=1
            )

        # Calcul de K_eq
        K_eq_dict[f"K_eq_{point}"] = calc_K_eq(
            K_dict["K1"][f"K1_{point}"], K_dict["K2"][f"K2_{point}"], K_dict["K3"][f"K3_{point}"]
        )

    return K_dict["K1"], K_dict["K2"], K_dict["K3"], K_eq_dict


# ---------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------#


def calc_kcp_beta(
    mater_rev, eps_rev, prof_fiss, long_fiss, ori_fiss, meca_mdb, K_eq_dict, temp_A, correction
):
    """
    AJOUT DE CORRECTION PLASTIQUE AU CALCUL DES
    FACTEURS D'INTENSITE DE CONTRAINTES
    """
    ninst, npoints = nbr_inst_pts(meca_mdb)

    # Calcul de la limite elastique du materiau
    sy = calc_Sy(mater_rev, temp_A, ninst)

    # Rayon de la zone plastique
    ry = (1.0 / (6.0 * np.pi)) * (K_eq_dict["K_eq_A"] / sy) ** 2

    # Tableau coefficients : RSE-M hauteur du défaut en mm
    if ori_fiss == "LONGI":
        ca = 0.165 * np.log(prof_fiss * 1000.0)
        cb = 0.465 * (1 + (prof_fiss / 100.0) * 1000.0)
    else:
        ca = 0.5
        cb = 0.5

    # Calcul des facteurs de correction plastique
    beta_A = 1.0 + ca * np.tanh(36.0 * ry / eps_rev)
    beta_B = 1.0 + cb * np.tanh(36.0 * ry / eps_rev)

    if correction == "BETA_2D":
        kcp_dict = {
            "KCP_A": K_beta(K_eq_dict["K_eq_A"], beta_A, ninst),
            "KCP_B": K_beta(K_eq_dict["K_eq_B"], beta_B, ninst),
            "KCP_C": K_beta(K_eq_dict["K_eq_C"], beta_B, ninst),
        }
    else:  # Correction BETA_3D (RSEM > 2016)
        term1 = (1.0 + 1.464 * (prof_fiss / (2.0 * long_fiss)) ** 1.65) ** 0.5
        term2 = (1.0 + 1.464 * (beta_B**2.0) * (prof_fiss / (2.0 * long_fiss)) ** 1.65) ** 0.5
        beta_B_3D = np.maximum(1, beta_B * term1 / term2)

        kcp_dict = {
            "KCP_A": K_beta(K_eq_dict["K_eq_A"], beta_A, ninst),
            "KCP_B": K_beta(K_eq_dict["K_eq_B"], beta_B_3D, ninst),
            "KCP_C": K_beta(K_eq_dict["K_eq_C"], beta_B, ninst),
        }

    return kcp_dict


# ---------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------#
