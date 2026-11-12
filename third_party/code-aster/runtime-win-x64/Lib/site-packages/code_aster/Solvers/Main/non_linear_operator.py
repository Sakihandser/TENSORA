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

from contextlib import AbstractContextManager

from libaster import deleteTemporaryObjects, resetFortranLoggingLevel, setFortranLoggingLevel

from ...Messages import UTMESS, MessageLog
from ...Objects import (
    HHO,
    ConstantFieldOnCellsReal,
    LinearSolver,
    NonLinearResult,
    ParallelContactNew,
    ParallelFrictionNew,
    Physics,
    ThermalResult,
)
from ...Supervis import ConvergenceError, IntegrationError, SolverError
from ...Utilities import (
    DEBUG,
    INFO,
    WARNING,
    ExecutionParameter,
    Options,
    logger,
    no_new_attributes,
    profile,
)
from ..Basics import Context, ContextMixin, EventId, EventSource, Observation, PhysicalState
from ..Basics import ProblemType as PBT
from ..Operators import BaseOperators
from ..Post import Annealing, ComputeDisplFromHHO, ComputeHydr, ComputeTempFromHHO
from ..StepSolvers import BaseStepSolver
from .contact_manager import ContactManager
from .storage_manager import StorageManager
from .time_stepper import TimeStepper


