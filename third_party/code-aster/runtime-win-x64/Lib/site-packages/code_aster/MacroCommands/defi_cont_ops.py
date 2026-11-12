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

from ..Messages import UTMESS
from ..Objects import (
    ContactAlgo,
    ContactNew,
    ContactParameter,
    ContactType,
    ContactVariant,
    ContactZone,
    FrictionAlgo,
    FrictionNew,
    FrictionParameter,
    FrictionType,
    InitialState,
    JacobianType,
    IntegrationType,
    PairingAlgo,
    PairingParameter,
    ParallelContactNew,
    ParallelFrictionNew,
    PairingMethod,
)
from ..Utilities import MPI


def _hasFriction(zones):
    for zone in zones:
        if zone["FROTTEMENT"] == "OUI":
            return True
    return False


def _is_Poulios_Renard_formulation(zone):
    is_Lag_PR = zone["ALGO_CONT"] == "LAGRANGIEN" and zone["VARIANTE"] == "ROBUSTE"
    is_Pena_PR = zone["ALGO_CONT"] == "PENALISATION"
    return is_Lag_PR or is_Pena_PR


def defi_cont_ops(self, **keywords):
    """Execute the command.

    Arguments:
        keywords (dict): User's keywords.
    """

    UTMESS("A", "QUALITY1_2", valk="DEFI_CONT")

    model = keywords["MODELE"]
    verbosity = keywords["INFO"]
    mesh = model.getMesh()

    if _hasFriction(keywords["ZONE"]):
        if mesh.isParallel() and MPI.ASTER_COMM_WORLD.Get_size() > 1:
            result = ParallelFrictionNew(keywords["MODELE"], mesh)
        else:
            result = FrictionNew(keywords["MODELE"])
    else:
        if mesh.isParallel() and MPI.ASTER_COMM_WORLD.Get_size() > 1:
            result = ParallelContactNew(keywords["MODELE"], mesh)
        else:
            result = ContactNew(keywords["MODELE"])

    # usefull dict
    _algo_cont = {
        "LAGRANGIEN": ContactAlgo.Lagrangian,
        "NITSCHE": ContactAlgo.Nitsche,
        "PENALISATION": ContactAlgo.Penalization,
    }
    _type_cont = {"UNILATERAL": ContactType.Unilateral, "BILATERAL": ContactType.Bilateral}
    _vari_cont = {
        "RAPIDE": ContactVariant.Fast,
        "ROBUSTE": ContactVariant.Robust,
        "SYMETRIC": ContactVariant.Symetric,
        "CLASSIQUE": ContactVariant.Classic,
    }
    _algo_frot = {
        "LAGRANGIEN": FrictionAlgo.Lagrangian,
        "NITSCHE": FrictionAlgo.Nitsche,
        "PENALISATION": FrictionAlgo.Penalization,
    }
    _type_frot = {
        "TRESCA": FrictionType.Tresca,
        "SANS": FrictionType.Without,
        "COULOMB": FrictionType.Coulomb,
        "ADHERENT": FrictionType.Stick,
    }
    _algo_pair = {"MORTAR": PairingAlgo.Mortar}
    _pair_method = {
        "RAPIDE": PairingMethod.Fast,
        "FORCEBRUTE": PairingMethod.BrutForce,
        "PANG": PairingMethod.Legacy,
    }
    _init_cont = {
        "INTERPENETRE": InitialState.Interpenetrated,
        "NON": InitialState.No,
        "OUI": InitialState.Yes,
    }
    _jac_type = {"ANALYTIQUE": JacobianType.Analytical, "PERTURBATION": JacobianType.Perturbation}
    _inte_type = {"ELEM_BASE": IntegrationType.Elembased, "SEG_BASE": IntegrationType.Segbased}
    # add global informations
    result.setVerbosity(verbosity)

    # add infomations for each ZONE
    list_zones = keywords["ZONE"]
    for zone in list_zones:
        contZone = ContactZone()

        contZone.checkNormals = zone["VERI_NORM"] == "OUI"
        contZone.setVerbosity(verbosity)
        contZone.setSlaveGroupOfCells(zone["GROUP_MA_ESCL"])
        contZone.setMasterGroupOfCells(zone["GROUP_MA_MAIT"])

        if zone.get("SANS_GROUP_MA") is not None:
            contZone.setExcludedSlaveGroupOfCells(zone["SANS_GROUP_MA"])
        if zone.get("SANS_GROUP_NO") is not None:
            contZone.setExcludedSlaveGroupOfNodes(zone["SANS_GROUP_NO"])

        if zone["LISSAGE"] == "OUI":
            contZone.hasSmoothing = True

        # contact parameters
        contParam = ContactParameter()
        contParam.setAlgorithm(_algo_cont[zone["ALGO_CONT"]])

        contParam.setVariant(ContactVariant.Empty)
        if _algo_cont[zone["ALGO_CONT"]] == ContactAlgo.Lagrangian:
            contParam.setJacobianType(_jac_type[zone["TYPE_MATR_TANG"]])
            variante = zone["VARIANTE"]
            contParam.setVariant(_vari_cont[variante])

        if _algo_cont[zone["ALGO_CONT"]] == ContactAlgo.Penalization:
            contParam.setJacobianType(_jac_type[zone["TYPE_MATR_TANG"]])
            contParam.setVariant(_vari_cont["ROBUSTE"])

        if _algo_cont[zone["ALGO_CONT"]] == ContactAlgo.Nitsche:
            if zone["SYME"] == "OUI":
                contParam.setVariant(_vari_cont["SYMETRIC"])
            else:
                contParam.setVariant(_vari_cont[zone["VARIANTE"]])

        contParam.setType(_type_cont[zone["TYPE_CONT"]])
        contParam.setCoefficient(zone["COEF_CONT"])
        contParam.setIntegrationType(_inte_type[zone["TYPE_INTE"]])
        contZone.setContactParameter(contParam)

        # friction parameters
        if zone["FROTTEMENT"] == "OUI":
            fricParam = FrictionParameter()
            fricParam.hasFriction = True
            fricParam.setAlgorithm(_algo_frot[zone["ALGO_FROT"]])
            fricParam.setType(_type_frot[zone["TYPE_FROT"]])

            if fricParam.getType() == FrictionType.Tresca:
                fricParam.setTresca(zone["TRESCA"])
            elif fricParam.getType() == FrictionType.Coulomb:
                fricParam.setCoulomb(zone["COULOMB"])

            # when using ROBUSTE (Poulios and Renard), COEF_CONT should be equal to COEF_FROT
            if _is_Poulios_Renard_formulation(zone):
                fricParam.setCoefficient(zone["COEF_CONT"])
            else:
                # in the case of undefined COEF_FROT, set it to the default value (100.)
                fricParam.setCoefficient(zone["COEF_FROT"] or 100.0)
            contZone.setFrictionParameter(fricParam)

        # pairing parameters
        pairParam = PairingParameter()
        contZone.setPairingParameter(pairParam)
        pairParam.setAlgorithm(_algo_pair[zone["APPARIEMENT"]])
        pairParam.setDistanceRatio(zone["COEF_MULT_APPA"])
        pairParam.setInitialState(_init_cont[zone["CONTACT_INIT"]])

        if zone["APPARIEMENT"] == "MORTAR":
            pairParam.setPairingTolerance(zone["APPA_TOLE"])
            pairParam.setAreaIntersectionTolerance(zone["AIRE_TOLE"])
            pairParam.setPairingMethod(_pair_method[zone["TYPE_APPA"]])

        if zone.get("CARA_ELEM") is not None:
            pairParam.setElementaryCharacteristics(zone["CARA_ELEM"])
            pairParam.hasBeamDistance = zone["DIST_POUTRE"] == "OUI"
            pairParam.hasShellDistance = zone["DIST_COQUE"] == "OUI"

        if zone.get("DIST_SUPP") is not None:
            pairParam.setDistanceFunction(zone["DIST_SUPP"])

        # build then append
        result.appendContactZone(contZone)

    # build result and contact zones
    result.build()

    return result
