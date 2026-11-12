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

from libaster import deleteTemporaryObjects, setFortranLoggingLevel, resetFortranLoggingLevel

from ..Cata.Syntax import _F
from ..Objects import DOFNumbering, ParallelDOFNumbering, ListOfLoads


def meshIsParallel(args):
    """The mesh is a ParallelMesh ?

    Arguments:
        args (dict): Keywords arguments of user's keywords.
    """

    model = args.get("MODELE")
    if model is not None:
        return model.getMesh().isParallel()
    else:
        matr = args.get("MATR_RIGI")[0]
        return matr.getMesh().isParallel()


def nume_ddl_ops(self, **args):
    """Execute the command.

    Arguments:
        **args (dict): User's keywords.
    """

    args = _F(args)

    setFortranLoggingLevel(args["INFO"])

    if meshIsParallel(args):
        nume_ddl = ParallelDOFNumbering()
    else:
        nume_ddl = DOFNumbering()

    model = args.get("MODELE")
    if model is not None:
        charge = args.get("CHARGE")
        listOfLoads = ListOfLoads(model)
        if charge is not None:
            for curLoad in charge:
                listOfLoads.addLoad(curLoad)
        nume_ddl.computeNumbering(model, listOfLoads)
    else:
        matrRigi = args["MATR_RIGI"]
        nume_ddl.computeNumbering(matrRigi)

    resetFortranLoggingLevel()
    deleteTemporaryObjects()

    return nume_ddl
