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
All Commands executors are subclasses of :class:`.ExecuteCommand`.
Commands are factories (:meth:`ExecuteCommand.run` *classmethod*) that
create an executor that is called to create a result object.

When a new command is added there are different levels of complexity:

- Commands that are automatically added just using their catalog.
  Only the commands that return no result can work with this method.
  Other commands will raise a *NotImplementedError* exception at runtime.
  Macro-commands do not need a specific executor. Their catalog and ``ops()``
  function are sufficient.

  .. note:: All Commands that are not explicitly imported by
    :mod:`code_aster.Commands.__init__` are automatically created using this
    method.

- Commands where the Fortran operator is directly called. Usually it is just
  necessary to define the type of result object.
  Example: :mod:`~code_aster.Commands.defi_compor`.

- Commands where keywords are used to create the output result.
  Example: :mod:`~code_aster.Commands.defi_group`.

- Commands where several steps must be adapted. Usually, the operator directly
  calls C++ Objects to do the job.


For all features that are not yet supported, please use utilities from
the :mod:`code_aster.Utilities` functions (example:
:func:`~code_aster.Utilities.compatibility.unsupported` or
:func:`~code_aster.Utilities.compatibility.required`) to identify them.


Base classes
============
"""

# For SDVERI:
# aslint: disable=C4014

import gc
import inspect
import linecache
import re
import sys
import time
import traceback
from contextlib import contextmanager

import aster_core
import libaster

from ..Cata import Commands
from ..Cata.Language.SyntaxObjects import _F
from ..Cata.SyntaxChecker import CheckerError, checkCommandSyntax
from ..Cata.SyntaxUtils import force_list, mixedcopy, remove_none, search_for
from ..Messages import UTMESS, MessageLog
from ..Objects import DataStructure, DataStructureDict, NamedTuple, PyDataStructure
from ..Utilities import (
    DEBUG,
    ExecutionParameter,
    Options,
    config,
    deprecated,
    haveMPI,
    import_object,
    logger,
    no_new_attributes,
)
from ..Utilities.outputs import command_text, decorate_name
from .code_file import Tracking
from .CommandSyntax import CommandSyntax
from .ctopy import check_ds_object
from .Serializer import FinalizeOptions, saveObjectsFromContext


@contextmanager
def command_execution():
    """Context manager used to simulate the execution of a legacy Fortran operator."""
    libaster.cmd_ctxt_enter()
    yield
    if libaster.jeveux_status():
        libaster.cmd_ctxt_exit()


class ExecuteCommand:
    """This class implements an executor of commands.

    Commands executors are defined by subclassing this class and overloading
    some of the methods. A user's Command is a factory of these classes.

    The :meth:`run` factory creates an instance of one of these classes and
    executes successively these steps:

        - :meth:`compat_syntax_` to eventually change the user's keywords to
          adapt the syntax from an older version **before** syntax checking.
          Subclasses **must not overload** this method.
          The compatibility changes must be defined in ``compat_syntax``
          attribute in the catalog.
          Subclasses may define a :meth:`change_syntax` method for modifications
          on non-keywords arguments. This should be limited to very specific
          cases.

        - :meth:`check_syntax` to check the user's keywords conformance to
          to catalog definition.

        - :meth:`adapt_syntax` to eventually change the user's keywords to
          adapt the syntax **after** syntax checking. Does nothing by default.

        - :meth:`create_result` to create the *DataStructure* object.
          The default implementation only works if the operator creates no
          object.

        - :meth:`exec_` that is the main function of the Command.
          The default implementation calls the *legacy* Fortran operator.

        - :meth:`post_exec` that allows to execute additional code after
          the main function. Does nothing by default.

    If a :attr:`libaster.AsterError` exception (or a derivated) is raised
    during :meth:`exec_` the behaviour depends on the execution mode.

    - In a standard study, the results are saved and the execution is
      interrupted. The current result is available if it is validated by the
      command and the study can be restarted.

    - In the testcase mode (option ``--test`` used, see
      :class:`~code_aster.Utilities.ExecutionParameter.ExecutionParameter` or
      ``CODE`` in :func:`DEBUT`/:func:`POURSUITE`), the exception is raised
      and can be catched in the commands file. The current result will be
      available in the ``except`` statement if it is validated by the command.
    """

    # class attributes
    command_name = command_op = command_cata = None
    level = 0
    hook = []

    _cata = _op = _result = _counter = _caller = _exc = None
    _tuplmode = None
    _gc_threshold = None

    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self):
        """Initialization"""
        assert self.command_name, "'command_name' attribute is not defined!"
        self._cata = self.command_cata or getattr(Commands, self.command_name)
        self._op = self.command_op or self._cata.definition["op"]
        self._result = None
        # index of the command
        self._counter = 0
        current_opt = ExecutionParameter().option
        self._tuplmode = current_opt & Options.UseLegacyMode == 0

    @classmethod
    def run(cls, **kwargs):
        """Run the command (class method).

        Arguments:
            keywords (dict): User keywords
        """
        cmd = cls()
        return cmd.run_(**kwargs)

    def run_(self, **kwargs):
        """Run the command (worker).

        Arguments:
            keywords (dict): User keywords
        """
        self._tuplmode = kwargs.pop("__use_namedtuple__", self._tuplmode)
        keywords = mixedcopy(kwargs)
        self.keep_caller_infos(keywords)
        timer = ExecutionParameter().timer
        if self.command_name not in ("DEBUT", "POURSUITE", "FIN"):
            check_jeveux()

        ExecuteCommand.level += 1
        MessageLog.reset_command()
        self._counter = ExecutionParameter().incr_command_counter()
        if self.show_syntax() or self.command_name in ("DEBUT", "POURSUITE"):
            timer.Start(str(self._counter), name=self.command_name)
        timer.Start(" . check syntax", num=1.1e6)
        self.compat_syntax_(keywords)
        try:
            self.check_syntax(keywords)
        finally:
            timer.Stop(" . check syntax")
        self.adapt_syntax(keywords)
        if ExecutionParameter().option & Options.TestMode:
            Tracking.add("KWDS", self._cata, self.command_name, keywords)
        self.create_result_(keywords)
        if not getattr(self._result, "userName", "n/a"):
            # attribute does exist but is not defined
            self._result.userName = get_user_name(
                self.command_name, self._caller["filename"], self._caller["lineno"]
            )

        self.print_syntax(keywords)
        with ExceptHookManager.wraps(self):
            try:
                if self._op is None and self.command_name not in ("DEBUT", "POURSUITE"):
                    # for commands that do not call any operator, do initializations
                    libaster.call_oper_init()
                with command_execution():
                    self.exec_(keywords)
            except libaster.AsterError as exc:
                self._exc = exc
                self.publish_result()
                raise
            finally:
                self.post_exec_(keywords)
                ExecuteCommand.level -= 1
        return self._result

    def publish_result(self):
        """Publish the result in the caller context."""
        if not hasattr(self._result, "userName"):
            return
        publish_in(self.caller_context, {self._result.userName: self._result})

    @property
    def caller_context(self):
        """dict: The context from which the command has be called."""
        return self._caller["context"]

    @property
    def exception(self):
        """*AsterError*: Exception raised during the execution, *None* if the
        execution was successful.
        """
        return self._exc

    @staticmethod
    def register_hook(func):
        """Register a hook for *post_exec* step.

        Arguments:
            func (function): Function with signature: *ExecuteCommand*, *dict*
                of keywords.
        """
        ExecuteCommand.hook.append(func)

    @classmethod
    def show_syntax(cls):
        """Tell if the current command syntax should be printed.

        Returns:
            bool: *True* if the syntax should be printed.
        """
        opt = ExecutionParameter().option
        return opt & Options.ShowSyntax and (
            ExecuteCommand.level <= 1 or opt & Options.ShowChildCmd
        )

    def _call_oper(self, syntax):
        """Call fortran operator.

        Arguments:
            syntax (*CommandSyntax*): Syntax description with user keywords.
        """
        return libaster.call_oper(syntax, 0)

    @property
    def name(self):
        """Returns the command name."""
        return self._cata.name

    def _add_deps_keywords(self, toVisit):
        name = self._result.getName()
        if type(toVisit) in (list, tuple):
            for value in toVisit:
                if isinstance(value, DataStructure):
                    if name != value.getName():
                        self._result.addDependency(value)
                else:
                    self._add_deps_keywords(value)
        elif type(toVisit) in (dict, _F):
            for value in toVisit.values():
                self._add_deps_keywords(value)
        elif isinstance(toVisit, DataStructure):
            if name != toVisit.getName():
                self._result.addDependency(toVisit)

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        The default implementation registers all input objects as dependencies.

        Arguments:
            keywords (dict): User's keywords.
        """
        self._add_deps_keywords(keywords)

    def remove_dependencies(self, keywords, key1, key2=None):
        """Remove dependencies to the input *DataStructure* objects passed
        with given keywords.

        Arguments:
            keywords (dict): User's keywords.
            key1 (str/list[str]): One or more simple keywords, or factor keyword.
            key2 (str/list[str]): One or more simple keywords if `key1` is a
                factor keyword.
        """
        if not key2:
            key1 = force_list(key1)
            for key in key1:
                value = keywords.get(key)
                if not value:
                    continue
                for obj in force_list(value):
                    self._result.removeDependency(obj)
        else:
            assert type(key1) is str, key1
            fact = keywords.get(key1)
            if not fact:
                return
            key2 = force_list(key2)
            for occ in force_list(fact):
                for key in key2:
                    value = occ.get(key)
                    if not value:
                        continue
                    for obj in force_list(value):
                        self._result.removeDependency(obj)

    def compat_syntax_(self, keywords):
        """Call the compatibility function defined in catalog.

        As the keywords have not been checked, no assumptions can be done about
        the presence or the number of values for example.
        If the syntax is already valid, call :meth:`adapt_syntax` instead.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """
        try:
            self._cata.get_compat_syntax()(keywords)
        except (AssertionError, KeyError, TypeError, ValueError, AttributeError) as exc:
            # in case of syntax error, show the syntax and raise the exception
            self.print_syntax(keywords)
            ExecuteCommand.level -= 1
            msg = getattr(exc, "msg", str(exc))
            if ExecutionParameter().option & Options.Debug:
                logger.error(msg)
                raise
            UTMESS("F", "DVP_10", valk=("compat_syntax", self.command_name, msg))
        self.change_syntax(keywords)

    def change_syntax(self, keywords):
        """Hook to change keywords before checking syntax.

        You must define `compat_syntax` in the command catalog to adapt the
        syntax from an old version or for compatibility.
        `compat_syntax` is also used by AsterStudy, `change_syntax` is only
        called during execution and limited to very specific cases.

        If the syntax is already valid, call :meth:`adapt_syntax` instead.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """

    def adapt_syntax(self, keywords):
        """Hook to adapt syntax *after* syntax checking.

        As the syntax is valid, changes are easier: existence, number of values
        verify syntax description.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """

    def print_syntax(self, keywords):
        """Print an echo of the Command.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        if not self.show_syntax():
            return
        printed_args = mixedcopy(keywords)
        remove_none(printed_args)
        filename = self._caller["filename"]
        lineno = self._caller["lineno"]

        logger.info(
            "\n.. _stg{0}_{1}".format(
                ExecutionParameter().get_option("stage_number"), self._caller["identifier"]
            )
        )
        logger.info(command_separator())
        logger.info(command_header(self._counter, filename, lineno))
        max_print = ExecutionParameter().get_option("max_print")
        user_name = get_user_name(self.command_name, filename, lineno, strict=False)
        logger.info(command_text(self.name, printed_args, user_name, limit=max_print))

    def print_result(self):
        """Print an echo of the result of the command."""
        if not self.show_syntax():
            return
        if self._result is not None:
            logger.info(command_result(self._counter, self.name, self._result))
            if hasattr(self._result, "getDependencies"):
                deps = self._result.getDependencies()
                if deps:
                    logger.info(MessageLog.GetText("I", "SUPERVIS2_80"))
                for dep in deps:
                    logger.info("# - {0} {1}".format(*_get_object_repr(dep)))
        self._print_stats()

    def _print_stats(self):
        """Print the memory and timer informations."""
        # not called if not show_syntax()
        timer = ExecutionParameter().timer
        times = timer.StopAndGet(str(self._counter))
        if ExecutionParameter().option & Options.TestMode:
            Tracking.add("PERF", self.name, *times)
        logger.info(command_memory(self.name))
        logger.info(command_time(self._counter, *times))
        logger.info(command_separator())

    def check_syntax(self, keywords):
        """Check the syntax passed to the command. *keywords* will contain
        default keywords after executing this method.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """
        try:
            self._cata.addDefaultKeywords(keywords)
            remove_none(keywords)
            logger.debug("checking syntax of %s...", self.name)
            max_check = ExecutionParameter().get_option("max_check")
            checkCommandSyntax(self._cata, keywords, add_default=False, max_check=max_check)
        except (
            CheckerError,
            AssertionError,
            KeyError,
            TypeError,
            ValueError,
            AttributeError,
        ) as exc:
            # in case of syntax error, show the syntax and raise the exception
            self.print_syntax(keywords)
            ExecuteCommand.level -= 1
            msg = getattr(exc, "msg", str(exc))
            if ExecutionParameter().option & Options.Debug:
                logger.error(msg)
                raise
            UTMESS("F", "SUPERVIS_4", valk=(self.command_name, msg))

    def create_result_(self, keywords):
        """Wrapper on `create_result` to be adapt by commands."""
        # change gc threshold to avoid created object to go to generation 2
        if ExecuteCommand.level == 1:
            ExecuteCommand._gc_threshold = gc.get_threshold()[:2]
            gc.set_threshold(self._gc_threshold[0], 1000000000)
        self.create_result(keywords)

    def create_result(self, keywords):
        """Create the result before calling the *exec* command function
        if needed.
        The result is stored in an internal attribute and will be built by
        *exec_*.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        sd_type = self._cata.get_type_sd_prod(**keywords)
        if sd_type is None:
            self._result = None
        else:
            raise NotImplementedError(
                "Method 'create_result' must be overridden for {0!r}.".format(self.name)
            )

    @property
    def result(self):
        """misc: Attribute that holds the result of the Command."""
        return self._result

    def exec_(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        syntax = CommandSyntax(self.name, self._cata)
        syntax.define(keywords, add_default=False)
        # set result and type names
        if self._result is None or type(self._result) is int:
            type_name = ""
            result_name = ""
        else:
            type_name = self._result.getType()
            result_name = self._result.getName()
        syntax.setResult(result_name, type_name)

        timer = ExecutionParameter().timer
        try:
            timer.Start(" . fortran", num=1.2e6)
            self._call_oper(syntax)
        finally:
            timer.Stop(" . fortran")
            syntax.free()
        # for special fortran operator that returns a int/float
        if syntax.getResultValue() is not None:
            self._result = syntax.getResultValue()

    def post_exec_(self, keywords):
        """Post-treatments executed after the `exec_` function. Commands may
        override `post_exec` method to add specific actions.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        try:
            self.post_exec(keywords)
            if isinstance(self._result, DataStructure):
                self.add_dependencies(keywords)
            if not self._exc and ExecutionParameter().get_option("sdveri"):
                self.check_ds()
            for func in self.hook:
                func(self, keywords)
        finally:
            self.cleanup()
            self.print_result()

    def post_exec(self, keywords):
        """Hook that allows to add post-treatments after the *exec* function.

        .. note:: If the Command executes the *op* fortran subroutine and if
            the result DataStructure references any inputs in a Jeveux object,
            pointers on these inputs must be explicitly references into
            the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """

    def cleanup(self):
        """Clean-up function."""
        # restore gc threshold
        if ExecuteCommand.level == 1:
            gc.set_threshold(self._gc_threshold[0], self._gc_threshold[1])

    def check_ds(self):
        """Check a result created by the command.

        Arguments:
            result (*DataStructure*): Object to be checked.
        """
        if not self.show_syntax():
            return
        self.check_ds_result(self._result)

    @staticmethod
    def check_ds_result(result):
        """Check a *DataStructure* object.

        Arguments:
            result (*DataStructure*): Object to be checked.
        """
        if not isinstance(result, DataStructure):
            return
        timer = ExecutionParameter().timer
        timer.Start(" . sdveri", num=1.3e6)
        try:
            iret = check_ds_object(result.sdj)
            if iret != 0:
                if logger.getEffectiveLevel() == DEBUG:
                    result.debugPrint()
                logger.error(
                    "SDVERI ended with exit code {0} for {1!r} ({2!r}, {3!r})".format(
                        iret, result.getName(), result.getType(), result.sdj.__class__.__name__
                    )
                )
        finally:
            timer.Stop(" . sdveri")

    def keep_caller_infos(self, keywords, level=3):
        """Register the caller frame infos.

        Arguments:
            keywords (dict): Dict of keywords.
            level (Optional[int]): Number of frames to rewind to find the
                caller. Defaults to 2 (1: *here*, 2: *run_*, 3: *run*).
        """
        self._caller = {"filename": "unknown", "lineno": 0, "context": {}, "identifier": ""}
        caller = inspect.currentframe()
        try:
            for _ in range(level):
                if not caller.f_back:
                    break
                caller = caller.f_back
            self._caller["filename"] = caller.f_code.co_filename
            self._caller["lineno"] = caller.f_lineno
            self._caller["context"] = caller.f_globals
        finally:
            del caller

        try:
            identifier = "cmd{0}".format(keywords.pop("identifier"))
        except KeyError:
            identifier = "txt{0}".format(self._caller["lineno"])
        self._caller["identifier"] = identifier

    @classmethod
    def debugPrintAll(cls):
        """Call ``debugPrint()`` after each command.

        Use ``ExecuteCommand.debugPrintAll()`` in a testcase to make each
        command to dump its result content.
        """

        def _debugPrintAll(cmd, dummy):
            if not isinstance(cmd.result, DataStructure):
                return
            cmd.result.debugPrint(unit=10000 + cmd._counter)

        cls.register_hook(_debugPrintAll)


def check_jeveux():
    """Check that the memory manager (Jeveux) is up."""
    if not libaster.jeveux_status():
        raise RuntimeError("code_aster memory manager is not started. No command can be executed.")


class ExecuteMacro(ExecuteCommand):
    """This implements an executor of *legacy* macro-commands.

    The OPS function of *legacy* macro-commands returns a return code and
    declared results through ``self.register_result(...)``.

    Now the results must be directly returned by the OPS function.

    Long term: ``result = MACRO_COMMAND(**keywords)`` where ``result`` is
    a *DataStructure* object (for one result) or a *namedtuple-like* object
    (a code_aster *NamedTuple*) for several results).
    ``result`` is created by the *ops* function.

    For compatibility: :meth:`create_result` gets the names of the results.
    The *ops* function returns the "main" result and registers others with
    :meth:`register_result`.
    :meth:`exec_` adds it at first position of the *namedtuple* under the
    name "main".

    Attributes:
        _sdprods (list[:class:`CO`]): List of CO objects.
        _result_names (list[str]): List of expected results names.
        _add_results (dict): Dict of additional results.
    """

    # class attributes
    _last_cleanup = 0
    _last_cleanup_date = time.time()
    _check_freq = False

    _sdprods = _result_names = _add_results = None

    def __init__(self):
        """Initialization"""
        super(ExecuteMacro, self).__init__()
        self._op = self.command_op or import_object(self._op)

    def create_result(self, keywords):
        """Macro-commands create their results in the *exec_* method.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """

        def _predicate(value):
            if type(value) in (list, tuple):
                return all(isinstance(val, CO) for val in value)
            return isinstance(value, CO)

        self._sdprods = search_for(keywords, _predicate)
        if self._sdprods:
            names_i = (
                (ii.getName() for ii in i) if (type(i) in (list, tuple)) else [i.getName()]
                for i in self._sdprods
            )
            names = [ii for i in names_i for ii in i]
            self._result_names = names
            self._add_results = {}

    def print_result(self):
        """Print an echo of the result of the command."""
        if not self.show_syntax():
            return
        if not self._sdprods and self._result:
            logger.info(command_result(self._counter, self.name, self._result))
        if self._result_names:
            for name in self._result_names:
                logger.info(command_result(self._counter, self.name, self._add_results.get(name)))
        self._print_stats()

    def cleanup(self):
        """Clean-up function.

        Force deletion of removed objects after each macro-command.
        Some macro-commands may directly call ``gc.collect()`` if they create
        a lot of objects or if there is a risk to recreate an object with the
        same name (example: NonLinearOperator).
        """
        # extract 'max_check' once (suppose to optimize performance if it is small)
        if ExecuteMacro._last_cleanup == 0:
            ExecuteMacro._check_freq = ExecutionParameter().get_option("max_check") < 5
        if ExecuteMacro._check_freq and time.time() - ExecuteMacro._last_cleanup_date < 1.0:
            return
        if ExecuteCommand.level > 1:
            if self._counter < ExecuteMacro._last_cleanup + 250:
                return
        ExecuteMacro._last_cleanup = self._counter
        ExecuteMacro._last_cleanup_date = time.time()
        timer = ExecutionParameter().timer
        timer.Start(" . cleanup", num=1.9e6)
        # Only eliminates created object in generation 1
        gc.collect(1)
        timer.Stop(" . cleanup")
        super().cleanup()

    def exec_(self, keywords):
        """Execute the command and fill the *_result* attribute.

        Arguments:
            keywords (dict): User's keywords.
        """
        output = self._op(self, **keywords)
        assert not isinstance(output, int), "OPS must return results, not 'int'."
        if not self._tuplmode:
            self._result = output
            # re-assign the user variable name
            if hasattr(self._result, "userName"):
                user_name = get_user_name(
                    self.command_name, self._caller["filename"], self._caller["lineno"]
                )
                self._result.userName = user_name
            if self._add_results:
                publish_in(self.caller_context, self._add_results)
            return

        if not self._sdprods:
            self._result = output
        else:
            dres = dict(main=output)
            dres.update([(k, v) for k, v in self._add_results.items() if k in self._result_names])
            missing = set(self._result_names).difference(list(dres.keys()))
            if missing:
                raise ValueError("Missing results: {0}".format(tuple(missing)))
            self._result = NamedTuple(dres)

    def register_result(self, result, target):
        """Register an additional result.

        It must called **after** that the result has been created.

        Arguments:
            result (*DataStructure*): Result object to register.
            target (:class:`CO`): CO object.
        """
        name = target.getName()
        orig = result.userName
        result.userName = name
        self._add_results[name] = result
        if ExecutionParameter().option & Options.ShowChildCmd:
            logger.info(MessageLog.GetText("I", "SUPERVIS2_69", valk=(orig, name)))

    def check_ds(self):
        """Check all results created by the command.

        Arguments:
            result (*DataStructure*): Object to be checked.
        """
        if not self.show_syntax():
            return
        super().check_ds()
        if self._add_results:
            for additional in self._add_results.values():
                self.check_ds_result(additional)

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Macro-commands should not have to add dependencies. This should be done
        by embedded commands.

        Arguments:
            keywords (dict): User's keywords.
        """

    @property
    @deprecated(case=2)
    def reuse(self):
        return

    @property
    @deprecated(case=2)
    def sd(self):
        return

    @property
    @deprecated(case=3, help="Use the 'logger' object instead.")
    def cr(self):
        return logger

    @property
    def sdprods(self):
        """Attribute that holds the auxiliary results."""
        return self._sdprods or []


