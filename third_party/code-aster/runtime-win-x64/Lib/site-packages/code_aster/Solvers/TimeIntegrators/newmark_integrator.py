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

from ...Utilities import no_new_attributes
from .base_integrator import BaseIntegrator, TimeScheme, IntegratorType


class NewmarkIntegrator(BaseIntegrator):
    """Implementation of Newmark's scheme."""

    integrator_type = TimeScheme.Implicit
    integrator_name = IntegratorType.Newmark

    _gamma = _beta = _J = None
    __setattr__ = no_new_attributes(object.__setattr__)

    @classmethod
    def builder(cls, context):
        """Builder of NewmarkIntegrator object.

        Args:
            context (Context): Context of the problem.

        Returns:
            instance: New object.
        """
        factkw = context.get_keyword("SCHEMA_TEMPS")
        instance = cls(gamma=factkw["GAMMA"], beta=factkw["BETA"])
        instance.context = context
        return instance

    def __init__(self, gamma, beta):
        super().__init__()
        self._gamma = gamma
        self._beta = beta

    def initializeStep(self):
        """Define the step parameters."""
        # formulation en DEPLACEMENT
        beta, gamma = self._beta, self._gamma
        self.U = self.U0.copy()
        self.dU = self.dU0 - gamma / beta * self.dU0 + (1 - gamma / beta / 2) * self.dt * self.d2U0
        self.d2U = self.d2U0 - 1 / beta / self.dt * self.dU0 - 1 / beta / 2 * self.d2U0

    def getJacobian(self, matrix_type):
        """Compute the jacobian matrix.

        Arguments:
            matrix_type (str): type of matrix used.

        Returns:
            AssemblyMatrixDisplacementReal: Jacobian matrix.
        """
        if self._first_jacobian is not None:
            jacobian = self._first_jacobian
            self._first_jacobian = None
        else:
            beta, gamma = self._beta, self._gamma
            K, C = self.getStiffAndDamp(self.t0, self.dt, self.U, self.dU, self.d2U, matrix_type)
            coef_damp = gamma / beta / self.dt
            coef_mass = 1 / beta / self.dt**2
            jacobian = K + coef_damp * C + coef_mass * self._mass
            self._lagr_scaling = K.getLagrangeScaling()
        return jacobian

    def getResidual(self, scaling=1.0):
        """Compute the residue vector."""
        matrix_type = "TANGENTE"
        _, C = self.getStiffAndDamp(self.t0, self.dt, self.U, self.dU, self.d2U, matrix_type)
        force = self.getFunctional(self.t0, self.dt, self.U, self.dU, self.d2U, scaling)
        force_dyna = -self._mass * self.d2U - C * self.dU
        force.resi = force_dyna + force.resi
        return force

    def updateVariables(self, deltaU):
        """Update the physical state."""
        beta, gamma = self._beta, self._gamma
        self.dU += gamma / beta / self.dt * deltaU
        self.d2U += 1 / beta / self.dt**2 * deltaU
