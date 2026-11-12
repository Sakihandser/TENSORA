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

from ..CodeCommands import STAT_NON_LINE, DEFI_LIST_INST, AFFE_MATERIAU
from ..Cata.Syntax import _F
from ..Objects import NonLinearResultDict


def get_list_inst(champ):
    """
    Fonction récupérant la liste des instants contenus dans le champ variable de commande
    argument : le champ variable de commande
    sortie : liste contenant les instants
    """

    liste_instant = [champ.getTime(index) for index in champ.getIndexes()]

    return liste_instant


def calc_meca_mult_ops(self, **args):
    """
    macro CALC_MECA_MULT
    """

    args = _F(args)

    # Définition modèle mécanique
    MODELE = args.get("MODELE")
    CARA_ELEM = args.get("CARA_ELEM")
    CHAM_MATER = args.get("CHAM_MATER")
    CHAR_MECA_GLOBAL = args.get("CHAR_MECA_GLOBAL")
    # Récupération champs thermiques pour modification du champ mater meca
    CAS_CHARGE = args.get("CAS_CHARGE")
    # Calcul thermomecanique
    LIST_INST = args.get("LIST_INST")
    CONVERGENCE = args.get("CONVERGENCE")
    NEWTON = args.get("NEWTON")
    SOLVEUR = args.get("SOLVEUR")

    # ------------------------------------------------
    #        PREPARATION OF MATERIALFIELDS
    # ------------------------------------------------

    # Creation of a new MaterialField for each case by overloading the intial MaterialField

    dict_mater_cas = {}
    dict_evol = {}

    for cas in CAS_CHARGE:
        dfkw = {}
        dfkw["VALE_REF"] = cas["VALE_REF"]
        dfkw["EVOL"] = cas["EVOL_THER"]
        dfkw["NOM_VARC"] = "TEMP"

        if cas["EVOL_THER"].getType() == "EVOL_THER":
            new_mat = AFFE_MATERIAU(MODELE=MODELE, CHAM_MATER=CHAM_MATER, AFFE_VARC=dfkw)
            dict_mater_cas[cas["NOM_CAS"]] = new_mat

            dict_evol[cas["NOM_CAS"]] = cas["EVOL_THER"]

        if cas["EVOL_THER"].getType() == "EVOL_THER_DICT":
            for nom_cas in cas["EVOL_THER"].keys():
                dfkw["EVOL"] = cas["EVOL_THER"][nom_cas]
                new_mat = AFFE_MATERIAU(MODELE=MODELE, CHAM_MATER=CHAM_MATER, AFFE_VARC=dfkw)

                dict_mater_cas[nom_cas] = new_mat
                dict_evol[nom_cas] = cas["EVOL_THER"][nom_cas]

    # ------------------------------------------------
    #        CALCULS
    # ------------------------------------------------

    calc_meca_dict = NonLinearResultDict("calc_meca_dict")

    for nom_cas in dict_mater_cas.keys():
        if LIST_INST is None:
            LIST_INST2 = DEFI_LIST_INST(DEFI_LIST=_F(VALE=get_list_inst(dict_evol[nom_cas])))
        else:
            LIST_INST2 = LIST_INST

        calc_meca_dict[nom_cas] = STAT_NON_LINE(
            MODELE=MODELE,
            CHAM_MATER=dict_mater_cas[nom_cas],
            CARA_ELEM=CARA_ELEM,
            EXCIT=(_F(CHARGE=CHAR_MECA_GLOBAL),),
            INCREMENT=_F(LIST_INST=LIST_INST2),
            CONVERGENCE=CONVERGENCE,
            NEWTON=NEWTON,
            SOLVEUR=SOLVEUR,
        )
    return calc_meca_dict