def UserMacro(name, cata, ops):
    """Helper function that defines a user macro-command from its catalog
    description and its operator.

    Arguments:
        name (str): Name of the macro-command.
        cata (*PartOfSyntax*): Catalog description of the macro-command.
        ops (str): OPS function of the macro-command.

    Returns:
        *ExecuteCommand.run*: Executor function.
    """

    class Macro(ExecuteMacro):
        """Execute legacy operator."""

        command_name = name
        command_cata = cata

        @staticmethod
        def command_op(self, **kwargs):
            return ops(self, **kwargs)

    return Macro.run


class CO(PyDataStructure):
    """Object that identify an auxiliary result of a Macro-Command."""

    _name = None

    @property
    def value_repr(self):
        """Returns the representation as a keyword value."""
        return "CO('{0}')".format(self.userName)

    def is_typco(self):
        """Tell if it is an auxiliary result."""
        return True

    def getType(self):
        """Return a type for syntax checking."""
        return "CO"

    def setType(self, typ):
        """Declare the future type."""
        pass

    # used in AsterStudy as settype
    settype = setType


def publish_in(context, dict_objects):
    """Publish some objects in a context.

    It supports list of results as declared in code_aster legacy:
    If an object is name ``xxx_n`` and that ``xxx`` exists and is a list in
    *context* and ``xxx[n]`` exists this item of the list is replaced by the
    new value.

    Arguments:
        context (dict): Destination context, changed in place.
        dict_objects (dict): Objects to be added into the context.
    """
    re_id = re.compile("^(.*)_([0-9]+)$")
    for name, value in list(dict_objects.items()):
        indexed = re_id.search(name)
        if indexed:
            bas, idx = indexed.groups()
            idx = int(idx)
            seq = context.get(bas)
            if seq and isinstance(seq, list) and len(seq) > idx:
                seq[idx] = value
                continue

        context[name] = value


