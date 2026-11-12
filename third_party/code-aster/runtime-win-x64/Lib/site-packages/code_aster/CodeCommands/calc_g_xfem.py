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
from .extr_table import EXTR_TABLE
from .crea_resu import CREA_RESU
from ..Supervis import ExecuteCommand, UserMacro
from ..Cata.Commands.calc_g_xfem import CALC_G_XFEM as calc_g_xfem_cata
from ..Cata.Syntax import _F


class ComputeGXFEM(ExecuteCommand):
    """Command that creates the :class:`~code_aster.Objects.Table`"""

    command_name = "CALC_G_XFEM"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        self._result = Table()

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """

        self._result.build()


def calc_g_xfem_with_co(self, **args):
    """Wrapper around the original CALC_G_XFEM command to return an additional
    result.

    Arguments:
        args (dict): Keywords arguments of user's keywords.

    Returns:
        Table: Result of the command.
    """
    _result_calc_g_xfem = ComputeGXFEM.run(**args)

    # Extraction de la table qui contient G
    _table_g_xfem = EXTR_TABLE(
        TYPE_RESU="TABLE_SDASTER",
        TABLE=_result_calc_g_xfem,
        NOM_PARA="NOM_SD",
        FILTRE=_F(NOM_PARA="NOM_OBJET", VALE_K="TABLE_G"),
    )

    # On fait quoi de theta ?
    if "CHAM_THETA" in args:
        # number of CHAM_THETA fields
        _nb_cham_theta = EXTR_TABLE(
            TYPE_RESU="ENTIER",
            TABLE=_result_calc_g_xfem,
            NOM_PARA="NUME_ORDRE",
            FILTRE=_F(NOM_PARA="NOM_OBJET", VALE_K="NB_CHAM_THETA"),
        )

        reuse = {}
        for i_cham in range(_nb_cham_theta):
            # get i-th CHAM_THETA field
            _cham_theta_no = EXTR_TABLE(
                TYPE_RESU="CHAM_NO_SDASTER",
                TABLE=_result_calc_g_xfem,
                NOM_PARA="NOM_SD",
                FILTRE=(
                    _F(NOM_PARA="NOM_OBJET", VALE_K="CHAM_THETA"),
                    _F(NOM_PARA="NUME_ORDRE", VALE_I=i_cham + 1),
                ),
            )

            _cham_theta = CREA_RESU(
                OPERATION="AFFE",
                TYPE_RESU="EVOL_NOLI",
                AFFE=(
                    _F(
                        NOM_CHAM="DEPL",
                        CHAM_GD=_cham_theta_no,
                        MODELE=args["RESULTAT"].getModel(),
                        INST=i_cham,
                    ),
                ),
                **reuse,
            )
            # for next iteration
            reuse = dict(reuse=_cham_theta, RESULTAT=_cham_theta)

        self.register_result(_cham_theta, args["CHAM_THETA"])

    return _table_g_xfem


CALC_G_XFEM = UserMacro("CALC_G_XFEM", calc_g_xfem_cata, calc_g_xfem_with_co)
