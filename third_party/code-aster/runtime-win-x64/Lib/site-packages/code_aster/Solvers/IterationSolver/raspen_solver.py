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

import warnings
from time import time

import numpy as np
from libaster import asmpi_free, asmpi_get, asmpi_set, asmpi_split
from scipy.sparse.linalg import LinearOperator, eigsh, svds

from ...Objects import redistributePetscMat, applyFactorOnSubBlocks
from ...Supervis import ConvergenceError
from ...Utilities import PETSc, no_new_attributes, profile, removePETScOptions
from ...Utilities.mpi_utils import MPI
from .iteration_solver import BaseIterationSolver
from .snes_solver import SNESSolver

# FIXME write in tmp + result file?
monitoringFilesPaths = {
    # "byRASPENSteps": os.getenv("HOME") + "/RASPENStepsData.txt",
    # "byTimeSteps": os.getenv("HOME") + "/timeStepsData.txt",
    # "byKSPSteps": os.getenv("HOME") + "/kspConvHist.txt",
}

monitoringFilesHeaders = {
    "byRASPENSteps": (
        "# Time_Instant, Glb_Nonlin_Iterations, Loc_Nonlin_Iterations, "
        "Linear_Iterations, Absolute_Error, Relative_Error, "
        "Overlap, Number_of_Subdomains, CoarsePb_Size, Method_Name\n"
    ),
    "byTimeSteps": (
        "# Time_Instant, Nonlinear_Iterations, Linear_Iterations, Overlap, "
        "Number_of_Subdomains, Execution_Time, CoarsePb_Size, Method_Name\n"
    ),
}

# Valid monitoring modes: if append, it add to the existing content of files in monitoringFilesPaths
#                         else, it overwrites these files
MonitoringModes = ["append", "write"]  # default: "append"

optionsAndPetscEquivalents = {
    # String options
    "solverType": "raspen_solver_type",
    "jacType": "raspen_jac_type",
    "coarsePbSide": "raspen_coarse_side",
    "coarseSpaceType": "raspen_coarse_type",
    # Boolean options
    "withCoarsePb": "raspen_with_coarse_pb",
    "withFinalJac": "raspen_with_final_jac",
    "withSubPrecond": "raspen_with_substructuring",
    "withMonitoring": "raspen_monitor",
}

# valid strings for options. "Firsts are default options"
validStringOptions = {
    # String options
    "solverType": ["RASPEN", "RASPIN", "ASPEN", "ASPIN", "RAS", "AS"],  # default: "RASPEN"
    "jacType": ["Exact", "Fd"],  # default: "Exact"
    "coarsePbSide": ["Left", "Right"],  # default: "Left"
    "coarseSpaceType": ["SubdomainSVD", "InterfaceSVD", "Nicolaides"],  # default: "SubdomainSVD"
    # Boolean options
    "withCoarsePb": [False, True],  # default: "False"
    "withFinalJac": [False, True],  # default: "False"
    "withSubPrecond": [False, True],  # default: "False"
    "withMonitoring": [False, True],  # default: "False"
}

Cvr_Rs_Dict = {
    3: "CONVERGED_ATOL",
    # 4: "CONVERGED_ATOL_NORMAL",
    6: "CONVERGED_CG_CONSTRAINED",
    5: "CONVERGED_CG_NEG_CURVE",
    8: "CONVERGED_HAPPY_BREAKDOWN",
    # 0: "CONVERGED_ITERATING",
    4: "CONVERGED_ITS",
    2: "CONVERGED_RTOL",
    1: "CONVERGED_RTOL_NORMAL",
    7: "CONVERGED_STEP_LENGTH",
    -5: "DIVERGED_BREAKDOWN",
    -6: "DIVERGED_BREAKDOWN_BICG",
    -4: "DIVERGED_DTOL",
    -10: "DIVERGED_INDEFINITE_MAT",
    -8: "DIVERGED_INDEFINITE_PC",
    -3: "DIVERGED_MAX_IT",
    -9: "DIVERGED_NANORINF",
    -7: "DIVERGED_NONSYMMETRIC",
    -2: "DIVERGED_NULL",
    -11: "DIVERGED_PCSETUP_FAILED",
    0: "ITERATING",
}


class RASPENSolver(BaseIterationSolver):
    """Solves a step using PETSc SNES, loops on iterations."""

    __needs__ = ("problem", "state", "keywords", "oper", "linear_solver")
    solver_type = BaseIterationSolver.SubType.Raspen
    _scaling = _options = None
    _local_solver = None
    rank = Instant = 0
    __setattr__ = no_new_attributes(object.__setattr__)

    @classmethod
    def builder(cls, context):
        """Builder of RaspenSolver object.

        Args:
            context (Context): Context of the problem.

        Returns:
            instance: New object.
        """
        instance = super().builder(context)
        instance._local_solver = SNESSolver(local=True)
        instance._local_solver.context = context
        return instance

    def __init__(self):
        super().__init__()
        self._scaling = self._options = None
        self._local_solver = None

    def initialize(self):
        """Initialize the object for the next step."""
        super().initialize()
        self._local_solver.initialize()

    def initializeMonitoring(self):
        """ "
        Initialize the monitoring files
        """
        # Check if monitoring is enabled
        opts = PETSc.Options()
        withMonitoring = opts.getBool("raspen_monitor", False)
        monitorMode = opts.getBool("raspen_monitor_mode", "append")
        if monitorMode not in MonitoringModes:
            warnings.warn(
                f"Unknown option {monitorMode} for option 'raspen_monitor_mode', "
                + f"should be in {MonitoringModes}. Program will "
                + f"continue with {MonitoringModes[0]}",
                RuntimeWarning,
            )
        # Wrtie headers in case of empty files
        if withMonitoring and self.rank == 0:
            for type, filePath in monitoringFilesPaths.items():
                try:
                    with open(filePath, "r") as f:
                        num_lines = sum(1 for _ in f)
                        writeHeader = num_lines == 0
                        f.close()
                except FileNotFoundError:
                    writeHeader = True

                if writeHeader or monitorMode == "write":
                    try:
                        fileHeader = monitoringFilesHeaders[type]
                        with open(filePath, "w") as file:
                            # Write headers
                            file.write(fileHeader)
                            file.close()
                    except Exception as e:
                        print(f"Error writing to file '{filePath}': {e}")

    @profile
    def solve(self, current_matrix):
        """Solve a step with SNES.

        Raises:
            *ConvergenceError* exception in case of error.
        """
        self.oper.initialize()
        self._scaling = self.oper.getLagrangeScaling(self.matrix_type)
        self.current_matrix = self.oper.first_jacobian

        p_jac = self.current_matrix.toPetsc(local=True)

        DDPart = DomainDecomposition(self.problem.getMesh(), self.problem.getDOFNumbering())

        local_solver = self._local_solver
        local_solver.initSNES()

        # Initialize monitoring
        self.initializeMonitoring()
        curr_time = 0
        raspen_solver = _RASPENSolver(
            local_solver,
            p_jac,
            self.oper,
            self.matrix_type,
            self.state.deltaU,
            DDPart,
            self.current_incr,
            curr_time,
            comm=DDPart.comm,
        )
        rtol = self.get_keyword("CONVERGENCE", "RESI_GLOB_RELA", 1e-6)
        atol = self.get_keyword("CONVERGENCE", "RESI_GLOB_MAXI", 1e-24)
        maxiter = self.get_keyword("CONVERGENCE", "ITER_GLOB_MAXI", 50)
        raspen_solver.setTolerances(rtol=rtol, atol=atol, maxiter=maxiter)

        # register the function in charge of
        # computing the nonlinear residual
        p_resi = p_jac.getVecRight()
        p_resi.set(0)

        # Manage options
        OptDB = PETSc.Options()
        if not self._options:
            self.linear_solver.build()
            self._options = self.linear_solver.getPetscOptions()
            # Ensure disabled line search for the global snes
            self._options += " -gsnes_snes_linesearch_type basic "
        OptDB.insertString(self._options)
        raspen_solver.glbSnes.setFromOptions()

        # solve the nonlinear problem
        raspen_solver.solve()

        if raspen_solver.glbSnes.getConvergedReason() < 0:
            # delete before exit
            local_solver.snes = None
            raspen_solver.destroyAll()
            raise ConvergenceError("MECANONLINE9_7")

        self.oper.finalize()
        # delete local snes
        local_solver.snes = None
        raspen_solver.destroyAll()
        # delete options from database
        removePETScOptions(self._options)
        return self.current_matrix


