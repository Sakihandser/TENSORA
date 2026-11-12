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
Definition of object that stores the parameters of a coupled simulation
between code_saturne and code_aster.
"""

import numpy as np

from ..Solvers import TimeStepper
from ..Utilities import no_new_attributes


class SchemeParams:
    """Object thats holds the values of the parameters of the scheme."""

    epsilon = nb_iter = stepper = adapt_step = None

    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self):
        self.epsilon = 1.0e-6
        self.nb_iter = 1
        self.stepper = None
        self.adapt_step = False

    @staticmethod
    def _get_value(args, param, default=None):

        if param in args:
            return args[param]

        return default

    def set_values(self, kwargs):
        """Set values from keyword arguments.

        Arguments:
            kwargs (dict): Dict of parameters values.
        """

        self.epsilon = self._get_value(kwargs, "epsilon", self.epsilon)
        self.nb_iter = self._get_value(kwargs, "nb_iter", self.nb_iter)

        init_time = self._get_value(kwargs, "init_time")
        nb_step = self._get_value(kwargs, "nb_step")
        final_time = self._get_value(kwargs, "final_time")
        delta_t = self._get_value(kwargs, "delta_t")
        time_list = self._get_value(kwargs, "time_list")

        if time_list or nb_step or final_time or delta_t:
            if time_list is None:
                assert init_time is not None
                if final_time is None:
                    assert delta_t is not None
                    final_time = init_time + nb_step * delta_t

                if nb_step is None:
                    assert final_time is not None
                    nb_step = int((final_time - init_time) / delta_t)

                time_list = np.linspace(init_time, final_time, nb_step + 1, endpoint=True)

            self.stepper = TimeStepper(time_list, initial=time_list[0])

        if final_time:
            self.final_time = final_time
        if init_time:
            self.init_time = init_time

    @property
    def init_time(self):
        """float: Initial time value."""
        return self.stepper.getInitial()

    @init_time.setter
    def init_time(self, time):
        """Define the initial time. Lesser values are removed.

        Arguments:
            time (float): First time to be used.
        """
        self.stepper.setInitial(time)

    @property
    def final_time(self):
        """float: Final time value."""
        return self.stepper.getFinal()

    @final_time.setter
    def final_time(self, time):
        """imit the sequence to the times lower than `time`.

        Arguments:
            time (float): Last time to be used.
        """
        self.stepper.setFinal(time)

    @property
    def delta_t(self):
        """float: delta time value."""
        return self.stepper.getIncrement()
