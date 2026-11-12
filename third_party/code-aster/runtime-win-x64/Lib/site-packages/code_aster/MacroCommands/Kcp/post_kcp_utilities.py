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
from ...Messages import UTMESS
from ...Objects import Function

# ---------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------#


def calc_bornes(table, valeur):
    """
    RECHERCHE LES BORNES MIN ET MAX POUR UNE VALEUR DANS UN TABLEAU
    """
    x1 = x2 = ix1 = ix2 = 0.0
    if table[0] > table[-1]:
        for i in range(1, len(table)):
            if valeur >= table[i]:
                x1 = table[i - 1]
                x2 = table[i]
                ix1 = i - 1
                ix2 = i
                break
    else:
        for i in range(1, len(table)):
            if valeur <= table[i]:
                x1 = table[i - 1]
                x2 = table[i]
                ix1 = i - 1
                ix2 = i
                break

    return x1, x2, ix1, ix2


# ---------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------#


def nbr_inst_pts(table):
    """
    RECUPERE LE NOMBRE D INSTANT (SANS DOUBLON) ET LE NOMBRE DE POINT PAR INSTANT
    """

    table = np.array(table.EXTR_TABLE().values()["INST"])
    ninst = len(set(table))
    npoints = table.shape[0] // ninst

    return ninst, npoints


# ---------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------#


def calc_K_eq(K1, K2, K3):
    """
    CALCUL DE KEQ PAR LA FORMULE DU CUMUL THETA
    """

    # Créer un masque pour les éléments où K2 != 0
    mask_non_zero_K2 = K2 != 0

    # Initialisation de K_theta
    K_theta = np.zeros_like(K1)

    # Cas où K2 != 0
    if np.any(mask_non_zero_K2):
        # Extraire les valeurs non nulles pour traitement
        K1_non_zero = K1[mask_non_zero_K2]
        K2_non_zero = K2[mask_non_zero_K2]

        # Calcul de theta pour les deux cas : + et -
        theta_plus = 2 * np.arctan(
            (K1_non_zero + np.sqrt(K1_non_zero**2 + 8 * K2_non_zero**2)) / (4 * K2_non_zero)
        )
        theta_minus = 2 * np.arctan(
            (K1_non_zero - np.sqrt(K1_non_zero**2 + 8 * K2_non_zero**2)) / (4 * K2_non_zero)
        )

        # Calcul de K_theta pour les deux angles
        K_theta_plus = (
            K1_non_zero * (np.cos(theta_plus / 2) ** 2) - (3 / 2) * K2_non_zero * np.sin(theta_plus)
        ) * np.cos(theta_plus / 2)
        K_theta_minus = (
            K1_non_zero * (np.cos(theta_minus / 2) ** 2)
            - (3 / 2) * K2_non_zero * np.sin(theta_minus)
        ) * np.cos(theta_minus / 2)

        # On choisit l'angle qui maximise K_theta
        K_theta[mask_non_zero_K2] = np.where(
            K_theta_plus > K_theta_minus, K_theta_plus, K_theta_minus
        )

    # Cas où K2 == 0
    if np.any(~mask_non_zero_K2):
        # Pour les éléments où K2 == 0, K_theta = max(0, K1)
        K_theta[~mask_non_zero_K2] = np.maximum(0, K1[~mask_non_zero_K2])

    # Calcul de K_eq
    K_eq = K_theta + 0.74 * np.abs(K3)

    return K_eq


# ---------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------#


