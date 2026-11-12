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

import aster
import numpy as NP
from numpy import linalg
from typing import List

from ...CodeCommands import CREA_CHAMP
from ...Utilities import disable_fpe


# --------------------------------------------------------------------------------
#   ROUTINES
# --------------------------------------------------------------------------------
def compute_pod(
    coherency_matrix: NP.ndarray, precision: float, frequencies: NP.ndarray, info: int
) -> List[NP.ndarray]:
    """compute POD
    Args:
        coherency_matrix : coherency matrix shape (nb_freq, nb_nodes, nb_nodes)
        precision : unitary threshold of the sum of the energy
        frequencies : frequencies
        info : verbosity level

    """

    def iter_on_eigen_values_and_vectors_all():
        """Resolve once the the eigenvalue problem for all frequencies"""
        if info == 2:
            aster.affiche("MESSAGE", "RESOLUTION DES VALEURS PROPRES POUR TOUTES LES FREQUENCES")

        with disable_fpe():
            eig, vec = linalg.eigh(coherency_matrix)

        eig = eig.real
        vec = vec.real

        eig[eig < 1.0e-10] = 0.0
        # les vecteurs sont en colonne en sortie de linalg.eigh
        vec = NP.transpose(vec, axes=(0, 2, 1))
        # Sort eigenvalues and eigenvectors in descending order
        eig = eig[:, ::-1]  # shape (nb_fre, nb_nodes)
        vec = vec[:, ::-1]
        yield from zip(eig, vec)

    pvec = []

    for freq, (values, vectors) in zip(frequencies, iter_on_eigen_values_and_vectors_all()):
        cum_nrj = 0.0

        energies = values**2
        e_tot = NP.sum(energies)

        if info == 2:
            aster.affiche("MESSAGE", "FREQUENCE DE CALCUL: " + str(freq))

        # keep only the modes than explain the precision of the cumulative energy
        for nbme, (nrj, value) in enumerate(zip(energies, values), 1):
            if info == 2:
                aster.affiche("MESSAGE", "VALEUR PROPRE " + str(nbme) + " : " + str(value))

            cum_nrj += nrj
            prec = cum_nrj / e_tot

            if prec > precision:
                break

        if info == 2:
            aster.affiche("MESSAGE", "NOMBRE DE MODES POD RETENUS : " + str(nbme))
            aster.affiche("MESSAGE", "PRECISION (ENERGIE RETENUE) : " + str(prec))

        _pvec = NP.sqrt(values[:nbme, None]) * vectors[:nbme]
        pvec.append(_pvec)

    return pvec


# ---------------------------------------------------------------------
# RECUPERATION DES MODES MECA (STATIQUES)
#  boucle sur les modes statiques
def compute_mecmode(NOM_CMP, GROUP_NO_INTER, resultat, nbmods, nbmodd):
    dict_modes = {"NUME_MODE": list(range(nbmods)), "MCMP": [], "som": [], "maxm": []}
    for mods in range(nbmods):
        nmo = nbmodd + mods + 1
        __CHAM = CREA_CHAMP(
            TYPE_CHAM="NOEU_DEPL_R",
            OPERATION="EXTR",
            NUME_ORDRE=nmo,
            RESULTAT=resultat,
            NOM_CHAM="DEPL",
        )
        MCMP, _ = __CHAM.getValuesWithDescription(NOM_CMP, [GROUP_NO_INTER])
        # on recupere la composante COMP (dx,dy,dz) des modes
        MCMP2, description = __CHAM.getValuesWithDescription(groups=[GROUP_NO_INTER])
        if mods == 0:
            NCMP2 = description[1]
            nddi = len(MCMP2)
            dict_modes["NCMP2"] = NCMP2
            dict_modes["nddi"] = nddi
            PHI = NP.zeros((nddi, nbmods))
        PHI[:, mods] = MCMP2
        som = NP.sum(MCMP)
        max1 = NP.max(MCMP)
        min1 = NP.min(MCMP)
        maxm = NP.max([abs(max1), abs(min1)])
        dict_modes["som"].append(som)
        dict_modes["maxm"].append(maxm)
        dict_modes["MCMP"].append(MCMP)
    dict_modes["PHI"] = PHI
    return dict_modes


# ------------------------------------------------------------------------------
def compute_corr_vari(dict_modes, VEC, KRS, FS0):
    PHI = dict_modes["PHI"]
    NCMP2 = dict_modes["NCMP2"]
    PHIT = NP.transpose(PHI)
    PPHI = NP.dot(PHIT, PHI)
    U0 = NP.dot(linalg.inv(KRS), FS0)
    XI = NP.dot(PHI, U0)
    XPI = XI
    SI0 = 0.0
    for k1 in range(dict_modes["nbpod"]):
        XOe = abs(NP.sum(VEC[k1])) / dict_modes["nbno"]
        SI0 = SI0 + XOe**2
    SI = NP.sqrt(SI0)
    for idd in range(0, dict_modes["nddi"]):
        if NCMP2[idd][0:2] == dict_modes["NOM_CMP"]:
            XPI[idd] = SI * XI[idd]
    QPI = NP.dot(PHIT, XPI)
    U0 = NP.dot(linalg.inv(PPHI), QPI)
    FS = NP.dot(KRS, U0)
    return FS
