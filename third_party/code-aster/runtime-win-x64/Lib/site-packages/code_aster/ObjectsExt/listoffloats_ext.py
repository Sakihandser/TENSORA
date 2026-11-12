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
:py:class:`ListOfFloats` --- List of floats
*******************************************

This object stores a list of floats. A *numpy* object can be retrieved using
:py:func:`ListOfFloats.getValuesAsArray`.

For convenience, you can use on this object the same methods than on a *numpy*
array.
"""

import numpy as np

from libaster import ListOfFloats

from ..Utilities import injector


@injector(ListOfFloats)
class ExtendedListOfFloats:
    cata_sdj = "SD.sd_listr8.sd_listr8"

    def __getattr__(self, attr):
        """Returns the attribute of the underlying :py:class:`numpy.array`
        object if it does not exist."""
        if attr in ("__getstate__", "__setstate__"):
            raise AttributeError("'ListOfFloats' object has no attribute '{0}'".format(attr))
        return getattr(np.array(self.getValues()), attr)

    def __len__(self):
        """Returns the number of values in the list.

        Returns:
            int: Number of values.
        """
        return self.size

    def getValuesAsArray(self):
        """Returns the values as a :py:class:`numpy.array`.

        Returns:
            list: The :py:class:`numpy.array` containing the values (by
                reference).
        """
        return np.array(self.getValues())
