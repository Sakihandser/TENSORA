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
:py:mod:`rootdir` --- Utilities
-----------------------------

This module provides convenient utilities for files manipulation,
system command execution, templates...
"""

__all__ = ("RUNASTER_ROOT", "RUNASTER_PLATFORM")

import os
from pathlib import Path


# Installation root is defined by launcher script or relatively to this file.
# It supports lib/pythonX.Y/site-packages or lib/aster installations.
def _set_root():
    path = os.environ.get("RUNASTER_ROOT")
    if path:
        return path
    path = Path(__file__).absolute()
    is_windows = os.name == "nt"
    # Windows' conda layout splits python (<prefix>\Lib\site-packages) from
    # compiled libraries/data (<prefix>\Library\{bin,lib,share}); "lib" (the
    # POSIX site-packages ancestor) never appears on this file's path at all
    # -- it is "Lib" here, a sibling of "Library", not an ancestor of it.
    # Without this, the comparison below never matches on Windows and the
    # loop silently walks all the way up to the drive root instead.
    target = "Lib" if is_windows else "lib"
    while path != path.parent and path.name != target:
        path = path.parent
    root = path.parent
    return str(root / "Library") if is_windows else str(root)


RUNASTER_ROOT = _set_root()
RUNASTER_PLATFORM = "linux" if os.name != "nt" else "win"
