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

from ...Utilities import no_new_attributes, logger
from ...Messages import UTMESS


class LoggingManager:
    """Object that decides about the logging."""

    columns = None
    length_col = 16
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self):
        self.columns = {}

    @staticmethod
    def _center(word, length):
        if len(word) > length:
            word = word[::length]
        len_word = len(word)
        diff = length - len_word
        left = diff // 2
        right = diff - left

        return " " * left + word + " " * right

    def addConvTableColumn(self, column):
        """Add a colum to the table

        Arguements:
            column[str]: title of the column
        """
        words = column.strip().split()
        self.columns[column] = [words, None]

    def printIntro(self, time, step):
        """Print introduction

        Arguements:
            time[float]: current time
            step[int]: step
        """
        self.printConvTableSeparator()

        UTMESS("I", "MECANONLINE6_1", vali=step, valr=time)

    def printConvTableSeparator(self):
        """Print separator."""
        logger.info("-" * (len(self.columns) * (self.length_col + 1) + 1))

    def printConvTableEntries(self):
        """Print titles of columns"""

        nb_row = 0
        for key in self.columns:
            nb_row = max(nb_row, len(self.columns[key][0]))

        self.printConvTableSeparator()
        for irow in range(nb_row):
            row = "|"
            for key in self.columns:
                if len(self.columns[key][0]) > irow:
                    val = self.columns[key][0][irow]
                else:
                    val = " "

                row += self._center(val, self.length_col) + "|"
            logger.info(row)

        self.printConvTableSeparator()

    def printConvTableRow(self, values):
        """Print values of colums"""

        row = "|"
        for val in values:
            if isinstance(val, float):
                word = f"{val:.8E}"
            else:
                word = str(val)
            row += self._center(word, self.length_col) + "|"

        logger.info(row)

    def printConvTableEnd(self):
        self.printConvTableSeparator()
        UTMESS("I", "MECANONLINE6_60")
