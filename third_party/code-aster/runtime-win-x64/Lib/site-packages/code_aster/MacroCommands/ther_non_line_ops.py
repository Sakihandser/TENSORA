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
from ..Helpers.syntax_adapters import adapt_increment_init
from ..Objects import (
    ParallelThermalLoadFunction,
    ParallelThermalLoadReal,
    PhysicalProblem,
    ThermalDirichletBC,
    ThermalLoadFunction,
    ThermalLoadReal,
)
from ..Solvers import NonLinearOperator
from ..Utilities import force_list, print_stats, reset_stats
from .Utils.ther_non_line_fort_op import THER_NON_LINE_FORT


def _use_fortran(keywords):
    excluded_keys = ("OBSERVATION",)

    for key in excluded_keys:
        if key in keywords:
            return True

    if keywords["METHODE"] in ("MODELE_REDUIT",):
        return True

    for comp in force_list(keywords["COMPORTEMENT"]):
        if comp["RELATION"] != "THER_NL":
            return True

    affi = keywords["AFFICHAGE"]
    if (
        "UNITE" in affi
        or "PAS" in affi
        or affi["INFO_RESIDU"] == "OUI"
        or affi["INFO_TEMP"] == "OUI"
    ):
        return True

    for load in keywords["EXCIT"]:
        if isinstance(load["CHARGE"], (ThermalLoadFunction, ThermalLoadReal)):
            if load["CHARGE"].hasLoadResult():
                return True

    return False


def ther_non_line_ops(self, **args):
    """Execute the command.

    Arguments:
        **args (dict): User's keywords.
    """
    args = _F(args)
    if _use_fortran(args):
        return THER_NON_LINE_FORT(**args)

    reset_stats()
    adapt_increment_init(args, "EVOL_THER")
    verbosity = args["INFO"]

    # Add parameters
    kwds = dict(
        ARCHIVAGE=args["ARCHIVAGE"],
        COMPORTEMENT=args["COMPORTEMENT"],
        CONVERGENCE=args["CONVERGENCE"],
        ETAT_INIT=args["ETAT_INIT"],
        INFO=args["INFO"],
        METHODE=args["METHODE"],
        NEWTON=args["NEWTON"],
        RECH_LINEAIRE=args["RECH_LINEAIRE"],
        SOLVEUR=args["SOLVEUR"],
        TYPE_CALCUL=args["TYPE_CALCUL"],
        INCREMENT=args["INCREMENT"],
        REUSE=args["reuse"],
        SCHEMA_TEMPS=args.get("SCHEMA_TEMPS"),
    )
    if kwds["SOLVEUR"]["METHODE"] == "PETSC":
        if kwds["SOLVEUR"]["PRE_COND"] == "LDLT_SP":
            kwds["SOLVEUR"]["REAC_PRECOND"] = 0

    phys_pb = PhysicalProblem(args["MODELE"], args["CHAM_MATER"], args["CARA_ELEM"])
    # Add loads
    if args["EXCIT"]:
        for load in args["EXCIT"]:
            if isinstance(
                load["CHARGE"],
                (
                    ThermalLoadFunction,
                    ThermalLoadReal,
                    ParallelThermalLoadFunction,
                    ParallelThermalLoadReal,
                    ThermalDirichletBC,
                ),
            ):
                phys_pb.addLoadFromDict(load)
            else:
                raise RuntimeError("Unknown load")

    operator = NonLinearOperator.factory(phys_pb, result=args.get("RESULTAT"), **kwds)
    operator.run()

    if verbosity > 1:
        print_stats()
    reset_stats()
    return operator.result
