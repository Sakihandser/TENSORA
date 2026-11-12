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
from ..Helpers import adapt_for_mgis_behaviour
from ..Helpers.syntax_adapters import adapt_increment_init
from ..Messages import UTMESS
from ..Objects import (
    MechanicalDirichletBC,
    MechanicalLoadFunction,
    MechanicalLoadReal,
    ParallelMechanicalLoadFunction,
    ParallelMechanicalLoadReal,
    PhysicalProblem,
)
from ..Solvers import NonLinearOperator
from ..Utilities import force_list, print_stats, reset_stats


def _contact_check(model, CONTACT):
    """Add controls to prohibit unconverted features in contact"""
    if CONTACT:
        CONTACT = force_list(CONTACT)
        # currently max=1 in C_CONTACT
        if len(CONTACT) > 1 and model.getMesh().isParallel():
            raise TypeError("Only one CONTACT factor keyword is allowed with a ParallelMesh")
        contDefi = CONTACT[0]["DEFINITION"]
        for zone in contDefi.getContactZones():
            assert not zone.hasSmoothing
            assert zone.getPairingParameter().getDistanceFunction() is None
            assert zone.getPairingParameter().getElementaryCharacteristics() is None
        if contDefi.hasFriction:
            assert CONTACT[0]["ALGO_RESO_FROT"] == "NEWTON"


def _keywords_check(keywords):
    """Add controls to prohibit unconverted features."""

    if "EXCIT" in keywords:
        for load in keywords["EXCIT"]:
            if load["TYPE_CHARGE"] not in ("FIXE_CSTE", "DIDI"):
                raise RuntimeError("TYPE_CHARGE not supported")

    if "CONVERGENCE" in keywords:
        for key in keywords["CONVERGENCE"]:
            if key in ("RESI_COMP_RELA"):
                raise RuntimeError("unsupported value in CONVERGENCE: %s" % key)

    if keywords["METHODE"] not in ["NEWTON", "SNES", "RASPEN"]:
        raise RuntimeError("unsupported value in METHODE")


def meca_non_line_ops(self, **args):
    """Execute the command.

    Arguments:
        **args (dict): User's keywords.
    """
    UTMESS("A", "QUALITY1_2", valk="MECA_NON_LINE")
    reset_stats()

    args = _F(args)
    # for compatibility with STAT_NON_LINE syntax
    args.pop("TITRE", None)
    adapt_increment_init(args, "EVOL_NOLI")

    # Add controls to prohibit unconverted features
    _contact_check(args["MODELE"], args["CONTACT"])
    _keywords_check(args)
    adapt_for_mgis_behaviour(self, args)

    kwds = {
        "ARCHIVAGE": args["ARCHIVAGE"],
        "COMPORTEMENT": args["COMPORTEMENT"],
        "CONTACT": args["CONTACT"],
        "CONVERGENCE": args["CONVERGENCE"],
        "ETAT_INIT": args["ETAT_INIT"],
        "INFO": args["INFO"],
        "METHODE": args["METHODE"],
        "NEWTON": args["NEWTON"],
        "RECH_LINEAIRE": args["RECH_LINEAIRE"],
        "SOLVEUR": args["SOLVEUR"],
        "REUSE": args["reuse"],
        "INCREMENT": args["INCREMENT"],
        "SCHEMA_TEMPS": args.get("SCHEMA_TEMPS"),
        "OBSERVATION": args["OBSERVATION"],
    }
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
                    MechanicalLoadFunction,
                    MechanicalLoadReal,
                    ParallelMechanicalLoadFunction,
                    ParallelMechanicalLoadReal,
                    MechanicalDirichletBC,
                ),
            ):
                phys_pb.addLoadFromDict(load)
            else:
                raise RuntimeError("Unknown load")

    operator = NonLinearOperator.factory(phys_pb, result=args.get("reuse"), **kwds)
    operator.run()

    print_stats()
    reset_stats()
    return operator.result
