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

from ..Basics import ProblemType as PBT
from .base_operators import BaseOperators


class MecaStatOperators(BaseOperators):
    """Object that provides operators to solve quasi-static mechanics."""

    problem_type = PBT.MecaStat

    def getLagrangeScaling(self, matrix_type):
        """Returns Lagrange scaling.

        Arguments:
            matrix_type (str): type of matrix used.
        """
        if self._lagr_scaling is None:
            self._first_jacobian = self.getJacobian(matrix_type)
        return self._lagr_scaling

    def getResidual(self, scaling=1.0):
        """Compute R(u, Lagr) = - (Rint(u, Lagr) + Rcont(u, Lagr) - Rext(u, Lagr)).

        This is not the true residual but the opposite.

        Arguments:
            scaling (float): Scaling factor for Lagrange multipliers (default: 1.0).

        Returns:
            tuple (Residuals(), FieldOnCellsReal, FieldOnCellsReal):
            Tuple with residuals, internal state variables (VARI_ELGA),
            Cauchy stress tensor (SIEF_ELGA).
        """
        resi_state, internVar, stress = super().getResidual(
            scaling=scaling, tmp_internVar=self._tmp_internVar
        )
        self._tmp_stress = stress
        self._tmp_internVar = internVar
        return resi_state

    def getJacobian(self, matrix_type):
        """Compute K(u) = d(Rint(u) - Rext(u)) / du

        Arguments:
            matrix_type (str): type of matrix used.

        Returns:
            AssemblyMatrixDisplacementReal: Jacobian matrix.
        """
        if self._first_jacobian is not None:
            jacobian = self._first_jacobian
            self._first_jacobian = None
        else:
            jacobian = super().getStiffnessJacobian(matrix_type, tmp_internVar=self._tmp_internVar)
            self._lagr_scaling = jacobian.getLagrangeScaling()
        return jacobian
