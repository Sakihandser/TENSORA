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

"""
:py:class:`Function2D` --- Representation of Function2D
**********************************************
"""

from ..Objects.function_py import t_fonction, t_nappe
from libaster import Function2D

from ..Utilities import injector


@injector(Function2D)
class ExtendedFunction2D:
    cata_sdj = "SD.sd_fonction.sd_fonction_aster"

    def convert(self):
        """Returns a `t_nappe` object, a Python copy of the 2D-function.

        Returns:
            t_nappe: Python object of the function.
        """
        if self._t_nappe:
            return self._t_nappe
        para = self.Parametres()
        vale = self.Valeurs()
        l_fonc = []
        i = 0
        for pf in para[1]:
            para_f = {
                "INTERPOL": pf["INTERPOL_FONC"],
                "PROL_DROITE": pf["PROL_DROITE_FONC"],
                "PROL_GAUCHE": pf["PROL_GAUCHE_FONC"],
                "NOM_PARA": para[0]["NOM_PARA_FONC"],
                "NOM_RESU": para[0]["NOM_RESU"],
            }
            l_fonc.append(t_fonction(vale[1][i][0], vale[1][i][1], para_f))
            i += 1
        self._t_nappe = t_nappe(vale[0], l_fonc, para[0], nom=self.getName())
        return self._t_nappe

    def Parametres(self):
        """Returns a dict containing the properties of the function.

        Returns:
            dict: keys of the dict are "INTERPOL", "NOM_PARA", "NOM_RESU",
            "PROL_GAUCHE", "PROL_DROITE", see `getProperties()` for the content.
        """
        prol = self.getProperties()
        TypeProl = {"E": "EXCLU", "L": "LINEAIRE", "C": "CONSTANT"}
        dico = {
            "INTERPOL": [prol[1][0:3], prol[1][4:7]],
            "NOM_PARA": prol[2][0:16].strip(),
            "NOM_RESU": prol[3][0:16].strip(),
            "PROL_DROITE": TypeProl[prol[4][1]],
            "PROL_GAUCHE": TypeProl[prol[4][0]],
            "NOM_PARA_FONC": prol[6][0:4].strip(),
        }
        lparf = []
        nbf = (len(prol) - 7) // 2
        for i in range(nbf):
            dicf = {
                "INTERPOL_FONC": [prol[7 + i * 2][0:3], prol[7 + i * 2][4:7]],
                "PROL_DROITE_FONC": TypeProl[prol[8 + i * 2][1]],
                "PROL_GAUCHE_FONC": TypeProl[prol[8 + i * 2][0]],
            }
            lparf.append(dicf)
        return [dico, lparf]

    def Valeurs(self):
        """Returns the list of the parameter values and a liste of couples
        (absc, ord) for each function.

        Returns:
            (list, list(couples)): List of parameter values and list of couples.
        """
        values = self.getValues()
        old = []
        for funcv in values:
            size = len(funcv) // 2
            old.append([funcv[:size], funcv[size:]])
        parameters = self.getParameters()
        return [parameters, old]

    def __call__(self, val1, val2, tol=1.0e-6):
        """Evaluate a function at 'val'. If provided, 'tol' is a relative
        tolerance to match an abscissa value."""
        val1 = float(val1)
        val2 = float(val2)
        __ff = self.convert()
        return __ff(val1, val2, tol=tol)
