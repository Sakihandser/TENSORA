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


from ..Objects import TableContainer
from .extr_table import EXTR_TABLE
from ..Supervis import ExecuteCommand, UserMacro
from ..Cata.Commands.calc_g import CALC_G as calc_g_cata
from ..Cata.Syntax import _F


class ComputeG(ExecuteCommand):
    """Command that creates the :class:`~code_aster.Objects.Table`"""

    command_name = "CALC_G"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        self._result = TableContainer()


def calc_g_with_co(self, **args):
    """Wrapper around the original CALC_G command to return an additional
    result.

    Arguments:
        args (dict): Keywords arguments of user's keywords.

    Returns:
        Table: Result of the command.
    """
    _result_calc_g = ComputeG.run(**args)
    _result_calc_g.build()
    titr = _result_calc_g.getTitle()

    # Extraction de la table qui contient G
    _table_g = EXTR_TABLE(
        TYPE_RESU="TABLE_SDASTER",
        TABLE=_result_calc_g,
        NOM_PARA="NOM_SD",
        FILTRE=_F(NOM_PARA="NOM_OBJET", VALE_K="TABLE_G"),
    )
    _table_g.setTitle(titr)
    # On fait quoi de theta ?
    _cham_theta_no = EXTR_TABLE(
        TYPE_RESU="CHAM_NO_SDASTER",
        TABLE=_result_calc_g,
        NOM_PARA="NOM_SD",
        FILTRE=_F(NOM_PARA="NOM_OBJET", VALE_K="CHAM_THETA"),
    )
    _cham_theta_no.build(args["RESULTAT"].getMesh())

    if ("CHAM_THETA" in args["THETA"]) and (args["THETA"]["CHAM_THETA"].is_typco()):
        # number of CHAM_THETA fields
        self.register_result(_cham_theta_no, args["THETA"]["CHAM_THETA"])
    else:
        del _cham_theta_no

    return _table_g


CALC_G = UserMacro("CALC_G", calc_g_cata, calc_g_with_co)
