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

from abc import ABC, abstractmethod
from functools import wraps
from typing import Any

from ...Objects import DiscreteComputation, FieldOnCellsReal, FieldOnNodesReal
from ...Utilities import no_new_attributes, profile
from .bases import Observer
from .bases import ProblemType as PBT


def _primalgetter(deriv):
    def decorator(dummy):
        @wraps(dummy)
        def wrapper(state):
            return (
                state._prim_prev[state._primal_names[deriv]]
                + state._prim_step[state._primal_names[deriv]]
            )

        return wrapper

    return decorator


def _primalsetter(deriv):
    def decorator(dummy):
        @wraps(dummy)
        def wrapper(state, value: Any):
            state._prim_step[state._primal_names[deriv]] = (
                value - state._prim_prev[state._primal_names[deriv]]
            )

        return wrapper

    return decorator


def get_all_subclasses(cls):
    """Return all subclasses of 'cls' recursively."""
    subclasses = set()
    for subclass in cls.__subclasses__():
        subclasses.add(subclass)
        subclasses.update(get_all_subclasses(subclass))

    return subclasses


class PhysicalState(Observer):
    """This object represents a Physical State of the model.

    Actually, it stores a stack of physical states and works as an *adapter*
    on the current state. Only the current state, the working one, has setters
    and so is writable. All other states on the stack are read-only.
    """

    class State(ABC):
        """Represents an elementary physical state (private).

        For the primal fields, one stores the field at the beginning of the step
        and its increment. They are accessed with U and eventually dU, d2U.
        The dual field is accessed with S (stress in mechanics) or
        Phi (heat flux in thermics) properties (value at t+dt).
        The other fields are accessed by name (value at t+dt).
        """

        _time_prev = _time_step = None
        _prim_prev = _prim_step = None
        _primal = _primal_names = _dual = None
        _data = None

        @classmethod
        def factory(cls, pb_type: PBT):
            """Create a new State object of ProblemType."""
            for kls in get_all_subclasses(cls):
                if kls.pb_type == pb_type:
                    return kls()
            raise TypeError(f"no candidate for cls={cls}, scheme: {pb_type!r}")

        def __init__(self):
            self._data = {}
            self._primal = self._primal_names[0]
            self._prim_prev = {f: None for f in self._primal_names}
            self._prim_step = {f: None for f in self._primal_names}
            self._time_prev = self._time_step = None

        @property
        def U(self):
            """U: Attribute that holds the primal unknown."""

        @U.setter
        @abstractmethod
        def U(self, value):
            pass

        def getFields(self):
            """Return the list of available fields."""
            return self._prim_prev.keys()

        @property
        def time_prev(self):
            """float: Previous time."""
            return self._time_prev

        @property
        def time_curr(self):
            """float: Current time."""
            return self._time_prev + self._time_step

        @property
        def time_step(self):
            """float: Time step."""
            return self._time_step

        @property
        def U_t(self):
            """FieldOnNodesReal: Primal field at previous time."""
            return self._prim_prev[self._primal]

        @U_t.setter
        def U_t(self, field):
            """Set previous primal field.

            Arguments:
                field (FieldOnNodesReal): primal
            """
            # assert isinstance(field, FieldOnNodesReal), f"unexpected type: {field}"
            self._prim_prev[self._primal] = field

        @property
        def deltaU(self):
            """FieldOnNodesReal: Primal increment."""
            return self._prim_step[self._primal]

        @deltaU.setter
        def deltaU(self, field):
            """Set the primal increment field.

            Arguments:
                field (FieldOnNodesReal): primal
            """
            # assert field is None or isinstance(field, FieldOnNodesReal), f"unexpected type: {field}"
            self._prim_step[self._primal] = field

        @property
        def fields_prev(self):
            """dict: Dictionary of previous fields."""
            return self._prim_prev

        @property
        def fields_step(self):
            """dict: Dictionary of fields steps."""
            return self._prim_step

        def get(self, key):
            """Return a field."""
            return self._data.get(key)

        def set(self, key, field):
            """Assign a field."""
            self._data[key] = field

        @property
        def dual(self):
            """FieldOnCellsReal: Dual field."""
            return self.get(self._dual)

        @dual.setter
        def dual(self, field: FieldOnCellsReal):
            """Set Stress field.

            Arguments:
                field (FieldOnCellsReal): Stress field
            """
            if field:
                assert isinstance(field, FieldOnCellsReal), f"unexpected type: {field}"
            self.set(self._dual, field)

        @property
        def internVar(self):
            """FieldOnCellsReal: Internal state variables."""
            return self.get("VARI_ELGA")

        @property
        def externVar(self):
            """FieldOnCellsReal: External state variables."""
            return self.get("VARI_EXTE")

        def copy(self, other):
            """Copy the content of an object into the current one.

            Arguments:
                other (PhysicalState.State): Object to be copied.

            Return:
                PhysicalState.State: Current object.
            """
            self._time_prev = other.time_prev
            self._time_step = other.time_step
            self._primal = other._primal
            self._primal_names = list(other._primal_names)
            for field in self.getFields():
                prev = other.fields_prev[field]
                self._prim_prev[field] = prev and prev.copy()
                step = other.fields_step[field]
                self._prim_step[field] = step and step.copy()
            for key, field in other._data.items():
                self._data[key] = field and field.copy()
            return self

        def duplicate(self):
            """Duplicate the physical state.

            Returns:
                PhysicalState.State: the new physical state.
            """
            return PhysicalState.State.factory(self.pb_type).copy(self)

        def swap(self, other):
            """Swap the content of an object with the current one.

            Arguments:
                other (PhysicalState.State): Object to be swaped.
            """
            self._time_prev, other._time_prev = other._time_prev, self._time_prev
            self._time_step, other._time_step = other._time_step, self._time_step
            self._primal, other._primal = other._primal, self._primal
            self._primal_names, other._primal_names = other._primal_names, self._primal_names
            for field in self.getFields():
                self._prim_prev[field], other._prim_prev[field] = (
                    other._prim_prev[field],
                    self._prim_prev[field],
                )
                self._prim_step[field], other._prim_step[field] = (
                    other._prim_step[field],
                    self._prim_step[field],
                )
            for key in set(self._data.keys()).union(other._data.keys()):
                self._data[key], other._data[key] = other._data.het(key), self._data.get(key)

        def asdict(self):
            """Returns the fields as a dict.

            Returns:
                dict: Dict of fields.
            """
            ret = {}
            for field_name in self.getFields():
                ret[field_name] = self.fields_prev[field_name]
            # add _data fields
            for key in self._data:
                if key == "VARI_EXTE":
                    # not yet supported in Result
                    continue
                ret[key] = self._data[key]
            return ret

        def debugPrint(self, label=""):
            """Print a representation of the object."""
            print(f"*** {label}Physical State at", self.time_curr, flush=True)
            values = self.U_t.getValues()
            print("* U_t ", sum(values) / len(values), flush=True)
            if self.deltaU:
                values = self.deltaU.getValues()
                print("* deltaU", sum(values) / len(values), flush=True)
            for key, field in self._data.items():
                if field:
                    values = field.getValues()
                    print(f"* {key:10s} ", sum(values) / len(values), flush=True)

    class StateMecaStat(State):
        pb_type = PBT.MecaStat
        _primal_names = ("DEPL",)
        _dual = "SIEF_ELGA"

        @property
        @_primalgetter(0)
        def U(self):
            """U: Attribute that holds the displacement field."""

        @U.setter
        @_primalsetter(0)
        def U(self, value):
            pass

    class StateMecaDyna(StateMecaStat):
        pb_type = PBT.MecaDyna
        _primal_names = ("DEPL", "VITE", "ACCE")

        @property
        @_primalgetter(1)
        def dU(self):
            """dU: Attribute that holds the derivative of displacement field."""

        @dU.setter
        @_primalsetter(1)
        def dU(self, value):
            pass

        @property
        @_primalgetter(2)
        def d2U(self):
            """U: Attribute that holds the second derivative of displacement field."""

        @d2U.setter
        @_primalsetter(2)
        def d2U(self, value):
            pass

    class StateThermal(StateMecaStat):
        pb_type = PBT.Thermal
        _primal_names = ("TEMP",)
        _dual = "FLUX_ELGA"

    _current = _stack = _size = _stash = _observ = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, pb_type, size=1):
        assert size > 0, f"invalid value ({size}) for 'size'"
        self._current = PhysicalState.State.factory(pb_type)
        self._stack = []
        self._size = size
        self._stash = None
        self._observ = None

    def copy(self, other):
        """Copy the content of an object into the current one.

        Arguments:
            other (PhysicalState): Object to be copied.

        Return:
            PhysicalState: Current object.
        """
        if other._stash:
            self._stash = other._stash.duplicate()
        self._current = other.current.duplicate()
        self._stack = [s.duplicate() for s in other._stack]
        self._size = other._size
        return self

    def duplicate(self):
        """Duplicate the physical state.

        Returns:
            PhysicalState: the new physical state.
        """
        return PhysicalState(self.pb_type).copy(self)

    def swap(self, other):
        """Swap the content of the physical state.

        Arguments:
            other (PhysicalState): the physical state to be swaped.
        """
        self._current, other._current = other._current, self._current
        self._stack, other._stack = other._stack, self._stack
        self._size, other._size = other._size, self._size
        self._stash, other._stash = other._stash, self._stash

    def getState(self, index=0):
        """Return a physical state by index (relative position).

        Arguments:
            index (int): 0 means the current one, -1 the previous one and so on.

        Returns:
            PhysicalState.State: physical state.
        """
        if index == 0:
            return self.current
        if index < -self._size or index > 0:
            raise IndexError(f"invalid value ({index}) for 'index': {-self._size} <= index <= 0")
        return self._stack[index]

    @property
    def pb_type(self):
        """ProblemType: The type of the physical problem"""
        return self._current.pb_type

    def setObservation(self, observation):
        """Register the Observation object."""
        self._observ = observation

    def notify(self, event):
        """Delegate to Observation object."""
        if not self._observ:
            return
        self._observ.notify(event)

    @property
    def current(self):
        """PhysicalState.State: The current physical state, the working one."""
        return self._current

    @property
    def time_prev(self):
        """float: Previous time."""
        return self.current.time_prev

    @time_prev.setter
    def time_prev(self, value):
        """Set previous time.

        Arguments:
            value (float): previous time
        """
        self.current._time_prev = value

    @property
    def time_curr(self):
        """float: Current time."""
        return self.current.time_curr

    @time_curr.setter
    def time_curr(self, value):
        """Set current time.

        Arguments:
            value (float): current time
        """
        self.current._time_step = value - self.current.time_prev

    @property
    def time_step(self):
        """float: Time step."""
        return self.current.time_step

    @time_step.setter
    def time_step(self, value):
        """Set time step.

        Arguments:
            value (float): time step
        """
        self.current._time_step = value

    @property
    def U_t(self):
        """FieldOnNodesReal: Primal field at previous time."""
        return self.current.U_t

    @U_t.setter
    def U_t(self, field):
        """Set previous primal field.

        Arguments:
           field (FieldOnNodesReal): primal
        """
        self.current.U_t = field

    @property
    def U(self):
        """FieldOnNodesReal: Primal field at current time."""
        return self.current.U

    @U.setter
    def U(self, field):
        """Set current primal field.

        Arguments:
           field (FieldOnNodesReal): primal
        """
        self.current.U = field

    @property
    def deltaU(self):
        """FieldOnNodesReal: Primal increment."""
        return self.current.deltaU

    @deltaU.setter
    def deltaU(self, field):
        """Set primal increment.

        Arguments:
            field (FieldOnNodesReal): Primal increment
        """
        self.current.deltaU = field

    @property
    def dual(self):
        """FieldOnCellsReal: Dual field."""
        return self.current.dual

    @dual.setter
    def dual(self, field: FieldOnCellsReal):
        """Set the dual field.

        Arguments:
            field (FieldOnCellsReal): Dual field
        """
        self.current.dual = field

    stress = phi = dual

    @property
    def internVar(self):
        """FieldOnCellsReal: Internal state variables."""
        return self.current.internVar

    @internVar.setter
    def internVar(self, field):
        """Set Internal state variables.

        Arguments:
            field (FieldOnCellsReal): Internal state variables
        """
        if field:
            assert isinstance(field, FieldOnCellsReal), f"unexpected type: {field}"
        self.current.set("VARI_ELGA", field)

    @property
    def externVar(self):
        """FieldOnCellsReal: External state variables."""
        return self.current.externVar

    @externVar.setter
    def externVar(self, field):
        """Set external state variables.

        Arguments:
            field (FieldOnCellsReal): external state variables
        """
        assert field is None or isinstance(field, FieldOnCellsReal), f"unexpected type: {field}"
        self.current.set("VARI_EXTE", field)

    def get(self, key):
        """FieldOnCellsReal: The field stored at this key."""
        return self.current.get(key)

    def set(self, key, field):
        """Assign a field at the given key.

        Arguments:
            field (FieldOnCellsReal): Field
        """
        self.current._data[key] = field

    def stash(self):
        """Stores the object state to provide transactionality semantics."""
        self._stash = PhysicalState.State.factory(self.pb_type).copy(self.current)

    def revert(self):
        """Revert the object to its previous state."""
        assert self._stash, "stash is empty!"
        self.current.copy(self._stash)
        self._stash = None

    @profile
    def commit(self):
        """Commits the current changes and add the state on the stack."""
        # do not use '+=' to create a new object (and not modify previous values)
        current = self.current

        for field in current.getFields():
            if current.fields_step[field]:
                current.fields_prev[field] += current.fields_step[field]
                current.fields_step[field].setValues(0.0)

        current._time_prev += current._time_step
        current._time_step = 0.0

        self._stash = None

        if len(self._stack) >= self._size:
            self._stack.pop(0)
        self._stack.append(current)

        self._current = PhysicalState.State.factory(self.pb_type).copy(current)

    @profile
    def getCurrentDelta(self):
        """Return the delta for the current state between it has been stashed.

        Returns:
            dict: Delta between states as returned by py:method:`asdict`.
        """
        return self._states_difference(self._stash, self.current)

    @profile
    def getDeltaBetweenStates(self, index1, index2):
        """Return the delta between two states.

        The states are extracted using `getState(index)`.
        It returns the difference `getState(index2) - getState(index1)`.

        Arguments:
            index1 (int): Index of the first state.
            index2 (int): Index of the second state.

        Returns:
            dict: Delta between states as returned by py:method:`asdict`.
        """
        return self._states_difference(self.getState(index1), self.getState(index2))

    @staticmethod
    def _states_difference(one, two):
        """Delta between states as returned by py:method:`asdict`."""
        ret = {}

        for field in one.getFields():
            first_field = one.fields_prev[field] + one._prim_step[field]
            second_field = two.fields_prev[field] + two._prim_step[field]
            ret[field] = second_field - first_field
        for key in set(one._data.keys()).intersection(two._data.keys()):
            if one._data[key] and two._data[key]:
                ret[key] = two._data[key] - one._data[key]
        return ret

    # FIXME setPrimalValue?
    @staticmethod
    @profile
    def createPrimal(phys_pb, value=0.0):
        """Create primal field with a given value

        Arguments:
            phys_pb (PhysicalProblem): Physical problem
            value (Union[float, dict]): value to set everywhere

        Returns:
            FieldOnNodes: primal field with a given value (DEPL|TEMP)
        """
        field = FieldOnNodesReal(phys_pb.getDOFNumbering())
        field.setValues(value)
        return field

    @staticmethod
    @profile
    def createFieldOnCells(phys_pb, localization, quantity, value=0.0):
        """Create a field with a given value

        Arguments:
            phys_pb (PhysicalProblem): Physical problem
            localization (str): localization of the field to create (ELNO, ELEM, ELGA)
            quantity (str): type of the field to create (ex: SIEF_R, ...)
            value (float): value to set everywhere

        Returns:
            FieldOnCells: field with a given value of type "type"
        """
        assert phys_pb.getBehaviourProperty(), "unexpected empty BehaviourProperty"
        field = FieldOnCellsReal(
            phys_pb.getModel(),
            localization,
            quantity,
            phys_pb.getBehaviourProperty(),
            phys_pb.getElementaryCharacteristics(),
        )
        field.setValues(value)
        return field

    @staticmethod
    @profile
    def createDual(phys_pb, value):
        """Create the dual field with a given value

        Arguments:
            phys_pb (PhysicalProblem): Physical problem
            value (float): value to set everywhere

        Returns:
            FieldOnCells: Stress field with a given value (SIEF_ELGA/FLUX_ELGA)
        """
        if phys_pb.isMechanical():
            type_field = "SIEF_R"
        else:
            type_field = "FLUX_R"

        return PhysicalState.createFieldOnCells(phys_pb, "ELGA", type_field, value)

    @staticmethod
    @profile
    def createInternalVariablesNext(phys_pb, value):
        """Create internal state variables field with a given value

        Arguments:
            phys_pb (PhysicalProblem): Physical problem
            value (float): value to set everywhere

        Returns:
            FieldOnCells: internal state variables field with a given value (VARI_ELGA)
        """
        return PhysicalState.createFieldOnCells(phys_pb, "ELGA", "VARI_R", value)

    @staticmethod
    @profile
    def createTimeField(phys_pb, value):
        """Create time field with a given value

        Arguments:
            phys_pb (PhysicalProblem): Physical problem
            value (float): value to set everywhere

        Returns:
            ConstantFieldOnCellsReal: time field with a given value
        """
        disc_comp = DiscreteComputation(phys_pb)
        return disc_comp.createTimeField(value)

    @profile
    def zeroInitialState(self, phys_pb):
        """Initialize with zero initial state

        Arguments:
            phys_pb (PhysicalProblem): Physical problem
        """
        self.time_prev = 0.0
        self.time_step = 0.0

        current = self.current
        current._data = {}

        for field in current.getFields():
            current.fields_prev[field] = self.createPrimal(phys_pb, 0.0)
            current.fields_step[field] = self.createPrimal(phys_pb, 0.0)

        if phys_pb.getBehaviourProperty():
            self.dual = self.createDual(phys_pb, 0.0)
            if phys_pb.isMechanical():
                self.internVar = self.createInternalVariablesNext(phys_pb, 0.0)
                self.externVar = None

    def asdict(self):
        """Returns the fields as a dict.

        Returns:
            dict: Dict of fields.
        """
        return self.current.asdict()

    def debugPrint(self, label="", recursive=False):
        """Print a representation of the object."""
        print(
            f"*** {label}Stack contains states for t =",
            [state.time_prev for state in self._stack],
            f"+ current (t = {self.current.time_curr})",
            flush=True,
        )
        if recursive:
            for state in self._stack:
                state.debugPrint(label)
            self.current.debugPrint(label)