class _RASPENSolver:
    def __init__(
        self,
        LocNSL,
        locJac,
        oper,
        matrix_type,
        primalStep,
        DDPart,
        current_incr,
        curr_time,
        comm=MPI.ASTER_COMM_WORLD,
    ):
        # Comm
        self.comm = comm
        # Rank
        self.rank = comm.Get_rank()
        # Nb of subdomains/Proc
        self.size = comm.Get_size()
        # PETSc options
        self.opts = PETSc.Options()
        # Set default tolerances (will be updated by 'setTolerances')
        self.rtol = 1e-6
        self.atol = 1e-24
        self.stol = 1e-24
        self.maxiter = 50
        # Current increment
        self.current_incr = current_incr
        # Current time
        self.curr_time = curr_time
        # Local non-linear Solver
        self.asterLocSnl = LocNSL
        # Operators manager
        self.oper = oper
        # Matrix type
        self.matrix_type = matrix_type
        # Z0 and Z vectors
        self.locSol = locJac.getVecRight()
        self.locSol.set(0)
        self.locSol0 = self.locSol.copy()
        # aster solution
        self.asterGlbSolution = primalStep
        # Domain Decomposition partitioner
        self.DDPart = DDPart
        # Nb of overlap layers
        self.overlap = DDPart.overlap
        # Vecscatter
        self.vecscatter = DDPart.getVecScatter()
        # Reads string options values from Petsc
        self.setUpOptions(optionsAndPetscEquivalents, validStringOptions)
        # Local dofs
        self.local_dofs = DDPart.getLocalDofs()
        # Nonoverlapping dofs in local numbering
        self.locNonOvlpDofs = DDPart.local_interior_dofs
        # Nonoverlapping dofs in global numbering
        self.glbNonOvlpDofs = DDPart.global_interior_dofs
        # Boundary and interior dofs
        self.bdDofs = np.array(DDPart.getLocalBoundaryDofs(), dtype=np.int32)
        # Local boundary size
        self.nbi = len(self.bdDofs)
        if self.nbi == 0:
            self.withCoarsePb = False
        # Global size
        self.glbSize = DDPart.getGlobalSize()
        # Local sizes
        self.locSize = DDPart.getLocalSize()
        # Local snes
        self.locSnes = self.asterLocSnl.snes
        # Logger
        self.Logger = RASPENLogger(self)
        # Verbose
        self.verbose = False
        # Local Jacobian
        [self.Jloc, self.Jploc, [self.JacFunc, _, _]] = self.locSnes.getJacobian()
        # Original function opers assembler
        self.operators = LocNSL._assembleOperators
        # A vector to hold local actions
        self.Yloc = self.locSol.duplicate()
        # Global solution
        self.glbSol = PETSc.Vec().createMPI(self.glbSize, comm=self.comm)
        # Global Res
        self.Res = self.glbSol.duplicate()
        # ------------------------------------------------------------------
        #               Information about neighbours
        #                   is still not used yet
        # ------------------------------------------------------------------
        # # Subdomain neighbours
        # self.neighbours = DDPart.getMyNeighbours(self.Yloc,self.Res)
        # Global Jacobian
        self.J = PETSc.Mat().createPython(self.glbSize, comm=MPI.ASTER_COMM_WORLD)
        # Ghost tools
        DDPart.BuildGhostsTools(self.Yloc, self.Res)
        # Multiplicities
        multiplicity = DDPart.getLocalMultiplicity(self.Yloc, self.Res)
        # Square root of multiplicites
        self.SQMult = np.sqrt(multiplicity)
        # Prefixing local snes
        self.locSnes.prefix = "lsnes_"
        # Local ksp
        self.locKsp = self.locSnes.getKSP()
        # Method name: solverType + coarseSpaceType (if CoarsePb enabled)
        self.methodName = self.solverType
        # Number of singular values to cosnider for coarse problem
        self.nb_svs = 0  # Initialization
        if self.withCoarsePb:
            # Other version of local Jacobians
            self.Jloc0 = self.Jloc.duplicate()
            # Number of singular values retained for each subdomain
            self.nb_svs = self.opts.getInt("raspen_nb_sd_singular_vec", 10)
            self.nb_svs = min((self.nbi - 1), self.nb_svs)
            # Append coarse problem type to methode name
            self.methodName += f"_{self.coarseSpaceType}"
            # Coarse problem solver
            self.GCGC = GalerkinCoarseGridCorrection(self, DDPart)

        # Substructured preconditioner
        if self.withSubPrecond:
            self.Jp = PETSc.Mat().createPython(self.glbSize, comm=MPI.ASTER_COMM_WORLD)
            self.JpCtx = substPrecondCtx(self, self.J)
        else:
            self.Jp = None
        # Global Snes
        self.glbSnes = self.setUpGlobalSnes()
        # Customized convergence test
        self.setGlbSnesConvergenceTest()
        # KSP time measure
        self.tCorrect = self.t_pro = self.tksp = 0
        # Cumulative number of linear solves and inner nonlinear solves
        self.cumulLinIter = self.cumLocNonlinear = 0
        # Assembling time measure and applying diff
        self.asstem = self.applyDiff = 0

    def setUpOptions(self, petscOpts, validOpts):
        """
        Set up the options from petsc options
        """
        for opt, petscOpt in petscOpts.items():
            if opt.startswith("with"):
                petscOptValue = self.opts.getBool(petscOpt, False)
                print(f" OPTION: {petscOpt}, VALUE: {petscOptValue}")
            else:
                petscOptValue = self.opts.getString(petscOpt, False)
            # Option value set to default
            valueToset = validOpts[opt][0]
            if petscOptValue in validOpts[opt]:
                # Take the user valid option
                valueToset = petscOptValue
            elif petscOptValue:
                # Warn user and continue with value by default
                default_value = validOpts[opt][0]
                valid_list = ", ".join(validOpts[opt])
                msg = (
                    f"Unknown option '{petscOptValue}' for '{opt}'.\n"
                    f"Valid options are: {valid_list}.\n"
                    f"Continuing with default: '{default_value}'."
                )
                warnings.warn(msg, RuntimeWarning)
            setattr(self, opt, valueToset)

    def setTolerances(self, rtol=1e-6, atol=1e-24, maxiter=50):
        """
        Set Tolerances
        """
        self.rtol = rtol
        self.atol = atol
        self.maxiter = maxiter

    def setUpGlobalSnes(self):
        """
        Sets up the global snes
        """
        glbSnes = PETSc.SNES().create(comm=MPI.ASTER_COMM_WORLD)
        glbSnes.prefix = "gsnes_"
        # Snes Ksp
        SnesKsp = glbSnes.getKSP()
        # Snes type
        glbSnes.setType("newtonls")
        # Linear solver type
        SnesKsp.setType("gmres")
        SnesKsp.setTolerances(rtol=self.rtol)
        # Linear precond type
        if self.withSubPrecond:
            SnesKsp.setPCSide(PETSc.PC.Side.RIGHT)
            linearPC = SnesKsp.getPC()
            linearPC.setType("python")
            linearPC.setPythonContext(self.JpCtx)
        else:
            SnesKsp.getPC().setType("none")

        # Fix local boundary ddls in Dirichlet case
        self.applyLocalDirichlet()

        # Monitoring functions
        def ksp_monitor(ksp, its, rnom):
            """
            Linear solver monitoring function
            """
            if not monitoringFilesPaths.get("byKSPSteps"):
                return
            if self.rank == 0:
                SnesIter = glbSnes.getIterationNumber()
                if its == 0:
                    self.ksp_rnorm_0 = rnom
                resi_rela = 0 if self.ksp_rnorm_0 == 0 else rnom / self.ksp_rnorm_0
                filePath = monitoringFilesPaths["byKSPSteps"]
                ksp_file = open(filePath, "a")
                ksp_file.write(
                    f"{its} {resi_rela} {SnesIter} {self.size} "
                    + f"{self.overlap} {self.nb_svs} {self.methodName}\n"
                )
                ksp_file.close()

        # Monitoring function
        def monitor(snes, its, fnorm):
            # This function is called at each SNES iteration
            # Compute original function relative error
            Rnorm = self.Fnorm / self.fnorm0
            # Add the linear iterations performed at this nonlinear iteration
            self.cumulLinIter += snes.getKSP().getIterationNumber()
            # Outer iterations logs
            if self.rank == 0:
                self.Logger.print_box(
                    f" Outer Iteration : {its}"
                    + f"   |    Global Residual Norm : {self.Fnorm:.8e}"
                    + f"   |    Relative Residual Norm : {Rnorm:.8e}"
                )
                if self.withMonitoring and monitoringFilesPaths.get("byRASPENSteps"):
                    filePath = monitoringFilesPaths["byRASPENSteps"]
                    # Save data on ConvergenceHistory/data.txt
                    with open(filePath, mode="a") as file:
                        file.write(
                            f"{self.curr_time:.3e} {its} {self.cumLocNonlinear}"
                            + f" {self.cumulLinIter} {self.Fnorm:.3e} {Rnorm:.3e} {self.overlap}"
                            + f" {self.size} {self.nb_svs} {self.methodName}\n"
                        )
                        file.close()

        # Sets outer snes customized monitoring function
        glbSnes.setMonitor(monitor)
        SnesKsp.setMonitor(ksp_monitor)

        # Defining the preconditioned function and jacobian
        def preFunc(snes, X, Y):
            """
            This is the preconditioned function
            """

            # Get currrent iteration
            It = snes.getIterationNumber()
            if self.tksp and self.rank == 0:
                self.tksp = time() - self.tksp
                print("Linear system execution time:", self.tksp, flush=True)
            # Get local solution approximation
            self.vecscatter.scatter(X, self.locSol0, mode="forward")
            # Set the approximation as the initial guess
            self.locSol.getArray()[:] = self.locSol0.getArray()[:]
            # Synchronize code_aster's unknowns
            dx = self.locSnes.getSolutionUpdate()
            # Hack to circumvent the PETSc pointers' nullity if asterLocSnl hasn't start yet
            if dx.handle:
                dx.set(0)
                previous = self.locSnes.getSolution()
                self.asterGlbSolution.fromPetsc(previous, local=True)
                previous.copy(self.locSol0)
            # # We want to recycle this in future computations
            self.originalFunction(X, Y)
            self.Fnorm = Y.norm()
            Converged = self.test_on_original_function(snes, It, None)
            if Converged:
                # No need to go further if convergence is achieved
                return
            if self.withCoarsePb and self.coarsePbSide == "Right":
                self.asterGlbSolution.toPetsc(local=True).copy(self.locSol)
                self.locSnes.computeJacobian(self.locSol, self.Jloc, self.Jploc)
                # Build prolongation operator if not built yet
                if not self.GCGC.ProlongationIsBuilt:
                    prolongBuild = getattr(
                        self.GCGC, "build" + self.coarseSpaceType + "Prolongation"
                    )
                    prolongBuild(It)
                # Apply coarse correction
                self.GCGC.correct(X, Y)
                # Compute Jacobian at the final iterate. IF was not computed
                # in "correct" due to successful convergence check before)
                if self.jacType == "Exact":
                    self.GCGC.saveLocalJac = True
                    self.GCGC.GCSnes.computeJacobian(self.GCGC.Xc, self.GCGC.Jc)
                    self.GCGC.saveLocalJac = False
                    self.GCGC.GCSnes.getKSP().setOperators(self.GCGC.Jc)
                # Add coarse
                Y.axpy(1.0, X)
                # Get local solution approximation
                self.vecscatter.scatter(Y, self.locSol)
            # Local solve
            # -------------------------------------------------
            # - retrieve the current communicator
            mycomm = asmpi_get()
            # - split in single processes
            comm_self = asmpi_split(mycomm, MPI.ASTER_COMM_WORLD.Get_rank(), "self")
            # - change the current communicator
            MPI.ASTER_COMM_WORLD.Barrier()
            asmpi_set(comm_self)
            # - sequential solve
            self.t_sdSolve = -time()
            # before local solve set context to no error
            self.locSnes.appctx = SNESSolver.SNES_SUCCESS
            # solve
            self.locSnes.solve(None, self.locSol)
            # broadcast error
            failed = MPI.ASTER_COMM_WORLD.allreduce(self.locSnes.appctx, op=MPI.MIN)
            if failed != SNESSolver.SNES_SUCCESS:
                self.locSnes.setConvergedReason(PETSc.SNES.ConvergedReason.DIVERGED_FNORM_NAN)
                self.glbSnes.setConvergedReason(PETSc.SNES.ConvergedReason.DIVERGED_FNORM_NAN)
            self.t_sdSolve += time()
            self.t_sdSolve = self.comm.reduce(self.t_sdSolve, op=MPI.MAX, root=0)
            if self.rank == 0:
                print(f"The longest local solve took: {self.t_sdSolve}", flush=True)
            # Number of nonlinear local iteration
            it = self.locSnes.getIterationNumber()
            # # Log coarse snes convergence history
            # self.Logger.log(f"Convergence history of subdomain {self.rank+1}")
            # self.Logger.cleanLogs()
            isDirect = self.locSnes.getKSP().getType() == "preonly"
            cond = ((not isDirect) and it % 2 == 1) or it == 0
            # Coarse problem correction
            if self.withCoarsePb and self.coarsePbSide == "Left":
                self.asterGlbSolution.toPetsc(local=True).copy(self.locSol)
                # self.operators(self.locSol,J=self.Jloc)
                self.locSnes.computeJacobian(self.locSol, self.Jloc, self.Jploc)
                self.locKsp.setOperators(self.Jloc, self.Jploc)
                self.Jloc.copy(self.Jloc0)
                if It == 0 or not self.GCGC.ProlongationIsBuilt:
                    prolongBuild = getattr(
                        self.GCGC, "build" + self.coarseSpaceType + "Prolongation"
                    )
                    prolongBuild(It)
                    self.t_pro += time()
                    print("Time to build prolongation:", self.t_pro, flush=True)
                self.DDPart.restrict(self.locSol)
                Y.set(0.0)
                # Assembles the local parts of the solution to a global solution
                self.vecscatter(self.locSol, Y, mode="reverse", addv=True)
                self.vecscatter(Y, self.locSol)
                Yd = Y.duplicate()
                # Second level correction
                self.comm.Barrier()
                self.tCorrect = -time()
                self.GCGC.correct(Y, Yd)
                self.tCorrect += time()
                self.tCorrect = self.comm.reduce(self.tCorrect, op=MPI.MAX, root=0)
                if self.jacType == "Exact":
                    self.GCGC.GCSnes.computeJacobian(self.GCGC.Xc, self.GCGC.Jc)
                    self.GCGC.GCSnes.getKSP().setOperators(self.GCGC.Jc)
                Y.axpy(1.0, Yd)
                self.originalFunction(Y, Yd)
                Yd.destroy()
                self.vecscatter(Y, self.locSol)

            # Local correction
            C = self.locSol - self.locSol0
            # Add inner nonlinear iterations
            MaxIt = self.comm.reduce(it, op=MPI.MAX, root=0)
            if self.rank == 0:
                self.cumLocNonlinear += MaxIt
            if self.solverType.startswith("RAS"):
                self.DDPart.restrict(C)
            # Add corrections to get residual
            Y.set(0.0)
            self.vecscatter.scatter(C, Y, mode="reverse", addv=True)
            if self.withFinalJac or cond or self.solverType.endswith("IN"):
                # One-level final Jacobian assembling
                w = self.locSnes.getSolution()
                self.locSol.copy(w)
                if self.solverType.endswith("IN"):
                    self.vecscatter.scatter(X + Y, w, mode="forward")
                self.locSnes.computeJacobian(w, self.Jloc, self.Jploc)
                self.locKsp.setOperators(self.Jloc, self.Jploc)

            # -------------------------------------------------
            # - switch back to initial communicator
            MPI.ASTER_COMM_WORLD.Barrier()
            asmpi_free(comm_self)
            asmpi_set(mycomm)
            self.tksp = time()

        def preJac(snes, X, J, Jp):
            """ "
            This is the preconditioned Jacobian
            """
            self.current_incr += 1
            Jctx = JacCtx(self, snes)
            # Set up jacobian of type shell
            J.setPythonContext(Jctx)
            J.setUp()

        glbSnes.setFunction(preFunc, self.Res)
        if self.jacType == "Fd":
            glbSnes.setUseMF(True)
        else:
            glbSnes.setJacobian(preJac, self.J, self.Jp)
        glbSnes.setTolerances(rtol=self.rtol, atol=self.atol, stol=self.stol, max_it=self.maxiter)
        glbSnes.setSolution(self.glbSol)
        return glbSnes

    def test_on_original_function(self, snes, its, args):
        """
        This is a customized convergence test
        routine that computes the true residual
        instead of the preconditioned one
        """
        # if a local solve failed, the global step must fail
        if self.locSnes.appctx == SNESSolver.SNES_FAILURE:
            return PETSc.SNES.ConvergedReason.DIVERGED_FNORM_NAN
        cvg = its > 0 and self.Fnorm / self.fnorm0 < self.rtol or self.Fnorm < self.atol
        return cvg

    def saveTimeStepPerfs(self, snes, time_exec):
        """
        Saves current time performance data in monitoring file
        """
        nonlinear_iters = snes.getIterationNumber()
        if monitoringFilesPaths.get("byTimeSteps"):
            filePath = monitoringFilesPaths["byTimeSteps"]
            try:
                with open(filePath, "a") as file:
                    # Write data to the file
                    file.write(
                        f"{self.curr_time:.3e} {nonlinear_iters} {self.cumulLinIter} {self.overlap} "
                        f"{self.size} {time_exec:.3e} {self.nb_svs} {self.methodName}\n"
                    )
                    file.close()
            except Exception as e:
                print(f"Error writing to log file '{filePath}': {e}")
        # Reset counter
        self.cumulLinIter = 0
        self.cumLocNonlinear = 0

    def setGlbSnesConvergenceTest(self):
        """
        Sets the convergence test of the global snes
        """
        self.glbSnes.setConvergenceTest(self.test_on_original_function)

    def applyLocalDirichlet(self):
        """
        Applies Dirichlet local boundary conditions
        on each subdomain
        """
        BCDofs = self.bdDofs
        r, locFunc = self.locSnes.getFunction()
        A, P, locJac = self.locSnes.getJacobian()

        def localFunction(snes, Xl, Yl, update=True):
            """
            The subdomain function
            """
            locFunc[0](snes, Xl, Yl, update=update)
            Yl.getArray()[BCDofs] = 0.0

        def localJacobian(snes, Xl, J, Jp):
            """
            The subdomain Jacobian
            """
            locJac[0](snes, Xl, J, Jp)
            J.zeroRows(BCDofs)
            Jp.zeroRows(BCDofs)

        # Sets new operators
        self.locSnes.setFunction(localFunction, r)
        self.locSnes.setJacobian(localJacobian, A)

    def originalFunction(self, X, Y, update=False):
        """
        A function that do the action of the original problem
        """
        locVec = self.Yloc.duplicate()
        self.vecscatter.scatter(X, locVec)
        self.operators(locVec, self.Yloc)
        self.DDPart.restrict(self.Yloc)
        Y.set(0.0)
        self.vecscatter.scatter(self.Yloc, Y, mode="reverse", addv=True)

    def originalFunctionNorm(self, normType=1):
        """
        Computes the norm of the original
        function
        """
        Y = self.glbSol.duplicate()
        self.originalFunction(self.glbSol, Y)
        return Y.norm(normType)

    def getGlbSnes(self):
        """
        Gets global snes
        """
        return self.glbSnes

    def getLocalKsp(self):
        """
        Gets the local ksp
        """
        return self.locKsp

    def getSolution(self):
        """
        Gets the solution petsc vector
        """
        return self.glbSol

    def solve(self, rhs=None):
        """
        RASPEN Solve
        """
        # Scattering data
        self.glbSol.set(0.0)
        self.DDPart.restrict(self.locSol0)
        self.vecscatter.scatter(self.locSol0, self.glbSol, mode="reverse", addv=True)
        self.fnorm0 = self.originalFunctionNorm()
        if self.withSubPrecond:
            self.JpCtx.Precond = None
        # Solving
        t = time()
        self.glbSnes.solve(rhs, self.glbSol)
        time_exec = time() - t
        if self.rank == 0:
            self.saveTimeStepPerfs(self.glbSnes, time_exec)

    def destroyAll(self):
        """
        Destroys all RASPEN objects
        """
        self.J.destroy()
        self.glbSnes.destroy()
        self.Res.destroy()
        self.glbSol.destroy()
        self.locKsp.destroy()
        self.locSnes.destroy()
        self.vecscatter.destroy()
        self.locSol.destroy()
        self.locSol0.destroy()
        self.Yloc.destroy()

        if self.withCoarsePb:
            self.Jloc0.destroy()

        if self.withSubPrecond:
            self.Jp.destroy()
            self.JpCtx.sksp.destroy()
            if self.JpCtx.Precond:
                self.JpCtx.Precond.destroy()


