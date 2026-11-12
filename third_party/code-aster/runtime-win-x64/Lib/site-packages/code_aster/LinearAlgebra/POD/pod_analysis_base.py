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
from abc import abstractmethod, ABC
import scipy.sparse
import numpy as np
from ...Utilities import PETSc, SLEPc, MPI, disable_fpe, no_new_attributes

# GENERAL PARAMETERS FOR THE MODULE
TOL_NUM = 1e-9

# CLASS DEFINITION FOR A POD ANALYSIS
POD_METHOD = ["SVD", "snapshot", "GS-classical", "GS-modified"]
POD_METHOD_WITHOUT_CRIT = ["GS-classical", "GS-modified"]
assert all(item in POD_METHOD for item in POD_METHOD_WITHOUT_CRIT)
POD_CRITERION_METHOD = ["energy", "nbModes"]
INCR_POD_METHOD = ["HPOD", "HAPOD"]
GS_METHOD = ["classical", "modified"]
OPTION_POD_VALUES = [1, 2]


class PODAnalysis(ABC):
    """
    Abstract class for building a base incrementally using POD.

    This class is designed to build a base from a set of snapshots.

    Attributes:
    _snapshots : Any
        Matrix of snapshots.
    _numberOfDOFs : int | None
        Number of degrees of freedom of the problem.
    _numberOfSnapshots : int | None
        Number of snapshots.
    _corrOperator : PETSc.Mat | None
        Correlation operator.
    _methodCompress : str | None
        Method used to compress the data (e.g., 'svd').
    _criterionModes : str | None
        Method used to choose the number of modes (e.g., 'tolerance').
    _crit_tolerance : float | None
        Tolerance for the POD basis construction.
    _crit_nbModes : int | None
        Fixed number of modes for the POD basis construction.
    _tol_num : float | None
        Numerical tolerance for various computations.
    """

    _methodCompress = _criterionModes = None
    _crit_tolerance = _crit_nbModes = _tol_num = None
    _snapshots = _numberOfDOFs = _numberOfSnapshots = _corrOperator = None
    __setattr__ = no_new_attributes(object.__setattr__)

    @classmethod
    def factory(cls, snapshots, **kwargs):
        """POD analysis factory.

        Selects and returns a concrete implementation (`PODAnalysisNumpy` or
        `PODAnalysisPetsc`) based on the input `snapshots` type.

        Arguments:
            snapshots (numpy.ndarray | PETSc.Mat): The snapshot matrix.
            **kwargs: Arguments passed to the chosen implementation's constructor.

        Returns:
            PODAnalysisNumpy | PODAnalysisPetsc: A concrete POD analysis instance.
        """
        klas = None
        for subclass in cls.__subclasses__():
            if subclass.supports(snapshots):
                klas = subclass
                break
        if not klas:
            raise TypeError(f"The snapshot type is not supported : {type(snapshots).__name__}")
        return klas(snapshots, **kwargs)

    def __init__(
        self, snapshots, method="SVD", criterion="energy", tolerance=None, nbModes=None, corrOp=None
    ):
        """Initialize the instance for Proper Orthogonal Decomposition (POD) analysis.

        This method configures the instance by setting the data (snapshots),
        the decomposition hyperparameters, and preparing the operators
        required for the analysis.

        Arguments:
            snapshots (Matrix): Matrix of snapshots, where each column represents a system snapshot (e.g., numpy.ndarray, PETSc.Mat).
            method (str, optional): Compression method to be used for the decomposition. By default, "SVD".
            criterion (str, optional): Criterion to determine the number of modes to retain. Options: 'energy', 'nbModes'. By default, "energy".
            tolerance (float, optional): Tolerance threshold for the 'energy' criterion, defining the cumulative energy to be preserved.
                Required if `criterion` is 'energy'.
            nbModes (int, optional): Fixed number of modes to retain. Required if `criterion` is 'nbModes'.
            corrOp (Matrix | None, optional): Correlation operator (e.g., mass matrix) for the inner product.
                If `None`, the Euclidean inner product is used. By default, `None`.
        """
        self._snapshots = snapshots  # Each column is a snapshot
        ## - Initialisation parameters
        self._methodCompress = None
        self._criterionModes = None
        self._crit_tolerance = tolerance
        self._crit_nbModes = nbModes
        self._tol_num = TOL_NUM
        self._numberOfDOFs = None
        self._numberOfSnapshots = None
        self._corrOperator = None
        ## - Prepare the operators for POD Analysis
        self.setInfosSnapshots()
        self.setCompressionMethod(method)
        self.setCorrelationOperator(corrOperator=corrOp)
        self.setCriterionModes(criterion)
        ## - Tests
        self.correctionSnapshots()
        self.validateMethodAttrs()
        self.validateHyperParametersAttrs()
        self.validateMethodState()
        self.runCompatibilityTests()
        assert self._methodCompress is not None
        assert self._criterionModes is not None

    @classmethod
    @abstractmethod
    def supports(cls, snapshots):
        """Tell if these snapshots are supported.

        Args:
            snapshots (Misc): snapshots to be tested.

        Returns:
            bool: supported or not.
        """

    def validateMethodAttrs(self):
        """Check the attributes associated to the numerical method (compression method and mode selection criterion)."""
        if self._methodCompress not in POD_METHOD:
            raise ValueError(
                f"PODAnalysis: method '{self._methodCompress}' is not valid. Choose method in {POD_METHOD}."
            )
        if self._criterionModes not in POD_CRITERION_METHOD:
            raise ValueError(
                f"PODAnalysis: criterion '{self._criterionModes}' is not valid. Choose method in {self._criterionModes}."
            )

    def validateHyperParametersAttrs(self):
        """Check the attributes associated to the numerical hyperparameters (tolerances, etc)"""
        if self._crit_tolerance is not None and (
            not isinstance(self._crit_tolerance, float) or self._crit_tolerance <= 0
        ):
            raise TypeError(
                "Tolerance for basis construction (tolerance) should be a float and positive"
            )
        if self._crit_nbModes is not None and (
            not isinstance(self._crit_nbModes, int) or self._crit_nbModes <= 0
        ):
            raise TypeError(
                "Number of modes for basis construction (nbModes) should be an int and positive"
            )
        if not isinstance(self._tol_num, float) or self._tol_num <= 0:
            raise TypeError(
                "Numerical tolerance for basis construction (TOL_NUM) should be an float and positive"
            )

    @abstractmethod
    def validateMethodState(self):
        """Check the attributes associated to the state (anything linked to matrices and vectors)"""
        pass

    def runCompatibilityTests(self):
        """Testing compatibility between options (for arguments)"""
        if self._methodCompress in ["GS-classical", "GS-modified"] and self._crit_tolerance is None:
            raise ValueError("If method is of GS type, user should provide a tolerance")
        if self._criterionModes == "energy" and self._crit_tolerance is None:
            raise ValueError("If criterion = energy, user should provide a tolerance")
        if self._criterionModes == "nbModes" and self._crit_nbModes is None:
            raise ValueError("If criterion = nbModes, user should provide a number of modes")

    def setCompressionMethod(self, method):
        """Set method for the compression method"""
        self._methodCompress = method

    def setCriterionModes(self, criterion):
        """Set method for the criterion for selecting modes"""
        self._criterionModes = criterion

    def getCompressionMethod(self, method):
        """Get method for the criterion for selecting modes"""
        return self._methodCompress

    def getCriterionModes(self, method):
        """Get method for the compression method"""
        return self._criterionModes

    def computePODBasis(self, option=1):
        """Method to construct a reduced order basis by POD
        using the stored snapshots

        Arguments:
            option (int): Changes the outputs of the function. If option=1, only reduced order basis. If option=2, returns reduced order basis and singular values.
        """
        assert option in OPTION_POD_VALUES
        return self.POD(self._snapshots, option=option)

    @abstractmethod
    def setInfosSnapshots(self):
        """Store information about the size of the snapshot matrix"""
        pass

    @abstractmethod
    def setCorrelationOperator(self, corrOperator=None):
        """Set method for the correlation operator

        Arguments:
            corrOperator (Any): Correlation operator when using the method of snapshots
        """
        pass

    @abstractmethod
    def correctionSnapshots(self):
        """Correct the snapshots by removing null values"""
        pass

    def selectModes(self, Phi, singval, tolerance=None, nbModes=None):
        """Selects modes and singular values based on a given criterion.

        The selection is performed according to the `_criterionModes` attribute,
        which can be 'energy' (using `tolerance`) or 'nbModes'.

        Arguments:
            Phi (Any): The full matrix of POD modes (format depends on class).
            singval (numpy.ndarray): The array of all singular values.
            tolerance (float | None, optional): Tolerance for the 'energy' criterion. Defaults to None.
            nbModes (int | None, optional): Number of modes for the 'nbModes' criterion. Defaults to None.

        Returns:
            Phi_v (Any): The truncated matrix of POD modes (reduced order basis).
            singval_v (numpy.ndarray): The truncated array of singular values.
        """
        ## - Test
        if tolerance is None and nbModes is None:
            raise ValueError(
                "selectModes: Either tolerance or nbModes should be provided to the method"
            )
        ## - Choice of the number of modes to keep
        if self._criterionModes == "energy":
            s_squared = singval**2
            sum_i = 0
            i = 0
            while i < len(singval) and sum_i / np.sum(s_squared) < (1 - tolerance):
                sum_i += s_squared[i]
                i += 1
            nbModes_v = i
        elif self._criterionModes == "nbModes":
            if nbModes is None or nbModes > len(singval):
                raise ValueError("selectModes: nbModes should be given or is too big!")
            nbModes_v = nbModes
        else:
            raise ValueError(
                f"PODAnalysis: Method '{self._criterionModes}' is not valid. Choose method in {POD_CRITERION_METHOD}."
            )
        ## - Truncation of the POD Basis
        Phi_v = self.correctionModesAfterSelection(Phi, nbModes_v)
        singval_v = singval[:nbModes_v]
        return Phi_v, singval_v

    @abstractmethod
    def correctionModesAfterSelection(self, Phi, nbModes_v):
        """Construction of a reduced basis by selecting
        the most important modes (the first nbModes_v)

        Arguments:
            Phi (Any): Basis
            nbModes_v (int): number of modes to keep (the first ones)
        """
        pass

    def POD(self, matS, option):
        """Method to construct a reduced order basis by POD

        Arguments:
            matS (Any): Matrix of snapshots on which the POD operator should be applied
            option (int): Changes the outputs of the function. If option=1, only reduced order basis.
                If option=2, returns reduced order basis and singular values.

        Returns:
            Phi (Any): Reduced order basis
            singval (numpy.ndarray): Singular values (only if option=2)
        """
        assert option in OPTION_POD_VALUES
        ## - Compression step
        if self._methodCompress == "snapshot":
            Phi, singval = self.snapshotMethod(matS)
        elif self._methodCompress == "SVD":
            Phi, singval = self.SVDMethod(matS)
        elif self._methodCompress == "GS-classical":
            Phi, singval = self.GSMethod(matS, self._crit_tolerance, "classical")
        elif self._methodCompress == "GS-modified":
            Phi, singval = self.GSMethod(matS, self._crit_tolerance, "modified")
        else:
            raise ValueError(
                f"PODAnalysis: Method '{self._methodCompress}' is not implemented yet."
            )
        if self._methodCompress in POD_METHOD_WITHOUT_CRIT:
            Phi_t, singval_t = Phi, singval
        else:
            ## - Apply truncation
            Phi_t, singval_t = self.selectModes(
                Phi, singval, self._crit_tolerance, self._crit_nbModes
            )
        ## - Return outputs
        if option == 1:
            return Phi_t
        elif option == 2:
            return Phi_t, singval_t
        else:
            raise ValueError("PODAnalysis: computePODBasis should be 1 or 2.")

    @abstractmethod
    def SVDMethod(self, matS, verbose=True):
        """Compression method using the snapshot method on a correlation matrix

        Arguments:
            matS (Any): Matrix of snapshots on which the POD operator should be applied

        Returns:
            Phi (Any): Reduced order basis
            singval (numpy.ndarray): Singular values
        """
        pass

    @abstractmethod
    def snapshotMethod(self, matS):
        """Compression method using SVD on the snapshot matrix

        Arguments:
            matS (Any): Matrix of snapshots on which the POD operator should be applied

        Returns:
            Phi (Any): Reduced order basis
            singval (numpy.ndarray): Singular values
        """
        pass

    @abstractmethod
    def updateGStype(self, Phi, singval, snapshot_new, tole, methodGS):
        """Compression method using a Gram-Schmidt process

        Arguments:
            matS (Any): Matrix of snapshots on which the POD operator should be applied
            tole (float): Tolerance used for the test when adding new snapshot
            methodGS (str): Should be "classical" or "modified" = GS method applied

        Returns:
            Phi (numpy.ndarray): Reduced order basis
            singval (numpy.ndarray): Singular values
        """
        pass

    @abstractmethod
    def computeGSprojection(self, Phi, s_new, methodGS):
        """Compute a Gram-Schmidt projection

        Arguments:
            Phi (Any): Basis
            s_new (Any): New snapshot considered
            methodGS (str): Should be "classical" or "modified" = GS method applied

        Returns:
            numpy.ndarray: Projected snapshot
        """
        pass

    @abstractmethod
    def GSMethod(self, matS, tole, methodGS):
        """Compression method using a Gram-Schmidt process

        Arguments:
            matS (Any): Matrix of snapshots on which the POD operator should be applied
            tole (float): Tolerance used for the test when adding new snapshot
            methodGS (str): Should be "classical" or "modified" = GS method applied

        Returns:
            Phi (Any): Reduced order basis
            singval (numpy.ndarray): Singular values
        """
        pass

    @abstractmethod
    def computePODBasisIncremental(self, Phi, singval=None, method="HPOD", option=1):
        """Method to enrich a reduced order basis with the stored snapshots

        Arguments:
            Phi (Any): Reduced order basis which has been previously computed
            method (str): Name of the incremental approach to use
            option (int): Changes the outputs of the function. If option=1, only reduced order basis.
                If option=2, returns reduced order basis and singular values.
        """
        pass

    def computeDecayRate(self, singval):
        """Compute a decay rate of a list of singular values

        Arguments:
            singval (numpy.ndarray): Singular values (order in a decreasing manner)

        Returns:
            float: Decay rate
        """
        nbSing = len(singval)

        N = np.log(np.arange(1, nbSing + 1))
        Y = np.log(singval)

        sum_N = np.sum(N)
        sum_Y = np.sum(Y)
        sum2_N = np.sum(N**2)

        decayRate = (nbSing * np.dot(Y.T, N) - sum_N * sum_Y) / (nbSing * sum2_N - sum_N**2)
        return decayRate

    def validateIncrementalParams(self, singval, method, option):
        """
        Validates parameters for the incremental POD computation.

        Raises:
            ValueError: If parameter combinations are invalid.
        """
        assert method in INCR_POD_METHOD
        assert option in OPTION_POD_VALUES
        if option == 2 and singval is None:
            raise ValueError(
                "To compute updated singular values (option=2), the initial "
                "singular values (`singval`) must be provided."
            )
        if method == "HAPOD" and singval is None:
            raise ValueError(
                "The 'HAPOD' method requires the initial singular values "
                "(`singval`) to be provided."
            )


