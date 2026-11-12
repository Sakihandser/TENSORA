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
from enum import IntFlag, auto

from ...Utilities import no_new_attributes
from ..Basics import ContextMixin, DispatcherMixin


class BaseIterationSolver(ABC, ContextMixin, DispatcherMixin):
    """Solves a step, loops on iterations."""

    class SubType(IntFlag):
        """Types of time integrators."""

        Unset = auto()
        Newton = auto()
        Snes = auto()
        Raspen = auto()

    __needs__ = ("keywords", "oper", "state")
    solver_type = SubType.Unset

    logManager = None
    current_incr = current_matrix = None
    __setattr__ = no_new_attributes(object.__setattr__)

    @classmethod
    def factory(cls, context):
        """Factory that creates the appropriate object.

        Args:
            context (Context): Context of the problem.

        Returns:
            instance: New object.
        """
        method = context.keywords.get("METHODE", default="NEWTON").capitalize()
        for kls in cls.__subclasses__():
            if kls.solver_type.name == method:
                return kls.builder(context)
        raise TypeError(f"no candidate for cls={cls}, method: {method}")

    def __init__(self):
        super().__init__()

    @property
    def matr_prediction(self):
        """str: Type of prediction matrix to be used."""
        return self.get_keyword("NEWTON", "PREDICTION", self.get_keyword("NEWTON", "MATRICE"))

    @property
    def update_matr_incr(self):
        """int: Number of increments between updating matrix."""
        return self.get_keyword("NEWTON", "REAC_ITER", 1)

    def initialize(self):
        """Initialize the object for the next step."""
        self.current_incr = 0
        self.current_matrix = None

    def setLoggingManager(self, logManager):
        """Assign the logging manager.

        Arguments:
            logManager (LoggingManager): Logging manager.
        """
        self.logManager = logManager

    @property
    def matrix_type(self):
        """str: Type of the matrix to be currently used."""
        if self.current_incr == 0:
            matrix_type = "PRED_" + self.matr_prediction
        else:
            matrix_type = self.get_keyword("NEWTON", "MATRICE", "TANGENTE")
        return matrix_type

    @abstractmethod
    def solve(self, current_matrix, callback=None):
        """Solve a step.

        Raises:
            *ConvergenceError* exception in case of error.
        """
