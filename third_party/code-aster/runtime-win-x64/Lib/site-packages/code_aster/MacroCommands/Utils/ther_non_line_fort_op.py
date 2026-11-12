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


from ...Objects import ThermalResult
from ...Supervis import ExecuteCommand
from ...Helpers import adapt_increment_init
from .ther_non_line_fort_cata import THER_NON_LINE_FORT_CATA


class NonLinearThermalAnalysisFort(ExecuteCommand):
    """Command that creates the :class:`~code_aster.Objects.ThermalResult` by assigning
    finite elements on a :class:`~code_aster.Objects.ThermalResult`."""

    command_name = "THER_NON_LINE_FORT"
    command_cata = THER_NON_LINE_FORT_CATA

    def adapt_syntax(self, keywords):
        """Hook to adapt syntax *after* syntax checking.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """
        # use initial time from ETAT_INIT
        adapt_increment_init(keywords, "EVOL_THER")

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        if "reuse" in keywords:
            self._result = keywords["reuse"]
        else:
            self._result = ThermalResult()

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        self._result.setModel(keywords["MODELE"], exists_ok=True)
        self._result.setMaterialField(keywords["CHAM_MATER"], exists_ok=True)
        if "CARA_ELEM" in keywords:
            self._result.setElementaryCharacteristics(keywords["CARA_ELEM"], exists_ok=True)

        feds = []
        fnds = []
        if "ETAT_INIT" in keywords:
            etat = keywords["ETAT_INIT"]

            field = "CHAM_NO"
            if field in etat:
                fnds.append(etat[field].getDescription())

            if "EVOL_THER" in etat:
                feds += etat["EVOL_THER"].getFiniteElementDescriptors()
                fnds += etat["EVOL_THER"].getEquationNumberings()

        self._result.build(feds, fnds, keywords.get("EXCIT"))

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Arguments:
            keywords (dict): User's keywords.
        """
        super().add_dependencies(keywords)
        self.remove_dependencies(keywords, "RESULTAT")
        self.remove_dependencies(keywords, "MODELE")
        self.remove_dependencies(keywords, "CHAM_MATER")
        self.remove_dependencies(keywords, "CARA_ELEM")
        self.remove_dependencies(keywords, "RESU_THER_SECH")
        self.remove_dependencies(keywords, "ETAT_INIT", ("EVOL_THER, 'CHAM_NO"))
        self.remove_dependencies(keywords, "EXCIT", ("CHARGE", "FONC_MULT"))


THER_NON_LINE_FORT = NonLinearThermalAnalysisFort.run
