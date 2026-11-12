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
This module provides a low level interface to the most of the code_aster objects.

.. code-block:: python

    >>> import code_aster
    >>> # 'code_aster.rc' object is available for customization.
    >>> # the following line automatically starts 'init()':
    >>> from code_aster import CA
    >>> # 'CA' provides all user objects and commands.

In a standard commands file, without advanced Python usage:

.. code-block:: python

    >>> import code_aster
    >>> from code_aster.Commands import *
"""

import atexit
import os
from functools import partial
from pathlib import Path

from .Utilities.rc import rc

if rc.initialize is None:
    rc.initialize = True

from .CodeCommands import *
from .CodeCommands.debut import init
from .CodeCommands.fin import close
from .Objects import *
from .ObjectsExt import DataStructure
from .Supervis import (
    AsterError,
    ContactError,
    ConvergenceError,
    IntegrationError,
    SolverError,
    TimeLimitError,
    saveObjects,
)
from .Utilities import MPI, TestCase, disable_fpe
from .Utilities.version import __version__

basedir = Path(os.environ.get("RUNASTER_CA_BASEDIR", "."))

if rc.initialize:
    init()

exit = partial(close, exit=True)

# objects can not be automatically saved during automatic exit
atexit.register(partial(close, atexit=True))

del atexit
del os
del partial
del Path
