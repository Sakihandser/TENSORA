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

from ...Objects import DiscreteComputation
from ...Utilities import no_new_attributes, profile
from ..Basics import ContextMixin, DispatcherMixin


class BaseOperators(ABC, ContextMixin, DispatcherMixin):
    """Base object that provides operators to solve the problem."""

    __needs__ = ("problem", "state", "contact")
    problem_type = None
    _first_jacobian = _lagr_scaling = None
    _tmp_stress = _tmp_internVar = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self):
        super().__init__()
        self._first_jacobian = None
        self._lagr_scaling = None
        self._tmp_stress = None
        self._tmp_internVar = None

    def initialize(self):
        """Initializes the operator manager."""
        self._first_jacobian = None
        self._lagr_scaling = None
        self._tmp_stress = None
        self._tmp_internVar = None

    def finalize(self):
        """Finalizes the operator manager."""
        self.state.dual = self._tmp_stress
        self.state.internVar = self._tmp_internVar

    def shouldExecuteIteration(self, iter_idx):
        """Tell if the Newton iteration `iter_idx` should be performed.

        Arguments:
            iter_idx (int): Newton iteration number.

        Returns:
            bool: whether Newton's iteration should be excuted or
            not, even if the solver has converged.
        """
        return False

    @property
    def first_jacobian(self):
        """Returns the first computed Jacobian"""
        assert self._first_jacobian is not None
        return self._first_jacobian

    @profile
    def getResidual(self, scaling=1.0, tmp_internVar=None):
        """Compute R(u, Lagr) = - (Rint(u, Lagr) + Rcont(u, Lagr) - Rext(u, Lagr)).

        This is not the true residual but the opposite.

        Arguments:
            scaling (float): Scaling factor for Lagrange multipliers (default: 1.0).

        Returns:
            tuple (Residuals, FieldOnCellsReal, FieldOnCellsReal):
            Tuple with residuals, internal state variables (VARI_ELGA),
            Cauchy stress tensor (SIEF_ELGA).
        """
        disc_comp = DiscreteComputation(self.problem)
        return disc_comp.getResidual(
            self.state, contact_manager=self.contact, scaling=scaling, tmp_internVar=tmp_internVar
        )

    @profile
    def getStiffnessJacobian(self, matrix_type, tmp_internVar=None):
        """Compute K(u) = d(Rint(u) - Rext(u)) / du

        Arguments:
            matrix_type (str): type of matrix used.

        Returns:
            AssemblyMatrixDisplacementReal: Jacobian matrix.
        """
        disc_comp = DiscreteComputation(self.problem)
        return disc_comp.getTangentMatrix(
            self.state,
            matrix_type=matrix_type,
            contact_manager=self.contact,
            assemble=True,
            tmp_internVar=tmp_internVar,
        )

    @abstractmethod
    def getJacobian(self, matrix_type):
        """Compute K(u) = d(Rint(u) - Rext(u)) / du

        Arguments:
            matrix_type (str): type of matrix used.

        Returns:
            AssemblyMatrix: Jacobian matrix.
        """
