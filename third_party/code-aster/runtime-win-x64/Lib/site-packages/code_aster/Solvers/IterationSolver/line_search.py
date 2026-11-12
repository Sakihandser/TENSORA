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

from abc import ABC, abstractmethod
from enum import IntFlag, auto

import numpy as np

from ...Messages import UTMESS
from ...Utilities import logger, no_new_attributes, profile
from ..Basics import ContextMixin


class LineSearchType(IntFlag):
    """Line Search types."""

    Unset = auto()
    Corde = auto()
    Mixte = auto()
    Pilotage = auto()

    @classmethod
    def by_name(cls, name):
        """Return an option value by its name.
        *AttributeError* is raised if the option does not exist.

        Arguments:
            name (str): Option name.

        Returns:
            int: Option value.
        """
        return getattr(cls, name)


class BaseLineSearch(ABC, ContextMixin):
    """Base for line search methods"""

    __needs__ = ("keywords", "state", "oper")
    linesearch_type = LineSearchType.Unset
    _cached_limits = None
    __setattr__ = no_new_attributes(object.__setattr__)

    @classmethod
    def factory(cls, context):
        """Factory that creates the appropriate object.

        Args:
            context (Context): Context of the problem.

        Returns:
            *BaseLineSearch*: New object.
        """
        method = context.get_keyword("RECH_LINEAIRE", "METHODE", "CORDE").capitalize()
        searched = LineSearchType.by_name(method)
        for kls in cls.__subclasses__():
            if searched in kls.linesearch_type:
                return kls.builder(context)
        raise TypeError(f"no candidate for cls={cls}, method: {method}")

    def __init__(self):
        super().__init__()
        self._cached_limits = None

    def _get(self, keyword=None, default=None):
        return self.get_keyword("RECH_LINEAIRE", keyword, default)

    def isEnabled(self):
        """bool: *True* if LineSearch is activated."""
        return self._get("ITER_LINE_MAXI", 0) > 0

    def compute_f(self, rho, solution, scaling=1.0):
        """Compute functional"""
        self.state.deltaU += rho * solution
        # compute residual
        resi_state = self.oper.getResidual(scaling)
        self.state.deltaU -= rho * solution
        return -resi_state.resi.dot(solution)

    def check_limits(self, rho):
        if self._cached_limits is None:
            self._cached_limits = [self._get(i) for i in ("RHO_MIN", "RHO_MAX", "RHO_EXCL")]
        min, max, excl = self._cached_limits
        if rho < min:
            rho = min
        if rho > max:
            rho = max
        assert rho >= 0.0
        if rho <= excl:
            rho = excl
        return rho

    @abstractmethod
    def solve(self, solution, scaling=1.0):
        """Apply linear search for mechanical problems.

        Arguments:
            solution (FieldOnNodes): Displacement solution.
            scaling (float): Scaling factor for Lagrange multipliers (default: 1.0).

        Returns:
            FieldOnNodes: Accelerated solution by linear search.
        """


