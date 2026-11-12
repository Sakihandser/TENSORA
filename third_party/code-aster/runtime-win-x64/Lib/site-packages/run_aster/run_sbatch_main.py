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
``bin/run_sbatch`` --- Script to execute code_aster using ``sbatch``
--------------------------------------------------------------------

``bin/run_sbatch`` executes code_aster using ``sbatch``.

Usage:

.. code-block:: sh

    bin/run_sbatch [sbatch-options] FILE.export

`sbatch-options` are passed to ``sbatch``.

See ``bin/run_sbatch --help`` for the available options.

"""

import argparse
import os
import os.path as osp
import stat
import sys
import tempfile
from math import ceil
from pathlib import Path
from subprocess import run
from typing import Any

from .base_params import RUNASTER_ROOT
from .config import CFG
from .export import Export
from .logger import logger

USAGE = """
    run_sbatch [sbatch-options] FILE.export

This script simply wraps the execution of a study with sbatch:

    sbatch <options from export> .../bin/run_aster FILE.export

'sbatch-options' are passed to 'sbatch' before those deduced from the .export file.
Use 'sbatch --help' for details and example below.
"""

EPILOG = """Example:
    run_sbatch --wckey=p10wb:aster --partition=bm FILE.export
or:
    export SBATCH_WCKEY=p10wb:aster
    export SBATCH_PARTITION=bm
    run_sbatch FILE.export
"""

HEADER = """#!/bin/bash
# + passed on command line: {sbatch_args}

#SBATCH --job-name={name}

# number of nodes
#SBATCH --nodes={mpi_nbnodes}

# number of MPI processes
#SBATCH --ntasks={mpi_nbcpu}

# number of threads per MPI process
#SBATCH --cpus-per-task={nbthreads} --threads-per-core=1

# max walltime
#SBATCH --time="00:00:{time_limit}"

# memory in MB
#SBATCH --mem={memory_node}M

# add `--exclusive` if several nodes, define `--partition=...`
#SBATCH {options}

# redirect output in the current directory
#SBATCH --output={output}
#SBATCH --error={output}.stderr
"""
COMMAND = """
{RUNASTER_ROOT}/bin/run_aster {run_aster_options} {study}
"""

HEADER_S3SP = """
# arguments for s3 slurm splugin
#SBATCH --s3sp-enable
#SBATCH --s3sp-search-dir={scratch_dir}/.spank
#SBATCH --s3sp-file-list=%j.output
"""
COMMAND_S3SP = """
SPDIR={scratch_dir}/.spank
fcap=${{SPDIR}}/${{SLURM_JOBID}}.output
ftmp=${{SPDIR}}/${{SLURM_JOBID}}.tmp.txt
mkdir -p ${{SPDIR}}

{RUNASTER_ROOT}/bin/run_aster {run_aster_options} {study} | tee ${{ftmp}}

{RUNASTER_ROOT}/share/aster/run_aster_extract -o ${{fcap}} ${{ftmp}}

