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
from contextlib import AbstractContextManager
import copy
from collections import Counter
from itertools import chain
from typing import Dict, List, Set, Tuple

import numpy as np

# petsc4py.init(['-info '])
try:
    from ..Utilities import PETSc
except ImportError:
    print("Error while importing petsc4py in MatrixScaler")
    assert False

from ..Objects import (
    AssemblyMatrixDisplacementReal,
    AssemblyMatrixTemperatureReal,
    FieldOnNodesReal,
)
from ..Utilities import logger
from ..Supervis import AsterError


def _busymscalinf(A, niter, atol):
    """
    Compute the scaling of the matrix to have all rows and cols in
    the scaled matrix As to have inf-norm equal to 1
    Arguments:
        A (petsc matrix) : the matrix to scale
        niter (int) : max number of iteration
        atol (float) : convergence tolerance
    Returns:
        As (petsc matrix) : the scaled matrix
        Dl (petsc vector) : the left scaling vector
        Dr (petsc vector) : the right scaling vector

    References: A symmetry preserving algorithm for matrix scaling
                Daniel Ruiz and Bora Ucar
                http://perso.ens-lyon.fr/bora.ucar/codes.html
    """

    # the scaled matrix
    As = A.duplicate(copy=True)
    # the scaling vectors
    Dl = As.getVecLeft()
    Dl.set(1.0)
    Dr = As.getVecRight()
    Dr.set(1.0)
    # auxilliary vecs to store the square of Dr, Dl
    Dr_2 = Dr.duplicate()
    Dl_2 = Dl.duplicate()
    # auxilliary vecs to store the scaling to return
    DDr = Dr.duplicate()
    DDr.set(1.0)
    DDl = Dl.duplicate()
    DDl.set(1.0)

    # usefull func to evaluate convergence
    def _isConverged(Dr, Dl, atol, Dr_2, Dl_2):
        Dr_2.pointwiseMult(Dr, Dr)
        Dl_2.pointwiseMult(Dl, Dl)
        Dr_2 = Dr_2 - 1.0
        Dl_2 = Dl_2 - 1.0
        Dr_2.abs()
        Dl_2.abs()
        ErrR = Dr_2.max()[-1]
        ErrL = Dl_2.max()[-1]
        Err = max(ErrR, ErrL)
        return Err < atol

    itrn = 0
    nrow, _ = As.getSize()
    while not _isConverged(Dr, Dl, atol, Dr_2, Dl_2) and itrn < niter or itrn == 0:
        # inverse pointwise
        Dl.reciprocal()
        Dr.reciprocal()

        As.diagonalScale(Dl, Dr)

        As.transpose()
        for i in range(nrow):
            Dr[i] = np.sqrt(np.max(np.abs(As.getRow(i)[-1])))
        As.transpose()  # switch back
        for i in range(nrow):
            Dl[i] = np.sqrt(np.max(np.abs(As.getRow(i)[-1])))

        DDr.pointwiseMult(DDr, Dr)
        DDl.pointwiseMult(DDl, Dl)

        itrn += 1
    DDl.reciprocal()
    DDr.reciprocal()

    return As, DDl, DDr


class mScaler(ABC):
    def __init__(self, scaling_type) -> None:
        "Initialization of mScaler"
        self.scaling_type = scaling_type
        self.lvect = None
        self.rvect = None

    @classmethod
    def factory(cls, scaling_type):
        if scaling_type:
            return MatrixScaler()
        else:
            return NoScaler()

    @abstractmethod
    def computeScaling(self, matrix, merge_dof, verbose):
        pass

    @abstractmethod
    def scaleMatrix(self, matrix: AssemblyMatrixDisplacementReal or AssemblyMatrixTemperatureReal):
        pass

    @abstractmethod
    def scaleRHS(self, rhs: FieldOnNodesReal):
        pass

    @abstractmethod
    def unscaleSolution(self, sol: FieldOnNodesReal):
        pass

    @abstractmethod
    def getScalingVectors(self):
        pass


