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
:py:mod:`utils` --- Utilities
-----------------------------

This module provides convenient utilities for files manipulation,
system command execution, templates...
"""

__all__ = ("RUNASTER_ROOT", "RUNASTER_PLATFORM", "RUNASTER_COPYMODE")

import gzip
import os
import os.path as osp
import shutil
import stat
from glob import glob
from pathlib import Path
from string import Template
from subprocess import run

try:
    from os import waitstatus_to_exitcode
except ImportError:
    pass

from .base_params import RUNASTER_PLATFORM, RUNASTER_ROOT
from .config import CFG
from .logger import logger

RUNASTER_COPYMODE = CFG.get("copymode", "shutil")


def copy(src, dst, verbose=False):
    """Copy the file or directory `src` to the file or directory `dst`.
    If `src` is a file, `dst` can be an existing directory or the destination
    file name.
    If `src` is a directory and `dst` is an existing directory, the files
    will be copied into `dst`.
    Parent directory of `dst` is created if necessary.

    If `dst` specifies a directory, the files will be copied into `dst` using
    the base filenames from `src`.

    Arguments:
        src (str): File or directory to be copied.
        dst (str): Destination.
        verbose (bool): Verbosity.
    """
    if verbose:
        logger.info("copying (%s) %r to %r...", RUNASTER_COPYMODE, src, dst)
    pardst = osp.dirname(osp.abspath(dst))
    if not osp.exists(pardst):
        os.makedirs(pardst)
    if osp.isfile(src):
        _copyfile(src, dst)
    else:
        if not osp.isdir(dst):
            _copydir(src, dst)
        else:
            for fname in os.listdir(src):
                if osp.isdir(osp.join(src, fname)):
                    copy(osp.join(src, fname), osp.join(dst, osp.basename(fname)), verbose=verbose)
                else:
                    copy(osp.join(src, fname), dst, verbose=verbose)


def _copyfile(src, dst):
    logger.debug("copyfile: %r to %r", src, dst)
    if RUNASTER_COPYMODE != "rsync":
        return shutil.copy2(src, dst)
    _copydir(src, dst, filemode=True)


def _copydir(src: Path, dst: Path, filemode: bool = False):
    logger.debug("copydir (filemode=%r): %r to %r", filemode, src, dst)
    if RUNASTER_COPYMODE != "rsync":
        return shutil.copytree(src, dst)
    if not filemode:
        # man rsync: "copy to a different name"
        src = str(src) + "/"
        dst = str(dst) + "/"
    # TODO check for supported algorithm
    cmd = ["rsync", "-a", "--checksum", str(src), str(dst)]
    logger.debug("copy: %r", cmd)
    proc = run(cmd)
    iret = proc.returncode
    if iret != 0:
        logger.error("%s exited with code %d", RUNASTER_COPYMODE, iret)


def compress(path, verbose=False):
    """Compress a file or the content of a directory.

    Arguments:
        path (str): File or directory path.
        verbose (bool): Verbosity.
    """
    if osp.isfile(path):
        dest = path + ".gz"
        files = [path]
    else:
        dest = path
        files = glob(osp.join(path, "*"))
    for fname in files:
        if verbose:
            tail = fname if len(fname) < 60 else "[...]" + fname[-60:]
            logger.info("compressing %r...", tail)
        with open(fname, "rb") as f_in:
            with gzip.open(fname + ".gz", "wb", compresslevel=6) as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(fname)
    return dest


def uncompress(path, verbose=False):
    """Decompress a file or the content of a directory.

    Arguments:
        path (str): File or directory path.
        verbose (bool): Verbosity.
    """
    if osp.isfile(path):
        dest = path.rstrip(".gz")
        files = [path]
    else:
        dest = path
        files = glob(osp.join(path, "*.gz"))
    for fname in files:
        if verbose:
            tail = fname if len(fname) < 60 else "[...]" + fname[-60:]
            logger.info("decompressing %r...", tail)
        with gzip.open(fname, "rb") as f_in:
            ungz = fname[:-3] if fname.endswith(".gz") else fname
            with open(ungz, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(fname)
    return dest


def make_writable(filename):
    """Force a file to be writable by the current user.

    Arguments:
        filename (str): File name.
    """
    os.chmod(filename, os.stat(filename).st_mode | stat.S_IWUSR)


def run_command(cmd, exitcode_file=None):
    """Execute a command and duplicate output to `logfile`.

    Arguments:
        cmd (list): Command line arguments.
        exitcode_file (str, optional): Read exit code from this file if
            it exists.

    Returns:
        int: exit code.
    """
    # previous revisions used `subprocess.run` but IntelMPI mpiexec does not
    # support the way the process is forked.
    if RUNASTER_PLATFORM == "win" and len(" ".join(cmd)) > 8191:
        # https://learn.microsoft.com/en-us/troubleshoot/windows-client/shell-experience/command-line-string-limitation
        logger.error("command too long to be executed")
        return 4
    iret = os.system(" ".join(cmd))
    iret = waitstatus_to_exitcode(iret)
    if exitcode_file and osp.isfile(exitcode_file):
        with open(exitcode_file) as fexit:
            iret = int(fexit.read() or 1)
        os.remove(exitcode_file)
    return iret


def _waitstatus_to_exitcode(status):
    """Replacement for `waitstatus_to_exitcode` function added in Python 3.9.

    Arguments:
        status (int): status as returned by `os.wait()`/`os.waitpid()`.

    Returns:
        int: exit code.
    """
    if RUNASTER_PLATFORM == "win":
        # os.system() on Windows returns the child's exit code directly (see the
        # comment on the assignment below), not a Unix-style wait status, so it
        # must NOT be shifted: >> 8 turned every code below 256 into 0, i.e. a
        # failed execution reported as success whenever no exitcode file was
        # written.
        return status
    if os.WIFSIGNALED(status):
        returncode = -os.WTERMSIG(status)
    elif os.WIFEXITED(status):
        returncode = os.WEXITSTATUS(status)
    elif os.WIFSTOPPED(status):
        returncode = -os.WSTOPSIG(status)
    else:
        returncode = 15
    return returncode


# On Windows, always use the custom implementation because os.system() returns
# the exit code directly, not a Unix-style wait status. The built-in
# waitstatus_to_exitcode (Python 3.9+) expects Unix wait status and fails on Windows.
if not hasattr(os, "waitstatus_to_exitcode") or RUNASTER_PLATFORM == "win":
    waitstatus_to_exitcode = _waitstatus_to_exitcode


def cmd_abspath(prog):
    """Return the absolute path of a program as found in PATH.

    If `prog` contains a '/', it is returned unchanged.

    Arguments:
        prog (str): Executable or script.

    Returns:
        str: Absolute path to run `prog`.
    """
    if os.sep not in prog:
        for path in os.getenv("PATH").split(os.pathsep):
            if osp.isfile(osp.join(path, prog)):
                if RUNASTER_PLATFORM == "win":
                    path = path.replace(" ", '" "')
                prog = osp.join(path, prog)
                break
    return prog


class PercTemplate(Template):
    """Template with '%' as delimiter."""

    delimiter = "%"
