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

from ...Objects import DiscreteComputation
from ...Supervis import ConvergenceError
from ...Utilities.mpi_utils import MPI
from ...Utilities import PETSc, no_new_attributes, profile, petscInitialize, removePETScOptions
from .iteration_solver import BaseIterationSolver
from time import time
import os


def Print(*args):
    print(*args, flush=True)


class SNESSolver(BaseIterationSolver):
    """Solves a step using PETSc SNES, loops on iterations."""

    __needs__ = ("problem", "state", "keywords", "oper", "linear_solver")
    solver_type = BaseIterationSolver.SubType.Snes
    _primal_incr = _resi_comp = None
    _scaling = _options = None
    local = snes = fnorm0 = None
    CumulLinIter = Instant = rank = 0
    __setattr__ = no_new_attributes(object.__setattr__)
    # Definition of the return codes of the nonlinear SNES solver
    SNES_SUCCESS = 0
    SNES_FAILURE = -1

    def __init__(self, local=False):
        super().__init__()
        petscInitialize()
        self._primal_incr = self._resi_comp = None
        self._scaling = self._options = None
        self.local = local
        self.snes = None
        self.fnorm0 = None
        self.rank = MPI.ASTER_COMM_WORLD.Get_rank()
        self.CumulLinIter = 0
        self.Instant = 0
        self.InitializeMonitoring()

    def initialize(self):
        """Initialize the object for the next step."""
        self.current_incr = 0
        # self.current_matrix = None  # keep

    def _assembleOperators(self, X, F=None, J=None):
        """
        Assembles the function and its Jacobian outside of the Newton context
            Inputs:
                - X : the position of the evaluation.
            Outputs:
                - F : if not None, it recieves the function evaluation at X.
                - J : if not None, it recieves the Jacobian evaluation at X.
        """
        if not (F or J):
            RuntimeWarning(
                "Neither the function nor the Jacobian " + "is given to the operators assembler"
            )
            return
        self.state.deltaU.fromPetsc(X, local=self.local)
        # ----------------------------- Function evaluation ---------------------------
        if F:
            # Build initial residual
            disc_comp = DiscreteComputation(self.problem)
            residual = self.oper.getResidual(self._scaling)
            # Apply Lagrange scaling
            residual.resi.applyLagrangeScaling(1 / self._scaling)
            # Apply DirichletBC into the residual
            diriBCs = disc_comp.getIncrementalDirichletBC(self.state.time_curr, self.state.U)
            self.current_matrix.applyDirichletBC(diriBCs, residual.resi)
            # Copy to PETSc
            residual.resi.toPetsc(local=self.local).copy(F)
        # ------------------------------ Jacobian evaluation ---------------------------
        if J:
            _matrix = self.oper.getJacobian(self.matrix_type)
            self.current_matrix = _matrix
            self._scaling = self.oper.getLagrangeScaling(self.matrix_type)
            _matrix.toPetsc(local=self.local).copy(J)

    def _evalFunction(self, snes, X, F, update=True):
        # Get the solution increment from PETSc
        if update:
            if snes.getSolutionUpdate().handle:
                self._primal_incr.fromPetsc(snes.getSolutionUpdate(), local=self.local)
            # Increment the solution
            self._primal_incr.applyLagrangeScaling(1 / self._scaling)
            self.state.deltaU += self._primal_incr
        disc_comp = DiscreteComputation(self.problem)
        try:
            residual = self.oper.getResidual(self._scaling)
            snes.appctx = self.SNES_SUCCESS
        except Exception as exc:
            snes.appctx = self.SNES_FAILURE
            snes.setConvergedReason(PETSc.SNES.ConvergedReason.DIVERGED_FNORM_NAN)
            return
        # Apply Lagrange scaling
        residual.resi.applyLagrangeScaling(1 / self._scaling)
        # Apply DirichletBC into the residual
        diriBCs = disc_comp.getIncrementalDirichletBC(self.state.time_curr, self.state.U)
        self.current_matrix.applyDirichletBC(diriBCs, residual.resi)
        # Copy to PETSc
        residual.resi.toPetsc(local=self.local).copy(F)
        # print("internVar=", self.oper._tmp_internVar.getValues()[:40:8], flush=True)

    def _evalJacobian(self, snes, X, J, P):
        if snes.appctx != self.SNES_SUCCESS:
            return
        if self.current_incr % self.update_matr_incr == 0:
            _matrix = self.oper.getJacobian(self.matrix_type)
            self.current_matrix = _matrix
            self._scaling = self.oper.getLagrangeScaling(self.matrix_type)
            _matrix.toPetsc(local=self.local).copy(P)
        self.current_incr += 1
        if J != P:
            J.assemble()  # matrix-free operator
        return PETSc.Mat.Structure.SAME_NONZERO_PATTERN

    def initSNES(self):
        if self.snes and self.local:
            return
        self.oper.initialize()

        self._scaling = self.oper.getLagrangeScaling(self.matrix_type)
        self.current_matrix = self.oper.first_jacobian

        p_jac = self.current_matrix.toPetsc(local=self.local)

        snes = PETSc.SNES().create(comm=p_jac.comm)
        # set a prefix if the solver is local in order to conveniently set options
        if self.local:
            snes.prefix = "lsnes_"
        self.snes = snes

        # register the function in charge of
        # computing the nonlinear residual
        p_resi = p_jac.getVecRight()
        p_resi.set(0)

        self._primal_incr = self.state.deltaU.copy()

        snes.setFunction(self._evalFunction, p_resi)
        snes.setJacobian(self._evalJacobian, p_jac)

        def _monitor(snes, its, fgnorm):
            self.fnorm0 = self.fnorm0 if its else fgnorm
            self.logManager.printConvTableRow(
                [its, fgnorm / self.fnorm0, fgnorm, " - ", self.matrix_type]
            )
            # If Aster snes monitor is enabled
            monitor_enabled = os.getenv("ASTER_SNES_MONITOR", "false").lower() == "true"
            if monitor_enabled:
                # Add the linear iterations performed at this nonlinear iteration
                self.CumulLinIter += snes.getKSP().getIterationNumber()

        snes.setMonitor(_monitor) if not self.local else None

        rtol = self.get_keyword("CONVERGENCE", "RESI_GLOB_RELA")
        atol = self.get_keyword("CONVERGENCE", "RESI_GLOB_MAXI", 1.0e-24)
        maxiter = self.get_keyword("CONVERGENCE", "ITER_GLOB_MAXI")
        snes.setTolerances(rtol=rtol, atol=atol, max_it=maxiter)

        OptDB = PETSc.Options()
        if not self._options:
            self.linear_solver.build()
            self._options = self.linear_solver.getPetscOptions()
        OptDB.insertString(self._options)
        snes.setFromOptions()

    @profile
    def solve(self, current_matrix):
        """Solve a step with SNES.

        Raises:
            *ConvergenceError* exception in case of error.
        """

        self.initSNES()

        snes = self.snes
        p_resi, _ = snes.getFunction()

        # solve the nonlinear problem
        b, x = None, p_resi.copy()
        x.set(0)  # zero initial guess

        # Solves with time monitoring
        t = time()
        snes.solve(b, x)
        time_exec = time() - t

        # Increment instant
        self.Instant += 1

        # Write monitoring data in the log file
        self.SnesAsterMonitor(snes, time_exec)

        if snes.getConvergedReason() < 0:
            raise ConvergenceError("MECANONLINE9_7")

        self.oper.finalize()

        if not self.local:
            snes.destroy()
            # delete options from database
            removePETScOptions(self._options)

        return self.current_matrix

    def SnesAsterMonitor(self, snes, time_exec):
        """
        Writes monitoring data in the log file
        """
        nonlinear_iters = snes.getIterationNumber()
        logFile_Path = os.getenv("ASTER_SNES_LOGFILE")
        if logFile_Path:  # Check if logFile_Path is not None or an empty string
            try:
                if self.rank == 0:
                    with open(logFile_Path, "a") as file:
                        # Write data to the file
                        file.write(
                            f"{self.Instant},{nonlinear_iters},{self.CumulLinIter},{time_exec},\n"
                        )
            except Exception as e:
                print(f"Error writing to log file '{logFile_Path}': {e}")
        else:
            print("No log filename specified; logging is disabled.")
        self.CumulLinIter = 0

    def InitializeMonitoring(self):
        """ "
        Monitors each SNES solve
        """
        monitor_enabled = os.getenv("ASTER_SNES_MONITOR", "false").lower() == "true"
        logFile_Path = os.getenv("ASTER_SNES_LOGFILE")
        if monitor_enabled:
            if logFile_Path:
                try:
                    if self.rank == 0:
                        with open(logFile_Path, "w") as file:
                            # Write headers
                            file.write(
                                "Instant_De_Calcul,Itérations_Nonlinéaire,Itérations_Linéaire,Temps_Execution\n"
                            )
                except Exception as e:
                    print(f"Error writing to log file '{logFile_Path}': {e}")
            else:
                print("No log filename specified; logging is disabled.")
        else:
            print("Monitor is disabled by environment variable.")

    def _get(self, keyword, parameter=None, default=None):
        """Return a keyword value"""
        args = self.param
        if parameter is not None:
            if args.get(keyword) is None:
                return default
            return _F(args[keyword])[0].get(parameter, default)

        return args.get(keyword, default)
