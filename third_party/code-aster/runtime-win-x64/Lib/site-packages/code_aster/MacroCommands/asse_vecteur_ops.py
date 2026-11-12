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

from libaster import setFortranLoggingLevel, resetFortranLoggingLevel

from ..Utilities import force_list


def asse_vecteur_ops(self, **args):
    """Execute the command ASSE_VECTEUR.

    Arguments:
        **args (dict): User's keywords.

    Returns:
        FiledOnNodes: field on nodes assembled
    """

    verbosity = args["INFO"]
    setFortranLoggingLevel(verbosity)

    vect_elem = force_list(args["VECT_ELEM"])
    nume_ddl = args["NUME_DDL"]
    #
    result = None
    for elem in vect_elem:
        cham_no = elem.assemble(nume_ddl)
        if result is None:
            result = cham_no
        else:
            result += cham_no

    resetFortranLoggingLevel()

    return result
