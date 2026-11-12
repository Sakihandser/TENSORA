# coding: utf-8

# Copyright (C) 1991 - 2026 EDF www.code-aster.org
#
# This file is part of Code_Aster.
#
# Code_Aster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Code_Aster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Code_Aster.  If not, see <http://www.gnu.org/licenses/>.

from itertools import count, product
from math import sqrt

import numpy as np
from libaster import setFortranLoggingLevel

from ..Messages import UTMESS
from ..Objects import MultipleElasticResult


def get_nodes(mesh, group_no):
    """Get the number of nodes.

    Arguments:
        mesh: the mesh
        group_no (list[str]): list name of groups of nodes

    Returns:
        tuple: Tuple containing the list of number of nodes and the list of
        the nodes name for each group.
    """

    nodes_num = []
    nodes_name = []
    if group_no is not None:
        nodes_num = mesh.getNodes(group_no, localNumbering=True)
        nodes_name = [str(i + 1) for i in nodes_num]
    return nodes_num, nodes_name


def get_spectres(spectre_in):
    """Get input form key_factor SPECTRE
    Args:
         input of key_factor SPECTRE by users
    Returns:
        spectres (dict[str, list]): gives spectras for each direction as a list
    """
    spectres = {"X": [], "Y": [], "Z": []}
    for spectre in spectre_in:
        directions = spectre.get("LIST_AXE")
        for direction in directions:
            spectres[direction].append(
                {
                    "direction": direction,
                    "nappe": spectre.get("SPEC_OSCI"),
                    "coefficient": spectre.get("ECHELLE"),
                    "corr_freq": spectre.get("CORR_FREQ"),
                    "nature": spectre.get("NATURE"),
                    "nom_appui": spectre.get("NOM_APPUI"),
                }
            )
    return spectres


def get_depl_mult_appui(depl_mult_appui):
    """Get input from key_factor DEPL_MULT_APPUI
    Args:
         input of key_factor DEPL_MULT_APPUI by users
    Returns:
        depl_mult_appuis (dict[str, dict]): gives property for each appui as a dict
    """
    depl_mult_appuis = {}
    if depl_mult_appui is None:
        return depl_mult_appuis
    # for each nom_appui, get information about DDS
    for mult_appui in depl_mult_appui:
        directions = []
        nom_appui = mult_appui.get("NOM_APPUI")
        depl_mult_appuis[nom_appui] = {}
        depl_mult_appuis[nom_appui]["mode_stat"] = mult_appui.get("MODE_STAT")
        depl_mult_appuis[nom_appui]["group_no_refe"] = mult_appui.get("GROUP_NO_REFE")
        depl_mult_appuis[nom_appui]["X"] = mult_appui.get("DX")
        depl_mult_appuis[nom_appui]["Y"] = mult_appui.get("DY")
        depl_mult_appuis[nom_appui]["Z"] = mult_appui.get("DZ")
        assert any(
            depl_mult_appuis[nom_appui][direction] is not None for direction in ("X", "Y", "Z")
        )

    return depl_mult_appuis


def get_appuis(appuis_in, mesh):
    """Get the input for APPUIS in case of Multi Appui

    Arguments:
        appuis_in: input for key_factor APPUIS

    Returns:
        appuis (dict[str, dict]): gives property for each appui as a dict
    """
    appuis = {}
    for appui in appuis_in:
        nom_appui = appui.get("NOM")
        groups = appui.get("GROUP_NO")
        appuis[nom_appui] = {}
        nodes, nodes_name = get_nodes(mesh, groups)
        appuis[nom_appui]["groups"] = groups
        appuis[nom_appui]["nodes"] = nodes
        appuis[nom_appui]["nodes_name"] = nodes_name

    # check if one node belonging to two APPUIS
    all_nodes = []
    for appui in appuis.values():
        all_nodes += appui["nodes"]
    if len(all_nodes) != len(set(all_nodes)):
        UTMESS("F", "SEISME_60")

    return appuis


def get_group_appuis(spectres, group_appui_correle=None):
    """Get information about group_appuis

    Arguments:
        spectres: input of operande SPECTRE
        group_appui_correle: input for operande GROUP_APPUI_CORRELE

    Returns:
        group_appuis (dict[str, list]): groups of appuis
    """
    # preparing for group_appui_correle
    group_appuis = {}
    all_nom_appuis = set()
    for spectres in spectres.values():
        all_nom_appuis.update([spectre["nom_appui"] for spectre in spectres])
    all_nom_appuis = list(all_nom_appuis)
    # add group_appui by users
    if group_appui_correle:
        # get information of input for GROUP_APPUI_CORRELE
        for group_appui in group_appui_correle:
            # add APPUIS to group_appui
            list_appuis = group_appui.get("LIST_APPUI")
            nom = group_appui.get("NOM")
            all_appui = group_appui.get("TOUT") == "OUI"
            if list_appuis:
                group_appuis[nom] = list_appuis
            elif all_appui:
                group_appuis["ALL"] = all_nom_appuis
        # all APPUIS not mentionned will be regrouped in separed groupe named as nom_appui
        remaining_appuis = []
        for nom_appui in all_nom_appuis:
            if all(nom_appui not in group for group in group_appuis.values()):
                remaining_appuis.append(nom_appui)
        if remaining_appuis:
            group_appuis["nom_appui"] = remaining_appuis
    else:
        # comb_mult_appui_corr is not mentionned --> all appuis are in the same group_appui_correle
        group_appuis["ALL"] = all_nom_appuis
    return group_appuis


def filter_ordre_freq(list_para, increment):
    """Filter the order of mode from mode_meca

    Arguments:
        list_para    : list_para from modal basis
        increment    : increment keyword

    Returns:
        freqs (ndarray): ordered list of filtered frequencies
        nume_ordres (ndarray): ordered list of filtered number order
        nume_modes (ndarray): ordered list of filtered number mode
        gene_masses (ndarray): ordered list of masse gene
    """
    l_nume_ordre = list_para["NUME_ORDRE"]
    l_freq = list_para["FREQ"]
    l_nume_mode = list_para["NUME_MODE"]
    l_gene_masses = list_para["MASS_GENE"]

    tout_ordre = increment.get("TOUT_ORDRE")
    list_ordre = increment.get("LIST_ORDRE")
    nume_mode = increment.get("NUME_MODE")
    nume_ordre = increment.get("NUME_ORDRE")
    list_freq = increment.get("LIST_FREQ")
    freq = increment.get("FREQ")
    precision = increment.get("PRECISION")
    critere = increment.get("CRITERE")

    # Gerer le cas où TOUT_ORDRE est la valeur par default si tout est à None
    if all(key is None for key in (tout_ordre, nume_ordre, freq, nume_mode, list_freq, list_ordre)):
        tout_ordre = "OUI"
    # all modes in modal basis are selected
    if tout_ordre == "OUI":
        l_nume_ordre_filtered = l_nume_ordre
        l_freq_filtered = l_freq
        l_nume_mode_filtered = l_nume_mode
    else:
        # selecting mode by nume_mode
        nume_mode = nume_mode if nume_mode is not None else []
        # selecting mode by nume_ordre
        nume_ordre = nume_ordre if nume_ordre is not None else []
        # selecting mode by list of nume_ordre
        if list_ordre is not None:
            nume_ordre = list_ordre.getValues()
        # selecting mode by list of frequencies
        elif list_freq is not None:
            freq = list_freq.getValues()
        # filtering frequencies
        if freq is not None:
            freqs = np.array(freq)
            if critere == "RELATIF":
                borne_inf, borne_sup = freqs * (1 - precision), freqs * (1 + precision)
            else:
                borne_inf, borne_sup = freqs - precision, freqs + precision
        else:
            borne_inf, borne_sup = -1, -1
        # filtered order modes
        l_nume_ordre_filtered, l_freq_filtered, l_nume_mode_filtered = [], [], []
        # Filtration des ordres
        for i_ordre, f, i_mode in zip(l_nume_ordre, l_freq, l_nume_mode):
            is_in_interval = np.any((borne_inf <= f) & (f <= borne_sup))
            if i_ordre in nume_ordre or i_mode in nume_mode or is_in_interval:
                l_nume_ordre_filtered.append(i_ordre)
                l_freq_filtered.append(f)
                l_nume_mode_filtered.append(i_mode)

    # Sort outputs in frequency increasing order
    _, _, argsort_freq = zip(*sorted(zip(l_freq_filtered, l_nume_ordre_filtered, count())))
    argsort_freq = list(argsort_freq)
    freqs = np.array(l_freq_filtered)[argsort_freq]
    nume_ordres = np.array(l_nume_ordre_filtered)[argsort_freq]
    nume_modes = np.array(l_nume_mode_filtered)[argsort_freq]
    gene_masses = np.array(l_gene_masses)[argsort_freq]

    return freqs, nume_ordres, nume_modes, gene_masses


