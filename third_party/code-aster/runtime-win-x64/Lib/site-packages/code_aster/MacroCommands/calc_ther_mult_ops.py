# coding=utf-8
# --------------------------------------------------------------------
# Copyright (C) 1991 - 2026 - EDF - www.code-aster.org
# This file is part of code_aster.
#
# code_aster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# code_aster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with code_aster.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

from ..CodeCommands import THER_NON_LINE, DEFI_FONCTION, DEFI_CONSTANTE, AFFE_CHAR_THER_F
from ..Messages import UTMESS
from ..Cata.Syntax import _F
from ..Objects import ThermalResultDict


def calc_ther_mult_ops(self, **args):
    """
    MACRO for multiple thermal analysis
    """
    args = _F(args)

    # Model definition
    MODELE = args.get("MODELE")
    CARA_ELEM = args.get("CARA_ELEM")
    CHAM_MATER = args.get("CHAM_MATER")
    CHAR_THER_GLOBAL = args.get("CHAR_THER_GLOBAL")
    # Timestepping
    # LIST_INST = args.get("LIST_INST")
    # Thermal resolution parameter
    PARM_THETA = args.get("PARM_THETA")
    # Thermal loading case
    CAS_CHARGE = args.get("CAS_CHARGE")

    CONVERGENCE = args.get("CONVERGENCE")

    SOLVEUR = args.get("SOLVEUR")

    NEWTON = args.get("NEWTON")

    # ------------------------------------------------
    #        Resolution
    # ------------------------------------------------
    # ------------------------------------ Mesh verification ---------------------------------
    # if mesh is quadratic, raise an alarm about the possibility of getting false results
    mesh = MODELE.getMesh()
    if mesh.isQuadratic():
        UTMESS("A", "CALCTHERMULT_1", valk=mesh.getName())

    # ------------------------------------ CHOC_UNIT group_ma verification ---------------------------------
    # check if there is no intersection between group_ma of all CAS_CHARGE with "TYPE_CHARGE" == "CHOC_UNIT"
    group_ma_elem_id = [
        list(set(mesh.getCells(grma)))
        for grma in [
            cas_choc["GROUP_MA"]
            for cas_choc in CAS_CHARGE
            if cas_choc["TYPE_CHARGE"] == "CHOC_UNIT"
        ]
    ]
    group_ma_elem_id_flat = sum(group_ma_elem_id, [])
    if len(set(group_ma_elem_id_flat)) - len(group_ma_elem_id_flat) < 0:
        UTMESS("E", "CALCTHERMULT_2")

    # ------------------------------------ Thermal resolution ---------------------------------
    ther_dict = ThermalResultDict("ther_dict")

    fonction_zero = DEFI_FONCTION(
        NOM_PARA="INST", VALE=(0.0, 0.0, 1.0, 0.0), PROL_DROITE="CONSTANT"
    )

    chgt_cas = {}
    for cas in CAS_CHARGE:
        chgt_cas[cas["NOM_CAS"]] = []

        # common thermal load
        if CHAR_THER_GLOBAL is not None:
            for charge in CHAR_THER_GLOBAL:
                chgt_cas[cas["NOM_CAS"]].append({"CHARGE": charge})

        # TYPE_CHARGE = "CLASSIQUE"
        # if cas["TYPE_CHARGE"] == "CLASSIQUE":
        # Classical loading
        if cas["EXCIT"] is not None:
            chgt_cas[cas["NOM_CAS"]].append({"CHARGE": cas["EXCIT"]})

            # # thermal resolution
            # ther_dict[cas["NOM_CAS"]] = THER_NON_LINE(
            #     CHAM_MATER=CHAM_MATER,
            #     CARA_ELEM=CARA_ELEM,
            #     EXCIT=(chgt_cas[cas["NOM_CAS"]]),
            #     INCREMENT=_F(LIST_INST=LIST_INST),
            #     CONVERGENCE=_F(RESI_GLOB_MAXI=1e-9),
            #     PARM_THETA=PARM_THETA,
            #     MODELE=MODELE,
            # )

        # TYPE_CHARGE = "CHOC_UNIT"
        # Unit shock loading
        # if cas["TYPE_CHARGE"] == "CHOC_UNIT":
        if cas["COEF_H"] is not None:
            # if LIST_INST for the case is empty, use the common LIST_INST
            # if cas["LIST_INST"] is not None:
            #    cas["LIST_INST"] = LIST_INST
            # function and loading creation
            fonction_choc = DEFI_FONCTION(
                NOM_PARA="INST", VALE=(0.0, 0.0, cas["DUREE_CHOC"], 1.0), PROL_DROITE="CONSTANT"
            )
            coefh = DEFI_CONSTANTE(VALE=cas["COEF_H"])
            fkw = AFFE_CHAR_THER_F(
                MODELE=MODELE,
                ECHANGE=_F(COEF_H=coefh, GROUP_MA=cas["GROUP_MA"], TEMP_EXT=fonction_choc),
            )

            chgt_cas[cas["NOM_CAS"]].append({"CHARGE": fkw})

            # on other group_ma temperature has to be zero
            for other_cas in CAS_CHARGE:
                if other_cas["COEF_H"] is not None and other_cas["NOM_CAS"] != cas["NOM_CAS"]:
                    coefh = DEFI_CONSTANTE(VALE=other_cas["COEF_H"])
                    fkw = AFFE_CHAR_THER_F(
                        MODELE=MODELE,
                        ECHANGE=_F(
                            COEF_H=coefh, GROUP_MA=other_cas["GROUP_MA"], TEMP_EXT=fonction_zero
                        ),
                    )

                    chgt_cas[cas["NOM_CAS"]].append({"CHARGE": fkw})

            # thermal resolution
        ther_dict[cas["NOM_CAS"]] = THER_NON_LINE(
            CHAM_MATER=CHAM_MATER,
            CARA_ELEM=CARA_ELEM,
            EXCIT=(chgt_cas[cas["NOM_CAS"]]),
            INCREMENT=_F(LIST_INST=cas["LIST_INST"]),
            ETAT_INIT=_F(VALE=0),
            PARM_THETA=PARM_THETA,
            MODELE=MODELE,
            CONVERGENCE=CONVERGENCE,
            SOLVEUR=SOLVEUR,
            NEWTON=NEWTON,
            METHODE="NEWTON",
        )
    return ther_dict
