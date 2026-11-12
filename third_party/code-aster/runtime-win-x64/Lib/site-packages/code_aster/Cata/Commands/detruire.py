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


from ..Commons import *
from ..Language.DataStructure import *
from ..Language.Syntax import *

from ..Language.SyntaxUtils import deprecate, force_list


def compat_syntax(keywords):
    """Hook to adapt syntax from a old version or for compatibility reasons.

    Arguments:
        keywords (dict): User's keywords, changed in place.
    """
    to_del = []
    kwlist = force_list(keywords.pop("CONCEPT", []))
    if kwlist:
        deprecate("DETRUIRE/CONCEPT/NOM", case=3, help="Just use DETRUIRE/NOM=... instead.")
        for occ in kwlist:
            to_del.extend(force_list(occ["NOM"]))
        keywords["NOM"] = to_del
    if keywords.pop("OBJET", None):
        deprecate("DETRUIRE/OBJET", case=2, help="Use DETRUIRE/NOM=... instead.")


DETRUIRE = MACRO(
    nom="DETRUIRE",
    op=None,
    compat_syntax=compat_syntax,
    fr=tr("Détruit des concepts utilisateurs du contexte courant"),
    NOM=SIMP(statut="o", typ=assd, validators=NoRepeat(), max="**"),
    INFO=SIMP(statut="f", typ="I", into=(1, 2), defaut=1),
)