def get_user_name(command, filename, lineno, strict=True):
    """Parse the caller syntax to extract the name used by the user.

    Arguments:
        command (str): Command name.
        filename (str): Filename of the caller
        lineno (int): Line number in the file.
        strict (bool, optional): Tell if the name must be a valid Python
            variable name.

    Returns:
        str: Variable name used by the user, empty if not found.
    """
    re_comment = re.compile(r"^\s*#.*")
    re_oper = re.compile(r"\b{0}\s*\(".format(command))
    if strict:
        re_name = re.compile(r"^\s*(?P<name>\w+)\s*" r"=\s*{0}\s*\(".format(command))
    else:
        re_name = re.compile(r"^\s*(?P<name>.+)\s*" r"=\s*{0}\s*\(".format(command))

    while lineno > 0:
        line = linecache.getline(filename, lineno)
        lineno = lineno - 1
        if re_comment.match(line):
            continue
        if re_oper.search(line):
            mat = re_name.search(line)
            if mat:
                # str() because of linecache in ipython, remove it in py3
                return str(mat.group("name")).strip()
            break

    return ""


def command_separator():
    """Return a separator line.

    Returns:
        str: A separator line.
    """
    if not hasattr(command_separator, "cache"):
        command_separator.cache = MessageLog.GetText("I", "SUPERVIS2_70")
    return command_separator.cache


