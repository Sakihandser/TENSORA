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
This module holds the initialization parameters.
"""

__all__ = ["rc"]


class Rc:
    """Runtime configuration options.

    Initialization:
        - If *True*, it automatically calls 'init()' when importing :py:mod:`code_aster.CA`,
        - If *False*, it does not call 'init()',
        - If *None*, to be decided.

    Restart policy:
        - If *True*, it restarts from the existing database (that must exist),
        - If *False*, it ignores any existing database and starts a new study,
        - If *None*, it restarts if a database exists, otherwise starts a new study.

    Attributes:
        initialize (bool): Automatic MPI initialization at import (default: None).
        restart (bool): Restart policy (default: None)
    """

    initialize = None
    restart = None

    def __init__(self, **kwargs):
        self(**kwargs)

    def __call__(self, **kwargs):
        for key in kwargs:
            if not hasattr(self, key):
                raise TypeError("unexpected argument '{0}'".format(key))
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self):
        return "<{0}.rc>".format(__name__)


rc = Rc()
