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
    AsFloat,
    AsInteger,
    ConstantFieldOnCellsReal,
    DataField,
    ElementaryMatrixDisplacementReal,
    ElementaryMatrixTemperatureReal,
    ElementaryVectorDisplacementReal,
    ElementaryVectorTemperatureReal,
    FieldOnCellsReal,
    FieldOnNodesReal,
    Function,
    FunctionComplex,
    Function2D,
    GeneralizedAssemblyMatrixReal,
    Model,
    ModeResult,
    Table,
)
from ..Supervis import ExecuteCommand


class ExtrTable(ExecuteCommand):
    """Command that defines :class:`~code_aster.Objects.Function`."""

    command_name = "EXTR_TABLE"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        typeResu = keywords["TYPE_RESU"]
        if typeResu == "VECT_ELEM_DEPL_R":
            self._result = ElementaryVectorDisplacementReal()
        elif typeResu == "FONCTION_SDASTER":
            self._result = Function()
        elif typeResu == "FONCTION_C":
            self._result = FunctionComplex()
        elif typeResu == "TABLE_SDASTER":
            self._result = Table()
        elif typeResu == "MATR_ASSE_GENE_R":
            self._result = GeneralizedAssemblyMatrixReal()
        elif typeResu == "MATR_ELEM_DEPL_R":
            self._result = ElementaryMatrixDisplacementReal()
        elif typeResu == "NAPPE_SDASTER":
            self._result = Function2D()
        elif typeResu == "MODE_MECA":
            self._result = ModeResult()
        elif typeResu == "CARTE_SDASTER":
            self._result = ConstantFieldOnCellsReal()
        elif typeResu == "CHAM_ELEM":
            self._result = FieldOnCellsReal()
        elif typeResu == "CHAM_NO_SDASTER":
            self._result = FieldOnNodesReal()
        elif typeResu == "CHAM_GD_SDASTER":
            self._result = DataField()
        elif typeResu == "ENTIER":
            self._result = AsInteger()
        elif typeResu == "REEL":
            self._result = AsFloat()
        else:
            raise NotImplementedError()

    def post_exec(self, keywords):
        """Build ElementaryTerms objects.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """
        if hasattr(self._result, "setModel"):
            model = [i for i in keywords["TABLE"].getDependencies() if isinstance(i, Model)]
            if model:
                self._result.setModel(model[0])

        if isinstance(self._result, FieldOnCellsReal):
            model = [i for i in keywords["TABLE"].getDependencies() if isinstance(i, Model)]
            if model:
                self._result.setDescription(model[0].getFiniteElementDescriptor())

        # not available for int/float
        # + not consistent when created by TableContainer::build
        supported = (
            "VECT_ELEM_DEPL_R",
            "VECT_ELEM_TEMP_R",
            "MATR_ELEM_DEPL_R",
            "MATR_ELEM_TEMP_R",
            "CHAM_NO_SDASTER",
            "TABLE_SDASTER",
        )
        if hasattr(self._result, "build") and keywords["TYPE_RESU"] in supported:
            self._result.build()

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Arguments:
            keywords (dict): User's keywords.
        """
        super().add_dependencies(keywords)
        self.remove_dependencies(keywords, "TABLE")


EXTR_TABLE = ExtrTable.run