def get_amor_reduit(list_para, nume_ordres, amor_reduit, list_amor, amor_gene):
    """Compute array of modal damping for each mode

    Arguments:
        list_para: list para of mode_meca
        nume_ordres: list of orders for which the dampings must be calculated
        amor_reduit: list of damping coefficient, user input
        list_amor : list of damping coefficients, user input
        amor_gene : generalized damping matrix, user input

    Returns:
        amors (ndarray): list of damping coefficients
    """
    # get values of damping coefficient
    if list_amor is not None:
        # get values of damping in list_amor
        amor_reduit = list_amor.getValues()
    elif amor_gene is not None:
        # List of parameters in mode_meca
        # computing damping coefficient from generalized damping matrix
        amors = amor_gene.getUpperValues()
        freqs = list_para["FREQ"]
        ordres = list_para["NUME_ORDRE"]
        masses = list_para["MASS_GENE"]
        amor_reduit = []
        for ordre in nume_ordres:
            idx = ordres.index(ordre)
            amor_reduit.append(amors[idx] / (4 * np.pi * freqs[idx] * masses[idx]))

    # if number of damping coefficient is less than modes to combine
    # add last value of damping coefficient to complete the damping vector
    nb_modes = len(nume_ordres)
    amors = np.array(list(amor_reduit) + [amor_reduit[-1]] * (nb_modes - len(amor_reduit)))

    return amors


class CombModalResponse:
    """Manage how to combine modals responses according to strategy defined by user

    Args:
        comb_mode (dict): input for key_factor COMB_MODE
        type_analyse (str): input for key TYPE_ANALYSE (MONO_APPUI or MULT_APPUI)
        amors (list[float]): list of all damping coefficients
        freqs (list[float]): list of all frequencies
    """

    def __init__(self, comb_mode, type_analyse, amors, freqs):
        self._type_comb = comb_mode["TYPE"]
        self._amors = amors
        self._freqs = freqs
        self._H = None

        if self._type_comb == "GUPTA":
            if type_analyse != "MONO_APPUI":
                UTMESS("F", "SEISME_58")
            self._freq1, self._freq2 = comb_mode["FREQ_1"], comb_mode["FREQ_2"]
            if self._freq1 > self._freq2:
                UTMESS("F", "SEISME_59")
            self._alpha_r = None

        elif self._type_comb in ("DSC", "NRC_DSA"):
            self._duree = comb_mode["DUREE"]
            assert self._duree is not None

        elif self._type_comb == "NRC_GROUPING":
            self._groups = None

    @staticmethod
    def cqc_array(amors, freqs):
        """Matrix des coefficients CQC

        Arguments:
            amors           : list of damping coefficients
            freqs           : list of frequencies

        Returns:
            H (ndarray): matrix of correlation between modes for CQC rule
        """
        nbmode = len(freqs)
        H = np.zeros((nbmode, nbmode))
        if np.any(amors == 0):
            H[np.diag_indices_from(H)] = 1
            return H
        omega = 2 * np.pi * freqs
        for i, (amor_i, w_i) in enumerate(zip(amors, omega)):
            for j, (amor_j, w_j) in enumerate(zip(amors, omega)):
                wij = w_i * w_j
                amor_ij = amor_i * amor_j
                H[i, j] = (8 * sqrt(amor_ij * wij) * (amor_i * w_i + amor_j * w_j) * wij) / (
                    (w_i**2 - w_j**2) ** 2
                    + 4 * amor_ij * wij * (w_i**2 + w_j**2)
                    + 4 * (amor_i**2 + amor_j**2) * wij**2
                )
        # return
        return H

    @staticmethod
    def dsc_array(amors, freqs, s):
        """Matrix des coefficients DSC

        Arguments:
            amors           : list of damping coefficients
            freqs           : list of frequencies
            s               : duration in second

        Returns:
            H (ndarray): matrix of correlation between modes for DSC rule
        """
        if np.any(amors == 0) or np.any(amors > 1):
            UTMESS("F", "SEISME_61")
        nbmode = len(freqs)
        H = np.zeros((nbmode, nbmode))
        omega = 2 * np.pi * freqs
        # correlation coefficients for DSC rule
        for i, (amor_i, w_i) in enumerate(zip(amors, omega)):
            for j, (amor_j, w_j) in enumerate(zip(amors, omega)):
                H[i, j] = 1 / (
                    1
                    + (w_i * sqrt(1 - amor_i**2) - w_j * sqrt(1 - amor_j**2)) ** 2
                    / (w_i * (amor_i + 2 / (s * w_i)) + w_j * (amor_j + 2 / (s * w_j))) ** 2
                )
        # return
        return H

    @staticmethod
    def nrc_ten_percent_array(freqs):
        """Matrix des coefficients DPC (selon NRC_TEN_PERCENT)

        Arguments:
            freqs           : list of frequencies

        Returns:
            H (ndarray): matrix of correlation between modes for NRC_TEN_PERCENT rule
        """

        nbmode = len(freqs)
        H = np.zeros((nbmode, nbmode))
        # correlation coefficients for DSC rule
        # using round() to invoid approximated values of frequencies
        for i in range(nbmode):
            for j in range(nbmode):
                if freqs[i] <= freqs[j]:
                    if freqs[j] <= round(1.1 * freqs[i], 5):
                        H[i, j] = 1
                else:
                    if freqs[i] <= round(1.1 * freqs[j], 5):
                        H[i, j] = 1
        # return
        return H

    @property
    def alpha_r(self):
        """Quasi-static factor"""
        if self._alpha_r is None:
            self._alpha_r = np.expand_dims(
                np.log(self._freqs / self._freq1) / np.log(self._freq2 / self._freq1), axis=1
            )
            self._alpha_r[self._freqs < self._freq1] = 0
            self._alpha_r[self._freqs > self._freq2] = 1
        return self._alpha_r

    @property
    def H(self):
        """Matrix of correlation"""
        if self._H is None:
            if self._type_comb in ("CQC", "GUPTA", "CQC_SIGNE"):
                self._H = self.cqc_array(self._amors, self._freqs)
                if self._type_comb == "GUPTA":
                    coeff_p = np.sqrt(1 - self.alpha_r**2)
                    self._H = self._H * coeff_p.T * coeff_p
            elif self._type_comb in ("DSC", "NRC_DSA"):
                self._H = self.dsc_array(self._amors, self._freqs, self._duree)
            elif self._type_comb == "NRC_TEN_PERCENT":
                self._H = self.nrc_ten_percent_array(self._freqs)
            self._H[np.diag_indices_from(self._H)] /= 2
        return self._H

    @property
    def groups(self):
        """
        Create the modal group list by analyzing the frequencies
        **bottom-up** as required by RG 1.92 Rev.1
        """
        if self._groups is None:
            self._groups = []
            for fidx, ff in enumerate(self._freqs):
                if fidx == 0:
                    # Initialize first group with the first mode
                    self._groups.append([fidx])
                    continue
                # "Current" group reference frequency
                ff_ref = self._freqs[self._groups[-1][0]]
                #
                if (ff - ff_ref) / ff_ref > 0.1:
                    # Start a new group if the 10% is exceeded
                    self._groups.append([fidx])
                else:
                    # Else, just append the mode index to the preceding group
                    self._groups[-1].append(fidx)
        return self._groups

    def get(self, R_mi):
        """
        Args:
            R_mi (ndarray): list of all vectors corresponding to all modal responses (mode by mode)

        Returns:
            R_m2 (ndarray): dynamic combined response of all oscillators in square
            R_qs (ndarray): quasi-statique combined response (for Gupta rule only)
        """

        if self._type_comb == "SRSS":
            R_m2 = np.sum(R_mi**2, axis=0)
        elif self._type_comb == "ABS":
            R_m2 = np.sum(np.abs(R_mi), axis=0) ** 2
        elif self._type_comb in ("CQC", "DSC", "GUPTA", "CQC_SIGNE"):
            H = self.H
            R_m2 = 0
            for i, r_i in enumerate(R_mi):
                for j, r_j in enumerate(R_mi[i:], i):
                    R_m2 += 2 * H[i, j] * r_i * r_j
            R_m2 = np.maximum(R_m2, 0)
        elif self._type_comb in ("NRC_DSA", "NRC_TEN_PERCENT"):
            H = self.H
            R_m2 = 0
            for i, r_i in enumerate(R_mi):
                for j, r_j in enumerate(R_mi[i:], i):
                    R_m2 += 2 * H[i, j] * np.abs(r_i * r_j)
            R_m2 = np.maximum(R_m2, 0)
        elif self._type_comb == "DPC":
            # neighbor modes (frequence close until 10%) will be combined by abs
            f0, r_r = self._freqs[0], R_mi[0]
            l_abs_R_r = [np.abs(r_r)]
            for i_freq in range(1, len(self._freqs)):
                freq = self._freqs[i_freq]
                r_r = R_mi[i_freq]
                fm_ = 0.5 * (f0 + freq)
                if abs(freq - f0) / fm_ >= 0.10:  # discrepance in freq bigger than 10%
                    f0 = freq
                    l_abs_R_r.append(np.abs(r_r))
                else:  # # discrepance in freq bigger than 10% --> sum by abs
                    f0 = freq
                    # combinied by abs value
                    l_abs_R_r[-1] += np.abs(r_r)
            return sum(r_x**2 for r_x in l_abs_R_r), 0

        elif self._type_comb == "NRC_GROUPING":
            # The regular Squared-Sum contribution (no correlation part)
            sum_rk_sq = np.sum(R_mi**2, axis=0)
            # The correlated part
            sum_rl_rm = np.zeros_like(sum_rk_sq)
            for group in self.groups:
                nbmodes = len(group)
                if nbmodes == 1:
                    continue
                for ii in range(0, nbmodes - 1):
                    rl = R_mi[group[ii]]
                    for jj in range(ii + 1, nbmodes):
                        rm = R_mi[group[jj]]
                        sum_rl_rm += 2.0 * np.abs(rl * rm)

            R_m2 = sum_rk_sq + sum_rl_rm
        else:
            assert False

        if self._type_comb == "GUPTA":
            R_qs = np.sum(R_mi * self.alpha_r, axis=0)
        else:
            R_qs = np.zeros((np.shape(R_m2)))

        return R_m2, R_qs