class JacCtx:
    """
    Jacobian context class
    """

    def __init__(self, Sl: _RASPENSolver, snes):
        # Function vector
        self.F = snes.getFunction()[0]
        # RASPEN solver
        self.Sl = Sl
        # Work vector
        self.locVec = Sl.Yloc.duplicate()
        if Sl.withCoarsePb:
            # Galerkin coarse Pb
            self.GCGC = Sl.GCGC
            # Coarse Problem linear solver
            self.coarseKSP = self.GCGC.GCSnes.getKSP()
            # Initial Jacobian needed for the FAS Jacobian
            self.Jloc = Sl.Jloc0
            # Setting the Jacobian to the linear solver
            self.Sl.locKsp.setOperators(self.Jloc, self.Jloc)
        else:
            self.Jloc = Sl.Jloc

    def applyCoarseCorrectionDiff(self, X, Y):
        """
        Apply the differentiation operator of the coarse correction function.

        Args:
            X: the direction of differentiation
            Y: the coarse correction result, i.e., Y = P0 C0'(Xs) X
        """
        timings = {}
        start = time()

        if self.Sl.coarsePbSide == "Left":
            Jloc = self.Sl.Jloc
        else:
            Jloc = self.Sl.Jloc0
        timings["select_Jloc"] = time() - start

        start = time()
        locVec = self.Sl.Yloc.duplicate()
        self.Sl.vecscatter(X, locVec)
        timings["scatter_X_to_locVec"] = time() - start

        start = time()
        Jloc.mult(locVec, self.Sl.Yloc)
        self.Sl.DDPart.restrict(self.Sl.Yloc)
        timings["local_J_mult_and_restrict"] = time() - start

        start = time()
        Y.set(0.0)
        self.Sl.vecscatter(self.Sl.Yloc, Y, mode="reverse", addv=True)
        timings["reverse_scatter_to_Y"] = time() - start

        start = time()
        self.GCGC.coarseRestriction(Y, self.GCGC.Xc)
        timings["coarse_restriction"] = time() - start

        start = time()
        Xc0 = self.GCGC.Xc.duplicate()
        self.coarseKSP.solve(self.GCGC.Xc, Xc0)
        timings["solve_coarse_problem"] = time() - start

        start = time()
        self.GCGC.coarseProlongation(Xc0, Y)
        Y.scale(-1.0)
        timings["coarse_prolongation_and_scale"] = time() - start

        # if self.Sl.rank == 0 and self.Sl.verbose:
        #     print("\n[Timing for applyCoarseCorrectionDiff()]", flush=True)
        #     for k, v in timings.items():
        #         print(f"  {k}: {v:.6f} seconds", flush=True)

    def mult(self, mat, X, Y):
        """
        Mat-Vec multiplication
        """
        if self.Sl.solverType.endswith("N"):
            # Scattering global direction to local vecs
            if self.Sl.withCoarsePb and self.Sl.coarsePbSide == "Right":
                # Applying coarse correction differential
                self.applyCoarseCorrectionDiff(X, Y)
                Y.axpy(1.0, X)
                # Scattering global direction to local vecs
                self.Sl.vecscatter.scatter(Y, self.locVec)
                Y.axpy(-1.0, X)
                Y.scale(-1.0)
            else:
                self.Sl.vecscatter.scatter(X, self.locVec)
            self.Jloc.mult(self.locVec, self.Sl.Yloc)
            self.Sl.Yloc.getArray()[self.Sl.bdDofs] = 0.0
            self.Sl.locKsp.solve(self.Sl.Yloc, self.Sl.Yloc)
            if self.Sl.solverType.startswith("RAS"):
                self.Sl.DDPart.restrict(self.Sl.Yloc)
            Y.set(0.0)
            self.Sl.vecscatter.scatter(self.Sl.Yloc, Y, mode="reverse", addv=True)
            if self.Sl.withCoarsePb and self.Sl.coarsePbSide == "Left":
                Y.axpby(1.0, -1.0, X)
                Yd = Y.copy()
                t = time()
                self.applyCoarseCorrectionDiff(Yd, Y)
                self.Sl.applyDiff += time() - t
                Y.axpy(1.0, Yd)
                Y.axpy(-1.0, X)
        else:
            X.copy(Y)


