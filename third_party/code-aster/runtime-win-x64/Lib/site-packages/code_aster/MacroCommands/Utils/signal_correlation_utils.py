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


# Routines for correlated signals ground motion spatial variability
"""spatial_variability.py

A collection of general-purpose routines using Numpy

CALC_COHE        ---   generation of coherency matrix
                       MITA_LUCO(Exponential Mita and Luco model)
                       ABRAHAMSON(Abrahamson rock coherency model)
                       CORRCOEF: correlation coefficient (not frequency dependent)
COHE_DATA_POINTS  ---  evaluate distances from nodal coordinates for coherency
DSP2ACCE_ND        ---   simulation of vector valued random process
gene_traj_gauss_evol_ND        ---   simulation of vector valued random process
"""

from math import pi, sqrt

import numpy as NP

from ...Utilities import disable_fpe
from ...Messages import UTMESS

from ...Objects.function_py import t_fonction
from .random_signal_utils import ACCE2SROM, acce_filtre_CP, calc_dsp_FR, calc_dsp_KT, dsp_filtre_CP


# -------------------------------------------------------------------
# COHERENCY MATRIX
# --------------------------------------------------------------------
def calc_coherency_matrix(frequencies, model, nom_mail, nom_group_inter, **kwargs):
    """
    Calculation of coherency matrix

    Arguments:
        frequencies : list of frequencies
        model : coherency function type
        nom_mail : mesh name
        nom_group_inter : group of nodes constituting the soil-structure interface
        kwargs: other arguments from the commands
    """
    if "NOEUDS_INTERF" in kwargs:
        noe_interf = kwargs["NOEUDS_INTERF"]
    else:
        liste_nom, noe_interf = get_group_nom_coord(nom_group_inter, nom_mail)
    if "DIST" in kwargs:
        DIST2 = kwargs["DIST"]
    else:
        DIST2 = calc_dist2(noe_interf)
    frequencies = frequencies[:, None, None]
    dist_xi = NP.sqrt(DIST2)
    if model == "MITA_LUCO":
        # PARAMETRES fonction de coherence
        VITE_ONDE = kwargs["VITE_ONDE"]
        alpha = kwargs["PARA_ALPHA"]
        COHE = NP.exp(-(DIST2 * (alpha * frequencies * 2.0 * pi / VITE_ONDE) ** 2.0))
    elif model == "ABRAHAMSON":
        p_a1 = 1.647
        p_a2 = 1.01
        p_a3 = 0.4
        p_n1 = 7.02
        p_n2 = 5.1 - 0.51 * NP.log(dist_xi + 10.0)
        pfc = -1.886 + 2.221 * NP.log(4000.0 / (dist_xi + 1.0) + 1.5)
        numerator = frequencies * NP.tanh(p_a3 * dist_xi)
        term1 = 1.0 + (numerator / (p_a1 * pfc)) ** p_n1
        term2 = 1.0 + (numerator / (p_a2 * pfc)) ** p_n2
        COHE = 1.0 / NP.sqrt(term1 * term2)
    elif model == "ABRA_ROCHER":
        p_a1 = 1.0
        p_a2 = 40.0
        p_a3 = 0.4
        p_n2 = 16.4
        log_d = NP.log(dist_xi + 1.0)
        p_n1 = 3.8 - 0.04 * log_d + 0.0105 * (log_d - 3.6) ** 2
        pfc = 27.9 - 4.82 * log_d + 1.24 * (log_d - 3.6) ** 2
        numerator = frequencies * NP.tanh(p_a3 * dist_xi)
        term1 = 1.0 + (numerator / (p_a1 * pfc)) ** p_n1
        term2 = 1.0 + (numerator / p_a2) ** p_n2
        COHE = 1.0 / NP.sqrt(term1 * term2)
    elif model == "ABRA_SOLMOYEN":
        p_a1 = 1.0
        p_a3 = 0.4
        p_n1 = 3.0
        p_n2 = 15.0
        p_a2 = 15.8 - 0.044 * dist_xi
        pfc = 14.3 - 2.35 * NP.log(dist_xi + 1.0)

        numerator = frequencies * NP.tanh(p_a3 * dist_xi)
        term1 = 1.0 + (numerator / (p_a1 * pfc)) ** p_n1
        term2 = 1.0 + (numerator / p_a2) ** p_n2
        COHE = 1.0 / NP.sqrt(term1 * term2)
    return COHE