def cart_cyl(table_meca):
    """
    TRANSFORMATION DU TENSEUR DES CONTRAINTES DE LA BASE CARTÉSIENNE
                    À LA BASE CYLINDRIQUE
    """
    # Contrainte dans la base cartésienne
    sixx_values = np.array(table_meca.EXTR_TABLE().values()["SIXX"])
    siyy_values = np.array(table_meca.EXTR_TABLE().values()["SIYY"])
    sizz_values = np.array(table_meca.EXTR_TABLE().values()["SIZZ"])
    sixy_values = np.array(table_meca.EXTR_TABLE().values()["SIXY"])
    sixz_values = np.array(table_meca.EXTR_TABLE().values()["SIXZ"])
    siyz_values = np.array(table_meca.EXTR_TABLE().values()["SIYZ"])

    # Coordonnees
    coorx_values = np.array(table_meca.EXTR_TABLE().values()["COOR_X"])
    coory_values = np.array(table_meca.EXTR_TABLE().values()["COOR_Y"])

    # r, cos(theta), sin(theta) et sin(theta)cos(theta)
    r = np.sqrt(coorx_values**2 + coory_values**2)
    r = np.where(r == 0, 1e-12, r)
    cos_theta = coorx_values / r
    sin_theta = coory_values / r
    sin_cos_theta = cos_theta * sin_theta

    # Contrainte dans la base cylindrique
    sigma_rr = (
        cos_theta**2 * sixx_values + 2 * sin_cos_theta * sixy_values + sin_theta**2 * siyy_values
    )
    sigma_thethet = (
        sin_theta**2 * sixx_values - 2 * sin_cos_theta * sixy_values + cos_theta**2 * siyy_values
    )
    sigma_rtheta = (
        -sin_cos_theta * sixx_values
        + (cos_theta**2 - sin_theta**2) * sixy_values
        + sin_cos_theta * siyy_values
    )

    sigma_rz = cos_theta * sixz_values + sin_theta * siyz_values
    sigma_thetaz = -sin_theta * sixz_values + cos_theta * siyz_values
    sigma_zz = sizz_values

    sigma_cyl = {
        "sigma_rr": sigma_rr,
        "sigma_thethet": sigma_thethet,
        "sigma_zz": sigma_zz,
        "sigma_rtheta": sigma_rtheta,
        "sigma_rz": sigma_rz,
        "sigma_thetaz": sigma_thetaz,
    }

    return sigma_cyl


# ---------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------#


def calc_coef_poly(eps_mdb, eps_rev, ori_fiss, table_meca, ndim, ninst, npoints):
    """
    SIGMA : CALCUL DES COEFFICIENTS DU POLYNOME DE DEGRE 5
    """

    # Récupère les différentes composantes sigma (K1, K2, K3)
    sigma = recup_sigma(ori_fiss, table_meca, ndim)

    # Reshape pour avoir les bonnes dimensions ninst x npoints
    sigma = {
        "sigma_K1": sigma["sigma_K1"].reshape(ninst, npoints),
        "sigma_K2": sigma["sigma_K2"].reshape(ninst, npoints),
        "sigma_K3": sigma["sigma_K3"].reshape(ninst, npoints),
    }

    # Expression polynomiale de degre 4
    if npoints != 5:
        UTMESS("F", "PREPOST_6", vali=npoints)

    abs_curv = np.array(table_meca.EXTR_TABLE().values()["ABSC_CURV"])
    coef = (eps_rev + abs_curv[0:npoints]) / (eps_rev + eps_mdb)

    # Matrice pour résoudre les systèmes linéaires
    matr = np.column_stack([coef**i for i in range(npoints)])

    # Initialisation du dictionnaire des résultats
    results = {}

    # Calcul pour chaque composante sigma (K1, K2, K3)
    for key, sigma_values in sigma.items():
        results[key] = np.array([np.linalg.solve(matr, sigma_row) for sigma_row in sigma_values])

    return results


# ---------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------#


