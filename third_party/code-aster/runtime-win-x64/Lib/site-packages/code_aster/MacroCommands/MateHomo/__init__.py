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

"""Package MateHomo"""

MESH_TOL = 1.0e-10


class HomoType:
    """
    Enumerator for Homogeneisation type.
    """

    Bulk = 0
    Plate = 1

    @staticmethod
    def value2str(value):
        """
        Get text representation of given value.

        Args:
            value (HomoType): Homogeneisation type.

        Returns:
            str: String representation of given value.

        Raises:
            KeyError: If wrong value is specified.
        """
        if value in (HomoType.Bulk,):
            return "MASSIF"
        elif value in (HomoType.Plate,):
            return "PLAQUE"
        raise KeyError("Unsupported value {}".format(value))

    @classmethod
    def str2value(cls, text):
        """
        Get value representation of given text.

        Args:
            text (str): Homogeneisation type.

        Returns:
            str: Value representation of given text.

        Raises:
            KeyError: If wrong text is specified.
        """
        if text in ("MASSIF",):
            return cls.Bulk
        elif text in ("PLAQUE",):
            return cls.Plate
        raise KeyError("Unsupported text {}".format(text))


class NameConverter:
    """
    Class to perfom name conversion for MED fields.
    """

    _trad = {
        "THER": "TH",
        "MECA": "ME",
        "DILA": "DI",
        "CORR_": "Z",
        "MEMB": "MB",
        "FLEX": "FL",
        "PINT": "PI",
    }

    @classmethod
    def toMed(cls, name):
        """
        Encode name to meet MED size limits.

        """
        assert "Z" not in name, f"{name} is already MED"
        s = name
        for src, dest in cls._trad.items():
            s = s.replace(src, dest)
        return s

    @classmethod
    def fromMed(cls, name):
        """
        Decode MED name.

        """
        assert "Z" in name, f"{name} is not MED"
        s = name
        for src, dest in cls._trad.items():
            s = s.replace(dest, src)

        for i in ("TEMP", "DEPL", "_"):
            s = s.rstrip(i)

        return s
