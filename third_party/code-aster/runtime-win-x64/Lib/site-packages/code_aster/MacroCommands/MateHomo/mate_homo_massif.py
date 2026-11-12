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

import numpy as np

from ...Cata.Syntax import _F
from ...CodeCommands import (
    AFFE_CHAR_CINE,
    AFFE_CHAR_MECA,
    AFFE_CHAR_MECA_F,
    AFFE_CHAR_THER,
    FORMULE,
    MECA_STATIQUE,
    THER_LINEAIRE,
    CALC_CHAMP,
    POST_ELEM,
    CALC_TABLE,
    CREA_TABLE,
)
from ...Messages import ASSERT
from ...Objects import ThermalResultDict, ElasticResultDict
from ...Utilities import logger

from . import mate_homo_utilities as utilities

# List of all the parameters in the result table

PARAMASSIF = [
    "E_L",
    "E_T",
    "E_N",
    "NU_LT",
    "NU_LN",
    "NU_TN",
    "G_LT",
    "G_LN",
    "G_TN",
    "ALPHA_L",
    "ALPHA_T",
    "ALPHA_N",
    "RHO",
    "LAMBDA_L",
    "LAMBDA_T",
    "LAMBDA_N",
    "RHO_CP",
    "A1111",
    "A2222",
    "A3333",
    "A1122",
    "A1133",
    "A2233",
    "A1212",
    "A2323",
    "A3131",
    "NU_TL",
    "NU_NL",
    "NU_NT",
    "K11",
    "K22",
    "K33",
    "ISOTRANS",
    "TEMP_DEF_ALPHA",
]


