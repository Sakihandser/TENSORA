# coding: utf-8

# Copyright (C) 1991 - 2026  EDF www.code-aster.org
#
# This file is part of Code_Aster.
#
# Code_Aster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Code_Aster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Code_Aster.  If not, see <http://www.gnu.org/licenses/>.

from libaster import deleteCachedObjects, resetFortranLoggingLevel, setFortranLoggingLevel

from ..CodeCommands import CALC_CHAMP
from ..Objects import (
    HHO,
    AssemblyMatrixTemperatureReal,
    DiscreteComputation,
    FieldOnNodesReal,
    LinearSolver,
    ParallelThermalLoadFunction,
    ParallelThermalLoadReal,
    PhysicalProblem,
    ThermalDirichletBC,
    ThermalLoadFunction,
    ThermalLoadReal,
    ThermalResult,
)

from ..Utilities import SearchList, logger, print_stats, profile, reset_stats
from ..Solvers import PhysicalState, StorageManager, TimeStepper
from ..Solvers import ProblemType as PBT
from ..Solvers.Post import ComputeTempFromHHO


def _checkArgs(args):
    if args.get("RESULTAT") is not None and args.get("reuse") is not None:
        assert args.get("RESULTAT") is args.get("reuse")

    if args.get("RESULTAT") is not None or args.get("reuse") is not None:
        assert args.get("ETAT_INIT") is not None
        assert args.get("ETAT_INIT").get("STAT") is None


def _hasExchangeFields(args):
    has_fields = False
    if args.get("EXCIT") is not None:
        for loadkws in args["EXCIT"]:
            load = loadkws["CHARGE"]
            if isinstance(load, (ThermalLoadFunction, ThermalLoadReal)):
                has_fields = (
                    has_fields
                    or load.hasLoadResult()
                    or load.hasLoadField("COEFH")
                    or load.hasLoadField("HECHP")
                )
    return has_fields


@profile
def _addLoads(phys_pb, args):
    """Add loads from cata inplace

    Arguments:
        phys_pb (PhysicalProblem): Physical problem to add load
        **args (dict): User's keywords.

    Returns:
        (PhysicalProblem): Modifel physical problem inplace
    """

    if args.get("EXCIT") is not None:
        for load in args["EXCIT"]:
            if isinstance(
                load["CHARGE"],
                (
                    ThermalLoadFunction,
                    ThermalLoadReal,
                    ThermalDirichletBC,
                    ParallelThermalLoadFunction,
                    ParallelThermalLoadReal,
                ),
            ):
                phys_pb.addLoadFromDict(load)
            else:
                raise RuntimeError("Unknown load")

    phys_pb.computeListOfLoads("THER_LINEAIRE")

    return phys_pb


@profile
def _setupInitialField(phys_pb, args):
    logger.debug("<THER_LINEAIRE><ETAT_INIT>: Start")

    initial_field = None
    is_stat_init = False
    initial_state = args.get("ETAT_INIT")

    if args["TYPE_CALCUL"] == "STAT" or "STAT" in initial_state:
        logger.debug(
            "<THER_LINEAIRE><ETAT_INIT>: Stationnary Computation initialized with a null field"
        )
        initial_field = FieldOnNodesReal(phys_pb.getDOFNumbering())
        initial_field.setValues(0.0)
        is_stat_init = True
    elif "CHAM_NO" in initial_state:
        logger.debug(
            "<THER_LINEAIRE><ETAT_INIT>: Initialized with given field '%s'"
            % initial_state.get("CHAM_NO").getName()
        )
        initial_field = initial_state["CHAM_NO"].copyUsingDescription(
            phys_pb.getDOFNumbering().getEquationNumbering()
        )
    elif "VALE" in initial_state:
        logger.debug(
            "<THER_LINEAIRE><ETAT_INIT>: Initialized with constant field with value %s"
            % initial_state["VALE"]
        )
        # For HHO, there is a projection to do.
        if phys_pb.getModel().existsHHO():
            initial_field = HHO(phys_pb).projectOnHHOSpace(initial_state["VALE"])
        else:
            initial_field = FieldOnNodesReal(phys_pb.getDOFNumbering())
            initial_field.setValues(initial_state["VALE"])
    elif "EVOL_THER" in initial_state:
        resu_ther = initial_state.get("EVOL_THER")
        para = resu_ther.getAccessParameters()

        index = initial_state.get("NUME_ORDRE") or para["NUME_ORDRE"][-1]

        if initial_state.get("INST") is not None:
            timelist = SearchList(
                para["INST"], initial_state["PRECISION"], initial_state["CRITERE"]
            )
            indext = timelist.index(initial_state["INST"])
            index = para["NUME_ORDRE"][indext]

        initial_field = resu_ther.getField("TEMP", index).copyUsingDescription(
            phys_pb.getDOFNumbering().getEquationNumbering()
        )
        logger.debug(
            "<THER_LINEAIRE><ETAT_INIT>: Initialized with field from '%s' at index '%s'"
            % (resu_ther.getName(), index)
        )
    else:
        assert False

    assert initial_field is not None
    logger.debug("<THER_LINEAIRE><ETAT_INIT>: Finish")
    return initial_field, is_stat_init


