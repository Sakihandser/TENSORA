# coding: utf-8
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
:py:mod:`searchlist` --- General purpose utilities for search lists
*******************************************************************

This modules gives some basic utilities for search lists.
"""

import numpy as np


class SearchList:
    @property
    def values(self):
        """Attribute that holds the list values.

        Returns:
            list[float|int]: List of values
        """
        return self._values

    @property
    def precision(self):
        """Attribute that holds the search precision.

        Returns:
            float: The search precision
        """
        return self._precision

    @precision.setter
    def precision(self, value):
        prec = np.finfo(float).eps
        if not value >= prec:
            raise ValueError(f"Invalid precision value {value}")
        self._precision = value

    @property
    def criterion(self):
        """Attribute that holds the search criterion.

        Returns:
            str: The search criterion, RELATIF | ABSOLU
        """
        return self._criterion

    @criterion.setter
    def criterion(self, value):
        expected = ("RELATIF", "ABSOLU")
        if value not in expected:
            raise ValueError(f"Criterion '{value}' is not in {expected}")
        self._criterion = value

    def __repr__(self):
        return f"[{' '.join(map(str, self._values))}]"

    def __iter__(self):
        yield from self._values

    def __init__(self, values, precision=1.0e-6, criterion="RELATIF"):
        """Initialization of the Search List

        Arguments:
            values (list[float|int]): The list of values for search
            precision (float): The search precision
            criterion (str): The search criterion ( ABSOLU|RELATIF )
        """

        assert len(values) >= 1
        assert all(np.isreal(values))
        self._values = np.array(values)
        self.precision = precision
        self.criterion = criterion

    def _get_bounds(self, value):
        """
        Get bounds of value considering precision and criterion
        """
        assert np.isreal(value), value

        if self.criterion == "RELATIF":
            min_v = value * (1 - self.precision)
            max_v = value * (1 + self.precision)
        else:
            min_v = value - self.precision
            max_v = value + self.precision

        return sorted((min_v, max_v))

    def _search_candidates(self, value):
        """
        Search indexes of value matching the defined criterion
        """
        min_v, max_v = self._get_bounds(value)
        return np.flatnonzero(np.logical_and(self._values >= min_v, self._values <= max_v))

    def __contains__(self, value):
        idx = self._search_candidates(value)
        return len(idx) > 0

    def unique(self, value):
        """
        Return True if value is unique
        """
        idx = self._search_candidates(value)
        return len(idx) == 1

    def assertAllUnique(self):
        """
        Assert if all the values are unique
        """
        if not all(self.unique(i) for i in self):
            raise ValueError(f"List values are not unique {self.values}")

    def index(self, value):
        """
        Return index of value if value is unique
        """
        idx = self._search_candidates(value)
        if len(idx) == 0:
            raise ValueError(f"{value} is not in list")
        if len(idx) > 1:
            values = [self._values[i] for i in idx]
            raise IndexError(f"{value} is not unique in list: {values} at indexes {idx}")
        else:
            return idx[0]