def calc_corr_massif_syme(MODME, CHMATME, MODTH, CHMATTH, L_INST, alpha_calc, ls_group_ma):
    """
    Compute the elastic and thermal correctors for the MASSIF (Bulk) case.

    This function performs a series of mechanical and thermal analyses to compute
    the corrector fields for a bulk material. Specifically, it conducts seven
    mechanical static analyses (MECA_STATIQUE) and three thermal linear analyses
    (THER_LINEAIRE). If the group `face_int` is present in the mesh, an
    additional mechanical static analysis is performed to compute the internal
    pressure corrector.

    The function also handles the computation of homogeneous parameters for
    various temperature values by treating the temperature as a pseudo-time
    value. This allows for the calculation of temperature-dependent properties.

    Args:
        MODME (Model): The mechanical model used for the analyses.
        CHMATME (MaterialField): The mechanical material field containing
            material properties.
        MODTH (Model): The thermal model used for the analyses.
        CHMATTH (MaterialField): The thermal material field containing material
            properties.
        L_INST (list[float]): A list of pseudo-time values representing
            homogenization temperature values.
        alpha_calc (list): A list of dilatation coefficients as a function of
            pseudo-time (temperature).
        ls_group_ma (list[str]): A list of groups where properties are
            prescribed.

    Returns:
        ElasticResultDict: A dictionary containing the elastic correctors for
            the bulk material.
        ThermalResultDict: A dictionary containing the thermal correctors for
            the bulk material.
    """

    # Chargements pour calcul des correcteurs MECANIQUES
    # =======================================================================

    SYME_MECA_XX = AFFE_CHAR_CINE(
        MODELE=MODME,
        MECA_IMPO=(
            _F(GROUP_MA="face_xmin", DX=0.0),
            _F(GROUP_MA="face_ymin", DY=0.0),
            _F(GROUP_MA="face_zmin", DZ=0.0),
            _F(GROUP_MA="face_xmax", DX=0.0),
            _F(GROUP_MA="face_ymax", DY=0.0),
            _F(GROUP_MA="face_zmax", DZ=0.0),
        ),
    )

    ANTI_MECA_12 = AFFE_CHAR_CINE(
        MODELE=MODME,
        MECA_IMPO=(
            _F(GROUP_MA="face_xmin", DY=0.0, DZ=0),
            _F(GROUP_MA="face_ymin", DX=0.0, DZ=0),
            _F(GROUP_MA="face_zmin", DZ=0.0),
            _F(GROUP_MA="face_xmax", DY=0.0, DZ=0),
            _F(GROUP_MA="face_ymax", DX=0.0, DZ=0),
            _F(GROUP_MA="face_zmax", DZ=0.0),
        ),
    )

    ANTI_MECA_31 = AFFE_CHAR_CINE(
        MODELE=MODME,
        MECA_IMPO=(
            _F(GROUP_MA="face_xmin", DZ=0.0, DY=0.0),
            _F(GROUP_MA="face_ymin", DY=0.0),
            _F(GROUP_MA="face_zmin", DX=0.0, DY=0.0),
            _F(GROUP_MA="face_xmax", DZ=0.0, DY=0.0),
            _F(GROUP_MA="face_ymax", DY=0.0),
            _F(GROUP_MA="face_zmax", DX=0.0, DY=0.0),
        ),
    )

    ANTI_MECA_23 = AFFE_CHAR_CINE(
        MODELE=MODME,
        MECA_IMPO=(
            _F(GROUP_MA="face_xmin", DX=0.0),
            _F(GROUP_MA="face_ymin", DZ=0.0, DX=0.0),
            _F(GROUP_MA="face_zmin", DY=0.0, DX=0.0),
            _F(GROUP_MA="face_xmax", DX=0.0),
            _F(GROUP_MA="face_ymax", DZ=0.0, DX=0.0),
            _F(GROUP_MA="face_zmax", DY=0.0, DX=0.0),
        ),
    )

    CHAR11 = AFFE_CHAR_MECA(MODELE=MODME, PRE_EPSI=_F(GROUP_MA=ls_group_ma, EPXX=-1.0))

    CHAR22 = AFFE_CHAR_MECA(MODELE=MODME, PRE_EPSI=_F(GROUP_MA=ls_group_ma, EPYY=-1.0))

    CHAR12 = AFFE_CHAR_MECA(MODELE=MODME, PRE_EPSI=_F(GROUP_MA=ls_group_ma, EPXY=-0.5))

    CHAR33 = AFFE_CHAR_MECA(MODELE=MODME, PRE_EPSI=_F(GROUP_MA=ls_group_ma, EPZZ=-1.0))

    CHAR31 = AFFE_CHAR_MECA(MODELE=MODME, PRE_EPSI=_F(GROUP_MA=ls_group_ma, EPXZ=-0.5))

    CHAR23 = AFFE_CHAR_MECA(MODELE=MODME, PRE_EPSI=_F(GROUP_MA=ls_group_ma, EPYZ=-0.5))

    CHARDIL = AFFE_CHAR_MECA_F(
        MODELE=MODME,
        PRE_EPSI=[
            _F(
                GROUP_MA=item["GROUP_MA"],
                EPXX=FORMULE(
                    VALE="-1.0*ALPHA_DIL(INST)",
                    NOM_PARA=("INST",),
                    ALPHA_DIL=item["FONC_ALPHA_TIME"],
                ),
                EPYY=FORMULE(
                    VALE="-1.0*ALPHA_DIL(INST)",
                    NOM_PARA=("INST",),
                    ALPHA_DIL=item["FONC_ALPHA_TIME"],
                ),
                EPZZ=FORMULE(
                    VALE="-1.0*ALPHA_DIL(INST)",
                    NOM_PARA=("INST",),
                    ALPHA_DIL=item["FONC_ALPHA_TIME"],
                ),
            )
            for item in alpha_calc
        ],
    )

    # Chargements pour calcul des correcteurs THERMIQUES
    # =======================================================================

    SYME_THER_11 = AFFE_CHAR_CINE(
        MODELE=MODTH,
        THER_IMPO=(_F(GROUP_MA="face_xmin", TEMP=0.0), _F(GROUP_MA="face_xmax", TEMP=0.0)),
    )

    SYME_THER_22 = AFFE_CHAR_CINE(
        MODELE=MODTH,
        THER_IMPO=(_F(GROUP_MA="face_ymin", TEMP=0.0), _F(GROUP_MA="face_ymax", TEMP=0.0)),
    )

    SYME_THER_33 = AFFE_CHAR_CINE(
        MODELE=MODTH,
        THER_IMPO=(_F(GROUP_MA="face_zmin", TEMP=0.0), _F(GROUP_MA="face_zmax", TEMP=0.0)),
    )

    CHAR1 = AFFE_CHAR_THER(MODELE=MODTH, PRE_GRAD_TEMP=_F(GROUP_MA=ls_group_ma, FLUX_X=-1.0))

    CHAR2 = AFFE_CHAR_THER(MODELE=MODTH, PRE_GRAD_TEMP=_F(GROUP_MA=ls_group_ma, FLUX_Y=-1.0))

    CHAR3 = AFFE_CHAR_THER(MODELE=MODTH, PRE_GRAD_TEMP=_F(GROUP_MA=ls_group_ma, FLUX_Z=-1.0))

    elas_fields = ElasticResultDict()
    ther_fields = ThermalResultDict()

    # Calcul des correcteurs MECANIQUES de DILATATION
    # ======================================================================

    elas_fields["CORR_DILA"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(_F(CHARGE=CHARDIL), _F(CHARGE=SYME_MECA_XX)),
        OPTION="SANS",
    )

    # Calcul des correcteurs MECANIQUES
    # ======================================================================

    elas_fields["CORR_MECA11"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(_F(CHARGE=CHAR11), _F(CHARGE=SYME_MECA_XX)),
        OPTION="SANS",
    )

    elas_fields["CORR_MECA22"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(_F(CHARGE=CHAR22), _F(CHARGE=SYME_MECA_XX)),
        OPTION="SANS",
    )

    elas_fields["CORR_MECA12"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(_F(CHARGE=CHAR12), _F(CHARGE=ANTI_MECA_12)),
        OPTION="SANS",
    )

    elas_fields["CORR_MECA33"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(_F(CHARGE=CHAR33), _F(CHARGE=SYME_MECA_XX)),
        OPTION="SANS",
    )

    elas_fields["CORR_MECA31"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(_F(CHARGE=CHAR31), _F(CHARGE=ANTI_MECA_31)),
        OPTION="SANS",
    )

    elas_fields["CORR_MECA23"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(_F(CHARGE=CHAR23), _F(CHARGE=ANTI_MECA_23)),
        OPTION="SANS",
    )

    # Calcul des correcteurs MECANIQUES de pression interne
    # ======================================================================

    if "face_int" in MODME.getMesh().getGroupsOfCells():
        CHAR_PINT = AFFE_CHAR_MECA(MODELE=MODME, PRES_REP=_F(GROUP_MA="face_int", PRES=1.0))
        elas_fields["CORR_PINT"] = MECA_STATIQUE(
            MODELE=MODME,
            CHAM_MATER=CHMATME,
            LIST_INST=L_INST,
            EXCIT=(_F(CHARGE=CHAR_PINT), _F(CHARGE=SYME_MECA_XX)),
            OPTION="SANS",
        )

    # Calcul des correcteurs THERMIQUES
    # ======================================================================
    ther_fields["CORR_THER11"] = THER_LINEAIRE(
        MODELE=MODTH,
        CHAM_MATER=CHMATTH,
        TYPE_CALCUL="STAT",
        INCREMENT=_F(LIST_INST=L_INST),
        EXCIT=(_F(CHARGE=CHAR1), _F(CHARGE=SYME_THER_11)),
    )

    ther_fields["CORR_THER22"] = THER_LINEAIRE(
        MODELE=MODTH,
        CHAM_MATER=CHMATTH,
        TYPE_CALCUL="STAT",
        INCREMENT=_F(LIST_INST=L_INST),
        EXCIT=(_F(CHARGE=CHAR2), _F(CHARGE=SYME_THER_22)),
    )

    ther_fields["CORR_THER33"] = THER_LINEAIRE(
        MODELE=MODTH,
        CHAM_MATER=CHMATTH,
        TYPE_CALCUL="STAT",
        INCREMENT=_F(LIST_INST=L_INST),
        EXCIT=(_F(CHARGE=CHAR3), _F(CHARGE=SYME_THER_33)),
    )

    return elas_fields, ther_fields


