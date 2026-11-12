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
:py:mod:`general` --- Definition of utilities for general purpose
*****************************************************************
"""

import builtins
import math
import random


# This function exists in AsterStudy - keep consistency.
def initial_context():
    """Returns *initial* Python context used for evalutations of formula.

    Returns:
        dict: pairs of name per corresponding Python instance.
    """
    context = {}
    context.update(builtins.__dict__)
    for func in dir(math):
        if not func.startswith("_"):
            context[func] = getattr(math, func)
    return context


class Random:
    """Wrapper on random functions to be called from fortran operator."""

    _random = None

    @classmethod
    def initialize(cls, jump=0):
        """Initialize the generator of random numbers.

        Arguments:
            jump (int): Non-negative integer to change the state of the
                numbers generator.
        """
        cls._random = random.Random(100)
        gen = cls._random
        gen.seed(jump)

    @classmethod
    def get_number(cls):
        """Returns a random number between 0 and 1.

        Returns:
            float: Random number.
        """
        if not cls._random:
            cls.initialize()
        return (cls._random.random(),)
