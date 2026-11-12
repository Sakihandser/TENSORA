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
:py:mod:`toolbox` --- Toolbox for the developers
------------------------------------------------
"""

import pathlib
import re
from .config import CFG
from .utils import run_command
import os

def make_shared(lib, src, *args):
    """Build a shared library from a fortran source file.

    Arguments:
        lib (str): Result library.
        src (str): Fortran source file.
        args (list[str]): Optional arguments passed to the linker.

    Returns:
        int: exit code.
    """
    fc = CFG.get("FC")
    fcp = pathlib.Path(fc)
    if not fcp.exists():
        fcp = pathlib.Path(os.getenv("FC") or fc)
    cmd = [fcp.as_posix()]
    cmd.extend(CFG.get("FCFLAGS"))
    if os.name == "nt":
        # ifx: build a DLL and export the Fortran routines explicitly, as
        # dll_umat.c resolves them with GetProcAddress (e.g. 'umat_')
        names = re.findall(
            r"^[^!c*\n][^!\n]*?\b(?:subroutine|function)\s+(\w+)",
            pathlib.Path(src).read_text(errors="replace"),
            re.I | re.M,
        )
        cmd.extend(["/dll", f"/Fe:{lib}", src, "/link"])
        cmd.extend(f"/EXPORT:{name.lower()}_" for name in dict.fromkeys(names))
    else:
        cmd.extend(["-shared", "-o", lib, src])
    cmd.extend(args)
    print("INFO make_shared command line:", " ".join(cmd))
    return run_command(cmd)
