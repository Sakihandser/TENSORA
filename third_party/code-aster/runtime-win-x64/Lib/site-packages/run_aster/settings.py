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
:py:mod:`settings` --- Objects to deal with settings
----------------------------------------------------

:py:class:`Store` is a general storage object that holds various kinds
of settings as typed parameters.

The base object is the :py:class:`AbstractParameter` object from which are
derivated objects to store values of type *str*, *int*, *float*, *bool* and
list of *str*.
"""

import os
from string import Template

from .logger import logger

DEPRECATED = "__DEPRECATED__"


def subst_vars(value: str) -> str:
    """Return the string after substituting environment vars."""
    if "$" in value:
        try:
            value = Template(value).substitute(os.environ)
        except (KeyError, ValueError):
            pass
    return value


class AbstractParameter:
    """An abstract parameter that must be subclassed to hold a typed value."""

    def __init__(self, name):
        self._name = name
        self._value = None

    @property
    def name(self):
        """str: Parameter name."""
        return self._name

    @property
    def value(self):
        """misc: Value of the parameter."""
        return self._value

    def convert(self, value):
        """Convert a value for the parameter type."""
        try:
            return self._convert(value)
        except (TypeError, ValueError) as exc:
            logger.error("Parameter %r: %s", self.name, exc, exception=exc)

    def _convert(self, value):
        raise NotImplementedError("must be subclassed!")

    def set(self, value):
        """Convert and set the value.

        Arguments:
            value (misc): New value.
        """
        self._value = self.convert(value)

    @classmethod
    def factory(cls, store_typed_params, name):
        """Create a Parameter of the right type.

        Arguments:
            store_typed_params (dict): Dict of parameters supported by the
                :py:class:`Store` giving the excpected type.
            name (str): Parameter name.
        """
        typ = store_typed_params.get(name)
        if typ is None:
            logger.warning("unknown parameter: %r", name)
            return None
        if typ == DEPRECATED:
            return None
        klass = cls._typed_subclasses(typ)
        if not klass:
            raise TypeError(typ)
        return klass(name)

    @staticmethod
    def _typed_subclasses(typ):
        """Return the subclass for the expected type or *None* if not found."""
        return {
            "str": ParameterStr,
            "varstr": ParameterVarStr,
            "bool": ParameterBool,
            "int": ParameterInt,
            "float": ParameterFloat,
            "list[str]": ParameterListStr,
            "varlist[str]": ParameterVarListStr,
            "dict[str]": ParameterDictStr,
        }.get(typ)


class ParameterStr(AbstractParameter):
    """A parameter defined in a Export object of type string.

    It may use environment variable "${VAR}", substitution is only done once
    when the value is assigned.
    """

    @staticmethod
    def _convert(value):
        if isinstance(value, (list, tuple)):
            value = " ".join([str(i) for i in value])
        if not value:
            return value
        return subst_vars(str(value))


class VarMixin:
    """Mixin class for a parameter that may be overridden by environment."""

    def set(self, value):
        """Convert and set the value.

        Arguments:
            value (misc): New value.
        """
        self._value = self.convert(os.environ.get(self._name, value))


class ParameterVarStr(VarMixin, ParameterStr):
    """A parameter defined in a Export object of type string that may be
    overridden by an environment variable."""


class ParameterBool(AbstractParameter):
    """A parameter defined in a Export object of type boolean."""

    @staticmethod
    def _convert(value):
        if isinstance(value, (list, tuple)):
            value = " ".join([str(i) for i in value])
        if value == "":
            value = True
        elif value == "False":
            value = False
        return bool(value)


class ParameterInt(AbstractParameter):
    """A parameter defined in a Export object of type integer."""

    @staticmethod
    def _convert(value):
        if isinstance(value, (list, tuple)):
            value = " ".join([str(i) for i in value])
        if value == "":
            value = 0
        return int(float(value))


class ParameterFloat(AbstractParameter):
    """A parameter defined in a Export object of type float."""

    @staticmethod
    def _convert(value):
        if isinstance(value, (list, tuple)):
            value = " ".join([str(i) for i in value])
        if value == "":
            value = 0.0
        return float(value)


class ParameterListStr(AbstractParameter):
    """A parameter defined in a Export object of type list of strings."""

    @staticmethod
    def _convert(value):
        if not isinstance(value, (list, tuple)):
            value = [value]
        value = [str(i) for i in value]
        return value


class ParameterVarListStr(VarMixin, ParameterListStr):
    """A parameter defined in a Export object of type list of strings that may
    be overridden by an environment variable."""


class ParameterDictStr(AbstractParameter):
    """A parameter defined in a Export object of type dict of strings."""

    @staticmethod
    def _convert(value):
        if not isinstance(value, dict):
            raise TypeError(f"dict expected, not {value}")
        for key, string in value.items():
            if not isinstance(key, str):
                raise TypeError(f"str expected, not {string}")
            value[key] = ParameterStr._convert(string)
        return value

    def set(self, value):
        """Convert and update the dict.

        Arguments:
            value (dict): New value.
        """
        if self._value is None:
            self._value = {}
        self._value.update(self.convert(value))


class Store:
    """A base object to store some settings.

    This class must be subclassed and a ``_new_param`` class method must be added
    to make `set()` method usable.
    """

    def __init__(self):
        self._params = {}

    def __len__(self):
        """Return the storage size.

        Returns:
            int: Number of stored parameters.
        """
        return len(self._params)

    def add(self, param):
        """Add a parameter.

        Arguments:
            param (*Parameter*): Parameter object.
        """
        self._params[param.name] = param

    def has_param(self, name):
        """Tell if `name` is a known parameter.

        Arguments:
            name (str): Parameter name.

        Returns:
            bool: *True* it the parameter is defined, *False* otherwise.
        """
        return name in self._params

    def get_param(self, name):
        """Return a parameter.

        Arguments:
            name (str): Parameter name.

        Returns:
            misc: Parameter or *None* if the parameter does not exist.
        """
        return self._params.get(name)

    def get(self, name, default=None):
        """Return a parameter value.

        Arguments:
            name (str): Parameter name.
            default (misc, optional): Default value if the parameter does
                not exist.

        Returns:
            misc: Parameter value.
        """
        param = self.get_param(name)
        return param.value if param and param.value is not None else default

    def set(self, name, value):
        """Automatically add a parameter of the expected type.

        Arguments:
            name (str): Parameter name.
            value (misc): Parameter value.
        """
        param = self._params.setdefault(name, self._new_param(name))
        if not param:
            del self._params[name]
            return
        param.set(value)

    @staticmethod
    def _new_param(name):
        """Create a Parameter of the right type."""
        return None