def command_header(counter, filename, lineno):
    """Return the command header.

    Arguments:
        counter (int): Number of the command.

    Returns:
        str: String representation.
    """
    return MessageLog.GetText("I", "SUPERVIS2_71", vali=(counter, lineno), valk=filename)


def _get_object_repr(obj):
    typ = ""
    if hasattr(obj, "getName"):
        nam = decorate_name(obj.getName().strip())
        if obj.userName:
            nam = "{0} ({1})".format(obj.userName.strip(), nam)
        typ = MessageLog.GetText("I", "SUPERVIS2_76", valk=type(obj).__name__)
    elif isinstance(obj, str):
        nam = decorate_name(obj)
    else:
        nam = str(obj)
    return nam, typ


def command_result(counter, command_name, result):
    """Return the command footer.

    Arguments:
        counter (int): Number of the command.
        command_name (str): Command name.
        result (~.code_aster.Objects.DataStructure|str|list[str]): Result object or name(s) of the
            result(s) of the command.

    Returns:
        str: String representation.
    """
    show_name, show_type = _get_object_repr(result)
    dict_args = dict(vali=counter, valk=(command_name, show_name, show_type))
    return MessageLog.GetText("I", "SUPERVIS2_72", **dict_args)


def command_memory(command_name):
    """Return a representation of the current memory consumption.

    Arguments:
        command_name (str): Command name.

    Returns:
        str: String representation.
    """
    rval, iret = aster_core.get_mem_stat("VMPEAK", "VMSIZE", "CMAX_JV", "CMXU_JV")
    txt = ""
    if iret == 0:
        if ExecutionParameter().option & Options.TestMode:
            Tracking.add("MEM", command_name, *rval)
        if rval[0] > 0.0:
            txt = MessageLog.GetText("I", "SUPERVIS2_73", valr=rval)
        else:
            txt = MessageLog.GetText("I", "SUPERVIS2_74", valr=rval)
    return txt


