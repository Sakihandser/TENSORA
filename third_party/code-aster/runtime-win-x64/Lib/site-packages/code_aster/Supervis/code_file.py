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
The CODE is not only to check the keywords coverage.
It also stores measures of elapsed times of each command, memory consumptions...

Each line starts with a prefix defining the type of information:
- TEST for keywords coverage
- PERF for elapsed time in a command
- MEM for the memory consumption
"""

import os

import libaster

from ..Cata.Language.SyntaxObjects import IDS
from ..Cata.SyntaxUtils import value_is_sequence
from ..Utilities import MPI, is_float, is_int

EMPTY = "--"


class Tracking:
    @staticmethod
    def add(type: str, *data):
        """High level function to store a new execution information.

        Arguments:
            type (str): Type of information: "KWDS", "TIME", "PERF".
            data (misc): Data to be stored, passed to a dedicated function.
        """
        if type == "KWDS":
            _track_coverage(*data)
        elif type == "PERF":
            _track_perf(*data)
        elif type == "MEM":
            _track_memory(*data)

    @staticmethod
    def stop_timer(timer):
        """Stop the timer to store the last measures.

        Arguments:
            time (Timer): Timer object.
        """
        specials = ("check syntax", "fortran", "sdveri", "cleanup")
        for key in specials:
            times = timer.StopAndGet(f" . {key}")
            _track_perf(key, *times)
        times = timer.StopAndGet(timer.total_key)
        _track_perf(timer.TotalKey, *times)


def _write_code(line):
    # only on proc #0
    if MPI.ASTER_COMM_WORLD.rank != 0:
        return
    if libaster.jeveux_status():
        libaster.affich("CODE", line)
    else:
        with open("fort.15", "a") as fcode:
            fcode.write(line + "\n")


def _track_coverage(command, name, keywords):
    """Track used keywords into the '.code' file.

    Arguments:
        command (*SyntaxObjects.Command*): Description object of the command
        name (str): Command name
        keywords (dict): Dict of keywords.
    """
    cover = CodeVisitor(name)
    command.accept(cover, keywords)
    _write_code(cover.get_text())


def _track_perf(command, *data):
    line = " ".join(["PERF", command] + [str(i) for i in data])
    _write_code(line)


def _track_memory(command, *data):
    line = " ".join(["MEM", command] + [str(i) for i in data])
    _write_code(line)


class CodeVisitor:
    """Object that prints the text of the used keywords.

    Default keywords should have been added before.

    Arguments:
        name (str): Command name
    """

    fname = "TEST"

    def __init__(self, name):
        """Initialization"""
        self.cmdname = name
        self.mcfact = EMPTY
        self.mcsimp = None
        self.value = ""
        self.args = []

    def add_args(self):
        """Add the keyword"""
        self.args.append((self.fname, self.cmdname, self.mcfact, self.mcsimp, self.value))

    def get_text(self):
        """Return the text"""
        fmt = "%s %s %s %s %s"
        lines = [fmt % args for args in self.args]
        return os.linesep.join(lines)

    def visitCommand(self, step, userDict=None):
        """Visit a Command object

        Arguments:
            step (*Command*): Command object
            userDict (dict): Keywords
        """
        self._visitComposite(step, userDict)

    def visitMacro(self, step, userDict=None):
        """Visit a Macro object

        Arguments:
            step (*Macro*): Macro object
            userDict (dict): Keywords
        """
        self.visitCommand(step, userDict)

    def visitBloc(self, step, userDict=None):
        """Visit a Bloc object - should not occur

        Arguments:
            step (*Bloc*): Bloc object
            userDict (dict): Keywords
        """
        pass

    def visitFactorKeyword(self, step, userDict=None):
        """Visit a FactorKeyword object

        Arguments:
            step (*Command*): Command object
            userDict (dict): Keywords.
        """
        self._visitComposite(step, userDict)
        self.mcfact = EMPTY

    def visitSimpleKeyword(self, step, skwValue):
        """Visit a SimpleKeyword object

        Arguments:
            step (*SimpleKeyword*): SimpleKeyword object
            skwValue (misc): Keyword value(s)
        """
        self.value = ""
        if not value_is_sequence(skwValue):
            skwValue = [skwValue]
        as_list = step.is_list() and step.definition.get("into") is not None
        svalues = []
        is_default = True
        default = step.definition.get("defaut")
        for value in skwValue:
            repr_value = ""
            if is_float(value):
                repr_value = str(value)
            elif is_int(value):
                repr_value = str(value)
            elif type(value) in (str, str):
                repr_value = repr(value)
            svalues.append(repr_value)
            try:
                if value != default:
                    is_default = False
            except ValueError:
                pass
        if as_list and len(svalues) == 1:
            svalues.append("")
        self.value = ", ".join(svalues)
        if as_list:
            self.value = "(%s)" % self.value
        if step.definition.get("into") is None:
            if not is_default:
                self.value = ""
        self.add_args()

    def _visitComposite(self, step, userDict):
        """Loop of subobjects contained in a composite object  (containing BLOC,
        FACT and SIMP objects).

        Arguments:
            step (misc): a composite object
            userDict (dict): Keywords
        """
        if step.undefined(userDict):
            return
        if isinstance(userDict, dict):
            userDict = [userDict]
        elif isinstance(userDict, (list, tuple)):
            pass
        else:
            raise TypeError("Type 'dict' or 'tuple' is expected")

        for userOcc in userDict:
            for key, value in userOcc.items():
                kwd = step.getKeyword(key, userOcc)
                if kwd.getCataTypeId() == IDS.simp:
                    self.mcsimp = key
                elif kwd.getCataTypeId() == IDS.fact:
                    # 2 commands must be fixed, see vocab01a
                    # assert (
                    #     self.mcfact == EMPTY
                    # ), f"nested FACT keywords dectected, level 2: {self.mcfact}"
                    self.mcfact = key
                else:
                    raise TypeError(type(kwd))
                kwd.accept(self, value)