class NonLinearOperator(ContextMixin, EventSource):
    """Solver for linear and non linear problem.

    Arguments:
        main (*NonLinearFeature*): Main object.
        result (*misc*): The result object.
    """

    __needs__ = ("keywords", "stepper", "problem", "problem_type", "result", "state")

    _eventid = EventId.NonLinearOperator
    _store = _step_solver = _hooks = None
    _verb = None
    # FIXME: prefer _current_matrix and property
    _step_idx = current_matrix = None
    __setattr__ = no_new_attributes(object.__setattr__)

    @classmethod
    def factory(cls, problem, result=None, **keywords):
        """Initialize a *NonLinearOperator*.
        Advanced users may override the *context* of the operator by customizing
        the content of `.context` object.

        NB: You must respect the rules of the related
        command. No default keywords are automatically added.

        Args:
            problem (PhysicalProblem): Problem to be solved.
            result (Result, optional): Object to be eventually reused.
            keywords (dict): Keywords arguments to adjust the features as
                usually passed to MECA_NON_LINE or THER_NON_LINE.

        Returns:
            instance: NonLinearOperator object.
        """
        context = Context()
        context.problem = problem
        context.keywords = keywords
        _get = context.get_keyword

        phys = problem.getModel().getPhysics()
        if phys == Physics.Thermal:
            context.problem_type = PBT.Thermal
            context.result = result or ThermalResult()

        elif phys == Physics.Mechanics:
            context.problem_type = PBT.MecaDyna if _get("SCHEMA_TEMPS") else PBT.MecaStat
            context.result = result or NonLinearResult()
            if _get("CONTACT"):
                definition = _get("CONTACT", "DEFINITION")
                context.contact = ContactManager(definition, problem)
                if isinstance(definition, (ParallelFrictionNew, ParallelContactNew)):
                    fed_defi = definition.getParallelFiniteElementDescriptor()
                else:
                    fed_defi = definition.getFiniteElementDescriptor()
                problem.setContactSlaveFED(fed_defi)
                problem.setContactFED(None)

        else:
            raise TypeError(f"unsupported physics: {phys}")

        context.oper = BaseOperators.factory(context)
        if _get("INCREMENT"):
            context.stepper = TimeStepper.from_keywords(**_get("INCREMENT"))
        if _get("SOLVEUR"):
            context.linear_solver = LinearSolver.factory("MECA_NON_LINE", mcf=_get("SOLVEUR"))
        context.state = PhysicalState(context.problem_type, size=1)
        context.state.setObservation(Observation.builder(context))
        context.check()
        return NonLinearOperator.builder(context)

    @classmethod
    def builder(cls, context):
        """Builder of a NonLinearOperator object.

        Args:
            context (Context): Context of the problem.

        Returns:
            instance: New object.
        """
        instance = cls(context)
        instance.context = context
        return instance

    def __init__(self, context) -> None:
        super().__init__()
        self._hooks = []
        self._step_idx = None
        self.current_matrix = None
        self._verb = logger.getEffectiveLevel(), ExecutionParameter().option & Options.ShowSyntax

    # convenient shortcuts properties to init and access subobjects
    @property
    def store(self):
        if not self._store:
            logger.debug("+++ init StorageManager")
            kwds = self.keywords
            reuse = kwds.get("REUSE")
            self._store = StorageManager(
                self.result, kwds.get("ARCHIVAGE"), reused=reuse is self.result
            )
            if reuse:
                init_state = kwds.get("ETAT_INIT")
                assert init_state
                if "EVOL_NOLI" in init_state:
                    # Pour l'instant, on se restreint au cas où la sd passée
                    # par reuse est la même que celle passée dans ETAT_INIT
                    assert init_state["EVOL_NOLI"] is reuse
                init_index = reuse.getIndexFromParameter(
                    "INST", self.stepper.getInitial(), "RELATIF", self.stepper.null_increment
                )
                # if stepper is None ?! should be happen
                # init_index = reuse.getLastIndex()
                self._store.setFirstStorageIndex(init_index + 1)
                self.state._observ.setReuseIndex(init_index)
        return self._store

    @property
    def step_solver(self):
        if self._step_solver:
            return self._step_solver
        logger.debug("+++ init StepSolver")
        self._step_solver = solv = BaseStepSolver.factory(self.context)
        return solv

    def isFinished(self):
        """Tell if there are steps to be computed.

        Returns:
            bool: *True* if there is no step to be computed, *False* otherwise.
        """
        return self.stepper.isFinished()

    def _storeState(self, state, ignore_policy=False):
        """Store the physical state.

        Arguments:
            time (float): current (pseudo)-time.
            ignore_policy (bool): ignore storing-policy.

        Returns:
            bool: *True* if it was actually stored, else *False*.
        """
        return self.store.storeState(
            self._step_idx,
            state.time_curr,
            self.problem,
            state,
            is_final_time=self.isFinished(),
            ignore_policy=ignore_policy,
        )

    @profile
    def initialize(self):
        """Initialize run"""
        phys_pb = self.problem
        kwds = self.keywords
        # not in builder/__init__ to allow the user to define its own objects
        self.add_observer(self.state)
        self.stepper.add_observer(self.state)
        # essential to be called enough soon (may change the size of VARI field)
        if self.get_keyword("ETAT_INIT"):
            phys_pb.computeBehaviourProperty(kwds["COMPORTEMENT"], "OUI", 2)
        else:
            phys_pb.computeBehaviourProperty(kwds["COMPORTEMENT"], "NON", 2)
        phys_pb.computeListOfLoads()
        phys_pb.computeDOFNumbering()
        if phys_pb.getMaterialField().hasExternalStateVariableForLoad():
            phys_pb.computeReferenceExternalStateVariables()
        self._register_hooks()
        self._step_idx = 0
        self.setInitialState()
        self._storeState(self.state)
        self.notifyObservers()

    def _register_hooks(self):
        if self.problem_type & PBT.AllMechanics:
            self.register_hook(Annealing())
            self.register_hook(ComputeDisplFromHHO())
        elif self.problem_type & PBT.Thermal:
            self.register_hook(ComputeHydr())
            self.register_hook(ComputeTempFromHHO())

    def register_hook(self, hook):
        """Register a new hook.

        Args:
            hook (BaseHook): Object that provides a *BaseHook* interface.
        """
        self._hooks.append(hook)

    # FIXME: mixin by problem_type / factory
    @profile
    def setInitialState(self):
        """Initialize the physical state."""
        self.state.zeroInitialState(self.problem)
        init_state = self.get_keyword("ETAT_INIT")
        nume_equa = self.problem.getDOFNumbering().getEquationNumbering()
        if init_state:
            model = self.problem.getModel()

            if "EVOL_NOLI" in init_state:
                resu = init_state.get("EVOL_NOLI")
                assert isinstance(resu, NonLinearResult), resu
                para, value = _extract_param(init_state, resu)

                self.state.U = resu.getField("DEPL", para=para, value=value).copyUsingDescription(
                    nume_equa, True
                )
                _msginit("DEPL", resu.userName)

                if self.state.pb_type == PBT.MecaDyna:
                    self.state.current.dU = resu.getField(
                        "VITE", para=para, value=value
                    ).copyUsingDescription(nume_equa)
                    _msginit("VITE", resu.userName)

                    self.state.current.d2U = resu.getField(
                        "ACCE", para=para, value=value
                    ).copyUsingDescription(nume_equa)
                    _msginit("ACCE", resu.userName)

                self.state.stress = _extract_resu_field_and_check_model(
                    self,
                    resu=resu,
                    para=para,
                    val=value,
                    name_field="SIEF_ELGA",
                    model=model,
                    fieldModel=self.state.stress,
                )
                _msginit("SIEF_ELGA", resu.userName)

                self.state.internVar = _extract_resu_field_and_check_model(
                    self,
                    resu=resu,
                    para=para,
                    val=value,
                    name_field="VARI_ELGA",
                    model=model,
                    fieldModel=self.state.internVar,
                )
                _msginit("VARI_ELGA", resu.userName)

                list_of_loads = self.problem.getListOfLoads()
                if list_of_loads.hasDifferential():
                    nume_didi = init_state.get("NUME_DIDI")
                    if nume_didi:
                        displ = resu.getField("DEPL", nume_didi).copyUsingDescription(nume_equa)
                    else:
                        displ = self.state.U
                    list_of_loads.setDifferentialDisplacement(displ)

            if "EVOL_THER" in init_state:
                resu = init_state.get("EVOL_THER")
                assert isinstance(resu, ThermalResult), resu
                para, value = _extract_param(init_state, resu)

                self.state.U = resu.getField("TEMP", para=para, value=value).copyUsingDescription(
                    nume_equa
                )

            if "CHAM_NO" in init_state:
                self.state.U = init_state.get("CHAM_NO").copyUsingDescription(nume_equa)

            if "DEPL" in init_state:
                self.state.U = init_state.get("DEPL").copyUsingDescription(nume_equa, False)
                list_of_loads = self.problem.getListOfLoads()
                if list_of_loads.hasDifferential():
                    list_of_loads.setDifferentialDisplacement(self.state.U)
                _msginit("DEPL")

            if "SIGM" in init_state:
                self.state.stress = _get_field_and_check_model(
                    self,
                    state=init_state,
                    name_field="SIGM",
                    model=model,
                    fieldModel=self.state.stress,
                )
                _msginit("SIEF_ELGA")

            if "VARI" in init_state:
                self.state.internVar = _get_field_and_check_model(
                    self,
                    state=init_state,
                    name_field="VARI",
                    model=model,
                    fieldModel=self.state.internVar,
                )
                _msginit("VARI_ELGA")

            if "VITE" in init_state:
                self.state.current.dU = init_state.get("VITE").copyUsingDescription(nume_equa)
                _msginit("VITE")

            if "ACCE" in init_state:
                self.state.current.d2U = init_state.get("ACCE").copyUsingDescription(nume_equa)
                _msginit("ACCE")

            if "VALE" in init_state:
                if model.existsHHO():
                    self.state.U = HHO(self.problem).projectOnHHOSpace(init_state["VALE"])
                else:
                    self.state.U = self.state.createPrimal(
                        self.problem, value={"TEMP": init_state.get("VALE")}
                    )

        init_time = self.stepper.getInitial()
        self.computeExternalStateVariables(init_time)
        self.state.time_curr = init_time

        if init_state:
            if init_state.get("STAT") == "OUI":
                self.step_solver.initialize()
                args = {"valr": self.state.time_curr, "vali": self.stepper.splitting_level}
                logger.info(MessageLog.GetText("I", "MECANONLINE6_5", **args))
                self.step_solver.solve()
                if (
                    self.stepper.size() == 1
                    and self.stepper.getCurrent() == self.stepper.getPrevious()
                ):
                    self.stepper.completed()

            self.post_hooks()

        self.state.commit()

    def run(self):
        """Solve the problem.

        Returns:
            *misc*: result object.
        """
        try:
            self._setLoggingLevel(self.get_keyword("INFO", default=1))
            self.run_()
        finally:
            self._resetLoggingLevel()
            deleteTemporaryObjects()
        return self.result

    @profile
    def run_(self):
        """Solve the problem."""
        self.initialize()
        matr_update_step = self.get_keyword("NEWTON", "REAC_INCR", 1)

        # Solve nonlinear problem
        solv = self.step_solver
        state = self.state
        last_stored = False
        while not self.isFinished():
            state.time_curr = self.stepper.getCurrent()
            state.time_step = state.time_curr - state.time_prev
            if self.stepper.splitting_level <= 0:
                logger.info(MessageLog.GetText("I", "MECANONLINE6_7", valr=state.time_curr))
            else:
                args = dict(valr=state.time_curr, vali=self.stepper.splitting_level)
                logger.info(MessageLog.GetText("I", "MECANONLINE6_5", **args))

            self.computeExternalStateVariables(state.time_curr)
            solv.initialize()

            if matr_update_step == 0 or (self._step_idx + 1) % matr_update_step:
                solv.current_matrix = self.current_matrix
            else:
                solv.current_matrix = None

            if logger.getEffectiveLevel() <= DEBUG:
                state.debugPrint("<t-> ")
            state.stash()
            try:
                solv.solve()
            except (ConvergenceError, IntegrationError, SolverError) as exc:
                logger.warning(exc.format("I"))
                with storeLastIfFailed(self, state):
                    self.stepper.failed(exc)
            else:
                try:
                    isok = False
                    with storeLastIfFailed(self, state):
                        isok = self.stepper.check_event(state)
                except ConvergenceError as exc:
                    # exception for DELTA_GRANDEUR + ARCHIVAGE
                    if exc.id_message == "ADAPTATION_14":
                        isok = True
                    else:
                        raise
                if not isok:
                    # + reset current_matrix to None (REAC_INCR)
                    state.revert()
                    continue
                self.post_hooks()
                state.commit()
                self.stepper.completed()
                self.current_matrix = solv.current_matrix
                self._step_idx += 1
                last_stored = self._storeState(state)
                self.notifyObservers()
        # ensure that last step was stored
        if not last_stored:
            self._storeState(state, ignore_policy=True)
        table = state._observ.getTable()
        if table:
            self.result.setTable("OBSERVATION", table)

    def post_hooks(self):
        """Call post hooks"""
        for hook in self._hooks:
            hook(self)

    def get_state(self):
        """Returns nothing to observers."""

    def computeExternalStateVariables(self, current_time):
        """Compute and set external variables in the physical state.

        Arguments:
            current_time (float): Current time value.
        """
        if self.problem.getMaterialField().hasExternalStateVariable():
            self.state.externVar = self.problem.getExternalStateVariables(current_time)

    def _setLoggingLevel(self, level):
        """Set logging level.

        Arguments:
            level (int): verbosity level (meaning INFO keyword).
        """
        info = {0: WARNING, 1: INFO, 2: DEBUG, 3: DEBUG, 4: DEBUG}
        if level is None:
            level = 1
        setFortranLoggingLevel(level)
        logger.setLevel(info[level])
        # Disable printing of python command
        if level < 3:
            ExecutionParameter().disable(Options.ShowSyntax)

    def _resetLoggingLevel(self):
        """Reset logging level."""
        level, show = self._verb
        resetFortranLoggingLevel()
        logger.setLevel(level)
        if show:
            ExecutionParameter().enable(Options.ShowSyntax)


