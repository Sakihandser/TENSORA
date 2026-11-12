#!/usr/bin/env python3
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
``bin/run_aster`` --- Script to execute code_aster
--------------------------------------------------

``bin/run_aster`` executes a code_aster study from the command line.
The parameters and files used by the study are defined in a ``.export`` file
(see :py:mod:`~run_aster.export` for description of the syntax of the
``.export``).

For parallel executions, these two forms are equivalent (if the ``.export``
contains ``P mpi_nbcpu 4``):

.. code-block:: sh

    bin/run_aster path/to/file.export

or:

.. code-block:: sh

    mpiexec -n 4 bin/run_aster path/to/file.export

Using the first syntax, ``bin/run_aster`` re-runs itself with ``mpiexec`` using
the second syntax (``mpiexec`` syntax is provided by the configuration, see
:py:mod:`~run_aster.config`).

If the version has been configured with ``--use-srun``, you *must* use:

.. code-block:: sh

    bin/run_aster path/to/file.export

or:

.. code-block:: sh

    srun -n 4 [options] bin/run_aster path/to/file.export


``bin/run_aster`` can also directly execute a Python file (``.py`` or ``.comm``
extension is expected) with code_aster commands.
In this case, no data or result files are managed by ``run_aster`` and
default values are used for memory and time limit (use options to change
these values).

.. code-block:: sh

    bin/run_aster path/to/file.py

Data files may be referenced in the Python file with relative paths from the
parent directory of ``file.py`` using, for example, ``os.path.dirname(__file__)``.

For the parallel version:

.. code-block:: sh

    mpiexec -n 2 bin/run_aster --only-proc0 path/to/file.py

or:

.. code-block:: sh

    bin/run_aster -n 2 --only-proc0 path/to/file.py

``bin/run_aster`` only runs its own version, those installed at the level of
the ``bin`` directory; unlike ``as_run`` where the same instance of ``as_run``
executes several versions of code_aster.
This makes ``bin/run_aster`` simpler and allows per version settings
(see :py:mod:`~run_aster.config` for more informations about the configuration
of a version).

More options are available to execute code_aster with an interactive Python
interpreter, to prepare a working directory and to start manually (through
a debugger for example)...
For example, executing ``bin/run_aster`` with no ``.export`` file starts an
interactive Python interpreter.

See ``bin/run_aster --help`` for the available options.

"""

# aslint: disable=C4009
# C4009: in a string, imported here

import argparse
import os
import os.path as osp
import shutil
import sys
import tempfile
from pathlib import Path
from subprocess import run

from .base_params import RUNASTER_PLATFORM, RUNASTER_ROOT
from .command_files import AUTO_START, NOINIT_START
from .config import CFG
from .export import Export, File, split_export
from .logger import DEBUG, WARNING, logger
from .run import RunAster, create_temporary_dir, get_procid
from .status import Status

try:
    import debugpy

    HAS_DEBUGPY = True
except ImportError:
    HAS_DEBUGPY = False

USAGE = """
    run_aster [options] FILE[.export|.py]

"""

EPILOG = """
The time limit is automatically increased to 24 hours for "interactive" usages
as '--interactive', '--env', '--no-comm', '--gdb', '--valgrind'.
"""

# for interactive executions (using IPython)
PROLOG = """
import os
import sys

