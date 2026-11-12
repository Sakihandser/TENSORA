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


from ..Objects import Table
from ..Supervis import ExecuteCommand
from ..Messages import UTMESS


class PostElem(ExecuteCommand):
    """Command that defines :class:`~code_aster.Objects.Table`."""

    command_name = "POST_ELEM"

    def adapt_syntax(self, keywords):
        """Perform checks of syntax based on argument content's.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """

        chamgd = keywords.get("CHAM_GD")
        chmater = keywords.get("CHAM_MATER")

        if chamgd and chmater:
            if chmater.hasExternalStateVariable() and keywords.get("INST") is None:
                UTMESS("F", "POSTELEM_7")

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        self._result = Table()

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Some references may be required for CARA_GEOM/CARA_POUTRE.

        Arguments:
            keywords (dict): User's keywords.
        """

    def post_exec(self, keywords):
        """
        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """
        self._result.build()


POST_ELEM = PostElem.run
