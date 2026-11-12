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

from libaster import AssemblyMatrixTemperatureReal

from ...Objects import DiscreteComputation
from ...Utilities import no_new_attributes
from ..Basics import ProblemType as PBT
from ..Basics import Residuals
from .base_operators import BaseOperators


class ThermalOperators(BaseOperators):
    """Object that provides operators to solve thermics."""

    problem_type = PBT.Thermal
    _theta = _resi_prev = _resi_temp = _first_iter = _stat_init = None
    __setattr__ = no_new_attributes(object.__setattr__)

    @classmethod
    def builder(cls, context):
        """Builder of ThermalOperators object.

        Args:
            context (Context): Context of the problem.

        Returns:
            instance: New object.
        """
        assert context.problem_type == cls.problem_type, f"unsupported type: {context.problem_type}"
        theta = context.keywords.get("SCHEMA_TEMPS", "THETA")
        stat = context.keywords.get("ETAT_INIT", "STAT") == "OUI"
        instance = cls(theta=theta, stat=stat)
        instance.context = context
        return instance

    def __init__(self, theta=None, stat=None):
        super().__init__()
        self._resi_prev = self._resi_temp = None
        self._theta = theta
        self._first_iter = True
        self._stat_init = stat and theta is not None

    def initialize(self):
        """Initializes the operator manager."""
        super().initialize()
        if not self.isStationary():
            self.computeFirstResidual()

    def finalize(self):
        """Finalizes the operator manager."""
        super().finalize()
        if self._stat_init:
            self.computeFirstResidual(residual=self._resi_temp)
        else:
            self._resi_prev = self._resi_temp

    def shouldExecuteIteration(self, iter_idx):
        """Tell if the Newton iteration `iter_idx` should be performed.

        Arguments:
            iter_idx (int): Newton iteration number.

        Returns:
            bool: whether Newton's iteration should be excuted or
            not, even if the solver has converged.
        """
        return iter_idx == 0 and self._theta is not None

    def isStationary(self):
        """Checks whether it is a stationary or transient case."""
        return self._stat_init or self._theta is None

    def computeFirstResidual(self, residual=None, scaling=1.0):
        """Computes the first residual."""
        if not self._first_iter:
            return

        if residual is None:
            time_curr = self.state.time_curr
            self.state.time_curr = self.state.time_prev
            self._resi_prev = super().getResidual(scaling=scaling)[0]
            self.state.time_curr = time_curr
        else:
            self._resi_prev = residual

        disc_comp = DiscreteComputation(self.problem)
        self._resi_prev.resi_mass = disc_comp.getNonLinearCapacityForces(
            self.state.U_t, self.state.deltaU, self.state.externVar
        )

        self._first_iter = self._stat_init = False

    def getLagrangeScaling(self, matrix_type):
        """Returns Lagrange scaling.

        Arguments:
            matrix_type (str): type of matrix used.

        """

        if self._lagr_scaling is None:
            self._first_jacobian = self.getJacobian(matrix_type)

        return self._lagr_scaling

    def getJacobian(self, matrix_type):
        """Compute the jacobian matrix."""
        if self._first_jacobian is not None:
            jacobian = self._first_jacobian
            self._first_jacobian = None
        else:
            if self.isStationary():
                jacobian = self._getJacobianStat(matrix_type)
            else:
                jacobian = self._getJacobianTrans(matrix_type)
            self._lagr_scaling = jacobian.getLagrangeScaling()
        return jacobian

    def _getJacobianStat(self, matrix_type):
        """Computes the jacobian matrix for the stationary case."""
        return super().getStiffnessJacobian(matrix_type)

    def _getJacobianTrans(self, matrix_type):
        """Computes the jacobian matrix for the transient case."""
        disc_comp = DiscreteComputation(self.problem)

        mass_ther = disc_comp.getTangentCapacityMatrix(
            self.state.U_t, self.state.deltaU, self.state.externVar
        )

        codret, rigi_ther, rigi_ther_dual = disc_comp.getInternalTangentMatrix(self.state)

        rigi_ther_ext = disc_comp.getExternalTangentMatrix(self.state)

        dt, theta = self.state.time_step, self._theta

        elemMatr = []
        elemMatr.append((rigi_ther, theta))
        elemMatr.append((rigi_ther_ext, theta))
        elemMatr.append((rigi_ther_dual, 1.0))
        elemMatr.append((mass_ther, 1.0 / dt))

        jacobian = AssemblyMatrixTemperatureReal(self.problem)
        jacobian.assemble(elemMatr, self.problem.getListOfLoads())

        return jacobian

    def getResidual(self, scaling=1.0):
        """Computes the residual."""
        if self.isStationary():
            residual = self._getResidualStat(scaling)
        else:
            residual = self._getResidualTrans(scaling)
        return residual

    def _getResidualStat(self, scaling=1.0):
        """Computes the residual for the stationary case."""
        residual, internVar, stress = super().getResidual(scaling=scaling)
        self._tmp_stress = stress  # should be named Phi
        self._tmp_internVar = internVar
        if self._stat_init:
            self._resi_temp = residual
        return residual

    def _getResidualTrans(self, scaling=1.0):
        """Computes the residual for the transient case."""
        dt, theta = self.state.time_step, self._theta
        disc_comp = DiscreteComputation(self.problem)

        resi_curr = super().getResidual(scaling=scaling)[0]

        resi_curr.resi_mass = disc_comp.getNonLinearCapacityForces(
            self.state.U_t, self.state.deltaU, self.state.externVar
        )

        residual = Residuals()

        residual.resi_stress = (
            (1.0 / dt) * (resi_curr.resi_mass - self._resi_prev.resi_mass)
            + theta * resi_curr.resi_stress
            + (1.0 - theta) * self._resi_prev.resi_stress
        )
        residual.resi_int = resi_curr.resi_int + residual.resi_stress - resi_curr.resi_stress
        residual.resi_ext = theta * resi_curr.resi_ext + (1.0 - theta) * self._resi_prev.resi_ext
        residual.resi = residual.resi_ext - residual.resi_int

        residual.resi_mass = resi_curr.resi_mass
        residual.resi_dual = resi_curr.resi_dual
        residual.resi_cont = resi_curr.resi_cont

        self._resi_temp = resi_curr

        return residual
