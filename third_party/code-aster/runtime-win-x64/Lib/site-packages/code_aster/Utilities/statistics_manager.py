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

import time
from functools import wraps

try:
    from resource import RUSAGE_SELF, getrusage
except ImportError:
    RUSAGE_SELF = getrusage = None

from .logger import logger


class Profiler:
    """This object defines a decorator to count the number of calls and
    to measure the execution time of a function or a method.
    """

    def __init__(self):
        self.reset_stats()

    def measure(self, func):
        """Main decorator."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            """wrapper function"""
            key = self.key(func, *args)
            self._calls.setdefault(key, 0)
            self._elaps.setdefault(key, 0.0)
            self._calls[key] += 1

            start = time.perf_counter()
            logger.debug("function '%s' is running...", key)
            result = func(*args, **kwargs)
            delta = time.perf_counter() - start
            self._elaps[key] += delta
            if getrusage:
                mem_used = int(getrusage(RUSAGE_SELF).ru_maxrss / 1024)
            else:
                mem_used = -1
            logger.debug("function '%s' has run in %f s (VmPeak %d MB)", key, delta, mem_used)
            return result

        return wrapper

    def reset_stats(self):
        """Reset statistics."""
        self._calls = {}
        self._elaps = {}
        self._lvl = 0

    def print_stats(self, by_class=True):
        """Show profiler statistics.

        Arguments:
            by_class (bool): Group functions by class if *True*.
        """
        logger.info("Statistics:")
        calls = {}
        elaps = {}

        for key in self._elaps:
            path = key.split(".")
            assert len(path) in (1, 2), path
            if by_class and len(path) > 1:
                klass, func = path
                calls.setdefault(klass, {})
                calls[klass][func] = self._calls[key]
                elaps.setdefault(klass, {})
                elaps[klass][func] = self._elaps[key]
            else:
                calls[key] = self._calls[key]
                elaps[key] = self._elaps[key]

        self._lvl = 0
        self._print_stats(calls, elaps)

    def _print_stats(self, calls, elaps):
        for key in calls:
            if not isinstance(calls[key], dict):
                self._print_line(key, calls[key], elaps[key])
            else:
                logger.info("%s- %s.", self._indent(), key)
                self._lvl += 1
                self._print_stats(calls[key], elaps[key])
                self._lvl -= 1

    def _print_line(self, key, calls, elaps):
        logger.info("%s- %s called %d times in %f s", self._indent(), key, calls, elaps)

    def _indent(self):
        return " " * 2 * self._lvl

    @staticmethod
    def key(callable, *args):
        """Build a name to be used as a key to identify the called function.

        Arguments:
            callable (function): Wrapped function or method.
            args (tuple): Positional arguments.
        """
        name = callable.__name__
        # is a method of class?
        if args and hasattr(args[0], name):
            name = args[0].__class__.__name__ + "." + name
        return name


# global object + convenient shortcuts
PROFILER = Profiler()
profile = PROFILER.measure
print_stats = PROFILER.print_stats
reset_stats = PROFILER.reset_stats


def _unittest():
    class Class:
        @profile
        def ftest(self, a, b):
            """help ftest"""
            return a * b

    @profile
    def ftest(a, b):
        return a + b

    for _ in range(43):
        assert ftest(1, 2) == 3
    inst = Class()
    assert inst.ftest(1, 2) == 2

    print_stats()
    assert len(Profiler._calls) == 2
    assert len(Profiler._elaps) == 2
    assert Profiler._calls["ftest"] == 43
