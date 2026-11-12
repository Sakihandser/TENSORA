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

from ...Objects import AssemblyMatrixDisplacementReal, DiscreteComputation
from ...Supervis import IntegrationError
from ..Basics import ProblemType as PBT
from .base_operators import BaseOperators


class MecaDynaOperators(BaseOperators):
    """Base object that provides operators to solve a dynamics problem."""

    problem_type = PBT.MecaDyna
    _mass = _elem_mass = None

    def __init__(self):
        super().__init__()
        self._elem_mass = self._mass = None

    def _getElemMassMatrix(self):
        """Compute the elementary mass matrix."""
        disc_comp = DiscreteComputation(self.problem)
        matr_elem_mass = disc_comp.getMassMatrix(
            time=self.state.time_curr, varc_curr=self.state.internVar
        )
        return matr_elem_mass

    def _getMassMatrix(self):
        """Compute the mass matrix."""
        mass_matr = AssemblyMatrixDisplacementReal(self.problem)
        mass_matr.assemble(self._elem_mass, self.problem.getListOfLoads())
        return mass_matr

    def getFunctional(self, t, dt, U, dU, d2U, scaling=1.0):
        """Computes the functional."""
        temp_phys_state = self.getTmpPhysicalState(t, dt, U, dU, d2U)
        temp_phys_state.swap(self.state)
        resi_state, internVar, stress = super().getResidual(scaling=scaling)
        self.state.swap(temp_phys_state)
        self._tmp_stress = stress
        self._tmp_internVar = internVar
        return resi_state

    def getStiffAndDamp(self, t, dt, U, dU, d2U, matrix_type):
        """Computes the jacobian."""
        temp_phys_state = self.getTmpPhysicalState(t, dt, U, dU, d2U)
        temp_phys_state.swap(self.state)

        disc_comp = DiscreteComputation(self.problem)

        # Compute elementary matrix
        codret, matr_elem_rigi, matr_elem_dual = disc_comp.getInternalTangentMatrix(
            self.state, matrix_type=matrix_type, assemble=False
        )

        if codret > 0:
            raise IntegrationError("MECANONLINE10_1")

        matr_elem_cont = disc_comp.getContactTangentMatrix(self.state, self.contact)
        matr_elem_ext = disc_comp.getExternalTangentMatrix(self.state)
        self.state.swap(temp_phys_state)

        # Assemble stiffness matrix
        elemMatr = []
        elemMatr.append(matr_elem_rigi)
        elemMatr.append(matr_elem_dual)
        elemMatr.append(matr_elem_cont)
        elemMatr.append(matr_elem_ext)

        rigi_matr = AssemblyMatrixDisplacementReal(self.problem)
        rigi_matr.assemble(elemMatr, self.problem.getListOfLoads())

        # Assemble damping matrix
        matr_elem_damp = disc_comp.getDampingMatrix(
            massMatrix=self._elem_mass,
            stiffnessMatrix=matr_elem_rigi,
            varc_curr=self.state.externVar,
        )

        damp_matr = AssemblyMatrixDisplacementReal(self.problem)
        damp_matr.assemble(matr_elem_damp, self.problem.getListOfLoads())

        return rigi_matr, damp_matr

    def getTmpPhysicalState(self, t, dt, U, dU, d2U):
        """Creates a temporary physical state"""
        # D'où vient le primal step qui doit être utilisée ?
        result = self.state.duplicate()

        result.time_prev = t
        result.time_step = dt
        result.time_curr = t + dt

        result.current.U = U
        result.current.dU = dU
        result.current.d2U = d2U

        return result
