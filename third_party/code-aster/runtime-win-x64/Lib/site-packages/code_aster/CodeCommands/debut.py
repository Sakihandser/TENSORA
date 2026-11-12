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
:py:class:`DEBUT` --- Initialization of code_aster
**************************************************

The :py:class:`Starter` starts the execution by initializing the code_aster
memory manager (*Jeveux*). For this task, it parses the arguments through the
:py:class:`~code_aster.Utilities.ExecutionParameter.ExecutionParameter` object.
By default, arguments are those read from the command line and those passed
:py:func:`.init`.
If the command line arguments are not set for code_aster, they can be ignored
with ``CA.init(..., noargv=True)``.

Some Python objects that have to be available from :py:mod:`libaster` are
passed during the initialization to the
:py:class:`~code_aster.Utilities.ExecutionParameter.ExecutionParameter`.
"""

from functools import partial

import aster_core
import libaster

from run_aster.run import copy_datafiles

from ..Behaviours import catalc
from ..Cata.Syntax import tr
from ..Helpers import LogicalUnitFile
from ..Messages import UTMESS, MessageLog
from ..Supervis import CommandSyntax, ExecuteCommand, Serializer, loadObjects
from ..Supervis.code_file import Tracking
from ..Supervis.ctopy import checksd, print_header
from ..Supervis.TestResult import testresu_print
from ..Utilities import MPI, ExecutionParameter, Options, config, import_object, logger
from ..Utilities.general import Random
from ..Utilities.i18n import localization
from ..Utilities.rc import rc

try:
    import debugpy

    HAS_DEBUGPY = True
except ImportError:
    HAS_DEBUGPY = False


class ExecutionStarter:
    """Initialize the
    :class:`~code_aster.Utilities.ExecutionParameter.ExecutionParameter` object
    for requests from the both sides Python/Fortran."""

    params = _is_initialized = None

    @classmethod
    def init(cls, set_args_callback, argv=None, fcomm=0):
        """Initialization of class attributes.

        Attributes:
            set_args_callback (func): Callback to assign parameters values after
                parsing arguments (but before the libaster initialization).
            argv (list[str], None): List of command line arguments
                (defaults to sys.argv).
            fcomm (int, optional): Id of the MPI communicator.

        Returns:
            bool: *True* if the initialization has been done, *False* if the
            execution was already initialized.
        """
        if cls._is_initialized:
            return False
        params = cls.params = ExecutionParameter()
        params.parse_args(argv)
        if set_args_callback:
            set_args_callback(params)
        params.register_global_object("catalc", catalc)
        params.register_global_object("logical_unit", LogicalUnitFile)
        params.register_global_object("syntax", CommandSyntax)
        params.register_global_object("print_header", print_header)
        params.register_global_object("checksd", checksd)
        params.register_global_object("testresu_print", testresu_print)
        params.register_global_object("iniran", Random.initialize)
        params.register_global_object("getran", Random.get_number)
        copy_datafiles(params.export.datafiles)
        aster_core.register(params, MessageLog)
        libaster.jeveux_init(fcomm)
        cls._is_initialized = True
        return True


class Starter(ExecuteCommand):
    """Define the commands DEBUT/POURSUITE."""

    command_name = "DEBUT"
    level = 7

    @classmethod
    def run(cls, caller, **keywords):
        """Run the Command.

        Arguments:
            keywords (dict): User keywords
        """
        init_args = list(keywords.pop("init_args", ()))
        if init_args:
            pass_cbck = init_args[0]
        else:
            pass_cbck = None
            init_args = [None]

        def callback(params):
            if pass_cbck:
                pass_cbck(params)
            mem = params.get_option("memory")
            if mem > 1024.0:
                kwmem = keywords.get("RESERVE_MEMOIRE", {})
                mem -= kwmem.get("VALE", mem * kwmem.get("POURCENTAGE", 0.1))
                params.set_option("memory", mem)
                logger.info(f"setting '--memory' value to {mem:.2f} MB (keyword RESERVE_MEMOIRE)")

        init_args[0] = callback
        if not ExecutionStarter.init(*init_args):
            return

        params = ExecutionStarter.params
        if caller == "init":
            cls.level += 1
        if rc.initialize:
            cls.level += 1
        # restart = 'True | False | None' from rc / override by keywords
        restart = rc.restart
        # force startup or continue ?
        mode = keywords.get("MODE")
        if mode == "DEBUT" or params.get_option("ForceStart"):
            restart = False
        if caller == "POURSUITE" or mode == "POURSUITE" or params.get_option("Continue"):
            restart = True

        startable = Serializer.canRestart(silent=True)
        if restart is None:
            restart = startable
        if restart:
            if not startable:
                logger.error("restart aborted!")
            logger.info("restarting from a previous execution...")
        else:
            logger.info("starting the execution...")

        params.set_option("ForceStart", not restart)
        params.set_option("Continue", restart)

        super().run(**keywords)

    def exec_(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        params = ExecutionStarter.params
        iwarn = False
        stop_with = "EXCEPTION"
        if params.option & Options.Abort:
            stop_with = "ABORT"
        if params.option & Options.TestMode or keywords.get("CODE", "NON") == "OUI":
            params.enable(Options.TestMode)
            stop_with = "ABORT"
            iwarn = True
            Tracking.add("KWDS", self._cata, self.command_name, keywords)

        erreur = keywords.get("ERREUR")
        if erreur:
            if erreur.get("ERREUR_F"):
                stop_with = erreur["ERREUR_F"]
            if erreur.get("ALARME") == "EXCEPTION":
                # too many warnings on migw for currently unsupported features
                if config["ASTER_PLATFORM_MINGW"]:
                    UTMESS("I", "SUPERVIS_11")
                else:
                    params.enable(Options.WarningAsError)
        if params.option & Options.SlaveMode:
            stop_with = "EXCEPTION"
        # must be the first call to correctly set 'vini' in onerrf
        libaster.onFatalError(stop_with)

        debug = keywords.get("DEBUG")
        if debug:
            jxveri = debug.get("JXVERI", "NON") == "OUI"
            params.set_option("jxveri", int(jxveri))
            if jxveri:
                UTMESS("I", "SUPERVIS_23")
            sdveri = debug.get("SDVERI", "NON") == "OUI"
            params.set_option("sdveri", int(sdveri))
            if sdveri:
                UTMESS("I", "SUPERVIS_24")
            dbgjeveux = debug.get("JEVEUX", "NON") == "OUI" or debug.get("VERI_BASE") is not None
            params.set_option("dbgjeveux", int(dbgjeveux))
            if dbgjeveux:
                UTMESS("I", "SUPERVIS_12")
            iwarn = iwarn or jxveri or sdveri or dbgjeveux
        if iwarn:
            UTMESS("I", "SUPERVIS_22", valk=("--test", "CA.init()"))
        if params.get_option("hook_post_exec"):
            path = params.get_option("hook_post_exec")
            hook = import_object(path)
            self.register_hook(hook)

        params.enable(Options.ShowSyntax)
        if keywords.get("IMPR_MACRO") == "OUI":
            params.enable(Options.ShowChildCmd)

        if keywords.get("LANG"):
            translation = localization.translation(keywords["LANG"])
            tr.set_translator(translation.gettext)

        if keywords.get("IGNORE_ALARM"):
            for idmess in keywords["IGNORE_ALARM"]:
                MessageLog.disable_alarm(idmess, skip=not params.option & Options.TestMode)

        super().exec_(keywords)

    def _call_oper(self, syntax):
        """Call fortran operator.

        Arguments:
            syntax (*CommandSyntax*): Syntax description with user keywords.
        """
        super()._call_oper(syntax)

        if ExecutionStarter.params.option & Options.Continue:
            # 1:_call_oper, 2:ExecuteCommand.exec_, 3:Starter.exec_,
            #  4:Restarter.run, 5:ExecuteCommand.run_, 6:ExecuteCmd.run, 7:user
            # 1:_call_oper, 2:ExecuteCommand.exec_, 3:Starter.exec_,
            #  4:_run_with_argv, 5:run_with_argv, 6:init, 7:user
            # when called during 'import CA', 9 levels are added...
            loadObjects(level=self.level)


DEBUT = partial(Starter.run, caller="DEBUT")
POURSUITE = partial(Starter.run, caller="POURSUITE")


def init(*argv, **kwargs):
    """Initialize code_aster as `DEBUT`/`POURSUITE` command does + command
    line options.

    If the code_aster study is embedded under another Python program, the
    "--slave" option may be useful to catch exceptions (even *TimeLimitError*)
    and **try** not to exit the Python interpreter.

    Arguments:
        argv (list): List of command line arguments.
        kwargs (dict): Keywords arguments passed to 'DEBUT'/'POURSUITE' +
            'debug (bool)' same as -g/--debug,
            'debugpy (int)' to start a debugpy session on this port number,
            'noargv (bool)' to ignore previously passed arguments,
            'comm (*mpi4py.MPI.Comm*)' to select the MPI communicator.
    """
    if kwargs.pop("noargv", False):
        ExecutionParameter().set_argv([])
    comm = kwargs.pop("comm", None)
    if comm:
        fcomm = comm.py2f()
        MPI.ASTER_COMM_WORLD = comm
    else:
        fcomm = 0
    debug = kwargs.pop("debug", False)
    port = kwargs.pop("debugpy", None)

    def callback(params):
        """Set parameters after parsing arguments"""
        if debug:
            params.enable(Options.Debug)
        if port and HAS_DEBUGPY:
            # add 10 hours for debugging
            tpmax = params.get_option("tpmax")
            params.set_option("tpmax", tpmax + 36000)

    if port and HAS_DEBUGPY:
        debugpy.listen(("localhost", port))
        logger.info("Waiting for debugger attach")
        debugpy.wait_for_client()
        debugpy.breakpoint()

    Starter.run("init", init_args=(callback, argv, fcomm), **kwargs)
