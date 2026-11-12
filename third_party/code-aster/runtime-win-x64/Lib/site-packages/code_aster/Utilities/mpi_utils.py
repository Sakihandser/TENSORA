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
This module gives common utilities for MPI.

Need only mpi4py package.
"""

import warnings
from functools import wraps

from .base_utils import config, force_list
from .ExecutionParameter import ExecutionParameter
from .options import Options


def haveMPI():
    """Tell if the library is built with MPI support.

    Returns:
        bool: *True* if MPI libraries are used, *False* otherwise.
    """
    return config.get("ASTER_HAVE_MPI", 0) == 1


def useHPCMode():
    """Tell if the HPC mode is enabled.

    It is relevant *after* the *ParallelMesh* has been created.

    Returns:
        bool: *True* if MPI is used and HPC mode is enabled.
    """
    return bool(haveMPI() and ExecutionParameter().option & Options.HPCMode)


try:
    import mpi4py.MPI

    class MPIWrap:
        """Minimal wrapper to encourage usage of ASTER_COMM_WORLD."""

        # must be override during initialization
        ASTER_COMM_WORLD = mpi4py.MPI.COMM_WORLD
        ASTER_COMM_SELF = mpi4py.MPI.COMM_SELF

        def __getattr__(self, attr):
            if attr == "COMM_WORLD":
                warnings.warn(
                    "returns ASTER_COMM_WORLD, directly use mpi4py if COMM_WORLD is required",
                    RuntimeWarning,
                    stacklevel=2,
                )
                return self.ASTER_COMM_WORLD
            if attr == "COMM_SELF":
                warnings.warn(
                    "returns ASTER_COMM_SELF, directly use mpi4py if COMM_SELF is required",
                    RuntimeWarning,
                    stacklevel=2,
                )
                return self.ASTER_COMM_SELF
            return getattr(mpi4py.MPI, attr)

        def use_comm_world(self):
            """Does code_aster use all processes?

            Returns:
                bool: True if all processes are used for code_aster.
            """
            return self.ASTER_COMM_WORLD == mpi4py.MPI.COMM_WORLD

    MPI = MPIWrap()

except ImportError:

    class FAKE_COMM_WORLD:
        """
        This class FAKE_COMM_WORLD contains methods for compatibility with
        sequential libraries

        Use MPI.COMM_WORLD as mpi4py to use mpi methods
        Some methods can be missing (add them here with the same name and
        arguments than mpi4py)
        """

        rank = 0
        size = 1

        def __init__(self):
            if haveMPI():
                raise RuntimeError("mpi4py is mandatory for mpi execution")

        def Is_initialized(self):
            """Tell if MPI is initialized."""
            return True

        def Get_rank(self):
            """Return the process rank."""
            return 0

        def Get_size(self):
            """Return the number of processes."""
            return 1

        def Barrier(self):
            """Set a barrier."""
            return

        def bcast(self, data, root=0):
            """Broadcast"""
            return data

        def Bcast(self, data, root=0):
            """Broadcast with buffers."""
            return data

        def gather(self, data, root=0):
            """Gather"""
            return data

        def allreduce(self, data, op):
            """Allreduce"""
            return op(force_list(data))

        def py2f(self):
            """Return the communicator id."""
            return 0

    class MPI:
        """
        This class MPI is an encapsulation of mpi4py for sequential libraries.

        The same API than mpi4py is used.

        It is equivalent to ``from mpi4py import MPI`` of parallel libraries.
        """

        MAX = max
        MIN = min
        SUM = sum
        PROD = sum

        Intracomm = FAKE_COMM_WORLD
        ASTER_COMM_WORLD = COMM_WORLD = FAKE_COMM_WORLD()
        ASTER_COMM_SELF = COMM_SELF = FAKE_COMM_WORLD()


def _generator(mpi_op):
    def decorator(hpc):
        """Decorator that executes a MPI operator on the value returned
        by each processor.

        Args:
            hpc (bool): Tells in which HPC mode the decorator is enabled.
        """

        def dec_mode(func):
            """Second level wrapper"""

            # It is important to test 'useHPCMode()' value inside the wrapper because
            # its value may be not defined during the definition of the function.
            @wraps(func)
            def wrapper(*args, **kwargs):
                """Wrapper"""
                comm = MPI.ASTER_COMM_WORLD
                if comm.size <= 1 or useHPCMode() is not hpc:
                    return func(*args, **kwargs)
                return comm.allreduce(func(*args, **kwargs), op=mpi_op)

            return wrapper

        return dec_mode

    return decorator


mpi_min = _generator(MPI.MIN)
mpi_max = _generator(MPI.MAX)
mpi_sum = _generator(MPI.SUM)