def _createTimeStepper(stationary, args):
    """Create time stepper from keywords

    Arguments:
        stationary (bool): *True* for a stationary study.
        args (dict): User's keywords.

    Returns:
        TimeStepper: a time stepper.
    """
    # <tpla06a> TYPE_CALCUL="STAT": initial=None, t=[0.]
    # <ttll01a.1> TYPE_CALCUL="TRAN" + STAT="OUI": initial=0., t=[0.001, ...]
    # <ttll01a.2> TYPE_CALCUL="TRAN" + STAT=None/EVOL_THER: initial=0.02, t=[0.03, ...]
    # <zzzz185a> TYPE_CALCUL="TRAN" + STAT="OUI": initial=0., t=[]
    logger.debug("<THER_LINEAIRE><TIMESTEPPER>: Start")
    if stationary:
        stepper = TimeStepper.from_keywords(**args["INCREMENT"], INST_INIT=None)
    else:
        stepper = TimeStepper.from_keywords(**args["INCREMENT"])
    resu = args.get("RESULTAT")
    if resu:
        last = resu.getLastTime()
        stepper.setInitial(last)

    logger.debug("<THER_LINEAIRE><TIMESTEPPER>: initial = %s", stepper.getInitial())
    logger.debug("<THER_LINEAIRE><TIMESTEPPER>: final = %s", stepper.getFinal())
    logger.debug("<THER_LINEAIRE><TIMESTEPPER>: size = %s", stepper.size())
    logger.debug("<THER_LINEAIRE><TIMESTEPPER>: times = %s", repr(stepper))
    return stepper


@profile
def _computeMatrix(disr_comp, matrix, is_evol, time_curr, time_delta, time_theta):
    """Compute and assemble the thermal matrix

    Arguments:
        disr_comp (DiscreteComputation): to compute discrete quantities
        matrix (AssemblyMatrixTemperatureReal): matrix to compute and assemble inplace
        time_curr (float): Current time
        time_delta (float): Time increment
        time_theta (float): Theta parameter for time scheme

    Returns:
        AssemblyMatrixTemperatureReal: matrix computed and assembled
    """
    logger.debug("<THER_LINEAIRE><MATRIX>: Start")

    phys_pb = disr_comp.getPhysicalProblem()

    varc = phys_pb.getExternalStateVariables(time_curr)

    matrElem = []

    logger.debug("<THER_LINEAIRE><MATRIX>: Linear Conductivity")
    matr_elem_rigi = disr_comp.getLinearStiffnessMatrix(time_curr, varc_curr=varc, with_dual=False)
    matrElem.append((matr_elem_rigi, time_theta))

    matr_elem_exch = disr_comp.getThermalExchangeMatrix(time_curr)
    matrElem.append((matr_elem_exch, time_theta))

    if phys_pb.getDOFNumbering().useLagrangeDOF():
        logger.debug("<THER_LINEAIRE><MATRIX>: Dual Conductivity")
        matr_elem_dual = disr_comp.getDualLinearConductivityMatrix()
        matrElem.append((matr_elem_dual, 1.0))

    if is_evol:
        logger.debug("<THER_LINEAIRE><MATRIX>: Linear Capacity")

        matr_elem_capa = disr_comp.getLinearCapacityMatrix(time_curr, varc)
        matrElem.append((matr_elem_capa, 1.0 / time_delta))

    matrix.assemble(matrElem, phys_pb.getListOfLoads())

    logger.debug("<THER_LINEAIRE><MATRIX>: Finish")

    return matrix


