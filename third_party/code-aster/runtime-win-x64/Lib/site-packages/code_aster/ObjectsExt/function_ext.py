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
:py:class:`Function` --- Function object
****************************************
"""

from math import pi

import numpy as NP
from libaster import Function, FunctionComplex

from ..Objects.function_py import t_fonction, t_fonction_c
from ..Objects.table_graph import Graph
from ..Utilities import accept_array, injector


@injector(Function)
class ExtendedFunction:
    cata_sdj = "SD.sd_fonction.sd_fonction_aster"

    setValues = accept_array(Function.setValues)

    def abs(self):
        """Return the absolute value of the function.

        Returns:
            (Function): Absolute value of the function.
        """
        new = Function()
        absc, ordo = self.Valeurs()
        new.setValues(absc, NP.abs(ordo))
        _, interp, para, result, extra, _ = self.getProperties()
        new.setParameterName(para)
        new.setResultName(result)
        new.setInterpolation(interp)
        new.setExtrapolation(extra)
        return new

    def getValuesAsArray(self):
        """Return the values of the function as a `numpy.array` of shape (N, 2).

        Returns:
            numpy.array: Array containing the values.
        """
        size = self.size()
        values = NP.array(self.getValues())
        values.shape = (2, size)
        return values.transpose()

    def convert(self, arg="real"):
        """Returns a `t_fonction` object, a Python copy of the function.

        Returns:
            t_fonction: Python object of the function.
        """
        class_fonction = t_fonction
        if arg == "complex":
            class_fonction = t_fonction_c
        absc, ordo = self.Valeurs()
        return class_fonction(absc, ordo, self.Parametres(), nom=self.getName())

    def Valeurs(self):
        """Returns two lists of values for the abscissas and the ordinates.

        Returns:
            tuple: Lists of abscissas and list of ordinates.
        """
        values = self.getValuesAsArray()
        return values[:, 0], values[:, 1]

    def Absc(self):
        """Returns the list of the abscissas.

        Returns:
            list: List of abscissas.
        """
        return self.Valeurs()[0]

    def Ordo(self):
        """Returns the list of the ordinates.

        Returns:
            list: List of ordinates.
        """
        return self.Valeurs()[1]

    def __call__(self, val, tol=1.0e-6):
        """Evaluate a function at 'val'. If provided, 'tol' is a relative
        tolerance to match an abscissa value."""
        val = float(val)
        __ff = self.convert()
        return __ff(val, tol=tol)

    def Parametres(self):
        """Returns a dict containing the properties of the function.

        Returns:
            dict: keys of the dict are "INTERPOL", "NOM_PARA", "NOM_RESU",
            "PROL_GAUCHE", "PROL_DROITE", see `getProperties()` for the content.
        """
        TypeProl = {"E": "EXCLU", "L": "LINEAIRE", "C": "CONSTANT"}
        _, interp, para, result, extra, _ = self.getProperties()
        dico = {
            "INTERPOL": interp.split(),
            "NOM_PARA": para,
            "NOM_RESU": result,
            "PROL_GAUCHE": TypeProl[extra[0]],
            "PROL_DROITE": TypeProl[extra[1]],
        }
        return dico

    def Trace(self, FORMAT="TABLEAU", **kargs):
        """Plot a function."""
        gr = Graph()
        para = self.Parametres()
        gr.AjoutCourbe(Val=self.Valeurs(), Lab=[para["NOM_PARA"], para["NOM_RESU"]])
        gr.Trace(FORMAT=FORMAT, **kargs)


@injector(FunctionComplex)
class ExtendedFunctionComplex:
    cata_sdj = "SD.sd_fonction.sd_fonction_aster"

    setValues = accept_array(FunctionComplex.setValues)

    def getValuesAsArray(self):
        """Return the values of the function as a `numpy.array` of shape (N, 3).

        Returns:
            numpy.array: Array containing the values.
        """
        size = self.size()
        values = NP.array(self.getValues())
        abscissas = values[:size].transpose()
        ordinates = values[size:].transpose()
        abscissas.shape = (size, 1)
        ordinates.shape = (size, 2)
        return NP.hstack([abscissas, ordinates])

    def Valeurs(self):
        """Returns three lists of values for the abscissas, the real part of the
        ordinates and the imaginary part of the ordinates.

        Returns:
            tuple: Lists of the abscissas, real part and imaginary part of the
            ordinates.
        """
        """
        Retourne trois listes de valeurs : abscisses, parties reelles et imaginaires.
        """
        values = self.getValuesAsArray()
        return values[:, 0], values[:, 1], values[:, 2]

    def Absc(self):
        """Returns the list of the abscissas.

        Returns:
            list: List of abscissas.
        """
        return self.Valeurs()[0]

    def Ordo(self):
        """Returns the list of the real part of the ordinates.

        Returns:
            list: List of the real part of the ordinates.
        """
        return self.Valeurs()[1]

    def OrdoImg(self):
        """Returns the list of the imaginary part of the ordinates.

        Returns:
            list: List of the imaginary part of the ordinates.
        """
        return self.Valeurs()[2]

    def convert(self, arg="real"):
        """Returns a `t_fonction` or `t_fonction_c` object, a Python copy of
        the function.

        The values of the created function depends on `arg` value.
        Select `arg` is "real" for the real part, "imag" for the imaginary part,
        "modul" for the modulus, "phase" for the angle. In these cases the
        created function is a `t_fonction`.
        If `arg` is "complex", the created function is a `t_fonction_c`
        containing the complex values.

        Arguments:
            arg (str): type of conversion, possible values are "real", "imag",
                "modul", "phase" or "complex".

        Returns:
            misc: a `t_fonction_c` if `arg="complex"`, a `t_fonction` otherwise.
        """
        class_fonction = t_fonction
        if arg == "complex":
            class_fonction = t_fonction_c
        if arg == "real":
            ordo = self.Ordo()
        elif arg == "imag":
            ordo = self.OrdoImg()
        elif arg == "modul":
            ordo = NP.sqrt(NP.array(self.Ordo()) ** 2 + NP.array(self.OrdoImg()) ** 2)
        elif arg == "phase":
            ordo = NP.arctan2(NP.array(self.OrdoImg()), NP.array(self.Ordo())) * 180.0 / pi
        elif arg == "complex":
            ordo = list(map(complex, self.Ordo(), self.OrdoImg()))
        else:
            assert False, "unexpected value for arg: %r" % arg
        return class_fonction(self.Absc(), ordo, self.Parametres(), nom=self.getName())

    def __call__(self, val, tol=1.0e-6):
        """Evaluate a function at 'val'. If provided, 'tol' is a relative
        tolerance to match an abscissa value."""
        try:
            val = val.valeur
        except AttributeError:
            val = float(val)
        __ff = self.convert(arg="complex")
        return __ff(val, tol=tol)

    def Parametres(self):
        """Returns a dict containing the properties of the function.

        Returns:
            dict: keys of the dict are "INTERPOL", "NOM_PARA", "NOM_RESU",
            "PROL_GAUCHE", "PROL_DROITE", see `getProperties()` for the content.
        """
        TypeProl = {"E": "EXCLU", "L": "LINEAIRE", "C": "CONSTANT"}
        _, interp, para, result, extra, _ = self.getProperties()
        dico = {
            "INTERPOL": interp.split(),
            "NOM_PARA": para,
            "NOM_RESU": result,
            "PROL_GAUCHE": TypeProl[extra[0]],
            "PROL_DROITE": TypeProl[extra[1]],
        }
        return dico

    def Trace(self, FORMAT="TABLEAU", **kargs):
        """Plot a function."""
        gr = Graph()
        para = self.Parametres()
        gr.AjoutCourbe(
            Val=self.Valeurs(),
            Lab=[para["NOM_PARA"], para["NOM_RESU"] + "_R", para["NOM_RESU"] + "_I"],
        )
        gr.Trace(FORMAT=FORMAT, **kargs)