def calc_loimel_massif(DEPLMATE, ls_group_tout):
    """
    Compute the average value of material parameters on the VER mesh.

    This function calculates the average values of various material parameters
    on the VER mesh using a pseudo-result obtained with a 0-load boundary
    condition. It leverages existing operators (CALC_CHAMP and POST_ELEM) to
    perform the calculations.

    List of computed parameters:
    - LAME_1: First Lamé coefficient
    - LAME_2: Second Lamé coefficient
    - ALPHA_3K: Compression modulus
    - RHO: Density
    - RHO_CP: Product of density with specific heat
    - LAMBDA_THER: Thermal conductivity

    Args:
        DEPLMATE (ElasticResult): Mechanical result from the 0-load boundary
            condition.
        ls_group_tout (list[str]): List of groups where properties are
            prescribed.

    Returns:
        dict: A dictionary containing the average properties values as a
            function of pseudo-time (temperature).
    """

    LAME_1 = FORMULE(NOM_PARA=("E", "NU"), VALE="E*NU/((1+NU)*(1-2*NU))")
    LAME_2 = FORMULE(NOM_PARA=("E", "NU"), VALE="E/(2*(1+NU))")
    ALPHA_3K = FORMULE(NOM_PARA=("E", "NU", "ALPHA"), VALE="ALPHA*E/(1-2*NU)")

    RESUMATE = CALC_CHAMP(
        RESULTAT=DEPLMATE,
        GROUP_MA=ls_group_tout,
        PROPRIETES=("MATE_ELGA",),
        CHAM_UTIL=_F(FORMULE=(LAME_1, LAME_2, ALPHA_3K), NOM_CHAM="MATE_ELGA", NUME_CHAM_RESU=1),
    )

    MATE_INTE = POST_ELEM(
        RESULTAT=RESUMATE,
        MODELE=RESUMATE.getModel(),
        INTEGRALE=_F(
            GROUP_MA=ls_group_tout,
            NOM_CMP=("RHO", "RHO_CP", "LAMBDA"),
            NOM_CHAM="MATE_ELGA",
            TYPE_MAILLE="3D",
        ),
    )

    LAME_INTE = POST_ELEM(
        RESULTAT=RESUMATE,
        MODELE=RESUMATE.getModel(),
        INTEGRALE=_F(
            GROUP_MA=ls_group_tout,
            NOM_CMP=("X1", "X2", "X3"),
            NOM_CHAM="UT01_ELGA",
            TYPE_MAILLE="3D",
        ),
    )

    if len(ls_group_tout) > 1:
        MATE_INTE = CALC_TABLE(
            reuse=MATE_INTE,
            TABLE=MATE_INTE,
            ACTION=(
                _F(OPERATION="FILTRE", NOM_PARA="GROUP_MA", CRIT_COMP="EQ", VALE_K="UNION_GROUP_MA")
            ),
        )

        LAME_INTE = CALC_TABLE(
            reuse=LAME_INTE,
            TABLE=LAME_INTE,
            ACTION=(
                _F(OPERATION="FILTRE", NOM_PARA="GROUP_MA", CRIT_COMP="EQ", VALE_K="UNION_GROUP_MA")
            ),
        )

    out = {}
    out["LAME1"], out["LAME2"], out["ALPHA3K"] = [
        LAME_INTE.EXTR_TABLE().values()[key] for key in ("INTE_X1", "INTE_X2", "INTE_X3")
    ]

    out["RHO"], out["RHO_CP"], out["LAMBDA_THER"] = [
        MATE_INTE.EXTR_TABLE().values()[key] for key in ("INTE_RHO", "INTE_RHO_CP", "INTE_LAMBDA")
    ]

    return out


