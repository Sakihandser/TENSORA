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


from ..Cata.Syntax import _F
from ..Messages import UTMESS
from ..Supervis import ExecuteCommand
from ..Utilities import ExecutionParameter, Options, force_list
from ..Objects.datastructure_py import DataStructureDict


class ImprResu(ExecuteCommand):
    """Command IMPR_RESU."""

    command_name = "IMPR_RESU"

    def add_result_name(self, resu):
        """Try to add NOM_RESU_MED keyword if not set.

        Arguments:
            resu (dict): factor keyword occurrence of RESU, changed in place.
        """
        if resu.get("NOM_CHAM_MED"):
            return
        if resu.get("RESULTAT"):
            resu_name = resu.pop("NOM_RESU_MED", resu["RESULTAT"].userName[0:8])
            if not resu_name:
                resu_name = resu["RESULTAT"].getName()
                UTMESS("A", "MED3_2", valk=resu_name)
                return
            if resu.get("NOM_CHAM"):
                resu_name = resu_name.ljust(8, "_")
                resu["NOM_CHAM"] = force_list(resu["NOM_CHAM"])
                resu["NOM_CHAM_MED"] = [resu_name + field for field in resu["NOM_CHAM"]]
            else:
                if resu.get("NOM_CMP"):
                    # NOM_RESU_MED not allowed with NOM_CMP, cf. irchor/MED3_6
                    return
                resu["NOM_RESU_MED"] = resu_name
        if resu.get("CHAM_GD"):
            field_name = resu["CHAM_GD"].userName
            if not field_name:
                UTMESS("A", "MED3_2", valk=resu["CHAM_GD"].getName())
                return
            resu["NOM_CHAM_MED"] = field_name

    def adapt_syntax(self, keywords):
        """Hook to adapt syntax *after* syntax checking.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """
        # if PROC0 is not provided by the user
        if not keywords.get("PROC0"):
            keywords["PROC0"] = "OUI"
            if ExecutionParameter().option & Options.HPCMode:
                keywords["PROC0"] = "NON"
        if keywords.get("FORMAT") in (None, "MED"):
            keywords["RESU"] = force_list(keywords["RESU"])
            for resu in keywords["RESU"]:
                self.add_result_name(resu)

    def change_syntax(self, keywords):
        """Hook to change keywords before checking syntax.

        - It takes into account child classes of DataStructureDict.
        - Change value depending if HPCMode is enabled or not.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """
        resu_to_print = []
        for resu in force_list(keywords["RESU"]):
            resu_to_print.extend(_syntax_dsdict(resu))

        keywords["RESU"] = tuple(resu_to_print)

        if keywords.get("FORMAT") in (None, "MED"):
            # "OUI" is only allowed with a ParallelMesh
            if "FICHIER_UNIQUE" in keywords and not ExecutionParameter().option & Options.HPCMode:
                keywords["FICHIER_UNIQUE"] = "NON"


def _syntax_dsdict(resu):
    if not isinstance(resu, dict):
        resu = resu[0]
    result = resu["RESULTAT"]
    list_resu = []
    if issubclass(type(result), DataStructureDict):
        for key in result.keys():
            list_resu.append({"RESULTAT": result[key], "NOM_RESU_MED": key})
    else:
        list_resu.append(resu)

    return list_resu


IMPR_RESU = ImprResu.run
