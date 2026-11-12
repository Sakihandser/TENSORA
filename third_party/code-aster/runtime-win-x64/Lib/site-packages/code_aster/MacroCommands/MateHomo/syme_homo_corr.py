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

from .syme_utilities import SymmetryManager


def BuildFullSymmetryMassif(resuin):
    """
    Returns a new result containing the symmetric projection merged with the
    current one.

    This function performs a symmetric projection of the input corrector fields
    along the `X`, `Y`, and `Z` axes, with respect to the Cartesian origin
    (0, 0, 0). The projection is done sequentially along each axis, and only
    nodal fields are considered in this process. The resulting fields are merged
    to produce a comprehensive symmetric dataset.

    Args:
        resuin (MEDFileData): The input corrector fields to be symmetrically
            projected.

    Returns:
        MEDFileData: The output corrector fields containing the symmetric
            projections merged with the original data.
    """

    point = [0, 0, 0]
    pmanager_x = SymmetryManager(point, "X")
    pmanager_y = SymmetryManager(point, "Y")
    pmanager_z = SymmetryManager(point, "Z")

    projX = pmanager_x.build_symmetry(resuin)
    projY = pmanager_y.build_symmetry(projX)
    projZ = pmanager_z.build_symmetry(projY)

    return projZ
