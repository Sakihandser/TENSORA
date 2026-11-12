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
import libAsterGC
from ..CodeCommands import CREA_TABLE
from ..Messages import UTMESS
from .PostVeriFerraillage.calculetatsect import sectionELU, sectionELS


def trouver_marges_seuil(data, seuil):
    """Extracts the list of mesh groups where the margin is below a threshold.

    This function scans the list of MARGE values and identifies the corresponding
    mesh entities whose margin is strictly below the given threshold value.

    Arguments:
        data (tuple): A tuple where the first element is the list of MARGE values
            (floats), and the second element is a list containing the mesh group
            names associated to each margin.
        seuil (float): Threshold value below which margins are considered critical.

    Returns:
        list[str]: A list of cells numbers whose associated margin is
        strictly lower than the specified threshold.
    """
    marges = data[0]
    mailles = data[1][0]
    mailles_correspondantes = []
    for i, marge in enumerate(marges):
        if marge <= seuil:
            mailles_correspondantes.append(mailles[i])

    return mailles_correspondantes


def trouver_NDIAG_marges_minimales(data, N_DIAG):
    """Finds the mesh groups with the N smallest margin values.

    This function sorts all mesh cells by their margin values in ascending order
    and extracts the names of those with the N_DIAG lowest margins.

    Arguments:
        data (tuple): A tuple where the first element is the list of MARGE values
            (floats), and the second element is a list containing the mesh group
            names associated to each margin.
        N_DIAG (int): The number of diagrams to consider. .

    Returns:
        list[str]: A list of cells numbers associated with the N_DIAG
        lowest margins.
    """
    marges = data[0]
    mailles = data[1][0]
    marges_mailles = list(zip(marges, mailles))

    # Trier la liste des tuples par marge
    marges_mailles.sort(key=lambda x: x[0])

    # Extraire les N_DIAG premières marges et leurs mailles correspondantes
    mailles_correspondantes = [maille for marge, maille in marges_mailles[:N_DIAG]]

    return mailles_correspondantes