class SubJacCtx:
    """
    Substructured Jacobian context
    """

    def __init__(self, Sl: _RASPENSolver):
        """
        Constructor
        """
        # Inherit the RASPEN solver
        self.Sl = Sl
        # The Jacobian context
        self.Jctx = self.Sl.J.getPythonContext()
        # Inherit domain decomposition partitioner
        self.DDPart = self.Sl.DDPart
        # Subdomain work vector
        self.Yloc = self.Sl.Yloc
        # Boundary ghosts DOFs
        self.bdGhostsDOFs = self.DDPart.local_boundary_dofs
        # Get internal ghosts indices
        self.interiorGhosts = self.DDPart.interiorGhosts
        if Sl.withCoarsePb:
            self.Res = Sl.GCGC.Res
            self.X = Sl.GCGC.glbVec
            self.coarseKSP = Sl.GCGC.GCSnes.getKSP()

    def mult(self, mat, X, Y):
        """
        Matrix-Vector product routine
        """
        # Communicating Ghost values between subdomain
        locVec = self.Yloc.duplicate()
        locVec.set(0.0)
        locVec.getArray()[self.interiorGhosts] = X.getArray(readonly=True)[:]
        if self.Sl.withCoarsePb:
            Yd = self.X
        else:
            Yd = self.Sl.Res.duplicate()
        Yd.set(0.0)
        self.Sl.vecscatter(locVec, Yd, mode="reverse", addv=True)
        self.Sl.vecscatter(Yd, locVec)
        self.Sl.Jloc.mult(locVec, self.Yloc)
        self.Yloc.getArray()[self.Sl.bdDofs] = 0.0
        self.Sl.locKsp.solve(self.Yloc, self.Yloc)
        # Restrict to nonOverlapping subdomain
        if self.Sl.solverType.startswith("RAS"):
            self.Sl.DDPart.restrict(self.Yloc)
        # Applying coarse differential
        if self.Sl.withCoarsePb:
            self.Res.set(0.0)
            self.Sl.vecscatter(locVec, self.Res, mode="reverse", addv=True)
            self.Res.axpby(1.0, -1.0, Yd)
            self.Res.copy(Yd)
            self.Sl.vecscatter(self.Res, locVec)
            self.Sl.Jloc.mult(locVec, self.Sl.Yloc)
            self.Sl.DDPart.restrict(self.Sl.Yloc)
            Y.set(0.0)
            self.Sl.vecscatter(self.Sl.Yloc, Y, mode="reverse", addv=True)
            self.Sl.GCGC.coarseRestriction(Y, self.Sl.GCGC.Xc)
            Xc0 = self.Sl.GCGC.Xc.duplicate()
            self.coarseKSP.solve(self.Sl.GCGC.Xc, Xc0)
            self.Sl.GCGC.coarseProlongation(Xc0, Yd)
            Yd.scale(-1.0)
            Yd.axpy(1.0, self.Res)
            Y.axpy(-1.0, X)
        # Write result in the output vector Y
        Y.getArray()[:] = self.Yloc.getArray()[self.interiorGhosts]


class substPrecondCtx:
    """
    Implements a shell preconditioner from the
    substructured Jacobian. In theory, this represents
    the exact inverse of the fine-level Jacobian, hence
    one should expect GMRES to converge in one or two iterations.
    """

    def __init__(self, Sl, J, subJ=None):
        """
        Preconditioner class constructor
        """
        # RASPEN
        self.Sl = Sl
        # Domain decomposition preconditioner
        self.DDPart = Sl.DDPart
        # Fine-level Jacobian
        self.J = J
        # Local Jacobian
        self.Jl = self.Sl.Jloc
        # Boundary dofs
        self.bdDofs = self.Sl.bdDofs
        # Local size
        self.locSize = self.DDPart.getLocalSize()
        # Eventually the substructured preconditionner
        self.Precond = None
        # Reconstructing the matrix
        self.reconstruct = True
        # Subdtructured Jacobian
        if subJ:
            assert isinstance(subJ, PETSc.Mat)
            self.subJ = subJ
        else:
            self.subJ = self.buildSubstruturedJacobian()
        # Substructured KSP
        self.sksp = self.setUpSksp()
        # Local work vector
        self.Yloc = self.Sl.Yloc
        # Ghosts sized PETSc vector
        self.GhostVec = self.Sl.DDPart.GhostPetscVec
        # Internal ghosts
        self.intGhosts = self.DDPart.interiorGhosts
        # IS of the ghost Map (must be stored as attribute to avoid suppression by Python garbage collector)
        self.jSet = PETSc.IS().createGeneral(self.DDPart.ghostsMap, comm=self.Jl.getComm())

    def buildSubstruturedJacobian(self):
        """
        Builds the substructured Jacobian
        """
        # Global number of ghost nodes
        ng = self.DDPart.glbGhostSize
        # Local number of interior ghosts
        nlg = self.DDPart.intGhostSize
        # Setting python context of the matrix
        subJ = PETSc.Mat().createPython(([nlg, ng], [nlg, ng]), comm=self.DDPart.comm)
        subJCtx = SubJacCtx(self.Sl)
        subJ.setPythonContext(subJCtx)
        subJ.setUp()
        return subJ

    def buildMatEntries(self):
        """
        Build substructured Jacobian entries
        """
        # Timings
        timings = {}
        # Seq Comm
        comm = self.Jl.getComm()

        # Local factorized matrix
        LUFct = self.Sl.locKsp.getPC().getFactorMatrix()
        LUFct.setMumpsIcntl(20, 1)

        # Test local ksp
        try:
            self.Sl.locKsp.solve(self.Sl.Yloc, self.Sl.Yloc)
        except Exception:
            raise RuntimeError("Local snes ksp failed ! ")

        # Slicing Local Jacobian only on ghost dofs
        rowsIs = PETSc.IS().createGeneral(np.arange(self.locSize, dtype=np.int32))
        colsIs = PETSc.IS().createGeneral(self.bdDofs)
        tempMat = self.Jl.createSubMatrices(rowsIs, colsIs)[0]
        tempMat.zeroRows(self.bdDofs, 0.0)

        # Applying forward/backward substitutions
        t0 = time()

        # Build the resulting matrix

        iSet = PETSc.IS().createGeneral(self.intGhosts, comm=comm)

        SubstMat = applyFactorOnSubBlocks(LUFct, tempMat, iSet, self.jSet)
        SubstMat.assemble()
        MPI.ASTER_COMM_WORLD.Barrier()
        gmax = self.Sl.comm.reduce(time() - t0, op=MPI.MAX, root=0)
        timings["Substructured matrix build time"] = gmax

        if self.Sl.rank == 0:
            for k, v in timings.items():
                print(f"  {k}: {v:.6f} seconds", flush=True)
        return SubstMat

    def setUpSksp(self):
        """
        Sets up the PETSc KSP to solve
        the substructured linear problem
        """
        ksp = PETSc.KSP().create(self.DDPart.comm)
        ksp.prefix = "sksp_"
        ksp.setOperators(self.subJ)
        return ksp

    def apply(self, mat, X, Y):
        """
        The preconditioner Matrix-Vector product
        """
        # Scattering data to subdomains
        self.Sl.vecscatter(X, self.Yloc)
        # Duplicating ghosts vec for work
        Yg = self.GhostVec.duplicate()
        # Writing ghosts values
        Yg.getArray()[:] = self.Yloc.getArray()[self.intGhosts]
        self.sksp.setFromOptions()
        if self.sksp.getPC().getType() != "none":
            if self.Precond is None:
                self.Precond = self.buildMatEntries()
        self.sksp.setOperators(self.subJ, self.Precond)
        self.sksp.setUp()
        # Substructured linear solve
        t0 = time()
        self.sksp.solve(Yg, self.GhostVec)
        if self.Sl.rank == 0:
            print(" Subst KSP time: ", time() - t0, flush=True)
        Yg.destroy()
        # Doing Fine level multiplication
        self.Yloc.set(0.0)
        self.Yloc.getArray()[self.intGhosts] = self.GhostVec.getArray()[:]
        Y.set(0.0)
        self.Sl.vecscatter(self.Yloc, Y, mode="reverse", addv=True)
        # Summing up all the terms
        Y.maxpy([1.0, -1.0], [X, self.J(Y)])


class DomainDecomposition:
    """
    Domain Decomposition class
    """

    def __init__(self, mesh, nume_ddl, overlap=1):
        """
        DDM constructor
        """
        # Setting inputs
        self.mesh = mesh
        self.dofNbg = nume_ddl
        numeq = nume_ddl.getEquationNumbering()
        self.overlap = overlap
        self.comm = MPI.ASTER_COMM_WORLD
        self.rank = self.comm.Get_rank()
        self.size = self.comm.Get_size()
        # in global numbering
        LGMap = nume_ddl.localToGlobalDOF
        neq = nume_ddl.getNumberOfDOFs(local=True)
        self.local_dofs = np.array([LGMap(i) for i in range(neq)], dtype=np.int32)
        # in global numbering
        self.non_overlap_dofs = numeq.getNoGhostDOFs(local=False)
        # all in ovp with ghosts in global numbering
        self.on_overlap_dofs = numeq.getGhostDOFs(local=False)
        # all in ovlp in local numbering
        self.local_ovlp_dofs = numeq.getGhostDOFs(local=True)
        # ghost in local numbering
        self.local_boundary_dofs = numeq.getGhostDOFs(local=True, lastLayerOnly=self.size > 1)
        # self.local_boundary_dofs = numeq.getGhostDOFs(local=True)
        # all except ghost in local numbering
        self.local_interior_dofs = numeq.getNoGhostDOFs(local=True)
        # all except ghost in global numbering
        self.global_interior_dofs = numeq.getNoGhostDOFs(local=False)
        # Local size
        self.localSize = nume_ddl.getNumberOfDOFs(local=True)
        # Initializing DD variables
        self.createVecscatter()

    def createVecscatter(self):
        """
        Creates the vector scatters
        """
        # Create global and local vectors
        # Global Vec
        GlbVec = PETSc.Vec().create(comm=self.comm)
        GlbVec.setSizes(self.getGlobalSize())
        GlbVec.setFromOptions()
        GlbVec.setUp()

        # Local Vec
        LocVec = PETSc.Vec().create(comm=MPI.ASTER_COMM_SELF)
        LocVec.setSizes(self.localSize)
        LocVec.setFromOptions()
        LocVec.setUp()

        # Creating Index Sets
        localIs = PETSc.IS().createGeneral(self.local_dofs, comm=self.comm)
        locRangeIs = PETSc.IS().createStride(self.localSize, step=1)

        # Create the scatter context for local to global mapping
        self.Vecscatter = PETSc.Scatter().create(GlbVec, localIs, LocVec, locRangeIs)

    def restrict(self, petscVec):
        """
        Restricts a local vector on its local non-overlap
        """
        # Local size
        size = petscVec.getSize()
        # Assertions
        assert size == self.localSize
        # Restriction on the non-overlapping part
        petscVec.getArray()[self.local_ovlp_dofs] = 0.0

    def BuildGhostsTools(self, locVec, glbVec):
        """Builds all the tools needed for the substructuring approach:

        Internal ghosts: The ghosts nodes of the other subdomains
                            that are on the interior of this subdomain.

        PETSc ghosts vector: A PETSc vector where each process subvector corresponds
                                to the internal ghosts that the subdomain owns."""
        # Preliminarly manipulations
        bd_dofs = self.local_boundary_dofs
        locVec.set(0.0)
        locVec.getArray()[bd_dofs] = 1.0
        glbVec.set(0.0)
        self.Vecscatter(locVec, glbVec, mode="reverse", addv=True)
        self.Vecscatter(glbVec, locVec)
        self.restrict(locVec)
        # Internal ghosts indices
        self.interiorGhosts = np.where(locVec.getArray() >= 1)[0]
        self.interiorGhosts = np.array(self.interiorGhosts, dtype=np.int32)
        glbIntGhosts = self.local_dofs[self.interiorGhosts]
        # Ghosts sized PETSc vector
        self.GhostPetscVec = PETSc.Vec().createWithArray(glbIntGhosts, comm=self.comm)
        self.GhostPetscVec.setUp()
        # Exterior to interior ghosts map
        toAll, SeqVec = PETSc.Scatter().toAll(self.GhostPetscVec)
        toAll(self.GhostPetscVec, SeqVec)
        vals = SeqVec.getArray()
        lookup = {val: i for i, val in enumerate(vals)}
        self.ghostsMap = np.array([lookup[v] for v in self.local_dofs[bd_dofs]], dtype=np.int32)
        del lookup
        # Internal ghosts size
        self.intGhostSize = self.GhostPetscVec.getLocalSize()
        # Global Ghosts size
        self.glbGhostSize = self.GhostPetscVec.getSize()

    def getMyNeighbours(self, locVec, glbVec):
        """
        Gets the neighbours of the current subdomain including itself
        """
        locVec.set(self.rank)
        self.restrict(locVec)
        self.Vecscatter(locVec, glbVec, mode="reverse", addv=True)
        self.Vecscatter(glbVec, locVec)
        neighbours = np.unique(locVec.getArray()[:])
        return neighbours

    def getLocalMultiplicity(self, locVec, glbVec):
        """
        Each subdomain gets multiplicity values
        at its interface nodes
        """
        # Setting to null
        locVec.set(0)
        glbVec.set(0)
        # Communicating
        locVec.getArray()[self.local_boundary_dofs] = 1
        # Writing
        self.Vecscatter(locVec, glbVec, mode="reverse", addv=True)
        # Reading
        self.Vecscatter(glbVec, locVec, mode="forward")
        # Getting values
        multiplicity = locVec[self.local_boundary_dofs]

        return multiplicity

    def getVecScatter(self):
        """
        Gets vecscatter from global to local
        """

        if not self.Vecscatter:
            raise (RuntimeError("createVecscatter method must be " + "called before this routine"))

        return self.Vecscatter

    def getGlobalSize(self):
        """
        Gets the global size of the mesh
        """
        return self.dofNbg.getNumberOfDOFs(local=False)

    def getLocalSize(self):
        """
        Gets the local size of the mesh
        """
        return self.localSize

    def getGhostsGlobalSize(self):
        """
        Gets the ghosts global size
        """
        return self.glbGhostSize

    def getLocalDofs(self):
        """
        Gets overlapping set of local DOFs in
        Global numbering representation
        """
        return self.local_dofs

    def getNonOverlappingLocalDofs(self):
        """
        Gets non-overlapping set of local DOFs in
        Global numbering representation
        """
        return self.non_overlap_dofs

    def getOnOverlapDofs(self):
        """
        Gets the set of dofs on the overlap
        """
        return self.on_overlap_dofs

    def getOnOverlapLocalDofs(self):
        """
        Gets the set of local dofs on the overlap
        """
        return self.local_ovlp_dofs

    def getLocalBoundaryDofs(self):
        """
        Gets local boundary dofs on local numbering
        """
        return self.local_boundary_dofs

    def getLocalInteriorDofs(self):
        """
        Gets local interior dofs on local numbering
        """
        return self.local_interior_dofs