class storeLastIfFailed(AbstractContextManager):
    def __init__(self, solver, state):
        self._solver = solver
        self._state = state

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if isinstance(exc_val, (ConvergenceError, IntegrationError, SolverError)):
            # an error occurred, ensure that the previous step was stored
            logger.warning("An error occurred, ensure that the last converged step is saved")
            self._solver._storeState(self._state.getState(-1), ignore_policy=True)
            raise


def _msginit(field, result=None):
    if result:
        logger.info(MessageLog.GetText("I", "ETATINIT_32", valk=(field, result)))
    else:
        logger.info(MessageLog.GetText("I", "ETATINIT_33", valk=(field,)))


def _extract_param(init_state, resu):
    """Extract parameters for getField()."""
    extract_time = init_state.get("INST")
    if extract_time is None:
        extract_time = resu.getLastTime()
    if init_state.get("NUME_ORDRE"):
        para, value = "NUME_ORDRE", init_state["NUME_ORDRE"]
    else:
        para, value = "INST", extract_time
    return para, value


def _raise_elga_error(name_field):
    """Raise an error to make sure that initial_state model and
    field model are the same."""
    UTMESS("F", "MECANONLINE_9", sk=name_field)


def _extract_resu_field_and_check_model(self, resu, para, val, name_field, model, fieldModel):
    """Extract the field from the result, then check that the model
    of the field is the same as the model given in parameter.

    Returns:
        FieldOnCells: the extracted field if the model is the same
    """
    field = resu.getField(name_field, para=para, value=val)

    error = 0
    if name_field == "VARI_ELGA":
        comporPrev = resu.getField("COMPORTEMENT", para=para, value=val)
        comporCurr = self.problem.getBehaviourProperty().getBehaviourField()
        newFEDesc = self.problem.getModel().getFiniteElementDescriptor()
        field.checkInternalStateVariables(comporPrev, comporCurr, newFEDesc)
        error = field.compareShape(fieldModel, True, "PVARI_R")
    if error != 0:
        _raise_elga_error(name_field)

    error = 0
    if name_field == "SIEF_ELGA":
        error = field.compareShape(fieldModel, True, "PSIEF_R")

    if error != 0:
        _raise_elga_error(name_field)

    return field


