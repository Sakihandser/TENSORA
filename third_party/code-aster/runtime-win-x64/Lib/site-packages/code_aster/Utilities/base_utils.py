# coding: utf-8
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
:py:mod:`base_utils` --- General purpose utilities
**************************************************

This modules gives some basic utilities.
"""

import inspect
import sys
from array import array
from collections import UserDict, defaultdict
from decimal import Decimal
from functools import wraps

import numpy


def no_new_attributes(wrapped_setattr):
    """Raise an error on attempts to add a new attribute, while
    allowing existing attributes to be set to new values.

    Taken from ?
    'Python Cookbook' by Alex Martelli, Anna Ravenscroft, David Ascher,
    ?6.3. 'Restricting Attribute Setting'
    """

    def __setattr__(self, name, value):
        if hasattr(self, name):  # not a new attribute, allow setting
            wrapped_setattr(self, name, value)
        else:
            raise AttributeError(f"Can't add attribute {name!r} to {self}")

    return __setattr__


def import_object(uri):
    """Load and return a python object (class, function...).
    Its `uri` looks like "mainpkg.subpkg.module.object", this means
    that "mainpkg.subpkg.module" is imported and "object" is
    the object to return.

    Arguments:
        uri (str): Path to the object to import.

    Returns:
        object: Imported object.
    """
    path = uri.split(".")
    modname = ".".join(path[:-1])
    if len(modname) == 0:
        raise ImportError(f"invalid uri: {uri}")
    mod = obj = "?"
    objname = path[-1]
    try:
        __import__(modname)
        mod = sys.modules[modname]
    except ImportError as err:
        raise ImportError(f"can not import module : {modname} ({err})")
    try:
        obj = getattr(mod, objname)
    except AttributeError:
        raise AttributeError(
            f"object ({objname}) not found in module {modname!r}. "
            f"Module content is: {tuple(dir(mod))}"
        )
    return obj


def get_caller_context(level):
    """Return the context some levels upper.

    Arguments:
        level (int): Number of parents in the calling stack. 0 means where
            `get_caller_context` is called. "Frozen" frames are skipped.

    Returns:
        dict: 'globals' context at this level.
    """
    caller = inspect.currentframe()
    count = 0
    while count < level + 1:
        caller = caller.f_back
        if caller.f_code.co_filename.startswith("<frozen"):
            continue
        count += 1
    try:
        context = caller.f_globals
    finally:
        del caller
    return context


def force_list(values):
    """Ensure `values` is iterable (list, tuple, array...) and return it as
    a list."""
    if not is_sequence(values):
        values = [values]
    return list(values)


def force_tuple(values):
    """Ensure `values` is iterable (list, tuple, array...) and return it as
    a tuple.
    """
    return tuple(force_list(values))


def cmp(a, b, rel_tol=None, abs_tol=None):
    """Compare two values using relative or absolute tolerance
    (similar to `math.isclose()`).

    Arguments:
        a (float): first argument.
        b (float): second argument.
        rel_tol (float, optional): relative tolerancev, *None* if not used.
        abs_tol (float, optional): minimum absolute tolerance, *None* if not used.

    Returns:
        int: -1 if a < b, 0 if a == b, +1 if a > b using tolerances.
    """
    eps = 0.0
    if rel_tol is not None:
        eps = rel_tol * max(abs(a), abs(b))
    if abs_tol is not None:
        eps = max(eps, abs_tol)
    if abs(a - b) < eps:
        return 0
    if a - eps < b:
        return -1
    return 1


def is_int(obj, onvalue=False):
    """Tell if an object is an integer.

    Arguments:
        obj (misc): Object to be tested.
        onvalue (bool, optional): If *onvalue* is True, accept a float number
            that is equal to its integer part. If *False*, acceptance is
            only based on the object type.
    """
    return isinstance(obj, (int, numpy.integer)) or (onvalue and is_float(obj) and obj == int(obj))


def is_float(obj):
    """Tell if an object is a float number."""
    return isinstance(obj, (float, Decimal, numpy.float32, numpy.float64))


def is_float_or_int(obj):
    """Tell if an object is a float or an integer."""
    return is_float(obj) or is_int(obj)


def is_complex(obj):
    """Tell if an object is a complex number."""
    if (
        isinstance(obj, (list, tuple))
        and len(obj) == 3
        and obj[0] in ("RI", "MP")
        and is_float_or_int(obj[1])
        and is_float_or_int(obj[2])
    ):
        return True
    return isinstance(obj, complex)


def is_number(obj):
    """Tell if an object is a number."""
    return is_float_or_int(obj) or is_complex(obj)


def is_str(obj):
    """Tell if an object is a string."""
    return isinstance(obj, str)


def is_sequence(obj):
    """Is a sequence (allow iteration, not a string)?"""
    return isinstance(obj, (list, tuple, array, numpy.ndarray))


value_is_sequence = is_sequence


def array_to_list(obj):
    """Convert an object to a list if possible (using `tolist()`) or keep it
    unchanged otherwise.

    Arguments:
        obj (misc): Object to convert.

    Returns:
        misc: Object unchanged or a list.
    """
    try:
        return obj.tolist()
    except AttributeError:
        return obj


def accept_array(func):
    """Decorator that automatically converts numpy arrays to lists.

    Needed to pass an array as argument to a Python/C++ method.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        """Wrapper"""
        args = [array_to_list(i) for i in args]
        return func(*args, **kwargs)

    return wrapper


class Singleton(type):
    """Singleton implementation in python (Metaclass)."""

    # add _singleton_id attribute to the subclasses to be independant of import
    # path used
    __inst = {}

    def __call__(cls, *args, **kws):
        cls_id = getattr(cls, "_singleton_id", cls)
        if cls_id not in cls.__inst:
            cls.__inst[cls_id] = super(Singleton, cls).__call__(*args, **kws)
        return cls.__inst[cls_id]


class ReadOnlyDict(UserDict):
    """Read-only dict object with default value to *None*.

    Items can be added but their values can not be changed later.
    """

    def __getitem__(self, key):
        """Disable setitem"""
        return self.data.get(key)

    def __setitem__(self, key, value):
        """Disable __setitem__"""
        if key in self:
            raise AttributeError("ReadOnlyDict: values can not be changed!")
        super().__setitem__(key, value)


# aster_pkginfo/aster_config will only be available after installation
try:
    from .aster_pkginfo import version_info
except ImportError:
    version_info = ()
try:
    from .aster_config import config as _cfg

    config = ReadOnlyDict(**_cfg)
    del _cfg
except ImportError:
    config = defaultdict(lambda: None)
