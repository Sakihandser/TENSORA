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
:py:class:`FIN` --- Finalization of code_aster
**********************************************

The :py:class:`Closer` finalizes the execution by closing the code_aster
memory manager (*Jeveux*).

The objects existing in the context where :py:func:`~code_aster.Commands.FIN`
is called are pickled while their *Jeveux* content is saved in ``glob.*``
databases.
A call to the function :py:func:`~code_aster.Supervis.Serializer.saveObjects`
is equivalent.
"""

import gc
import sys

import libaster

from ..Supervis import ExecuteCommand, FinalizeOptions, saveObjects
from ..Supervis.code_file import Tracking
from ..Utilities import ExecutionParameter, Options, haveMPI, logger


class Closer(ExecuteCommand):
    """Command that closes the execution."""

    command_name = "FIN"
    _options = None
    _exit = None
    _is_finalized = None
    _atexit = None

    def change_syntax(self, keywords):
        """Adapt syntax before checking syntax.

        Consume argument to force to exit after the command.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """
        self._exit = keywords.pop("exit", False)
        self._atexit = keywords.pop("atexit", False)

    @classmethod
    def run(cls, **keywords):
        """Run the Command.

        Arguments:
            keywords (dict): User keywords
        """
        if cls._is_finalized or not libaster.jeveux_status():
            return
        # it seems a good idea to force pending deletions
        gc.collect()
        super().run(**keywords)

    def exec_(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        option = ExecutionParameter().option
        self._options = FinalizeOptions.Set
        if not option & Options.LastStep:
            self._options |= FinalizeOptions.SaveBase
        else:
            # at the last step
            if haveMPI() and not option & Options.HPCMode:
                self._options |= FinalizeOptions.OnlyProc0
            if option & Options.SaveBase:
                self._options |= FinalizeOptions.SaveBase
        if keywords.get("INFO_BASE") == "OUI":
            self._options |= FinalizeOptions.InfoBase
        if keywords.get("INFO_RESU") == "OUI":
            self._options |= FinalizeOptions.InfoResu
        if keywords.get("RETASSAGE") == "OUI":
            self._options |= FinalizeOptions.Repack
        super().exec_(keywords)
        Closer._is_finalized = True
        # restore excepthook
        sys.excepthook = sys.__excepthook__

    def _call_oper(self, dummy):
        """Save objects that exist in the context of the caller.

        The memory manager is closed when :mod:`libaster` is unloaded.
        """
        # Ensure that `saveObjects` has not been already called
        if libaster.jeveux_status():
            if not self._atexit:
                # 1: here, 2: exec_, 3: parent.exec_, 4: run_, 5: run, 6: cls.run, 7: user space
                saveObjects(level=7, options=self._options)
            else:
                # called "atexit", objects may be deleted, only close database
                libaster.jeveux_finalize(0)
        Tracking.stop_timer(ExecutionParameter().timer)
        logger.info(repr(ExecutionParameter().timer))

    def post_exec(self, keywords):
        """Force to exit if `exit=True` option was passed.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        if self._exit:
            sys.exit()


FIN = close = Closer.run