def CALC_COHE(puls, **kwargs):
    """
    Use to call calc_coherency_matrix from CALC_MISS
    Convert pulsations to frequencies and call calc_coherency_matrix

    Arguments :
        pusl : pulsation values vector

    Return :
        Coherency matrix
    """
    coherency_matrix = calc_coherency_matrix(
        frequencies=NP.array([puls / (2.0 * pi)]),
        model=kwargs["TYPE"],
        nom_mail=kwargs["MAILLAGE"],
        nom_group_inter=kwargs["GROUP_NO_INTERF"],
        **kwargs,
    )
    return coherency_matrix[0]


def get_group_nom_coord(group_inter, nom_mail):
    print("in signal_correlation_utils")
    # no des noeuds
    liste_no_interf = nom_mail.getNodes(group_inter, localNumbering=True)
    # nom des noeuds
    liste_nom_no_int = [str(node + 1) for node in liste_no_interf]
    COORD_3D = nom_mail.getCoordinates().getValues()
    coord_no_interf = NP.array([COORD_3D[3 * node : 3 * (node + 1)] for node in liste_no_interf])
    if len(coord_no_interf[0]) == 2:
        z = NP.zeros((len(coord_no_interf[:, 0]), 1))
        coord_no_interf = NP.append(coord_no_interf, z, axis=1)
    return liste_nom_no_int, coord_no_interf


def get_no_refe(PHASE_DATA):
    nom_mail = PHASE_DATA["MAILLAGE"]
    group_inter = PHASE_DATA["GROUP_NO_INTERF"]
    direction = PHASE_DATA["DIRECTION"]
    l_nom, coord_no = get_group_nom_coord(group_inter, nom_mail)
    ldir = NP.dot(NP.array(coord_no), NP.array(direction))
    index_min = ldir.argmin()
    coord_refe = coord_no[index_min]
    return coord_refe


def calc_dist2(noe_interf):
    XX = noe_interf[:, 0]
    YY = noe_interf[:, 1]
    nbno = len(XX)
    XN = NP.repeat(XX, nbno)
    YN = NP.repeat(YY, nbno)
    XR = NP.reshape(XN, (nbno, nbno))
    YR = NP.reshape(YN, (nbno, nbno))
    XRT = NP.transpose(XR)
    YRT = NP.transpose(YR)
    DX = XR - XRT
    DY = YR - YRT
    DIST = DX**2 + DY**2
    return DIST


# -------------------------------------------------------------------
# CORRELATION MATRIX
# --------------------------------------------------------------------
def CALC_CORRE(rho, dim, RATIO_HV=1.0):
    if dim == 2:
        Mat_cor = NP.array([[1.0, rho], [rho, 1.0]])
    elif dim == 3:
        Mat_cor = NP.array([[1.0, rho, 0.0], [rho, 1.0, 0.0], [0.0, 0.0, RATIO_HV]])
    return Mat_cor


def _symmetric_psd_sqrt(matrix):
    """Return the principal square root of a symmetric positive semidefinite matrix.

    Eigenvectors returned by LAPACK are not unique: their signs and order
    may differ between implementations, and a degenerate eigenspace may be
    represented by a different orthonormal basis.
    The principal square root Q sqrt(Lambda) Q.T is invariant under those
    sign, ordering and degenerate-basis changes.  Small negative eigenvalues
    caused by round-off are clipped to zero, as required for a covariance or
    coherency matrix.
    """
    # --- Platform-independent coherency factorization: begin ---
    # Remove any round-off-sized antisymmetric part before calling the LAPACK
    # routine dedicated to real symmetric matrices.
    symmetric_matrix = 0.5 * (matrix + matrix.T)

    with disable_fpe():
        eigenvalues, eigenvectors = NP.linalg.eigh(symmetric_matrix)

    # A coherency matrix is positive semidefinite in exact arithmetic.  Tiny
    # negative eigenvalues may nevertheless be returned because of round-off.
    eigenvalues = NP.clip(eigenvalues, 0.0, None)

    # NumPy broadcasting scales column j of eigenvectors by sqrt(lambda_j).
    # Multiplication by eigenvectors.T then builds Q sqrt(Lambda) Q.T.
    matrix_sqrt = (eigenvectors * NP.sqrt(eigenvalues)) @ eigenvectors.T
    # --- Platform-independent coherency factorization: end ---
    return matrix_sqrt