class PODAnalysisNumpy(PODAnalysis):
    """
    Class for building a base incrementally using POD
    when using numpy arrays for storage
    """

    def __init__(self, *args, **kwargs):
        "Initialization of PODAnalysisNumpy"
        super().__init__(*args, **kwargs)

    @classmethod
    def supports(cls, snapshots):
        """Tell if these snapshots are supported.

        Args:
            snapshots (Misc): snapshots to be tested.

        Returns:
            bool: *True* if *snapshots* is a numpy array.
        """
        return isinstance(snapshots, np.ndarray)

    def validateMethodState(self):
        """Check the attributes associated to the state (anything linked to matrices and vectors)"""
        if not isinstance(self._corrOperator, (np.ndarray, scipy.sparse.csr_matrix)):
            raise TypeError("The correlation operator should be a CSR matrix or a numpy matrix")
        if not isinstance(self._snapshots, np.ndarray):
            raise TypeError("The snapshots should be strored in a numpy matrix")

    def setInfosSnapshots(self):
        """Store information about the size of the snapshot matrix"""
        self._numberOfDOFs = self._snapshots.shape[0]
        self._numberOfSnapshots = self._snapshots.shape[1]

    def setCorrelationOperator(self, corrOperator=None):
        """Set method for the correlation operator

        Arguments:
            corrOperator (scipy.sparse.csr_matrix | None): Correlation operator when using the method of snapshots
        """
        if corrOperator is None:
            self._corrOperator = scipy.sparse.identity(self._numberOfDOFs, format="csr")
        else:
            self._corrOperator = corrOperator

    def correctionSnapshots(self):
        """Correct the snapshots by removing null values"""
        norms = np.linalg.norm(self._snapshots, axis=0)
        self._snapshots = self._snapshots[:, norms > self._tol_num]

    def correctionModesAfterSelection(self, Phi, nbModes_v):
        """Construction of a reduced basis by selecting
        the most important modes (the first nbModes_v)

        Arguments:
            Phi (numpy.ndarray): Basis
            nbModes_v (int): number of modes to keep (the first ones)
        """
        return Phi[:, :nbModes_v]

    def computePODBasisIncremental(self, Phi, singval=None, method="HPOD", option=1):
        """Method to enrich a reduced order basis with the stored snapshots

        Arguments:
            Phi (numpy.ndarray): Reduced order basis which has been previously computed
            method (str): Name of the incremental approach to use
            option (int): Changes the outputs of the function. If option=1, only reduced order basis.
            If option=2, returns reduced order basis and singular values.
        """
        self.validateIncrementalParams(singval, method, option)
        if method == "HPOD":
            matS = self._snapshots
            projS = np.zeros(np.shape(matS))
            for i in range(matS.shape[1]):
                projS[:, i] = self.computeGSprojection(Phi, matS[:, i], "modified")
            Phi_new, singval_new = self.POD(projS, option=option)
            if option == 1:
                return np.column_stack((Phi, Phi_new))
            else:
                assert singval is not None
                return np.column_stack((Phi, Phi_new)), np.concatenate(
                    (singval, singval_new), axis=None
                )
        elif method == "HAPOD":
            assert singval is not None
            mPhi = singval * Phi
            assert np.shape(Phi) == np.shape(mPhi)
            mS = np.column_stack((mPhi, self._snapshots))
            return self.POD(mS, option=option)
        else:
            raise ValueError(
                f"PODAnalysis: Method '{method}' is not valid. Choose method in {INCR_POD_METHOD}."
            )

    def updateGStype(self, Phi, singval, snapshot_new, tole, methodGS):
        """Compression method using a Gram-Schmidt process

        Arguments:
            matS (numpy.ndarray): Matrix of snapshots on which the POD operator should be applied
            tole (float): Tolerance used for the test when adding new snapshot
            methodGS (str): Should be "classical" or "modified" = GS method applied

        Returns:
            Phi (numpy.ndarray): Reduced order basis
            singval (numpy.ndarray): Singular values
        """
        assert methodGS in GS_METHOD
        ## - Check that the added snapshot is 1D
        s_new = snapshot_new.flatten()
        s_new_norm = np.linalg.norm(snapshot_new)
        ## - GS orthogonalisation
        s_new = self.computeGSprojection(Phi, s_new, methodGS)
        s_new_perp_norm = np.linalg.norm(s_new)
        if s_new_perp_norm > tole * s_new_norm:
            Phi = np.column_stack((Phi, s_new / s_new_perp_norm))
            singval = np.hstack([singval, s_new_perp_norm])
        return Phi, singval

    def GSMethod(self, matS, tole, methodGS):
        """Compression method using a Gram-Schmidt process

        Arguments:
            matS (numpy.ndarray): Matrix of snapshots on which the POD operator should be applied
            tole (float): Tolerance used for the test when adding new snapshot
            methodGS (str): Should be "classical" or "modified" = GS method applied

        Returns:
            Phi (numpy.ndarray): Reduced order basis
            singval (numpy.ndarray): Singular values
        """
        s_0_norm = np.linalg.norm(matS[:, 0])
        Phi = matS[:, 0:1] / s_0_norm
        singval = np.array([s_0_norm])
        n_snap = matS.shape[1]
        for i in range(1, n_snap):
            Phi, singval = self.updateGStype(Phi, singval, matS[:, i : i + 1], tole, methodGS)
        return Phi, singval

    def computeGSprojection(self, Phi, s_new, methodGS):
        """Compute a Gram-Schmidt projection

        Arguments:
            Phi (numpy.ndarray): Basis
            s_new (numpy.ndarray): New snapshot considered
            methodGS (str): Should be "classical" or "modified" = GS method applied

        Returns:
            numpy.ndarray: Projected snapshot
        """
        assert methodGS in GS_METHOD
        ## - GS orthogonalisation
        n_modes = Phi.shape[1]
        for kp in range(2):  # Kahan-Parlett process
            if methodGS == "classical":
                s_new_loc = s_new
                for k in range(n_modes):
                    s_new = s_new - np.dot(s_new_loc, Phi[:, k]) * Phi[:, k]
            if methodGS == "modified":
                for k in range(n_modes):
                    s_new = s_new - np.dot(s_new, Phi[:, k]) * Phi[:, k]
        return s_new

    def SVDMethod(self, matS, verbose=True):
        """Compression method using the snapshot method on a correlation matrix

        Arguments:
            matS (numpy.ndarray): Matrix of snapshots on which the POD operator should be applied

        Returns:
            Phi (numpy.ndarray): Reduced order basis
            singval (numpy.ndarray): Singular values
        """
        ## - Apply SVD directly on the snapshot matrix
        # LAPACK (MKL) may raise floating point exceptions internally
        with disable_fpe():
            U, sigma, _ = np.linalg.svd(matS, full_matrices=False)
        ## - Order eigenvalues and compute basis
        n = np.where(sigma == 0)[0]
        if n.size == 0:
            n = len(sigma)
        else:
            n = n[0]
        return U[:, :n], sigma[:n]

    def snapshotMethod(self, matS):
        """Compression method using SVD on the snapshot matrix

        Arguments:
            matS (numpy.ndarray): Matrix of snapshots on which the POD operator should be applied

        Returns:
            Phi (numpy.ndarray): Reduced order basis
            singval (numpy.ndarray): Singular values
        """
        ## - Compute correlation matrix
        corrMatrix = matS.T @ self._corrOperator @ matS
        ## - Solve eigenproblem
        with disable_fpe():
            eigenvalues, eigenvectors = np.linalg.eigh(corrMatrix)
        ## - Order eigenvalues and compute basis
        idx = np.argsort(eigenvalues)[::-1]
        eigenvalues = eigenvalues[idx]
        eigenvalues = np.where(eigenvalues < 0, 0, eigenvalues)
        eigenvectors = eigenvectors[:, idx]

        n = np.where(eigenvalues == 0)[0]
        if n.size == 0:
            n = len(eigenvalues)
        else:
            n = n[0]
        # - Return reduced order basis and singular values
        return np.dot(matS, eigenvectors[:, :n]) / np.sqrt(eigenvalues[:n]), np.sqrt(
            eigenvalues[:n]
        )