class GalerkinCoarseGridCorrection:
    """
    Implements the nonlinear coarse correction using a
    nonlinear subspace iteration approach for a given
    domain decomposition partition.

    The goal is compute a coarse correction C(X) for a given approximation X such that:

                             R f( X + P C(X) ) = 0.

    R and P (R = P.T) are respectively the chosen coarse restriction and prolongation.

    """

    def __init__(self, raspen: RASPENSolver, DDPart: DomainDecomposition):
        """
        The constructor for the Galerkin coarse correction class
        """
        # Getting a ref of the RASPEN solver instance
        self.raspen = raspen
        # Getting the RASPEN communicator
        self.comm = self.raspen.comm
        # Getting the number of procs/subdomains
        self.size = self.raspen.size
        # Getting the proc rank
        self.rank = self.raspen.rank
        # Getting the assembler of operators (Function/Jacobian)
        self.operators = self.raspen.operators
        # Vecscatter
        self.vecscatter = self.raspen.vecscatter
        # Gettting the original function
        self.f = raspen.originalFunction
        # Getting the domain decomposition partitioner
        self.DDPart = DDPart
        # Subdomain discretization size
        self.locSize = self.DDPart.getLocalSize()
        # Subdomain dofs in global numbering
        self.locDofs = self.DDPart.local_dofs
        # Subdomain interior dofs in local numbering
        self.intDofs = self.DDPart.local_interior_dofs
        # Subdomain dofs that are on the overlap in local numbering
        self.onOvlpDofs = self.DDPart.local_ovlp_dofs
        # Dofs on the subdomain boundary
        # (Ghost dofs) in local numbering
        self.bdDofs = self.raspen.bdDofs
        print(" Local number of ghost nodes", len(self.bdDofs), flush=True)
        # Ghosts multiplicity
        self.SQMult = self.raspen.SQMult
        # Number of singular values to consider for each subdomain
        self.nb_svs = self.raspen.nb_svs
        # Getting the global problem size
        self.glbSize = self.DDPart.getGlobalSize()
        # Coarse space type
        self.coarseSpaceType = raspen.coarseSpaceType
        # Coarse problem side
        self.coarsePbSide = raspen.coarsePbSide
        # Global vectors
        self.glbSol = self.raspen.Res.duplicate()
        self.glbVec = self.glbSol.duplicate()
        # Local work vector
        self.Yloc = self.raspen.Yloc
        # Coarse pb solver tolerances
        self.rtol = 1e-8
        self.atol = 1e-12
        self.maxIt = 50
        # A boolean to indicate the coarse prolongation build state
        self.ProlongationIsBuilt = False
        # Builds the coarse Jacobian and its initial version as AIJ mats
        self.CPbMFJac = False
        # A boolean for saving local Jacobian
        self.saveLocalJac = False
        # Initializing variables to be built later
        # Coarse problem nonlinear solver
        self.GCSnes = None
        # Coarse problem size
        self.coarseSize = None
        # Jacobian
        self.Jc = None
        # Function vector
        self.Fc = None
        # Solution vector
        self.Xc = None
        # Prolongation
        self.P = None
        # Local prolongation
        self.Ploc = None  # To be extracted from self.P with getLocalProlongation
        # Linear solve (Sequential if True otherwise it is Parallel)
        self.isRedistributed = True
        # Cumulative of the nonlinear coarse Pb iterations
        self.nonlinCumIts = 0
        # Time to assemble
        self.assTime = 0
        # Correction time
        self.corrTime = 0
        # function time
        self.funcTime = 0
        # Ksp time
        self.t_ksp = None

    def buildSubdomainSVDProlongation(self, k, S=True, L=False):
        """
        Builds the coarse prolongation from a symmetric
        local subdomain eigen values problem.
        """
        timings = {}

        assert (
            S or L
        ), "To build prolongation, at least either large or small eigen pairs should be selected"

        start = time()
        linOp = self.BtBOperator()
        timings["BtBOperator"] = time() - start

        start = time()
        evals, evecs = eigsh(linOp, which="LM", k=self.nb_svs)
        timings["eigsh"] = time() - start

        start = time()
        tol = 1e-3
        mask = evals >= tol
        evals = evals[mask]
        evecs = evecs[:, mask]
        self.raspen.nb_svs = self.nb_svs = len(evals)
        timings["filter_eigenpairs"] = time() - start

        start = time()
        if S and L:
            self.nb_svs *= 2
            self.raspen.nb_svs *= 2
        timings["adjust_nb_svs"] = time() - start

        start = time()
        samplMat = self.buildSamplingMat(evals, evecs, S, L)
        timings["buildSamplingMat"] = time() - start
        start = time()
        if self.coarsePbSide == "Right":
            self.P = samplMat
        else:
            NNCols, samplMat = self.getLocalSamplingMat(samplMat)
            timings["getLocalSamplingMat"] = time() - start
            start = time()
            self.P = self.buildPrlongFromSamplMat(samplMat, NNCols, self.nb_svs)
        timings["build_prolongation"] = time() - start

        start = time()
        self.ProlongationIsBuilt = True
        self.getLocalProlongation()
        timings["local_prolongation"] = time() - start

        start = time()
        sizeHasChanged = self.P.getSize()[1] != self.coarseSize
        self.coarseSize = self.P.getSize()[1]
        if self.GCSnes is None or sizeHasChanged:
            self.GCSnes = self.buildCoarseSnes()
        timings["check_coarseSize_and_buildSnes"] = time() - start

        # if self.raspen.rank == 0:
        #     for k, v in timings.items():
        #         print(f"  {k}: {v:.6f} seconds",flush=True)

    def getLocalSamplingMat(self, glbSamplMat):
        """
        Given the global sampling matrix, this routine extracts the
        needed local sampling matrix.
        """
        timings = {}

        start = time()
        locComm = self.raspen.Jloc.getComm()
        timings["getComm"] = time() - start

        start = time()
        locDofs = self.locDofs
        bd_dofs = self.bdDofs
        glb_bd_dofs = locDofs[bd_dofs]
        timings["get_dof_indices"] = time() - start

        start = time()
        nloc = self.locSize
        coarseSize = glbSamplMat.getSize()[1]
        locSamplMat = PETSc.Mat().createAIJ((nloc, coarseSize), comm=locComm)
        timings["create_mat"] = time() - start

        start = time()
        nnz = np.zeros(nloc, dtype=np.int32)
        nnz[bd_dofs] = coarseSize
        # locSamplMat.setPreallocationNNZ(nnz)
        locSamplMat.setUp()
        timings["preallocate_matrix"] = time() - start

        start = time()
        all_cols = np.arange(coarseSize, dtype=np.int32)
        rowsIs = PETSc.IS().createGeneral(glb_bd_dofs)
        colsIs = PETSc.IS().createGeneral(all_cols)
        subSamplMat = glbSamplMat.createSubMatrices(rowsIs, colsIs)[0]
        timings["create_submatrix"] = time() - start

        start = time()
        NNCols = np.unique(subSamplMat.getValuesCSR()[1])
        timings["get_nonnull_columns"] = time() - start

        start = time()
        locSamplMat.setValues(bd_dofs, NNCols, subSamplMat[:, NNCols])
        locSamplMat.assemble()
        timings["set_values_and_assemble"] = time() - start

        # if self.raspen.rank == 0 and self.raspen.verbose:
        #     print("\n[Timing for getLocalSamplingMat()]", flush=True)
        #     for k, v in timings.items():
        #         print(f"  {k}: {v:.6f} seconds", flush=True)

        return NNCols, locSamplMat

    def buildPrlongFromSamplMat(self, samplMat, NNCols, nb_sv):
        """
        Given a sampling matrix, this routine
        builds the coarse prolongation matrix.
        """
        timings = {}

        start = time()
        Jl = self.raspen.Jloc
        LUFct = self.raspen.locKsp.getPC().getFactorMatrix()
        LUFct.setMumpsIcntl(20, 1)
        bd_dofs = self.bdDofs
        nloc = self.locSize
        coarseSize = samplMat.getSize()[1]
        intDofs = self.intDofs
        intSize = len(intDofs)
        timings["setup_and_parameters"] = time() - start

        start = time()
        samplMat = Jl.matMult(samplMat)
        samplMat.zeroRows(bd_dofs, 0.0)
        ResMat = PETSc.Mat().createDense((nloc, coarseSize), comm=Jl.getComm())
        ResMat.setUp()
        timings["jacobian_mult_and_setup_ResMat"] = time() - start

        start = time()
        samplMat = samplMat.transpose()
        samplMat_T = samplMat.createTranspose(samplMat)
        LUFct.matSolve(samplMat_T, ResMat)
        ResMat.zeroRows(self.onOvlpDofs, 0.0)
        samplMat.destroy()
        samplMat_T.destroy()
        timings["sparse_rhs_solve"] = time() - start

        nbCols = self.size * coarseSize
        P = PETSc.Mat().createAIJ(([intSize, None], nbCols), comm=self.comm)
        # P.setPreallocationNNZ((maxNNZ,0))
        P.setUp()
        values = ResMat.getDenseArray()
        start_row, end_row = P.getOwnershipRange()
        sdRows = np.arange(start_row, end_row, dtype=np.int32)
        vals = values[np.ix_(intDofs, NNCols)]
        P.setValues(sdRows, self.raspen.rank * coarseSize + NNCols, vals.flatten(), addv=True)
        start = time()
        P.assemble()
        timings["build_sparse_prolongation"] = time() - start
        start = time()
        rows = np.arange(coarseSize + 1, dtype=np.int32)
        cols = np.arange(coarseSize, dtype=np.int32)
        vals = np.ones_like(cols, dtype=np.int32)
        I = PETSc.Mat().createAIJWithArrays(
            (nbCols, [nb_sv, coarseSize]), csr=(rows, cols, vals), comm=self.comm
        )
        I.setUp()
        # start = time()
        # I = PETSc.Mat().createAIJ((nbCols, [nb_sv, coarseSize]),
        #                           comm=self.comm)
        # I.setPreallocationNNZ(1)
        # I.setUp()
        # for j in range(coarseSize):
        #     rows = [k * coarseSize + j for k in range(self.size)]
        #     I.setValues(rows, j, np.ones(self.size))
        # I.assemble()
        timings["build_identity_and_assemble"] = time() - start

        start = time()
        P = P.matMult(I)
        timings["final_mat_mult"] = time() - start

        # if self.raspen.rank == 0 and self.raspen.verbose:
        #     print("\n[Timing for buildPrlongFromSamplMat()]", flush=True)
        #     for k, v in timings.items():
        #         print(f"  {k}: {v:.6f} seconds", flush=True)
        return P

    def buildInterfaceSVDProlongation(self, k):
        """
        Builds the coarse prolongation using Matrix-Free
        local SVDs with ARPACK through Scipy
        """
        # Same dofs but the global numbering
        glbIntDofs = self.DDPart.global_interior_dofs
        # Forming the scipy linear operator
        locLinOp = self.formLocalLinearOperator()
        U, s, _ = svds(locLinOp, k=self.nb_svs, which="LM", return_singular_vectors="u")
        # U = np.eye(*U.shape, dtype=U.dtype)        # unpack (n, m)
        # Declaring the prologation matrix in memory
        self.P = PETSc.Mat().createAIJ((self.glbSize, [self.nb_svs, None]), comm=self.comm)
        # # Optimizing memory preallocation
        # self.P.setPreallocationNNZ(self.nb_svs)

        # Setting up the matrix
        self.P.setUp()
        # Determining the subdomains owned cols
        start, end = self.P.getOwnershipRangeColumn()
        self.sd_coarseCols = np.arange(start, end).astype(np.int32)
        # Setting values and assembling
        self.P.setValues(glbIntDofs, self.sd_coarseCols, U[self.intDofs, :])
        self.P.assemble()
        # Changing build status of prolongation
        self.ProlongationIsBuilt = True
        # Getting the local part of the prolongation
        # This requires addtional storage memory but
        # prevents ulterior recurrent memory comms
        self.getLocalProlongation()
        # Set the size
        sizeHasChanged = self.P.getSize()[1] != self.coarseSize
        self.coarseSize = self.P.getSize()[1]
        # Rebuilding the coarse
        if self.GCSnes is None or sizeHasChanged:
            self.GCSnes = self.buildCoarseSnes()

    def buildSamplingMat(self, evals, evecs, S=True, L=False):
        """
        This routine takes the eigenpairs computed on the
        subdomain interface and generates the prolongation
        sampling matrix on the entire subdomain.
        """
        timings = {}

        start = time()
        assert (
            S or L
        ), "To build prolongation, at least either large \
                         or small eigen pairs should be selected"

        nloc = self.DDPart.getLocalSize()
        nep = len(evals)
        Jl = self.raspen.Jloc
        ksp = self.raspen.locKsp
        LUFct = ksp.getPC().getFactorMatrix()
        LUFct.setMumpsIcntl(20, 1)

        bd_dofs = self.bdDofs
        glb_bd_dofs = self.locDofs[bd_dofs]
        int_ghosts = self.DDPart.interiorGhosts
        glb_int_ghosts = self.locDofs[int_ghosts]
        timings["setup_parameters"] = time() - start

        start = time()
        if S:
            small_evals = 0.5 * (evals - np.sqrt(evals**2 + 4 * evals))
        if L:
            large_evals = 0.5 * (evals + np.sqrt(evals**2 + 4 * evals))
        timings["compute_adjusted_evals"] = time() - start

        start = time()
        evecsMat = PETSc.Mat().createAIJ((nloc, nep), comm=Jl.getComm())
        nnz = np.zeros(nloc, dtype=np.int32)
        nnz[bd_dofs] = nep
        # evecsMat.setPreallocationNNZ(nnz)
        evecsMat.setUp()

        evecs = evecs.T
        for i, evec in enumerate(evecs):
            evecsMat.setValues(bd_dofs, i, evec)
        evecsMat.assemble()
        timings["build_and_fill_evecsMat"] = time() - start

        start = time()
        evecsMat = Jl.matMult(evecsMat)
        evecsMat.zeroRows(bd_dofs, 0.0)
        ResMat = PETSc.Mat().createDense((nloc, nep), comm=Jl.getComm())
        ResMat.setUp()
        evecsMat = evecsMat.transpose()
        evecsMat_T = evecsMat.createTranspose(evecsMat)
        LUFct.matSolve(evecsMat_T, ResMat)
        ResMat.zeroRows(self.onOvlpDofs, 0.0)
        evecsMat.destroy()
        evecsMat_T.destroy()
        timings["matSolve_and_cleanup"] = time() - start

        start = time()
        int_norms = np.sum(ResMat.getDenseArray() ** 2, axis=0)
        timings["compute_int_norms"] = time() - start

        start = time()
        nr = self.DDPart.getGlobalSize()
        nc = 2 * nep if (S and L) else nep

        SamplMat = PETSc.Mat().create(comm=self.comm)
        SamplMat.setType("aij")
        SamplMat.setSizes(([nc, None], nr))
        timings["create_sampling_matrix"] = time() - start
        start = time()
        if self.coarsePbSide == "Right":
            nnz = self.locSize
        else:
            onnz = len(bd_dofs)
            dnnz = len(int_ghosts)
            nnz = dnnz + onnz

        # SamplMat.setPreallocationNNZ(nnz)
        timings["setPrealloc_sampling_matrix"] = time() - start
        start = time()
        SamplMat.setUp()
        timings["setup_sampling_matrix"] = time() - start
        start = time()
        startCol, _ = SamplMat.getOwnershipRange()
        offset = startCol
        # offset = startCol + self.raspen.rank*coarseSize
        if S:
            ghost_scaling = 1.0 / np.sqrt(1 + int_norms / small_evals**2)
            interior_scaling = 1.0 / np.sqrt(int_norms + small_evals**2)
            for i, evec in enumerate(evecs):
                gScal = ghost_scaling[i]
                iScal = interior_scaling[i]
                if self.coarsePbSide == "Right":
                    SamplMat.setValues(offset + i, self.locDofs, -iScal * ResMat[:, i], addv=True)
                else:
                    SamplMat.setValues(
                        offset + i, glb_int_ghosts, -iScal * ResMat[int_ghosts, i], addv=True
                    )
                SamplMat.setValues(offset + i, glb_bd_dofs, gScal * evec, addv=True)
            offset += nep

        if L:
            ghost_scaling = 1.0 / np.sqrt(1 + int_norms / large_evals**2)
            interior_scaling = 1.0 / np.sqrt(int_norms + large_evals**2)
            for i, evec in enumerate(evecs):
                gScal = ghost_scaling[i]
                iScal = interior_scaling[i]
                if self.coarsePbSide == "Right":
                    SamplMat.setValues(offset + i, self.locDofs, -iScal * ResMat[:, i], addv=True)
                else:
                    SamplMat.setValues(
                        offset + i, glb_int_ghosts, -iScal * ResMat[int_ghosts, i], addv=True
                    )
                SamplMat.setValues(offset + i, glb_bd_dofs, gScal * evec, addv=True)
        timings["build_sampling_matrix"] = time() - start
        start = time()
        SamplMat.assemble()
        timings["assemble_sampling_matrix"] = time() - start
        start = time()
        SamplMat = SamplMat.transpose()
        timings["transpose_sampling_matrix"] = time() - start

        # if self.raspen.rank == 0 and self.raspen.verbose:
        #     print("\n[Timing for buildSamplingMat()]", flush=True)
        #     for k, v in timings.items():
        #         print(f"  {k}: {v:.6f} seconds", flush=True)

        return SamplMat

    def buildNicolaidesProlongation(self, k):
        """
        Builds the Nicolaides prolongation
        """
        # Sets up the prolongation matrix
        self.P = PETSc.Mat().createAIJ((self.glbSize, self.size), comm=self.comm)
        self.P.setUp()
        # Allocating a local work vector in memory
        locVec = self.Yloc.duplicate()
        # Setting the values on the boundary to ones
        locVec.set(0.0)
        locVec.getArray()[self.bdDofs] = 1.0
        # Computations ...
        self.raspen.Jloc.mult(locVec, self.Yloc)
        self.Yloc.getArray()[self.bdDofs] = 0.0
        self.raspen.locKsp.solve(self.Yloc, self.Yloc)
        self.DDPart.restrict(self.Yloc)
        # Setting the values on prolongation operator
        self.P.setValues(self.locDofs, self.raspen.rank, self.Yloc, addv=True)
        # Assembling
        self.P.assemble()
        self.ProlongationIsBuilt = True
        # Getting the local part of the prolongation
        # This equires addtional storage memory but
        # prevents ulterior reccurent memory comms
        self.getLocalProlongation()
        # Set the size
        sizeHasChanged = self.P.getSize()[1] != self.coarseSize
        self.coarseSize = self.P.getSize()[1]
        # Rebuilding the coarse in case
        if self.GCSnes is None or sizeHasChanged:
            self.GCSnes = self.buildCoarseSnes()

    def formGlobalLinearOperator(self):
        """
        Form the operator associated with the rectangle
        global matrix on which the SVD is going to be performed
        """
        size = (self.glbSize, self.glbSize)
        # Subdomain local boundary dofs in glb numberings
        glb_bdDofs = self.locDofs[self.bdDofs]

        toAll, SeqVec = PETSc.Scatter().toAll(self.glbVec)

        def mat_vec(v):
            """
            Matrix mat-vec product
            """
            # Flattening data
            v = v.flatten()

            # Allocating a local work vector to store data
            locVec = self.Yloc.duplicate()
            locVec.set(0.0)

            # Writing data on the work vector
            locVec.getArray()[self.bdDofs] = v[glb_bdDofs]

            # Computations...
            self.raspen.Jloc.mult(locVec, self.Yloc)
            self.Yloc.getArray()[self.bdDofs] = 0.0
            self.raspen.locKsp.solve(self.Yloc, self.Yloc)
            self.DDPart.restrict(self.Yloc)
            self.glbVec.set(0)
            self.vecscatter(self.Yloc, self.glbVec, mode="reverse", addv=True)

            # Copy resulting data
            toAll(self.glbVec, SeqVec)
            return np.copy(SeqVec.getArray()[:])

        def mat_vec_transpose(v):
            """
            Transpose matrix mat-vec product
            """
            # Flattening data
            v = v.flatten()
            # Allocating a local work vector to store data
            locVec = self.Yloc.duplicate()
            locVec.set(0.0)

            # Writing data on the work vector
            locVec.getArray()[:] = v[self.locDofs]

            # Computations...
            self.DDPart.restrict(locVec)
            self.raspen.locKsp.solveTranspose(locVec, locVec)
            locVec.getArray()[self.bdDofs] = 0.0
            self.raspen.Jloc.multTranspose(locVec, self.Yloc)
            self.glbVec.set(0)
            SavedValues = np.copy(self.Yloc[self.bdDofs])
            self.Yloc.set(0.0)
            self.Yloc.getArray()[self.bdDofs] = SavedValues[:]
            self.vecscatter(self.Yloc, self.glbVec, mode="reverse", addv=True)

            # Copy resulting data
            toAll(self.glbVec, SeqVec)
            return np.copy(SeqVec.getArray()[:])

        # Making the scipy linear operator
        linOp = LinearOperator(size, matvec=mat_vec, rmatvec=mat_vec_transpose)
        return linOp

    def formLocalLinearOperator(self):
        """
        Form the operator associated with the rectangle
        local matrix on which SVD is going to be performed
        """

        loc_ng = len(self.bdDofs)
        size = (self.locSize, loc_ng)

        def mat_vec(v):
            """
            Matrix mat-vec product
            """
            # Flattening data
            v = (v.flatten()) * self.SQMult

            # Allocating a local work vector to store data
            locVec = self.Yloc.duplicate()
            locVec.set(0.0)

            # Writing data on the work vector
            locVec.getArray()[self.bdDofs] = v[:]
            # Computations...
            self.raspen.Jloc.mult(locVec, self.Yloc)
            self.Yloc.getArray()[self.bdDofs] = 0.0
            self.raspen.locKsp.solve(self.Yloc, self.Yloc)
            self.DDPart.restrict(self.Yloc)
            # Copy resulting data
            result = np.copy(self.Yloc.getArray())
            return result

        def mat_vec_transpose(v):
            """
            Transpose matrix mat-vec product
            """
            # Flattening data
            v = v.flatten()
            # Allocating a local work vector to store data
            locVec = self.Yloc.duplicate()
            locVec.set(0.0)
            # Writing data on the work vector
            locVec.getArray()[:] = v
            # Computations...
            self.DDPart.restrict(locVec)
            self.raspen.locKsp.solveTranspose(locVec, locVec)
            locVec.getArray()[self.bdDofs] = 0.0
            self.raspen.Jloc.multTranspose(locVec, self.Yloc)
            # Unscaled values
            result = self.Yloc.getArray()[self.bdDofs]
            # Scale and return
            return result * self.SQMult

        # Making the scipy linear operator
        linOp = LinearOperator(size, matvec=mat_vec, rmatvec=mat_vec_transpose)
        return linOp

    def BtBOperator(self):
        """
        This implements the subdomain symmetritized
        matrix of the subdomain off-diagonal B that is: B.t B
        """
        # subdomain ghosts size
        ng = len(self.bdDofs)

        # The symmetric matrix mat-vec product
        def mat_vec(v):
            # Flattening vector data
            v = v.flatten()
            # Local work vector
            locVec = self.Yloc.duplicate()
            # Mat product
            locVec.set(0.0)
            # Writting data in work vector
            locVec.getArray()[self.bdDofs] = v
            # Computations...
            self.raspen.Jloc.mult(locVec, self.Yloc)
            self.Yloc.getArray()[self.bdDofs] = 0.0
            self.raspen.locKsp.solve(self.Yloc, self.Yloc)
            self.DDPart.restrict(self.Yloc)
            # Mat transpose product
            locVec.getArray()[:] = self.Yloc[:]
            self.DDPart.restrict(locVec)
            self.raspen.locKsp.solveTranspose(locVec, locVec)
            locVec.getArray()[self.bdDofs] = 0.0
            self.raspen.Jloc.multTranspose(locVec, self.Yloc)
            # Copy resulting data
            result = np.copy(self.Yloc.getArray()[self.bdDofs])
            return result

        # Returning the linear operator
        return LinearOperator((ng, ng), matvec=mat_vec)

    def buildCoarseSnes(self):
        """
        This routine rebuilds coarse snes
        parameters with a smaller size
        """
        # Assertion for prolongation existence
        assert isinstance(self.P, PETSc.Mat), "Prolongation not built yet"
        # Getting a model vector for multiplication of
        # the coarse prolongation from the right side
        self.Xc = self.P.getVecRight()
        # Number of coarse space vectors contributed by the subdomain
        nl = self.Xc.getLocalSize()
        # The total size of the coarse problem
        self.coarseSize = self.Xc.getSize()
        # PETSc vector to host the coarse function values
        self.Fc = self.Xc.duplicate()
        # Allocating the coarse Jacobian
        if self.CPbMFJac:
            # Shell type: defined only by its action on a vector
            self.Jc = PETSc.Mat().createPython(
                ([nl, self.coarseSize], [nl, self.coarseSize]), comm=self.comm
            )
        else:
            # Sparse PETSc matrix
            self.Jc = PETSc.Mat().createAIJ(
                ([nl, self.coarseSize], [nl, self.coarseSize]), comm=self.comm
            )
            # Setting up th matrix
            self.Jc.setUp()

        # -------- Snes Setup ----------
        Snes = PETSc.SNES().create(comm=self.comm)
        Snes.prefix = "csnes_"
        Snes.setFunction(self.GalerkinCoarseFunction, self.Fc)
        Snes.setJacobian(self.GalerkinCoarseJacobian, self.Jc)
        # Snes.setUseMF(True)
        Snes.setTolerances(max_it=self.maxIt, rtol=self.rtol, atol=self.atol)
        # Set from petsc options
        Snes.setFromOptions()
        # Setting the KSP options
        snesKsp = Snes.getKSP()
        if self.CPbMFJac:
            snesKsp.setType("gmres")
            snesKsp.getPC().setType("none")
        elif self.isRedistributed:
            snesKsp.setType("preonly")
            linearPC = snesKsp.getPC()
            linearPC.setType("python")
            subCommSize = min(self.size, 12)
            ctx = GalerkinPcCtx(subCommSize)
            linearPC.setPythonContext(ctx)
        else:
            snesKsp.setType("preonly")
            snesKsp.getPC().setType("lu")

        # Snes.setMonitor(coarse_monitor)
        Snes.setUp()
        # # Setting monitoring function to coarse snes
        # self.raspen.Logger.setLocalMonitoringFunction(Snes)
        return Snes

    def updateProlongation(self, P):
        """
        Updates the prolongation operator
        """
        assert isinstance(P, PETSc.Mat), "P is not a PETSc mat"
        glbSize, coarseSize = P.getSize()[1]
        assert self.glbSize == glbSize
        self.P = P
        if not self.coarseSize == coarseSize:
            # Rebuild snes due to problem size change
            self.GCSnes = self.buildCoarseSnes()

    def getLocalProlongation(self):
        """
        Gets the local part of the prolongation operator
        """
        # Rows index set
        rowsIs = PETSc.IS().createGeneral(self.DDPart.local_dofs)
        # Cols index set
        colsIs = PETSc.IS().createGeneral(np.arange(self.P.getSize()[1], dtype=np.int32))
        self.Ploc = self.P.createSubMatrices(rowsIs, colsIs)[0]

    def coarseProlongation(self, X, fineVec, coef=None):
        """
        Prolongates from coarse to fine mesh
        """
        # Ensuring prolongation operator is already built
        assert self.ProlongationIsBuilt, "The prolongation has not yet been built."
        # Check is a coef is given for add mode else do insert mode

        if coef is None:
            fineVec.set(0.0)
            coef = 1.0
        else:
            assert isinstance(coef, float)

        condition = self.coarsePbSide == "Left" and self.coarseSpaceType == "SubdomainSVD"
        if condition:
            locVec = self.Yloc.duplicate()
            locVec.set(0.0)
            locVec.getArray()[self.intDofs] = self.P(X).getArray()[:]
            locVec.scale(coef)
            self.raspen.vecscatter(locVec, fineVec, mode="reverse", addv=True)
        else:
            fineVec.axpy(coef, self.P(X))

        # --------------------------------------------------
        # --------------------------------------------------
        #    Below, an alternative way to prolongate
        # --------------------------------------------------
        # --------------------------------------------------

        # locVec = self.Yloc.duplicate()
        # locVec.set(0.)
        # locVec.getArray()[self.DDPart.local_interior_dofs] = self.P(X).getArray()[:]
        # locVec.scale(coef)
        # self.raspen.vecscatter(locVec,fineVec,mode="reverse",addv=True)

    def coarseRestriction(self, fineVec, Y):
        """
        Restricts from fine to coarse mesh
        in a Galerkin way R = P.T
        """
        # Ensuring prolongation operator is already built
        assert self.ProlongationIsBuilt, "The prolongation has not yet been built."
        # Restrict
        # # self.P.multTranspose(fineVec,Y)

        condition = self.coarsePbSide == "Left" and self.coarseSpaceType == "SubdomainSVD"
        if condition:
            locVec = self.Yloc.duplicate()
            self.raspen.vecscatter(fineVec, locVec)
            temp = self.P.getVecLeft()
            temp.getArray()[:] = locVec.getArray()[self.intDofs]
            self.P.multTranspose(temp, Y)
        else:
            self.P.multTranspose(fineVec, Y)

        # --------------------------------------------------
        # --------------------------------------------------
        #      Below, an alternative way to restrict
        # --------------------------------------------------
        # --------------------------------------------------

        # locVec = self.Yloc.duplicate()
        # self.raspen.vecscatter(fineVec,locVec)
        # temp = self.P.getVecLeft()
        # temp.getArray()[:] = locVec.getArray()[self.DDPart.local_interior_dofs]
        # self.P.multTranspose(temp,Y)

    def GalerkinCoarseFunction(self, snes, X, Y):
        """
        Galerkin coarse projected function
        Where X is a vector in the fine mesh
        """
        t_s = time()
        if self.t_ksp is not None:
            print(" Coarse Lu time :", time() - self.t_ksp, flush=True)
        # Prolongate coarse solution to fine mesh
        self.coarseProlongation(X, self.glbVec)
        # Add the global solution to correction
        self.glbVec.axpy(1.0, self.glbSol)
        self.raspen.vecscatter(self.glbVec, self.raspen.locSol)
        # Assembling the original problem operators
        t_ops = time()
        self.operators(self.raspen.locSol, self.Yloc, self.raspen.Jloc)
        print("Operators execution time:", time() - t_ops, flush=True)
        self.raspen.Jloc.copy(self.raspen.Jploc)
        # Save the Jacobian in right coarse side type
        if self.saveLocalJac:
            self.raspen.Jloc.copy(self.raspen.Jloc0)
        # Restrict solution to subdomain level
        self.DDPart.restrict(self.Yloc)
        self.glbVec.set(0.0)
        self.raspen.vecscatter(self.Yloc, self.glbVec, addv=True, mode="reverse")
        # Saving function norm for monitoring purposes
        self.fineNorm = self.glbVec.norm()
        # Restricting the fine function norm the coarse level
        self.coarseRestriction(self.glbVec, Y)
        Y.scale(-1.0)
        self.t_ksp = time()
        self.funcTime += time() - t_s
        print("Coarse function evaluation:", time() - t_s, flush=True)

    def GalerkinCoarseJacobian(self, snes, X, Jc, Jcp):
        """
        Jacobian of coarse function
        """
        if self.CPbMFJac:
            # Here the Jacobian will be defined only its action
            ctx = GalerkinJacCtx(self, self.raspen.Jloc)
            Jc.setPythonContext(ctx)
            Jc.setUp()
        else:
            # Here the matrix entries of Jc will be computed
            t = time()
            self.AssembleJacMatrix(self.raspen.Jloc, Jc)
            self.assTime += time() - t
            # Build the sequential KSP in case
            if self.isRedistributed:
                pc = snes.getKSP().getPC()
                ctx = pc.getPythonContext()
                ctx.buildKSP(Jc)

    def AssembleJacMatrix(self, Jloc, Jc):
        """
        Assembles the entries of the coarse Jacobian
        """
        # Create a nonoverlapping work copy of the coarse Jacobian
        Jwork = Jloc.copy()
        # Sets the rows corresponding to overlapping dofs to zero
        Jwork.zeroRows(self.DDPart.local_ovlp_dofs, 0.0)
        # Do the Ploc.T x Jwork x Ploc mat product
        ResMat = Jwork.ptap(self.Ploc)
        Jwork.destroy()
        # Getting CSR Values
        I, J, V = ResMat.getValuesCSR()
        # Setting CSRValues
        Jc.zeroEntries()
        Jc.setValuesLocalCSR(I, J, V, addv=True)
        # Assembling the matrix
        Jc.assemble()

    def correct(self, X, Y=None):
        """
        Performs the coarse correction
        """
        # Build snes if needed
        if not self.GCSnes:
            self.GCSnes = self.buildCoarseSnes()
        if Y is None:
            Y = X.duplicate()
            reuse = False
        else:
            reuse = True
        Y.set(0.0)
        X.copy(self.glbSol)
        self.Xc.set(0.0)
        self.t_ksp = None
        self.GCSnes.solve(None, self.Xc)
        self.coarseProlongation(self.Xc, Y)
        if not reuse:
            return Y


