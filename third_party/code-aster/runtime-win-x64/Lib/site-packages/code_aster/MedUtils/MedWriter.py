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

from enum import Enum, auto

from ..Objects import AsterToMedWriter
from .medtoasterconnectivity import ASTER_TYPES, MED_TYPES, MYMED2ASTER_CONNECT, toAsterGeoType

toMedGeoType = None
if ASTER_TYPES is not None and MED_TYPES is not None:
    toMedGeoType = dict(zip(ASTER_TYPES, MED_TYPES))


def printMeshToMedFile(mesh, filename, local=True):
    """Print mesh in a med file

    Arguments:
        mesh (Mesh|ParallelMesh|ConnectionMesh): mesh to print
        filename (Path|str): filename of MED file
        local (bool=True): True if one med file must open for each processor

    Return:
        bool: True if print is ok
    """
    writer = AsterToMedWriter()
    return writer.printMesh(mesh, filename, local)


def printResultToMedFile(result, filename, local=True):
    """Print result in a med file

    Arguments:
        result (Result): results to print
        filename (Path|str): filename of MED file
        local (bool=True): True if one med file must open for each processor

    Return:
        bool: True if print is ok
    """
    writer = AsterToMedWriter()
    return writer.printResult(result, filename, local)