# -------------------------------------------------------------------
# ALGORITHME DE GENERATION DE SIGNAUX GAUSSIENS POUR LE CAS VECTORIEL
# --------------------------------------------------------------------
def DSP2ACCE_ND(f_dsp, data_cohe, rv=None):
    # ----------------------------------
    # IN: f_dsp: dsp function for of list frequencies lw2 on (0, OM)
    #     rv: realisation des N (2) vecteurs
    #         de variables aleatoires gaussiennes complexe
    #     cohe : coherency matrix or correlation coefficient
    # OUT: Xt: trajectoire du processus gaussien stationnaire normalise (m=0, ect=1)
    # ----------------------------------
    vale_dsp = f_dsp.vale_y
    lw2 = f_dsp.vale_x
    DW = lw2[1] - lw2[0]
    nbfreq2 = len(lw2)
    nbfreq = nbfreq2 * 2
    if data_cohe["TYPE"] == "COEF_CORR":
        cohec = data_cohe["MAT_COHE"]
        dim = cohec.shape[0]
    else:
        liste_nom, l2 = get_group_nom_coord(data_cohe["GROUP_NO_INTERF"], data_cohe["MAILLAGE"])
        dim = len(liste_nom)
    CS = NP.array([0.0 + 0j] * dim * nbfreq)
    CS.resize(nbfreq, dim)
    Xt = NP.array([0.0] * dim * nbfreq)
    Xt.resize(dim, nbfreq)

    if rv is None:
        vecc1 = NP.random.normal(0.0, 1.0, nbfreq2 * dim) + 1j * NP.random.normal(
            0.0, 1.0, nbfreq2 * dim
        )
        vecc2 = NP.random.normal(0.0, 1.0, nbfreq2 * dim) + 1j * NP.random.normal(
            0.0, 1.0, nbfreq2 * dim
        )
        vecc1.resize(dim, nbfreq2)
        vecc2.resize(dim, nbfreq2)
    elif rv is not None:
        rva = NP.array(rv)
        vecc1 = rva[:, :nbfreq2]
        vecc2 = rva[:, nbfreq2:]

    for iifr in range(nbfreq2):
        if data_cohe["TYPE"] != "COEF_CORR":
            cohec = CALC_COHE(lw2[iifr], **data_cohe)
            # --- Platform-independent coherency factorization: begin ---
            # Use the unique symmetric square root
            sqrt_cohec = _symmetric_psd_sqrt(cohec)
            dsp_scale = sqrt(vale_dsp[iifr])
            vale_xp = dsp_scale * NP.dot(sqrt_cohec, vecc1[:, iifr])
            vale_xn = dsp_scale * NP.dot(sqrt_cohec, vecc2[:, iifr])
            # --- Platform-independent coherency factorization: end ---
        else:
            dsps = sqrt(vale_dsp[iifr]) * (cohec)
            vale_xp = NP.dot(dsps, vecc1[:, iifr])
            vale_xn = NP.dot(dsps, vecc2[:, iifr])
        CS[nbfreq2 + iifr] = vale_xp
        CS[nbfreq2 - iifr - 1] = vale_xn

    CS = NP.transpose(CS)
    SX = NP.fft.ifft(CS, nbfreq, 1) * nbfreq
    ha = NP.exp(-1.0j * pi * NP.arange(nbfreq) * (1.0 - 1.0 / nbfreq))
    for kkk in range(dim):
        Xt[kkk] = sqrt(DW) * (SX[kkk] * ha).real
    return Xt.tolist()