def command_time(counter, cpu, system, elapsed):
    """Return a representation of elapsed times in a command.

    Arguments:
        cpu (float): User time.
        system (float): System time.
        elapsed (float): Elapsed time.

    Returns:
        str: String representation.
    """
    return MessageLog.GetText("I", "SUPERVIS2_75", vali=counter, valr=(cpu, system, elapsed))


class loop_on_dsdict:
    r"""Decorator on ExecuteCommand that overloads 'run\_' method to
    loop on each result of a DataStructureDict.

    Arguments:
        mark (str): Possible paths to keywords that may hold the DataStructureDict
            object. Format: "mcf1/mcs1|mcf2/mcs2|mcs3|..."
    """

    def __init__(dec, mark: str):
        dec._mark: str = mark

    def __call__(dec, command):
        command._orig_run_ = command.run_

        def run_(self, **kwargs):
            """Run the command."""

            def path_(kwds: dict):
                """Return the path to the relevant keyword"""
                candidates = dec._mark.split("|")
                for key in candidates:
                    store = kwds
                    mcs = key.split("/")
                    if len(mcs) < 2:
                        mcf = None
                    else:
                        mcf = mcs.pop(0)
                        if not kwds.get(mcf):
                            mcf = None
                            continue
                        store = kwds[mcf]
                    mcs = mcs.pop(0)
                    if store.get(mcs):
                        return mcf, mcs
                return None

            def extr_(kwds: dict, path: tuple[str]):
                """Return the value of the relevant keyword"""
                mcf, mcs = path
                if mcf:
                    kwds = kwds[mcf]
                return kwds[mcs]

            def set_(kwds: dict, path: tuple[str], value: DataStructureDict):
                """Set the value of the relevant keyword"""
                mcf, mcs = path
                if mcf:
                    kwds = kwds[mcf]
                kwds[mcs] = value

            self.keep_caller_infos(kwargs)
            caller = self._caller
            path = path_(kwargs)
            if not path or not isinstance(extr_(kwargs, path), DataStructureDict):
                output = command._orig_run_(self, **kwargs)
                if not getattr(output, "userName", "n/a"):
                    # attribute does exist but is not defined
                    output.userName = get_user_name(
                        self.command_name, caller["filename"], caller["lineno"]
                    )
                return output

            keywords = mixedcopy(kwargs)
            input = extr_(keywords, path)
            in_place = "reuse" in keywords
            if in_place:
                output = keywords["reuse"]
                assert output is input, "unexpected object in reuse"
            else:
                self.create_result(keywords)
                output = self._result
                if output is not None and not isinstance(output, DataStructureDict):
                    raise TypeError(f"Output should be a DataStructureDict or None, not {output}.")

            for key in input:
                set_(keywords, path, input[key])
                if in_place:
                    keywords["reuse"] = extr_(keywords, path)
                output[key] = command._orig_run_(self, **keywords)
            return output

        command.run_ = run_
        return command


