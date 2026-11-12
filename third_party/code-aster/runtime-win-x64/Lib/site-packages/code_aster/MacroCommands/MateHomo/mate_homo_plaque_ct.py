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


from ...Cata.Syntax import _F
from ...CodeCommands import (
    AFFE_CHAR_CINE,
    AFFE_CHAR_MECA,
    AFFE_CHAR_MECA_F,
    FORMULE,
    MECA_STATIQUE,
    CALC_MATR_ELEM,
    CALC_VECT_ELEM,
    ASSE_VECTEUR,
    NUME_DDL,
)
from ...Messages import ASSERT
from ...Objects import ThermalResultDict, ElasticResultDict


def calc_corr_plaque_ct(
    MODME, CHMATME, MODTH, CHMATTH, L_INST, alpha_calc, ls_group_ma, ep_ver, type_homo
):
    """
    Compute the elastic correctors for PLAQUE (Plate) case.

    Thermal homogenization is not implemented yet; this function performs 6
    MECA_STATIQUE.

    The computation of the homogeneous parameters for several temperature values
    is done by considering the temperature as a pseudo-time value.

    Args:
        MODME (Model): Mechanical model.
        CHMATME (MaterialField): Mechanical material field.
        MODTH (Model): Thermal model.
        CHMATTH (MaterialField): Thermal material field.
        L_INST (list[float]): List of pseudo-time values (homogenization
            temperature values).
        ls_group_ma (list[str]): List of groups where properties are prescribed.
        ep_ver (float): The VER thickness.
        type_homo (str): Name of the homogeneization type

    Returns:
        ElasticResultDict: Dictionary of elastic correctors.
        ThermalResultDict: Dictionary of thermal correctors. Empty.
    """

    SYME_MECA_XX = AFFE_CHAR_CINE(
        MODELE=MODME,
        MECA_IMPO=(
            _F(GROUP_NO="lock_rigi", DZ=0.0),
            _F(GROUP_MA="face_xmin", DX=0.0),
            _F(GROUP_MA="face_ymin", DY=0.0),
            _F(GROUP_MA="face_xmax", DX=0.0),
            _F(GROUP_MA="face_ymax", DY=0.0),
        ),
    )

    ANTI_MECA_12 = AFFE_CHAR_CINE(
        MODELE=MODME,
        MECA_IMPO=(
            _F(GROUP_NO="lock_rigi", DZ=0.0),
            _F(GROUP_MA="face_xmin", DY=0.0),
            _F(GROUP_MA="face_ymin", DX=0.0),
            _F(GROUP_MA="face_xmax", DY=0.0),
            _F(GROUP_MA="face_ymax", DX=0.0),
        ),
    )

    ANTI_MECA_31 = AFFE_CHAR_CINE(
        MODELE=MODME,
        MECA_IMPO=(
            _F(GROUP_NO="lock_rigi", DX=0.0),
            _F(GROUP_MA="face_xmin", DZ=0.0),
            _F(GROUP_MA="face_ymin", DY=0.0),
            _F(GROUP_MA="face_xmax", DZ=0.0),
            _F(GROUP_MA="face_ymax", DY=0.0),
        ),
    )

    ANTI_MECA_23 = AFFE_CHAR_CINE(
        MODELE=MODME,
        MECA_IMPO=(
            _F(GROUP_NO="lock_rigi", DY=0.0),
            _F(GROUP_MA="face_ymin", DZ=0.0),
            _F(GROUP_MA="face_xmin", DX=0.0),
            _F(GROUP_MA="face_ymax", DZ=0.0),
            _F(GROUP_MA="face_xmax", DX=0.0),
        ),
    )

    # Chargement CT, indépendant du matériau.
    # Il faut toutefois en spécifier un. On utilise donc celui disponible, à un instant quelconque.

    INST_CT = L_INST.getValues()[0]
    CHCX = AFFE_CHAR_MECA(
        MODELE=MODME, FORCE_FACE=(_F(GROUP_MA="face_zmin", FX=-1), _F(GROUP_MA="face_zmax", FX=1))
    )

    CHCY = AFFE_CHAR_MECA(
        MODELE=MODME, FORCE_FACE=(_F(GROUP_MA="face_zmin", FY=-1), _F(GROUP_MA="face_zmax", FY=1))
    )

    MELR = CALC_MATR_ELEM(
        MODELE=MODME, CHAM_MATER=CHMATME, INST=INST_CT, CHARGE=(CHCX, CHCY), OPTION="RIGI_MECA"
    )

    NUM = NUME_DDL(MATR_RIGI=MELR)

    VEX = CALC_VECT_ELEM(OPTION="CHAR_MECA", INST=INST_CT, CHAM_MATER=CHMATME, CHARGE=CHCX)

    VEY = CALC_VECT_ELEM(OPTION="CHAR_MECA", INST=INST_CT, CHAM_MATER=CHMATME, CHARGE=CHCY)

    FX = ASSE_VECTEUR(VECT_ELEM=VEX, NUME_DDL=NUM)
    FY = ASSE_VECTEUR(VECT_ELEM=VEY, NUME_DDL=NUM)

    C_LIMX = AFFE_CHAR_MECA(MODELE=MODME, LIAISON_CHAMNO=_F(CHAM_NO=FX, COEF_IMPO=0))
    C_LIMY = AFFE_CHAR_MECA(MODELE=MODME, LIAISON_CHAMNO=_F(CHAM_NO=FY, COEF_IMPO=0))

    LOAD_ff_xx = FORMULE(VALE="1.0 * Z", NOM_PARA="Z")
    LOAD_ff_xy = FORMULE(VALE="0.5 * Z", NOM_PARA="Z")

    if type_homo in ("PLAQUE_CT_TOURATIER",):
        LOAD_ct = FORMULE(VALE="-0.5 * (pi/2)*cos(pi * Z / h)", NOM_PARA="Z", h=ep_ver)
    elif type_homo in ("PLAQUE_CT_MINDLIN",):
        LOAD_ct = FORMULE(VALE="-0.5", NOM_PARA="Z")
    else:
        ASSERT(False)

    CHAR11_mm = AFFE_CHAR_MECA(MODELE=MODME, PRE_EPSI=_F(GROUP_MA=ls_group_ma, EPXX=-1.0))

    CHAR22_mm = AFFE_CHAR_MECA(MODELE=MODME, PRE_EPSI=_F(GROUP_MA=ls_group_ma, EPYY=-1.0))

    CHAR12_mm = AFFE_CHAR_MECA(MODELE=MODME, PRE_EPSI=_F(GROUP_MA=ls_group_ma, EPXY=-0.5))

    CHAR11_ff = AFFE_CHAR_MECA_F(MODELE=MODME, PRE_EPSI=_F(GROUP_MA=ls_group_ma, EPXX=LOAD_ff_xx))

    CHAR22_ff = AFFE_CHAR_MECA_F(MODELE=MODME, PRE_EPSI=_F(GROUP_MA=ls_group_ma, EPYY=LOAD_ff_xx))

    CHAR12_ff = AFFE_CHAR_MECA_F(MODELE=MODME, PRE_EPSI=_F(GROUP_MA=ls_group_ma, EPXY=LOAD_ff_xy))

    CHAR31_ct = AFFE_CHAR_MECA_F(MODELE=MODME, PRE_EPSI=_F(GROUP_MA=ls_group_ma, EPXZ=LOAD_ct))

    CHAR23_ct = AFFE_CHAR_MECA_F(MODELE=MODME, PRE_EPSI=_F(GROUP_MA=ls_group_ma, EPYZ=LOAD_ct))

    CHARDIL_mm = AFFE_CHAR_MECA_F(
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

    CHARDIL_ff = AFFE_CHAR_MECA_F(
        MODELE=MODME,
        PRE_EPSI=[
            _F(
                GROUP_MA=item["GROUP_MA"],
                EPXX=FORMULE(
                    VALE="1.0*Z*ALPHA_DIL(INST)",
                    NOM_PARA=("INST", "Z"),
                    ALPHA_DIL=item["FONC_ALPHA_TIME"],
                ),
                EPYY=FORMULE(
                    VALE="1.0*Z*ALPHA_DIL(INST)",
                    NOM_PARA=("INST", "Z"),
                    ALPHA_DIL=item["FONC_ALPHA_TIME"],
                ),
                EPZZ=FORMULE(
                    VALE="1.0*Z*ALPHA_DIL(INST)",
                    NOM_PARA=("INST", "Z"),
                    ALPHA_DIL=item["FONC_ALPHA_TIME"],
                ),
            )
            for item in alpha_calc
        ],
    )

    elas_fields = ElasticResultDict()
    ther_fields = ThermalResultDict()

    # Calcul des correcteurs MECANIQUES de DILATATION
    # ======================================================================

    elas_fields["CORR_DILA_MEMB"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(
            _F(CHARGE=CHARDIL_mm),
            _F(CHARGE=C_LIMX),
            _F(CHARGE=C_LIMY),
            _F(CHARGE=SYME_MECA_XX),
        ),
        OPTION="SANS",
    )

    elas_fields["CORR_DILA_FLEX"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(
            _F(CHARGE=CHARDIL_ff),
            _F(CHARGE=C_LIMX),
            _F(CHARGE=C_LIMY),
            _F(CHARGE=SYME_MECA_XX),
        ),
        OPTION="SANS",
    )

    # Calcul des correcteurs MECANIQUES
    # ======================================================================

    elas_fields["CORR_MECA11_MEMB"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(_F(CHARGE=CHAR11_mm), _F(CHARGE=C_LIMX), _F(CHARGE=C_LIMY), _F(CHARGE=SYME_MECA_XX)),
        OPTION="SANS",
    )

    elas_fields["CORR_MECA22_MEMB"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(_F(CHARGE=CHAR22_mm), _F(CHARGE=C_LIMX), _F(CHARGE=C_LIMY), _F(CHARGE=SYME_MECA_XX)),
        OPTION="SANS",
    )

    elas_fields["CORR_MECA12_MEMB"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(_F(CHARGE=CHAR12_mm), _F(CHARGE=C_LIMX), _F(CHARGE=C_LIMY), _F(CHARGE=ANTI_MECA_12)),
        OPTION="SANS",
    )

    elas_fields["CORR_MECA11_FLEX"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(_F(CHARGE=CHAR11_ff), _F(CHARGE=C_LIMX), _F(CHARGE=C_LIMY), _F(CHARGE=SYME_MECA_XX)),
        OPTION="SANS",
    )

    elas_fields["CORR_MECA22_FLEX"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(_F(CHARGE=CHAR22_ff), _F(CHARGE=C_LIMX), _F(CHARGE=C_LIMY), _F(CHARGE=SYME_MECA_XX)),
        OPTION="SANS",
    )

    elas_fields["CORR_MECA12_FLEX"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(_F(CHARGE=CHAR12_ff), _F(CHARGE=C_LIMX), _F(CHARGE=C_LIMY), _F(CHARGE=ANTI_MECA_12)),
        OPTION="SANS",
    )

    elas_fields["CORR_MECA31_CT"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(_F(CHARGE=CHAR31_ct), _F(CHARGE=C_LIMX), _F(CHARGE=C_LIMY), _F(CHARGE=ANTI_MECA_31)),
        OPTION="SANS",
    )

    elas_fields["CORR_MECA23_CT"] = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHMATME,
        LIST_INST=L_INST,
        EXCIT=(_F(CHARGE=CHAR23_ct), _F(CHARGE=C_LIMX), _F(CHARGE=C_LIMY), _F(CHARGE=ANTI_MECA_23)),
        OPTION="SANS",
    )

    return elas_fields, ther_fields
