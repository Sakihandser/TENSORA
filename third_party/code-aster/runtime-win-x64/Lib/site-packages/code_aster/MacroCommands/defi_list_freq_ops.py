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

from ..Cata.Syntax import _F
from ..Cata.SyntaxUtils import remove_none
from ..CodeCommands import DEFI_LIST_REEL, INFO_MODE, CREA_TABLE
from ..Messages import UTMESS
from ..Utilities import no_new_attributes


class Refinement:
    """Refinement procedure.

    Arguments:
        keywords (dict): Keywords passed to the RAFFINEMENT keyword.
    """

    epsilon = 1.0e-12
    crit = df_min = nbpts = freq = amor = None
    _disp = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, keywords) -> None:
        self.crit = keywords["CRITERE"]
        self.df_min = keywords["PAS_MINI"]
        self.nbpts = keywords["NB_POINTS"]
        self.freq = np.array(keywords["LIST_RAFFINE"])
        if self.crit in ("RELATIF", "ABSOLU"):
            amor = []
            self._disp = keywords["DISPERSION"]
        else:
            self._disp = None
            if keywords.get("AMOR_REDUIT") is not None:
                amor = list(keywords["AMOR_REDUIT"])
            else:
                amor = keywords["LIST_AMOR"].getValues()
        self.amor = np.array(amor)

    def dispersion(self, idx):
        """Return the dispersion at the given index (the intervalle width to be
        refined)."""
        if self.crit == "ABSOLU":
            return self._disp
        if self.crit == "RELATIF":
            return self._disp * self.freq[idx]
        if self.amor[idx] > self.epsilon:
            return 2.0 * self.amor[idx] * self.freq[idx]
        return 0.01 * self.freq[idx]

    def _extend_amor(self):
        """Extend the list of damping values with the last one if the size is
        less than the number of frequencies.
        """
        if self.amor.size == 0:
            return
        amor2 = np.ones(self.freq.size) * self.amor[-1]
        amor2[: self.amor.size] = self.amor
        self.amor = amor2

    @staticmethod
    def _remove_multiple(first, second=None, delta=0.0):
        """Remove multiple values from the first list and remove same indexes in
        the other lists.

        Arguments:
            first (list[float]): List to be filtered.
            second (list[float]): List to filter with the same indexes.
            delta (float): Precision.
        """
        idx = np.ones(first.size, dtype=bool)
        idx[1:] = np.diff(first) > delta
        first = first[idx]
        if second is not None and second.size > 0:
            second = second[idx]
        return first, second

    def _center_freq(self):
        """Shift the frequencies to be centered on the module resonance"""
        if self.amor.size == 0:
            return
        idx = self.amor > self.epsilon
        # f * sqrt(1 - 2 amor^2) if amor > eps else f * 1.
        coef = np.sqrt(1.0 - 2 * self.amor**2) * idx
        coef += np.ones(self.amor.size) * (1 - idx)
        self.freq *= coef

    def refine(self, list_init):
        """Refine the given list.

        Arguments:
            list_init (list[float]): Initial list of frequencies.
        """
        self._extend_amor()
        self.freq, self.amor = self._remove_multiple(self.freq, self.amor, delta=self.df_min)

        freq0 = self.freq.copy()
        self._center_freq()

        # add refinement around initial frequencies
        cum = np.array([])
        for i, frq in enumerate(self.freq):
            dfr = self.dispersion(i)
            # check for overlap
            if i > 0 and cum.max() > frq - dfr / 2.0:
                UTMESS("I", "DYNAMIQUE_26", valr=(freq0[i - 1], freq0[i]))
            steps = (np.arange(self.nbpts, dtype=float) / (self.nbpts - 1) - 0.5) * dfr
            cum = np.hstack((cum, frq + steps))

        if self.nbpts % 2 == 0:
            # add a point at the center
            cum = np.hstack((cum, self.freq, self.freq / np.sqrt(1 - 2 * self.amor**2)))
        cum = np.hstack((cum, list_init))
        cum.sort()

        self.freq = cum
        # should we keep double frequencies if present in list_init or LIST_RAFFINE?
        result = self._remove_multiple(self.freq, delta=self.df_min)[0]
        return result


