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
:py:mod:`logger` --- Logging and messages output
************************************************

This module defines a logger object and error functions.
All message outputs should pass by this object.
Probably additional levels should be added to distinguish low-debug messages,
debug messages that may be interesting for the user (equivalent to
``INFO=2``)...
It might be necessary to refactor it in C++ for better performance and a
global access (no C interface currently)...
"""

import logging
import os
import sys
from contextlib import contextmanager
from functools import partial, wraps

from libaster import AsterError

# using these values allows to use them as `lvl` in `logger.log(lvl, ...)`
ERROR = logging.ERROR
WARNING = logging.WARNING
INFO = logging.INFO
OK = INFO
DEBUG = logging.DEBUG

RETURNCODE = {OK: 0, DEBUG: 0, WARNING: 2, ERROR: 4}
assert OK < WARNING < ERROR, (OK, WARNING, ERROR)


class PerLevelFormatter(logging.Formatter):
    """Formatter for messages"""

    formats = {
        ERROR: "ERROR: %(message)s",
        WARNING: "WARNING: %(message)s",
        INFO: "%(message)s",
        DEBUG: "DEBUG: %(message)s",
    }

    def format(self, record):
        """Enhance error and warning messages"""
        log_fmt = self.formats.get(record.levelno, self.formats[INFO])
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


class PerLevelColorFormatter(PerLevelFormatter):
    """Formatter for messages"""

    def _adjust_color(self, level):
        """Choose a color function according to the level"""
        func = lambda message: message
        if level >= ERROR:
            func = red
        elif level >= WARNING:
            func = blue
        return func

    def format(self, record):
        """Enhance error and warning messages"""
        lvl = record.levelno
        return self._adjust_color(lvl)(PerLevelFormatter.format(self, record))


class HgStreamHandler(logging.StreamHandler):
    """StreamHandler switching between sys.stdout and sys.stderr
    like the mercurial ui does"""

    def _adjust_stream(self, level):
        """Adjust the stream according to the given level"""
        self.flush()
        if level >= WARNING:
            self.stream = sys.stderr
        else:
            self.stream = sys.stdout

    def emit(self, record):
        """Enhance error and warning messages"""
        self._adjust_stream(record.levelno)
        return logging.StreamHandler.emit(self, record)


def build_logger(level=INFO, raise_exception=True):
    """Initialize the logger with its handlers.

    Arguments:
        level (int): Logging level.
        raise_exception (bool): If *True* (default), an exception is raised in
            case of error.

    Returns:
        Logger: logger object.
    """
    logger = logging.getLogger("code_aster")
    # keep only debug, info and error
    logger.critical = logger.fatal = None
    if int(os.getenv("DEBUG", 0)):
        level = DEBUG
    logger.setLevel(level)
    term = HgStreamHandler(sys.stdout)
    term.setFormatter(PerLevelFormatter())
    logger.addHandler(term)

    if raise_exception:
        logger._error_orig = logger.error

        def _error(self, *args, **kwargs):
            logger._error_orig(self, *args, **kwargs)
            raise AsterError("SUPERVIS_99")

        logger.error = _error

    return logger


logger = build_logger()


@contextmanager
def loglevel(level):
    """Change the logging level.

    Arguments:
        level (int): Logger level.
    """
    previous = logger.getEffectiveLevel()
    logger.setLevel(level)
    try:
        yield
    finally:
        logger.setLevel(previous)


def with_loglevel(level=DEBUG, with_result=False):
    """Decorator to temporarly change the logging level for a function
    (only for debuging a priori).

    Example:

    .. code-block:: python

        @with_loglevel()
        def my_function(its_args):
            [...]

    Arguments:
        level (int): Logger level.
        with_result (bool): If *True*, the result is logged (debug mode).
    """

    def change_level(func):
        """Raw decorator"""

        @wraps(func)
        def wrapper(*args, **kwargs):
            """Wrapper"""
            with loglevel(level):
                result = func(*args, **kwargs)
                if with_result:
                    logger.debug("returns: %s", result)
            return result

        return wrapper

    return change_level


COLOR = {
    "red": r"\033[1;31m",
    "green": r"\033[1;32m",
    "blue": r"\033[1;34m",
    "grey": r"\033[1;30m",
    "magenta": r"\033[1;35m",
    "cyan": r"\033[1;36m",
    "yellow": r"\033[1;33m",
    "endc": r"\033[1;m",
}

try:
    _colored = sys.stdout.isatty()
except AttributeError:
    _colored = False


def _colorize(color, string):
    """Return the colored `string`"""
    if not _colored or not string.strip():
        return string
    return COLOR[color] + string + COLOR["endc"]


red = partial(_colorize, "red")
green = partial(_colorize, "green")
blue = partial(_colorize, "blue")
magenta = partial(_colorize, "magenta")
cyan = partial(_colorize, "cyan")
yellow = partial(_colorize, "yellow")
grey = partial(_colorize, "grey")