class NoScaler(mScaler):
    def __init__(self):
        "Initialization of NoScaler"
        super().__init__("NoScaler")

    def computeScaling(self, matrix, merge_dof, verbose):
        lsize = matrix.size(local=True)[0]
        lvect = np.ones(lsize)
        rvect = np.ones(lsize)
        self.lvect = lvect
        self.rvect = rvect

    def scaleMatrix(self, matrix: AssemblyMatrixDisplacementReal or AssemblyMatrixTemperatureReal):
        """Scale the matrix in argument using the previously computed scaling vectors
        (from initial to normalized)."""
        return matrix

    def scaleRHS(self, rhs: FieldOnNodesReal):
        """Scale the rhs in argument using the previously computed scaling vectors
        (from initial to normalized)."""
        return rhs

    def unscaleSolution(self, sol: FieldOnNodesReal):
        """Unscale the solution in argument using the previously computed scaling vectors
        (from normalized to initial)."""
        return sol

    def getScalingVectors(self):
        """Return the left and right scaling vectors (in this order)."""
        return self.lvect, self.rvect


class MatrixScaler(mScaler):
    """Helper object to scale matrices or vectors according to [1].
    The scaling is computed and applied by groups of components aka for a
    thermo-hydro-mechanical problem, all displacement dofs are scaled by the same
    value ; the same for the temperature and pressure dofs. This way, the nature of
    the underlying pde is preserved.

    [1] A symmetry preserving algorithm for matrix scaling
            Daniel Ruiz and Bora Ucar
            http://perso.ens-lyon.fr/bora.ucar/codes.html"""

    def __init__(self):
        "Initialization of MatrixScaler"
        super().__init__("MatrixScaler")

    def computeScaling(
        self,
        matrix: AssemblyMatrixDisplacementReal or AssemblyMatrixTemperatureReal,
        merge_dof,
        verbose=False,
    ):
        """Compute and store the entries of the right and left scaling vectors.

        Arguments:
        matrix [AssemblyMatrix] : the matrix providing the dofs and the reference values
        merge_dof [str] : the dofs that will be considered together
        """
        nmbrg = matrix.getDOFNumbering()
        pA = matrix.toPetsc()

        dof2row = nmbrg.getDictComponentsToDOFs(local=False)

        # Helper function to merge some dof if needed
        def merge_keys(data: Dict[str, Set[int]], *merge_list: List[Tuple[str, str]]):
            """return dict with keys and values merged according to the merge_list
            >>> d={'1':[0,1], '2':[0,1,2], '3':[0,1,3]}
            >>> merge_keys(d, '1', '2', '5')
            {'1+2': [0, 1, 0, 1, 2], '3': [0, 1, 3]}"""
            merged_data = {}
            merge_list = [dof for dof in merge_list if dof in data.keys()]
            in_list = list(
                chain(*map(lambda k: list(data.get(k, {})) if k in merge_list else [], data))
            )
            merged_data["+".join(merge_list)] = in_list
            not_merged_data = {k: data[k] for k in data if k not in merge_list}
            ret = {**merged_data, **not_merged_data}
            ret_clean = {k: v for k, v in ret.items() if v}
            return ret_clean

        # Merge some dof to treat them as a single block
        merged_dof = copy.deepcopy(dof2row)
        for dof in merge_dof:
            merged_dof = merge_keys(merged_dof, *dof)
        ndof = len(merged_dof.keys())
        if logger.level or verbose:
            print(
                f"<{self.__class__.__name__}> Considering the components {list(merged_dof.keys())}",
                flush=True,
            )

        # Create matrix that contains the norm of the block of dof
        norm_mat = PETSc.Mat().create(comm=PETSc.COMM_SELF)
        norm_mat.setType(PETSc.Mat.Type.SEQDENSE)
        norm_mat.setSizes(ndof, ndof)
        norm_mat.setUp()
        # Dict giving the dofs associated to row of the norm_mat
        norm_dof2row = {
            sdof: row for row, (dof, _) in enumerate(merged_dof.items()) for sdof in dof.split("+")
        }
        for row, (_, val_row) in enumerate(merged_dof.items()):
            indx_row = PETSc.IS().createGeneral(val_row)
            for col, (_, val_col) in enumerate(merged_dof.items()):
                indx_col = PETSc.IS().createGeneral(val_col)
                nrm = pA.createSubMatrix(indx_row, indx_col).norm()
                norm_mat.setValue(row, col, nrm)

        norm_mat.assemble()
        if logger.level or verbose:
            print(
                f"<{self.__class__.__name__}> Initial norm matrix of considered "
                + f"components \n{norm_mat.getValues(range(ndof), range(ndof))}",
                flush=True,
            )

        norm_mat_scaled, nmat_lvect, nmat_rvect = _busymscalinf(norm_mat, 100, 1.0e-6)
        if logger.level or verbose:
            print(
                f"<{self.__class__.__name__}> Scaled norm matrix of considered "
                + f"components \n{norm_mat_scaled.getValues(range(ndof), range(ndof))}",
                flush=True,
            )

        # the scaling vectors - they have the same shape as the local matrix
        lsize = matrix.size(local=True)[0]
        lvect = np.zeros(lsize)
        rvect = np.zeros(lsize)
        for row in range(lsize):
            dof = nmbrg.getComponentFromDOF(row, local=True)
            lvect[row] = nmat_lvect[norm_dof2row[dof]]
            rvect[row] = nmat_rvect[norm_dof2row[dof]]
        # We do *not* scale the dof that have Dirichlet BC
        # TODO fix the dirty hack after solution of issue32296
        has_DirichletBC = False
        try:
            has_DirichletBC = any(matrix.getDirichletBCDOFs())
        except AsterError:
            pass
        if has_DirichletBC:
            lvect[np.where(np.array(matrix.getDirichletBCDOFs()) == 1)] = 1.0
            rvect[np.where(np.array(matrix.getDirichletBCDOFs()) == 1)] = 1.0

        self.lvect = lvect
        self.rvect = rvect

    def scaleMatrix(self, matrix: AssemblyMatrixDisplacementReal or AssemblyMatrixTemperatureReal):
        """Scale the matrix in argument using the previously computed scaling vectors
        (from initial to normalized)."""
        if self.rvect is None or self.lvect is None:
            raise ValueError("The scaling must be computed before using it")
        return matrix.scale(self.lvect, self.rvect)

    def scaleRHS(self, rhs: FieldOnNodesReal):
        """Scale the rhs in argument using the previously computed scaling vectors
        (from initial to normalized)."""
        if self.rvect is None or self.lvect is None:
            raise ValueError("The scaling must be computed before using it")
        return rhs.scale(self.lvect)

    def unscaleSolution(self, sol: FieldOnNodesReal):
        """Unscale the solution in argument using the previously computed scaling vectors
        (from normalized to initial)."""
        if self.rvect is None or self.lvect is None:
            raise ValueError("The scaling must be computed before using it")
        return sol.scale(self.rvect)

    def getScalingVectors(self):
        """Return the left and right scaling vectors (in this order)."""
        return self.lvect, self.rvect


class matrixScaler(AbstractContextManager):
    def __init__(self, matrix, rhs, merge_dof=None, scaling_type=False, verbose=False):
        self._scaling = mScaler.factory(scaling_type)
        self._matrix = matrix
        self._rhs = rhs
        self._merge_dof = merge_dof or [["DX", "DY", "DZ"], ["DRX", "DRY", "DRZ"]]
        self._verbose = verbose

    def __enter__(self):
        self._scaling.computeScaling(self._matrix, merge_dof=self._merge_dof, verbose=self._verbose)
        self._scaling.scaleMatrix(self._matrix)
        self._scaling.scaleRHS(self._rhs)
        return self._scaling

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