class BinnedDataCumulativeDistributionFunction(object):
    r"""Cumulative distribution function (CDF) for binned data.

    Given :math:`m \ge 1` bins with ends :math:`([y_{i-1}, y_{i}[)_{1 \le i \le m}` (:math:`y_0 < y_1 < \dots < y_m`)
    and counts :math:`(n_i)_{1 \le i \le m}` (i.e. there are :math:`n_i` values in :math:`[y_{i-1},y_{i}[`),
    defines the function :math:`\hat{F} : [y_{0}, y_{m}] \longrightarrow [0,1]` given by:

    .. math::
        \hat{F}(x) = \frac{1}{N} \sum_{i=1}^{m},

    where :math:`N = \sum_{i=1}^m n_i`.

    The generalized inverse of :math:`\hat{F}` is the function :math:`\hat{F}^{(-1)} : [0,1] \longrightarrow [y_0, y_m]` defined by:

    .. math::
        \hat{F}^{(-1)}(q) = \inf\left\{ x \in [y_0, y_m] \ \vert \ \hat{F}(x) \ge q \right\}.
    """

    def __init__(self, bins, counts):
        r"""Constructor

        Args:
            bins (:class:`list` [:math:`m+1`]): bins ends :math:`(y_i)_{0 \le i \le m}`

            counts (:class:`list` [:math:`m`]): bins counts :math:`(n_i)_{1 \le i \le m}`
        """
        self.bins = np.atleast_1d(bins)
        self.counts = np.atleast_1d(counts)
        #
        if len(counts) != len(bins) - 1:
            raise ValueError(
                "The number of bins ends is not consistent with the number of bins counts."
            )
        #
        self.N = np.sum(self.counts)
        self.values = np.concatenate(([0], np.cumsum(self.counts) / self.N))

    def evaluate(self, x):
        r"""Evaluate CDF :math:`\hat{F}` at :math:`x`

        Args:
            x (:class:`numpy.ndarray` [:math:`n`]): evaluation points :math:`x`

        Returns:
            (:class:`numpy.ndarray` [:math:`n`]): CDV output values
        """
        x = np.atleast_1d(x)
        out = np.zeros(x.shape[0])
        for i in range(out.shape[0]):
            idx = np.max(np.where(self.bins <= x[i])[0])
            out[i] = self.values[idx]
        return out

    def inverse(self, q):
        r"""Evaluate generalized inverse :math:`\hat{F}^{(-1)}` at :math:`q`

        Args:
            q (:class:`numpy.ndarray` [:math:`n`]): evaluation points :math:`q`

        Returns:
            (:class:`numpy.ndarray` [:math:`n`]): generalized inverse output values
        """
        q = np.atleast_1d(q)
        out = np.zeros(q.shape[0])
        for i in range(out.shape[0]):
            idx = np.min(np.where(self.values >= q[i])[0])
            out[i] = self.bins[idx]
        return out

    def count(self, bins):
        r"""Returns counts associated to given bins

        Args:
            bins (:class:`numpy.ndarray` [:math:`p`]): bins

        Returns:
            (:class:`numpy.ndarray` [:math:`p-1`]): bins counts
        """
        return np.round(np.diff(self.evaluate(bins)) * self.N).astype(int)


