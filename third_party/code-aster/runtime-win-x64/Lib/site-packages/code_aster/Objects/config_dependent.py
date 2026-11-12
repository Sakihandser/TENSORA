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
Objects defined depending on the configuration
**********************************************

The availability of the objects depends on the configuration.
Some of them are not available with a sequential version.
Some others are only defined if a prerequisite is well configured.
"""

import libaster
from .datastructure_py import UnavailableObject


def add_undefined(store):
    """Add config dependent objects.

    Arguments:
        store (dict): Container object.
    """
    # NB: keep consistency with the list imported!
    _names = (
        "CommGraph",
        "ConnectionMesh",
        "IncompleteMesh",
        "MedFileAccessType",
        "MedFileReader",
        "MeshBalancer",
        "MeshConnectionGraph",
        "MGISBehaviour",
        "ParallelContactNew",
        "ParallelContactPairing",
        "ParallelDOFNumbering",
        "ParallelEquationNumbering",
        "ParallelFiniteElementDescriptor",
        "ParallelFrictionNew",
        "ParallelMechanicalLoadFunction",
        "ParallelMechanicalLoadReal",
        "ParallelMesh",
        "ParallelThermalLoadFunction",
        "ParallelThermalLoadReal",
        "PtScotchPartitioner",
    )
    for obj in _names:
        store[obj] = getattr(libaster, obj, type(obj, (UnavailableObject,), {}))


add_undefined(globals())
del add_undefined
