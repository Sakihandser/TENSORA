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
Base objects used to solve generic non linear problems.
"""

from functools import wraps

from ...Cata.Language.SyntaxObjects import _F
from ...Utilities import logger, no_new_attributes
from .bases import ProblemType as PBT


class Context:
    """Object that stores the objects required by a :py:class:`NonLinearOperator`.

    It only stores objects that are shared at different levels of the algorithm.
    Objects only used by one stage/object should be created there.
    If different objects should be created at each timestep for example, they
    should not be here.

    Attributes:
        problem: :py:class:`PhysicalProblem` object
        state: :py:class:`PhysicalState` object
        result: :py:class:`Result` object (:py:class:`NonLinearResult`,
            :py:class:`ThermalResult` , :py:class:`DryingResult`)
        problem_type: :py:class:`ProblemType` enum value
        keywords: Part of the user keywords
        oper: :py:class:`BaseOperators` object
        stepper: :py:class:`TimeStepper` object
        contact: :py:class:`ContactManager` object
        linear_solver: :py:class:`LinearSolver` object
    """

    # FIXME: with TimeScheme.Multiple? several '.oper'? one '.oper' per StepSolver?
    # FIXME: Creating all objects in ops should allow overloading
    # FIXME: and to known syntax in one place (for instance: RECH_LINEAIRE in NewtonSolver)

    class KeywordsStore:
        """Container that stores and gives access to some user keywords."""

        _dict_kwds = None
        __setattr__ = no_new_attributes(object.__setattr__)

        def __init__(self, keywords):
            self._dict_kwds = keywords

        def __getitem__(self, keyword):
            """Return a keyword value.

            Args:
                keyword (str): Simple keyword.

            Returns:
                *misc*: Keyword value.
            """
            return self._dict_kwds[keyword]

        def get(self, keyword, parameter=None, default=None):
            """Return a keyword value.

            Args:
                keyword (str): Simple or factor keyword.
                parameter (str|None): Simple keyword under the factor keyword, or *None*.
                default (*misc*): Default value if the keyword is undefined.

            Returns:
                *misc*: Keyword value.
            """
            kwds = self._dict_kwds
            if parameter is not None:
                if kwds.get(keyword) is None:
                    return default
                return _F(kwds[keyword])[0].get(parameter, default)

            return kwds.get(keyword, default)

    _problem = _type = _state = _keywords = _result = None
    _stepper = _oper = _contact = _linsolv = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self):
        self._type = None
        self._keywords = Context.KeywordsStore({})
        self._problem = None
        self._state = None
        self._result = None
        self._stepper = None
        self._oper = None
        self._contact = None
        self._linsolv = None

    def check(self):
        """Check for required/optional attributes."""
        for attr in ("problem_type", "problem", "state", "result", "oper", "keywords"):
            if not getattr(self, attr):
                logger.error(f"{attr!r} attribute is required")
        for attr in ("stepper", "linear_solver"):
            if not getattr(self, attr):
                logger.warning(f"{attr!r} is not yet defined")

    @property
    def problem_type(self):
        """ProblemType: Attribute that holds the type of problem."""
        return self._type

    @problem_type.setter
    def problem_type(self, value):
        assert self._type is None, "must be set only once!"
        self._type = value

    @property
    def keywords(self):
        """Dict: Attribute that holds the keywords object."""
        return self._keywords

    @keywords.setter
    def keywords(self, value_dict):
        assert isinstance(value_dict, dict), f"unsupported type: {type(value_dict)}"
        self._keywords = Context.KeywordsStore(value_dict)

    def get_keyword(self, keyword, parameter=None, default=None):
        """ "Return a keyword value.

        Args:
            keyword (str): Simple or factor keyword.
            parameter (str|None): Simple keyword under the factor keyword, or *None*.
            default (*misc*): Default value if the keyword is undefined.

        Returns:
            *misc*: Keyword value.
        """
        return self._keywords.get(keyword, parameter, default)

    @property
    def problem(self):
        """PhysicalProblem: current problem description."""
        return self._problem

    @problem.setter
    def problem(self, problem):
        assert self._problem is None, "must be set only once!"
        self._problem = problem

    @property
    def state(self):
        """PhysicalState: current state."""
        return self._state

    @state.setter
    def state(self, state):
        assert self._state is None, "must be set only once!"
        self._state = state

    @property
    def result(self):
        """Result: Attribute that holds the result object."""
        return self._result

    @result.setter
    def result(self, value):
        self._result = value

    @property
    def stepper(self):
        """TimeStepper: Attribute that holds the time stepper."""
        return self._stepper

    @stepper.setter
    def stepper(self, value):
        self._stepper = value

    @property
    def oper(self):
        """Operators: Object that adapts operators for each type of problem."""
        return self._oper

    @oper.setter
    def oper(self, value):
        self._oper = value

    @property
    def contact(self):
        """ContactManager: Object to solve contact conditions"""
        return self._contact

    @contact.setter
    def contact(self, value):
        self._contact = value

    @property
    def linear_solver(self):
        """LinearSolver: Attribute that holds the linear solver."""
        return self._linsolv

    @linear_solver.setter
    def linear_solver(self, value):
        self._linsolv = value


def check_access(alt=None):
    """Decorator to wrap TestCase methods by calling writeResult"""

    def decorator(method):
        @wraps(method)
        def wrapper(inst, *args, **kwds):
            """wrapper"""
            required = alt or method.__name__
            if required != "context" and required not in inst.__needs__:
                raise AttributeError(f"undeclared access to {required!r}")
                # logger.warning(f"undeclared access from {inst.__class__.__name__} to {required}")
            return method(inst, *args, **kwds)

        return wrapper

    return decorator


class ContextMixin:
    """Mixin object that wraps access to the objects of Context.

    Attributes:
        problem: :py:class:`PhysicalProblem` object
        state: :py:class:`PhysicalState` object
        result: :py:class:`Result` object (:py:class:`NonLinearResult`,
            :py:class:`ThermalResult`, :py:class:`DryingResult`)
        problem_type: :py:class:`ProblemType` enum value
        keywords: Part of the user keywords
        oper: :py:class:`BaseOperators` object
        contact: :py:class:`ContactManager` object
        linear_solver: :py:class:`LinearSolver` object
    """

    # each class must declared what attributes it needs to access
    __needs__ = ()
    _ctxt = None
    __setattr__ = no_new_attributes(object.__setattr__)

    @classmethod
    def builder(cls, context):
        """Default builder for :py:class:`ContextMixin` object.
        Should be subclassed for non trivial constructor.

        Args:
            context (Context): Context of the problem.

        Returns:
            instance: New object.
        """
        instance = cls()
        instance.context = context
        return instance

    def __init__(self):
        super().__init__()
        self._ctxt = Context()

    @property
    @check_access()
    def context(self):
        """Data: Context attached to the object."""
        return self._ctxt

    @context.setter
    @check_access()
    def context(self, other):
        assert isinstance(other, Context)
        self._ctxt = other

    # convenient shortcuts properties
    @property
    @check_access()
    def problem_type(self):
        """ProblemType: Attribute that holds the type of problem."""
        return self._ctxt.problem_type

    @problem_type.setter
    @check_access()
    def problem_type(self, value):
        self._ctxt.problem_type = value

    @property
    @check_access()
    def keywords(self):
        """Dict: Attribute that holds the keywords object."""
        return self._ctxt.keywords

    @keywords.setter
    @check_access()
    def keywords(self, value_dict):
        self._ctxt.keywords = value_dict

    @check_access(alt="keywords")
    def get_keyword(self, keyword, parameter=None, default=None):
        """ "Return a keyword value.

        Args:
            keyword (str): Simple or factor keyword.
            parameter (str|None): Simple keyword under the factor keyword, or *None*.
            default (*misc*): Default value if the keyword is undefined.

        Returns:
            *misc*: Keyword value.
        """
        return self._ctxt.get_keyword(keyword, parameter, default)

    @property
    @check_access()
    def problem(self):
        """PhysicalProblem: current problem description."""
        return self._ctxt.problem

    @problem.setter
    @check_access()
    def problem(self, value):
        self._ctxt.problem = value

    @property
    @check_access()
    def state(self):
        """PhysicalState: current state."""
        return self._ctxt.state

    @state.setter
    @check_access()
    def state(self, value):
        self._ctxt.state = value

    @property
    @check_access()
    def result(self):
        """Result: Attribute that holds the result object."""
        return self._ctxt.result

    @result.setter
    @check_access()
    def result(self, value):
        self._ctxt.result = value

    @property
    @check_access()
    def stepper(self):
        """TimeStepper: Attribute that holds the time stepper."""
        return self._ctxt.stepper

    @stepper.setter
    @check_access()
    def stepper(self, value):
        self._ctxt.stepper = value

    @property
    @check_access()
    def oper(self):
        """Operators: Object that adapts operators for each type of problem."""
        return self._ctxt.oper

    @oper.setter
    @check_access()
    def oper(self, value):
        self._ctxt.oper = value

    @property
    @check_access()
    def contact(self):
        """ContactManager: Object to solve contact conditions"""
        return self._ctxt.contact

    @contact.setter
    @check_access()
    def contact(self, value):
        self._ctxt.contact = value

    @property
    @check_access()
    def linear_solver(self):
        """LinearSolver: Attribute that holds the linear solver."""
        return self._ctxt.linear_solver

    @linear_solver.setter
    @check_access()
    def linear_solver(self, value):
        self._ctxt.linear_solver = value
