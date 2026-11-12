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

import numpy as np

import scipy.linalg
import scipy.optimize
from ...Utilities import MPI, no_new_attributes


class NNLSSolver(ABC):
    """
    Abstract Base Class for Non-Negative Least Squares (NNLS) solvers.

    This class defines the common interface that all concrete NNLS solver
    implementations must follow.
    """

    _C = _d = _m = _n = None

    __setattr__ = no_new_attributes(object.__setattr__)

    @classmethod
    def factory(cls, C, d, **kwargs):
        """NNLS solver factory.

        Selects and returns a concrete implementation (`NNLSSolverNumpy` or
        `NNLSSolverNumpy`) based on the inputs `C` and 'd' types.

        Arguments:
            C (numpy.ndarray): The dictionnary matrix.
            d (numpy.ndarray): The second member.
            **kwargs: Arguments passed to the chosen implementation's constructor.

        Returns:
            NNLSSolverNumpy : A concrete NNLSSolver instance.
        """
        klas = None
        for subclass in cls.__subclasses__():
            if subclass.supports(C, d):
                klas = subclass
                break
        if not klas:
            raise TypeError(f"The dictionnary matrix is not supported : {type(C).__name__}")
        return klas(C, d, **kwargs)

    def __init__(self, C, d):
        """Initializes the solver with the problem data.
         The concrete type depends on the subclass

        Arguments:
            C (Any): The system matrix (m x n).
            d (Any): The target vector (m,).
        """

        self._C = C
        self._d = d
        self._validate_dimensions()
        self._m, self._n = self.get_shape()

    @abstractmethod
    def get_shape(self):
        """Returns the dimensions (rows, columns) of the matrix C."""
        pass

    @abstractmethod
    def _validate_dimensions(self):
        """Validates that the dimensions of C and d are compatible."""
        pass

    @abstractmethod
    def _initialize_state(self, P0, tol):
        """Initializes all backend-specific state variables for the solver.

        Arguments:
            P0 (Any): Initial set of indices or mask for non-zero variables.
            tol (float): Tolerance value used for calculating scaled tolerances.

        Returns:
            Tuple: A tuple containing the initialized state variables
                (e.g., x, P, w, wsc, wsc0, threshold_error, residual_history).
        """
        pass

    @abstractmethod
    def _check_stopping_criteria(self, P, x, residual_vec, threshold_error):
        """Checks if the algorithm should terminate.

        Arguments:
            P (Any): The current active set mask or indices.
            x (Any): The current solution vector.
            residual_vec (Any): The current residual vector (if applicable).
            threshold_error (float): The error threshold for stopping.

        Returns:
            bool: True if the stopping criteria are met, False otherwise.
        """
        pass

    @abstractmethod
    def _select_variable_to_add(self, P, w, wsc):
        """Selects the best variable to add to the active set.

        Arguments:
            P (Any): The current active set mask or indices.
            w (Any): The current dual vector (negative gradient).
            wsc (Any): The current scaled tolerance vector.

        Returns:
            int: The index of the variable to add.
        """
        pass

    @abstractmethod
    def _solve_subproblem(self, P):
        """Solves the least-squares subproblem for the active set P.

        Arguments:
            P (Any): The active set mask or indices.

        Returns:
            Tuple[Any, float]: A tuple containing:
                - z (Any): The solution vector for the subproblem.
                - min_val (float): The minimum value of the active variables.
        """
        pass

    @abstractmethod
    def solve(self, P0=None, opts=None):
        """Solves the NNLS problem: minimize ||Cx - d||^2 subject to x >= 0.

        Arguments:
            P0 (Any, optional): Initial active set. Defaults to None.
            opts (dict, optional): Solver options (e.g., tolerance, max iterations).
                Defaults to None.

        Returns:
            Tuple[Any, dict]: A tuple containing:
                - x (Any): The non-negative solution vector.
                - info (dict): Metadata about the execution (iterations, residuals, etc.).
        """
        pass


