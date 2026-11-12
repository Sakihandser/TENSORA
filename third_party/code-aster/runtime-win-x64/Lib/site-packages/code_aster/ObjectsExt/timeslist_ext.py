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
:py:class:`TimesList` --- List of times
******************************************

This object stores a list of the times for evolutive operators.

This object holds transitionnally a *TimeStepper* object.
This allows to continue to use the *TimesList* for legacy operators and the
*TimeStepper* for new ones.
"""

from libaster import TimesList

from ..Objects.Serialization import InternalStateBuilder
from ..Solvers import TimeStepper
from ..Utilities import injector


class TimesListStateBuilder(InternalStateBuilder):
    """Class that returns the internal state of a *TimesList*."""

    def save(self, obj):
        """Return the internal state of a *TimesList* to be pickled.

        Arguments:
            obj (*TimesList*): The *TimesList* object to be pickled.

        Returns:
            *InternalStateBuilder*: The internal state itself.
        """
        super().save(obj)
        self._st["stepper"] = obj.stepper
        return self

    def restore(self, obj):
        """Restore the *DataStructure* content from the previously saved internal
        state.

        Arguments:
            obj (*DataStructure*): The *DataStructure* object to be restored.
        """
        super().restore(obj)
        obj.stepper = self._st["stepper"]


@injector(TimesList)
class ExtendedTimesList:
    cata_sdj = "SD.sd_list_inst.sd_list_inst"
    internalStateBuilder = TimesListStateBuilder
    orig_init = TimesList.__init__

    def __init__(self, *args, **kwargs):
        self.orig_init(*args, **kwargs)
        self.stepper = None

    def __getattr__(self, attr):
        """Returns the attribute of the underlying :py:class:`TimeStepper`
        object if it does not exist."""
        if attr in ("__getstate__", "__setstate__"):
            raise AttributeError("'TimesList' object has no attribute '{0}'".format(attr))
        return getattr(self.stepper, attr)

    def buildStepperFromKeywords(self, keywords):
        """Assign the underlying *TimeStepper* object.

        Args:
            stepper (TimeStepper): Underlying object.
        """
        self.stepper = TimeStepper.command_factory(keywords)

    def setValues(self, values):
        """
        Args:
            values (list[float]): list of values to set
        """
        self._setValues(values)
        self.stepper.setTimes(values)
