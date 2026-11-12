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
This module gives common utilities for MPI communications.

Need only mpi4py package.
"""

from array import array

from ..Utilities.logger import logger
from ..Utilities.mpi_utils import MPI


class MPICoupler:
    """
    This class MPICoupler is an encapsulation of MPI communication
    between intra/inter software.

    The same API than mpi4py is used.

    Arguments:
        comm (*MPI.Comm*): communicator between applications.
        sub_comm (*MPI.Comm*): sub-communicator for the application.
        other_root (int): root of the other application.
        log (logger): logger (default: None).
    """

    DOUBLE = MPI.DOUBLE
    INT = MPI.INT
    CHAR = MPI.CHAR
    BOOL = MPI.BOOL

    LAND = MPI.LAND


    class MPIComm:
        def __init__(self, comm, sub_comm, other_root, log):
            self.comm = comm
            self.sub_comm = sub_comm
            self._other_root = other_root
            self.log = log

            # Buffers persistants
            self._buf_int = array('i', [0])
            self._buf_double = array('d', [0.0])
            self._buf_bool = array('i', [0])


        def _get_buffer(self, typ):
            if typ == MPICoupler.INT:
                return self._buf_int
            elif typ == MPICoupler.DOUBLE:
                return self._buf_double
            elif typ == MPICoupler.BOOL:
                return self._buf_bool
            else:
                raise RuntimeError(f"Unsupported MPI type {typ}")


        def recv(self, iteration, name, typ):
            """Receive a scalar parameter.

            Arguments:
                iteration (int): Iteration number.
                name (str): Expected parameter name.
                typ (:py:class:`~MPICoupler.INT`|:py:class:`~MPICoupler.DOUBLE`): Type of MPI data.

            Returns:
                int|double: Received value of the parameter.
            """

            value = None

            if self.sub_comm.rank == 0:
                self.log(
                    f"waiting for parameter {name!r} from proc #{self._other_root}...",
                    verbosity=2,
                )

                args = dict(source=self._other_root, tag=iteration)
                buf = self._get_buffer(typ)
                self.comm.Recv(buf, **args)
                value = buf[0]

                self.log(f"received parameter {name!r}: {value}", verbosity=2)

            # Broadcast scalaire Python
            value = self.sub_comm.bcast(value, root=0)
            self.log(f"receive parameter {name!r} (iteration {iteration}): {value}")
            return value

        def send(self, iteration, name, value, typ):
            """Send a scalar parameter.

            Arguments:
                iteration (int): Iteration number.
                name (str): Parameter name.
                value (int|double): Value of the parameter.
                typ (:py:class:`~MPICoupler.INT`|:py:class:`~MPICoupler.DOUBLE`): Type of MPI data.
            """

            self.log(f"send parameter {name!r} (iteration {iteration}): {value}")

            if self.sub_comm.rank == 0:
                args = dict(dest=self._other_root, tag=iteration)
                buf = self._get_buffer(typ)
                buf[0] = value
                self.comm.Send(buf, **args)

            self.sub_comm.Barrier()

        def bcast(self, root, iteration, name, value, typ):
            """Broadcast a parameter between root and receiver.

            Arguments:
                root (bool): root or not ?
                iteration (int): Iteration number.
                name (str): Parameter name.
                value (int|double): Value of the parameter.
                typ (:py:class:`~MPICoupler.INT`|:py:class:`~MPICoupler.DOUBLE`): Type of MPI data.

            Returns:
                (int|double): broadcasted value.
            """

            if root:
                self.send(iteration, name, value, typ)
            else:
                value = self.recv(iteration, name, typ)

            return value

        def allreduce(self, iteration, name, value, typ, op):
            """Allreduce a parameter between root and receiver.

            Arguments:
                root (bool): root or not ?
                iteration (int): Iteration number.
                name (str): Parameter name.
                value (int|double): Value of the parameter.
                typ (:py:class:`~MPICoupler.BOOL`): Type of MPI data.

            Returns:
                (bool): broadcasted value.
            """

            self.log(f"allreduce parameter {name!r} (iteration {iteration}): {value}")

            if typ == MPICoupler.BOOL:
                buf = self._get_buffer(MPICoupler.INT)
                buf[0] = int(value)
                self.comm.Allreduce(MPI.IN_PLACE, buf, op)
                return bool(buf[0])

            raise NotImplementedError()

    def __init__(self, comm, sub_comm, other_root, logfunc=None):
        self.log = logfunc if logfunc else logger
        self.cpl_comm = self.MPIComm(comm, sub_comm, other_root, self.log)

    @property
    def ASTER_COMM_WORLD(self):
        """*MPI.Comm*: (sub-)communicator for the application."""
        return self.cpl_comm.sub_comm

    @property
    def COMM_WORLD(self):
        """*MPI.Comm*: global communicator for all applications."""
        return self.cpl_comm.comm

    @property
    def COUPLING_COMM_WORLD(self):
        """*MPI.Comm*: communicator between applications."""
        return self.cpl_comm