AVAILABLE_NPSOLVE_OPTION = ["SC_linalg_lstq", "QR_solve"]


class NNLSSolverNumpy(NNLSSolver):
    """
    Concrete NNLS solver using numpy and an active-set algorithm.
    """

    _solve_option = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, C, d):
        """
        Initializes the numpy-based solver.

        Arguments:
            C (np.ndarray): The system matrix.
            d (np.ndarray): The target vector.
            solve_option (str, optional): Method for solving the subproblem.
                - 'SC_linalg_lstq': Uses np.linalg.lstsq.
                - 'QR_solve': Uses QR decomposition.
                Defaults to 'SC_linalg_lstq'.
        """
        self._solve_option = self.set_solve_option("SC_linalg_lstq")
        super().__init__(C, d)

    @classmethod
    def supports(cls, C, d):
        """Tell if these entires are supported.

        Arguments:
            C (Misc): dictionnary matrix to be tested.
            d (Misc): The second member to be tested..

        Returns:
            bool: *True* if *C* and *d* are numpy arrays.
        """
        return isinstance(C, np.ndarray) and isinstance(d, np.ndarray)

    def set_solve_option(self, solve_option):
        """Defines the resolution option for subproblem in active set (NNLS)

        Arguments:
            solve_option (str): Resolution option for subproblem in active set

        Raises:
            ValueError: If the solver option in the subproblem solver is not
                available
        """
        if solve_option not in AVAILABLE_NPSOLVE_OPTION:
            allowed_options = ", ".join(AVAILABLE_NPSOLVE_OPTION)
            raise ValueError(
                f"'{solve_option}' is not a valid option. "
                f"solve_option must be one of: {allowed_options}"
            )
        self._solve_option = solve_option

    def get_shape(self):
        """Returns the shape of the numpy matrix C."""
        return self._C.shape

    def _validate_dimensions(self):
        """Validates dimensions for numpy arrays."""
        if self._C.shape[0] != self._d.shape[0]:
            raise ValueError("Shape mismatch: C and d must have the same number of rows.")

    def _initialize_state(self, P0, tol):
        """
        Initializes all state variables for the numpy solver.

        Arguments:
            P0 (list | np.ndarray | None): Initial set of indices for non-zero variables.
            tol (float): The tolerance value used for calculating scaled tolerances.

        Returns:
            tuple: A tuple containing:
                - x (np.ndarray): The initial solution vector (zeros).
                - P (np.ndarray): The initial boolean active set mask.
                - w (np.ndarray): The initial negative gradient vector.
                - wsc (np.ndarray): The initial scaled tolerance vector.
                - wsc0 (float): The initial norm of the gradient.
                - threshold_error (float): The residual norm stopping criterion.
                - list: An empty list for residual history.
        """
        P = np.zeros(self._n, dtype=bool)
        if P0 is not None:
            P[P0] = True
        x = np.zeros(self._n)
        w = self._C.T @ self._d
        wsc0 = np.linalg.norm(w)
        wsc = wsc0 * tol * np.ones(self._n)
        threshold_error = np.linalg.norm(self._d) * tol
        return x, P, w, wsc, wsc0, threshold_error, []

    def _check_stopping_criteria(self, P, x, residual_vec, threshold_error):
        """
        Checks stopping criteria for the numpy solver.

        Arguments:
            P (np.ndarray): The current active set mask (boolean).
            x (np.ndarray): The current solution vector.
            residual_vec (None): Unused, kept for compatibility (e.g., PETSc).
            threshold_error (float): The target residual norm for early stopping.

        Returns:
            bool: True if a stopping criterion is met, False otherwise.
        """
        if np.all(P):
            return True
        residual_norm = np.linalg.norm(self._C @ x - self._d)
        return residual_norm <= threshold_error

    def _select_variable_to_add(self, P, w, wsc):
        """
        Selects the best variable to add to the active set using numpy.

        Arguments:
            P (np.ndarray): The current active set mask (boolean).
            w (np.ndarray): The current negative gradient vector.
            wsc (np.ndarray): The current scaled tolerance vector.

        Returns:
            int: The index of the best variable to add to the active set.
        """
        inactive_indices = np.where(~P)[0]
        best_new_var_local_idx = np.argmax(w[inactive_indices] - wsc[inactive_indices])
        return inactive_indices[best_new_var_local_idx]

    def _solve_subproblem(self, P):
        """
        Solves the subproblem using numpy/scipy.

        Arguments:
            P (np.ndarray): The active set mask (boolean).

        Returns:
            tuple[np.ndarray, float]: A tuple containing:
                - z (np.ndarray): The solution vector.
                - min_val (float): The minimum value of z on the active set.
        """
        z = np.zeros(self._n)
        C_p = self._C[:, P]
        if C_p.shape[1] == 0:
            return z, 0.0

        if self._solve_option == "SC_linalg_lstq":
            z[P] = np.linalg.lstsq(C_p, self._d, rcond=None)[0]
        else:
            Qp, Rp = scipy.linalg.qr(C_p, mode="economic")
            z[P] = scipy.linalg.solve_triangular(Rp, Qp.T @ self._d)

        min_val = np.min(z[P]) if C_p.shape[1] > 0 else 0.0
        return z, min_val

    def solve(self, P0=None, opts=None):
        """
        Executes the active-set algorithm to solve the NNLS problem.

        Arguments:
            P0 (list | np.ndarray, optional): Initial set of indices for variables
                assumed to be non-zero. Defaults to None.
            opts (dict, optional): Dictionary of solver options:
                - 'Tol' (float): Stopping tolerance based on residual norm.
                - 'Iter' (int): Maximum number of iterations.
                - 'StoreResiduals' (bool): If True, stores residual history.
                Defaults to None.

        Returns:
            tuple[np.ndarray, dict]: A tuple containing:
                - x (np.ndarray): The non-negative solution vector of shape (n,).
                - info (dict): Dictionary with execution details such as
                  'iterations' and 'final_residual_norm'.

        Raises:
            RuntimeError: If the algorithm fails to converge within the maximum
                number of iterations.
        """

        opts = opts if opts is not None else {}
        tol, maxiter, store_residuals = (
            opts.get("Tol", 1e-5),
            opts.get("Iter", 3 * self._n),
            opts.get("StoreResiduals", False),
        )
        x, P, w, wsc, wsc0, threshold_error, residual_history = self._initialize_state(P0, tol)

        iter_count = 0
        new_variable_added = False

        while True:
            if self._check_stopping_criteria(P, x, None, threshold_error):
                break

            best_new_var_idx = self._select_variable_to_add(P, w, wsc)
            P[best_new_var_idx] = True
            new_variable_added = True

            while True:
                iter_count += 1
                if iter_count > maxiter:
                    raise RuntimeError(f"NNLS failed to converge in {maxiter} iterations.")

                z, z_min = self._solve_subproblem(P)

                if z_min >= 0:
                    x = z
                    if store_residuals:
                        residual_history.append(np.linalg.norm(self._C @ x - self._d))
                    w = self._C.T @ (self._d - self._C @ x)
                    wsc[P] = np.maximum(wsc[P], 2 * np.abs(w[P]))
                    break

                negative_z_indices = np.where((z < 0) & P)[0]
                ratios = x[negative_z_indices] / (
                    x[negative_z_indices] - z[negative_z_indices] + np.finfo(float).eps
                )
                alpha = np.min(ratios)

                x = x + alpha * (z - x)
                if store_residuals:
                    residual_history.append(np.linalg.norm(self._C @ x - self._d))

                P[(x <= np.finfo(float).eps) & P] = False
                new_variable_added = False

        info = {
            "iterations": iter_count,
            "final_residual_norm": np.linalg.norm(self._C @ x - self._d),
            "wsc0": wsc0,
        }
        if store_residuals:
            info["residual_history"] = residual_history
        return x, info