# --------------------------------------------------------------------------
#  ALGORITHME DE GENERATION DE SIGNAUX GAUSSIENS DSP evolutive non separable
# ---------------------------------------------------------------------------
def gene_traj_gauss_evol_ND(self, data_cohe, rv=None, **kwargs):
    # ---------------------------------------------
    # IN: calc_dsp_KT: function for the definition of the PSD matrix (KT ou rational type)
    #      lw2: the list of frequencies corresponding to spec (0, OM)
    #      wg, wn: fond freq and evolution [rad/s],
    #      fcp [Hz]: corner frequency for Clough & Penzien filter
    # OUT: Xt: trajectoire du processus gaussien stationnaire normalise (m=0, ect=1)
    # ---------------------------------------------
    nbfreq2 = len(self.sampler.liste_w2)
    nbfreq = 2 * nbfreq2
    DW = self.sampler.DW
    fg = kwargs["FREQ_FOND"]
    amo = kwargs["AMORT"]
    fp = kwargs["FREQ_PENTE"]
    TYPE = kwargs["TYPE_DSP"]

    if data_cohe["TYPE"] == "COEF_CORR":
        cohec = data_cohe["MAT_COHE"]
    else:
        cohec = CALC_COHE(DW * 10.0, **data_cohe)
        with disable_fpe():
            Mat_cohe = NP.linalg.cholesky(cohec)

    dim = cohec.shape[0]
    Xt = NP.array([0.0] * dim * nbfreq)
    Xt.resize(dim, nbfreq)

    if TYPE == "FR":
        R0 = kwargs["para_R0"]
        R2 = kwargs["para_R2"]
        l_FIT = kwargs["fonc_FIT"].vale_y
        assert len(l_FIT) == nbfreq2, "ERREUR listes frequences: emettre une fiche anomalie!"
        dsp_fr_refe = calc_dsp_FR(self.sampler.liste_w2, fg, amo, R0, R2, self.FREQ_CORNER)
        #   calcul de la variance (sigma^2) de normalisation mof
        if "ALEA_DSP" in kwargs:
            l_ALPHA = kwargs["ALEA_DSP"]
            mof = NP.trapezoid(dsp_fr_refe * l_FIT * l_ALPHA, self.sampler.liste_w2) * 2.0
            l_FIT = l_FIT * l_ALPHA
        else:
            mof = NP.trapezoid(dsp_fr_refe * l_FIT, self.sampler.liste_w2) * 2.0
    if rv is None:
        #        rv = NP.random.normal(0.0, 1., nbfreq) + \
        #            1j * NP.random.normal(0.0, 1., nbfreq)
        vecc1 = NP.random.normal(0.0, 1.0, nbfreq2 * dim) + 1j * NP.random.normal(
            0.0, 1.0, nbfreq2 * dim
        )
        vecc2 = NP.random.normal(0.0, 1.0, nbfreq2 * dim) + 1j * NP.random.normal(
            0.0, 1.0, nbfreq2 * dim
        )
        vecc1.resize(dim, nbfreq2)
        vecc2.resize(dim, nbfreq2)
    else:
        rva = NP.array(rv)
        vecc1 = rva[:, 0:nbfreq2]
        vecc2 = rva[:, nbfreq2:]
    t_mid = 0.5 * (self.modulator.T1 + self.modulator.T2)
    fg_fin = fg + fp * (self.modulator.T2 - t_mid)
    fg_ini = fg + fp * (self.modulator.T1 - t_mid)

    for nii, tii in enumerate(self.sampler.liste_temps):
        if tii < self.modulator.T1:
            fgt = fg_ini
        elif tii > self.modulator.T2:
            fgt = fg_fin
        else:
            fgt = fg + fp * (tii - t_mid)
        if fgt <= 0.0:
            UTMESS("F", "SEISME_35", valk=(str(tii)))
        # calcul du facteur de normalisation
        if TYPE == "KT":
            dsp = calc_dsp_KT(self, fgt, amo)
            # constante de normalisation pour que ecart_type=1 a pour tout t
            S_cst = 1.0 / NP.trapezoid(dsp, self.sampler.liste_w2) * 0.5
            vale_dsp = calc_dsp_KT(self, fgt, amo, S_cst)
        elif TYPE == "FR":
            dsp = calc_dsp_FR(self.sampler.liste_w2, fgt, amo, R0, R2, self.FREQ_CORNER)
            # constante de normalisation pour que ecart_type=1 a pour tout t
            S_cst = mof / (NP.trapezoid(dsp * l_FIT, self.sampler.liste_w2) * 2.0)
            vale_dsp = (
                calc_dsp_FR(self.sampler.liste_w2, fgt, amo, R0, R2, self.FREQ_CORNER, So=S_cst)
                * l_FIT
            )

        vsin = 1.0j * NP.sin(self.sampler.liste_w2 * tii)
        vcos = NP.cos(self.sampler.liste_w2 * tii)
        vale_x = []
        for vdim in range(dim):
            vale_x.append(
                sum(
                    NP.sqrt(vale_dsp) * vecc1[vdim] * (vcos + vsin)
                    + NP.sqrt(vale_dsp) * vecc2[vdim] * (vcos - vsin)
                )
            )
        vale_Xt = NP.dot(cohec, vale_x)
        Xt[:, nii] = NP.real(vale_Xt) * sqrt(DW)
    return Xt.tolist()


