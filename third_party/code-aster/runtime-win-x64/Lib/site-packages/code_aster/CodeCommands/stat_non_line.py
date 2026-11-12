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

from ..Helpers import adapt_for_mgis_behaviour, adapt_increment_init
from ..Messages import UTMESS
from ..Objects import FieldOnCellsComplex, FieldOnCellsReal, NonLinearResult
from ..Objects import ResultManager
from ..Supervis import ExecuteCommand


class NonLinearStaticAnalysis(ExecuteCommand):
    """Command that defines :class:`~code_aster.Objects.NonLinearResult`."""

    command_name = "STAT_NON_LINE"

    def adapt_syntax(self, keywords):
        """Hook to adapt syntax *after* syntax checking.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """
        # Change the content of the COMPORTEMENT keyword.
        adapt_for_mgis_behaviour(self, keywords)
        # because MNL support SUBD_NIVEAU={0, 1} and SNL does not
        stepper = keywords["INCREMENT"][0]["LIST_INST"]
        try:
            stepper.checkMaxLevel(min=0)
        except AttributeError:
            pass
        except ValueError as exc:
            UTMESS("F", "SUPERVIS_4", valk=(self.command_name, str(exc)))

        # use initial time from ETAT_INIT
        adapt_increment_init(keywords, "EVOL_NOLI")

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        if keywords.get("reuse"):
            self._result = keywords["reuse"]
            incr = keywords["INCREMENT"][0]
            index = incr.get("NUME_INST_INIT")
            if index is None:
                prec = incr.get("PRECISION", 1.0e-6)
                crit = incr.get("CRITERE", "RELATIF")
                index = self._result.getIndexFromParameter("INST", incr["INST_INIT"], crit, prec)
            self._result.clear(index + 1)
        else:
            self._result = NonLinearResult()
        self._result.setMesh(keywords["MODELE"].getMesh())
        self._result.addFiniteElementDescriptor(keywords["MODELE"].getFiniteElementDescriptor())
        if "ETAT_INIT" in keywords:
            etat = keywords["ETAT_INIT"]
            fields = ["DEPL", "VITE", "ACCE"]
            for field in fields:
                if field in etat:
                    if etat[field].getDescription() is not None:
                        self._result.addEquationNumbering(etat[field].getDescription())

            fields = ["COHE", "SIGM", "VARI", "STRX"]
            for field in fields:
                if field in etat:
                    if isinstance(etat[field], (FieldOnCellsReal, FieldOnCellsComplex)):
                        if etat[field].getDescription() is not None:
                            self._result.addFiniteElementDescriptor(etat[field].getDescription())

            if "EVOL_NOLI" in etat:
                for fed in etat["EVOL_NOLI"].getFiniteElementDescriptors():
                    self._result.addFiniteElementDescriptor(fed)
                for fnd in etat["EVOL_NOLI"].getEquationNumberings():
                    self._result.addEquationNumbering(fnd)
        ResultManager.getInstance().setCurrentResult(self._result)

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        result = self._result
        caraElem = keywords.get("CARA_ELEM")
        contact = keywords.get("CONTACT")
        result.setModel(keywords["MODELE"], exists_ok=True)
        result.setMaterialField(keywords["CHAM_MATER"], exists_ok=True)
        if caraElem:
            result.setElementaryCharacteristics(caraElem, exists_ok=True)
        if contact:
            result.setContact(contact)

        if self.exception and self.exception.id_message in ("MECANONLINE5_82",):
            return

        result.build([], [], keywords.get("EXCIT"))
        ResultManager.getInstance().releaseCurrentResult()

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
        self.remove_dependencies(keywords, "CONTACT")
        self.remove_dependencies(
            keywords,
            "ETAT_INIT",
            ("DEPL", "SIGM", "VARI", "STRX", "COHE", "VITE", "ACCE", "EVOL_NOLI"),
        )
        self.remove_dependencies(keywords, "EXCIT", ("CHARGE", "FONC_MULT"))
        self.remove_dependencies(keywords, "INCREMENT", "LIST_INST")
        self.remove_dependencies(keywords, "ARCHIVAGE", "LIST_INST")


STAT_NON_LINE = NonLinearStaticAnalysis.run
