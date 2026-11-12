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


from ..Helpers import LogicalUnitFile, MGISBuilder


def crea_lib_mfront_ops(self, NOM_COMPOR, UNITE_MFRONT=None, UNITE_LIBRAIRIE=None, **args):
    """Build a MGIS Behaviour object from a precompiled library or from a
    '.mfront' file.
    """
    name = NOM_COMPOR
    src = None
    if UNITE_MFRONT:
        src = LogicalUnitFile.filename_from_unit(UNITE_MFRONT)
    lib = None
    if UNITE_LIBRAIRIE:
        lib = LogicalUnitFile.filename_from_unit(UNITE_LIBRAIRIE)

    if src:
        flags = []
        if args.get("DEBUG", "NON") == "OUI":
            flags.append("--debug")
        return MGISBuilder.from_source(name, src, lib, flags)

    assert lib, "Exactly one argument of UNITE_MFRONT or UNITE_LIBRAIRIE is required"
    return MGISBuilder.from_library(NOM_COMPOR, lib)