class Resu:
    """
    Manage the MULT_ELAS output result: a facility to add fields
    Args:
        type_resu       : input of TYPE_RESU
        mode_meca       : input of MODE_MECA
        mesh            : the mesh
    """

    _response_by_type = {
        "VALE_QS": "PART_QS{}",
        "VALE_DIRE": "DIRE{}",
        "VALE_DDS": "PART_DDS{}",
        "VALE_INER": "PART_INER{}",
        "VALE_DYNA": "PART_DYNA{}",
        "VALE_TOTA": "TOTA{}",
    }
    _newmark_by_type = {
        "VALE_TOTA": "NEWM_{}",
        "VALE_DYNA": "DYNA_NEWN_{}",
        "VALE_INER": "INER_NEWM_{}",
        "VALE_DDS": "DDS_NEWM_{}",
        "VALE_QS": "QS_NEWM_{}",
    }

    def __init__(self, type_resu, mode_meca, mesh):
        self._type_resu = type_resu
        self._mode_meca = mode_meca
        self._mesh = mesh
        self._result = MultipleElasticResult()
        self._nbIndexes = 0
        self._field_by_option = {}

    def _incr_index(self):
        """resize sd result"""
        self._nbIndexes += 1
        self._result.resize(self._nbIndexes)

    def _setField(self, option, values, name):
        """Add field to result
        Args:
            option (str): field name
            values (ndarray): field values
            name (str) : access parameter name
        """
        field = self._copy_field(option)
        field.setValues(values)
        self._incr_index()
        self._result.setField(field, option, value=name, para="NOM_CAS")

    def _copy_field(self, option):
        """Create a working copy field for the given option by extracting it from mode_meca
        Args:
            option (str): field name to get from mode_meca
        Returns:
            field (field): the working copy field
        """
        field = self._field_by_option.get(option)
        if not field:
            if option in ("VITE", "ACCE_ABSOLU"):
                option2 = "DEPL"
            else:
                option2 = option
            field = self._mode_meca.getField(option2, 1).copy()
            self._field_by_option[option] = field
        return field

    def _get_type(self, vale_type):
        """Return type_resu corresponding to vale_type, if found in user input
        Args:
            vale_type (str): type of response
        Returns:
            type_resu (str): return type_resu
        """
        for type_resu in self._type_resu:
            if type_resu.get("TYPE") == vale_type:
                return type_resu
        return None

    def add_dire_response(self, option, direction, R, vale_type):
        """Add directional response field in output result, if requested by user
        Args:
            option (str)   : name of field to be added
            direction (str): direction X, Y or Z
            R (ndarray)    : directional response
            vale_type (str): type of response
        """
        type_resu = self._get_type(vale_type)
        if type_resu is None:
            return

        list_axe = type_resu.get("LIST_AXE")
        if list_axe and direction in list_axe:
            self._setField(option, R, self._response_by_type[vale_type].format("_" + direction))

    def add_response(self, option, R, R_newmark_all, vale_type):
        """Add response field in output result, if requested by user
        Args:
            option (str)           : name of field to be added
            R (ndarray)            : response
            R_newmark_all (ndarray): response by NEWMARK
            vale_type (str)        : type of response
        """
        type_resu = self._get_type(vale_type)
        if type_resu is None:
            return

        self._setField(option, R, self._response_by_type[vale_type].format(""))
        if type_resu.get("NEWMARK") == "OUI":
            for i, r_newmark in enumerate(R_newmark_all):
                self._setField(option, r_newmark, self._newmark_by_type[vale_type].format(i + 1))

    def add_spectral_response(self, option, direction, R, nume_ordres_resu, appui=""):
        """Add spectral response (mono or multi appuis) in output result, if requested by user
        Args:
            option (str)              : name of field to be printed
            direction (str)           : direction X, Y or Z
            R (ndarray)               : spectral response
            nume_ordres_resu (ndarray): nume ordres corresponding to raws of R
            appui (str)               : name of support, to be given for MULTI_APPUI
        """
        type_resu = self._get_type("VALE_SPEC")
        if type_resu is None:
            return

        _, nume_ordres, _, _ = filter_ordre_freq(self._mode_meca.getParameters(), type_resu)
        list_axe = type_resu.get("LIST_AXE")
        list_appui = type_resu.get("LIST_APPUI")
        tout_appui = type_resu.get("TOUT_APPUI")
        nume_ordres_resu = nume_ordres_resu.tolist()
        if direction in list_axe and (not appui or tout_appui == "OUI" or appui in list_appui):
            for nume_ordre in nume_ordres:
                i_ordre = nume_ordres_resu.index(nume_ordre)
                self._setField(option, R[i_ordre], f"SPEC_{nume_ordre}{direction}{appui}")

    def get(self):
        """Update and return the result
        Returns:
            result (MultipleElasticResult): the result
        """
        model = self._mode_meca.getModel()
        if model:
            self._result.setModel(model)
        else:
            self._result.setMesh(self._mesh)
        cara_elem = self._mode_meca.getElementaryCharacteristics()
        if cara_elem:
            self._result.setElementaryCharacteristics(cara_elem)
        return self._result


