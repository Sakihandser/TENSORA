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

from math import sqrt

from ..Messages import UTMESS
from ..Objects import Function
from ..Supervis import ExecuteMacro
from ..Utilities import force_list, is_number


class MaterialDefinition(ExecuteMacro):
    """Command that defines a Material."""

    command_name = "DEFI_MATERIAU"

    def adapt_syntax(self, keywords):
        """Adapt syntax to :
                - convert character parameters to real parameters (BETON_DESORP, SECH_RFT)
                - replace parameters with a list of values ​​into as many parameters with a single value
                  (ELAS_HYPER_VISC, HYPER_HILL)
                - replace TABLE content in keywords.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """
        if "VISC_ISOT_PLAS" in keywords:
            mcfact = keywords["VISC_ISOT_PLAS"]
            # Check strict bounds for PoissonRatio, Young Modulus and TAILLE_GRAIN to avoid division by zero
            if mcfact["YoungModulus"] <= 0.0:
                UTMESS("F", "ELEMENTS4_67")
            if mcfact["PoissonRatio"] <= -1.0:
                UTMESS("F", "COMPOR1_29")
            if mcfact["PoissonRatio"] >= 0.5:
                UTMESS("F", "COMPOR1_30")
            if mcfact["TAILLE_GRAIN"] <= 0.0:
                UTMESS("F", "COMPOR1_31")
            # Adapt length and stress units
            coef_l = 1.0
            value_unit = mcfact.pop("UNITE_LONGUEUR")
            if value_unit == "MM":
                coef_l = 1.0e3
            coef_p = 1.0
            value_unit = mcfact.pop("UNITE_CONTRAINTE")
            if value_unit == "MPa":
                coef_p = 1.0e-6
            mcfact["LengthUnit"] = coef_l
            mcfact["StressUnit"] = coef_p

        if "VISC_ISOT_PLAS_FO" in keywords:
            mcfact = keywords["VISC_ISOT_PLAS_FO"]
            # Check bounds for the material properties (in VISC_ISOT_PLAS_FO only)
            names_mater = (
                "YoungModulus",
                "PoissonRatio",
                "TAILLE_GRAIN",
                "D_DISLOC",
                "C_AMAS",
                "TAILLE_AMAS",
            )
            for i in range(len(names_mater)):
                name = names_mater[i]
                values_xy = tuple(mcfact[name].getValues())
                if len(values_xy) % 2 != 0:
                    UTMESS("F", "UTILITAI2_68")
                nbr = len(values_xy) // 2
                values_mater = values_xy[nbr:]
                for j in range(len(values_mater)):
                    if name != "PoissonRatio" and values_mater[j] < 0.0:
                        UTMESS("F", "COMPOR1_15", valk=("VISC_ISOT_PLAS_FO", name))
                    if name == "YoungModulus" and values_mater[j] <= 0.0:
                        UTMESS("F", "ELEMENTS4_67")
                    if name == "PoissonRatio" and values_mater[j] <= -1.0:
                        UTMESS("F", "COMPOR1_29")
                    if name == "PoissonRatio" and values_mater[j] >= 0.5:
                        UTMESS("F", "COMPOR1_30")
                    if name == "TAILLE_GRAIN" and values_mater[j] <= 0.0:
                        UTMESS("F", "COMPOR1_31")
            # Adapt length and stress units
            coef_l = 1.0
            value_unit = mcfact.pop("UNITE_LONGUEUR")
            if value_unit == "MM":
                coef_l = 1.0e3
            coef_p = 1.0
            value_unit = mcfact.pop("UNITE_CONTRAINTE")
            if value_unit == "MPa":
                coef_p = 1.0e-6
            mcfact["LengthUnit"] = coef_l
            mcfact["StressUnit"] = coef_p

        if "BETON_DESORP" in keywords:
            mcfact = keywords["BETON_DESORP"]
            if mcfact["LEVERETT"] == "OUI":
                coef_p = 1.0
                value = mcfact.pop("UNITE_PRESSION")
                if value == "MPa":
                    coef_p = 1e6
                    mcfact["COEF_UNITE_P"] = coef_p

        adapt_elas(keywords)
        if "ELAS_HYPER_VISC" in keywords:
            mcfact = keywords["ELAS_HYPER_VISC"]
            # check list sizes
            if "G" in mcfact and "TAU" in mcfact:
                mcfact["G"] = force_list(mcfact["G"])
                mcfact["TAU"] = force_list(mcfact["TAU"])
                if len(mcfact["G"]) != len(mcfact["TAU"]):  # and len(mcfact["G"]) != mcfact["Nv"]:
                    UTMESS("F", "TABLE0_14", valk=("G", "TAU"))
                mcfact["NV"] = len(mcfact["G"])
                adapt_list_of_values(mcfact, "G")
                adapt_list_of_values(mcfact, "TAU")

        if "HYPER_HILL" in keywords:
            mcfact = keywords["HYPER_HILL"]
            # check list sizes
            if "ALPHA" in mcfact and "BETA" in mcfact and "MU":
                mcfact["ALPHA"] = force_list(mcfact["ALPHA"])
                mcfact["BETA"] = force_list(mcfact["BETA"])
                mcfact["MU"] = force_list(mcfact["MU"])
                if len(mcfact["ALPHA"]) not in [len(mcfact["BETA"]), mcfact["MU"]]:
                    UTMESS("F", "TABLE0_14", valk=("ALPHA", "BETA", "MU"))
                mcfact["Nvk"] = len(mcfact["ALPHA"])
                adapt_list_of_values(mcfact, "ALPHA")
                adapt_list_of_values(mcfact, "BETA")
                adapt_list_of_values(mcfact, "MU")

        if "SECH_RFT" in keywords:
            mcfact = keywords["SECH_RFT"]
            # check list sizes
            coef_l = 1.0
            coef_t = 1.0
            value = mcfact.pop("UNITE_LONGUEUR")
            if value == "MM":
                coef_l = 1e-3
            value = mcfact.pop("UNITE_TEMPS")
            if value == "MIN":
                coef_t = 60.0
            elif value == "H":
                coef_t = 3600.0
            elif value == "J":
                coef_t = 3600.0 * 24.0
            mcfact["COEF_UNITE_L"] = coef_l
            mcfact["COEF_UNITE_T"] = coef_t

        if "TABLE" not in keywords:
            return

        self.print_syntax(keywords)
        cmd_name = "DEFI_MATERIAU <TABLE>"
        cmd_kws = self._cata.keywords

        table_kws = keywords.get("TABLE")
        cmd_kws["TABLE"].addDefaultKeywords(table_kws)
        table_values = table_kws["TABLE"].EXTR_TABLE().values()

        varc_name = table_kws["NOM_PARA"]
        # Vérification du contenu de la table
        if varc_name not in table_values.keys():
            errmsg = "Parameter '{0}' is missing.".format(varc_name)
            UTMESS("F", "SUPERVIS_4", valk=(cmd_name, errmsg))

        for mater in table_kws["COMPOR"]:
            if mater in keywords or mater.replace("_FO", "") in keywords:
                errmsg = "Material '{0}' cannot be repeated outside TABLE.".format(
                    mater.replace("_FO", "")
                )
                UTMESS("F", "SUPERVIS_4", valk=(cmd_name, errmsg))

        # Extraction des valuers de la table sous forme de fonction
        para_functions = {}
        varc_values = table_values.pop(varc_name)

        # Traitement particulier pour les parametres constants type TEMP_DEF_ALPHA
        constant_para_names = ("TEMP_DEF_ALPHA",)
        for cpara_name in constant_para_names:
            if cpara_name in table_values:
                cpara_values = list(set(table_values.pop(cpara_name)))
                if len(cpara_values) != 1:
                    errmsg = "Parameter '{0}' is not constant.".format(cpara_name)
                    UTMESS("F", "SUPERVIS_4", valk=(cmd_name, errmsg))

                para_functions[cpara_name] = cpara_values[0]

        # Tous les autres
        for vpara_name, vpara_values in table_values.items():
            para_f = Function()
            para_f.setParameterName(varc_name)
            para_f.setResultName(vpara_name)
            para_f.setExtrapolation(
                "{0}{1}".format(table_kws["PROL_GAUCHE"][0], table_kws["PROL_DROITE"][0])
            )
            para_f.setInterpolation("{0} {0}".format(table_kws["INTERPOL"]))
            para_f.setValues(varc_values, vpara_values)

            para_functions[vpara_name] = para_f

        # On ajoute le contenu de la table à DEFI_MATERIAU
        for mater in table_kws["COMPOR"]:
            mater_kws = {}
            for key in cmd_kws[mater].keywords.keys():
                if key in para_functions:
                    mater_kws[key] = para_functions[key]

            keywords[mater] = mater_kws

        valk = (
            ", ".join(table_kws["COMPOR"]),
            "{0} ('<{1}>')".format(table_kws["TABLE"].userName, table_kws["TABLE"].getName()),
        )
        UTMESS("I", "MATERIAL1_11", valk=valk)
        keywords.pop("TABLE")
        # check syntax after changing the keywords
        self.check_syntax(keywords)