def post_veri_ferraillage_ops(self, CHAM_VFER, **args):
    """
    macro POST_VERI_FERRAILLAGE
    """
    if (len(args)) > 1:
        UTMESS("F", "VERIFERRAILLAGE_15")

    Ma = CHAM_VFER.getMesh()
    lisgrma = Ma.getGroupsOfCells()

    if "GROUP_MA" in args:
        GROUP_MA = args.get("GROUP_MA")
        if not (all(element in lisgrma for element in GROUP_MA)):
            UTMESS("F", "VERIFERRAILLAGE_12")
        list_ma = CHAM_VFER.getValuesWithDescription("MARGE", GROUP_MA)[1][0]
    elif "SEUIL_MIN_MARGE" in args:
        marge_struct = CHAM_VFER.getValuesWithDescription("MARGE")
        SEUIL_MARGE = args["SEUIL_MIN_MARGE"]
        list_ma = trouver_marges_seuil(marge_struct, SEUIL_MARGE)
        if len(list_ma) == 0:
            UTMESS("F", "VERIFERRAILLAGE_13")
    elif "NB_DIAG" in args:
        marge_struct = CHAM_VFER.getValuesWithDescription("MARGE")
        NB_DIAG = args.get("NB_DIAG")
        list_ma = trouver_NDIAG_marges_minimales(marge_struct, NB_DIAG)
        if NB_DIAG > len(list_ma):
            UTMESS("F", "VERIFERRAILLAGE_14")
    else:
        raise KeyError("unexpected arguments")

    # lecture des paramètres CHAM_VFER
    cmps = CHAM_VFER.getComponents()
    dint_param = CHAM_VFER.getValuesWithDescription([], list_ma)[0]

    # Initialisation du dictionnaire de résultats
    resultats = {nom: [] for nom in cmps}
    n_composantes = len(cmps)
    # Remplissage du dictionnaire
    for i in range(len(list_ma)):
        for j, nom in enumerate(cmps):
            resultats[nom].append(dint_param[i * n_composantes + j])
    marge_crit = resultats["MARGE"]
    dnsinf_crit = resultats["DNSINF"]
    dnssup_crit = resultats["DNSSUP"]
    effn0_crit = resultats["N0"]
    effm0_crit = resultats["M0"]
    effn_crit = resultats["NED"]
    effm_crit = resultats["MED"]
    Nrd_crit = resultats["N_DIAG"]
    Mrd_crit = resultats["M_DIAG"]
    typcmb = resultats["TYPCMB"]
    typco = resultats["TYPCO"]
    cequi = resultats["CEQUI"]
    enrobi = resultats["ENROBI"]
    enrobs = resultats["ENROBS"]
    sigs = resultats["SIGS"]
    sigci = resultats["SIGCI"]
    sigcs = resultats["SIGCS"]
    alphacc = resultats["ALPHACC"]
    gammas = resultats["GAMMAS"]
    gammac = resultats["GAMMAC"]
    facier = resultats["FACIER"]
    eys = resultats["EYS"]
    typdiag = resultats["TYPDIAG"]
    fbeton = resultats["FBETON"]
    clacier = resultats["CLACIER"]
    uc = resultats["UC"]
    ht = resultats["HT"]
    bw = resultats["BW"]
    length = len(list_ma)

    # Appeler la fonction pour chaque maille
    # Listes pour stocker les résultats
    nom_results = []
    nrd_results = []
    mrd_results = []
    hc_results = []
    epsilon_beton_results = []
    epsilon_acierinf_results = []
    epsilon_aciersup_results = []
    sigma_beton_results = []
    sigma_acierinf_results = []
    sigma_aciersup_results = []
    for i in range(length):
        if typcmb[i] == 0:
            typco[i] = int(typco[i])
            clacier[i] = int(clacier[i])
            typdiag[i] = int(typdiag[i])
            uc[i] = int(uc[i])
            nrd, mrd = libAsterGC.dintelu(
                typco[i],
                alphacc[i],
                ht[i],
                bw[i],
                enrobi[i],
                enrobs[i],
                facier[i],
                fbeton[i],
                gammas[i],
                gammac[i],
                clacier[i],
                eys[i],
                typdiag[i],
                uc[i],
                dnsinf_crit[i],
                dnssup_crit[i],
            )
            my_section = sectionELU(
                marge_crit[i],
                typco[i],
                uc[i],
                clacier[i],
                typdiag[i],
                ht[i],
                enrobs[i],
                enrobi[i],
                facier[i],
                fbeton[i],
                alphacc[i],
                eys[i],
                gammac[i],
                gammas[i],
                dnsinf_crit[i],
                dnssup_crit[i],
                effn_crit[i],
                effm_crit[i],
                Nrd_crit[i],
                Mrd_crit[i],
            )
            # The starting point for NR iterations at ELU is the solution at ELS
            my_section_ELS = sectionELS(
                marge_crit[i],
                ht[i],
                enrobs[i],
                enrobi[i],
                sigs[i],
                sigcs[i],
                sigci[i],
                eys[i],
                15.0,
                dnsinf_crit[i],
                dnssup_crit[i],
                effn_crit[i],
                effm_crit[i],
                Nrd_crit[i],
                Mrd_crit[i],
            )
            etat0 = my_section_ELS.compute_x_and_curv_ELS()
            etat = my_section.compute_etat_section_ELU(etat0)
        elif typcmb[i] == 1:
            uc[i] = int(uc[i])
            nrd, mrd = libAsterGC.dintels(
                cequi[i],
                ht[i],
                bw[i],
                enrobi[i],
                enrobs[i],
                sigci[i],
                sigcs[i],
                sigs[i],
                uc[i],
                dnsinf_crit[i],
                dnssup_crit[i],
            )
            my_section = sectionELS(
                marge_crit[i],
                ht[i],
                enrobs[i],
                enrobi[i],
                sigs[i],
                sigcs[i],
                sigci[i],
                eys[i],
                cequi[i],
                dnsinf_crit[i],
                dnssup_crit[i],
                effn_crit[i],
                effm_crit[i],
                Nrd_crit[i],
                Mrd_crit[i],
            )
            etat = my_section.compute_etat_section_ELS()
        # on ajoute 1 au numero de maille pour correspondre a la numerotation de salome
        nom_results.extend([list_ma[i] + 1] * (len(nrd) + 2))
        nrd_results.extend(nrd)
        nrd_results.append(effn0_crit[i])
        nrd_results.append(effn_crit[i])
        mrd_results.extend(mrd)
        mrd_results.append(effm0_crit[i])
        mrd_results.append(effm_crit[i])
        hc_results.extend([etat[0]] * (len(nrd) + 2))

        if typcmb[i] == 1:
            epsilon_beton_results.extend([max(etat[1][0], etat[1][1])] * (len(nrd) + 2))
            epsilon_acierinf_results.extend([etat[1][2]] * (len(nrd) + 2))
            epsilon_aciersup_results.extend([etat[1][3]] * (len(nrd) + 2))
            sigma_beton_results.extend([max(etat[2][0], etat[2][1])] * (len(nrd) + 2))
            sigma_acierinf_results.extend([etat[2][2]] * (len(nrd) + 2))
            sigma_aciersup_results.extend([etat[2][3]] * (len(nrd) + 2))
        else:
            epsilon_beton_results.extend([etat[1][0]] * (len(nrd) + 2))
            epsilon_acierinf_results.extend([etat[1][1]] * (len(nrd) + 2))
            epsilon_aciersup_results.extend([etat[1][2]] * (len(nrd) + 2))
            sigma_beton_results.extend([etat[2][0]] * (len(nrd) + 2))
            sigma_acierinf_results.extend([etat[2][1]] * (len(nrd) + 2))
            sigma_aciersup_results.extend([etat[2][2]] * (len(nrd) + 2))

    tabout = CREA_TABLE(
        LISTE=(
            _F(PARA="NUMERO_MAILLE", LISTE_I=nom_results),
            _F(PARA="N", LISTE_R=nrd_results),
            _F(PARA="M", LISTE_R=mrd_results),
            _F(PARA="HAUTEUR_COMPRIMEE", LISTE_R=hc_results),
            _F(PARA="EPSILON_BETON", LISTE_R=epsilon_beton_results),
            _F(PARA="EPSILON_ACIER_INF", LISTE_R=epsilon_acierinf_results),
            _F(PARA="EPSILON_ACIER_SUP", LISTE_R=epsilon_aciersup_results),
            _F(PARA="SIGMA_BETON", LISTE_R=sigma_beton_results),
            _F(PARA="SIGMA_ACIER_INF", LISTE_R=sigma_acierinf_results),
            _F(PARA="SIGMA_ACIER_SUP", LISTE_R=sigma_aciersup_results),
        )
    )

    return tabout
