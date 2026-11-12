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

from abc import ABC, abstractmethod

from ...Objects import HHO, PostProcessing


class BaseHook(ABC):
    """Base class to define hooks"""

    def __init__(self) -> None:
        self._enabled = None

    def __call__(self, nl_oper):
        """Entrypoint of hook object"""
        if self._enabled is None:
            self.setup(nl_oper)
        if not self._enabled:
            return
        self.run(nl_oper)

    def setup(self, nl_oper):
        """Setup function: default implementation always enables the hook."""
        self._enabled = True

    @abstractmethod
    def run(self, nl_oper):
        """Execute the hook

        Args:
            nl_oper (NonLinearOperator): Non linear operator
        """


class Annealing(BaseHook):
    """This object deals with annealing.

    This class can be used to calculate the mechanical state after annealing for
    non-linear mechanical calculations.

    It does:

    ..math::

        NewInternVar^{n} = f( InterVar^{n}, t^{n-1}, t^{n}, ExtVar^{n-1}, ExtVar^{n})
    """

    def setup(self, nl_oper):
        """Setup function"""
        self._enabled = nl_oper.problem.getBehaviourProperty().hasAnnealing()

    def run(self, nl_oper):
        """Execute the hook

        Args:
            nl_oper (NonLinearOperator): Non linear operator
        """
        try:
            previous = nl_oper.state.getState(-1)
        except IndexError:
            # No post-pro at initial step
            return
        current = nl_oper.state
        post_process = PostProcessing(nl_oper.problem)
        internVar_anneal = post_process.computeAnnealing(
            current.internVar,
            previous.time_curr,
            current.time_curr,
            previous.externVar,
            current.externVar,
        )
        current.set("VARI_ELGA", internVar_anneal)
        current.internVar = internVar_anneal


class ComputeHydr(BaseHook):
    """Hook to compute HYDR_ELGA."""

    def setup(self, nl_oper):
        """Setup function"""
        self._enabled = nl_oper.problem.getBehaviourProperty().hasBehaviour("THER_HYDR")

    def run(self, nl_oper):
        """Execute the hook

        Args:
            nl_oper (NonLinearOperator): Non linear operator
        """
        current = nl_oper.state
        post = PostProcessing(nl_oper.problem)
        try:
            hydr_prev = current.getState(-1).auxiliary["HYDR_ELGA"]
            hydr_curr = post.computeHydration(
                current.U_t, current.U, current.time_prev, current.time_curr, hydr_prev
            )
        except IndexError:
            hydr_curr = current.createFieldOnCells(nl_oper.problem, "ELGA", "HYDR_R")
        current.set("HYDR_ELGA", hydr_curr)


class ComputeStress(BaseHook):
    """This object deals with stess.

    This class can be used to calculate SIEF_ELGA.
    """

    def __init__(self) -> None:
        super().__init__()
        self._post = None

    def setup(self, nl_oper):
        """Setup function"""
        self._enabled = True
        self._post = PostProcessing(nl_oper.problem)

    def run(self, nl_oper):
        """Execute the hook

        Args:
            nl_oper (NonLinearOperator): Non linear operator
        """

        current = nl_oper.state

        strx_elga = None
        if nl_oper.problem.getModel().existsMultiFiberBeam():
            strx_elga = self._post.computeStructuralStress(
                current.U, current.time_curr, current.externVar
            )
            current.set("STRX_ELGA", strx_elga)

        sief_elga = self._post.computeStress(
            current.U, current.time_curr, current.externVar, strx_elga
        )
        current.set("SIEF_ELGA", sief_elga)
        current.stress = sief_elga


class PostHHO(BaseHook):
    """Compute the true primal field from HHO unknowns."""

    def __init__(self) -> None:
        super().__init__()
        self._hho = None

    @property
    @abstractmethod
    def _field_name(self):
        """str: Name of the field to be created"""

    def setup(self, nl_oper):
        """Setup function"""
        self._enabled = nl_oper.problem.getModel().existsHHO()
        self._hho = HHO(nl_oper.problem)

    def run(self, nl_oper):
        """Execute the hook

        Args:
            nl_oper (NonLinearOperator): Non linear operator
        """
        current = nl_oper.state
        hho_field = self._hho.projectOnLagrangeSpace(current.U)
        current.set(self._field_name, hho_field)


class ComputeDisplFromHHO(PostHHO):
    """Compute the displacement field from HHO unknowns."""

    @property
    def _field_name(self):
        """str: Name of the field to be created"""
        return "HHO_DEPL"


class ComputeTempFromHHO(PostHHO):
    """Compute the temperature field from HHO unknowns."""

    @property
    def _field_name(self):
        """str: Name of the field to be created"""
        return "HHO_TEMP"
