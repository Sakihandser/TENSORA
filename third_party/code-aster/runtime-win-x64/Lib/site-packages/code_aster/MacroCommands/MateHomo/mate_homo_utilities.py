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

from collections import OrderedDict

from ...Cata.Syntax import _F
from ...CodeCommands import (
    DEFI_CONSTANTE,
    DEFI_MATERIAU,
    AFFE_MATERIAU,
    AFFE_MODELE,
    CREA_RESU,
    CREA_CHAMP,
    DEFI_LIST_REEL,
    AFFE_CHAR_CINE,
    MECA_STATIQUE,
    POST_ELEM,
)
from ...Messages import ASSERT, UTMESS
from ...Objects import Function

DEFAULT_TEMP_REF = 20.0


def create_empty_dictpara(ls_para):
    """
    Init empty result table.

    Args:
        para (list[str]): List of output parameters.

    Returns:
        OrderedDict: Output table.
    """

    tabpara = OrderedDict()
    for para in ls_para:
        tabpara[para] = []
    return tabpara


def get_temp_def_alpha_material(mate, missing=DEFAULT_TEMP_REF):
    """
    Retrieve the TEMP_DEF_ALPHA parameter from a material datastructure.

    If not found, returns the default value of 20°C.

    Args:
        mate (Material): The input datastructure.
        missing (float): The default value if parameter is missing.

    Returns:
        float: The parameter value.
    """

    temp_def_alpha = missing
    for name in mate.getMaterialNames():
        try:
            temp_def_alpha = mate.getValueReal(name, "TEMP_DEF_ALPHA")
            break
        except RuntimeError:
            pass

    return temp_def_alpha


def get_temp_def_alpha_result(result, missing=DEFAULT_TEMP_REF):
    """
    Retrieve the TEMP_DEF_ALPHA parameter from a result datastructure.

    Args:
        mate (Material): The input datastructure.
        missing (float): The default value if parameter is missing.

    Returns:
        float: The parameter value.
    """

    temp_def_alpha = missing
    mate = result.getMaterialField()
    for m in mate.getVectorOfMaterial():
        temp_def_alpha = get_temp_def_alpha_material(m, missing=None)
        if temp_def_alpha is not None:
            break

    return temp_def_alpha


