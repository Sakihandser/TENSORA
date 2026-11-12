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
This module gives common utilities for PLE.

Need only pyple package.
"""

try:
    from ple.pyple_coupler import pyple_coupler

    pyple_coupler = pyple_coupler

except ImportError:

    import logging

    from mpi4py import MPI

    class pyple_coupler:
        """
        This class is an emulation of ple.pyple_coupler if it is not present.

        The same API than ple.pyple_coupler is used.

        It is equivalent to ``from ple.pyple_coupler import pyple_coupler``.
        """

        def __init__(self, verbosity=1, logdir=None, output_mode="master"):
            """Initialzation.

            Arguments:
                verbosity (int) : log verbosity level (default=1)
                                  1:info level
                                  2:debug level
                                  If negative value, no output.
                logdir (str) : User defined directory name for the logfile.
                               Default is None, use the current working directory.
                output_mode (str) : Log output mode. Options are "all" or "master"
                                    default is "master".
            """
            self.base_comm = None
            self.my_comm = None
            self.verbosity = verbosity
            self.logdir = logdir
            self.output_mode = output_mode
            self.app_ranks = {}
            self.init_log()

        def init_log(self):
            """Init the log file."""

            self.logger = logging.getLogger("PyPLE")

            if self.verbosity == 1:
                self.logger.setLevel(logging.INFO)
            else:
                self.logger.setLevel(logging.DEBUG)

        def init_coupling(self, app_name, app_type=None):
            """Start the coupling communicator based on the PLE coupling library
            of code_saturne.

            Arguments:
                app_name (str): name of the other application.
                app_type (str): type of application (default=None).
            """

            self.app_name = app_name
            self.base_comm = MPI.COMM_WORLD

            rank = self.base_comm.rank

            # split the global communicator
            color = 0
            for letter in app_name:
                color += ord(letter)

            self.my_comm = self.base_comm.Split(color, rank)
            assert self.my_comm.size < self.base_comm.size

            # send name, root, n_rank
            mapping = self.base_comm.allgather({self.app_name: {self.my_comm.rank: rank}})

            app_ranks = {}
            for id in mapping:
                for app_name, ranks in id.items():
                    if app_name not in app_ranks:
                        app_ranks[app_name] = {}
                    for loc, glob in ranks.items():
                        app_ranks[app_name][loc] = glob

            self.app_ranks = {}
            for name in app_ranks.keys():
                ranks = app_ranks[name]
                self.app_ranks[name] = len(ranks) * [None]
                for loc, glob in ranks.items():
                    self.app_ranks[name][loc] = glob

        def get_app_ranks(self, app_name):
            """Retrieve the ranks in MPI_COMM_WORLD of a given app.

            Arguments:
                app_name (str): name of the app.

            Returns:
                list[int]: list of rank used for the application.
            """

            return self.app_ranks[app_name]

        def sync_coupling_status(self, end_coupling=False):
            """Synchronize with other application.

            Arguments:
                end_coupling (bool): Flag to force the end of the coupled run (default=False).

            Returns:
                (bool): Returns exit_status which tells us if the coupling needs to stop.
            """

            return self.base_comm.allreduce(end_coupling, op=MPI.LOR)

        def log(self, msg, verbosity=0):
            """Write a message to the log file.

            Arguments:
                msg (str): message to be printed
                verbosity: verbosity level
            """

            if verbosity == 0:
                self.logger.info(msg)
            elif verbosity > 0:
                self.logger.debug(msg)

        def finalize(self):
            self.app_ranks = {}
            self.my_comm = None
