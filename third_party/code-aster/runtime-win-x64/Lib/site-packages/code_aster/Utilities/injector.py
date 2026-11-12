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
:py:mod:`injector` --- Methods injection in pybind11 Objects
************************************************************
"""


def injector(pybind_class):
    """Decorator to inject methods into pybind11 objects.

    Private methods are not injected, except a sublist:
    ``__add__``,
    ``__call__``,
    ``__eq__``,
    ``__getattr__``,
    ``__getinitargs__``,
    ``__getitem__``,
    ``__getstate__``,
    ``__getstate_manages_dict__``,
    ``__iadd__``,
    ``__imul__``,
    ``__init__``,
    ``__len__``,
    ``__mul__``,
    ``__setstate__``.

    Arguments:
        pybind_class (*pybind11 class*): pybind11 class to enrich.

    Returns:
        class: Decorated class.
    """

    def decorated(cls):
        for parent in reversed(cls.mro()):
            if parent is object:
                continue
            for name, attr in parent.__dict__.items():
                if name.startswith("__"):
                    if name not in (
                        "__add__",
                        "__call__",
                        "__eq__",
                        "__getattr__",
                        "__getinitargs__",
                        "__getitem__",
                        "__getstate__",
                        "__getstate_manages_dict__",
                        "__iadd__",
                        "__imul__",
                        "__init__",
                        "__len__",
                        "__mul__",
                        "__setstate__",
                    ):
                        continue
                setattr(pybind_class, name, attr)

    return decorated