class GalerkinJacCtx:
    """
    The context of the galerkin jacobian
    """

    def __init__(self, GCGC, J):
        """
        Context constructor
        """
        self.GCGC = GCGC
        self.raspen = GCGC.raspen
        self.DDPart = GCGC.DDPart
        self.glbVec = GCGC.glbVec
        self.Yloc = self.Yloc
        self.J = J.copy()

    def mult(self, snes, X, Y):
        """
        Multiplication routine
        """
        self.GCGC.coarseProlongation(X, self.glbVec)
        self.raspen.vecscatter(self.glbVec, self.Yloc)
        temp = self.J(self.Yloc)
        self.DDPart.restrict(temp)
        self.glbVec.set(0.0)
        self.raspen.vecscatter(temp, self.glbVec, mode="reverse", addv=True)
        self.GCGC.coarseRestriction(self.glbVec, Y)


class GalerkinPcCtx:
    """
    The context of the preconditioner for the galerkin jacobian
    """

    def __init__(self, subCommSize=1):
        """
        Context constructor
        """
        # Get proc rank
        self.rank = MPI.ASTER_COMM_WORLD.Get_rank()
        # Number of procs
        self.size = MPI.ASTER_COMM_WORLD.Get_size()
        # Size of the subcommunicator
        self.subCommSize = subCommSize
        # Sequential Jac
        self.redJac = None
        # Sequental KSP
        self.redKSP = None
        # Vecscatter to zero
        self.vecscatter = None
        # Redistribution vecscatter
        self.vecscatter_red = None
        # # Redistribution vecscatter
        # self.redVecScatter = self.createRedVecScatter()
        if subCommSize > 1:
            self.apply = self.apply_redistributed
        else:
            self.apply = self.apply_seq

    # def createRedVecScatter(self):
    #     """
    #     Creates a vecscatter from the original
    #     comm to subcomm used for redistribution
    #     """
    #     self.redVecScatter = PETSc.Scatter().create()

    def buildKSP(self, Jc):
        """
        builds the sequential KSP from the parallely
        distributed coarse Jacobian.
        """
        redFct = self.size // self.subCommSize
        if self.subCommSize > 1:
            self.redJac = redistributePetscMat(Jc, redFct)
        else:
            n = Jc.getSize()[0]
            start, end = Jc.getOwnershipRange()
            if self.rank == 0:
                idxs = np.arange(0, n, dtype=np.int32)
                isRows = PETSc.IS().createGeneral(idxs)
            else:
                idxs = np.arange(start, end, dtype=np.int32)
                isRows = PETSc.IS().createGeneral(idxs)
            self.redJac = Jc.createSubMatrices(isRows)[0]
        # Creating the Vecscatter
        self.vecscatter = PETSc.Scatter().toZero(Jc.getVecRight())[0]
        # Set up the linear solver
        if self.redJac:
            # Defining the redistribution vecscatter
            if self.subCommSize > 1:
                self.vecscatter_red = PETSc.Scatter().toZero(self.redJac.getVecRight())[0]
            comm = self.redJac.getComm()
            # Create the linear solver (KSP)
            ksp = PETSc.KSP().create(comm)
            # Set KSP options from petsc commands
            ksp.setFromOptions()
            # Set the sequential matrix as an operator
            ksp.setOperators(self.redJac)
            # Use direct solver (LU)
            ksp.setType("preonly")
            # Set MUMPS as the LU solver
            pc = ksp.getPC()
            pc.setType("lu")
            pc.setFactorSolverType("mumps")
            ksp.setUp()
            self.redKSP = ksp

    def apply_seq(self, mat, X, Y):
        """
        The preconditioner Matrix-Vector product for sequential solve
        """
        timings = {}
        start = time()
        # Assert that the ksp is built
        assert self.redKSP is not None, "Sequential KSP is not built yet"
        # Apply the sequential LU solve
        if self.rank == 0:
            XSeq = self.redJac.getVecRight()
        else:
            # Dummy vector with size 0 on other ranks
            XSeq = PETSc.Vec().createSeq(0, comm=MPI.ASTER_COMM_SELF)
        timings["Creating_sequential_vec"] = time() - start
        start = time()
        self.vecscatter.scatter(X, XSeq)
        timings["Forward_scattering"] = time() - start

        if self.rank == 0:
            start = time()
            self.redKSP.solve(XSeq, XSeq)
            timings["Ksp_solve"] = time() - start

        start = time()
        self.vecscatter.scatter(XSeq, Y, mode="reverse")
        timings["Backward_scattering"] = time() - start
        # if self.rank == 0 and self.raspen.verbose:
        #     print("\n[Timing for apply_seq()]", flush=True)
        #     for k, v in timings.items():
        #         print(f"  {k}: {v:.6f} seconds", flush=True)

    def apply_redistributed(self, mat, X, Y):
        """
        The preconditioner Matrix-Vector product for redistributed solve
        """
        timings = {}
        start = time()
        # Communicating the distributed vector to the proc zero
        if self.rank == 0:
            n = X.getSize()
            XSeq = PETSc.Vec().createSeq(n, comm=MPI.ASTER_COMM_SELF)
        else:
            # Dummy vector with size 0 on other ranks
            XSeq = PETSc.Vec().createSeq(0, comm=MPI.ASTER_COMM_SELF)
        timings["Creating_sequential_vec"] = time() - start
        start = time()
        self.vecscatter.scatter(X, XSeq)
        timings["Forward_scattering"] = time() - start

        # Applying preconditioner on the subcomm
        if self.redKSP:
            start = time()
            # The proc zero gets the RHS from procs of the subcomm
            Xred = self.redJac.getVecRight()
            self.vecscatter_red.scatter(XSeq, Xred, mode="reverse")
            timings["red_Backward_scattering"] = time() - start

            # Solve LU on the subcommunicator
            start = time()
            self.redKSP.solve(Xred, Xred)
            timings["Ksp_solve"] = time() - start

            # Writing the result on the proc zero
            start = time()
            self.vecscatter_red.scatter(Xred, XSeq, mode="forward")
            timings["red_Forward_scattering"] = time() - start
        start = time()
        # The zero proc communicates back the result to all
        self.vecscatter.scatter(XSeq, Y, mode="reverse")
        timings["Backward_scattering"] = time() - start
        # if self.rank == 0 and self.raspen.verbose:
        #     print("\n[Timing for apply_redistributed()]", flush=True)
        #     for k, v in timings.items():
        #         print(f"  {k}: {v:.6f} seconds", flush=True)


