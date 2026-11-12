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

ASTER_TYPES = [1, 2, 4, 6, 7, 9, 11, 12, 14, 16, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27]

MED_TYPES = [
    1,
    102,
    103,
    104,
    203,
    206,
    207,
    204,
    208,
    209,
    304,
    310,
    306,
    315,
    318,
    305,
    313,
    308,
    320,
    327,
]

MED2ASTER_CONNECT = {
    "POINT1": [0],
    "SEG2": range(2),
    "TRI3": range(3),
    "QUAD4": range(4),
    "TETRA4": [0, 2, 1, 3],
    "HEXA8": [0, 3, 2, 1, 4, 7, 6, 5],
    "PYRA5": [0, 3, 2, 1, 4],
    "PENTA6": [0, 2, 1, 3, 5, 4],
    "SEG3": range(3),
    "TRI6": range(6),
    "QUAD8": range(8),
    "TETRA10": [0, 2, 1, 3, 6, 5, 4, 7, 9, 8],
    "HEXA20": [0, 3, 2, 1, 4, 7, 6, 5, 11, 10, 9, 8, 16, 19, 18, 17, 15, 14, 13, 12],
    "PYRA13": [0, 3, 2, 1, 4, 8, 7, 6, 5, 9, 12, 11, 10],
    "PENTA15": [0, 2, 1, 3, 5, 4, 8, 7, 6, 12, 14, 13, 11, 10, 9],
    "SEG4": range(4),
    "TRI7": range(7),
    "QUAD9": range(9),
    "PENTA18": [0, 2, 1, 3, 5, 4, 8, 7, 6, 12, 14, 13, 11, 10, 9, 17, 16, 15],
    "HEXA27": [
        0,
        3,
        2,
        1,
        4,
        7,
        6,
        5,
        11,
        10,
        9,
        8,
        16,
        19,
        18,
        17,
        15,
        14,
        13,
        12,
        20,
        24,
        23,
        22,
        21,
        25,
        26,
    ],
}

MYMED2ASTER_CONNECT = {
    1: [0],
    102: range(2),
    203: range(3),
    204: range(4),
    304: [0, 2, 1, 3],
    308: [0, 3, 2, 1, 4, 7, 6, 5],
    305: [0, 3, 2, 1, 4],
    306: [0, 2, 1, 3, 5, 4],
    103: range(3),
    206: range(6),
    208: range(8),
    310: [0, 2, 1, 3, 6, 5, 4, 7, 9, 8],
    320: [0, 3, 2, 1, 4, 7, 6, 5, 11, 10, 9, 8, 16, 19, 18, 17, 15, 14, 13, 12],
    313: [0, 3, 2, 1, 4, 8, 7, 6, 5, 9, 12, 11, 10],
    315: [0, 2, 1, 3, 5, 4, 8, 7, 6, 12, 14, 13, 11, 10, 9],
    104: range(4),
    207: range(7),
    209: range(9),
    318: [0, 2, 1, 3, 5, 4, 8, 7, 6, 12, 14, 13, 11, 10, 9, 17, 16, 15],
    327: [
        0,
        3,
        2,
        1,
        4,
        7,
        6,
        5,
        11,
        10,
        9,
        8,
        16,
        19,
        18,
        17,
        15,
        14,
        13,
        12,
        20,
        24,
        23,
        22,
        21,
        25,
        26,
    ],
}


def toAsterGeoType(medfile_type):
    """Convert a med mesh type to a code_aster type.

    Arguments:
        medfile_type (int): med type.

    Returns:
        int: code_aster type (index in '&CATA.TM.NOMTM').
    """
    if not hasattr(toAsterGeoType, "cache_dict"):
        toAsterGeoType.cache_dict = dict(zip(MED_TYPES, ASTER_TYPES))
    return toAsterGeoType.cache_dict[medfile_type]