class BaseRunner:
    """Runner base class containing common routines"""

    def __init__(self, mode_meca, option, nume_ordres, freqs, amors, freq_coup_in, mode_corr):
        self._mode_meca = mode_meca
        self._option = option
        self._nume_ordres = nume_ordres
        self._freqs = freqs
        self._amors = amors

        self._R_mi = {}
        self._R_x = {}  # list of directional total result
        self._part_d = {}  # list of directional result part dynamique
        self._part_s = {}  # list of directional result part pseudo-statique
        self._R_prim = {}  # list of RCCM part primaire
        # preparing for printing out to INFO
        self._SA = {}  # list of info about read spectra at eigen-frequencies by direction
        self._pseudo = {}  # list of info about correction by pseudo mode by direction

        # Cutting frequency
        if freq_coup_in is not None:
            self._freq_coup = freq_coup_in
        else:
            self._freq_coup = freqs[-1]
            if mode_corr == "OUI":
                UTMESS("A", "SEISME_95", valr=self._freq_coup)

        # step 1: Get eigen-vector to combine from mode_meca
        self._phis = self._get_phis(self._mode_meca, self._option, self._nume_ordres)
        self._directions = []

    @staticmethod
    def _comb_directions(type_comb_dir, l_R_x):
        """Combine directional responses according to the given type of combination

        Args:
            type_comb_dir (str): type of combination
            l_R_x (list): list of the directional responses

        Returns:
            R_xyz (ndarray): combined array
        """
        # ("lancer combi directionnelle")
        l_R_x = list(l_R_x)
        nb_direction = len(l_R_x)
        if nb_direction > 1:
            if type_comb_dir == "QUAD":
                R_xyz = np.sqrt(sum(r_x**2 for r_x in l_R_x))
                R_newmark_all = []

            elif type_comb_dir == "ABS":
                R_xyz = np.sum(np.abs(l_R_x), axis=0)
                R_newmark_all = []

            else:  # type_comb_dir == "NEWMARK":
                # 24/8/2 combinations if 3/2/1 directions :
                # R = [± EX  ± 0, 4 * EY  ± 0, 4 * EZ]
                # R = [± 0, 4 * EX  ± EY  ± 0, 4 * EZ]
                # R = [± 0, 4 * EX  ± 0, 4 * EY  ± EZ]
                newmark = np.zeros(len(l_R_x[0]))
                R_newmark_all = []

                def circular_shifts(p):
                    return [np.roll(p, -i) for i in range(len(p))]  # idem as in more_itertools

                for ijk in circular_shifts(range(nb_direction)):
                    r_xyz = [l_R_x[idx] for idx in ijk]
                    for exponents in product([0, 1], repeat=nb_direction):
                        comb_nk = sum(
                            (-1) ** expo * coef * r_x
                            for expo, coef, r_x in zip(exponents, [1, 0.4, 0.4], r_xyz)
                        )
                        newmark = np.maximum(newmark, comb_nk)
                        R_newmark_all.append(comb_nk)
                R_xyz = newmark
        elif nb_direction == 1:
            R_xyz = l_R_x[0]
            R_newmark_all = [R_xyz, -1.0 * R_xyz]
        # return
        return R_xyz, R_newmark_all

    @staticmethod
    def _get_phis(mode_meca, option, nume_ordres):
        """Get eigen-vector

        Args:
            mode_meca (mode_meca): modale basis
            option (str): fields to get, except for (VITE, ACCE_ABSOLU)
            nume_ordres (list[int)]): nume_ordre of feild to be gotten

        Returns:
            ndarray: phis
        """

        if option in ("VITE", "ACCE_ABSOLU"):
            option = "DEPL"

        if option not in mode_meca.getFieldsNames():
            UTMESS("F", "SEISME_62", valk=option)

        phis = np.array([])
        if all(nume_ordre in mode_meca.getIndexes() for nume_ordre in nume_ordres):
            phis = np.empty((len(nume_ordres), mode_meca.getField(option, nume_ordres[0]).size()))
            for i, imode in enumerate(nume_ordres):
                phis[i] = mode_meca.getField(option, imode).getValues()
        return phis

    @staticmethod
    def _get_signe_mode(mode_meca, option, signed_order):
        """Get sign of considered eigen-vector, for CQC_SIGNE method

        Args:
            mode_meca (mode_meca): modal basis
            option (str): fields to get, except for (VITE, ACCE_ABSOLU)
            signed_order (int): selected order number to sign the response

        Returns:
            ndarray: phis
        """

        if option in ("VITE", "ACCE_ABSOLU"):
            option = "DEPL"

        if option not in mode_meca.getFieldsNames():
            UTMESS("F", "SEISME_62", valk=option)

        modeValues = mode_meca.getField(option, signed_order).getValues()
        modal_sign = np.sign(modeValues)
        # Convention : sign(0) = 1.
        modal_sign[modal_sign == 0] = 1.0
        return modal_sign

    def _apply_signed_cqc(self, mode_sign, direction):
        """Apply CQC_SIGNE feature.

        Arguments:
            mode_sign (int): index of the signed eigen vector.
            indexes (list[int]): list of eigen vectors indexes

        Returns:
            ndarray: phis
        """
        l_params = self._mode_meca.getParameters()
        ordre_to_mode = {
            int(nume_ordre): int(nume_mode)
            for nume_ordre, nume_mode in zip(l_params["NUME_ORDRE"], l_params["NUME_MODE"])
        }
        nume_modes_retenus = np.asarray(
            [ordre_to_mode[int(nume_ordre)] for nume_ordre in self._nume_ordres], dtype=int
        )
        mode_to_order = {
            int(nume_mode): int(nume_ordre)
            for nume_mode, nume_ordre in zip(l_params["NUME_MODE"], l_params["NUME_ORDRE"])
        }
        if not mode_sign:
            UTMESS("F", "SEISME_93", valk=direction)
        if mode_sign not in nume_modes_retenus:
            l_modes = ", ".join(str(nume_mode) for nume_mode in nume_modes_retenus)
            UTMESS("F", "SEISME_99", valk=(direction, l_modes), vali=mode_sign)

        ordr_signe = mode_to_order[mode_sign]
        applied_signs = self._get_signe_mode(self._mode_meca, self._option, ordr_signe)
        return applied_signs

    def _s_r_freq_cut(self, spectre):
        """Value of ZPA at the cutting frequency

        Args:
            spectre : spectrum parameters

        Returns:
            s_r_freq_cut : value of ZPA at the cutting frequency
        """
        # ZPA at cut frequency
        s_r_freq_cut = spectre["nappe"](self._amors[-1], self._freq_coup) * spectre["coefficient"]
        # correction of spectrum if corr_freq is "OUI"
        if spectre["corr_freq"] == "OUI":
            s_r_freq_cut = s_r_freq_cut * np.sqrt(1 - self._amors[-1] ** 2)
        # nature of spectrum to ACCE spectrum
        if spectre["nature"] == "DEPL":
            s_r_freq_cut = ((2 * np.pi * self._freq_coup) ** 2) * s_r_freq_cut
        elif spectre["nature"] == "VITE":
            s_r_freq_cut = (2 * np.pi * self._freq_coup) * s_r_freq_cut
        return s_r_freq_cut

    def _corr_pseudo_mode(self, pr_wr2_phi, w_r, direction, pseudo_mode, s_r_freq_cut):
        """Correction by pseudo-mode/mode statique, for TYPE_ANALYSE = 'MONO_APPUI' and 'ENVELOPPE'

        Args:
            pr_wr2_phi (ndarray)    : sum of list of produit rho*phi/omega^2
            w_r (ndarray)           : list of omega = 2*pi*freq
            direction (str)         : X, Y or Z
            pseudo_mode (ModeResult): pseudo mode for static correction
            s_r_freq_cut (ndarray)  : value of ZPA at the cutting frequency

        Returns:
            R_c (ndarray): response by correction of pseudo-mode
        """

        # search for index (NUME_CMP) in MODE_STATIQUE corresponding to direction
        ps_noeud_cmp = pseudo_mode.getAccessParameters()["NOEUD_CMP"]
        ps_nume_mode = pseudo_mode.getAccessParameters()["NUME_MODE"]

        index_pseudo_mode = ps_nume_mode[ps_noeud_cmp.index(f"ACCE    {direction}")]
        if index_pseudo_mode is None:
            UTMESS("F", "SEISME_63", valk=direction)

        # get field in mode_statique
        if self._option == "VITE":  # on accepte que VITE = DEPL * omega (pseudo-vitesse relative)
            phi_ps = pseudo_mode.getField("DEPL", index_pseudo_mode).getValues()
            UTMESS("F", "SEISME_10", valk=self._option)
            # pseudo-mode
            R_c = (phi_ps * w_r - pr_wr2_phi) * s_r_freq_cut
        if self._option == "ACCE_ABSOLU":
            phi_ps = pseudo_mode.getField("DEPL", index_pseudo_mode).getValues()
            # this component is zero because this correction is automatic for mono-appui
            R_c = np.zeros(np.shape(phi_ps))
        else:
            phi_ps = pseudo_mode.getField(self._option, index_pseudo_mode).getValues()
            # pseudo-mode
            R_c = (phi_ps - pr_wr2_phi) * s_r_freq_cut

        return R_c

    def compute(
        self, comb_modal_response, spectres, mode_corr, pseudo_mode, d_fact_partici, comb_mode
    ):
        """Compute responses for TYPE_ANALYSE = 'MONO_APPUI' and 'ENVELOPPE'
        Args:
            comb_modal_response (CombModalResponse): instance to combine modals responses
            spectres (dict[str, list]): list of spectras, by direction
            mode_corr (str): static correction, user input
            pseudo_mode (ModeResult): pseudo modes, user input
            d_fact_partici (dict[str, ndarray]): given participation factors, by direction
            comb_mode (dict): input for key_factor COMB_MODE
        """

        # some checks
        if self._analyse == "MONO_APPUI":
            if max([len(spectres[direction]) for direction in ("X", "Y", "Z")]) > 1:
                UTMESS("F", "SEISME_64")
        elif self._analyse == "ENVELOPPE":
            natures = []
            corr_freqs = []
            for direction in ("X", "Y", "Z"):
                natures.extend([spectre["nature"] for spectre in spectres[direction]])
                corr_freqs.extend([spectre["corr_freq"] for spectre in spectres[direction]])
            if not all(nature == natures[0] for nature in natures):
                UTMESS("F", "SEISME_65", valk="NATURE")
            if not all(corr_freq == corr_freqs[0] for corr_freq in corr_freqs):
                UTMESS("F", "SEISME_65", valk="CORR_FREQ")
        else:
            assert False

        self._directions = [direction for direction in ("X", "Y", "Z") if spectres[direction]]
        for direction in self._directions:
            if self._analyse == "MONO_APPUI":
                spectre = spectres[direction][0]
                # Spectrale values at eigen-frequencies
                nappe = spectre["nappe"]
                coeff = spectre["coefficient"]
                S_r_freq = [
                    nappe(amor, freq) * coeff for amor, freq in zip(self._amors, self._freqs)
                ]

            elif self._analyse == "ENVELOPPE":
                # Spectrale values at eigen-frequencies
                S_r_freq = []
                for spectre in spectres[direction]:
                    nappe = spectre["nappe"]
                    coeff = spectre["coefficient"]
                    S_r_freq.append(
                        [nappe(amor, freq) * coeff for amor, freq in zip(self._amors, self._freqs)]
                    )
                S_r_freq = np.array(S_r_freq)
                S_r_freq = np.max(S_r_freq, axis=0)
                # envelope spectra at cutting frequency
                S_r_freq_cut = [
                    spectre["nappe"](self._amors[-1], self._freq_coup) * spectre["coefficient"]
                ]
                spectre = spectres[direction][S_r_freq_cut.index(max(S_r_freq_cut))]

            # eigen-pulsation before corr_freq
            w_r = 2 * np.pi * self._freqs

            # If correction
            if spectre["corr_freq"] == "OUI":
                correct = np.sqrt(1 - self._amors**2)
                w_r *= correct
                S_r_freq *= correct

            #  Correction of spectrum by nature of spectrum
            if spectre["nature"] == "DEPL":
                S_r_freq = ((2 * np.pi * self._freqs) ** 2) * S_r_freq
            elif spectre["nature"] == "VITE":
                S_r_freq = 2 * np.pi * self._freqs * S_r_freq
            # save for INFO
            self._SA[direction] = S_r_freq

            # Spectral response
            if self._option not in ["VITE", "ACCE_ABSOLU"]:
                if mode_corr == "OUI":
                    # interrogration ??? pq ne pas utiliser omega corrige?
                    pr_wr2_phi = np.sum(
                        (d_fact_partici[direction] / (2 * np.pi * self._freqs) ** 2)[:, None]
                        * self._phis,
                        axis=0,
                    )
                R_mi = (S_r_freq * d_fact_partici[direction] / w_r**2)[:, None] * self._phis

            elif self._option == "VITE":  # ici: phis correspond à DEPL
                if mode_corr == "OUI":
                    pr_wr2_phi = np.sum(
                        (d_fact_partici[direction] / w_r)[:, None] * self._phis, axis=0
                    )
                R_mi = (S_r_freq * d_fact_partici[direction] / w_r)[:, None] * self._phis
            elif self._option == "ACCE_ABSOLU":  # ici: phis correspond à DEPL
                pr_wr2_phi = np.sum((d_fact_partici[direction])[:, None] * self._phis, axis=0)
                R_mi = (S_r_freq * d_fact_partici[direction])[:, None] * self._phis
            self._R_mi[direction] = R_mi
            # in case where the first mode is bigger than cutting frequency
            if self._freq_coup and self._freq_coup >= self._freqs[0]:
                pass
            elif self._freq_coup < self._freqs[0]:
                if mode_corr == "OUI" or self._option == "ACCE_ABSOLU":
                    pr_wr2_phi = np.zeros((self._phis.shape[1],))
                R_mi = np.zeros(self._phis.shape)
                # Raise alarm for zero mode to be considered before cutting frequency
                UTMESS("A", "SEISME_96", valr=self._freq_coup)

            # step 3: modal combinaison
            # Get input COMB_MODE
            R_m2, R_qs = comb_modal_response.get(R_mi)
            # Automatic correction for ACCE_ABSOLU in mono-appui
            if self._option == "ACCE_ABSOLU":
                # field of unit value for acce_absolu
                acce_unitaire = self._mode_meca.getField("DEPL", 1).copy()
                acce_unitaire.setValues({f"D{direction}": 1.0}, [])
                s_r_freq_cut = (
                    spectre["nappe"](self._amors[-1], self._freq_coup) * spectre["coefficient"]
                )

                R_tt = (acce_unitaire.getValues() - pr_wr2_phi) * s_r_freq_cut
                # add to combined modale responses in square
                R_m2 += R_tt**2
            # modale response
            R_m = np.sqrt(R_m2)
            # step 4 : Entrainement zero pour mon_appui
            R_e2 = np.zeros(np.shape(R_m2))
            # step 5 : pseudo-mode response
            if mode_corr == "OUI":
                S_r_freq_cut = self._s_r_freq_cut(spectre)
                R_c = self._corr_pseudo_mode(pr_wr2_phi, w_r, direction, pseudo_mode, S_r_freq_cut)
                # save for INFO
                self._pseudo[direction] = S_r_freq_cut
            else:
                R_c = np.zeros(np.shape(R_m2))
                s_r_freq_cut = None
            # step 6 : reponse by direction
            # total
            R_x = np.sqrt(R_m2 + (R_qs + R_c) ** 2 + R_e2)

            if comb_mode["TYPE"] == "CQC_SIGNE":
                applied_signs = self._apply_signed_cqc(
                    comb_mode[f"NUME_MODE_{direction}"], direction
                )
                R_x = R_x * applied_signs

            # inertial part (part primaire)
            R_prim = np.sqrt(R_m2 + (R_qs + R_c) ** 2)
            # add total directionnal responses
            self._R_x[direction] = R_x
            # POST_ROCHE/ part dynamique et pseudo statique
            self._part_d[direction] = R_m
            self._part_s[direction] = R_c
            # RCCM part primaire
            self._R_prim[direction] = R_prim

    def combine(self, resu, comb_direction):
        """Combine responses and add to output result
        Args:
            resu (Resu): instance of output result
            comb_direction (str): type of combination
        """
        for direction in self._directions:
            if self._analyse == "MULTI_APPUI":
                for nom_appui, R_m_appui in self._R_mi[direction].items():
                    # Print out spectral response at each mode, direction and appui
                    resu.add_spectral_response(
                        self._option, direction, R_m_appui, self._nume_ordres, nom_appui
                    )
            else:
                resu.add_spectral_response(
                    self._option, direction, self._R_mi[direction], self._nume_ordres
                )
            resu.add_dire_response(self._option, direction, self._R_x[direction], "VALE_DIRE")
            resu.add_dire_response(self._option, direction, self._part_d[direction], "VALE_DYNA")
            resu.add_dire_response(self._option, direction, self._part_s[direction], "VALE_QS")
            resu.add_dire_response(self._option, direction, self._R_prim[direction], "VALE_INER")
            if self._analyse == "MULTI_APPUI":
                resu.add_dire_response(self._option, direction, self._R_seco[direction], "VALE_DDS")

        # step 7 : reponse by directional combinaison
        R_xyz, R_newmark_all = self._comb_directions(comb_direction, self._R_x.values())
        # POST_ROCHE / part dynamique et pseudo statique
        R_d, Rd_newmark_all = self._comb_directions(comb_direction, self._part_d.values())
        R_ps, Rps_newmark_all = self._comb_directions(comb_direction, self._part_s.values())
        # RCCM
        R_prim, R_prim_newmark_all = self._comb_directions(comb_direction, self._R_prim.values())

        resu.add_response(self._option, R_xyz, R_newmark_all, "VALE_TOTA")
        resu.add_response(self._option, R_d, Rd_newmark_all, "VALE_DYNA")
        resu.add_response(self._option, R_ps, Rps_newmark_all, "VALE_QS")
        resu.add_response(self._option, R_prim, R_prim_newmark_all, "VALE_INER")

        if self._analyse == "MULTI_APPUI":
            # RCCM
            R_seco, R_seco_newmark_all = self._comb_directions(
                comb_direction, self._R_seco.values()
            )
            resu.add_response(self._option, R_seco, R_seco_newmark_all, "VALE_DDS")

    def prints(self, verbosity, spectres, mode_corr, comb_dds_correle, comb_direction, nume_modes):
        """Print out for INFO = 1 or 2"""
        if verbosity:
            # info for modal basis to be considered/combined
            for direction in ("X", "Y", "Z"):
                UTMESS("I", "SEISME_48")
            # about spectra
            for direction in self._directions:
                for spectre in spectres[direction]:
                    nom_appui = spectre["nom_appui"]
                    # nature of spectra
                    UTMESS("I", "SEISME_17", valk=spectre["nature"])
                    # info of read value on spectra
                    if self._analyse == "MULTI_APPUI":
                        UTMESS("I", "SEISME_97")
                        for i_freq in range(len(self._freqs)):
                            vali = nume_modes[i_freq]
                            valr = (
                                self._freqs[i_freq],
                                self._amors[i_freq],
                                self._SA[direction][nom_appui][i_freq],
                                self._parti[direction][nom_appui][i_freq],
                            )
                            valk = (direction, nom_appui)
                            UTMESS("I", "SEISME_98", vali=vali, valr=valr, valk=valk)
                    else:
                        UTMESS("I", "SEISME_53")
                        for i_freq in range(len(self._freqs)):
                            vali = nume_modes[i_freq]
                            valr = (
                                self._freqs[i_freq],
                                self._amors[i_freq],
                                self._SA[direction][i_freq],
                            )
                            valk = direction
                            UTMESS("I", "SEISME_54", vali=vali, valr=valr, valk=valk)
                    # about correction by pseudo-mode
                    if mode_corr == "OUI":
                        # cutting frequency et ZPA
                        UTMESS("I", "SEISME_56")
                        if self._analyse == "MULTI_APPUI":
                            valr = (self._freq_coup, self._pseudo[direction][nom_appui])
                        else:
                            valr = (self._freq_coup, self._pseudo[direction])
                        valk = (direction, self._analyse)
                        UTMESS("I", "SEISME_57", valr=valr, valk=valk)
            # about combinaison of response due to DDS
            if comb_dds_correle:
                UTMESS("I", "SEISME_19", valk=comb_dds_correle)
            # about directional combinaison
            UTMESS("I", "SEISME_18", valk=comb_direction)