def calc_tabpara_massif(DEPLMATE, volume_ver, ls_group_ma, varc_name, ls_varc, **fields):
    """
    Compute the homogeneous properties values.

    This function calculates the homogeneous elastic and thermal properties for
    a bulk material (MASSIF) case. It uses mechanical and thermal corrector
    fields to compute the properties at various temperatures or irradiation
    levels.

    Args:
        DEPLMATE (ElasticResult): Mechanical result from the 0-load boundary
            condition.
        volume_ver (float): Volume of the Volume Element Representative (VER).
        ls_group_ma (list[str]): List of groups where properties are prescribed.
        varc_name (str): Name of the command variable (e.g., TEMP for
            temperature, IRRA for irradiation).
        ls_varc (list[float]): List of values for the command variable at which
            parameters are computed.
        **fields (ElasticResultDict, ThermalResultDict): Corrector fields for
            mechanical and thermal analyses.

    Returns:
        list[np.ndarray]: Homogeneous elastic matrix for each value of the
            command variable.
        list[np.ndarray]: Homogeneous thermal matrix for each value of the
            command variable.
        Table: Aster table with all the homogeneous parameters, ready for
            DEFI_MATERIAU.
    """

    CORR_MECA11 = fields["CORR_MECA11"]
    CORR_MECA22 = fields["CORR_MECA22"]
    CORR_MECA33 = fields["CORR_MECA33"]
    CORR_MECA12 = fields["CORR_MECA12"]
    CORR_MECA31 = fields["CORR_MECA31"]
    CORR_MECA23 = fields["CORR_MECA23"]
    CORR_DILA = fields["CORR_DILA"]
    CORR_THER11 = fields["CORR_THER11"]
    CORR_THER22 = fields["CORR_THER22"]
    CORR_THER33 = fields["CORR_THER33"]

    insts_meca = CORR_MECA11.getAccessParameters()["INST"]
    insts_ther = CORR_THER11.getAccessParameters()["INST"]

    ASSERT(len(insts_meca) == len(insts_ther) == len(ls_varc))

    dictpara = utilities.create_empty_dictpara([varc_name] + PARAMASSIF)
    loimel = calc_loimel_massif(DEPLMATE, ls_group_ma)
    tda = utilities.get_temp_def_alpha_result(DEPLMATE)
    ls_A_hom = {}
    ls_K_hom = {}

    for i, (inst_meca, inst_ther) in enumerate(zip(insts_meca, insts_ther)):
        ASSERT(inst_meca == inst_ther)

        work_dila_11 = utilities.cross_work(CORR_MECA11, CORR_DILA, inst_meca, ls_group_ma)
        work_dila_22 = utilities.cross_work(CORR_MECA22, CORR_DILA, inst_meca, ls_group_ma)
        work_dila_33 = utilities.cross_work(CORR_MECA33, CORR_DILA, inst_meca, ls_group_ma)

        work_ther_11 = utilities.cross_work(CORR_THER11, CORR_THER11, inst_ther, ls_group_ma)
        work_ther_22 = utilities.cross_work(CORR_THER22, CORR_THER22, inst_ther, ls_group_ma)
        work_ther_33 = utilities.cross_work(CORR_THER33, CORR_THER33, inst_ther, ls_group_ma)

        work_meca_11_11 = utilities.cross_work(CORR_MECA11, CORR_MECA11, inst_meca, ls_group_ma)
        work_meca_22_22 = utilities.cross_work(CORR_MECA22, CORR_MECA22, inst_meca, ls_group_ma)
        work_meca_33_33 = utilities.cross_work(CORR_MECA33, CORR_MECA33, inst_meca, ls_group_ma)

        work_meca_11_22 = utilities.cross_work(CORR_MECA11, CORR_MECA22, inst_meca, ls_group_ma)
        work_meca_11_33 = utilities.cross_work(CORR_MECA11, CORR_MECA33, inst_meca, ls_group_ma)
        work_meca_22_33 = utilities.cross_work(CORR_MECA22, CORR_MECA33, inst_meca, ls_group_ma)

        work_meca_12_12 = utilities.cross_work(CORR_MECA12, CORR_MECA12, inst_meca, ls_group_ma)
        work_meca_23_23 = utilities.cross_work(CORR_MECA23, CORR_MECA23, inst_meca, ls_group_ma)
        work_meca_31_31 = utilities.cross_work(CORR_MECA31, CORR_MECA31, inst_meca, ls_group_ma)

        ########################
        # Matrice homogeneisee
        lambda_ther = loimel["LAMBDA_THER"][i]

        K11_hom = (1 / volume_ver) * (lambda_ther - work_ther_11)
        K22_hom = (1 / volume_ver) * (lambda_ther - work_ther_22)
        K33_hom = (1 / volume_ver) * (lambda_ther - work_ther_33)

        # fmt: off
        K_hom = np.array([[K11_hom, 0,       0      ],
                          [0,       K22_hom, 0      ],
                          [0,       0,       K33_hom]])
        # fmt: on
        ls_K_hom[inst_ther] = K_hom

        lambda_meca = loimel["LAME1"][i]
        mu_meca = loimel["LAME2"][i]

        A1111_hom = (1 / volume_ver) * ((lambda_meca + 2 * mu_meca) - work_meca_11_11)
        A2222_hom = (1 / volume_ver) * ((lambda_meca + 2 * mu_meca) - work_meca_22_22)
        A3333_hom = (1 / volume_ver) * ((lambda_meca + 2 * mu_meca) - work_meca_33_33)

        A1122_hom = (1 / volume_ver) * (lambda_meca - work_meca_11_22)
        A1133_hom = (1 / volume_ver) * (lambda_meca - work_meca_11_33)
        A2233_hom = (1 / volume_ver) * (lambda_meca - work_meca_22_33)

        A1212_hom = (1 / volume_ver) * (mu_meca - work_meca_12_12)
        A2323_hom = (1 / volume_ver) * (mu_meca - work_meca_23_23)
        A3131_hom = (1 / volume_ver) * (mu_meca - work_meca_31_31)

        check_isotrop_trans = abs(round((2 * A1212_hom - A1111_hom + A1122_hom) / A1212_hom, 12))

        # fmt: off
        A_hom = np.array([[A1111_hom, A1122_hom, A1133_hom, 0,         0,         0         ],
                          [A1122_hom, A2222_hom, A2233_hom, 0,         0,         0         ],
                          [A1133_hom, A2233_hom, A3333_hom, 0,         0,         0         ],
                          [0,         0,         0,         A1212_hom, 0,         0         ],
                          [0,         0,         0,         0,         A2323_hom, 0         ],
                          [0,         0,         0,         0,         0,         A3131_hom]])
        # fmt: on
        ls_A_hom[inst_meca] = A_hom

        A_inv = np.linalg.inv(A_hom)
        K_inv = np.linalg.inv(K_hom)

        LAMBDA_L, LAMBDA_T, LAMBDA_N = K_inv.diagonal() ** -1

        E_L, E_T, E_N, G_LT, G_LN, G_TN = A_inv.diagonal() ** -1

        alpha_3k_meca = loimel["ALPHA3K"][i]
        Bdil_11 = (1 / volume_ver) * (alpha_3k_meca - work_dila_11)
        Bdil_22 = (1 / volume_ver) * (alpha_3k_meca - work_dila_22)
        Bdil_33 = (1 / volume_ver) * (alpha_3k_meca - work_dila_33)

        ALPHA_L, ALPHA_T, ALPHA_N = np.dot(A_inv, (Bdil_11, Bdil_22, Bdil_33, 0, 0, 0))[:3]

        NU_TL = -A_inv[0, 1] / A_inv[1, 1]
        NU_NL = -A_inv[0, 2] / A_inv[2, 2]
        NU_NT = -A_inv[1, 2] / A_inv[2, 2]

        NU_LT = -A_inv[1, 0] / A_inv[0, 0]
        NU_LN = -A_inv[2, 0] / A_inv[0, 0]
        NU_TN = -A_inv[2, 1] / A_inv[1, 1]

        RHO = (1 / volume_ver) * loimel["RHO"][i]
        RHO_CP = (1 / volume_ver) * loimel["RHO_CP"][i]

        logger.debug(f"<HOMO-WORK><V {inst_ther}>: THER_11 {work_ther_11}")
        logger.debug(f"<HOMO-WORK><V {inst_ther}>: THER_22 {work_ther_22}")
        logger.debug(f"<HOMO-WORK><V {inst_ther}>: THER_22 {work_ther_33}")

        logger.debug(f"<HOMO-WORK><V {inst_meca}>: DILA_11 {work_dila_11}")
        logger.debug(f"<HOMO-WORK><V {inst_meca}>: DILA_22 {work_dila_22}")
        logger.debug(f"<HOMO-WORK><V {inst_meca}>: DILA_22 {work_dila_33}")

        logger.debug(f"<HOMO-WORK><V {inst_meca}>: MECA_11_11 {work_meca_11_11}")
        logger.debug(f"<HOMO-WORK><V {inst_meca}>: MECA_22_22 {work_meca_22_22}")
        logger.debug(f"<HOMO-WORK><V {inst_meca}>: MECA_33_33 {work_meca_33_33}")

        logger.debug(f"<HOMO-WORK><V {inst_meca}>: MECA_11_22 {work_meca_11_22}")
        logger.debug(f"<HOMO-WORK><V {inst_meca}>: MECA_22_33 {work_meca_22_33}")
        logger.debug(f"<HOMO-WORK><V {inst_meca}>: MECA_22_33 {work_meca_22_33}")

        logger.debug(f"<HOMO-WORK><V {inst_meca}>: MECA_12_12 {work_meca_12_12}")
        logger.debug(f"<HOMO-WORK><V {inst_meca}>: MECA_23_23 {work_meca_23_23}")
        logger.debug(f"<HOMO-WORK><V {inst_meca}>: MECA_31_31 {work_meca_31_31}")

        logger.debug(f"<HOMO-LOIMEL><V {inst_ther}>: LAMBDA THER {lambda_ther}")
        logger.debug(f"<HOMO-LOIMEL><V {inst_meca}>: LAMBDA LAME {lambda_meca}")
        logger.debug(f"<HOMO-LOIMEL><V {inst_meca}>: MU LAME {mu_meca}")
        logger.debug(f"<HOMO-LOIMEL><V {inst_meca}>: ALPHA3K {alpha_3k_meca}")
        logger.debug(f"<HOMO-VOLUME><V {inst_meca}>: VER {volume_ver}")

        dictpara["E_L"].append(E_L)
        dictpara["E_T"].append(E_T)
        dictpara["E_N"].append(E_N)
        dictpara["NU_LT"].append(NU_LT)
        dictpara["NU_LN"].append(NU_LN)
        dictpara["NU_TN"].append(NU_TN)
        dictpara["G_LT"].append(G_LT)
        dictpara["G_LN"].append(G_LN)
        dictpara["G_TN"].append(G_TN)
        dictpara["ALPHA_L"].append(ALPHA_L)
        dictpara["ALPHA_T"].append(ALPHA_T)
        dictpara["ALPHA_N"].append(ALPHA_N)
        dictpara["LAMBDA_L"].append(LAMBDA_L)
        dictpara["LAMBDA_T"].append(LAMBDA_T)
        dictpara["LAMBDA_N"].append(LAMBDA_N)
        dictpara["A1111"].append(A1111_hom)
        dictpara["A2222"].append(A2222_hom)
        dictpara["A3333"].append(A3333_hom)
        dictpara["A1122"].append(A1122_hom)
        dictpara["A1133"].append(A1133_hom)
        dictpara["A2233"].append(A2233_hom)
        dictpara["A1212"].append(A1212_hom)
        dictpara["A2323"].append(A2323_hom)
        dictpara["A3131"].append(A3131_hom)
        dictpara["NU_TL"].append(NU_TL)
        dictpara["NU_NL"].append(NU_NL)
        dictpara["NU_NT"].append(NU_NT)
        dictpara["K11"].append(K11_hom)
        dictpara["K22"].append(K22_hom)
        dictpara["K33"].append(K33_hom)
        dictpara["RHO"].append(RHO)
        dictpara["RHO_CP"].append(RHO_CP)
        dictpara["ISOTRANS"].append(check_isotrop_trans)
        dictpara["TEMP_DEF_ALPHA"].append(tda)

    dictpara[varc_name] = ls_varc

    tabpara = CREA_TABLE(LISTE=[_F(PARA=para, LISTE_R=values) for para, values in dictpara.items()])

    return ls_A_hom, ls_K_hom, tabpara
