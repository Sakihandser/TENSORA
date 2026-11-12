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

# aslint: disable=C4007
# C4007: INCLUDE() is also discouraged

import os
import traceback
from pathlib import Path

from ..Messages import UTMESS
from ..Supervis import ExecuteCommand
from ..Utilities import ExecutionParameter, Options, get_caller_context


class Include(ExecuteCommand):
    """Command that *imports* an additional commands file."""

    command_name = "INCLUDE"

    def exec_(self, keywords):
        """Execute the file to be included in the parent context."""
        context = get_caller_context(3)

        if keywords.get("ALARME", "OUI") == "OUI":
            UTMESS("A", "SUPERVIS_25", valk=("AsterStudy", "import"))
        if keywords.get("UNITE"):
            filename = Path(f"fort.{keywords['UNITE']}")
        else:
            rcdir = Path(ExecutionParameter().get_option("rcdir"))
            filename = rcdir / "tests_data" / keywords["DONNEE"]
        if not filename.is_file():
            UTMESS("F", "FICHIER_1", valk=os.fspath(filename))

        option = ExecutionParameter().option
        show = keywords.get("INFO", 0) >= 1 and not option & Options.ShowChildCmd
        if show:
            ExecutionParameter().enable(Options.ShowChildCmd)
        try:
            with open(filename) as fobj:
                exec(compile(fobj.read(), filename, "exec"), context)
        except NameError:
            dict_args = dict(
                valk=(
                    os.fspath(filename),
                    traceback.format_exc(),
                    "from code_aster.Commands import *",
                )
            )
            UTMESS("F", "FICHIER_3", **dict_args)
        except Exception:
            UTMESS("F", "FICHIER_2", valk=(os.fspath(filename), traceback.format_exc()))
        finally:
            if show:
                ExecutionParameter().disable(Options.ShowChildCmd)


INCLUDE = Include.run