def parse_mater_groups(ls_affe, varc_name, ls_group_tout):
    """
    Returns the appropriate material fields prescription to compute the
    homogeneous parameters.

    This function processes the material prescriptions provided by the user to
    prepare them for homogenization computations. It handles the following tasks:
    1. Ignores the ALPHA and RHO_CP parameters for multiple temperature values to
       ensure accurate homogenization.
    2. Converts the command variable to a pseudo-TEMP if it is not already TEMP.
    3. Converts the TOUT='OUI' prescription to GROUP_MA='BODY' to standardize the
       input.

    Args:
        ls_affe (list): List of material prescriptions from the user command.
            These prescriptions define the material properties and their variations
            with respect to temperature or other variables.
        varc_name (str): Name of the command variable (TEMP | IRRA). This variable
            indicates the type of parameter variation (e.g., temperature or
            irradiation).
        ls_group_tout (list[str]): List of groups where properties are prescribed.

    Returns:
        affe_mate (dict): Modified material prescription for material averaging.
        affe_calc (dict): Modified material prescription for corrector computation.
    """

    # material properties are accessed without "_FO" suffix
    mat1, mat2, mat3 = "ELAS", "THER", "THER_NL"
    mandatory_elas, optional_elas = ["E", "NU"], ["RHO", "ALPHA"]
    mandatory_ther, optional_ther = ["LAMBDA"], ["RHO_CP"]

    affe_mod_mate = []
    affe_mod_calc = []

    f_zero = DEFI_CONSTANTE(VALE=0.0)
    ls_temp_def_alpha = []

    for item in ls_affe:
        mater = item["MATER"]

        if "GROUP_MA" in item:
            new_item_mate = {"GROUP_MA": item["GROUP_MA"]}
            new_item_calc = {"GROUP_MA": item["GROUP_MA"]}
        elif "TOUT" in item:
            new_item_mate = {"GROUP_MA": ls_group_tout}
            new_item_calc = {"GROUP_MA": ls_group_tout}
        else:
            ASSERT(False)

        matNames = mater.getMaterialNames()
        if mat1 not in matNames:
            UTMESS("F", "HOMO1_8", valk=(mat1, mater.getName(), mater.userName))

        if mat2 not in matNames and mat3 not in matNames:
            UTMESS("F", "HOMO1_9", valk=(mat2, mat3, mater.getName(), mater.userName))

        keyelas = " ".join([m for m in matNames if m in (mat1,)])
        keyther = " ".join([m for m in matNames if m in (mat2, mat3)])

        f_para = {}
        f_para_temp = {}

        parse_list = {
            keyelas: mandatory_elas + optional_elas,
            keyther: mandatory_ther + optional_ther,
        }

        temp_def_alpha_current_mat = get_temp_def_alpha_material(mater, missing=None)
        ls_temp_def_alpha.append(temp_def_alpha_current_mat)

        for key, lspara in parse_list.items():
            missing_in_at_least_one = []
            for p in lspara:
                func = mater.getFunction(key, p)
                if func:
                    if p in missing_in_at_least_one:
                        UTMESS("F", "HOMO1_12", valk=p)
                    f_para[p] = func
                else:
                    try:
                        mater.getValueReal(key, p)
                        UTMESS("F", "HOMO1_13", valk=p)
                    except RuntimeError:
                        pass
                missing_in_at_least_one.append(p)

        check_list = mandatory_elas + mandatory_ther
        for p in check_list:
            if p not in f_para:
                UTMESS("F", "HOMO1_10", valk=(p, mater.getName(), mater.userName))

        for p, fp in f_para.items():
            pro = fp.getProperties()
            if not (pro[0] == "CONSTANT" or (pro[0] == "FONCTION" and pro[2] == varc_name)):
                UTMESS("F", "HOMO1_11", valk=(p, mater.getName(), mater.userName, varc_name))

            if pro[0] == "FONCTION" and pro[2] != "TEMP":
                f_para_temp[p] = Function()
                f_para_temp[p].setParameterName("TEMP")
                f_para_temp[p].setInterpolation(pro[1])
                f_para_temp[p].setExtrapolation(pro[4])
                values = fp.getValues()
                x, y = values[: len(values) // 2], values[len(values) // 2 :]
                f_para_temp[p].setValues(x, y)
            else:
                f_para_temp[p] = fp

        elas_fo_kw = {
            "E": f_para_temp["E"],
            "NU": f_para_temp["NU"],
            "ALPHA": f_zero,
            "TEMP_DEF_ALPHA": DEFAULT_TEMP_REF,
        }

        ther_fo_kw = {"LAMBDA": f_para_temp.get("LAMBDA", f_zero), "RHO_CP": f_zero}

        new_item_calc["MATER"] = DEFI_MATERIAU(ELAS_FO=_F(**elas_fo_kw), THER_FO=_F(**ther_fo_kw))

        affe_mod_calc.append(new_item_calc)

        if "ALPHA" in f_para_temp:
            ASSERT(temp_def_alpha_current_mat is not None)
            elas_fo_kw["ALPHA"] = f_para_temp["ALPHA"]
            elas_fo_kw["TEMP_DEF_ALPHA"] = temp_def_alpha_current_mat

        if "RHO" in f_para_temp:
            elas_fo_kw["RHO"] = f_para_temp["RHO"]

        if "RHO_CP" in f_para_temp:
            ther_fo_kw["RHO_CP"] = f_para_temp["RHO_CP"]

        new_item_mate["MATER"] = DEFI_MATERIAU(ELAS_FO=_F(**elas_fo_kw), THER_FO=_F(**ther_fo_kw))

        affe_mod_mate.append(new_item_mate)

    if len(set(ls_temp_def_alpha)) > 1:
        UTMESS("F", "HOMO1_14", valk=("TEMP_DEF_ALPHA",))

    return affe_mod_mate, affe_mod_calc


def prepare_alpha_loads(ls_affe_mod_mate, varc_values):
    """
    Modifies the ALPHA function parameters.

    This function converts the prescribed ALPHA function of temperature into
    functions of time. These modified functions are used for the computation of
    the dilatation corrector fields, which are essential for accurately modeling
    thermal expansion behavior.

    Args:
        ls_affe_mod_mate (list[dict]): Modified material prescription for material
            averaging. This list contains dictionaries with material properties
            that have been adjusted for homogenization.
        varc_values (list[float]): List of temperatures at which parameters are
            computed. These values are used to create the time-dependent ALPHA
            functions.

    Returns:
        list[dict]: Modified ALPHA functions as a list of dictionaries. Each
            dictionary contains the group name and the corresponding ALPHA function
            of time.
    """

    ls_alpha_calc = []

    for item in ls_affe_mod_mate:
        group_ma_affe = item["GROUP_MA"]
        mater = item["MATER"]
        f_alpha_temp = mater.getFunction("ELAS", "ALPHA")
        pro = f_alpha_temp.getProperties()
        f_alpha_time = Function()
        f_alpha_time.setParameterName("INST")
        f_alpha_time.setInterpolation(pro[1])
        f_alpha_time.setExtrapolation(pro[4])
        f_alpha_time.setValues(varc_values, [f_alpha_temp(t) for t in varc_values])
        ls_alpha_calc.append({"GROUP_MA": group_ma_affe, "FONC_ALPHA_TIME": f_alpha_time})

    return ls_alpha_calc


def setup_calcul(mesh, ls_group_tout, ls_affe, varc_name, varc_values):
    """
    Sets up the computation of homogeneous parameters.

    This function prepares the necessary components for the computation of
    homogeneous parameters based on the specified type of homogenization
    (either MASSIF or PLAQUE). It processes the material prescriptions provided
    by the user, sets up the mechanical and thermal models, and computes the
    dilatation coefficients as functions of pseudo-time (temperature).

    The function performs the following tasks:
    1. Processes the material prescriptions to handle different temperature
       values and converts command variables to pseudo-TEMP if necessary.
    2. Sets up the mechanical model and material field for the computation of
       mechanical properties.
    3. Sets up the thermal model and material field for the computation of
       thermal properties.
    4. Computes the dilatation coefficients (ALPHA) as functions of pseudo-time,
       which correspond to the specified temperature values.

    Args:
        type_homo (str): Type of homogenization (MASSIF | PLAQUE). Determines the
            type of homogenization to be performed.
        mesh (Mesh): The VER mesh used for the computation.
        ls_group_tout (list[str]): List of groups where properties are prescribed.
            These groups define the regions of the mesh where material properties
            are applied.
        ls_affe (list): List of material prescriptions from the user command.
            These prescriptions define the material properties and their
            variations with respect to temperature or other variables.
        varc_name (str): Name of the command variable (TEMP | IRRA). This variable
            indicates the type of parameter variation (e.g., temperature or
            irradiation).
        varc_values (list[float]): List of temperatures at which parameters are
            computed. These values define the pseudo-time steps for the
            homogenization process.

    Returns:
        ElasticResult: Mechanical result from 0-load boundary condition. This
            result contains the computed mechanical properties of the material
            under the specified conditions.
        Model: Mechanical model used for the computation of mechanical properties.
        MaterialField: Mechanical material field containing the material
            properties for the mechanical model.
        Model: Thermal model used for the computation of thermal properties.
        MaterialField: Thermal material field containing the material properties
            for the thermal model.
        ListOfFloats: List of pseudo-time values (homogenization temperature
            values). These values correspond to the specified temperature values
            and are used as time steps in the homogenization process.
        list: List of dilatation coefficients (ALPHA) as functions of pseudo-time
            (temperature). These coefficients describe the thermal expansion
            behavior of the material at different temperatures.
    """

    ls_affe_mod_mate, ls_affe_mod_calc = parse_mater_groups(ls_affe, varc_name, ls_group_tout)

    ls_alpha_calc = prepare_alpha_loads(ls_affe_mod_mate, varc_values)

    MODTH = AFFE_MODELE(
        MAILLAGE=mesh, AFFE=_F(TOUT="OUI", MODELISATION="3D", PHENOMENE="THERMIQUE")
    )

    MODME = AFFE_MODELE(
        MAILLAGE=mesh, AFFE=_F(TOUT="OUI", MODELISATION="3D", PHENOMENE="MECANIQUE")
    )

    EVOLVARC = CREA_RESU(
        OPERATION="AFFE",
        TYPE_RESU="EVOL_VARC",
        AFFE=[
            _F(
                CHAM_GD=CREA_CHAMP(
                    TYPE_CHAM="NOEU_TEMP_R",
                    OPERATION="AFFE",
                    MAILLAGE=mesh,
                    AFFE=_F(GROUP_MA=ls_group_tout, NOM_CMP="TEMP", VALE=value),
                ),
                INST=value,
                NOM_CHAM="TEMP",
            )
            for value in varc_values
        ],
    )

    affevarckw = {
        "GROUP_MA": ls_group_tout,
        "NOM_VARC": "TEMP",
        "EVOL": EVOLVARC,
        "NOM_CHAM": "TEMP",
        "VALE_REF": DEFAULT_TEMP_REF,
    }

    CHLOIME = AFFE_MATERIAU(
        MODELE=MODME, AFFE=[_F(**affekw) for affekw in ls_affe_mod_mate], AFFE_VARC=_F(**affevarckw)
    )

    CHMATME = AFFE_MATERIAU(
        MODELE=MODME, AFFE=[_F(**affekw) for affekw in ls_affe_mod_calc], AFFE_VARC=_F(**affevarckw)
    )

    CHMATTH = AFFE_MATERIAU(
        MODELE=MODTH, AFFE=[_F(**affekw) for affekw in ls_affe_mod_calc], AFFE_VARC=_F(**affevarckw)
    )

    L_INST = DEFI_LIST_REEL(VALE=varc_values)

    # Calcul des lois de melange
    # ======================================================================

    LOCK_MECA = AFFE_CHAR_CINE(
        MODELE=MODME, MECA_IMPO=(_F(GROUP_MA=ls_group_tout, DX=0.0, DY=0.0, DZ=0.0))
    )

    DEPLMATE = MECA_STATIQUE(
        MODELE=MODME,
        CHAM_MATER=CHLOIME,
        LIST_INST=L_INST,
        EXCIT=(_F(CHARGE=LOCK_MECA)),
        OPTION="SANS",
    )

    return DEPLMATE, MODME, CHMATME, MODTH, CHMATTH, L_INST, ls_alpha_calc


def cross_work(RESU1, RESU2, INST, ls_group_tout):
    """
    Computes the cross work value of correctors using the potential energy.

    This function calculates the cross work value of correctors based on their
    potential energy. The cross work value is determined using the following
    formulas:
    - If X == Y: W = 2 * EPOT(X)
    - If X != Y: W = EPOT(X + Y) - EPOT(X) - EPOT(Y)

    Note: These formulas depend on the choice of boundary conditions (BC) for
    correctors (PRE_EPSI).

    Args:
        RESU1 (Result): The first result data structure, either elastic or
            thermal.
        RESU2 (Result): The second result data structure, either elastic or
            thermal.
        INST (float): The pseudo-time (temperature) value for the work
            computation.
        ls_group_tout (list[str]): List of groups where properties are
            prescribed.

    Returns:
        float: The cross work value.
    """

    ASSERT(RESU1.getMesh() is RESU2.getMesh())
    ASSERT(RESU1.getModel() is RESU2.getModel())
    ASSERT(RESU1.getMaterialField() is RESU2.getMaterialField())
    ASSERT(RESU1.getType() == RESU2.getType())

    RESU_TYPE = RESU1.getType()
    ASSERT(RESU_TYPE in ("EVOL_ELAS", "EVOL_THER"))
    CH_TYPE = "DEPL" if "ELAS" in RESU_TYPE else "TEMP"

    MOD = RESU1.getModel()
    CHMAT = RESU1.getMaterialField()

    CH1 = CREA_CHAMP(
        RESULTAT=RESU1,
        TYPE_CHAM="NOEU_%s_R" % CH_TYPE,
        OPERATION="EXTR",
        NOM_CHAM=CH_TYPE,
        INST=INST,
    )

    EPOT_CH1 = POST_ELEM(
        CHAM_GD=CH1, INST=INST, MODELE=MOD, CHAM_MATER=CHMAT, ENER_POT=_F(GROUP_MA=ls_group_tout)
    )

    epot_ch1 = abs(sum(EPOT_CH1.EXTR_TABLE().values()["TOTALE"]))

    if RESU1 is RESU2:
        work = 2 * epot_ch1

    else:
        CH2 = CREA_CHAMP(
            RESULTAT=RESU2,
            TYPE_CHAM="NOEU_%s_R" % CH_TYPE,
            OPERATION="EXTR",
            NOM_CHAM=CH_TYPE,
            INST=INST,
        )

        EPOT_CH2 = POST_ELEM(
            CHAM_GD=CH2,
            INST=INST,
            MODELE=MOD,
            CHAM_MATER=CHMAT,
            ENER_POT=_F(GROUP_MA=ls_group_tout),
        )
        epot_ch2 = abs(sum(EPOT_CH2.EXTR_TABLE().values()["TOTALE"]))

        EPOT_SOMME = POST_ELEM(
            CHAM_GD=CH1 + CH2,
            INST=INST,
            MODELE=MOD,
            CHAM_MATER=CHMAT,
            ENER_POT=_F(GROUP_MA=ls_group_tout),
        )
        epot_chsomme = abs(sum(EPOT_SOMME.EXTR_TABLE().values()["TOTALE"]))

        work = epot_chsomme - epot_ch1 - epot_ch2

    return work
