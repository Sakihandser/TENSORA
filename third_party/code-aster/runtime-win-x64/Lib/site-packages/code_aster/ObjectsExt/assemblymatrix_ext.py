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
:py:class:`AssemblyMatrixDisplacementReal` --- Assembly matrix
****************************************************
"""

import numpy as NP
from libaster import (
    AssemblyMatrixDisplacementComplex,
    AssemblyMatrixDisplacementReal,
    AssemblyMatrixEliminatedReal,
    AssemblyMatrixPressureComplex,
    AssemblyMatrixPressureReal,
    AssemblyMatrixTemperatureComplex,
    AssemblyMatrixTemperatureReal,
    assemblyMatrixToPetsc,
)

from ..Objects.Serialization import InternalStateBuilder
from ..Utilities import PETSc, injector, profile


class AssemblyMatrixStateBuilder(InternalStateBuilder):
    """Class that returns the internal state of a *AssemblyMatrix* to be pickled."""

    def save(self, matrix):
        """Return the internal state of a *AssemblyMatrix* to be pickled.

        Arguments:
            matrix (*AssemblyMatrix*): The *AssemblyMatrix* object to be pickled.

        Returns:
            *InternalStateBuilder*: The internal state itself.
        """
        super().save(matrix)
        self._st["numbering"] = matrix.getDOFNumbering()
        return self

    def restore(self, matrix):
        """Restore the *AssemblyMatrix* content from the previously saved internal
        state.

        Arguments:
            matrix (*AssemblyMatrix*): The *DataStructure* object to be restored.
        """
        super().restore(matrix)
        matrix.setDOFNumbering(self._st["numbering"])


class BaseAssemblyMatrix:
    """Base object for AssemblyMatrix."""

    cata_sdj = "SD.sd_matr_asse.sd_matr_asse"
    internalStateBuilder = AssemblyMatrixStateBuilder

    def toPetsc(self, local=False):
        """Convert the matrix to a PETSc matrix object.

        Arguments:
            local (bool): extract only the sequential matrix of the subdomain or the global parallel matrix (default False)

        Returns:
            PetscMat: PETSc matrix.
        """

        if isinstance(
            self,
            (
                AssemblyMatrixDisplacementReal,
                AssemblyMatrixTemperatureReal,
                AssemblyMatrixEliminatedReal,
            ),
        ):
            return assemblyMatrixToPetsc(self, local)
        raise NotImplementedError("Type not supported by Petsc")

    def toNumpy(self):
        """Returns the matrix values as `numpy.array`.

        Returns:
            numpy.array: A simple `numpy.array` of the dense matrix.
        """

        nu = self.getDOFNumbering()

        smos = nu.getMorseStorage()
        smhc = smos.getDiagonalPositions()
        smdi = smos.getRows()
        ccid = self.getDirichletBCDOFs()[:-1]  # suppress last entry containing number of bc
        sym = self.isSymmetric()
        dim = len(smdi)
        nnz = len(smhc)
        triang_sup = NP.array(self.getUpperValues())
        if sym:
            triang_inf = triang_sup
        else:
            triang_inf = NP.array(self.getLowerValues())

        if isinstance(
            self,
            (
                AssemblyMatrixDisplacementReal,
                AssemblyMatrixTemperatureReal,
                AssemblyMatrixPressureReal,
                AssemblyMatrixEliminatedReal,
            ),
        ):
            dtype = float
        else:
            dtype = complex

        data = NP.zeros([dim, dim], dtype=dtype)
        jcol = 0
        for kterm in range(nnz):
            ilig = smhc[kterm] - 1
            if smdi[jcol] < kterm + 1:
                jcol += 1
            data[jcol, ilig] = triang_inf[kterm]
            data[ilig, jcol] = triang_sup[kterm]
        # apply kinematic boundary conditions
        if ccid:
            elim = NP.where(NP.array(ccid) == 1)
            data[elim, :] = 0.0
            data[:, elim] = 0.0
            data[elim, elim] = 1.0
        return data

    def getValuesWithDescription(self, epsilon=None):
        """Returns the values of the matrix.

        To create a 'scipy.sparse' matrix use the following code:
            'scipy.sparse.coo_matrix((val, (rows, cols)), shape=(dim, dim))'

        Arguments:
            epsilon (float): Terms less than this value is considered null.
                By default, no filtering is done.

        Returns:
            tuple `(val, rows, cols, dim)`: `val`
            contains the values, `rows` the rows indices, `cols` the columns
            indices and `dim` the number of terms.
        """

        nu = self.getDOFNumbering()

        smos = nu.getMorseStorage()
        smhc = smos.getDiagonalPositions()
        smdi = smos.getRows()
        ccid = self.getDirichletBCDOFs()[:-1]  # suppress last entry containing number of bc
        sym = self.isSymmetric()
        dim = len(smdi)
        nnz = len(smhc)
        triang_sup = NP.array(self.getUpperValues())
        if sym:
            triang_inf = triang_sup
        else:
            triang_inf = NP.array(self.getLowerValues())

        if isinstance(
            self,
            (
                AssemblyMatrixDisplacementReal,
                AssemblyMatrixTemperatureReal,
                AssemblyMatrixPressureReal,
                AssemblyMatrixEliminatedReal,
            ),
        ):
            dtype = float
        else:
            dtype = complex

        rows = NP.array(smhc) - 1
        diag = NP.array(smdi) - 1

        # generate the columns indices
        cols = NP.zeros(nnz, dtype=int)
        jcol = 0
        for i in range(1, nnz):
            if i > diag[jcol]:
                jcol += 1
            cols[i] = jcol

        # diag is where "row == col"
        helper = rows - cols
        diag_indices = NP.where(helper == 0)[0]

        # transpose indices in 'inf' part and remove diagonal terms
        cols_inf = NP.delete(rows, diag_indices)
        rows_inf = NP.delete(cols, diag_indices)
        triang_inf = NP.delete(triang_inf, diag_indices)

        # join 'sup' and 'inf' parts
        rows = NP.concatenate((rows, rows_inf))
        cols = NP.concatenate((cols, cols_inf))
        data = NP.concatenate((triang_sup, triang_inf))

        # filter terms
        if epsilon is not None:
            nulls = NP.where(abs(data) < epsilon)
            rows = NP.delete(rows, nulls)
            cols = NP.delete(cols, nulls)
            data = NP.delete(data, nulls)

        # apply kinematic boundary conditions
        if ccid:
            elim = NP.where(NP.array(ccid) == 1)[0]
            keep = NP.isin(rows, elim, invert=True) & NP.isin(cols, elim, invert=True)
            data = data[keep]
            rows = rows[keep]
            cols = cols[keep]
            rows = NP.concatenate((elim, rows))
            cols = NP.concatenate((elim, cols))
            data = NP.concatenate((NP.ones(len(elim)), data))
        return data, rows, cols, dim

    def norm(self, norm_type):
        """Compute various norm as

        Arguments:
            norm_type (str) : type between 'NORM_1', 'NORM_FROBENIUS', 'NORM_INFINITY'

        Returns:
            float: norm of the matrix
        """

        conv = {
            "NORM_1": PETSc.NormType.NORM_1,
            "NORM_FROBENIUS": PETSc.NormType.NORM_FROBENIUS,
            "NORM_INFINITY": PETSc.NormType.NORM_INFINITY,
        }

        return self.toPetsc().norm(conv[norm_type])


class BaseAssemblyMatrixReal(BaseAssemblyMatrix):
    """Base object for real AssemblyMatrix."""


class BaseAssemblyMatrixComplex(BaseAssemblyMatrix):
    """Base object for complex AssemblyMatrix."""


@injector(AssemblyMatrixDisplacementReal)
class ExtendedAssemblyMatrixDisplacementReal(BaseAssemblyMatrixReal):
    # add profile to theses methods
    assemble = profile(AssemblyMatrixDisplacementReal.assemble)


@injector(AssemblyMatrixEliminatedReal)
class ExtendedAssemblyMatrixEliminatedReal(BaseAssemblyMatrixReal):
    # add profile to theses methods
    assemble = profile(AssemblyMatrixEliminatedReal.assemble)


@injector(AssemblyMatrixDisplacementComplex)
class ExtendedAssemblyMatrixDisplacementComplex(BaseAssemblyMatrixComplex):
    # add profile to theses methods
    assemble = profile(AssemblyMatrixDisplacementComplex.assemble)


@injector(AssemblyMatrixTemperatureReal)
class ExtendedAssemblyMatrixTemperatureReal(BaseAssemblyMatrixReal):
    # add profile to theses methods
    assemble = profile(AssemblyMatrixTemperatureReal.assemble)


@injector(AssemblyMatrixTemperatureComplex)
class ExtendedAssemblyMatrixTemperatureComplex(BaseAssemblyMatrixComplex):
    # add profile to theses methods
    assemble = profile(AssemblyMatrixTemperatureComplex.assemble)


@injector(AssemblyMatrixPressureReal)
class ExtendedAssemblyMatrixPressureReal(BaseAssemblyMatrixReal):
    # add profile to theses methods
    assemble = profile(AssemblyMatrixPressureReal.assemble)


@injector(AssemblyMatrixPressureComplex)
class ExtendedAssemblyMatrixPressureComplex(BaseAssemblyMatrixComplex):
    # add profile to theses methods
    assemble = profile(AssemblyMatrixPressureComplex.assemble)