class RASPENLogger:
    """
    A class that stuctor the monitoring
    logs of local nonlinear solvers
    """

    def __init__(self, raspen):
        """
        Logger class Initializer
        """
        self.raspen = raspen
        self.rank = raspen.rank
        self.size = raspen.size
        self.locSnes = raspen.locSnes
        self.DDPart = raspen.DDPart
        self.fnorm0 = None
        self.TabHeaders = [
            "Iteration",
            "Local Residual",
            "Local Relative Residual",
            "KSP Type",
            "KSP.PC Type",
            "KSP Converged Reason",
        ]
        self.TabData = []

    def setLocalMonitoringFunction(self, inSnes):
        """
        Set a customized monitoring function to snes
        """

        def SnesMonitor(snes, its, fnorm):
            """
            A customized monitoring function
            """
            if its == 0:
                self.fnorm0 = fnorm
            rnorm = fnorm / self.fnorm0 if self.fnorm0 > 0 else 0
            KSP = snes.getKSP()
            KSP_Type = KSP.getType()
            PC_Type = KSP.getPC().getType()
            CvrReason = KSP.getConvergedReason()
            self.TabData.append(
                [its, f"{fnorm:.8e}", f"{rnorm:.8e}", KSP_Type, PC_Type, Cvr_Rs_Dict.get(CvrReason)]
            )

        inSnes.setMonitor(SnesMonitor)

    # def log(self, msg):
    #     """
    #     Logs monitoring table
    #     """
    #     tab = tabulate(self.TabData, self.TabHeaders, tablefmt="pretty")
    #     self.print_box(msg, extra_content=tab + "\n")

    def print_box(self, content, extra_content="", vpad=3, hpad=12, tab=""):
        """
        Puts a logs content inside a box
        """
        box_width = len(content) + hpad  # Adjust the width based on content size
        top_lines = (vpad - 1) // 2
        bottom_lines = vpad - top_lines - 1

        pattern = (
            "\n"
            + "*" * box_width
            + "\n"
            + "".join(["*{:^{width}}*\n".format("", width=box_width - 2) for _ in range(top_lines)])
            + "*{:^{width}}*\n".format(content, width=box_width - 2)
            + "".join(
                ["*{:^{width}}*\n".format("", width=box_width - 2) for _ in range(bottom_lines)]
            )
            + "*" * box_width
            + "\n"
            + tab
            + "\n"
        )
        print(pattern + extra_content, flush=True)

    def cleanLogs(self):
        """
        Cleans logs from previous iteration data
        """
        self.fnorm0 = None
        self.TabData = []