class FrequencyBandOptimizationAlgorithm(object):
    r"""Frequency band optimization algorithm.

    Given a standard generalized eigenvalue problem of the form :math:`\mathbf{A}\mathbf{u} = \lambda \mathbf{B}\mathbf{u}`
    with (real) eigenfrequencies :math:`x_1 \le \dots \le x_N`, find the ends of :math:`B \ge 1` frequency bands
    :math:`([y_{i-1}, y_{i}[)_{1 \le i \le B}` such that each band contains a comparable number of eigenfrequencies.
    """

    def __init__(self, args):
        r"""Constructor

        Args:
            args (:class:`dict`): algorithm arguments
        """
        # Parse algorithm mode (matrix-based or list-based)
        self.freq_min = args["FREQ_MIN"]
        self.freq_max = args["FREQ_MAX"]
        self.hasMatrices = args["TYPE_SAISIE"] == "MATR_ASSE"
        if self.hasMatrices:
            # Check if matrices are symmetric
            if (not args["MATR_RIGI"].isSymmetric()) or (not args["MATR_MASS"].isSymmetric()):
                UTMESS("F", "DYNAMIQUE1_5")
            self.matr_rigi = args["MATR_RIGI"]
            self.matr_mass = args["MATR_MASS"]
        else:
            self.list_freq = sorted(args["LIST_FREQ"])
        # Parse algorithm parameters
        self.tol = args["TOLERANCE"]
        self.n_init = args["NB_POINTS_INIT"]
        self.n_supp = args["NB_POINTS_SUPP"]
        self.iter_maxi = args["ITER_MAXI"]
        self.n_modes = args["NB_MODES"]

    def run(self):
        r"""Run algorithm

        Returns:
            (:class:`libaster.Table`): result table
        """
        ### Initialization
        bins = np.linspace(self.freq_min, self.freq_max, self.n_init + 1)  # initial bins
        bins_info = bins.copy()  # inputs bins of INFO_MODE operator

        ### Frequency band optimization procedure
        idx = []
        for n in range(self.iter_maxi):
            # Call INFO_MODE operator (on new bins only)
            counts_info = self._countFrequencies(bins_info)  # counts obtained with INFO_MODE

            if n == 0:
                # Initialize variables after first INFO_MODE call
                counts = counts_info.copy()
                N = np.sum(counts)
                Nb = int(N / self.n_modes) + 1  # number of bands
                q_tar = np.linspace(0, 1, Nb + 1)  # target quantiles
            else:
                # Update counts values with new values obtained from INFO_MODE
                counts = np.insert(np.delete(counts, idx), idx, counts_info)
                bins = np.insert(bins, idx + 1, bins_info[1:-1])  # associated bins

            # Build CDF approximation from binned data
            G = BinnedDataCumulativeDistributionFunction(bins, counts)

            # Compute bins from target quantiles
            bins_tar = G.inverse(q_tar)

            # Estimate error on target bins counts
            counts_tar = G.count(bins_tar)
            err = (counts_tar - self.n_modes) / G.N  # counts relative error

            # Refine frequency grid in the band with the largest error
            imax = np.argmax(err)
            l_idx = np.where((bins >= bins_tar[imax]) * (bins <= bins_tar[imax + 1]))[0][
                :-1
            ]  # indices of sub-intervals in the imax-th band
            idx = l_idx[-1]  # choose the sub-interval at the right boundary
            bins_info = np.linspace(bins[idx], bins[idx + 1], self.n_supp + 2)

            # Stopping criterion
            err_max = np.max(np.abs(err))
            if err_max < self.tol:
                UTMESS("I", "DYNAMIQUE1_4", valr=err_max, vali=n + 1)
                break
            else:
                if n + 1 == self.iter_maxi:
                    UTMESS("A", "DYNAMIQUE1_3")
        # Return result table
        return CREA_TABLE(
            TITRE="RESU_EQUI_MODES",
            LISTE=(
                _F(PARA="NUME_BANDE", LISTE_I=np.arange(1, Nb + 1)),
                _F(PARA="FREQ_MIN", LISTE_R=bins_tar[:-1]),
                _F(PARA="FREQ_MAX", LISTE_R=bins_tar[1:]),
                _F(PARA="NB_MODES", LISTE_I=counts_tar),
                _F(PARA="NB_CIBLE", LISTE_I=[self.n_modes] * Nb),
                _F(PARA="ERR_REL", LISTE_R=np.abs(err)),
                _F(PARA="NB_ITER", LISTE_I=[n + 1] * Nb),
                _F(PARA="ITER_MAX", LISTE_I=[self.iter_maxi] * Nb),
            ),
        )

    def _countFrequencies(self, bins):
        r"""Returns the number of eigenfrequencies in given bins

        Args:
            bins (:class:`numpy.ndarray` [:math:`m`]): bins

        Returns:
            (:class:`numpy.ndarray` [:math:`m-1`]): bins counts
        """
        # Call INFO_MODE operator if assembly matrices are specified
        if self.hasMatrices:
            return self._countFrequenciesFromMatrices(bins)
        # Else, mock INFO_MODE operator through direct counting in a list
        else:
            return self._countFrequenciesFromList(bins)

    def _countFrequenciesFromList(self, bins):
        r"""Returns the number of eigenfrequencies in given bins, for a
        given list of eigenfrequencies

        Args:
            bins (:class:`numpy.ndarray` [:math:`m`]): bins

        Returns:
            (:class:`numpy.ndarray` [:math:`m-1`]): bins counts
        """
        m = len(bins)
        out = np.zeros(m - 1)
        for b in range(m - 1):
            out[b] = np.sum((self.list_freq >= bins[b]) * (self.list_freq <= bins[b + 1]))
        return out.astype(int)

    def _countFrequenciesFromMatrices(self, bins):
        r"""Returns the number of eigenfrequencies in frequency bins given
        assembly stiffness and mass matrices, through a call to INFO_MODE operator

        Args:
            bins (:class:`numpy.ndarray` [:math:`m`]): bins

        Returns:
            (:class:`numpy.ndarray` [:math:`m-1`]): bins counts
        """
        # Call INFO_MODE operator
        tab_info = INFO_MODE(
            TYPE_MODE="DYNAMIQUE",
            MATR_RIGI=self.matr_rigi,
            MATR_MASS=self.matr_mass,
            FREQ=bins,
            COMPTAGE=_F(METHODE="AUTO"),
        )
        val_info = tab_info.EXTR_TABLE().values()

        # Extract bins and counts from result table
        counts = np.array(val_info["NB_MODE"])
        if len(counts) != len(bins) - 1:
            raise RuntimeError(
                "The number of obtained counts is not consistent"
                + " with the number of input bins."
            )

        return counts


def defi_list_freq_ops(self, **args):
    """Definition of a list of frequencies."""
    args = _F(args)
    remove_none(args)

    # RAFFINEMENT
    refine_args = args.pop("RAFFINEMENT", [None])[0]
    if refine_args is not None:
        listr = DEFI_LIST_REEL(**args)
        list_init = listr.getValues()
        builder = Refinement(refine_args)
        refined_list = builder.refine(list_init)

        return DEFI_LIST_REEL(VALE=refined_list)

    # EQUI_MODES
    equi_args = args.pop("EQUI_MODES", [None])[0]
    if equi_args is not None:
        # Run algorithm
        algo = FrequencyBandOptimizationAlgorithm(equi_args)
        tab = algo.run()

        return tab
