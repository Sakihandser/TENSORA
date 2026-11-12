# coding: utf-8

# Copyright (C) 1991 - 2026  EDF www.code-aster.org
#
# This file is part of Code_Aster.
#
# Code_Aster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Code_Aster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Code_Aster.  If not, see <http://www.gnu.org/licenses/>.

import gc

from ..Messages import UTMESS
from ..Objects import DataStructure
from ..Supervis import ExecuteCommand
from ..Utilities import deprecate, get_caller_context


class Deleter(ExecuteCommand):
    """Command that deletes *DataStructure* instances from the calling stack."""

    command_name = "DETRUIRE"

    def exec_(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords, changed in place to force
                deletion. "NOM" will not be available for 'post_exec'.
        """
        if self.level > 1:
            deprecate(
                "DETRUIRE is deprecated (in macro-command), just use 'del' instead.",
                case=9,
                level=5,
            )
            return

        to_del = [obj.getName() for obj in keywords.pop("NOM")]
        if not to_del:
            return

        # calling context
        context = get_caller_context(3)

        for name in list(context.keys()):
            if isinstance(context[name], DataStructure):
                if context[name].getName() in to_del:
                    UTMESS("I", "SUPERVIS_5", valk=name)
                    del context[name]

        # force garbage collection
        gc.collect()


DETRUIRE = Deleter.run
