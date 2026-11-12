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

from ..Utilities import no_new_attributes


class UnavailableObject:
    """This object is only available in parallel."""

    def __init__(self, *args, **kwargs):
        raise NameError(
            f"The object '{self.__class__.__name__}' is not available in this installation."
        )


class PyDataStructure:
    """Temporary object used as a DataStructure during a Command execution."""

    def __init__(self, name="unnamed"):
        """Initialization"""
        self._name = name

    def getName(self):
        """Return the CO name."""
        return self._name

    @property
    def userName(self):
        """Same as 'getName'."""
        return self.getName()

    @userName.setter
    def userName(self, name):
        self._name = name

    def getType(self):
        """Return a type for syntax checking."""
        raise NotImplementedError("must be subclassed")


class AsInteger(PyDataStructure):
    """This class defines a simple integer used as a DataStructure."""

    @classmethod
    def getType(cls):
        """Return type as string."""
        return "ENTIER"


class AsFloat(PyDataStructure):
    """This class defines a simple float used as a DataStructure."""

    @classmethod
    def getType(cls):
        """Return type as string."""
        return "REEL"


class NamedTuple:
    """This class defines a namedtuple-like object.

    This is not a namedtuple because the field names are known during the
    execution of the macro-command itself.

    Arguments:
        values (dict[str]): Values of each member.
    """

    _items = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, field_items={}):
        self._items = field_items

    def __getstate__(self):
        return self._items

    def __setstate__(self, items):
        self._items = items

    def __getattr__(self, key):
        if not self._items:
            return
        try:
            return self._items[key]
        except KeyError:
            raise AttributeError(f"'NamedTuple' object has no attribute {key!r}")

    # dicts keep insertion ordered in python>=3.7
    def __getitem__(self, idx):
        return list(self._items.values())[idx]

    def __len__(self):
        return len(self._items)

    def __repr__(self):
        values = ", ".join([f"{k}={v}" for k, v in self._items.items()])
        return f"NamedTuple({values})"

    def __iter__(self):
        return iter(self._items.values())

    def __contains__(self, elt):
        return elt in self._items.values()


class DataStructureDict(PyDataStructure):
    """Dict-like object that stores datastructures associated to a key.

    This is the implementation of derivatives of ``ds_dict`` objects used in the syntax.
    """

    object_type = None

    def __init__(self, name="unnamed"):
        super().__init__(name)
        self._store = {}

    @classmethod
    def getType(cls):
        """Return a type for syntax checking."""
        return cls.object_type + "_DICT"

    def __len__(self):
        return len(self._store)

    def __iter__(self):
        return iter(self._store)

    def __contains__(self, key):
        return key in self._store

    def keys(self):
        """Return a view on the access keys."""
        return self._store.keys()

    def values(self):
        """Return a view on the values."""
        return self._store.values()

    def items(self):
        """Return items."""
        return self._store.items()

    def __setitem__(self, key, obj):
        """Store an object with the given access key."""
        if obj.getType() != self.object_type:
            raise TypeError(f"__setitem__ value must be a {self.object_type!r}")
        self._store[key] = obj

    def __getitem__(self, key):
        """Returns the value for key if key is in the store, otherwise
        raises *KeyError*."""
        return self._store[key]

    def get(self, key, default=None):
        """Return the value for key if key is in the store, else default.

        Arguments:
            key (str): Access key.
            default (*object_type*, optional): Default value if no object is
                stored with that key.

        Returns:
            *object_type*: Object stored with that key.
        """
        return self._store.get(key, default)


class ThermalResultDict(DataStructureDict):
    """Set of thermal results."""

    object_type = "EVOL_THER"


class ElasticResultDict(DataStructureDict):
    """Set of elastic results."""

    object_type = "EVOL_ELAS"


class NonLinearResultDict(DataStructureDict):
    """Set of nonlinear results."""

    object_type = "EVOL_NOLI"
