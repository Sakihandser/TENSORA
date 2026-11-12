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
:py:class:`Material` --- Assignment of material properties on mesh
************************************************************************
"""

import re

import aster
from libaster import Material

from ..Cata.Commands.defi_materiau import DEFI_MATERIAU as DEF
from ..Cata.Syntax import _F
from ..Cata.SyntaxUtils import old_complex
from ..Messages import UTMESS
from ..Supervis.visitors import EnumVisitor
from ..Utilities import injector, logger


@injector(Material)
class ExtendedMaterial:
    cata_sdj = "SD.sd_mater.sd_mater"

    class Builder(EnumVisitor):
        """This object loops on factor keywords to define material properties."""

        def __init__(self, mater):
            """Initialization"""
            super().__init__()
            self.mater = mater

        def visitFactorKeyword(self, step, userDict=None):
            """Visit a FactorKeyword object"""
            if not userDict:
                return
            if isinstance(userDict, dict):
                userDict = [userDict]
            # loop on occurrences filled by the user
            key = self._stack[-1]
            for userOcc in userDict:
                self._add_properties_with_cata(step, key, userOcc)

        def _add_properties_with_cata(self, fact, name, kwargs):
            """Define properties for a behaviour, based on a factor keyword.

            Arguments:
                fact (*FactorKeyword*): Syntax object defining the keywords.
                name (str): Behaviour name (equivalent to factor keywords of DEFI_MATERIAU).
                kwargs (dict): Properties with their values.
            """
            mater = self.mater
            ordr = kwargs.get("ORDRE_PARAM", [])
            kord = []
            seen = []
            valR = []
            valC = []
            nameR = []
            nameC = []
            nameT = []
            nameF = []
            nameLR = []
            nameLF = []
            obj = []
            idx = mater.size() + 1
            userOrig = kwargs.copy()
            for key, value in kwargs.items():
                if key == "ORDRE_PARAM":
                    continue
                # NB: block conditions are evaluated with the original values
                skw = fact.getKeyword(key, userOrig)
                skw.accept(self, value)
                if self._changed is not None:
                    value = kwargs[key] = self._changed
                    self._changed = None
                typ = skw.definition["typ"]
                limit = skw.definition.get("max", 1)
                logger.debug("keyword %s: %s - type %s", key, value, typ)
                if isinstance(typ, (list, tuple)) and len(typ) == 1:
                    typ = typ[0]
                if typ == "TXM":
                    if "enum" not in skw.definition:
                        # only used for catalog conditions
                        continue
                    # used as float
                    typ = "R"
                # specific cases
                islist = key == "LISTE_COEF" or (typ in ("R", "C") and limit > 1)
                if islist:
                    assert not ordr, "'LISTE_COEF' and 'ORDRE_PARAM' exclude each other!"
                    if typ == "R":
                        nameLR.append(key)
                        obj.append(mater._storeListReal(value))
                        logger.debug("store reals: %s.LISV_R8: %s", obj[-1], value)
                    else:
                        nameLF.append(key)
                        obj.append(mater._storeListFunc([func.getName() for func in value]))
                        mater.addDependencies(*value)
                        logger.debug("store functions: %s.LISV_FO: %s", obj[-1], value)
                    seen.append(key)
                    continue

                # generic cases
                if typ == "R":
                    nameR.append(key)
                    valR.append(value)
                elif typ == "C":
                    nameC.append(key)
                    valC.append(old_complex(value))
                elif hasattr(typ, "getType") and typ.getType() == "TABLE_SDASTER":
                    nameT.append(key)
                    obj.append(value.getName())
                    mater.addDependency(value)
                else:
                    # function/formula
                    nameF.append(key)
                    obj.append(value.getName())
                    mater.addDependency(value)
                    if name in ("TRACTION", "META_TRACTION"):
                        mater._setTractionFunction(name, key, value)

                seen.append(key)

            valK = nameR + nameC + nameF + nameT + nameLR + nameLF + obj
            if ordr:
                kord.append(len(ordr))
                kord.append(len(seen))
                # see rcvalt.F90, line ~215
                kord.extend([ordr.index(key) + 1 for key in seen])
                kord.extend([valK.index(key) + 1 if key in nameR else 0 for key in seen])
                kord.extend([valK.index(key) + 1 if key in nameC else 0 for key in seen])
                kord.extend(
                    [
                        valK.index(key) + 1 if key not in nameR and key not in nameC else 0
                        for key in seen
                    ]
                )
            logger.debug("Content of {}.CPT.{:06d}".format(mater.getName(), idx))
            logger.debug(".VALR: %s, size: %d", valR, len(nameR))
            logger.debug(".VALC: %s, size: %d", valC, len(nameC))
            logger.debug(".VALK: %s", valK)
            if ordr:
                logger.debug(".ORDR: %s", ordr)
                logger.debug(".KORD: %s", kord)
            name = re.sub("_FO$", "", name.strip())
            logger.debug('NOMRC.append("%s")', name)
            mater._addProperties(name, len(seen), valR, valC, valK, ordr, kord)

    def addProperties(self, name, context=None, **kwargs):
        """Define properties for a behaviour.

        Arguments:
            name (str): Behaviour name (equivalent to factor keywords of DEFI_MATERIAU).
            context (dict, optional): External keywords that may be used as condition.
            kwargs (dict): Properties with their values.
        """
        args = {name: _F(kwargs)}
        visit = self.Builder(self)
        if context:
            args.update(context)
        DEF.addDefaultKeywords(args)
        DEF.accept(visit, args)

    def RCVALE(self, phenomene, nompar=(), valpar=(), nomres=(), stop=1):
        """Appel à la routine fortran RCVALE pour récupérer les valeurs des
        propriétés du matériau.
        """
        # vérification des arguments
        if not type(nompar) in (list, tuple):
            nompar = [nompar]
        if not type(valpar) in (list, tuple):
            valpar = [valpar]
        if not type(nomres) in (list, tuple):
            nomres = [nomres]
        nompar = tuple(nompar)
        valpar = tuple(valpar)
        nomres = tuple(nomres)
        if len(nompar) != len(valpar):
            vk1 = ", ".join(nompar)
            vk2 = ", ".join([repr(v) for v in valpar])
            UTMESS("F", "SDVERI_4", valk=[vk1, vk2])
        if len(nomres) < 1:
            UTMESS("F", "SDVERI_5")
        # appel à l'interface Python/C
        return aster.rcvale(self.getName(), phenomene, nompar, valpar, nomres, stop)
