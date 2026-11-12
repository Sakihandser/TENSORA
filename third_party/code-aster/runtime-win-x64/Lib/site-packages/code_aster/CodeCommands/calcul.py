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

from collections import namedtuple

from ..Cata import Commands
from ..Helpers import adapt_for_mgis_behaviour
from ..Objects import TableContainer
from ..Supervis import ExecuteCommand, UserMacro
from .extr_table import EXTR_TABLE


class Compute(ExecuteCommand):
    """Command that creates the :class:`~code_aster.Objects.Table`"""

    command_name = "_CALCUL_"
    command_cata = Commands.CALCUL
    # Change the content of the COMPORTEMENT keyword.
    adapt_syntax = adapt_for_mgis_behaviour

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        reuse = keywords.get("reuse")
        if reuse is not None:
            self._result = reuse
        else:
            self._result = TableContainer()

    def post_exec(self, keywords):
        """Update the result

        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """
        self._result.build()

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Arguments:
            keywords (dict): User's keywords.
        """
        self._result.addDependency(keywords["MODELE"])


_CALCUL_ = Compute.run


def calcul_ops(self, **kwargs):
    """Executor of CALCUL.

    By default, a *TableContainer* object is returned. If `__use_namedtuple__`
    is *True*, a namedtuple is returned, using objects names from the table.

    Returns:
        (table|namedtuple): Container as Table or a tuple.
    """
    container = _CALCUL_(**kwargs)
    if not self._tuplmode:
        result = container
    else:
        table = container.EXTR_TABLE()
        if kwargs["INFO"] > 1:
            print(table)
        objects = []
        content = {}
        for row in table:
            name = row["NOM_OBJET"]
            objects.append(name)
            if row["TYPE_OBJET"]:
                content[name] = EXTR_TABLE(
                    TABLE=container,
                    TYPE_RESU=row["TYPE_OBJET"],
                    NOM_PARA="NOM_SD",
                    FILTRE=_F(NOM_PARA="NOM_OBJET", VALE_K=name),
                )
                if hasattr(content[name], "setModel"):
                    content[name].setModel(kwargs["MODELE"])
                if hasattr(content[name], "build"):
                    content[name].build()
            else:
                assert name == "CODE_RETOUR_INTE", name
                content[name] = EXTR_TABLE(
                    TABLE=container,
                    TYPE_RESU="ENTIER",
                    NOM_PARA="VALE_I",
                    FILTRE=_F(NOM_PARA="NOM_OBJET", VALE_K=name),
                )

        result_type = namedtuple("Result", objects)
        result = result_type(**content)

    return result


CALCUL = UserMacro("CALCUL", Commands.CALCUL, calcul_ops)
