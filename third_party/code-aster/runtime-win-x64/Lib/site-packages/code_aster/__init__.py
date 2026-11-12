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
This is the main entry point for the users.

:py:mod:`code_aster.Commands` is the high level user interface.
It provides the *Commands*.

:py:mod:`code_aster.CA` is a lower level interface that gives access the
*DataStructure* objects (and also *Commands* for convenience).

Standard users should use the high level interface:

.. code-block:: python

    >>> import code_aster
    >>> from code_aster.Commands import *
    >>> DEBUT()
    >>> mesh = LIRE_MAILLAGE(...)

Note::
    The first two lines that import :py:mod:`code_aster` and all commands from
    :py:mod:`code_aster.Commands` are automatically inserted in the user commands
    file by `run_aster`.

The lower level user interface is used as:

.. code-block:: python

    >>> import code_aster
    >>> from code_aster import CA
    >>> mesh = CA.Mesh()
    >>> mesh.readMedFile(...)

See :py:mod:`code_aster.rc` object to adjust the initialization parameters.

Here is the diagram of the packages organization:

.. image:: ../../img/diagr_code_aster.svg
   :align: center

"""

__all__ = ("libaster", "rc", "__version__")

# image generated with:
#   diagr_import --pkg --grp -g doc/img/diagr_code_aster.svg \
#       code_aster/**/*.py

# importing cmath may raise a fpe, maybe due to mkl...
import cmath
import os
import sys

python_version = sys.version_info

if sys.platform == "win32" and python_version >= (3, 8):
    # On Windows, we need to ensure that the DLLs are found, from Python 3.8 we need to
    # use os.add_dll_directory to add the directory containing the DLLs.
    # Add the directory of the current script to the DLL search path
    # This is necessary for Python 3.8+ on Windows to find the DLLs.
    # To simplify we use the LD_LIBRARY_PATH environment variable like on Unix systems.
    ld_library_path = os.getenv("LD_LIBRARY_PATH", "")
    if ld_library_path:
        # Split the LD_LIBRARY_PATH and add each directory
        for path in ld_library_path.split(os.pathsep):
            print("Adding directory:", path)
            if os.path.isdir(path):
                print(os.add_dll_directory(os.path.abspath(path)))

try:
    # embedded modules must be imported before libaster
    # because there are set up by initAsterModules
    import aster
    import aster_core
    import aster_fonctions
    import libaster

    # setup, do not keep references here...
    del aster, aster_core, aster_fonctions, libaster

    # ... except for rc and package info
    from .Utilities.rc import rc
    from .Utilities.version import __version__
except ImportError:
    # AsterStudy only uses code_aster/Cata without the extensions modules (.so).
    # So, the exception is only raised during the building process.
    if os.environ.get("WAFLOCK"):
        raise

del cmath, os