class MonoAppuiRunner(BaseRunner):
    """Runner for MONO_APPUI strategy"""

    _analyse = "MONO_APPUI"


class EnveloppeRunner(BaseRunner):
    """Runner for ENVELOPPE strategy"""

    _analyse = "ENVELOPPE"


class MultiAppuiRunner(BaseRunner):
    """Runner for MULTI_APPUI strategy"""

    _analyse = "MULTI_APPUI"

    def __init__(self, mode_meca, option, nume_ordres, freqs, amors, freq_coup_in, mode_corr):
        super().__init__(mode_meca, option, nume_ordres, freqs, amors, freq_coup_in, mode_corr)
        self._parti = {}  # dict of info about participation factor in case of mult_appui
        self._R_seco = {}  # list of directional result RCCM part secondaire

    def _comb_appui_corr(self, type_comb, R_mi):
        """Combines modals responses

        Args:
            type_comb (str): combination strategy
            R_mi (ndarray): list of all vectors corresponding to all correlated supports

        Returns:
            R_m (ndarray): combined response
        """

        R_m = 0
        if type_comb == "QUAD":
            R_m = np.sqrt(np.sum(R_mi**2, axis=0))
        elif type_comb == "LINE":
            R_m = np.sum(R_mi, axis=0)
        elif type_comb == "ABS":
            R_m = np.sum(np.abs(R_mi), axis=0)

        return R_m

    def _corr_pseudo_mode(
        self, pr_wr2_phi, w_r, direction, pseudo_mode, s_r_freq_cut, l_group_no, nom_appui, mesh
    ):
        """Correction by pseudo-mode/mode statique, for MULTI_APPUI
        Args:
            pr_wr2_phi (ndarray)    : sum of list of produit rho*phi/omega^2
            w_r (ndarray)           : list of omega = 2*pi*freq
            direction (str)         : X, Y or Z
            pseudo_mode (ModeResult): pseudo mode for static correction
            s_r_freq_cut (ndarray)  : value of ZPA at the cutting frequency
            l_group_no list[str]    : list of all group_no of support
            nom_appui               : support name
            mesh (Mesh)             : mesh extracted from mode_meca

        Returns:
            R_c (ndarray): response by correction by pseudo-mode
        """

        ps_nume_modes = pseudo_mode.getAccessParameters()["NUME_MODE"]
        ps_noeud_cmps = pseudo_mode.getAccessParameters()["NOEUD_CMP"]

        # searche for index (APPUI_CMP) in MODE_STATIQUE / PSEUDO_MODE
        appui_cmp = nom_appui.ljust(8) + f"D{direction}"
        if appui_cmp in ps_noeud_cmps:
            ps_nume_mode = ps_nume_modes[ps_noeud_cmps.index(appui_cmp)]
            phi_ps = pseudo_mode.getField(self._option, ps_nume_mode)
        else:
            # searche for index (NUME_CMP) in MODE_STATIQUE / PSEUDO_MODE
            # list of node_num and node_name in group_no
            _, nodes_name = get_nodes(mesh, l_group_no)
            # list of all noeud_cmp
            l_noeud_cmp = []
            for node_name in nodes_name:
                noeud_cmp = node_name.ljust(8) + f"D{direction}"
                l_noeud_cmp.append(noeud_cmp)
            if all(noeud_cmp in ps_noeud_cmps for noeud_cmp in l_noeud_cmp):
                l_phi_ps = []
                for noeud_cmp in l_noeud_cmp:
                    ps_nume_mode = ps_nume_modes[ps_noeud_cmps.index(noeud_cmp)]
                    l_phi_ps.append(pseudo_mode.getField(self._option, ps_nume_mode))
                phi_ps = l_phi_ps[0].copy()
                for x in l_phi_ps[1:]:
                    phi_ps += x
            else:
                for noeud_cmp in l_noeud_cmp:
                    if noeud_cmp not in ps_noeud_cmps:
                        UTMESS("E", "SEISME_66", valk=(noeud_cmp, "PSEUDO_MODE"))
                UTMESS("F", "SEISME_68", valk=(nom_appui, direction, appui_cmp))

        if self._option == "VITE":  # pseudo-mode is not allowed
            UTMESS("F", "SEISME_10", valk=self._option)
            R_c_noeud = (phi_ps.getValues() * w_r - pr_wr2_phi) * s_r_freq_cut
        elif (
            self._option == "ACCE_ABSOLU"
        ):  # correction by pseudo-mode is not allowed for ACCE_ABSOLU in mutl_appui
            UTMESS("F", "SEISME_10", valk=self._option)
            R_c_noeud = np.zeros(phi_ps.size())
        else:
            R_c_noeud = (phi_ps.getValues() - pr_wr2_phi) * s_r_freq_cut

        return R_c_noeud

    def compute(
        self,
        comb_modal_response,
        spectres,
        mode_corr,
        pseudo_mode,
        gene_masses,
        cumul_intra,
        cumul_inter,
        comb_dds_correle,
        depl_mult_appuis,
        appuis,
        group_appuis,
        mesh,
        comb_mode,
    ):
        """Compute responses for TYPE_ANALYSE = 'MULTI_APPUI'

        Args:
            comb_modal_response (CombModalResponse): instance to combine modal responses
            spectres (dict[str, list]): list of spectras, by direction
            mode_corr (str): static correction, user input
            pseudo_mode (ModeResult): pseudo modes, user input
            gene_masses (ndarray): list of generalized masses, to compute participation factors
            cumul_intra (str) : combination of contributions of each response of support inside a group
            cumul_inter (str) : combination of contributions of each group of supports
            comb_dds_correle (str) : combination of contributions for correlated support
            depl_mult_appuis (dict[str, dict]): suport properties
            appuis (dict[str, dict]): supports, by direction
            group_appuis (list[dict[str, list]]): groups of supports
            mesh (Mesh): mesh extracted from mode_meca
            comb_mode (dict): input for key_factor COMB_MODE
        """
        # search for all directions presented by users
        self._directions = [direction for direction in ("X", "Y", "Z") if spectres[direction]]

        # Iteration on directions
        for direction in self._directions:
            # save for print out as INFO
            # dict of info about read spectra at eigen-frequencies by direction
            self._SA[direction] = {}
            self._R_mi[direction] = {}
            self._parti[direction] = {}
            # dict of info about correction by pseudo mode by direction
            self._pseudo[direction] = {}

            # Iteration on appuis
            R_appuis = []  # list reponse tous appuis
            for spectre in spectres[direction]:
                nom_appui = spectre["nom_appui"]
                # ("iteration on support:", nom_appui)
                # Reponse oscillator et pseudo-mode
                # Pulsation before correction by corr_freq
                w_r = 2 * np.pi * self._freqs

                # Spectrum interpolation
                nappe = spectre["nappe"]
                coeff = spectre["coefficient"]
                S_r_freq = [
                    nappe(amor, freq) * coeff for amor, freq in zip(self._amors, self._freqs)
                ]

                # Correction of spectrum by corr_freq
                if spectre["corr_freq"] == "OUI":
                    # pulsation propre amortie
                    correct = np.sqrt(1 - self._amors**2)
                    w_r *= correct
                    S_r_freq *= correct

                # Correction of spectrum by nature
                if spectre["nature"] == "DEPL":
                    S_r_freq *= (2 * np.pi * self._freqs) ** 2
                elif spectre["nature"] == "VITE":
                    S_r_freq *= 2 * np.pi * self._freqs

                # iteration on node in appui
                l_group_no = appuis[nom_appui]["groups"]
                R_m_noeuds = []  # stockage reponse oscillateur de tous noeuds
                R_c_noeuds = []  # stockage reponse pseudo-mode de tous noeuds
                # save for INFO
                self._SA[direction][nom_appui] = S_r_freq
                # modal spectral response
                # preparing a list of reac_noda for all modes and all group_no
                reac_noda = []
                dofs = (
                    self._mode_meca.getDOFNumbering()
                    .getEquationNumbering()
                    .getDOFs(list_cmp=[f"D{direction}"], list_grpno=l_group_no)
                )
                for imode in self._nume_ordres:
                    # all values of reac_node for mode
                    reac_noda_all = self._mode_meca.getField("REAC_NODA", imode)
                    # values for all nodes in the same group_no without knowing the order
                    reac_noda_by_mode = reac_noda_all.getValues(dofs)
                    reac_noda.append(reac_noda_by_mode)
                # Reac_node for all modes at 1 support
                reac_noda = np.sum(reac_noda, axis=1)
                # participation factor for all modes at 1 support
                fact_partici = -1.0 * reac_noda / (gene_masses * w_r**2)
                # Spectral response at node, mode, direction

                if self._option == "VITE":  # ici: phis correspond à DEPL
                    if mode_corr == "OUI":
                        pr_wr2_phi = np.sum(
                            (fact_partici / (2 * np.pi * self._freqs))[:, None] * self._phis, axis=0
                        )
                    R_mi = (S_r_freq * fact_partici / w_r)[:, None] * self._phis
                elif self._option == "ACCE_ABSOLU":  # ici: phis correspond à DEPL
                    if mode_corr == "OUI":
                        pr_wr2_phi = np.sum((fact_partici)[:, None] * self._phis, axis=0)
                    R_mi_all = (S_r_freq * fact_partici)[:, None] * self._phis
                else:
                    if mode_corr == "OUI":
                        pr_wr2_phi = np.sum(
                            (fact_partici / (2 * np.pi * self._freqs) ** 2)[:, None] * self._phis,
                            axis=0,
                        )
                    R_mi = (S_r_freq * fact_partici / w_r**2)[:, None] * self._phis
                # Check if cutting frequency is smaller than firt mode
                if self._freq_coup and self._freq_coup >= self._freqs[0]:
                    pass
                elif self._freq_coup < self._freqs[0]:
                    if mode_corr == "OUI":
                        pr_wr2_phi = np.zeros((self._phis.shape[1],))
                    R_mi = np.zeros(self._phis.shape)
                    # Raise alarm message if first mode bigger than cutting frequency
                    UTMESS("A", "SEISME_96", valr=self._freq_coup)
                # saving all responses at all nodes of considerd appui
                R_m_noeuds.append(R_mi)
                # --- pseudo mode response
                if mode_corr == "OUI":
                    s_r_freq_cut = self._s_r_freq_cut(spectre)
                    R_c_noeud = self._corr_pseudo_mode(
                        pr_wr2_phi,
                        w_r,
                        direction,
                        pseudo_mode,
                        s_r_freq_cut,
                        l_group_no,
                        nom_appui,
                        mesh,
                    )
                    # save for INFO
                    self._pseudo[direction][nom_appui] = s_r_freq_cut
                else:
                    R_c_noeud = np.zeros(np.shape(self._phis[0]))
                # saving all pseudo-modes at all nodes of considerd appui
                R_c_noeuds.append(R_c_noeud)
                # step 3: LINE combinaison intra-appui: considered as CORRELATED
                R_m_appui = np.sum(R_m_noeuds, axis=0)
                R_c_appui = np.sum(R_c_noeuds, axis=0)
                # save for INFO
                self._parti[direction][nom_appui] = fact_partici

                self._R_mi[direction][nom_appui] = R_m_appui

                # response due to DDS
                if nom_appui in depl_mult_appuis.keys() and depl_mult_appuis[nom_appui][direction]:
                    mode_stat = depl_mult_appuis[nom_appui]["mode_stat"]
                    coef = depl_mult_appuis[nom_appui][direction]
                    # iteration on node in APPUI
                    l_nodes_num = appuis[nom_appui]["nodes"]
                    l_nodes_name = appuis[nom_appui]["nodes_name"]
                    R_e_noeuds = []  # stock of DDS response at all nodes in considered APPUI
                    for i_node in range(len(l_nodes_num)):
                        # ("Iteration sur les nodes dans un appui")
                        node_name = l_nodes_name[i_node]
                        noeud_cmp = node_name.ljust(8) + f"D{direction}"
                        stat_nume_modes = mode_stat.getAccessParameters()["NUME_MODE"]
                        stat_noeud_cmps = mode_stat.getAccessParameters()["NOEUD_CMP"]
                        if noeud_cmp in stat_noeud_cmps:
                            stat_nume_mode = stat_nume_modes[stat_noeud_cmps.index(noeud_cmp)]
                            # Get static mode
                            if self._option in ("VITE", "ACCE_ABSOLU"):
                                UTMESS("F", "SEISME_67", valk=self._option)

                            phi_stat = mode_stat.getField(self._option, stat_nume_mode).getValues()
                            # Reponse due to DDS at node
                            R_e_noeud = np.array(phi_stat) * coef
                        else:
                            # noeud_cmp is not found --> raise fatal erreur
                            UTMESS("F", "SEISME_66", valk=(noeud_cmp, "MODE_STAT"))
                        # save responses DDS at all nodes in considered APPUI
                        R_e_noeuds.append(R_e_noeud)
                    # save en array
                    R_e_noeuds = np.array(R_e_noeuds)
                    # calculate response at APPUI
                    # step 3: LINE combinaison intra-appui: considered as CORRELATED
                    R_e_appui = np.sum(R_e_noeuds, axis=0)
                else:
                    R_e_appui = np.zeros(np.shape(self._phis[0]))
                # all responses at one APPUI
                R_appuis.append([nom_appui, R_m_appui, R_e_appui, R_c_appui])
            # step 4: iteration on group_appui
            l_R_x_j = []  # list des reponse directionnelle de tous les group_appui
            l_part_d_j = []  # list des reponse part dyn  de tous les group_appui
            l_part_s_j = []  # list des reponse part sta  de tous les group_appui
            l_R_prim_j = []  # list des reponse RCCM part primaire de tous les group_appui
            l_R_seco_j = []  # list des reponse RCCM part primaire de tous les group_appui
            for group_appui in group_appuis.values():
                # ("iteration on nom_group_appui:", nom_group_appui)
                R_m_j, R_e_j, R_c_j = [], [], []
                for [appui, R_m, R_e, R_c] in R_appuis:
                    if appui in group_appui:
                        R_m_j.append(R_m)
                        R_e_j.append(R_e)
                        R_c_j.append(R_c)
                R_m_j = np.array(R_m_j)
                R_e_j = np.array(R_e_j)
                R_c_j = np.array(R_c_j)
                # step 5: combinaison of all appuis in a group_appui
                # rules are different for different components
                # pour oscillator and pseudo-mode: CUMUL_INTRA
                # pour dds: rule definied in COMB_DDS_CORRELE
                # response of oscillator by group_appui

                R_m_group_appui = self._comb_appui_corr(cumul_intra, R_m_j)
                # response of pseudo-mode by group_appui
                R_c_group_appui = self._comb_appui_corr(cumul_intra, R_c_j)
                # response of DDS by group_appui)
                R_e_group_appui = self._comb_appui_corr(comb_dds_correle, R_e_j)
                # step 6: modal combinaison pour R_m_group_appui
                R_m2, R_qs = comb_modal_response.get(R_m_group_appui)
                # Automatic correction for ACCE_ABSOLU: not used in mult-appui
                if self._option == "ACCE_ABSOLU":
                    # raise fatal error message to stop
                    UTMESS("F", "SEISME_10", valk=self._option)
                    spectre = spectres[direction][0]

                    # unit field
                    acce_unitaire = self._mode_meca.getField("DEPL", 1).copy()
                    acce_unitaire.setValues({f"D{direction}": 1.0}, [])
                    # recalculate pr_wr2_phi for acce_absolu
                    pr_wr2_phi_all = fact_partici[:, None] * self._phis
                    pr_wr2_phi = pr_wr2_phi_all[self._freqs <= self._freq_coup]
                    # i_appui=0 : only first support to be considered
                    index_dir = spectres[0][0].index(direction)
                    s_r_freq_cut = (
                        spectre["nappe"](self._amors[-1], self._freq_coup) * spectre["coefficient"]
                    )
                    R_tt = (acce_unitaire.getValues() - np.sum(pr_wr2_phi, axis=0)) * s_r_freq_cut
                    # reponse oscillator by adding correction for ACCE_ABSOLU:Not used
                    R_m2 += R_tt**2
                # reponse oscillator
                R_m = np.sqrt(R_m2)
                # step 7 : reponse by direction for group_appui
                # ("reponse directionnelle : sqrt(Rm**2 + Rc**2 + Re**2)")
                R_x_j = np.sqrt(R_m2 + (R_qs + R_c_group_appui) ** 2 + R_e_group_appui**2)
                l_R_x_j.append(R_x_j)
                # RCCM part primaire
                R_prim_group_appui = np.sqrt(R_m2 + (R_qs + R_c_group_appui) ** 2)
                # POST_ROCHE/ part dynamique et pseudo statique
                l_part_d_j.append(R_m)
                l_part_s_j.append(R_c_group_appui)
                # RCCM
                l_R_prim_j.append(R_prim_group_appui)
                l_R_seco_j.append(R_e_group_appui)

                # step 8: combinaison of all group_appui
                # While nb of group_appui > 1: rule = QUAD (considered as DECORRELATED)
                if len(l_R_x_j) > 1:
                    # combi all group_appui
                    if cumul_inter == "QUAD":
                        R_x = np.sqrt(np.sum(np.array(l_R_x_j) ** 2, axis=0))
                        part_d_x = np.sqrt(np.sum(np.array(l_part_d_j) ** 2, axis=0))
                        part_s_x = np.sqrt(np.sum(np.array(l_part_s_j) ** 2, axis=0))
                        R_prim_x = np.sqrt(np.sum(np.array(l_R_prim_j) ** 2, axis=0))
                        R_seco_x = np.sqrt(np.sum(np.array(l_R_seco_j) ** 2, axis=0))
                    elif cumul_inter == "ABS":  # HB: NEW METHOD
                        R_x = np.sum(np.abs(np.array(l_R_x_j)), axis=0)
                        part_d_x = np.sum(np.abs(np.array(l_part_d_j)), axis=0)
                        part_s_x = np.sum(np.abs(np.array(l_part_s_j)), axis=0)
                        R_prim_x = np.sum(np.abs(np.array(l_R_prim_j)), axis=0)
                        R_seco_x = np.sum(np.abs(np.array(l_R_seco_j)), axis=0)
                    elif cumul_inter == "LINE":  # HB: NEW METHOD
                        R_x = np.sum(np.array(l_R_x_j), axis=0)
                        part_d_x = np.sum(np.array(l_part_d_j), axis=0)
                        part_s_x = np.sum(np.array(l_part_s_j), axis=0)
                        R_prim_x = np.sum(np.array(l_R_prim_j), axis=0)
                        R_seco_x = np.sum(np.array(l_R_seco_j), axis=0)

                elif len(l_R_x_j) == 1:  # un seul group appui = multi appui correle
                    # combi group_appui not done if one group_appui
                    R_x = l_R_x_j[0]
                    part_d_x = l_part_d_j[0]
                    part_s_x = l_part_s_j[0]
                    R_prim_x = l_R_prim_j[0]
                    R_seco_x = l_R_seco_j[0]

            if comb_mode["TYPE"] == "CQC_SIGNE":
                applied_signs = self._apply_signed_cqc(
                    comb_mode[f"NUME_MODE_{direction}"], direction
                )
                R_x = R_x * applied_signs

            self._R_x[direction] = R_x
            # POST_ROCHE / part dynamique et pseudo statique
            self._part_d[direction] = part_d_x
            self._part_s[direction] = part_s_x
            # RCCM part primaire
            self._R_prim[direction] = R_prim_x
            self._R_seco[direction] = R_seco_x


