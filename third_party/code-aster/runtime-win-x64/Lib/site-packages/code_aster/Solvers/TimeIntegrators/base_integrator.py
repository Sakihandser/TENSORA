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

from abc import abstractmethod
from enum import IntFlag, auto

from ...Utilities import no_new_attributes
from ..Operators.meca_dyna_operators import MecaDynaOperators


class TimeScheme(IntFlag):
    """Time integrator schemes."""

    Unset = auto()
    Implicit = auto()
    Explicit = auto()
    Multiple = auto()


class IntegratorType(IntFlag):
    """Types of time integrators."""

    Unset = auto()
    Newmark = auto()


class BaseIntegrator(MecaDynaOperators):
    """
    Integrator for systems like : M ddX = Fext - Fc(dX) - Fk(X) = funForce(X, dX)
    In case of a linear problem : M ddX = Fext - C dX - K X

    Arguments:
        mass : Mass matrix
        f : difference between external and internal forces
        df : Jacobian matrix of f
    """

    integrator_type = TimeScheme.Unset
    integrator_name = IntegratorType.Unset

    _init_state = _set_up = None
    __setattr__ = no_new_attributes(object.__setattr__)

    @classmethod
    def factory(cls, context):
        """Factory that creates the appropriate object.

        Args:
            context (Context): Context of the problem.

        Returns:
            *BaseIntegrator*: A relevant *BaseIntegrator* object.
        """
        # FIXME: for multi-steps, should probably return a list to build a MultiStepSolver on...
        # see transient-history repository, NLIntegrators.py?ref_type=heads#L329
        assert context.problem_type == cls.problem_type, f"unsupported type: {context.problem_type}"
        integr = context.get_keyword("SCHEMA_TEMPS", "SCHEMA", "").capitalize()
        for kls in cls.__subclasses__():
            if kls.integrator_name.name == integr:
                return kls.builder(context)
        raise TypeError(f"no candidate for cls={cls}, scheme: {integr}")

    def __init__(self):
        super().__init__()
        self._set_up = False
        self._init_state = None

    @property
    def t0(self):
        """Time at the beginning of the step."""
        return self.state.time_prev

    @property
    def dt(self):
        """Returns the current time step"""
        return self.state.time_step

    def getLagrangeScaling(self, matrix_type):
        """Returns Lagrange scaling.

        Arguments:
            matrix_type (str): type of matrix used.

        """

        if self._lagr_scaling is None:
            self._first_jacobian = self.getJacobian(matrix_type)

        return self._lagr_scaling

    def getInitialState(self):
        """Return the physical state used at the beginning of the iteration.

        Returns:
            PhysicalState: Initial physical state.
        """
        return self._init_state

    def setInitialState(self, initial_state):
        """Define the state at the beginning of the iteration.

        Arguments:
            state (PhysicalState): State at the beginning of the iteration.
        """
        self._init_state = initial_state.duplicate()
        if not self._set_up:
            self.setup()

    @abstractmethod
    def initializeStep(self):
        """Define the step parameters."""

    @abstractmethod
    def updateVariables(self, q, dq=None, ddq=None):
        """Update the physical state."""

    @abstractmethod
    def getResidual(self, scaling=1.0):
        """Compute the residue vector."""

    def computeAcceleration(self):
        """Computes the acceleration."""
        force = self.getFunctional(self.t0, self.dt, self.U, self.dU, self.d2U).resi
        if not self._mass.isFactorized():
            self.linear_solver.factorize(self._mass)
        self.state.current.d2U = self.linear_solver.solve(force)

    @property
    def U0(self):
        """Initial primal unknowns."""
        return self._init_state.current.U

    @U0.setter
    def U0(self, field):
        """Set initial primal unknowns.

        Arguments:
            field (FieldOnNodesReal): field value
        """
        self._init_state.current.U = field

    @property
    def dU0(self):
        """Initial derivative of primal unknowns."""
        return self._init_state.current.dU

    @dU0.setter
    def dU0(self, field):
        """Set derivative of initial primal unknowns.

        Arguments:
            field (FieldOnNodesReal): field value
        """
        self._init_state.current.dU = field

    @property
    def d2U0(self):
        """Initial second derivative of primal unknowns."""
        return self._init_state.current.d2U

    @d2U0.setter
    def d2U0(self, field):
        """Set second derivative of initial primal unknowns.

        Arguments:
            field (FieldOnNodesReal): field value
        """
        self._init_state.current.d2U = field

    @property
    def U(self):
        """Current primal unknowns."""
        return self.state.current.U

    @U.setter
    def U(self, field):
        """Set current primal unknowns.

        Arguments:
            field (FieldOnNodesReal): field value
        """
        self.state.current.U = field

    @property
    def dU(self):
        """Current derivative of primal unknowns."""
        return self.state.current.dU

    @dU.setter
    def dU(self, field):
        """Set derivative of current primal unknowns.

        Arguments:
            field (FieldOnNodesReal): field value
        """
        self.state.current.dU = field

    @property
    def d2U(self):
        """Current second derivative of primal unknowns."""
        return self.state.current.d2U

    @d2U.setter
    def d2U(self, field):
        """Set second derivative of current primal unknowns.

        Arguments:
            field (FieldOnNodesReal): field value
        """
        self.state.current.d2U = field

    def setup(self):
        """set up the integrator."""
        self._elem_mass = self._getElemMassMatrix()
        self._mass = self._getMassMatrix()
        self._set_up = True
