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


from ..Supervis import ExecuteCommand
from ..Utilities import required


class ComputeError(ExecuteCommand):
    """Command that creates the :class:`~code_aster.Objects.Result`"""

    command_name = "CALC_ERREUR"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        if "reuse" in keywords:
            self._result = keywords["reuse"]
        else:
            self._result = type(keywords["RESULTAT"])()

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        new_model = keywords.get("MODELE")
        if not new_model:
            previous = keywords["RESULTAT"].getModels()
            new_model = previous[-1] if previous else None
        if new_model:
            self._result.setModel(new_model, exists_ok=True)
        self._result.build()


CALC_ERREUR = ComputeError.run
