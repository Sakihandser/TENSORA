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
:py:class:`Formula` --- Formula object
**************************************
"""

import traceback

from libaster import Formula

from ..Objects.Serialization import InternalStateBuilder
from ..Utilities import force_list, initial_context, injector, logger


class FormulaStateBuilder(InternalStateBuilder):
    """Class that returns the internal state of a *Formula*."""

    def save(self, form):
        """Return the internal state of a *Formula* to be pickled.

        Arguments:
            form (*Formula*): The *Formula* object to be pickled.

        Returns:
            *InternalStateBuilder*: The internal state itself.
        """
        super().save(form)
        init = initial_context()
        user_ctxt = {}
        # use 'Serializer._filteringContext'?
        for key, val in form.getContext().items():
            # objects defined in *main* could not be restored/reimported
            if getattr(val, "__module__", "") == "__main__":
                logger.warning("can not pickle object: %s %s", key, type(val))
                continue
            if val is not init.get(key):
                user_ctxt[key] = val
        self._st["expr"] = form.getExpression()
        self._st["ctxt"] = user_ctxt
        return self

    def restore(self, form):
        """Restore the *DataStructure* content from the previously saved internal
        state.

        Arguments:
            form (*DataStructure*): The *DataStructure* object to be restored.
        """
        super().restore(form)
        form.setExpression(self._st["expr"])
        # try to load the context
        try:
            ctxt = initial_context()
            logger.debug("restoring formula context: %s", self._st["ctxt"])
            ctxt.update(self._st["ctxt"])
            form.setContext(ctxt)
        except:
            logger.warning("can not restore context of formula %r", form.getName())
            logger.debug(traceback.format_exc())


@injector(Formula)
class ExtendedFormula:
    cata_sdj = "SD.sd_fonction.sd_formule"
    internalStateBuilder = FormulaStateBuilder

    def __call__(self, *val):
        """Evaluate the formula with the given variables values.

        Arguments:
            val (list[float]): List of the values of the variables.

        Returns:
            float/complex: Value of the formula for these values.
        """
        result = self.evaluate(force_list(val))
        if self.getType() == "FORMULE_C":
            result = complex(*result)
        else:
            result = result[0]
        return result

    def Parametres(self):
        """Return a dict containing the properties of the formula that can be
        directly passed to CALC_FONC_INTERP.

        Same method exists for real and complex function.

        Returns:
            dict: Dict of properties.
        """
        dico = {
            "INTERPOL": ["LIN", "LIN"],
            "NOM_PARA": self.getVariables(),
            "NOM_RESU": self.getProperties()[3],
            "PROL_DROITE": "EXCLU",
            "PROL_GAUCHE": "EXCLU",
        }
        return dico
