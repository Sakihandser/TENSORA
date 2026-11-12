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


from ..Objects import (
    GeneralizedAssemblyVectorReal,
    GeneralizedAssemblyVectorComplex,
    FieldOnNodesComplex,
)
from ..Supervis import ExecuteCommand


class ProjVectBase(ExecuteCommand):
    """Command that defines :class:`~code_aster.Objects.GeneralizedAssemblyVectorReal`."""

    command_name = "PROJ_VECT_BASE"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        if "VECT_ASSE_GENE" in keywords:
            self._result = type(keywords["VECT_ASSE_GENE"])()
        else:
            if type(keywords["VECT_ASSE"]) == FieldOnNodesComplex:
                self._result = GeneralizedAssemblyVectorComplex()
            else:
                self._result = GeneralizedAssemblyVectorReal()


PROJ_VECT_BASE = ProjVectBase.run
