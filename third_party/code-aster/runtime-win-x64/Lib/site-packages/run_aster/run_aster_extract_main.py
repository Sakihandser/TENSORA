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
``bin/run_aster_extract`` --- Extract some informations from a batch execution
------------------------------------------------------------------------------

``bin/run_aster_extract`` extracts some informations from the output file
of a code_aster execution.

Usage:

.. code-block:: sh

    bin/run_aster_extract -o output-file input-file

"""

import argparse
import getpass
import re
import sys
from functools import wraps
from pathlib import Path
from time import time
from .config import CFG

USAGE = """
    run_aster_extract -o output-file input-file

This script extracts some informations from 'input-file' and writes the
extracted/filtered lines into 'output-file'.

"""

MB = 1024 * 1024
# estimated compression ratio (from tests outputs of the 'exclusive' list)
RATIO = 15
# maximum target size of the compressed file
MAXSIZE = 10 * MB


def parse_args(argv: list[str]):
    """Parse command line arguments.

    Arguments:
        argv (list): List of command line arguments.
    """
    parser = argparse.ArgumentParser(
        usage=USAGE, formatter_class=argparse.RawDescriptionHelpFormatter, allow_abbrev=False
    )
    parser.add_argument("-o", "--output", action="store", type=Path, help="output file")
    parser.add_argument(
        "--fmt",
        action="store",
        type=str,
        default="srun" if CFG.get("use_srun") else "ompi",
        help="MPI pattern to be used ('ompi' or 'srun').",
    )
    parser.add_argument("file", metavar="FILE", type=Path, help="input file")
    args = parser.parse_args(argv)
    if not args.output:
        parser.error("'--output' option is required")
    if args.fmt not in ("ompi", "srun"):
        parser.error("only 'ompi' and 'srun' are supported")
    return args


def stats(func):
    """show statistics"""

    @wraps(func)
    def wrapper(inst, *args, **kwds):
        """wrapper"""
        start = time()
        try:
            return func(inst, *args, **kwds)
        finally:
            dt = (time() - start) * 1000.0
            size = len(inst.content)
            print(f"{func.__name__}: {dt:.3f} ms, {size} bytes")

    return wrapper


class Filter:
    """Class that applies filters on an output file."""

    def __init__(self, fmt: str):
        self.content: str = ""
        assert fmt in ("ompi", "srun"), fmt
        self.fmt = fmt

    @stats
    def read(self, filename: Path):
        """Read the file content"""
        with open(filename, "r", errors="ignore") as fobj:
            self.content = fobj.read()

    @stats
    def write(self, filename: Path):
        filename.write_text(self.content)

    def run(self):
        """Do extraction"""
        self.proc0_only()
        self.truncate()
        self.anonymize()

    @stats
    def truncate(self):
        """Truncate the file to the target size (as soon as possible)"""
        self.content = self.content[: RATIO * MAXSIZE]

    @stats
    def anonymize(self):
        """Remove username"""
        username = getpass.getuser()
        expr = re.compile(re.escape(username), re.I)
        self.content = expr.sub("x" * len(username), self.content)

    @stats
    def proc0_only(self):
        """Keep only lines from proc #0"""
        if self.fmt == "srun":
            expr = re.compile(r"^ *0:[ ]?|^(?! *\d+:[ ]?)")
        else:
            expr = re.compile(r"^ *\[1,0\]<stdout>:|^(?! *\[1,\d+\]<stdout>:)")

        lines = [line for line in self.content.splitlines() if expr.search(line)]
        lines = [expr.sub("", line) for line in lines]
        self.content = "\n".join(lines)


def main(argv=None):
    """Entry point for extraction script.

    Arguments:
        argv (list): List of command line arguments.
    """
    args = parse_args(argv or sys.argv[1:])
    extr = Filter(args.fmt)
    extr.read(args.file)
    extr.run()
    extr.write(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