def itersimcor_SRO(self, FONC_DSP, data_cohe, **SRO_args):
    # ---------------------------------------------
    # IN  : FONC_DSP: DSP [rad/s], FONC_SPEC: spectre cible [Hz],
    #    amort: amortissement sro,  meme disretisation
    #    type_mod: type de fonction de modulation     niter: nombre d'iterations,
    #    FMIN: fequence min pour fit et filtrage ("corner frequency" Hz)
    # OUT : f_out: accelerogramme apres iterations pour fitter au mieux le spectre cible
    # ---------------------------------------------
    #  dsp in
    FMIN = SRO_args["FMIN"]
    amort = SRO_args["AMORT"]
    dico_err = SRO_args["DICO_ERR"]
    NB_ITER = SRO_args["NB_ITER"]
    NB_TIRAGE = data_cohe["DIM"]
    # dsp initiale
    para_dsp = FONC_DSP.para
    freq_dsp = FONC_DSP.vale_x
    vale_dsp = FONC_DSP.vale_y
    nbfreq2 = len(freq_dsp)
    nbfreq = 2 * nbfreq2
    # sro cible
    freq_sro = freq_dsp / (2.0 * pi)
    vale_sro_ref = SRO_args["FONC_SPEC"].evalfonc(freq_sro).vale_y
    #  fonction de modulation
    hmod = self.modulator.fonc_modul.vale_y
    dt = self.sampler.DT

    #  FMIN pour le calcul de l'erreur relative
    FMINM = max(FMIN, 0.1)
    FC = max(self.FREQ_FILTRE, FMINM)
    N1 = NP.searchsorted(freq_sro, FMINM) + 1
    FRED = freq_sro[N1:]
    ZPA = vale_sro_ref[-1]
    vpsum = sum([err_listes[0] for err_listes in list(dico_err.values())])
    coef_ZPA = dico_err["ERRE_ZPA"][0] / vpsum
    coef_MAX = dico_err["ERRE_MAX"][0] / vpsum
    coef_RMS = dico_err["ERRE_RMS"][0] / vpsum
    rv = NP.random.normal(0.0, 1.0, nbfreq) + 1j * NP.random.normal(0.0, 1.0, nbfreq)
    list_rv = [rv]
    ntir = 1
    while ntir < NB_TIRAGE:
        rv = NP.random.normal(0.0, 1.0, nbfreq) + 1j * NP.random.normal(0.0, 1.0, nbfreq)
        list_rv.append(rv)
        ntir = ntir + 1

    #  INITIALISATION
    errmult = []
    l_dsp = [FONC_DSP]
    liste_valesro = []
    Xt = DSP2ACCE_ND(FONC_DSP, data_cohe, list_rv)
    for acce in Xt:
        acce = acce * hmod  # modulation
        if self.FREQ_FILTRE > 0.0:
            acce = acce_filtre_CP(acce, dt, self.FREQ_FILTRE)
        f_acce = t_fonction(self.sampler.liste_temps, acce, para=self.modulator.para_fonc_modul)
        f_sroi = ACCE2SROM(self, f_acce, amort, freq_sro, 2, SRO_args["METHODE_SRO"])
        liste_valesro.append(f_sroi.vale_y)

    if SRO_args["TYPE_ITER"] == "SPEC_MEDIANE":
        valesro = NP.median(NP.array(liste_valesro), axis=0)
    elif SRO_args["TYPE_ITER"] == "SPEC_MOYENNE":
        valesro = NP.mean(NP.array(liste_valesro), axis=0)

    l_sro = [valesro]
    err_zpa, err_max, err_min, err_rms, freq_err = erre_spectre(
        FRED, valesro[N1:], vale_sro_ref[N1:]
    )
    #  erreur multiobjectif
    err_ZPA = coef_ZPA * err_zpa
    err_MAX = coef_MAX * err_max
    err_RMS = coef_RMS * err_rms
    errmult.append(sqrt(1.0 / 3.0 * (err_ZPA**2 + err_MAX**2 + err_RMS**2)))
    if self.INFO == 2:
        UTMESS("I", "SEISME_43", valr=(err_zpa, err_max, err_rms, errmult[-1]))

    # ITERATIONS
    for kk in range(NB_ITER):
        #  CALCUL CORRECTION des DSP et mise a jour f_dsp
        nz = NP.nonzero(valesro)
        factm = NP.ones(nbfreq2)
        factm[nz] = vale_sro_ref[nz] / valesro[nz]
        vale_dspi = vale_dsp * factm**2
        #          vale_dsp[N1:]= vale_dspi[N1:]
        vale_dsp = vale_dspi
        f_dsp = t_fonction(freq_dsp, vale_dsp, para=para_dsp)
        f_dsp = dsp_filtre_CP(f_dsp, FC)
        l_dsp.append(f_dsp)

        #  ITERATION DSP ACCE

        liste_valesro = []
        Xt = DSP2ACCE_ND(f_dsp, data_cohe, list_rv)
        for acce in Xt:
            acce = acce * hmod  # modulation
            if self.FREQ_FILTRE > 0.0:
                acce = acce_filtre_CP(acce, dt, self.FREQ_FILTRE)
            f_acce = t_fonction(self.sampler.liste_temps, acce, para=self.modulator.para_fonc_modul)
            f_sroi = ACCE2SROM(self, f_acce, amort, freq_sro, 2, SRO_args["METHODE_SRO"])
            liste_valesro.append(f_sroi.vale_y)
        if SRO_args["TYPE_ITER"] == "SPEC_MEDIANE":
            valesro = NP.median(NP.array(liste_valesro), axis=0)
        elif SRO_args["TYPE_ITER"] == "SPEC_MOYENNE":
            valesro = NP.mean(NP.array(liste_valesro), axis=0)

        #  CALCUL DES ERREURS
        l_sro.append(valesro)
        err_zpa, err_max, err_min, err_rms, freq_err = erre_spectre(
            FRED, valesro[N1:], vale_sro_ref[N1:]
        )
        #         print 'err_zpa, err_max,  err_RMS:', err_zpa, err_max, err_rms
        #  erreur multionjectif
        err_ZPA = coef_ZPA * err_zpa
        err_MAX = coef_MAX * err_max
        err_RMS = coef_RMS * err_rms
        errmult.append(sqrt(1.0 / 3.0 * (err_ZPA**2 + err_MAX**2 + err_RMS**2)))
        if self.INFO == 2:
            UTMESS("I", "SEISME_42", vali=(kk + 1, NB_ITER), valr=errmult[-1])
    # OPTIMUM
    ind_opt = NP.argmin(NP.array(errmult))
    f_dsp_opt = l_dsp[ind_opt]
    valesro_opt = l_sro[ind_opt]
    err_zpa, err_max, err_min, err_rms, freq_err = erre_spectre(
        FRED, valesro_opt[N1:], vale_sro_ref[N1:]
    )
    dico_err["ERRE_ZPA"].append(err_zpa)
    dico_err["ERRE_MAX"].append(err_max)
    dico_err["ERRE_RMS"].append(err_rms)
    if self.INFO == 2:
        valargs = _F(
            vali=ind_opt,
            valr=(errmult[ind_opt], err_max, freq_err[0], err_min, freq_err[1], err_zpa, err_rms),
        )
        UTMESS("I", "SEISME_41", *valargs)
    for keys, listev in list(dico_err.items()):
        tole = listev[1] * 100.0
        erre = abs(listev[-1])
        if abs(erre) > tole:
            nbi = ind_opt
            UTMESS("A", "SEISME_36", vali=nbi, valk=keys, valr=(erre, tole))
    return f_dsp_opt, list_rv


