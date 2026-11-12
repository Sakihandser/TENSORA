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
:py:class:`TransientGeneralizedResult` --- Assignment of mesh
************************************************************************
"""

import aster
from libaster import TransientGeneralizedResult, HarmoGeneralizedResult

from ..Utilities import injector
from ..Objects.Serialization import InternalStateBuilder


class GeneralizedResultStateBuilder(InternalStateBuilder):
    """Class that returns the internal state of a *GeneralizedResult*."""

    def save(self, result):
        """Return the internal state of a *GeneralizedResult* to be pickled.

        Arguments:
            result (*GeneralizedResult*): The *GeneralizedResult* object to be pickled.

        Returns:
            *InternalStateBuilder*: The internal state itself.
        """
        super().save(result)
        self._st["numbering"] = result.getDOFNumbering()
        self._st["generalized_numbering"] = result.getGeneralizedDOFNumbering()

        return self

    def restore(self, result):
        """Restore the *DataStructure* content from the previously saved internal
        state.

        Arguments:
            result (*DataStructure*): The *DataStructure* object to be restored.
        """
        super().restore(result)
        result.build()
        result.setDOFNumbering(self._st["numbering"])
        result.setGeneralizedDOFNumbering(self._st["generalized_numbering"])


@injector(HarmoGeneralizedResult)
class ExtendedHarmoGeneralizedResult:
    cata_sdj = "SD.sd_dyna_gene.sd_dyna_gene"
    internalStateBuilder = GeneralizedResultStateBuilder


@injector(TransientGeneralizedResult)
class ExtendedTransientGeneralizedResult:
    cata_sdj = "SD.sd_dyna_gene.sd_dyna_gene"
    internalStateBuilder = GeneralizedResultStateBuilder

    def _check_input_inoli(self, inoli):
        if inoli == -1:
            print(
                "Nonlinearity index not specified, by default the first nonlinearity",
                " will be considered.",
            )
            inoli = 1
        nbnoli = self._nb_nonl()
        if nbnoli == 0:
            raise ValueError("Linear calculation, no information can be retrieved.")
        if (inoli <= 0) or (inoli > nbnoli):
            raise ValueError(
                "The nonlinearity index should be a comprised "
                "between 1 and %d, the total number of "
                "nonlinearities." % nbnoli
            )
        return inoli

    def FORCE_RELATION(self, inoli=-1):
        """
        Returns a 1D numpy array giving the evolution of the forces defined
        as displacement or velocity relationships
        """
        inoli = self._check_input_inoli(inoli)

        nltypes = self._type_nonl()
        if not (nltypes[inoli - 1] in ("RELA_EFFO_DEPL", "RELA_EFFO_VITE")):
            self.INFO_NONL()
            raise TypeError(
                "The chosen nonlinearity index (%d) does not"
                " correspond to a RELA_EFFO_DEPL or RELA_EFFO_VITE'"
                " nonlinearity\nThese are the only nonlinearities that"
                " calculate and save a relationship defined force." % inoli
            )

        vint = self.VARI_INTERNE(inoli, describe=False)

        # The relationship defined forces are saved in position 2  for
        # RELA_EFFO_DEPL and RELA_EFFO_VITE nonlinearities
        return vint[:, 1]

    def FORCE_AXIALE(self, inoli=-1):
        """
        Returns a 1D numpy array giving the evolution of the axial force at
        the archived instants
        """

        inoli = self._check_input_inoli(inoli)

        nltypes = self._type_nonl()
        if not (nltypes[inoli - 1] in ("ANTI_SISM", "DIS_VISC", "DIS_ECRO_TRAC", "CHOC_ELAS_TRAC")):
            self.INFO_NONL()
            raise TypeError(
                "The chosen nonlinearity index (%d) does not correspond to a :\n"
                "  ANTI_SISM, DIS_VISC, DIS_ECRO_TRAC, CHOC_ELAS_TRAC nonlinearity\n",
                "These are the only nonlinearities that calculate and save an axial force."
                % (inoli),
            )

        vint = self.VARI_INTERNE(inoli, describe=False)
        #
        if nltypes[inoli - 1] in ["ANTI_SISM", "CHOC_ELAS_TRAC"]:
            # The axial forces are saved in position 1 for ANTI_SISM, CHOC_ELAS_TRAC
            return vint[:, 0]
        elif nltypes[inoli - 1] in ["DIS_VISC", "DIS_ECRO_TRAC"]:
            # The axial forces are saved in position 8 for DIS_VISC, DIS_ECRO_TRAC
            return vint[:, 7]
        #
        return None