@profile
def _computeRhs(disr_comp, is_evol, time_curr, time_delta, time_theta, previousPrimalField):
    """Compute and assemble the right hand side

    Arguments:
        disr_comp (DiscreteComputation): to compute discrete quantities
        time_curr (float): Current time
        time_delta (float): Time increment
        time_theta (float): Theta parameter for integration
        previousPrimalField (fieldOnNodesReal): solution field at previous time

     Returns:
         FieldOnNodesReal: vector of load
    """

    logger.debug("<THER_LINEAIRE><RHS>: Start")

    # compute imposed temperature with Lagrange
    rhs = disr_comp.getImposedDualBC(time_curr)
    logger.debug("<THER_LINEAIRE><RHS>: Nodal BC")

    @profile
    def rhs_theta(disr_comp, time, temp):
        varc = disr_comp.getPhysicalProblem().getExternalStateVariables(time)

        rhs = disr_comp.getThermalNeumannForces(time)

        rhs += disr_comp.getThermalVolumetricForces(time, varc_curr=varc)

        rhs += disr_comp.getThermalExchangeForces(temp, time)

        rhs += disr_comp.getTransientThermalLoadForces(time, temp)

        logger.debug("<THER_LINEAIRE><RHS>: Neumann BC")

        return rhs

    if is_evol:
        # compute load at time_prev (theta=0)
        rhs += (1.0 - time_theta) * rhs_theta(
            disr_comp, time_curr - time_delta, previousPrimalField
        )

    # compute load at time_curr (theta=1)
    rhs += time_theta * rhs_theta(
        disr_comp, time_curr, FieldOnNodesReal(disr_comp.getPhysicalProblem().getDOFNumbering())
    )

    if is_evol:
        varc = disr_comp.getPhysicalProblem().getExternalStateVariables(time_curr)

        rhs += disr_comp.getTransientThermalForces(
            time_curr, time_delta, time_theta, previousPrimalField, varc_curr=varc
        )

        logger.debug("<THER_LINEAIRE><RHS>: Transient Load BC")

    logger.debug("<THER_LINEAIRE><RHS>: Finish")
    return rhs


class OperatorMockup:
    """Simulate a NonLinearOperator object."""

    def __init__(self, phys_pb, phys_state) -> None:
        self.problem = phys_pb
        self.state = phys_state


def _post_hooks(lin_operator, hooks):
    """Call hooks"""
    for hook in hooks:
        hook(lin_operator)