class SecantLineSearch(BaseLineSearch):
    """Line search for CORDE & MIXTE methods."""

    linesearch_type = LineSearchType.Corde | LineSearchType.Mixte
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self):
        super().__init__()

    @property
    def _tiny(self):
        return np.finfo("float64").tiny

    def _setup_message(self, best, solution):
        logger.debug(
            "Line-search iteration %d: rho = %.6f, f(rho) = %.6f", best[0], best[1], best[2]
        )
        return best[1] * solution

    def _apply_corde(self, f, f_old, rho_old, rho1):
        denom = f - f_old
        if abs(denom) > self._tiny:
            # Apply method CORDE
            rho1 = (f * rho_old - f_old * rho1) / denom
            rho1 = self.check_limits(rho1)
        elif f * (rho1 - rho_old) * denom <= 0.0:
            rho1 = self._get("RHO_MAX")
        else:
            rho1 = self._get("RHO_MIN")
        return rho1

    def _apply_mixte(self, f, f_old, f0, rho_pos_old, rho_neg_old, rho_old, rho1):
        success = True
        sens = 1.0 if f0 <= 0.0 else -1.0
        # Track sign changes for bisection
        # zbborn
        if np.sign(f) != np.sign(f0):
            rho_pos = rho1
            rho_neg = rho_neg_old
            has_pos = True
        else:
            rho_pos = rho_pos_old
            rho_neg = rho1
            has_pos = False

        if has_pos:
            # Root finding in interval [rho_neg, rho_pos]
            # zbroot
            if abs(f) < abs(f_old):
                # Apply method MIXTE
                if abs(rho1 - rho_old) > self._tiny:
                    rho1 = self._apply_mixte_special_case(f, f_old, rho_neg, rho_pos, rho_old, rho1)
                else:
                    success = False
                    return rho1, rho_pos, rho_neg, success
            else:
                # en cas de non pertinence des iteres : dichotomie
                rho1 = np.mean([rho_neg, rho_pos])
        else:
            # Increase rho aggresively to find sign change
            rho_old = rho1
            rho1 = 3 * rho_old

        # zbproj
        if rho1 < rho_neg:
            if has_pos:
                rho1 = np.mean([rho_neg, rho_pos])
            else:
                success = False
                return rho1, rho_pos, rho_neg, success

        if has_pos and rho1 > rho_pos:
            rho1 = np.mean([rho_neg, rho_pos])

        # zbinte
        rho1 = self.check_limits(rho1)
        return rho1, rho_pos, rho_neg, success

    def _apply_mixte_special_case(self, f, f_old, rho_neg, rho_pos, rho_old, rho1):
        p1 = (f - f_old) / (rho1 - rho_old)
        p0 = f_old - p1 * rho_old
        if abs(p1) <= abs(f_old) / (rho_pos + rho_old):
            rho1 = 0.5 * (rho_neg + rho_pos)
        else:
            rho1 = -p0 / p1
        return rho1

    @profile
    def solve(self, solution, scaling=1.0):
        """Apply linear search for mechanical problems.

        Arguments:
            solution (FieldOnNodes): Displacement solution.
            scaling (float): Scaling factor for Lagrange multipliers (default: 1.0).

        Returns:
            FieldOnNodes: Accelerated solution by linear search.
        """
        if not self.isEnabled():
            return solution

        method = self._get("METHODE")
        assert method in ("CORDE", "MIXTE"), method

        # Initial values
        rho0 = 0.0
        rho1 = 1.0
        f0 = self.compute_f(rho0, solution)
        logger.debug("fonctionnelle initiale %.6f", f0)
        f1 = self.compute_f(rho1, solution)
        tol = 1.0e-12 * self.oper.getResidual().resi.norm() * solution.norm()
        if abs(f0) <= tol and abs(f1) <= tol:
            UTMESS("A", "MECANONLINE5_49")
            return solution
        fcvg = abs(self._get("RESI_LINE_RELA") * f0)

        # Best values and updates during line search
        best_options = (-1, rho1, np.finfo("float64").max)

        # Variables for the methods CORDE and MIXTE
        rho_old = rho0
        f_old = f0
        sens = 1.0

        # Variables only for the method MIXTE
        if method == "MIXTE":
            sens = 1.0 if f0 <= 0.0 else -1.0
            rho_pos = 0.0
            rho_neg = 0.0

        for iteration in range(self._get("ITER_LINE_MAXI") + 1):
            logger.debug("rho courant %.6f", sens * rho1)
            try:
                f = self.compute_f(sens * rho1, solution)
                logger.debug("fonctionnelle courante %.6f", f)
            except Exception:
                # do we already have an rhoopt ?
                if iteration > 0:
                    logger.warning("Exception in compute_f, returning best rho found so far")
                    return best_options[1] * solution
                raise

            # Update best solution if improved
            # zbopti
            if abs(f) <= best_options[2]:
                best_options = (iteration, rho1, abs(f))
                # converged ?
                if abs(f) < fcvg:
                    return self._setup_message(best_options, solution)

            rho_tmp = rho1  # save current rho before update

            if method == "CORDE":
                rho1 = self._apply_corde(f, f_old, rho_old, rho1)

            elif method == "MIXTE":
                output = self._apply_mixte(f, f_old, f0, rho_pos, rho_neg, rho_old, rho1)
                rho1, rho_pos, rho_neg, success = output
                if not success:
                    return self._setup_message(best_options, solution)

            # Update variables for next iteration
            rho_old = rho_tmp
            f_old = f

        return self._setup_message(best_options, solution)
