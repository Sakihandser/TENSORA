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
This module gives common utilities.

No external import of other :py:mod:`code_aster` packages.
"""

from .as_timer import Timer
from .base_utils import (
    ReadOnlyDict,
    Singleton,
    accept_array,
    array_to_list,
    cmp,
    config,
    force_list,
    force_tuple,
    get_caller_context,
    import_object,
    is_complex,
    is_float,
    is_float_or_int,
    is_int,
    is_number,
    is_sequence,
    is_str,
    no_new_attributes,
    value_is_sequence,
    version_info,
)
from .compatibility import (
    compat_listr8,
    deprecate,
    deprecated,
    remove_keyword,
    required,
    unsupported,
)
from .ExecutionParameter import ExecutionParameter, disable_fpe
from .general import initial_context
from .i18n import localization
from .i18n import translate as _
from .import_helper import ParaMEDMEM, PETSc, SLEPc, medcoupling, sympy
from .injector import injector
from .interpolatelist import InterpolateList
from .logger import DEBUG, ERROR, INFO, WARNING, logger, loglevel, with_loglevel
from .misc import SharedTmpdir, get_shared_tmpdir, shared_tmpdir
from .mpi_utils import MPI, haveMPI, useHPCMode
from .options import Options
from .petsc_utils import petscFinalize, petscInitialize, removePETScOptions
from .report import CR
from .searchlist import SearchList
from .statistics_manager import print_stats, profile, reset_stats
from .strfunc import (
    center,
    clean_string,
    convert,
    copy_text_to,
    cut_long_lines,
    from_unicode,
    get_encoding,
    maximize_lines,
    textbox,
    to_unicode,
    ufmt,
)
from .Tester import TestCase
from .transpose import transpose
from .version import get_version, get_version_desc
