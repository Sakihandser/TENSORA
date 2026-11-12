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
Useful objects used to build operators.
"""

from abc import ABC, abstractmethod
from enum import IntFlag, auto
from inspect import isabstract

from ...Utilities import logger


class ProblemType(IntFlag):
    """Types of physical problems."""

    Unset = auto()
    MecaStat = auto()
    MecaDyna = auto()
    Thermal = auto()
    AllMechanics = MecaStat | MecaDyna


class DispatcherMixin:
    """Mixin class that provides a factory depending on the type of physical problem."""

    @classmethod
    def factory(cls, context):
        """Factory that creates the appropriate object.

        Args:
            context (Context): Context of the problem.

        Returns:
            instance: A new object of the relevant type.
        """
        for kls in cls.__subclasses__():
            logger.debug("candidate for '%s': %s / %s", context.problem_type, kls, isabstract(kls))
            if kls.problem_type == context.problem_type:
                if isabstract(kls):
                    return kls.factory(context)
                return kls.builder(context)
        raise TypeError(f"no candidate for cls={cls}, type: {context.problem_type}")


class Observer(ABC):
    """The Observer interface declares the `notify` method, used by events."""

    @abstractmethod
    def notify(self, event):
        """Receive notification from event.

        Arguments:
            event (EventSource): Object that sends the notification.
        """
        # calls event.get_state()


# Could more general: "EntityId"
class EventId(IntFlag):
    """Identifiers of EventSource objects."""

    IterationSolver = auto()
    TimeStepper = auto()
    NonLinearOperator = auto()


class EventSource(ABC):
    """The EventSource interface declares a set of methods for managing observers."""

    # for no_new_attributes
    _observers = _eventid = None

    def __init__(self) -> None:
        super().__init__()
        self._observers = []

    @property
    def eid(self):
        """EventId: Attribute that holds the id of the event."""
        return self._eventid

    def add_observer(self, observer):
        """Attach an observer to the event.

        Arguments:
            observer (Observer): Observer object to be added.
        """
        self._observers.append(observer)

    def remove_observer(self, observer):
        """Detach an observer from the event.

        Arguments:
            observer (Observer): Observer object to be removed.
        """
        self._observers.remove(observer)

    def notifyObservers(self):
        """Notify all observers about an event."""
        for obs in self._observers:
            obs.notify(self)

    @abstractmethod
    def get_state(self):
        """Returns the current state to be shared with observers."""