class ExceptHookManager:
    """Object to manager the definition of the *excepthook*."""

    _current_cmd = None

    @classmethod
    def enter(cls, command):
        """Assign the excepthook when entering in a command."""
        # keep the outer command
        if not cls._current_cmd:
            cls._current_cmd = command

    @classmethod
    def exit(cls, command):
        """Called when exiting a command."""
        if command is cls._current_cmd:
            cls._current_cmd = None

    @classmethod
    def init(cls):
        """Assign the basic hook."""
        sys.excepthook = cls.excepthook

    @classmethod
    def excepthook(cls, type, value, traceb):
        """Hook called on uncaught exceptions raised during the execution of a command.

        Args:
            command (ExecuteCommand): The current command.
            type (type): Exception type.
            value (BaseException): Exception instance.
            traceb (traceback): Exception traceback.
        """
        opt = ExecutionParameter().option
        traceback.print_exception(type, value, traceb, file=sys.stderr)
        sys.stderr.flush()
        if config["ASTER_PLATFORM_MINGW"]:
            time.sleep(1)
        if (
            sys.flags.interactive
            or opt & Options.InteractiveInterpreter
            or "__IPYTHON__" in globals()
        ):
            print("An exception occurred! Return to interactive session.")
            return
        if cls._current_cmd:
            options = FinalizeOptions.Set
            if haveMPI() and not opt & Options.HPCMode:
                options |= FinalizeOptions.OnlyProc0
            if opt & Options.SaveBase:
                options |= FinalizeOptions.SaveBase
            print("\nException: Trying to close the database after an uncaught exception...\n")
            print(
                f"\nPublishing the result of the current command {cls._current_cmd.name}...\n",
                flush=True,
            )
            cls._current_cmd.publish_result()
            saveObjectsFromContext(cls._current_cmd.caller_context, options=options)
        else:
            sys.__excepthook__(type, value, traceb)

    @classmethod
    @contextmanager
    def wraps(cls, command):
        """Context manager used to enable a specific hook during a command execution."""
        cls.enter(command)
        yield
        cls.exit(command)


ExceptHookManager.init()
