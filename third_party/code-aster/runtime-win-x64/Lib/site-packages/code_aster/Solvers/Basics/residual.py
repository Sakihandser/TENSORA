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

from ...Utilities import no_new_attributes


class Residuals:
    """Container to store intermediate field.

    Attributes:
        resi (FieldOnNodesReal): Global residual.
        resi_int (FieldOnNodesReal):  Internal residual.
        resi_ext (FieldOnNodesReal): External residual.
        resi_dual (FieldOnNodesReal): Dirichlet reactions.
        resi_stress (FieldOnNodesReal): Internal forces.
        resi_cont (FieldOnNodesReal): Contact residual.
        resi_mass (FieldOnNodesReal): Inertial residual.
    """

    resi = resi_int = resi_ext = resi_dual = resi_stress = resi_cont = resi_mass = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def update(self):
        if self.resi:
            self.resi.updateValuePointers()
        if self.resi_int:
            self.resi_int.updateValuePointers()
        if self.resi_ext:
            self.resi_ext.updateValuePointers()
        if self.resi_dual:
            self.resi_dual.updateValuePointers()
        if self.resi_stress:
            self.resi_stress.updateValuePointers()
        if self.resi_cont:
            self.resi_cont.updateValuePointers()
        if self.resi_mass:
            self.resi_mass.updateValuePointers()

    def reset(self):
        self.resi = None
        self.resi_int = None
        self.resi_ext = None
        self.resi_dual = None
        self.resi_stress = None
        self.resi_cont = None
        self.resi_mass = None
