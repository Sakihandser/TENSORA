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
Definition of objects for coupled simulations with code_aster.
"""
import os

from ..Utilities import logger, no_new_attributes
from ..Utilities import medcoupling as MEDC
from .med_coupler import MEDCoupler
from .mpi_coupler import MPICoupler
from .parameters import SchemeParams
from .ple_utils import pyple_coupler


class ExternalCoupling:
    """Coupled simulation with code_aster and other software with PLE.

    Arguments:
        app (str): Application name (default: "code_aster").
        starter (bool): *True* if this instance starts (it sends first),
            *False* if it receives first (default: "False").
        debug (bool): Enable debugging mode (default: "False")".
    """

    _whoami = _other_app = _starter = None
    _debug = False
    _ple = _MPI = _medcpl = None
    _fields_in = _fields_out = None
    _params = None

    def __init__(self, app="code_aster", starter=False, debug=False):
        self._whoami = app
        self._other_app = None
        self._starter = starter
        self._debug = debug
        self._ple = None
        self._MPI = None
        self._medcpl = None
        self._fields_in = []
        self._fields_out = []
        self._params = SchemeParams()

    def __getstate__(self):
        """Disable pickling"""
        return None

    def sync(self, end_coupling=False):
        """Synchronization with the other application.

        Arguments:
            end_coupling (bool): *True* to stop the coupling loop.

        Returns:
            bool: *True* if the study should terminate.
        """
        return self._ple.sync_coupling_status(end_coupling=end_coupling)

    def log(self, *args, **kwargs):
        """Log messages using the logging function of the coupler object."""
        func = self._ple.log if self._ple else logger
        if self._debug:
            prargs = kwargs.copy()
            prargs.pop("verbosity", None)
            prargs["flush"] = True
            logger.info(*args)
        return func(*args, **kwargs)

    def _init_paramedmem(self, with_app, interface):
        """Initialize ParaMEDMEM coupling.

        Arguments:
            with_app (str): name of coupling application
            interface (tuple(Mesh, list[str])): whole mesh and groups of the interface.
        """

        my_ranks = self._ple.get_app_ranks(self._whoami)
        other_ranks = self._ple.get_app_ranks(with_app)

        # Creating the parallel DEC
        list_dec = []
        conv = {"NODES": MEDC.ON_NODES, "NODES_FE": MEDC.ON_NODES_FE, "CELLS": MEDC.ON_CELLS}
        for _, _, discr in self._fields_in + self._fields_out:
            if conv[discr] not in list_dec:
                list_dec.append(conv[discr])

        if self._starter:
            self._medcpl.init_coupling(ranks1=my_ranks, ranks2=other_ranks, list_dec=list_dec)
        else:
            self._medcpl.init_coupling(ranks1=other_ranks, ranks2=my_ranks, list_dec=list_dec)

        # Define coupling mesh
        self._medcpl.create_mesh_interface(interface[0], interface[1])

        # Define coupled fields
        for name, components, discr in self._fields_in + self._fields_out:
            self._medcpl.add_field(name, components, discr)

    def recv_input_fields(self):
        """Receive the input fields from the other code.

        Returns:
            (dict[*ParaFIELD*]): fields used to define the inputs at the next step.
        """
        names = [name for name, _, _ in self._fields_in]
        return self._medcpl.recv(names)

    def send_output_fields(self):
        """Send the output fields to the other code.

        Arguments:
            outputs (dict[*ParaFIELD*]): fields used to define the inputs of the other code.
        """

        send_field = {}
        for name, _, _ in self._fields_out:
            send_field[name] = self._medcpl.get_field(name)

        self._medcpl.send(send_field)

    def set_parameters(self, params):
        """Set parameters.

        Arguments:
            params (dict): Parameters of the coupling scheme.
        """

        if self._starter:
            self._params.set_values(params)

        self._params.nb_iter = self.MPI.COUPLING_COMM_WORLD.bcast(
            self._starter, 0, "NBSSIT", self._params.nb_iter, self.MPI.INT
        )
        self._params.epsilon = self.MPI.COUPLING_COMM_WORLD.bcast(
            self._starter, 0, "EPSILO", self._params.epsilon, self.MPI.DOUBLE
        )

        if self._starter:
            if self._params.stepper:
                times = self._params.stepper._times
                nb_step = len(times)
            else:
                nb_step = 0
            self.MPI.COUPLING_COMM_WORLD.send(0, "NBPDTM", nb_step, self.MPI.INT)
            if nb_step > 0:
                self.MPI.COUPLING_COMM_WORLD.send(
                    0, "STEP", self._params.init_time, self.MPI.DOUBLE
                )
                for i in range(nb_step):
                    self.MPI.COUPLING_COMM_WORLD.send(0, "STEP", times[i], self.MPI.DOUBLE)
        else:
            nb_step = self.MPI.COUPLING_COMM_WORLD.recv(0, "NBPDTM", self.MPI.INT)

            if nb_step > 0:
                times = [self.MPI.COUPLING_COMM_WORLD.recv(0, "STEP", self.MPI.DOUBLE)]
                for _ in range(nb_step):
                    times.append(self.MPI.COUPLING_COMM_WORLD.recv(0, "STEP", self.MPI.DOUBLE))

                self._params.set_values({"time_list": times})

    def init_coupling(self, with_app):
        """Initialize the coupling with an other application.

        Arguments:
            with_app (str): Name of the other application to be coupled with.
        """
        verbosity = 2 if self._debug else 1
        output = "all" if self._debug else "master"
        LOGDIR = os.environ.get("CA_COUPLING_LOGDIR", "/tmp")
        self._ple = pyple_coupler(verbosity=verbosity, logdir=LOGDIR, output_mode=output)
        self._ple.init_coupling(app_name=self._whoami, app_type="code_aster")

        self._other_app = with_app

        myranks = self._ple.get_app_ranks(self._whoami)
        self.log(f"allocated ranks for {self._whoami!r}: {myranks}", verbosity=verbosity)
        other_ranks = self._ple.get_app_ranks(with_app)
        self.log(f"allocated ranks for {with_app!r}: {other_ranks}", verbosity=verbosity)
        assert other_ranks, f"Application {with_app!r} not found!"
        self._MPI = MPICoupler(self._ple.base_comm, self._ple.my_comm, other_ranks[0], self.log)

        self.log(
            f"{self._whoami!r} coupler created from #{myranks[0]}, "
            f"{with_app!r} root proc is #{other_ranks[0]}"
        )

        self._medcpl = MEDCoupler(logfunc=self.log, debug=self._debug)

    def setup(self, interface, input_fields, output_fields, **params):
        """Initialize the coupling.

        Arguments:
            interface (tuple(Mesh, list[str])): whole mesh and groups of the interface.
            input_fields (list): List of exchanged fields as input.
            output_fields (list): List of exchanged fields as output.
            params (dict): Parameters of the coupling scheme.
        """

        self._fields_in = input_fields
        self._fields_out = output_fields
        self.set_parameters(params)
        self._init_paramedmem(self._other_app, interface)

    def finalize(self):
        """Finalize the coupling."""
        self._ple.finalize()

    def testing(self, exec_iteration, data=None):
        """Execute one iteration without coupling.

        Arguments:
            exec_iteration (func): Function that execute one iteration.
            data (dict[*ParaFIELD*]): fields to use in exec_iteration (default: None)

        Returns:
            dict[*ParaFIELD*]: output fields of exec_iteration function.
        """

        if data is None:
            data = {}
            for name, _, _ in self._fields_in:
                data[name] = None

        output_data = exec_iteration(0, 0.0, 1.0, data, self._medcpl)

        return output_data

    def run(self, solver, **params):
        """Execute the coupling loop.

        Arguments:
            solver (object): Solver contains at least a method run_iteration.
            params (dict): Parameters of the coupling scheme.
        """

        # set parameters
        self.set_parameters(params)

        # initial sync before the loop
        exit_coupling = self.sync()

        stepper = self._params.stepper
        first_start = self._starter
        istep = 0

        while not stepper.isFinished():
            istep += 1
            current_time = stepper.getCurrent()
            delta_time = stepper.getIncrement()
            self.log("coupling step #{0:d}, time: {1:f}".format(istep, current_time))

            for i_iter in range(self._params.nb_iter):

                self.log("coupling iteration #{0:d}, time: {1:f}".format(i_iter, current_time))

                # recv data from the other code
                if first_start:
                    first_start = False
                    input_data = {}
                    for name, _, _ in self._fields_in:
                        input_data[name] = None
                else:
                    input_data = self.recv_input_fields()

                has_cvg = solver.run_iteration(i_iter, current_time, delta_time, input_data)

                # send data to other code
                if self._starter:
                    self.send_output_fields()
                    converged = self.MPI.COUPLING_COMM_WORLD.allreduce(
                        i_iter, "ICVAST", has_cvg, self.MPI.BOOL, self.MPI.LAND
                    )
                else:
                    converged = self.MPI.COUPLING_COMM_WORLD.allreduce(
                        i_iter, "ICVAST", has_cvg, self.MPI.BOOL, self.MPI.LAND
                    )
                    self.send_output_fields()

                if converged:
                    break

                self.log(f"end of iteration.")

            stepper.completed()

            self.log(f"end of time step.")

        # only to avoid deadlock
        if self._starter:
            input_data = self.recv_input_fields()

        self.log(f"coupling completed with exit status: {stepper.isFinished()}")

        return True

    @property
    def mesh_interface(self):
        """Mesh|ParallelMesh: mesh of the interface."""
        return self._medcpl.mesh_interf

    @property
    def mesh(self):
        """Mesh|ParallelMesh: coupled mesh."""
        return self._medcpl.mesh

    @property
    def MPI(self):
        """MPICoupler: like mpi4py but for coupling."""
        return self._MPI

    @property
    def medcpl(self):
        """MEDCoupler: medcoupling coupler."""
        return self._medcpl


class SaturneCoupling(ExternalCoupling):
    """Coupled simulation with code_aster and code_saturne with PLE.

    Arguments:
        app (str): Application name (default: "code_aster").
        debug (bool): Enable debugging mode (default: "False")".
    """

    _use_CFEMDEC = False

    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, app="code_aster", debug=False):
        super().__init__(app, False, debug)

    def init_coupling(self, with_app="code_saturne"):
        """Initialize the coupling with code_saturne.

        Arguments:
            with_app (str): Name of the code_saturne application.
        """

        super().init_coupling(with_app)

    def setup(self, interface, **params):
        """Initialize the coupling.

        The input filed is the fluid pressure and the output fields ate the mesh_displacement
        and the mesh_velocity of the interface.

        These names are impodes by code_saturne.

        Arguments:
            interface (tuple(Mesh, list[str])): whole mesh and groups of the interface.
            params (dict): Parameters of the coupling scheme.
        """

        if interface[0].getDimension() != 3:
            raise RuntimeError("The mesh has to be 3D.")

        self.set_parameters(params)

        # need mecoupling >= 9.16.0 to use InterpKernelDECWithOverlap
        # remove PMM.InterpKernelDEC later
        node_typ = "NODES"
        if self._medcpl.supportOverlap():
            node_typ = "NODES_FE"

        if self._use_CFEMDEC:
            fieldType = "NODES_FE"
        else:
            fieldType = "CELLS"

        self._fields_in = [("boundary_stress", ["FX", "FY", "FZ"], fieldType)]
        self._fields_out = [
            ("mesh_displacement", ["DX", "DY", "DZ"], node_typ),
            ("mesh_velocity", ["DX", "DY", "DZ"], node_typ),
        ]
        self._init_paramedmem(self._other_app, interface)

    def set_parameters(self, params):
        """Set parameters. Received values from code_saturne.

        Arguments:
            params (dict): Parameters of the coupling scheme (not used).

        Returns:
            (bool): True if the computation is a success else False.
        """

        self._use_CFEMDEC = bool(self.MPI.COUPLING_COMM_WORLD.recv(0, "ALGOP", self.MPI.INT))

        self._params.nb_iter = self.MPI.COUPLING_COMM_WORLD.recv(0, "NBSSIT", self.MPI.INT)
        self._params.adapt_step = bool(self.MPI.COUPLING_COMM_WORLD.recv(0, "TADAPT", self.MPI.INT))

        self._params.epsilon = self.MPI.COUPLING_COMM_WORLD.recv(0, "EPSILO", self.MPI.DOUBLE)
        init_time = self.MPI.COUPLING_COMM_WORLD.recv(0, "TTINIT", self.MPI.DOUBLE)
        final_time = self.MPI.COUPLING_COMM_WORLD.recv(0, "TTMAX", self.MPI.DOUBLE)
        delta_t = self.MPI.COUPLING_COMM_WORLD.recv(0, "PDTREF", self.MPI.DOUBLE)

        self._params.set_values(
            {"init_time": init_time, "final_time": final_time, "delta_t": delta_t, "nb_step": 1}
        )

    def run(self, solver):
        """Execute the coupling loop.

        Arguments:
            solver (object): Solver contains at least a method run_iteration.

        Returns:
            (bool): True if the computation is a success else False.
        """

        current_time = self._params.init_time
        delta_time = self._params.delta_t
        delta_one = self._params.final_time - self._params.init_time
        completed = exit_coupling = False
        istep = 0

        if not self._params.adapt_step:
            self.sync(end_coupling=False)

        while not completed and not exit_coupling:
            istep += 1
            # for the moment the time_step is controlled by code_saturne
            # modify delta one to adapt code_saturne time_step
            self.MPI.COUPLING_COMM_WORLD.send(istep, "DTAST", delta_one, self.MPI.DOUBLE)
            delta_time = self.MPI.COUPLING_COMM_WORLD.recv(istep, "DTCALC", self.MPI.DOUBLE)
            current_time += delta_time

            self.log("coupling step #{0:d}, time: {1:f}".format(istep, current_time))

            for i_iter in range(self._params.nb_iter):

                self.log("coupling iteration #{0:d}, time: {1:f}".format(i_iter, current_time))

                # recv data from code_saturne
                input_data = self.recv_input_fields()
                assert len(input_data) == 1

                solver.run_iteration(i_iter, current_time, delta_time)

                # received cvg
                converged = bool(self.MPI.COUPLING_COMM_WORLD.recv(istep, "ICVAST", self.MPI.INT))

                # send results to code_saturne
                self.send_output_fields()

                if converged:
                    break

            completed = current_time >= self._params.final_time
            if not self._params.adapt_step:
                exit_coupling = self.sync(end_coupling=completed)
            else:
                exit_coupling = completed

            self.log(f"end of time step with status: {exit_coupling}")

        exit_coupling = self.sync(end_coupling=True)

        self.log(
            "coupling {0} with exit status: {1}".format(
                "completed" if completed else "interrupted", exit_coupling
            )
        )

        return exit_coupling

    def export_displacement(self, displ):
        """Export displacement field

        Arguments:
            displ (*FieldOnNodes*): Displacement field.
        """

        self._medcpl.export_displacement("mesh_displacement", displ)

    def export_velocity(self, velocity):
        """Export displacement field

        Arguments:
            velocity (*FieldOnNodes*): Velocity field.
        """

        self._medcpl.export_velocity("mesh_velocity", velocity)

    def import_fluidLoad(self, model, time):
        """Import fluid load

        Arguments:
            model (Model): Mechanical model.
            time (float): Time of assignment.

        Returns:
            *LoadResult*: surface forces load.
        """

        fluid = self._medcpl.get_field("boundary_stress")
        return self._medcpl.import_fluidforces(fluid, model, time)
