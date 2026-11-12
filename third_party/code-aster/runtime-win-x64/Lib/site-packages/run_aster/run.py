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
:py:mod:`run` --- Main classes for execution
--------------------------------------------

This module defines the objects that prepare the working directory, copy the
data files, execute code_aster and copy the result files.
"""

import os
import os.path as osp
import platform
import tempfile
from glob import glob
from pathlib import Path
from subprocess import PIPE, run

from .base_params import RUNASTER_PLATFORM, RUNASTER_ROOT
from .command_files import (
    add_coding_line,
    add_import_commands,
    change_procdir,
    file_changed,
    stop_at_end,
)
from .config import CFG
from .logger import WARNING, logger
from .status import StateOptions, Status, get_status
from .timer import Timer
from .utils import PercTemplate, cmd_abspath, compress, copy, make_writable, run_command, uncompress

EXITCODE_FILE = "_exit_code_"
TMPMESS = "fort.6"
FMT_DIAG = """
------------------------------------------------------------
--- DIAGNOSTIC JOB : {state}
------------------------------------------------------------
"""


def create_temporary_dir(dir=None):
    """Create a temporary directory.

    Returns:
        str: Path of the directory.
    """
    dir = dir or os.environ.get("ASTER_WORKDIR", CFG.get("tmpdir"))
    if dir:
        os.makedirs(dir, exist_ok=True)
    return tempfile.mkdtemp(prefix="run_aster_", dir=dir)


class RunAster:
    """Execute code_aster from a `.export` file.

    Arguments:
        export (Export): Export object defining the calculation.
    """

    _show_comm = True
    _chg_procdir = False

    @classmethod
    def factory(
        cls,
        export,
        test=False,
        env=False,
        tee=False,
        output=None,
        interactive=False,
        exectool=None,
        savedb=None,
        proc0id=0,
    ):
        """Return a *RunAster* object from an *Export* object.

        Arguments:
            export (Export): Export object defining the calculation.
            test (bool): for a testcase,
            env (bool): to only prepare the working directory and show
                command lines to be run,
            tee (bool): to follow execution output,
            output (str): Path to redirect stdout.
            interactive (bool): to keep Python interpreter active.
            exectool (str): command that preceeds code_aster command line.
            savedb (bool): tell if the database should be saved.
            proc0id (int): id of the process that replaces the proc #0.
        """
        class_ = RunAster
        if env:
            class_ = RunOnlyEnv
        return class_(export, test, tee, output, interactive, exectool, savedb, proc0id)

    def __init__(
        self,
        export,
        test=False,
        tee=False,
        output=None,
        interactive=False,
        exectool=None,
        savedb=None,
        proc0id=0,
    ):
        self.export = export
        self.jobnum = str(os.getpid())
        logger.debug("Export content: %s", self.export.filename)
        logger.debug("\n%s", self.export)
        self._parallel = CFG.get("parallel", 0)
        self._test = test
        self._tee = tee
        self._output = output or TMPMESS
        self._interact = interactive
        self._exectool = exectool
        if self.export.get("hide-command"):
            self._show_comm = False
        self._proc0id = proc0id
        procid = 0
        if self._parallel:
            procid = get_procid()
        procid = max(procid, 0)
        self._procid = procid
        # multi-steps study
        if not export.has_param("step"):
            export.set("step", 0)
        if not export.has_param("nbsteps"):
            export.set("nbsteps", len(self.export.commfiles))
        self._last = export.get("step") + 1 == export.get("nbsteps")
        self._savdb = savedb or bool([i for i in export.resultfiles if i.filetype == "base"])

    def execute(self, workdir):
        """Execution in a working directory.

        Arguments:
            workdir (str): Working directory.

        Returns:
            Status: Status object.
        """
        if self._parallel:
            workdir = osp.join(workdir, f"proc.{self._procid}")
        os.makedirs(workdir, exist_ok=True)
        os.chdir(workdir)
        status = self._execute()
        return status

    def _execute(self):
        """Execution in the current working directory.

        Returns:
            Status: Status object.
        """
        timer = Timer()
        timer.load("__timer__")
        logger.info("TITLE Execution of code_aster")
        timer.start("Preparation of environment")
        self.prepare_current_directory()
        timer.stop()
        timer.start("Execution of code_aster")
        status = self.execute_study()
        timer.stop()
        if self._last or not status.is_completed():
            timer.start("Copying results")
            self.ending_execution(status.results_saved())
            logger.info("TITLE Execution summary")
            logger.info(timer.report())
            if self._procid == self._proc0id:
                logger.info(FMT_DIAG.format(state=status.diag))
        timer.save("__timer__")
        return status

    def prepare_current_directory(self):
        """Prepare the working directory."""
        logger.info("TITLE Prepare environment in %s", os.getcwd())
        self.export.write_to(self.jobnum + ".export")
        os.makedirs("REPE_IN", exist_ok=True)
        os.makedirs("REPE_OUT", exist_ok=True)

    def execute_study(self):
        """Execute the study.

        Returns:
            Status: Status object.
        """
        commfiles = [obj.path for obj in self.export.commfiles]
        if not commfiles:
            logger.error("no .comm file found")
        if self.export.get("nbsteps") > 1:
            os.makedirs("BASE_PREC", exist_ok=True)

        timeout = self.export.get("time_limit", 86400) * 1.25 * self.export.get("ncpus", 1)
        status = Status()
        comm = commfiles[0]
        logger.info(
            "TITLE Command file #{0} / {1}".format(
                self.export.get("step") + 1, self.export.get("nbsteps")
            )
        )
        comm = self.change_comm_file(comm)
        status.update(self._exec_one(comm, timeout - status.times[-1]))
        if platform.system() != "Windows":
            self._coredump_analysis()
        return status

    def _exec_one(self, comm, timeout):
        """Show instructions for a command file.

        Arguments:
            comm (str): Command file name.
            timeout (float): Remaining time.

        Returns:
            Status: Status object.
        """
        idx = self.export.get("step")
        logger.info("TITLE Command line #%d:", idx + 1)
        timeout = int(max(1, timeout))
        cmd = self._get_cmdline(idx, comm, timeout)
        logger.info("    %s", " ".join(cmd))

        set_num_threads(self.export.get("ncpus", 1))
        # use environment variable to make it works with ipython
        os.environ["PYTHONFAULTHANDLER"] = "1"
        exitcode = run_command(cmd, exitcode_file=EXITCODE_FILE)
        status = self._get_status(exitcode)
        # workaround on windows to write the output into the '.mess' file running by ctest
        if RUNASTER_PLATFORM == "win" and not self._tee:
            with open(self._output, "rb") as fobj:
                text = fobj.read().decode(errors="replace")
            logger.info(text)

        msg = f"\nEXECUTION_CODE_ASTER_EXIT_{self.jobnum}={status.exitcode}\n\n"
        logger.info(msg)
        self._log_mess(msg)

        if status.results_saved():
            if not self._last and status.is_completed():
                for vola in glob("vola.*"):
                    os.remove(vola)
                logger.info("saving result databases to 'BASE_PREC'...")
                for base in glob("glob.*") + glob("pick.*"):
                    copy(base, "BASE_PREC")
            msg = f"execution ended (command file #{idx + 1}): {status.diag}"
            logger.info(msg)
        else:
            logger.info("restoring result databases from 'BASE_PREC'...")
            for base in glob(osp.join("BASE_PREC", "*")):
                copy(base, os.getcwd())
            msg = f"execution failed (command file #{idx + 1}): {status.diag}"
            logger.warning(msg)
        if self._procid == self._proc0id:
            self._log_mess(FMT_DIAG.format(state=status.diag))
        return status

    def _get_cmdline_exec(self, commfile, idx):
        """Build the command line really executed, without redirection.

        Arguments:
            commfile (str): Command file name.
            idx (int): Index of execution.

        Returns:
            list[str]: List of command line arguments, without redirection.
        """
        cmd = []
        if self._exectool:
            cmd.append(self._exectool)
        wrapped = False
        python = CFG.get("python")
        if not self._interact:
            # absolute path is necessary to call the debugger
            cmd.append(cmd_abspath(python))
            if self._parallel:
                # see documentation of `mpi4py.run`
                cmd.extend(["-m", "mpi4py"])
        else:
            cmd.append(CFG.get("python_interactive", python))
            wrapped = CFG.get("python_interactive_is_wrapped")
            # 'python3 -m mpi4py -i' does not work
            cmd.append("-i")
        # To show executed lines with trace module:
        # import sys
        # ign = [sys.prefix, sys.exec_prefix, "$HOME/.local", os.getenv("PYTHONPATH")]
        # cmd.extend(["-m", "trace", "--trace",
        #             "--ignore-dir=" + ":".join(ign)])
        cmd.append(f'"{commfile}"')
        if wrapped:
            cmd.append("--")
        # remaining arguments are treated by code_aster script
        if self._interact:
            cmd.append("--interactive_interpreter")
        if self._test:
            cmd.append("--test")
        if self._last:
            cmd.append("--last")
        if self._savdb:
            cmd.append("--save_db")
        # copy datafiles only the first time because all share the same workdir
        if idx == 0:
            for obj in self.export.datafiles:
                cmd.append(f'--link="{obj.as_argument}"')
        cmd.extend(self.export.args)
        # TODO add pid + mode to identify the process by asrun
        return cmd

    def _coredump_analysis(self):
        """Process the coredump file."""
        core = glob("core*")
        if not core:
            return
        logger.info("\ncoredump analysis...")
        python3 = cmd_abspath(CFG.get("python"))
        if not osp.isfile(python3):
            logger.warning("'python3' not found in PATH.")
            return
        tmpf = "cmd_gdb.sh"
        with open(tmpf, "w") as fobj:
            fobj.write(os.linesep.join(["where", "quit", ""]))
        # may be required if gdb is linked against a different libpython
        bck = os.environ.pop("PYTHONHOME", None)
        cmd = ["gdb", "-batch", "-x", tmpf, "-e", python3, "-c", core[0]]
        run_command(cmd)
        if bck:
            os.environ["PYTHONHOME"] = bck

    def _get_cmdline(self, idx, commfile, timeout):
        """Build the command line.

        Arguments:
            idx (int): Index of execution.
            commfile (str): Command file name.
            timeout (float): Remaining time.

        Returns:
            list[str]: List of command line arguments.
        """
        cmd = self._get_cmdline_exec(commfile, idx)
        if self._interact:
            if not Path(self._output).exists():
                Path(self._output).touch()
        elif self._tee:
            orig = " ".join(cmd)
            if RUNASTER_PLATFORM == "linux":
                cmd = [f"( {orig} ; echo $? > {EXITCODE_FILE} )", "2>&1"]
            else:
                cmd = [f"( {orig} & echo %errorlevel% > {EXITCODE_FILE} )"]
            cmd.extend(["|", "tee", "-a", self._output])
        else:
            cmd.extend([">>", self._output, "2>&1"])
        if RUNASTER_PLATFORM == "linux":
            cmd.insert(0, f"ulimit -c unlimited ; ulimit -t {timeout:.0f} ;")
        return cmd

    def _get_status(self, exitcode):
        """Get the execution status.

        Arguments:
            exitcode (int): Return code.

        Returns:
            Status: Status object.
        """
        status = get_status(exitcode, self._output, test=self._test and self._last)
        expected = self.export.get("expected_diag", [])
        if status.diag in expected:
            logger.debug(f"Original status: {status.diag} reset to OK")
            status.state = StateOptions.Ok
            status.exitcode = 0
        # else the status unchanged
        return status

    def ending_execution(self, results_saved):
        """Post execution phase : copying results, cleanup...

        Arguments:
            results_saved (bool): *True* if execution did not abort and may have
                created results, *False* otherwise.
        """
        logger.info("TITLE Content of %s after execution:", os.getcwd())
        logger.info(_ls(".", "REPE_OUT"))
        if self._procid != self._proc0id:
            return

        results = self.export.resultfiles
        if results:
            logger.info("TITLE Copying results")
            copy_resultfiles(results, results_saved, test=self._test)

    def change_comm_file(self, comm):
        """Change a command file.

        Arguments:
            comm (str): Command file name.

        Returns:
            str: Name of the file to be executed.
        """
        with open(comm, "rb") as fobj:
            text_init = fobj.read().decode(errors="replace")
        text = text_init
        if self._chg_procdir:
            text = change_procdir(text)
        text = add_import_commands(text)
        if self._interact:
            text = stop_at_end(text, last=self._last)
        changed = text.strip() != text_init.strip()
        if changed:
            text = file_changed(text, comm)
        text = add_coding_line(text)
        if self._show_comm:
            # Normalize line endings for consistent display on Windows
            display_text = text.replace('\r\n', '\n').replace('\r', '\n')
            logger.info("\nContent of the file to execute:\n%s\n", display_text)
        if not changed:
            return comm

        filename = osp.basename(comm) + ".changed.py"
        with open(filename, "wb") as fobj:
            fobj.write(text.encode())
        return filename

    def _log_mess(self, msg):
        """Log a message into the *message* file."""
        with open(self._output, "a") as fobj:
            fobj.write(msg + "\n")


class RunOnlyEnv(RunAster):
    """Prepare a working directory for a manual execution.

    Arguments:
        export (Export): Export object defining the calculation.
    """

    _show_comm = False
    _chg_procdir = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._procid != self._proc0id:
            logger.setLevel(WARNING)

    def prepare_current_directory(self):
        """Prepare the working directory."""
        if self.export.get("step") == 0:
            super().prepare_current_directory()

    def execute_study(self):
        """Execute the study.

        Returns:
            Status: Status object.
        """
        if self.export.get("step") == 0:
            logger.info("TITLE Copy/paste these command lines:")
            profile = osp.join(RUNASTER_ROOT, "share", "aster", "profile.sh")
            timeout = self.export.get("time_limit", 0) * 1.25
            if not self._parallel:
                logger.info("    cd %s", os.getcwd())
            else:
                logger.info("    cd %s", osp.dirname(os.getcwd()))
            logger.info("    . %s", profile)
            logger.info("    ulimit -c unlimited")
            logger.info("    ulimit -t %.0f", timeout)
        return super().execute_study()

    def _exec_one(self, comm, timeout):
        """Show instructions for a command file.

        Arguments:
            comm (str): Command file name.
            timeout (float): Remaining time.
        """
        is_ok = Status(StateOptions.Ok, exitcode=0)
        if self._procid != self._proc0id:
            return is_ok

        idx = self.export.get("step")
        base_cmd = self._get_cmdline_exec("proc.0/" + comm, idx)
        if not self._parallel:
            logger.info(" ".join(base_cmd))
            return is_ok

        nbthread = self.export.get("ncpus", 1)
        _gen_cmd_file(f"cmd{idx}.sh", [" ".join(base_cmd)], nbthread)
        shell = f"cmd{idx}.sh"
        args_cmd = dict(mpi_nbcpu=self.export.get("mpi_nbcpu", 1), program="proc.0/" + shell)
        cmd = CFG.get("mpiexec").format(**args_cmd)
        logger.info("    " + cmd)

        shell = f"ddt_cmd{idx}.sh"
        _gen_ddt_template(shell, cmd, idx, nbthread)
        logger.info("Run with DDT using:")
        logger.info("    " + "proc.0/" + shell)

        return is_ok

    def ending_execution(self, _):
        """Nothing to do in this case."""


def get_procid():
    """Return the identifier of the current process.

    Returns:
        int: Process ID, -1 if a parallel version is not run under *mpiexec/srun*.
    """
    proc = run(CFG.get("mpi_get_rank"), shell=True, stdout=PIPE, universal_newlines=True)
    try:
        procid = int(proc.stdout.strip())
    except ValueError:
        procid = -1
    return procid


def get_nbcores():
    """Return the number of available cores.

    Returns:
        int: Number of cores.
    """
    return os.cpu_count()


def set_num_threads(value):
    """Define the number of threads to be used by OpenMP, MKL and OpenBLAS.

    Arguments:
        value (int): Maximum number of threads.
    """
    # openblas_set_num_threads does not work, maybe conflicts with numpy init
    # --numthreads option could be removed
    os.environ["OMP_NUM_THREADS"] = str(value)
    # mkl and openblas should used the same value if they are not defined.


def copy_datafiles(files, verbose=True):
    """Copy data files into the working directory.

    Arguments:
        files (list[File]): List of File objects.
        verbose (bool): Verbosity.
    """
    for obj in files:
        dest = None
        # fort.*
        if obj.unit != 0 or obj.filetype == "nom":
            if obj.unit in (6, 15):
                raise IndexError(
                    "Files fort.6 and fort.15 are reserved.\n"
                    "Please change unit number for: {}".format(obj.path)
                )
            dest = "fort." + str(obj.unit)
            if obj.filetype == "nom":
                dest = osp.basename(obj.path)
            # warning if file already exists
            if osp.exists(dest):
                logger.warning("%r overwrites %r", obj.path, dest)
            if obj.compr:
                dest += ".gz"
        # for directories
        else:
            if obj.filetype == "base":
                dest = osp.basename(obj.path)
            elif obj.filetype == "repe":
                dest = "REPE_IN"

        if dest is not None:
            copy(obj.path, dest, verbose=verbose)
            if obj.compr:
                dest = uncompress(dest)
            # move the bases in main directory
            if obj.filetype == "base":
                for fname in glob(osp.join(dest, "*")):
                    os.rename(fname, osp.basename(fname))
            # force the file to be writable
            make_writable(dest)


def copy_resultfiles(files, copybase, test=False):
    """Copy result files from the working directory.

    Arguments:
        files (list[File]): List of File objects.
        copybase (bool): Tell if result databases will be copied.
        test (bool, optional): *True* for a testcase, *False* for a study.
    """
    for obj in files:
        if test and obj.unit not in (6, 15):
            continue
        lsrc = []
        # fort.*
        if obj.unit != 0:
            lsrc.append("fort." + str(obj.unit))
        elif obj.filetype == "nom":
            lsrc.append(osp.basename(obj.path))
        # for directories
        else:
            if copybase and obj.filetype == "base":
                lsrc.extend(glob("glob.*"))
                lsrc.extend(glob("pick.*"))
            elif obj.filetype == "repe":
                lsrc.extend(glob(osp.join("REPE_OUT", "*")))

        for filename in lsrc:
            if not osp.exists(filename):
                logger.warning("file not found: %s", filename)
            else:
                if obj.compr:
                    filename = compress(filename)
                if obj.isdir and not osp.exists(obj.path):
                    os.makedirs(obj.path)
                dst = obj.path
                if osp.isdir(filename) and obj.filetype != "nom":
                    dst = osp.join(obj.path, osp.basename(filename))
                copy(filename, dst, verbose=True)


def _ls(*paths):
    if RUNASTER_PLATFORM == "linux":
        proc = run(["ls", "-l"] + list(paths), stdout=PIPE, universal_newlines=True)
    else:
        # Use cp850 (OEM/console codepage) which is the default for cmd.exe output
        # /N flag uses long list format without thousand separators
        proc = run(
            ["dir", "/-C"] + list(paths),
            stdout=PIPE,
            shell=True,
            encoding="cp850",
            errors="replace"
        )
    return proc.stdout


def _gen_cmd_file(filename, lines, nbthread):
    cmd = []
    cmd.append("#!/bin/bash")
    cmd.append(f"export OMP_NUM_THREADS={nbthread}")
    cmd.append("\n".join(lines))
    cmd.append("")
    with open(filename, "w") as fobj:
        fobj.write("\n".join(cmd))
    os.chmod(filename, 0o755)


def _gen_ddt_template(filename, cmd, idx, nbthread):
    redir = ">" if idx == 0 else ">>"
    with open(Path(RUNASTER_ROOT) / "share" / "aster" / "ddt_wrapper.tmpl") as ftmpl:
        script = PercTemplate(ftmpl.read()).substitute(
            command=cmd, redirect_to=redir, nbthread=nbthread
        )
    with open(filename, "w") as fobj:
        fobj.write(script)
    os.chmod(filename, 0o755)
