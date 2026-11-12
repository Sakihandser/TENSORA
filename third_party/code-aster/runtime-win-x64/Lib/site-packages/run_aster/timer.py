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
:py:mod:`timer` --- Simple timer
--------------------------------

This module defines the simple timer object to store elapsed times during
different steps of an execution.
"""


import os
import pickle
from collections import OrderedDict, namedtuple


Measure = namedtuple("Measure", "cpu system total elapsed")


class Timer:
    """Object to trace the time spent during execution."""

    header = "{:30s} {:>10s} {:>10s} {:>10s} {:>10s}"
    fmt = (
        "{title:<30s} {measure.cpu:10.2f} {measure.system:10.2f} "
        "{measure.total:10.2f} {measure.elapsed:10.2f}"
    )

    def __init__(self, title="Total"):
        self._started = OrderedDict()
        self._measures = OrderedDict()
        self.start(title)
        self._global = title

    def start(self, title):
        """Start a new timer.

        Arguments:
            title (str): Title, also used as identifier for the timer.
        """
        self._started[title] = os.times()

    def stop(self, title=None):
        """Stop a timer. If no timer is provided, it stops the last started one.

        Arguments:
            title (str, optional): Title, also used as identifier for the timer.
        """
        title = title or list(self._started.keys())[-1]
        started = self._started.pop(title, self._started.get(self._global))
        delta = self.deltat(started, os.times())
        delta = self.add(delta, self._measures.setdefault(title))
        self._measures[title] = delta

    def stop_all(self):
        """Stop all non stopped timers."""
        for title in list(self._started.keys()):
            self.stop(title)
        self._measures.move_to_end(self._global)

    def report(self):
        """Return a report of the measures.

        Returns:
            str: Report.
        """
        self.stop_all()
        separator = "-" * 80
        lines = [self.header.format("", "cpu", "system", "cpu+sys", "elapsed"), separator]
        lines.extend(
            [self.fmt.format(title=title, measure=i) for title, i in self._measures.items()]
        )
        lines.insert(-1, separator)
        lines.append(separator)
        return "\n".join(lines)

    @staticmethod
    def deltat(start, end):
        """Return a tuple of *(cpu, sys, total, elapsed)* between `start` and `end`.

        Arguments:
            start (*times_result*): Initial time as return by `timer()`.
            end (*times_result*): End time.

        Returns:
            Measure: Tuple of 4 floats: (cpu, system, total, elapsed).
        """
        cpu = end.user - start.user + end.children_user - start.children_user
        sys = end.system - start.system + end.children_system - start.children_system
        elapsed = end.elapsed - start.elapsed
        return Measure(cpu, sys, cpu + sys, elapsed)

    @staticmethod
    def add(measure, other):
        """Cumulate two measures.

        Arguments:
            measure (*Measure*): First measure.
            other (*Measure*): Second measure, that may be null (*None*).
        """
        if other:
            measure = Measure(
                measure.cpu + other.cpu,
                measure.system + other.system,
                measure.total + other.total,
                measure.elapsed + other.elapsed,
            )
        return measure

    def save(self, filename):
        """Save timer content to a file.

        Arguments:
            filename (str): Filename to be written.
        """
        self.stop_all()
        with open(filename, "wb") as fpick:
            pickle.dump(self._global, fpick)
            pickle.dump(self._measures, fpick)

    def load(self, filename):
        """Restore timer content from a file.

        Arguments:
            filename (str): Filename to be read.
        """
        if not os.path.exists(filename):
            return
        with open(filename, "rb") as fpick:
            self._global = pickle.load(fpick)
            self._measures = pickle.load(fpick)
