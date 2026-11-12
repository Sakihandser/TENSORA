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
:py:mod:`interpolatelist` --- General purpose utilities for search lists
*******************************************************************

This modules gives some basic utilities for search lists.
"""

import numpy as np
from .searchlist import SearchList


class InterpolateList(SearchList):
    @property
    def left(self):
        """Attribute that holds the left extrapolation.

        Returns:
            str: The extrapolation left, EXCLU | CONSTANT | LINEAIRE
        """
        return self._left

    @left.setter
    def left(self, value):
        expected = ("EXCLU", "CONSTANT", "LINEAIRE")
        if value not in expected:
            raise ValueError(f"Left '{value}' is not in {expected}")
        self._left = value

    @property
    def right(self):
        """Attribute that holds the right extrapolation.

        Returns:
            str: The extrapolation right, EXCLU | CONSTANT | LINEAIRE
        """
        return self._right

    @right.setter
    def right(self, value):
        expected = ("EXCLU", "CONSTANT", "LINEAIRE")
        if value not in expected:
            raise ValueError(f"Right '{value}' is not in {expected}")
        self._right = value

    def __init__(self, values, left="EXCLU", right="EXCLU", precision=1.0e-6, criterion="RELATIF"):
        """Initialization of the Interpolation List

        Arguments:
            values (list[float|int]): The list of values for interpolation
            left (str): The left extrapolation criterion ( EXCLU | CONSTANT | LINEAIRE )
            right (str): The left extrapolation criterion ( EXCLU | CONSTANT | LINEAIRE )
            precision (float): The search precision
            criterion (str): The search criterion ( ABSOLU|RELATIF )
        """
        assert len(values) >= 2
        super().__init__(values, precision, criterion)
        self.left = left
        self.right = right

    def assertInclude(self, value):
        """
        Assert value is inside the interpolation range
        """
        self.assertAllUnique()
        min_v, _ = self._get_bounds(min(self.values))
        _, max_v = self._get_bounds(max(self.values))

        included_left = value >= min_v or self.left != "EXCLU"
        included_right = value <= max_v or self.right != "EXCLU"

        if not (included_left and included_right):
            msg = f"{value} is not included in the list range"
            raise ValueError(msg)
