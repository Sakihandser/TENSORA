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


from ..Helpers import adapt_for_mgis_behaviour
from ..Objects import (
    LoadResult,
    ThermalResult,
    FullHarmonicResult,
    FullTransientResult,
    ExternalStateVariablesResult,
    ElasticResult,
    ModeResultComplex,
    ModeResult,
    EmpiricalModeResult,
    NonLinearResult,
    DryingResult,
)
from ..Supervis import ExecuteCommand


class ResultsReader(ExecuteCommand):
    """Command that creates the :class:`~code_aster.Objects.??` by assigning
    finite elements on a :class:`~code_aster.Objects.??`."""

    command_name = "LIRE_RESU"
    # Change the content of the COMPORTEMENT keyword.
    adapt_syntax = adapt_for_mgis_behaviour

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        typ = keywords["TYPE_RESU"]
        if "reuse" in keywords:
            self._result = keywords["reuse"]
        elif typ == "EVOL_THER":
            self._result = ThermalResult()
        elif typ == "EVOL_SECH":
            self._result = DryingResult()
        elif typ == "EVOL_ELAS":
            self._result = ElasticResult()
        elif typ == "EVOL_NOLI":
            self._result = NonLinearResult()
        elif typ == "EVOL_CHAR":
            self._result = LoadResult()
        elif typ == "DYNA_TRANS":
            self._result = FullTransientResult()
        elif typ == "DYNA_HARMO":
            self._result = FullHarmonicResult()
        elif typ == "MODE_MECA":
            self._result = ModeResult()
        elif typ == "MODE_EMPI":
            self._result = EmpiricalModeResult()
        elif typ == "MODE_MECA_C":
            self._result = ModeResultComplex()
        elif typ == "EVOL_VARC":
            self._result = ExternalStateVariablesResult()
        else:
            raise NotImplementedError("Type of result {0!r} not yet " "implemented".format(typ))

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        if "MODELE" in keywords:
            self._result.setModel(keywords["MODELE"], exists_ok=True)
        elif "MAILLAGE" in keywords:
            self._result.setMesh(keywords["MAILLAGE"])

        if "CHAM_MATER" in keywords:
            self._result.setMaterialField(keywords["CHAM_MATER"], exists_ok=True)

        if "CARA_ELEM" in keywords:
            self._result.setElementaryCharacteristics(keywords["CARA_ELEM"], exists_ok=True)

        if "MATR_RIGI" in keywords:
            dofNum = keywords["MATR_RIGI"].getDOFNumbering()
            if dofNum:
                self._result.setDOFNumbering(dofNum)

        if "NUME_DDL" in keywords:
            numeEqua = keywords["NUME_DDL"].getEquationNumbering()
            self._result.build([], [numeEqua])
        else:
            self._result.build()


LIRE_RESU = ResultsReader.run
