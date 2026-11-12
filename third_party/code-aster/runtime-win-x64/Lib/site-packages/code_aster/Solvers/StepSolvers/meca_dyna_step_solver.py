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

from ...Utilities import logger, no_new_attributes
from ..Basics import ProblemType
from ..TimeIntegrators import IntegratorType, TimeScheme
from .base_step_solver import BaseStepSolver


class MecaDynaStepSolver(BaseStepSolver):
    """Solves a step, loops on iterations."""

    problem_type = ProblemType.MecaDyna
    integrator_type = TimeScheme.Unset
    __setattr__ = no_new_attributes(object.__setattr__)

    @classmethod
    def factory(cls, context):
        """Builder of MecaDynaStepSolver object.

        Args:
            context (Context): Context of the problem.

        Returns:
            instance: New object.
        """
        # FIXME: for multi-steps, see transient-history repository, NLIntegrators.py?ref_type=heads#L329
        assert context.problem_type == cls.problem_type, f"unsupported type: {context.problem_type}"
        oper = context._oper
        assert (
            context.problem_type == oper.problem_type
        ), f"operators not consistent: {oper.problem_type}"
        for kls in cls.__subclasses__():
            logger.debug("candidate for '%s': %s", context.problem_type, kls)
            if kls.integrator_type == oper.integrator_type:
                return kls.builder(context)
        raise TypeError(f"no candidate for cls={cls}, type: {oper.integrator_type}")

    def __init__(self):
        super().__init__()

    def initialize(self):
        """Initialization."""
        super().initialize()
        self.state.deltaU = self.state.createPrimal(self.problem, 0.0)
        self.setInitialState(self.state)

    def setInitialState(self, initial_state):
        """Define the initial state of the integrator.

        Arguments:
            initial_state (PhysicalState): State at the beginning of the iteration.
        """
        return self.oper.setInitialState(initial_state)

    def getInitialState(self):
        """Return the physical state used at the beginning of the iteration.

        Returns:
            PhysicalState: Initial physical state.
        """
        return self.oper.getInitialState()

    @classmethod
    def support(cls, integrator):
        """Tell if the StepSolver supports this kind of integrator.

        Arguments:
            integrator (Integrator): *Integrator* object.

        Returns:
            bool: *True* if the integrator is supported, *False* otherwise.
        """
        return cls.integrator_type == integrator.integrator_type

    @classmethod
    def _getIntegrators(cls, schema):
        """Returns the list of integrators to use.

        Arguments:
            schema (str) : Value of *SCHEMA_TEMPS/SCHEMA* keyword.

        Returns:
            list[IntegratorType]: list of integrator names.
        """
        # could be TRBDF2 and return [Tr, Bdf2]...
        assert schema == "Newmark", schema
        return [IntegratorType.Newmark]
