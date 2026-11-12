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
from ..Objects import DiscreteComputation, PhysicalProblem


def calc_char_cine_ops(self, **args):
    """Execute the command.

    Arguments:
        **args (dict): User's keywords.
    """

    args = _F(args)

    setFortranLoggingLevel(args["INFO"])

    # Create physical problem
    phys_pb = PhysicalProblem(args["NUME_DDL"])

    # Add loads
    for load in args["CHAR_CINE"]:
        phys_pb.addDirichletBC(load)

    phys_pb.computeListOfLoads()

    disc_comp = DiscreteComputation(phys_pb)

    diriBCs = disc_comp.getDirichletBC(args["INST"])

    resetFortranLoggingLevel()
    deleteTemporaryObjects()

    return diriBCs