def comb_sism_modal_ops(self, **args):
    """Execute the command COMB_SISM_MODAL.

    Arguments:
        **args (dict): User's keywords.

    Returns:
        resu: result for linear modal combinaison
    """
    mode_meca = args.get("MODE_MECA")
    amor_reduit = args.get("AMOR_REDUIT")
    list_amor = args.get("LIST_AMOR")
    amor_gene = args.get("AMOR_GENE")
    mode_corr = args.get("MODE_CORR")
    pseudo_mode = args.get("PSEUDO_MODE")
    freq_coup_in = args.get("FREQ_COUP")
    type_analyse = args.get("TYPE_ANALYSE")
    spectre_in = args.get("SPECTRE")
    appuis_in = args.get("APPUIS")
    comb_mode = args.get("COMB_MODE")
    comb_direction = args.get("COMB_DIRECTION")
    group_appui_correle = args.get("GROUP_APPUI_CORRELE")
    cumul_intra = args.get("CUMUL_INTRA")
    cumul_inter = args.get("CUMUL_INTER")
    comb_dds_correle = args.get("COMB_DDS_CORRELE")
    depl_mult_appui = args.get("DEPL_MULT_APPUI")
    type_resu = args.get("TYPE_RESU")
    verbosity = args["INFO"]
    setFortranLoggingLevel(verbosity)

    # Check if CQC_SIGNE uses directionnal combine "NEWMARK"
    if comb_mode["TYPE"] == "CQC_SIGNE" and comb_direction != "NEWMARK":
        UTMESS("F", "SEISME_94")

    # exploring mode_meca
    mesh = mode_meca.getMesh()
    list_para = mode_meca.getParameters()

    # get numeber of orders of modes to be combined
    freqs, nume_ordres, nume_modes, gene_masses = filter_ordre_freq(list_para, args)

    # Get damping coefficients
    amors = get_amor_reduit(list_para, nume_ordres, amor_reduit, list_amor, amor_gene)

    # Get spectres
    spectres = get_spectres(spectre_in)

    if type_analyse == "MULT_APPUI":
        # Get appuis
        depl_mult_appuis = get_depl_mult_appui(depl_mult_appui)
        appuis = get_appuis(appuis_in, mesh)
        group_appuis = get_group_appuis(spectres, group_appui_correle)
    else:
        # Get participation factors
        d_fact_partici = {}
        for direction in ("X", "Y", "Z"):
            fact_partici = []
            for nume_ordre in nume_ordres:
                # search for index of number of order of considered mode
                index_nume_ordre = list_para["NUME_ORDRE"].index(nume_ordre)
                fact_partici.append(list_para[f"FACT_PARTICI_D{direction}"][index_nume_ordre])
            d_fact_partici[direction] = np.array(fact_partici)

    # Output result preparing
    resu = Resu(type_resu, mode_meca, mesh)

    # Combinaison
    comb_modal_response = CombModalResponse(comb_mode, type_analyse, amors, freqs)
    for option in args["OPTION"]:
        if type_analyse == "MONO_APPUI":
            runner = MonoAppuiRunner(
                mode_meca, option, nume_ordres, freqs, amors, freq_coup_in, mode_corr
            )
            runner.compute(
                comb_modal_response, spectres, mode_corr, pseudo_mode, d_fact_partici, comb_mode
            )
            runner.combine(resu, comb_direction)
            runner.prints(
                verbosity, spectres, mode_corr, comb_dds_correle, comb_direction, nume_modes
            )
        elif type_analyse == "ENVELOPPE":
            runner = EnveloppeRunner(
                mode_meca, option, nume_ordres, freqs, amors, freq_coup_in, mode_corr
            )
            runner.compute(
                comb_modal_response, spectres, mode_corr, pseudo_mode, d_fact_partici, comb_mode
            )
            runner.combine(resu, comb_direction)
            runner.prints(
                verbosity, spectres, mode_corr, comb_dds_correle, comb_direction, nume_modes
            )
        elif type_analyse == "MULT_APPUI":
            runner = MultiAppuiRunner(
                mode_meca, option, nume_ordres, freqs, amors, freq_coup_in, mode_corr
            )
            runner.compute(
                comb_modal_response,
                spectres,
                mode_corr,
                pseudo_mode,
                gene_masses,
                cumul_intra,
                cumul_inter,
                comb_dds_correle,
                depl_mult_appuis,
                appuis,
                group_appuis,
                mesh,
                comb_mode,
            )
            runner.combine(resu, comb_direction)
            runner.prints(
                verbosity, spectres, mode_corr, comb_dds_correle, comb_direction, nume_modes
            )
        verbosity = 0

    return resu.get()
