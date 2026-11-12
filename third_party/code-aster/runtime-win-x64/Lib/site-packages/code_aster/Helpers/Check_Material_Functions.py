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

from ..Objects import Function
from ..Messages import UTMESS


def check_dis_choc_elas(keywords, options=[]):
    """Check function of DIS_CHOC_ELAS behaviour

    Arguments:
        keywords (dict): DIS_CHOC_ELAS keyword, changed in place.
        options        : list of option
                                RIGIP : creation of the function RIGIP

    Returns:
        dict: DIS_CHOC_ELAS keyword, changed in place if needed. Raises '<F>' in case of error.

    Use with :  defi_materiau
                dyna_vibra/comportement
    """

    #
    # jean-luc.flejou@edf.fr
    #
    def _message(num, mess2="", mess3=""):
        UTMESS("F", "DISCRETS_66", valk=("CHOC_ELAS", mess2, mess3), vali=(num,))

    precis = 1.0e-08
    #
    # --------------------------------------------------------------- Début des vérifications
    # Conditions sur la fonction FX
    #   paramètre 'DX'
    #   interpolation LIN LIN
    #   prolongée à gauche et à droite : exclue
    fct = keywords["FX"]
    OkFct = type(fct) is Function
    param = fct.Parametres()
    OkFct = OkFct and param["NOM_PARA"] == "DX"
    OkFct = OkFct and param["INTERPOL"][0] == "LIN"
    OkFct = OkFct and param["INTERPOL"][1] == "LIN"
    OkFct = OkFct and param["PROL_DROITE"] in ["EXCLU", "LINEAIRE"]
    OkFct = OkFct and param["PROL_GAUCHE"] == "EXCLU"
    if not OkFct:
        _message(1, fct.getName(), "%s" % param)
    # FX : 2 points minimum
    Fxx, Fxy = fct.Valeurs()
    if not (len(Fxx) >= 2):
        _message(2, "%s" % fct.getName(), "%d" % len(Fxx))
    # Le 1er point c'est ZERO,ZERO
    if not ((0.0 <= Fxx[0] <= precis) and (0.0 <= Fxy[0] <= precis)):
        _message(3, "%s" % fct.getName(), "%s, %s" % (Fxx[0], Fxy[0]))
    #
    # Abscisses et ordonnées strictement croissantes
    x0 = Fxx[0]
    y0 = Fxy[0]
    Rix = []
    Riy = []
    for ii in range(1, len(Fxx)):
        x1 = Fxx[ii]
        y1 = Fxy[ii]
        if (x0 >= x1) or (y0 >= y1) or (y1 < 0.0) or (x1 < 0.0):
            _message(4, "%s" % fct.getName(), "point(%d) : %s,%s" % (ii + 1, x0, y0))
        Rix.append(0.5 * (x1 + x0))
        Riy.append((y1 - y0) / (x1 - x0))
        x0 = x1
        y0 = y1
    # --------------------------------------------------------------- Fin des vérifications
    if "RIGIP" in options:
        # Création des nouvelles fonctions
        newRi = Function()
        newRi.setResultName("Raideur")
        newRi.setExtrapolation("CC")
        newRi.setInterpolation("LIN LIN")
        newRi.setParameterName("DX")
        # Affectations des valeurs
        newRi.setValues(Rix, Riy)
        # Fonction d'écrouissage
        keywords["RIGIP"] = newRi
