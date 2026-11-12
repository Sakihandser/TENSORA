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
This module defines `adapt_syntax` functions shared by several commands.
"""

from ..Cata.Syntax import _F


def adapt_increment_init(keywords, init_kwd):
    """Adapt INCREMENT keyword: automatically adds INST_INIT from ETAT_INIT
    if it is not defined.

    Arguments:
        keywords (dict): Keywords arguments of user's keywords, changed
            in place.
        init_kwd (str): Keyword defining the initial state under ETAT_INIT.
    """
    incr = keywords["INCREMENT"][0]
    if "INST_INIT" in incr or "NUME_INST_INIT" in incr:
        return

    init_state = keywords.get("ETAT_INIT", _F())
    if init_state and type(init_state) in (list, tuple):
        init_state = init_state[0]
    init_result = init_state.get(init_kwd)
    if init_state and init_result:
        inst_init = init_result.getLastTime()
        if "INST" in init_state:
            inst_init = init_state["INST"]
        if "NUME_ORDRE" in init_state:
            inst_init = init_result.getTime(init_state["NUME_ORDRE"])
        incr["INST_INIT"] = inst_init
    else:
        incr["NUME_INST_INIT"] = 0
    keywords["INCREMENT"] = incr