def calc_Sy(mater, temp_A, ninst):
    """
    CALCUL DE LA LIMITE ELASTIQUE À PARTIR D'UNE
    RELATION DE VON MISES À ÉCROUISSAGE ISOTROPE
    """
    phenom = mater.getMaterialNames()

    if "TRACTION" in phenom:
        rev = mater.getFunction("TRACTION", "SIGM")
        if "NAPPE" in rev.getProperties():
            # 'NAPPE'
            # Valeur des températures définit pour la nappe
            temp = np.array(rev.Valeurs()[0])
            # courbe de traction pour les différentes températures de temp
            eps_sigm = rev.Valeurs()[1]
            # Ordonnee du premier point définit la limite élastique du matériau
            sy_temp = np.array([tab[1][0] for tab in eps_sigm])
            # Evaluation de la fonction a temp A
            fsy = Function()
            fsy.setParameterName(rev.getProperties()[2])
            fsy.setExtrapolation(rev.getProperties()[4])
            fsy.setInterpolation(rev.getProperties()[1])
            fsy.setValues(temp, sy_temp)
            sy_tempA = np.array([fsy(t) for t in temp_A])
        else:
            # 'FONCTION'
            # Ordonnee du premier point définit la limite élastique du matériau
            sy_tempA = np.tile(rev.Valeurs()[1][0], ninst)

    elif "ECRO_LINE" in phenom:
        rev = mater.getFunction("ECRO_LINE", "SY")
        if rev is not None:  # 'FONCTION'
            # Sy
            sy_temp = np.array(rev.Valeurs()[1])
            # Evaluation de la fonction a temp A
            sy_tempA = np.array([rev(t) for t in temp_A])
        else:  # 'REEL'
            sy = mater.getValueReal("ECRO_LINE", "SY")
            sy_tempA = np.tile(sy, ninst)
    else:
        UTMESS("F", "PREPOST_10")

    return sy_tempA


# ---------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------#


def recup_sigma(ori_fiss, table_meca, ndim):
    """
    RECUPERATION DES CHAMPS DES CONTRAINTES MECANIQUES
    EN FONCTION DE LA DIMENSION ET ORIENTATION DU DEFAUT (R7.02.10)
    """
    sigma_K1, sigma_K2, sigma_K3 = None, None, None
    tabval = table_meca.EXTR_TABLE().values()

    # Cas 2D
    if ndim == 2:
        if ori_fiss == "CIRC":
            sigma_K1 = np.array(tabval["SIYY"])
            sigma_K2 = np.array(tabval["SIXY"])
        else:
            sigma_K1 = np.array(tabval["SIZZ"])
            sigma_K2 = np.zeros_like(sigma_K1)  # Contrainte hors plan nulle

        sigma_K3 = np.zeros_like(sigma_K1)  # Toujours nul en 2D

    # Cas 3D
    else:
        sigma_cyl = cart_cyl(table_meca)
        if ori_fiss == "CIRC":
            sigma_K1 = sigma_cyl["sigma_zz"]
            sigma_K2 = sigma_cyl["sigma_rz"]
            sigma_K3 = sigma_cyl["sigma_thetaz"]
        else:
            sigma_K1 = sigma_cyl["sigma_thethet"]
            sigma_K2 = sigma_cyl["sigma_rtheta"]
            sigma_K3 = sigma_cyl["sigma_thetaz"]

    return {"sigma_K1": sigma_K1, "sigma_K2": sigma_K2, "sigma_K3": sigma_K3}


# ---------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------#


def recup_temp(table_ther, table_meca):
    """
    RECUPERATION DES TEMPERATURES AUX POINTES DE LA FISSURE A et B
                 POUR CHAQUE INSTANT MÉCANIQUE
    """
    ninst, npoints = nbr_inst_pts(table_ther)
    table_ther = np.array(tuple(table_ther.EXTR_TABLE().values()[i] for i in ("INST", "TEMP")))
    table_ther = table_ther.reshape(2, ninst, npoints).T

    # Recuperation des instants mécanique sans doublon
    table_meca_instant = np.array(table_meca.EXTR_TABLE().values()["INST"])
    _, unique_indices = np.unique(table_meca_instant, return_index=True)
    table_meca_instant = table_meca_instant[np.sort(unique_indices)]

    temp_A = np.interp(table_meca_instant, table_ther[0].T[0], table_ther[0].T[1])
    temp_B = np.interp(table_meca_instant, table_ther[-1].T[0], table_ther[-1].T[1])

    return temp_A, temp_B, table_meca_instant


# ---------------------------------------------------------------------------------------------------#
# ---------------------------------------------------------------------------------------------------#
