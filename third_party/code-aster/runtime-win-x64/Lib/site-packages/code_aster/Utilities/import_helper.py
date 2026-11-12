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
This module gives wrapper objects to use PETSc, medcoupling and sympy as optional modules.
The modules are actually imported at the first use.
To force the availability just access to an attribute (``__version__`` for example).

Please *always* these mdoules using these wrappers rather than directly
by doing, for example for PETSc: ``from ..Utilities import PETSc``...
"""

try:
    from typing import TYPE_CHECKING
except (ImportError, ModuleNotFoundError):
    TYPE_CHECKING = False

# aslint: disable=C4008
from .ExecutionParameter import disable_fpe


class NoPickling(type):
    __pickling_disabled__ = 1


class _PETScMeta(NoPickling):
    """Meta class for petsc4py wrapping."""

    _init = False
    _mod = None

    def __getattr__(cls, attr):
        if not cls._init:
            import petsc4py
            from petsc4py import PETSc as origin

            cls._init = True
            cls._mod = origin
        return getattr(cls._mod, attr)


class _SLEPcMeta(NoPickling):
    """Meta class for slepc4py wrapping."""

    _init = False
    _mod = None

    def __getattr__(cls, attr):
        if not cls._init:
            import slepc4py
            from slepc4py import SLEPc as origin

            cls._init = True
            cls._mod = origin
        return getattr(cls._mod, attr)


class PETSc(metaclass=_PETScMeta):
    """Wrapper to petsc4py.PETSc"""


class SLEPc(metaclass=_SLEPcMeta):
    """Wrapper to slepc4py.SLEPc"""


class _medcouplingMeta(NoPickling):
    """Meta class for medcoupling module wrapping."""

    _init = False
    _mod = None

    def __getattr__(cls, attr):
        if not cls._init:
            import medcoupling as origin

            cls._init = True
            cls._mod = origin
        return getattr(cls._mod, attr)


class _ParaMEDMEMMeta(NoPickling):
    """Meta class for ParaMEDMEM module wrapping."""

    _init = False
    _mod = None

    def __getattr__(cls, attr):
        if not cls._init:
            import ParaMEDMEM as origin

            cls._init = True
            cls._mod = origin
        return getattr(cls._mod, attr)


class medcoupling(metaclass=_medcouplingMeta):
    """Wrapper to medcoupling"""


class ParaMEDMEM(metaclass=_ParaMEDMEMMeta):
    """Wrapper to ParaMEDMEM"""


class _sympyMeta(NoPickling):
    """Meta class for sympy module wrapping."""

    _init = False
    _mod = None

    def __getattr__(cls, attr):
        if not cls._init:
            with disable_fpe():
                import sympy as origin

            cls._init = True
            cls._mod = origin
        return getattr(cls._mod, attr)


class sympy(metaclass=_sympyMeta):
    """Wrapper to sympy"""


if TYPE_CHECKING:
    import medcoupling
    import sympy
