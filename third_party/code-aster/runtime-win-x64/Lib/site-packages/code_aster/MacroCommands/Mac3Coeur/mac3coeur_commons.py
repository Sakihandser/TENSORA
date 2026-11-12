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


import numpy as np
from collections import OrderedDict
from ...Utilities import force_list

MAC3_ROUND = 14


class CollectionMAC3:
    @property
    def size(self):
        return len(self._collection)

    @property
    def keys(self):
        return list(self._collection.keys())

    def __init__(self, label):
        self._collection = OrderedDict()
        self.label = label

    def __getitem__(self, key):
        return self._collection[key]

    def __setitem__(self, key, item):
        self._collection[key] = item

    def __iter__(self):
        yield from self._collection.values()

    def items(self):
        return self._collection.items()

    def filter(self, keys):
        """
        Get all items with key matching args
        """
        return tuple(
            item
            for key, item in self._collection.items()
            if any(w in key for w in force_list(keys))
        )


def flat_list(list_of_list):
    return [item for element in list_of_list for item in element]


def get_first_digit(spline):

    digit = 0
    for i, v in enumerate(spline):
        try:
            float(v)
            digit = i
            break
        except ValueError:
            continue

    return digit


def check_centers_and_size(z, ep, s):
    """
    Up to THYC 5.5 the vector Ep(m) is wrong by a shift of 1.
    This function is to check the accordance between Z and Ep

    If returns True using s = 0 the THYC file is OK
    If returns True using s = 1 the THYC file is affected by the bug
    If returns False using both s = O and 1 the THYC file is corrupted for un unknown reason
    """
    assert s in (0, 1)
    assert len(z) == len(ep)
    return all(
        abs(z[i + s] - z[i + 1 + s] + 0.5 * (ep[i] + ep[i + 1])) < 1.0e-5
        for i in range(len(z) - 1 - s)
    )


def check_contiguous(arr):
    return all(arr[i + 1] == arr[i] + 1 for i in range(len(arr) - 1))


def find_nearest_idx(value, array, bounds=None):

    array = np.asarray(array)

    if bounds is None:
        diff = np.abs(array - value)
        idx = diff.argmin()
    else:
        bmax = array + bounds / 2
        bmin = array - bounds / 2
        condition = np.logical_and(value > bmin, value < bmax)
        assert np.count_nonzero(condition) == 1
        idx = condition.argmax()

    return idx
