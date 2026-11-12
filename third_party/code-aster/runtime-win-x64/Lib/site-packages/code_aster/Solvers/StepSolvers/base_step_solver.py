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

from ...Utilities import no_new_attributes
from ..Basics import ContextMixin, DispatcherMixin, LoggingManager
from ..IterationSolver import BaseIterationSolver


class BaseStepSolver(ABC, ContextMixin, DispatcherMixin):
    """Solves a step, loops on iterations."""

    __needs__ = ("problem", "state", "oper", "linear_solver")
    _iterations_solv = None
    current_matrix = None
    __setattr__ = no_new_attributes(object.__setattr__)

    @classmethod
    def builder(cls, context):
        """Default builder for :py:class:`ContextMixin` object.
        Should be subclassed for non trivial constructor.

        Args:
            context (Context): Context of the problem.

        Returns:
            instance: New object.
        """
        instance = super().builder(context)
        instance._iterations_solv = BaseIterationSolver.factory(context)
        return instance

    def __init__(self):
        super().__init__()
        self.current_matrix = None

    def initialize(self):
        """Initialization."""

    def createLoggingManager(self):
        """Return a logging manager

        Returns:
            LoggingManager: object for logging
        """
        logManager = LoggingManager()
        logManager.addConvTableColumn("NEWTON")
        logManager.addConvTableColumn("RESIDU RELATIF RESI_GLOB_RELA")
        logManager.addConvTableColumn("RESIDU ABSOLU RESI_GLOB_MAXI")
        logManager.addConvTableColumn("RESIDU REFERENCE RESI_REFE_RELA")
        logManager.addConvTableColumn("RESIDU GEOMETRIQUE RESI_GEOM")
        logManager.addConvTableColumn("OPTION ASSEMBLAGE")

        return logManager

    @abstractmethod
    def solve(self):
        """Solve a step.

        Raises:
            *ConvergenceError* exception in case of error.
        """