class PODAnalysisPetsc(PODAnalysis):
    """
    Class for building a base incrementally using POD
    when using PETSc arrays for storage
    """

    _comm = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, *args, **kwargs):
        "Initialization of PODAnalysisPetsc"
        super().__init__(*args, **kwargs)

    @classmethod
    def supports(cls, snapshots):
        """Tell if these snapshots are supported.

        Args:
            snapshots (Misc): snapshots to be tested.

        Returns:
            bool: *True* if *snapshots* is a PETSc matrix.
        """
        return isinstance(snapshots, PETSc.Mat)

    def validateMethodState(self):
        """Check the attributes associated to the state (anything linked to matrices and vectors)"""
        if not isinstance(self._corrOperator, PETSc.Mat):
            raise TypeError("The correlation operator should be a PETSc.Mat")
        if not isinstance(self._snapshots, PETSc.Mat):
            raise TypeError("The snapshots should be strored in a PETSc.Mat")

    def setInfosSnapshots(self):
        """Store information about the size of the snapshot matrix"""
        self._numberOfDOFs, self._numberOfSnapshots = self._snapshots.getSize()
        ## - Add communicator to handle the parallel version
        self._comm = self._snapshots.getComm()

    def _extractColumnsPetscMat(self, matA, select_condition):
        """Extracts columns from a PETSc matrix based on a condition.

        Arguments:
            matA (PETSc.Mat): The source PETSc matrix.
            select_condition (Callable): Function returning True for columns to keep.
        """
        i_start, i_end = matA.getOwnershipRange()
        is_rows = PETSc.IS().createStride(i_end - i_start, i_start, 1, comm=self._comm)
        i_start, i_end = matA.getOwnershipRangeColumn()
        cols = []
        for i in range(i_start, i_end):
            if select_condition(i):
                cols.append(i)
        is_cols = PETSc.IS().createGeneral(cols, comm=self._comm)
        matB = matA.createSubMatrix(is_rows, is_cols)
        return matB

    def _restrictBasisAfterProcedure(self, n_rows, vectors, n):
        """Assembles a list of PETSc vectors into a single PETSc matrix.

        Arguments:
            n_rows (int): Total number of rows for the final basis matrix (global vector size).
            vectors (list[PETSc.Vec]): A list of the PETSc vectors that will form the columns of the matrix.
            n (int): The number of vectors in the list (and columns in the final matrix).

        Returns:
            PETSc.Mat: The assembled basis matrix, where each column is an input vector.
        """
        ## - Set transpose of the basis matrix
        Phi_petscT = PETSc.Mat().createDense([n, n_rows], comm=self._comm)
        Phi_petscT.setUp()
        row = 0
        for i in range(n):
            vec = vectors[i]
            i_start, i_end = vec.getOwnershipRange()
            vec_array = vec.getArray(readonly=True)
            Phi_petscT.setValues(
                row,
                np.arange(i_start, i_end, dtype="int32"),
                vec_array,
                addv=PETSc.InsertMode.INSERT_VALUES,
            )
            row += 1
        Phi_petscT.assemble()

        return Phi_petscT.transpose()

    def setCorrelationOperator(self, corrOperator=None):
        """Set method for the correlation operator

        Arguments:
            corrOperator (PETSc.Mat | None): Correlation operator when using the method of snapshots
        """
        if corrOperator is None:
            I = PETSc.Mat().create(self._comm)
            loc_row, _ = self._snapshots.getLocalSize()
            I.setSizes(((loc_row, self._numberOfDOFs), (loc_row, self._numberOfDOFs)))
            I.setType("aij")
            I.setPreallocationNNZ(1)
            diag_vec = I.createVecLeft()
            diag_vec.set(1.0)

            I.setDiagonal(diag_vec)
            diag_vec.destroy()
            I.assemble()
            self._corrOperator = I
        else:
            self._corrOperator = corrOperator

    def correctionSnapshots(self):
        """Correct the snapshots by removing null values"""
        col_vec = self._snapshots.createVecLeft()
        indices_to_keep = []
        for j in range(self._numberOfSnapshots):
            self._snapshots.getColumnVector(j, col_vec)
            if col_vec.norm() > self._tol_num:
                indices_to_keep.append(j)

        if len(indices_to_keep) < self._numberOfSnapshots:
            self._snapshots = self._extractColumnsPetscMat(
                self._snapshots, lambda i: i in indices_to_keep
            )

    def correctionModesAfterSelection(self, Phi, nbModes_v):
        """Construction of a reduced basis by selecting
        the most important modes (the first nbModes_v)

        Arguments:
            Phi (PETSc.Mat): Basis
            nbModes_v (int): number of modes to keep (the first ones)
        """
        Phi_v = self._extractColumnsPetscMat(Phi, lambda i: i < nbModes_v)

        return Phi_v

    def _stackMatriceHorizontally(self, mat_a, mat_b):
        """
        Compute a new matrix [mat_a, mat_b] using an efficient method for dense matrices.

        Arguments:
            mat_a (PETSc.Mat): (dense)
            mat_b (PETSc.Mat): (dense)
        """
        ## - Get sizes and check for compatibility
        M1, N1 = mat_a.getSize()
        M2, N2 = mat_b.getSize()

        if M1 != M2:
            raise ValueError(f"Matrices must have the same number of rows. Got {M1} and {M2}.")

        ## - Create the new dense matrix
        M = M1
        N_new = N1 + N2
        new_mat = PETSc.Mat().createDense([M, N_new], comm=self._comm)
        new_mat.setUp()

        ## - Concatenates the local arrays horizontally
        local_a_arr = mat_a.getDenseArray(readonly=True)
        local_b_arr = mat_b.getDenseArray(readonly=True)
        local_new_arr_content = np.hstack((local_a_arr, local_b_arr))

        ## - Place the result into the new matrix
        local_new_mat_arr = new_mat.getDenseArray()
        local_new_mat_arr[:, :] = local_new_arr_content

        ## - Assemble the final matrix
        new_mat.assemble()
        new_mat.assemblyBegin()
        new_mat.assemblyEnd()

        return new_mat

    def computePODBasisIncremental(self, Phi, singval=None, method="HPOD", option=1):
        """Method to enrich a reduced order basis with the stored snapshots

        Arguments:
            Phi (PETSc.Mat): Reduced order basis which has been previously computed
            method (str): Name of the incremental approach to use
            option (int): Changes the outputs of the function. If option=1, only reduced order basis.
            If option=2, returns reduced order basis and singular values.
        """
        self.validateIncrementalParams(singval, method, option)
        row_indices = np.arange(self._numberOfDOFs, dtype="int32")

        if method == "HPOD":
            matS = self._snapshots
            M, N = matS.getSize()

            projS = matS.duplicate(copy=False)
            projS.setUp()
            local_projS_arr = projS.getDenseArray()

            rstart, rend = projS.getOwnershipRange()
            m_local = projS.getLocalSize()[0]

            ## - Prepare temporary vectors
            col_s = matS.createVecLeft()
            col_proj = matS.createVecLeft()

            ## - Iterates on the colomuns (basis vectors)
            for i in range(N):
                matS.getColumnVector(i, col_s)
                col_proj = self.computeGSprojection(Phi, col_s, "modified")
                local_col_proj_data = col_proj.getArray(readonly=True)

                if local_col_proj_data.size != m_local:
                    raise ValueError("Local size mismatch between the matrix and the vector..")

                local_projS_arr[:, i] = local_col_proj_data

            projS.assemble()

            Phi_new, singval_new = self.POD(projS, option=option)
            if option == 1:
                return self._stackMatriceHorizontally(Phi, Phi_new)
            else:
                assert singval is not None
                return self._stackMatriceHorizontally(Phi, Phi_new), np.concatenate(
                    (singval, singval_new), axis=None
                )

        elif method == "HAPOD":
            assert singval is not None
            mPhi = Phi.duplicate(copy=True)
            col_temp = Phi.createVecLeft()

            k = len(singval)
            i_start, i_end = mPhi.getOwnershipRange()
            local_row_indices = np.arange(i_start, i_end, dtype="int32")

            for j in range(k):
                mPhi.getColumnVector(j, col_temp)
                col_temp.scale(singval[j])
                local_values_array = col_temp.getArray(readonly=True)
                values_to_set = local_values_array.reshape(-1, 1)
                col_index_array = np.array([j], dtype="int32")

                mPhi.setValues(
                    local_row_indices,
                    col_index_array,
                    values_to_set,
                    addv=PETSc.InsertMode.INSERT_VALUES,
                )

            mPhi.assemble()

            mS = self._stackMatriceHorizontally(mPhi, self._snapshots)
            return self.POD(mS, option=option)

        else:
            raise ValueError(
                f"PODAnalysis: Method '{method}' is not valid. Choose method in {INCR_POD_METHOD}."
            )

    def updateGStype(self, Phi, singval, snapshot_new, tole, methodGS):
        """Update of a reduced order basis using a Gram-Schmidt process

        Arguments:
            Phi (PETSc.Mat): Basis
            singval (numpy.ndarray): Singular values
            snapshot_new (PETSc.Vec): New snapshot considered
            tole (float): Tolerance used for the test when adding new snapshot
            methodGS (str): Should be "classical" or "modified" = GS method applied

        Returns:
            Phi (PETSc.Mat): Reduced order basis
            singval (numpy.ndarray): Singular values
        """
        assert methodGS in GS_METHOD
        _, N = Phi.getSize()

        s_new_norm = snapshot_new.norm()
        s_new_proj = self.computeGSprojection(Phi, snapshot_new, methodGS)

        s_new_perp_norm = s_new_proj.norm()

        if s_new_perp_norm > tole * s_new_norm:
            _, N = Phi.getSize()

            def vectorToMatrixCol(v: PETSc.Vec) -> PETSc.Mat:
                """
                Converts a PETSc vector into a single-column dense PETSc matrix.
                """
                comm = v.getComm()

                m_global = v.getSize()
                m_local = v.getLocalSize()

                V_mat = PETSc.Mat().create(comm=comm)
                V_mat.setSizes(((m_local, m_global), (1, 1)))
                V_mat.setType(PETSc.Mat.Type.DENSE)
                V_mat.setUp()

                local_v_array = v.getArray(readonly=True)
                local_v_mat_array = V_mat.getDenseArray()
                local_v_mat_array[:, 0] = local_v_array

                V_mat.assemble()

                return V_mat

            a = vectorToMatrixCol(s_new_proj)
            a.scale(1.0 / s_new_perp_norm)
            Phi_new = self._stackMatriceHorizontally(Phi, a)
            ## - Update the singular values
            singval_new = np.hstack([singval, s_new_perp_norm])

            return Phi_new, singval_new
        else:
            ## - If nothing is needed, return basis and singular values unchanged
            return Phi, singval

    def GSMethod(self, matS, tole, methodGS):
        """Compression method using a Gram-Schmidt process

        Arguments:
            matS (PETSc.Mat): Matrix of snapshots on which the POD operator should be applied
            tole (float): Tolerance used for the test when adding new snapshot
            methodGS (str): Should be "classical" or "modified" = GS method applied

        Returns:
            Phi (PETSc.Mat): Reduced order basis
            singval (numpy.ndarray): Singular values
        """
        ## - Set first column for GS process
        col_vec = matS.createVecLeft()
        matS.getColumnVector(0, col_vec)
        s_0_norm = col_vec.norm()

        singval = np.array([s_0_norm])
        Phi = PETSc.Mat().createDense([self._numberOfDOFs, 1], comm=self._comm)
        if s_0_norm > self._tol_num:
            col_vec.scale(1.0 / s_0_norm)
        col_vec_array = col_vec.getArray(readonly=True)

        i_start, i_end = Phi.getOwnershipRange()
        local_rows_indices = np.arange(i_start, i_end, dtype="int32")
        Phi.setValues(
            local_rows_indices,
            np.array([0], dtype="int32"),
            col_vec_array,
            addv=PETSc.InsertMode.INSERT_VALUES,
        )
        Phi.assemble()

        ## - Loop to add vectors in an incremental way
        for i in range(1, matS.getSize()[1]):
            matS.getColumnVector(i, col_vec)
            Phi, singval = self.updateGStype(Phi, singval, col_vec, tole, methodGS)

        return Phi, singval

    def computeGSprojection(self, Phi, s_new, methodGS):
        """Compute a Gram-Schmidt projection

        Arguments:
            Phi (PETSc.Mat): Basis
            s_new (PETSc.Vec): New snapshot considered
            methodGS (str): Should be "classical" or "modified" = GS method applied

        Returns:
            PETSc.Vec: Projected snapshot
        """
        assert methodGS in GS_METHOD

        s_proj = s_new.copy()

        M, n_modes = Phi.getSize()
        phi_k = Phi.createVecLeft()

        for kp in range(2):
            if methodGS == "classical":
                s_loc = s_proj.copy()
                for k in range(n_modes):
                    Phi.getColumnVector(k, phi_k)
                    alpha = s_loc.dot(phi_k)
                    # s_proj = s_proj - alpha * phi_k
                    s_proj.axpy(-alpha, phi_k)
            elif methodGS == "modified":
                for k in range(n_modes):
                    Phi.getColumnVector(k, phi_k)
                    alpha = s_proj.dot(phi_k)
                    # s_proj = s_proj - alpha * phi_k
                    s_proj.axpy(-alpha, phi_k)
        return s_proj

    def SVDMethod(self, matS, verbose=False):
        """Compression method using SVD on the snapshot matrix

        Arguments:
            matS (PETSc.Mat): Matrix of snapshots on which the POD operator should be applied

        Returns:
            Phi (PETSc.Mat): Reduced order basis
            singval (numpy.ndarray): Singular values
        """
        Print = PETSc.Sys.Print

        ## - Creation and configuration of the SVD solver
        svd = SLEPc.SVD().create(comm=self._comm)
        svd.setOperator(matS)
        svd.setType(SLEPc.SVD.Type.TRLANCZOS)

        svd.setFromOptions()
        ## - Resolution

        svd.solve()

        n_conv = svd.getConverged()
        if verbose:
            Print("******************************")
            Print("*** SLEPc SVD Solution Results ***")
            Print("******************************\n")
            svd_type = svd.getType()
            Print(f"Solution method: {svd_type}")
            its = svd.getIterationNumber()
            Print(f"Number of iterations: {its}")
            nsv, _, _ = svd.getDimensions()
            Print(f"Number of requested singular values: {nsv}")
            tol, maxit = svd.getTolerances()
            Print(f"Stopping condition: tol={tol:.4g}, maxit={maxit}")
            Print(f"Number of converged singular triplets: {n_conv}\n")

        ## - Construction of the outputs
        singular_values = []
        singular_vectors = []

        if n_conv > 0:
            v_tmp, u_tmp = matS.createVecs()

            if verbose:
                Print("    sigma       residual norm ")
                Print("-------------  ---------------")

            for i in range(n_conv):
                sigma_i = svd.getSingularTriplet(i, u_tmp, v_tmp)
                singular_values.append(sigma_i)
                singular_vectors.append(u_tmp.copy())

                if verbose:
                    error = svd.computeError(i)
                    Print(f"   {sigma_i:6f}     {error:12g}")

            if verbose:
                Print()

            u_tmp.destroy()
            v_tmp.destroy()

        sigma = np.array(singular_values)
        zero_indices = np.where(sigma < self._tol_num)[0]
        n = zero_indices[0] if zero_indices.size > 0 else len(sigma)

        Phi_petsc = self._restrictBasisAfterProcedure(matS.getSize()[0], singular_vectors, n)

        ## - Clean vectors
        for vec in singular_vectors:
            vec.destroy()
        svd.destroy()

        return Phi_petsc, sigma[:n]

    def snapshotMethod(self, matS):
        """Compression method using the snapshot method on a correlation matrix

        Arguments:
            matS (PETSc.Mat): Matrix of snapshots on which the POD operator should be applied

        Returns:
            Phi (PETSc.Mat): Reduced order basis
            singval (numpy.ndarray): Singular values
        """
        ## - Compute correlation matrix
        corrMatrix = self._corrOperator.ptap(matS)
        # - Solve eigenproblem using SLEPc
        eps = SLEPc.EPS().create(comm=self._comm)
        eps.setOperators(corrMatrix)
        eps.setProblemType(SLEPc.EPS.ProblemType.HEP)
        eps.solve()

        ## - Extract eigenvalues and compute basis
        nconv = eps.getConverged()
        eigenvalues = []
        basis_vectors = []

        _, v = corrMatrix.createVecs()
        phi_i = matS.createVecLeft()
        for i in range(nconv):
            k = eps.getEigenvalue(i)

            if k.real <= self._tol_num:
                break

            eigenvalues.append(k.real)

            ## - Get eigenvector and compute the mode
            eps.getEigenvector(i, v)
            sing_val = np.sqrt(k.real)

            matS.mult(v, phi_i)
            phi_i.scale(1.0 / sing_val)

            basis_vectors.append(phi_i.copy())

        ## - Assembly of the final bais  matrix from all the vectors computed before
        n_modes = len(basis_vectors)

        if n_modes == 0:
            Phi = PETSc.Mat().createDense([matS.getSize()[0], 0], comm=matS.getComm())
            Phi.assemble()
            return Phi, np.array([])
        else:
            Phi_petsc = self._restrictBasisAfterProcedure(
                matS.getSize()[0], basis_vectors, len(basis_vectors)
            )

            singular_values = np.sqrt(np.array(eigenvalues))
            return Phi_petsc, singular_values