def ther_lineaire_ops(self, **args):
    """Execute the command THER_LINEAIRE.

    Arguments:
        **args (dict): User's keywords.

    Returns:
        ThermalResult: result for linear thermal problem
    """
    logger.debug("<THER_LINEAIRE>: Initialization")
    logger.debug("<THER_LINEAIRE>: Args : %s" % args)

    _checkArgs(args)

    verbosity = args.get("INFO") or 1
    setFortranLoggingLevel(verbosity)
    reset_stats()

    is_evol = args["TYPE_CALCUL"] == "TRAN"

    # Create result
    result = args.get("RESULTAT") or args.get("reuse")
    if result is None:
        result = ThermalResult()
        result.setTitle(args.get("TITRE") or "RESU_THER_LINEAIRE")

    # Create physical problem
    model = args["MODELE"]
    phys_pb = PhysicalProblem(model, args["CHAM_MATER"], args.get("CARA_ELEM"))
    logger.debug("<THER_LINEAIRE>: Physical Problem created")

    # Add loads
    phys_pb = _addLoads(phys_pb, args)
    has_exchange_fields = _hasExchangeFields(args)
    logger.debug("<THER_LINEAIRE>: Loads added")

    # Compute numbering
    phys_pb.computeDOFNumbering()
    logger.debug("<THER_LINEAIRE>: DOFNumbering computed")

    # Setup ETAT_INIT
    initial_field, is_stat_init = _setupInitialField(phys_pb, args)

    # Create time stepper
    timeStepper = _createTimeStepper(not is_evol, args)

    # do not erase initial state if the same result is reused
    first_index = 0
    save_initial_state = True
    if not is_evol:
        first_index = 1
    elif args.get("RESULTAT"):
        resu = args["RESULTAT"]
        first_index = resu.getLastIndex()
        if resu is args["ETAT_INIT"].get("EVOL_THER"):
            first_index += 1
            save_initial_state = False
    logger.debug(
        "<THER_LINEAIRE><STORAGE>: first_index=%d, save_init=%s", first_index, save_initial_state
    )

    # Create linear solver
    linear_solver = LinearSolver.factory("THER_LINEAIRE", args["SOLVEUR"])
    if (model.getMesh().isParallel()) and (not linear_solver.supportParallelMesh()):
        raise RuntimeError("ParallelMesh not allowed with this linear solver")

    linear_solver.build()

    # Create storage manager
    storage_manager = StorageManager(result, args["ARCHIVAGE"])
    storage_manager.setFirstStorageIndex(first_index)

    # Define main objects
    phys_state = PhysicalState(PBT.Thermal)
    disc_comp = DiscreteComputation(phys_pb)
    lin_operator = OperatorMockup(phys_pb, phys_state)
    hooks = [ComputeTempFromHHO()]

    # we define the matrix before to have an unique name
    # because of a bug with LDLT_SP
    matrix = AssemblyMatrixTemperatureReal(phys_pb)
    # the matrix depends on times or external variables
    is_const = phys_pb.getCodedMaterial().constant()

    # Detect external state variables
    hasExternalStateVariable = phys_pb.getMaterialField().hasExternalStateVariable()

    # Compute reference value vector for external state variables
    if phys_pb.getMaterialField().hasExternalStateVariableWithReference():
        phys_pb.computeReferenceExternalStateVariables()

    # Run computation
    logger.debug("<THER_LINEAIRE>: Start computation")

    phys_state.zeroInitialState(phys_pb)
    phys_state.U = initial_field
    time_delta_prev = timeStepper.null_increment

    step_rank = 0
    # Compute initial state
    if is_evol:
        phys_state.time_curr = timeStepper.getInitial()
        time_theta = 1.0
        time_delta = timeStepper.null_increment
        if is_stat_init:
            matrix = _computeMatrix(
                disc_comp, matrix, False, phys_state.time_curr, time_delta, time_theta
            )
            linear_solver.factorize(matrix)

            rhs = _computeRhs(
                disc_comp, False, phys_state.time_curr, time_delta, time_theta, phys_state.U
            )

            # solve linear system
            diriBCs = disc_comp.getDirichletBC(phys_state.time_curr)
            phys_state.U = linear_solver.solve(rhs, diriBCs)

        _post_hooks(lin_operator, hooks)
        phys_state.commit()

        if save_initial_state:
            storage_manager.storeState(
                step_rank,
                phys_state.time_curr,
                phys_pb,
                phys_state,
                param={"PARM_THETA": time_theta},
            )

    # Loop on time step
    while not timeStepper.isFinished():
        phys_state.time_curr = timeStepper.getCurrent()

        if is_evol:
            time_theta = args["SCHEMA_TEMPS"]["THETA"]
            time_delta = timeStepper.getIncrement()
        else:
            time_theta = 1.0
            time_delta = timeStepper.null_increment

        logger.debug("<THER_LINEAIRE>:     IS_EVOL %s", is_evol)
        logger.debug("<THER_LINEAIRE>:     IS_CONST = %s", is_const)
        logger.debug("<THER_LINEAIRE>:     HAS_EXT_STATE_VAR = %s", hasExternalStateVariable)
        logger.debug("<THER_LINEAIRE>:     CURRENT TIME %s", phys_state.time_curr)
        logger.debug("<THER_LINEAIRE>:     TIME_CURR %s", phys_state.time_curr)
        logger.debug("<THER_LINEAIRE>:     TIME_DELTA %s", time_delta)
        logger.debug("<THER_LINEAIRE>:     TIME_THETA %s", time_theta)

        if (
            not is_const
            or (is_const and time_delta == timeStepper.null_increment)
            or (is_const and has_exchange_fields)
            or (is_const and abs(time_delta - time_delta_prev) > timeStepper.null_increment)
            or (is_const and hasExternalStateVariable)
        ):
            matrix = _computeMatrix(
                disc_comp, matrix, is_evol, phys_state.time_curr, time_delta, time_theta
            )
            linear_solver.factorize(matrix)

        rhs = _computeRhs(
            disc_comp, is_evol, phys_state.time_curr, time_delta, time_theta, phys_state.U
        )

        # solve linear system
        diriBCs = disc_comp.getDirichletBC(phys_state.time_curr)
        phys_state.U = linear_solver.solve(rhs, diriBCs)

        _post_hooks(lin_operator, hooks)
        phys_state.commit()

        step_rank += 1
        storage_manager.storeState(
            step_rank, phys_state.time_curr, phys_pb, phys_state, param={"PARM_THETA": time_theta}
        )

        timeStepper.completed()
        time_delta_prev = time_delta

    logger.debug("<THER_LINEAIRE>: Finish computation")
    # delete factorized matrix - free memory
    linear_solver.deleteFactorizedMatrix()

    # store field
    result = storage_manager.getResult()

    if model.isXfem():
        result = CALC_CHAMP(RESULTAT=result, reuse=result, THERMIQUE="TEMP_ELGA")

    if verbosity > 1:
        print_stats()
    resetFortranLoggingLevel()
    reset_stats()

    # cleaning
    deleteCachedObjects()

    return result
