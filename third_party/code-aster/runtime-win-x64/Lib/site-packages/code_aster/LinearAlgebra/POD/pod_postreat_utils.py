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
import numpy as np
import scipy
from ...Utilities import PETSc, MPI
from .pod_analysis_base import TOL_NUM

# POST-TREATMENT FUNCTIONNALITIES


def computeProjectionErrors(Phi, snapshots):
    """Compute the projection errors on snaphots knowing a reduced order basis

    Arguments:
        Phi (numpy.ndarray | PETSc.Mat): Reduced order basis.
        snapshots (numpy.ndarray | PETSc.Mat): Snapshot array. Each column contains a given snapshot (size = number of dofs * number of snapshots).

    .. warning::
    Phi and snapshots should have the same type. If not, a TypeError will be raised.

    Returns:
        abs_errors_arr (numpy.ndarray): Array of absolute projection error
        rel_errors_arr (numpy.ndarray): Array of relative projection error
    """
    abs_errors_arr = []
    rel_errors_arr = []

    if isinstance(Phi, np.ndarray) and isinstance(snapshots, np.ndarray):
        for i in range(snapshots.shape[1]):
            u = snapshots[:, i]
            ## - Projection and reconstruction
            u_proj = Phi @ (Phi.T @ u)
            ## - Compute errors
            norm_u = np.linalg.norm(u)
            abs_error = np.subtract(u, u_proj)

            if norm_u > TOL_NUM:
                rel_error = np.linalg.norm(abs_error) / norm_u
            else:
                rel_error = 0.0

            abs_errors_arr.append(np.linalg.norm(abs_error))
            rel_errors_arr.append(rel_error)

        return np.array(abs_errors_arr), np.array(rel_errors_arr)
    elif isinstance(Phi, PETSc.Mat) and isinstance(snapshots, PETSc.Mat):
        n_dim, n_snapshots = snapshots.getSize()
        u_vec = Phi.createVecLeft()
        u_proj_vec = Phi.createVecLeft()
        abs_error_vec = Phi.createVecLeft()
        projected_coords_vec = Phi.createVecRight()

        for i in range(n_snapshots):
            snapshots.getColumnVector(i, u_vec)
            Phi.multTranspose(u_vec, projected_coords_vec)
            Phi.mult(projected_coords_vec, u_proj_vec)
            u_vec.copy(result=abs_error_vec)
            abs_error_vec.axpy(-1.0, u_proj_vec)

            norm_u = u_vec.norm(PETSc.NormType.NORM_2)
            abs_error = abs_error_vec.norm(PETSc.NormType.NORM_2)

            if norm_u > TOL_NUM:
                rel_error = abs_error / norm_u
            else:
                rel_error = 0.0
            abs_errors_arr.append(abs_error)
            rel_errors_arr.append(rel_error)
        return np.array(abs_errors_arr), np.array(rel_errors_arr)
    else:
        raise TypeError(
            f"Unsupported type for Phi and snapshots (same type for both is expected). "
            "Only numpy.ndarray and PETSc.Mat are supported."
        )


def is_orthonormal_basis(matrix, corrOp):
    """Checks if the columns of a given matrix form an orthonormal basis.
    The function is dispatched based on the matrix type and works for both
    dense numpy arrays and distributed PETSc matrices in parallel.

    Arguments:
        matrix (numpy.ndarray | PETSc.Mat): The matrix whose columns are to be checked.
        corrOp (numpy.ndarray | scipy.sparse.spmatrix | PETSc.Mat): The correlation operator defining the inner product

    Returns:
        bool: True if the columns form an orthonormal basis within the given
        tolerance, False otherwise.

    Raises:
        TypeError: If the input matrix is not a supported type.
    """
    tol = TOL_NUM
    if isinstance(matrix, np.ndarray):
        if isinstance(corrOp, (np.ndarray, scipy.sparse.csr_matrix)):
            return _is_orthonormal_numpy(matrix, corrOp, tol)
        else:
            raise TypeError(
                f"With a numpy `matrix`, `corrOp` must be numpy or scipy sparse, "
                f"not {type(corrOp).__name__}."
            )
    elif isinstance(matrix, PETSc.Mat):
        if isinstance(corrOp, PETSc.Mat):
            return _is_orthonormal_petsc(matrix, corrOp, tol)
        else:
            raise TypeError(
                f"With a PETSc `matrix`, `corrOp` must also be PETSc.Mat, "
                f"not {type(corrOp).__name__}."
            )
    else:
        raise TypeError(
            f"Unsupported type for `matrix`: {type(matrix).__name__}. "
            "Only numpy.ndarray and PETSc.Mat are supported."
        )


def _is_orthonormal_numpy(matrix, corrOp, tol):
    """numpy/scipy implementation for checking orthonormality.

    Arguments:
        matrix (numpy.ndarray): The basis matrix, with vectors as columns.
        corrOp (numpy.ndarray | scipy.sparse.csr_matrix): The correlation operator for the inner product.
        tol (float): The absolute tolerance for the numerical comparison.

    Returns:
        bool: True if the basis is orthonormal, False otherwise.
    """
    n_cols = matrix.shape[1]
    if n_cols == 0:
        return True

    identity_check = matrix.T @ corrOp @ matrix

    identity = np.identity(n_cols)
    return np.allclose(identity_check, identity, atol=tol, rtol=0)


def _is_orthonormal_petsc(matrix, corrOp, tol):
    """PETSc implementation for checking orthonormality.

    Arguments:
        matrix (PETSc.Mat): The basis matrix, with vectors as columns.
        corrOp (PETSc.Mat): The correlation operator for the inner product.
        tol (float): The absolute tolerance for the numerical comparison.

    Returns:
        bool: True if the basis is orthonormal, False otherwise.
    """
    comm = matrix.getComm()
    n_cols = matrix.getSize()[1]

    if n_cols == 0:
        return True

    ## - Create temporary vectors
    qi = matrix.createVecLeft()
    qj = matrix.createVecLeft()
    temp_vec = corrOp.createVecLeft()
    ## - Double loop
    is_orthonormal_local = True
    for i in range(n_cols):
        matrix.getColumnVector(i, qi)

        for j in range(i, n_cols):
            matrix.getColumnVector(j, qj)

            corrOp.mult(qj, temp_vec)
            dot_product = qi.dot(temp_vec)

            ## - Check the value
            target = 1.0 if i == j else 0.0
            if abs(dot_product - target) > tol:
                is_orthonormal_local = False
                break

        if not is_orthonormal_local:
            break
    ## - Synchronization
    mpi_comm = comm.tompi4py()
    global_is_orthonormal = mpi_comm.allreduce(is_orthonormal_local, op=MPI.LAND)
    return global_is_orthonormal
