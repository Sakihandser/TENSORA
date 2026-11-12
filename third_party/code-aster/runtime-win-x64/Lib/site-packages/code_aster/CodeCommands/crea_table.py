# coding=utf-8
#
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

from ..Objects import Table, TableContainer, TableOfFunctions
from ..Supervis import ExecuteCommand


class TableCreation(ExecuteCommand):
    """Execute legacy operator CREA_TABLE."""

    command_name = "CREA_TABLE"

    def adapt_syntax(self, keywords):
        """Force required types for TABLE_CONTAINER.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """
        if keywords.get("RESU"):
            fkwd = keywords["RESU"][0]
            if fkwd.get("RESULTAT"):
                name = fkwd["RESULTAT"].userName
            else:
                name = fkwd["CHAM_GD"].userName
            fkwd["INTITULE"] = name
        if keywords["TYPE_TABLE"] != "TABLE_CONTAINER" or not keywords.get("LISTE"):
            return
        for occ in keywords["LISTE"]:
            if not occ.get("LISTE_K"):
                continue
            if occ["PARA"] in ("NOM_OBJET", "TYPE_OBJET"):
                occ["TYPE_K"] = "K16"
            if occ["PARA"] == "NOM_SD" and occ["TYPE_K"] not in ("K8", "K24"):
                occ["TYPE_K"] = "K24"

    def create_result(self, keywords):
        """Create the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        reuse = keywords.get("reuse")
        if reuse is not None:
            self._result = reuse
        else:
            typ = keywords["TYPE_TABLE"]
            assert typ in ("TABLE", "TABLE_CONTAINER", "TABLE_FONCTION"), typ
            if typ == "TABLE_FONCTION":
                self._result = TableOfFunctions()
            elif typ == "TABLE_CONTAINER":
                self._result = TableContainer()
            else:
                self._result = Table()

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Arguments:
            keywords (dict): User's keywords.
        """
        super().add_dependencies(keywords)
        self.remove_dependencies(keywords, "RESU", ("RESULTAT", "CHAM_GD"))

    def post_exec(self, keywords):
        """
        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """
        liste = keywords.get("LISTE")
        if liste:
            concepts = None
            names = None
            for occ in liste:
                if "LISTE_CO" in occ:
                    concepts = occ["LISTE_CO"]
                if "LISTE_K" in occ:
                    if "NOM_OBJET" in occ["PARA"]:
                        names = occ["LISTE_K"]

            if concepts:
                for name, concept in zip(names, concepts):
                    self._result.addObject(name, concept)
        self._result.build()


CREA_TABLE = TableCreation.run
