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
This module gives objects to manage the execution.
"""

from .Check_Material_Functions import check_dis_choc_elas
from .LogicalUnit import Action, FileAccess, FileType, LogicalUnitFile, ReservedUnitUsed
from .MGISHelper import MGISBuilder, adapt_for_mgis_behaviour
from .syntax_adapters import adapt_increment_init