# calcul de l'erreur
# ---------------------------------------------
def erre_spectre(Freq, valesro, vale_sro_ref):
    errlin = (valesro - vale_sro_ref) / vale_sro_ref * 100.0
    errzpa = errlin[-1]
    errmax = max(abs(errlin))
    errmin = min(errlin)
    errms = sqrt(1.0 / len(Freq) * NP.sum(errlin**2))
    freqerr = [Freq[NP.argmax(abs(errlin))], Freq[NP.argmin((errlin))]]
    return errzpa, errmax, errmin, errms, freqerr


def itersimcortir_SRO(self, FONC_DSP, data_cohe, NB_TIR, **SRO_args):
    # ---------------------------------------------
    # IN  : FONC_DSP: DSP [rad/s], FONC_SPEC: spectre cible [Hz],
    #    amort: amortissement sro,  meme disretisation
    #    type_mod: type de fonction de modulation     niter: nombre d'iterations,
    #    FMIN: fequence min pour fit et filtrage ("corner frequency" Hz)
    # OUT : f_out: accelerogramme apres iterations pour fitter au mieux le spectre cible
    # ---------------------------------------------
    #  dsp in
    FMIN = SRO_args["FMIN"]
    amort = SRO_args["AMORT"]
    dico_err = SRO_args["DICO_ERR"]
    NB_ITER = SRO_args["NB_ITER"]
    dim = data_cohe["DIM"]
    # dsp initiale
    para_dsp = FONC_DSP.para
    freq_dsp = FONC_DSP.vale_x
    vale_dsp = FONC_DSP.vale_y
    nbfreq2 = len(freq_dsp)
    nbfreq = 2 * nbfreq2
    # sro cible
    freq_sro = freq_dsp / (2.0 * pi)
    vale_sro_ref = SRO_args["FONC_SPEC"].evalfonc(freq_sro).vale_y
    #  fonction de modulation
    hmod = self.modulator.fonc_modul.vale_y
    dt = self.sampler.DT

    #  FMIN pour le calcul de l'erreur relative
    FMINM = max(FMIN, 0.1)
    FC = max(self.FREQ_FILTRE, FMINM)
    N1 = NP.searchsorted(freq_sro, FMINM) + 1
    FRED = freq_sro[N1:]
    ZPA = vale_sro_ref[-1]
    vpsum = sum([err_listes[0] for err_listes in list(dico_err.values())])
    coef_ZPA = dico_err["ERRE_ZPA"][0] / vpsum
    coef_MAX = dico_err["ERRE_MAX"][0] / vpsum
    coef_RMS = dico_err["ERRE_RMS"][0] / vpsum

    #   rv = NP.random.normal(0.0, 1., nbfreq) + \
    #       1j * NP.random.normal(0.0, 1., nbfreq)
    list_rv = []
    ntir = 0
    while ntir < NB_TIR:
        rv = []
        for kk in range(dim):
            rv.append(NP.random.normal(0.0, 1.0, nbfreq) + 1j * NP.random.normal(0.0, 1.0, nbfreq))
        list_rv.append(rv)
        ntir = ntir + 1
    #  INITIALISATION
    errmult = []
    l_dsp = [FONC_DSP]
    liste_valesro = []
    liste_Xt = []
    for nbtir in range(NB_TIR):
        Xt = DSP2ACCE_ND(FONC_DSP, data_cohe, list_rv[nbtir])
        liste_Xt.extend(Xt)
    for acce in liste_Xt:
        acce = acce * hmod  # modulation
        if self.FREQ_FILTRE > 0.0:
            acce = acce_filtre_CP(acce, dt, self.FREQ_FILTRE)
        f_acce = t_fonction(self.sampler.liste_temps, acce, para=self.modulator.para_fonc_modul)
        f_sroi = ACCE2SROM(self, f_acce, amort, freq_sro, 2, SRO_args["METHODE_SRO"])
        liste_valesro.append(f_sroi.vale_y)
    if SRO_args["TYPE_ITER"] == "SPEC_MEDIANE":
        valesro = NP.median(NP.array(liste_valesro), axis=0)
    elif SRO_args["TYPE_ITER"] == "SPEC_MOYENNE":
        valesro = NP.mean(NP.array(liste_valesro), axis=0)
    l_sro = [valesro]
    err_zpa, err_max, err_min, err_rms, freq_err = erre_spectre(
        FRED, valesro[N1:], vale_sro_ref[N1:]
    )
    #  erreur multiobjectif
    err_ZPA = coef_ZPA * err_zpa
    err_MAX = coef_MAX * err_max
    err_RMS = coef_RMS * err_rms
    errmult.append(sqrt(1.0 / 3.0 * (err_ZPA**2 + err_MAX**2 + err_RMS**2)))
    if self.INFO == 2:
        UTMESS("I", "SEISME_43", valr=(err_zpa, err_max, err_rms, errmult[-1]))

    # ITERATIONS
    for kk in range(NB_ITER):
        #  CALCUL CORRECTION des DSP et mise a jour f_dsp
        nz = NP.nonzero(valesro)
        factm = NP.ones(nbfreq2)
        factm[nz] = vale_sro_ref[nz] / valesro[nz]
        vale_dspi = vale_dsp * factm**2
        #          vale_dsp[N1:]= vale_dspi[N1:]
        vale_dsp = vale_dspi
        f_dsp = t_fonction(freq_dsp, vale_dsp, para=para_dsp)
        f_dsp = dsp_filtre_CP(f_dsp, FC)
        l_dsp.append(f_dsp)

        #  ITERATION DSP ACCE

        liste_valesro = []
        liste_Xt = []
        for nbtir in range(NB_TIR):
            Xt = DSP2ACCE_ND(f_dsp, data_cohe, list_rv[nbtir])
            liste_Xt.extend(Xt)
        for acce in liste_Xt:
            acce = acce * hmod  # modulation
            if self.FREQ_FILTRE > 0.0:
                acce = acce_filtre_CP(acce, dt, self.FREQ_FILTRE)
            f_acce = t_fonction(self.sampler.liste_temps, acce, para=self.modulator.para_fonc_modul)
            f_sroi = ACCE2SROM(self, f_acce, amort, freq_sro, 2, SRO_args["METHODE_SRO"])
            liste_valesro.append(f_sroi.vale_y)
        if SRO_args["TYPE_ITER"] == "SPEC_MEDIANE":
            valesro = NP.median(NP.array(liste_valesro), axis=0)
        elif SRO_args["TYPE_ITER"] == "SPEC_MOYENNE":
            valesro = NP.mean(NP.array(liste_valesro), axis=0)
        #  CALCUL DES ERREURS
        l_sro.append(valesro)
        err_zpa, err_max, err_min, err_rms, freq_err = erre_spectre(
            FRED, valesro[N1:], vale_sro_ref[N1:]
        )
        #  erreur multionjectif
        err_ZPA = coef_ZPA * err_zpa
        err_MAX = coef_MAX * err_max
        err_RMS = coef_RMS * err_rms
        errmult.append(sqrt(1.0 / 3.0 * (err_ZPA**2 + err_MAX**2 + err_RMS**2)))
        if self.INFO == 2:
            UTMESS("I", "SEISME_42", vali=(kk + 1, NB_ITER), valr=errmult[-1])
    # OPTIMUM
    ind_opt = NP.argmin(NP.array(errmult))
    f_dsp_opt = l_dsp[ind_opt]
    valesro_opt = l_sro[ind_opt]
    err_zpa, err_max, err_min, err_rms, freq_err = erre_spectre(
        FRED, valesro_opt[N1:], vale_sro_ref[N1:]
    )
    dico_err["ERRE_ZPA"].append(err_zpa)
    dico_err["ERRE_MAX"].append(err_max)
    dico_err["ERRE_RMS"].append(err_rms)
    if self.INFO == 2:
        valargs = _F(
            vali=ind_opt,
            valr=(errmult[ind_opt], err_max, freq_err[0], err_min, freq_err[1], err_zpa, err_rms),
        )
        UTMESS("I", "SEISME_41", **valargs)
    for keys, listev in list(dico_err.items()):
        tole = listev[1] * 100.0
        erre = abs(listev[-1])
        if abs(erre) > tole:
            nbi = ind_opt
            UTMESS("A", "SEISME_36", vali=nbi, valk=keys, valr=(erre, tole))
    return f_dsp_opt, list_rv
