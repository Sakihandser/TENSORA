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

"""
:py:class:`LinearSolver` --- Base of linear solver objects
**********************************************************
"""

import gc

from ..Cata.Commons.c_solveur import C_SOLVEUR
from ..Objects import (
    GcpcSolver,
    LdltSolver,
    LinearSolver,
    MultFrontSolver,
    MumpsSolver,
    PetscSolver,
)
from ..Utilities import injector, logger, profile


@injector(LinearSolver)
class ExtendedLinearSolver:
    @classmethod
    def factory(cls, command=None, mcf=None, **kwargs):
        """Create the solver object from the SOLVEUR factor keyword.

        Arguments:
            command (str): Command Name (default: "STAT_NON_LINE").
            mcf (list|tuple|dict): Convenient option to pass `(kwargs,)`, the value
                returned for a factor keyword.
            kwargs (dict): Valid SOLVEUR keywords (syntax checked, with defaults).

        Returns:
            :class:`~code_aster.Objects.LinearSolver` (derivated of):
            Instance of a solver.
        """
        if not command:
            command = "STAT_NON_LINE"
        if mcf:
            if isinstance(mcf, (list, tuple)):
                mcf = mcf[0]
            if isinstance(mcf, dict):
                kwargs = mcf
        kwargs["command"] = command
        name = kwargs.get("METHODE")
        for kls in cls.__subclasses__():
            if kls.solverName() == name:
                return kls(**kwargs)
        raise TypeError(f"no candidate for cls={cls}, solver: {name}")

    # add profile to these methods
    factorize = profile(LinearSolver.factorize)
    solve = profile(LinearSolver.solve)


class LinearSolverExt:
    """Base object for LinearSolver."""

    cata_sdj = "SD.sd_solveur.sd_solveur"
    _name = _init = None

    def __init__(self, *args, **kwargs):
        assert len(args) <= 1, "at most one argument is expected"
        self._init(*args)
        command = kwargs.pop("command", "MECA_STATIQUE")
        mcf = C_SOLVEUR(command)
        keywords = dict(METHODE=self._name)
        keywords.update(kwargs)
        mcf.addDefaultKeywords(keywords)
        logger.debug("solver init with: %s", keywords)
        self.setKeywords(keywords)
        self.setCataPath("code_aster.Cata.Commons.c_solveur.C_SOLVEUR_" + command)

    @classmethod
    def solverName(cls):
        """Return the solver name.

        Returns:
            str: Solver name, matching METHODE value.
        """
        return cls._name


@injector(GcpcSolver)
class ExtendedGcpcSolver(LinearSolverExt):
    _name = "GCPC"
    _init = GcpcSolver.__init__


@injector(LdltSolver)
class ExtendedLdltSolver(LinearSolverExt):
    _name = "LDLT"
    _init = LdltSolver.__init__


@injector(MultFrontSolver)
class ExtendedMultFrontSolver(LinearSolverExt):
    _name = "MULT_FRONT"
    _init = MultFrontSolver.__init__


@injector(MumpsSolver)
class ExtendedMumpsSolver(LinearSolverExt):
    _name = "MUMPS"
    _init = MumpsSolver.__init__


@injector(PetscSolver)
class ExtendedPetscSolver(LinearSolverExt):
    _name = "PETSC"
    _init = PetscSolver.__init__
