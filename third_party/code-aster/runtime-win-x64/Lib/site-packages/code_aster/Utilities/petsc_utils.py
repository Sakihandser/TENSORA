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
This module gives common utilities for PETSc.
"""

from libaster import petscFinalize, petscInitialize

from ..Utilities import PETSc


def removePETScOptions(options):
    """Remove the options from PETSc's options database

    Arguments:
        options[str]: PETSc options
    """
    OptDB = PETSc.Options()
    loc_opt = [t for t in options.split(" ") if t.startswith("-")]
    [OptDB.delValue(opt) for opt in loc_opt]