def adapt_elas(keywords):
    """Compute (E, NU) from (K, MU) or (CELE_P, CELE_S, RHO)

    If (E, NU) already exist, check the consistency.
    Otherwise, assign (E, NU) values.
    """

    def is_equal(x, y, epsi=1.0e-3):
        """Tell if 2 floats are almost equal."""
        return abs(x - y) < 2.0 * epsi * abs(x + y)

    def compare(par1, val1, par2, val2, epsi=1.0e-3):
        """Compare and raise an error if the values are not equal."""
        if not is_number(val1) or not is_number(val2):
            return
        if not is_equal(val1, val2):
            UTMESS("F", "MATERIAL1_13", valr=(val1, val2, epsi), valk=(par1, par2))

    elas = keywords.get("ELAS")
    if not elas:
        return

    elas = force_list(elas)[0]
    valK = elas.pop("K", None)
    valMU = elas.pop("MU", None)
    celP = elas.pop("CELE_P", None)
    celS = elas.pop("CELE_S", None)
    if set([valK, valMU, celP, celS]).difference([None]):
        if None not in (valK, valMU):
            if valK <= 0.0:
                UTMESS("F", "MATERIAL1_14", valk="K")
            if valMU <= 0.0:
                UTMESS("F", "MATERIAL1_14", valk="MU")
            valE = 9.0 * valK * valMU / (3.0 * valK + valMU)
            valNU = (3.0 * valK - 2.0 * valMU) / (6.0 * valK + 2.0 * valMU)
            UTMESS("I", "MATERIAL1_12", valr=(valE, valNU), valk="(K, MU)")
        elif None not in (celP, celS):
            if celS <= 0.0:
                UTMESS("F", "MATERIAL1_14", valk="CELE_S")
            if celP / celS < 2.0 * sqrt(3.0) / 3.0:
                UTMESS("F", "MATERIAL1_15", valr=(celP / celS, 2.0 * sqrt(3.0) / 3.0))
            valE = elas["RHO"] * celS**2 * (3.0 * celP**2 - 4.0 * celS**2) / (celP**2 - celS**2)
            valNU = (celP**2 - 2.0 * celS**2) / (celP**2 - celS**2) / 2.0
            UTMESS("I", "MATERIAL1_12", valr=(valE, valNU), valk="(CELE_P, CELE_S, RHO)")

        elas["E"] = valE
        elas["NU"] = valNU

    # check for elastic parameters passed for MFront behaviours with E, nu
    for key, userDict in keywords.items():
        if isinstance(userDict, dict):
            userDict = [userDict]
        elif not isinstance(userDict, (list, tuple)):
            continue
        for occ in userDict:
            if occ.get("YoungModulus"):
                compare(key + "/YoungModulus", occ["YoungModulus"], "ELAS/E", elas["E"])
            if occ.get("PoissonRatio"):
                compare(key + "/PoissonRatio", occ["PoissonRatio"], "ELAS/NU", elas["NU"])


# K = E / (3. * (1 - 2 * NU))
# MU = E / (2. * (1 + NU))
# Vp = sqrt( (K + 4/3 * MU) / rho )
# Vs = sqrt( MU / rho )


def adapt_list_of_values(mcfact, name):
    """Replace a list of values by separated parameters.

    Example: G=(a, b, c) is replaced by G1=a, G2=b, G3=c.

    Args:
        mcfact (dict): factor keyword, changed in place.
        name (str): keyword containing the list.
    """
    values = mcfact.pop(name, None)
    if not values:
        return
    for i, value in enumerate(values):
        mcfact[f"{name}{i + 1}"] = value


DEFI_MATERIAU = MaterialDefinition.run