from code_aster.Utilities import ExecutionParameter
ExecutionParameter().set_argv(sys.argv)
"""

CWD = r"""
print(f"Working directory: {os.getcwd()}")
print("# CA.basedir is the directory from which run_aster started")
print(f"CA.basedir: {CA.basedir}\n")
"""


def parse_args(argv):
    """Parse command line arguments.

    Arguments:
        argv (list): List of command line arguments.
    """
    # command arguments parser
    parser = argparse.ArgumentParser(
        usage=USAGE, epilog=EPILOG, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--version", action="store_true", help="show code_aster version")
    parser.add_argument(
        "-g",
        "--debug",
        action="store_true",
        help="print debugging information (same as DEBUG=1 in environment)",
    )
    parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="inspect interactively after running script instead of calling FIN command",
    )
    parser.add_argument(
        "--no-init",
        dest="no_init",
        action="store_true",
        help="do not automatically initialize code_aster with '--interactive'",
    )
    parser.add_argument(
        "--env",
        action="store_true",
        help="do not execute, only prepare the working directory ('--workdir' is required)",
    )
    parser.add_argument(
        "-w", "--workdir", action="store", help="use this directory as working directory"
    )
    parser.add_argument("--wrkdir", action="store", help=argparse.SUPPRESS)
    parser.add_argument(
        "--all-procs",
        dest="only_proc0",
        action="store_false",
        default=None,
        help="show all processors output",
    )
    parser.add_argument(
        "--only-proc0",
        dest="only_proc0",
        action="store_true",
        default=None,
        help="only processor #0 is writing on stdout",
    )
    parser.add_argument(
        "--proc0-is",
        dest="proc0id",
        action="store",
        type=int,
        default=0,
        help="make this process to replace proc #0 (for example, it will copy the results)",
    )
    parser.add_argument(
        "--mpi",
        dest="rerun_mpi",
        action="store_const",
        const=True,
        default="auto",
        help="restart run_aster with 'mpiexec -n MPI_NBCPU run_aster ...' "
        "(it uses mpiexec or srun depending on the configuration of the version). "
        "By default, it is done only if necessary",
    )
    parser.add_argument(
        "--no-mpi",
        dest="rerun_mpi",
        action="store_const",
        const=False,
        default="auto",
        help="do not restart run_aster with 'mpiexec -n MPI_NBCPU run_aster ...' "
        "even if it seems necessary",
    )
    parser.add_argument("-t", "--test", action="store_true", help="execution of a testcase")
    parser.add_argument(
        "--ctest",
        action="store_true",
        help="testcase execution inside ctest (implies '--test'), the 'code' file is saved into "
        "the current directory (which is '--resutest' directory for 'run_ctest')",
    )
    parser.add_argument(
        "-n",
        dest="mpi_nbcpu",
        type=int,
        action="store",
        help="override the number of MPI processes",
    )
    parser.add_argument(
        "--time_limit",
        dest="time_limit",
        type=float,
        action="store",
        default=None,
        help="override the time limit (may also be changed by FACMTPS environment variable)",
    )
    parser.add_argument(
        "--memory_limit",
        dest="memory_limit",
        type=float,
        action="store",
        help="override the memory limit in MB",
    )
    parser.add_argument(
        "--no-comm",
        dest="no_comm",
        action="store_true",
        help="do not execute the `.comm` files but start an interactive Python session"
        "`CA.init()` is automatically called.",
    )
    parser.add_argument(
        "--save_db",
        action="store_true",
        help="force the closure of the database results even if there is none",
    )
    parser.add_argument(
        "--gdb",
        action="store_const",
        const="gdb",
        dest="exectool",
        help="wrap code_aster execution using share/aster/exectool/gdb_wrapper",
    )
    parser.add_argument(
        "--valgrind",
        action="store_const",
        const="valgrind",
        dest="exectool",
        help="wrap code_aster execution using 'valgrind --tool=memcheck...'",
    )
    parser.add_argument(
        "--exectool",
        action="store",
        help="wrap code_aster execution using this tool (debugger, valgrind, custom command...)",
    )
    parser.add_argument("--debugpy-runner", action="store", type=int, help=argparse.SUPPRESS)
    parser.add_argument(
        "--debugpy-rank", action="store", type=int, default=0, help=argparse.SUPPRESS
    )
    parser.add_argument("--status-file", action="store", dest="statusfile", help=argparse.SUPPRESS)
    parser.add_argument(
        "file",
        metavar="FILE",
        nargs="?",
        help="Export file (.export) defining the calculation or "
        "Python file (.py|.comm). "
        "Without file, it starts an interactive Python session",
    )

    args = parser.parse_args(argv)
    if args.debug:
        logger.setLevel(DEBUG)
        os.environ["DEBUG"] = str(os.environ.get("DEBUG") or 1)
    if args.version:
        tag = CFG.get("version_tag")
        sha1 = CFG.get("version_sha1")[:12]
        logger.info("code_aster %s (%s)", tag, sha1)
        parser.exit(0)
    if args.wrkdir:
        logger.warning("'--wrkdir' is deprecated, please use '--workdir'")
        if not args.workdir:
            args.workdir = args.wrkdir
    if args.env and not args.workdir:
        parser.error("Argument '--workdir' is required if '--env' is enabled")
    if args.debugpy_runner and not HAS_DEBUGPY:
        parser.error("can not import 'debugpy'")
    return args


def main(argv=None):
    """Entry point for code_aster runner.

    Arguments:
        argv (list): List of command line arguments.
    """
    argv = argv or sys.argv[1:]
    args = parse_args(argv)

    args.proc0id = max(0, args.proc0id)
    procid = args.proc0id
    if CFG.get("parallel", False):
        procid = get_procid()
    if procid < 0:
        args.only_proc0 = False

    direct = args.file and osp.splitext(args.file)[-1] in (".py", ".comm")
    export = Export(
        args.file if not direct else None, " ", test=args.test or args.ctest, check=False
    )
    args.test = args.test or export.get("service") == "testcase"
    make_env = args.env or "make_env" in export.get("actions", [])
    if export.get("no-mpi"):
        args.rerun_mpi = False
    logger.debug("parallel: %s, procid: %d", CFG.get("parallel", False), procid)
    logger.debug("nbcomm: %d", len(export.commfiles))
    need_split = len(export.commfiles) > 1
    need_mpiexec = args.rerun_mpi
    if need_split and CFG.get("parallel", False) and procid >= 0:
        # keep as warning in case mpiexec is badly detected
        funclog = logger.error if need_mpiexec == "auto" else logger.warning
        funclog(
            "\n ------------------------------------------------------------"
            "\n This study contains several comm files."
            "\n Each comm file must be separately executed under MPI runner"
            "\n because MPI can not be restarted after a finalization."
            "\n This instance of run_aster seems to be already run with mpiexec or srun."
            "\n It will probably fail or block."
            "\n Let run_aster automatically split and run each comm file separately"
            "\n or execute each comm file one by one."
            "\n Add '--mpi' or '--no-mpi' option to change this error into a warning."
            "\n ------------------------------------------------------------"
        )
    if args.mpi_nbcpu:
        export.set("mpi_nbcpu", args.mpi_nbcpu)
    if need_mpiexec == "auto":
        need_mpiexec = export.get("mpi_nbcpu", 1) > 1 or CFG.get("require_mpiexec", False)
        if need_mpiexec and procid < 0:
            logger.warning(
                "\n ------------------------------------------------------------"
                "\n run_aster will be restarted under MPI runner."
                "\n Use '--no-mpi' option if you do not want to use 'mpi_nbcpu' from the export file."
                "\n ------------------------------------------------------------"
            )
    logger.debug("need_split: %s / need_mpiexec: %s", need_split, need_mpiexec)

    if (
        args.debugpy_runner
        and (procid < 0 or procid == args.debugpy_rank)
        and not (need_split or need_mpiexec)
    ):
        debugpy.listen(("localhost", args.debugpy_runner))
        print("Waiting for debugger attach")
        debugpy.wait_for_client()
        debugpy.breakpoint()

    tmpf = None
    if args.no_comm:
        for comm in export.commfiles:
            export.remove_file(comm)
    if not os.environ.get("RUNASTER_CA_BASEDIR"):
        basedir = os.fspath(Path.cwd())
        if export.filename:
            basedir = os.fspath(Path(export.filename).parent)
        if export.get("service") == "testcase":
            # run from as_run via run_testcases
            basedir = Path(export.commfiles[0].path).parent
        os.environ["RUNASTER_CA_BASEDIR"] = str(basedir)

    if direct:
        export.add_file(File(osp.abspath(args.file), filetype="comm", unit=1))
    elif not args.file or args.no_comm:
        args.interactive = True
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as fobj:
            tmpl = NOINIT_START if args.no_init else AUTO_START
            fobj.write(tmpl.substitute(prolog=PROLOG, starter=CWD))
            export.add_file(File(fobj.name, filetype="comm", unit=1))
            tmpf = fobj.name
    # output = None
    if args.ctest:
        args.test = True
        basename = osp.splitext(osp.basename(args.file))[0]
        add = {15: "code"}
        for unit, typ in add.items():
            if export.files_of_type(typ):
                continue
            res = File(osp.abspath(basename + "." + typ), filetype=typ, unit=unit, resu=True)
            export.add_file(res)
    if args.time_limit:
        export.set_time_limit(args.time_limit)
    # use FACMTPS from environment
    mult = 1.0
    if not (need_split or need_mpiexec):
        try:
            mult = float(os.environ.get("FACMTPS", 1))
        except ValueError:
            pass
    limit = export.get("time_limit", 86400.0) * mult
    export.set_time_limit(limit)
    if args.interactive:
        export.set("interact", True)
    if args.interactive or make_env or args.exectool in ("valgrind", "gdb"):
        export.set_time_limit(86400.0)
    if args.memory_limit:
        export.set_memory_limit(args.memory_limit)
    export.check()

    if args.only_proc0 is None:
        args.only_proc0 = CFG.get("only-proc0", False)

    workdir = args.workdir or create_temporary_dir()
    exitcode = -1
    try:
        if need_split or need_mpiexec:
            logger.warning(
                "If MPI_Abort is called during execution, result files could not be copied."
            )
            run_aster = osp.join(RUNASTER_ROOT, "bin", "run_aster")
            try:
                expdir = create_temporary_dir(dir=os.fspath(Path.home() / ".tmp_run_aster"))
            except (OSError, KeyError):
                expdir = create_temporary_dir()
            statfile = osp.join(expdir, "__status__")
            basn = osp.basename(osp.splitext(args.file or "unnamed")[0])
            expected = export.get("expected_diag", [])
            for exp_i in split_export(export):
                fexp = osp.join(expdir, basn + "." + str(exp_i.get("step")))
                exp_i.write_to(fexp)
                argv_i = [i for i in argv if i not in (args.file, "--mpi")]
                if not args.workdir:
                    argv_i.append("--workdir")
                    argv_i.append(workdir)
                argv_i.extend(["--status-file", statfile])
                if "--no-mpi" not in argv_i:
                    argv_i.append("--no-mpi")
                argv_i.append(fexp)

                cmd = f"{run_aster} {' '.join(argv_i)}"
                if need_mpiexec:
                    args_cmd = dict(
                        mpi_nbcpu=export.get("mpi_nbcpu", 1),
                        ncpus=export.get("ncpus", 1),
                        program=cmd,
                    )
                    memnode = os.environ.get("SLURM_MEM_PER_NODE")
                    if memnode and export.get("memory_limit"):
                        memcpu = float(memnode) / float(os.environ.get("SLURM_CPUS_ON_NODE", 1))
                        args_cmd["mem-per-cpu"] = int(memcpu)
                    cmd = CFG.get("mpiexec").format(**args_cmd)
                    logger.debug("Args: %s", args_cmd)
                logger.info("Running: %s", cmd)
                proc = run(cmd, shell=True, check=False)
                status = Status.load(statfile)
                exitcode = proc.returncode
                if exitcode != 0:
                    if status.is_completed() and "<F>_ABNORMAL_ABORT" in expected:
                        # RunAster._get_status has reset the status
                        exitcode = 0
                        continue
                    break
            shutil.rmtree(expdir, ignore_errors=True)
            return exitcode

        if args.only_proc0 and procid != args.proc0id:
            logger.setLevel(WARNING)
        opts = {}
        opts["test"] = args.test
        opts["env"] = make_env
        if RUNASTER_PLATFORM == "linux":
            opts["tee"] = not args.only_proc0 or procid == args.proc0id
        else:
            # MSVC build: tee through the Windows console breaks the output capture
            opts["tee"] = False
        opts["interactive"] = args.interactive
        opts["savedb"] = args.save_db
        opts["proc0id"] = args.proc0id
        if args.exectool:
            wrapper = CFG.get("exectool", {}).get(args.exectool)
            if not wrapper:
                logger.warning(
                    "'%s' is not defined in your configuration, it is used as a command line.",
                    args.exectool,
                )
                wrapper = args.exectool
            opts["exectool"] = wrapper
        calc = RunAster.factory(export, **opts)
        status = calc.execute(workdir)
        exitcode = status.exitcode
        if args.statusfile:
            status.save(args.statusfile)
        if tmpf and not opts["env"]:
            os.remove(tmpf)
    finally:
        if not args.workdir:
            os.chdir(osp.dirname(workdir))
            shutil.rmtree(workdir, ignore_errors=True)
    return exitcode


if __name__ == "__main__":
    sys.exit(main())