def _get_field_and_check_model(self, state, name_field, model, fieldModel=None):
    """Extract the field from the initial state, then check that
    the model of the field is the same as the model given in parameter.
    If the field in a ConstantFieldOnCellsReal, it is converted in FieldOnCellsReal
    using fieldModel.

    Returns the field if the model is the same
    """
    field = state.get(name_field)
    error = 0

    if isinstance(field, ConstantFieldOnCellsReal):
        simpleFieldModel = fieldModel.toSimpleFieldOnCells()
        simpleField = field.toSimpleFieldOnCells(simpleFieldModel)
        field = simpleField.toFieldOnCells(model.getFiniteElementDescriptor(), "TOU_INI_ELGA", "")
    elif field.getLocalization() == "ELNO":
        field = field.asLocalization("ELGA")

    if name_field == "VARI":
        comporPrev = None
        comporCurr = self.problem.getBehaviourProperty().getBehaviourField()
        newFEDesc = self.problem.getModel().getFiniteElementDescriptor()
        field.checkInternalStateVariables(comporPrev, comporCurr, newFEDesc)
        error = field.compareShape(fieldModel, True, "PVARI_R")

    if error != 0:
        _raise_elga_error(name_field)

    error = 0
    if name_field == "SIGM":
        error = field.compareShape(fieldModel, True, "PSIEF_R")

    if error != 0:
        _raise_elga_error(name_field)

    return field