echo "+ cleaning old files from ${{SPDIR}}..."
find ${{SPDIR}} -type f -mmin +240 -print -delete
rm -f ${{ftmp}}
"""


def parse_args(argv: list[str]):
    """Parse command line arguments.

    Arguments:
        argv (list): List of command line arguments.
    """
    parser = argparse.ArgumentParser(
        usage=USAGE,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        allow_abbrev=False,
    )
    parser.add_argument(
        "-n", "--dry-run", action="store_true", help="do not execute, just show the script content"
    )
    parser.add_argument(
        "--output",
        action="store",
        type=Path,
        help="output file (default: <export filename>-%%j.txt)",
    )
    parser.add_argument(
        "--run_aster_option",
        dest="opts",
        action="append",
        default=[],
        help="option to be passed to run_aster, can be repeated "
        "(example: --run_aster_option='--only-proc0')",
    )
    parser.add_argument(
        "--ctest",
        dest="opts",
        action="append_const",
        const="--ctest",
        help="shortcut for --run_aster_option='--ctest'",
    )
    parser.add_argument(
        "--time_limit",
        dest="time_limit",
        type=float,
        action="store",
        default=None,
        help="override the time limit in seconds",
    )
    parser.add_argument(
        "--memory_limit",
        dest="memory_limit",
        type=float,
        action="store",
        default=None,
        help="override the memory limit in MB",
    )
    parser.add_argument(
        "file", metavar="FILE.export", help="Export file (.export) defining the calculation."
    )

    args, others = parser.parse_known_args(argv)
    return args, others


def _run(cmd: list[str]):
    logger.debug("execute: %s", " ".join(cmd))
    return run(cmd)


class SlurmJob:
    """This object represents the setup of a Slurm job."""

    _params = _args = _template = None

    def __init__(self):
        self._params = {}
        self._args = []
        self._template = HEADER + COMMAND

    def set(self, key: str, value: Any):
        """Set the value of a parameter."""
        self._params[key] = value

    def update(self, values: dict):
        """Update parameters values from a dict."""
        self._params.update(values)

    def get(self, key: str) -> Any:
        """Get the value of a parameter."""
        return self._params[key]

    def check_parameters(self):
        """Check parameters consistency."""
        params = self._params
        nbnodes = params["mpi_nbnodes"]
        cpu_per_node = ceil(params["mpi_nbcpu"] / nbnodes)
        params["memory_node"] = int(cpu_per_node * params["memory_limit"])
        params["time_limit"] = int(params["time_limit"])
        if nbnodes > 1 or cpu_per_node >= 16 or "exclusive" in params["testlist"]:
            params["options"] += " --exclusive"
        if "bm" in params["testlist"]:
            params["options"] += " --partition=bm"
        self.check_s3sp()

    def check_s3sp(self):
        """Setup for S3 Slurm Plugin."""
        # check if the plugin is installed within this version
        # and if it is not disabled with the ASTER_S3SP environment variable (=0).
        is_enabled = CFG.get("use_s3sp") and os.environ.get("ASTER_S3SP", "1") != "0"
        if not is_enabled:
            return
        self._template = HEADER + HEADER_S3SP + COMMAND_S3SP

    def render(self) -> str:
        """Render the template with the job parameters."""
        logger.debug("Parameters: %s", self._params)
        return self._template.format(**self._params)

    def submit(self, dry_run: bool = False) -> int:
        """Submit the job and return the exit code."""
        content = self.render()
        with tempfile.NamedTemporaryFile(
            prefix="batch", suffix=".sh", mode="w", delete=False
        ) as fobj:
            fobj.write(content)
            script = fobj.name

        logger.info("+ submitted script:\n%s", content)
        os.chmod(script, stat.S_IRWXU)
        if dry_run:
            logger.info("+ filename: %s", script)
            return 0
        self._params["output"].parent.mkdir(parents=True, exist_ok=True)
        with open(str(self._params["output"]).replace("-%j", "") + ".sbatch", "w") as fscr:
            logger.info("+ filename: %s", fscr.name)
            fscr.write(content)
        try:
            proc = _run(["sbatch"] + self._params["sbatch_args"] + [script])
        finally:
            os.remove(script)
        return proc.returncode


def main(argv=None):
    """Entry point for sbatch wrapper.

    Arguments:
        argv (list): List of command line arguments.
    """
    args, sbatch_args = parse_args(argv or sys.argv[1:])

    export = Export(args.file)

    # initialized with default values
    addmem = CFG.get("addmem", 0.0)
    memory = args.memory_limit or export.get("memory_limit", 16384)
    memory += addmem
    if args.time_limit:
        args.opts.append(f"--time_limit={args.time_limit}")
    if args.memory_limit:
        args.opts.append(f"--memory_limit={args.memory_limit}")

    job = SlurmJob()
    job.update(
        {
            "name": osp.splitext(osp.basename(args.file))[0],
            "mpi_nbcpu": export.get("mpi_nbcpu", 1),
            "mpi_nbnodes": export.get("mpi_nbnoeud", 1),
            "nbthreads": export.get("ncpus", 1),
            "time_limit": args.time_limit or export.get("time_limit", 3600),
            "memory_limit": memory,
            "memory_node": None,
            "options": "",
            "study": args.file,
            "run_aster_options": " ".join(args.opts),
            "RUNASTER_ROOT": RUNASTER_ROOT,
            "testlist": export.get("testlist", []),
            "sbatch_args": sbatch_args,
            "scratch_dir": os.environ.get("SCRATCHDIR", "/tmp"),
        }
    )
    job.set("output", args.output or Path(job.get("name") + "-%j.txt"))
    job.check_parameters()

    exitcode = job.submit(args.dry_run)
    return exitcode


if __name__ == "__main__":
    sys.exit(main())
