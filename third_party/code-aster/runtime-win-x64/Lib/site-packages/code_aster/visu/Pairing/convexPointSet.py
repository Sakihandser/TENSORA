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
from abc import ABC, abstractmethod
from ...Utilities import no_new_attributes


## -----------------------------------------------------------
#   HELPER FUNCTION
## -----------------------------------------------------------
def transformToPlanarCoords(point, ref, vec1, vec2):
    """Transforms a 3D point into planar coordinates based on a basis defined by two vectors.

    This function projects the vector from a reference point (ref) to a given point (point)
    onto the two basis vectors (vec1, vec2), and returns the resulting 2D coordinates.

    Arguments:
        point (numpy.ndarray): 3D point to transform (array of 3 elements).
        ref (numpy.ndarray): 3D reference point (array of 3 elements).
        vec1 (numpy.ndarray): First basis vector (array of 3 elements).
        vec2 (numpy.ndarray): Second basis vector (array of 3 elements).

    Returns:
        numpy.ndarray: Array of 2 elements containing the planar coordinates.
    """
    # - Compute the vector between a given point and the ref point (ref)
    pointVector = point - ref
    # - Project on the basis vectors vec1 and vec2
    coord1 = np.dot(pointVector, vec1)
    coord2 = np.dot(pointVector, vec2)

    return np.array([coord1, coord2])


## -----------------------------------------------------------
#   NUMERICAL STRATEGIES ASSOCIATED TO CONVEX SETS
## ----------------------------------------------------------


class ConvexSetStrategyInterface(ABC):
    """
    Base class for numerical strategies for convex sets.

     Attributes:
         _initPoints (numpy.ndarray): The array of initial (unsorted) points provided at creation.
             The shape is (N, D), where N is the number of points and D is the dimension.
         _sortedPoints (numpy.ndarray | None): The array of sorted points to form a simple polygon
             (e.g., counter-clockwise). Initialized to None and computed on demand.
         _bary (numpy.ndarray | None): The barycenter (centroid) of the initial points.
             Initialized to None and computed on demand.
    """

    _initPoints = _sortedPoints = _bary = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, points):
        """
        Initializes the strategy with a set of points.

        Arguments:
            points (numpy.ndarray): An array of points of shape (N, D) defining the convex set.
        """
        self._initPoints = points
        self._sortedPoints = None
        self._bary = None

    @abstractmethod
    def sortPoints(self):
        """Sorts the points to form a simple, ordered polygon."""
        pass

    @abstractmethod
    def computeArea(self):
        """Computes the area (or length for 1D sets).

        Returns:
            float: The area of the polygon.
        """
        pass

    @abstractmethod
    def computeBary(self):
        """Computes the barycenter of the points.

        Returns:
            numpy.ndarray: The barycenter point.
        """

    def getSortedPoints(self):
        """Returns the sorted points, sorting them first if necessary."""
        if self._sortedPoints is None:
            self.sortPoints()
        return self._sortedPoints


class CSStrat1D(ConvexSetStrategyInterface):
    """Strategy for 1D convex sets (lines) in any dimensional space."""

    def sortPoints(self):
        """Sorts points along the first available coordinate axis."""
        indicesSorted = np.argsort(self._initPoints[:, 0])
        self._sortedPoints = np.copy(self._initPoints[indicesSorted])

    def computeBary(self):
        """Computes the barycenter (midpoint) of the 1D set.

        Returns:
            numpy.ndarray: The barycenter point.
        """
        if self._bary is None:
            self._bary = np.mean(self._initPoints, axis=0)
        return self._bary

    def computeArea(self):
        """Computes the length of the 1D convex set.
        The "area" of a 1D set is its total length, defined by the distance
        between its two extreme points.

        Returns:
            float: The length of the segment.
        """
        if self._sortedPoints is None:
            self.sortPoints()
        return np.linalg.norm(self._sortedPoints[0] - self._sortedPoints[-1])


class CSStrat2DCodim0(ConvexSetStrategyInterface):
    """Strategy for 2D convex sets in a 2D ambient space."""

    def computeBary(self):
        """Computes the barycenter of the points.

        Returns:
            numpy.ndarray: The barycenter point.
        """
        if self._bary is None:
            self._bary = np.mean(self._initPoints, axis=0)
        return self._bary

    def sortPoints(self):
        """Sorts 2D points in counter-clockwise order around their barycenter."""
        bary = self.computeBary()
        angles = np.arctan2(self._initPoints[:, 1] - bary[1], self._initPoints[:, 0] - bary[0])
        indicesSorted = np.argsort(angles)
        self._sortedPoints = np.copy(self._initPoints[indicesSorted])

    def computeArea(self):
        """Computes the area of a 2D polygon.

        Returns:
            float: The area of the polygon.
        """
        if self._sortedPoints is None:
            self.sortPoints()

        n = len(self._sortedPoints)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += self._sortedPoints[i, 0] * self._sortedPoints[j, 1]
            area -= self._sortedPoints[j, 0] * self._sortedPoints[i, 1]
        return abs(area) / 2.0


class CSStrat2DCodim1(ConvexSetStrategyInterface):
    """Strategy for 2D convex sets in a 3D ambient space.

    In addition to the attributes inherited from `ConvexSetStrategyInterface`,
    this class defines:

    Attributes:
        _localBasis (numpy.ndarray | None): A local orthonormal basis [tangent1, tangent2, normal]
            for the plane containing the points.
    """

    _localBasis = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, points):
        super().__init__(points)
        self._localBasis = None

    def computeBary(self):
        """Computes the barycenter of the 3D points.

        Returns:
            numpy.ndarray: The barycenter point.
        """
        if self._bary is None:
            self._bary = np.mean(self._initPoints, axis=0)
        return self._bary

    def computeLocalBasis(self):
        """
        Computes a local orthonormal basis [tangent1, tangent2, normal] for the plane.

        Returns:
            numpy.ndarray: The local basis as a (3, 3) array.
        """
        if self._localBasis is not None:
            return self._localBasis

        a = self._initPoints[0]
        vecA = self._initPoints[1] - a
        norm_vecA = np.linalg.norm(vecA)
        if np.isclose(norm_vecA, 0):
            raise ValueError("The first two points are identical, cannot form a basis vector.")
        vec1 = vecA / norm_vecA  # First normalized tangent vector

        # - Find a second, non-collinear vector
        vecB = None
        for i in range(2, len(self._initPoints)):
            vec_candidate = self._initPoints[i] - a
            if not np.allclose(np.cross(vecA, vec_candidate), 0):
                vecB = vec_candidate
                break
        if vecB is None:
            raise ValueError("All provided points are collinear. Cannot form a 2D basis.")

        # - Compute the normal and the second tangent vector
        normal = np.cross(vecA, vecB)
        norm = normal / np.linalg.norm(normal)
        vec2 = np.cross(norm, vec1)

        self._localBasis = np.array([vec1, vec2, norm])
        return self._localBasis

    def computeArea(self):
        """
        Computes the area of the 2D polygon in 3D space.

        This is done by projecting the sorted 3D points onto their local 2D plane
        and then applying compute the area.
        """
        if self._sortedPoints is None:
            self.sortPoints()

        localBasis = self.computeLocalBasis()
        origin = self._initPoints[0]
        vec1, vec2 = localBasis[0], localBasis[1]

        coords_2d = np.array(
            [transformToPlanarCoords(p, origin, vec1, vec2) for p in self._sortedPoints]
        )

        n = len(coords_2d)
        area = 0.0
        for i in range(n):
            j = (i + 1) % n
            area += coords_2d[i, 0] * coords_2d[j, 1]
            area -= coords_2d[j, 0] * coords_2d[i, 1]

        return abs(area) / 2.0

    def sortPoints(self):
        """Sorts 3D points by projecting them onto their local 2D plane and sorting by angle."""
        bary = self.computeBary()
        localBasis = self.computeLocalBasis()

        # - Project all points and the barycenter to the local 2D coordinate system
        coords = np.array(
            [
                transformToPlanarCoords(p, self._initPoints[0], localBasis[0], localBasis[1])
                for p in self._initPoints
            ]
        )
        baryLoc = transformToPlanarCoords(bary, self._initPoints[0], localBasis[0], localBasis[1])

        # - Sort based on angle in the local plane
        angles = np.arctan2(coords[:, 1] - baryLoc[1], coords[:, 0] - baryLoc[0])
        indicesSorted = np.argsort(angles)
        self._sortedPoints = np.copy(self._initPoints[indicesSorted])


## -----------------------------------------------------------
#   CONVEX SET POINT CLASS
## -----------------------------------------------------------
class ConvexPointSet:
    """
    Based on the dimension and codimension, this class selects and
    instantiates the appropriate calculation strategy, then
    delegates all computational work to it.

    Attributes:
        _dim (int): Dimension of the convex set itself (1 for a line, 2 for a surface).
        _codim (int): Codimension of the set (ambient_space_dim - dim).
        _initPoints (np.ndarray): A copy of the points provided at construction.
        _pointSorted (bool): A flag to indicate if the points have already been sorted.
        _strategy (ConvexSetStrategyInterface): The chosen strategy instance for
            performing all calculations.
    """

    _dim = _codim = _initPoints = _pointSorted = _strategy = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, dim, points, codim):
        """Constructor for a convex set of points.

        Arguments:
            dim (int): Dimension of the convex set itself (1 for a line, 2 for a surface).
            points (list or np.ndarray): List of points defining the convex set.
            codim (int): Codimension of the set (ambient_space_dim - dim).

        Raises:
            NotImplementedError: If no strategy is available for the given dim/codim combination.
            ValueError, TypeError: For invalid input arguments (validation is recommended).
        """
        self._validateDimensions(dim, codim)
        init_points = self._validateAndConvertPoints(points)

        self._dim = dim
        self._codim = codim
        self._initPoints = init_points
        self._pointSorted = False

        self._createStrategy()

    def _validateDimensions(self, dim, codim):
        """Internal helper to validate dimension and codimension values.

        Arguments:
            dim (int): The dimension of the convex set.
            codim (int): The codimension of the convex set in its ambient space.

        Raises:
            TypeError: If 'dim' or 'codim' is not an integer.
            ValueError: If 'dim' or 'codim' is outside the allowed values.
        """
        DIM_AVAILABLE = [1, 2]
        CODIM_AVAILABLE = [0, 1, 2]
        if not isinstance(dim, int):
            raise TypeError(f"Dimension 'dim' must be an integer, but got {type(dim)}.")
        if not isinstance(codim, int):
            raise TypeError(f"Codimension 'codim' must be an integer, but got {type(codim)}.")
        if dim not in DIM_AVAILABLE:
            raise ValueError(f"Dimension 'dim' must be 1 or 2, but got {dim}.")
        if codim not in CODIM_AVAILABLE:
            raise ValueError(f"Codimension 'codim' must be 0, 1 or 2, but got {codim}.")

    def _validateAndConvertPoints(self, points):
        """Internal helper to validate and convert input points to a numpy array.

        Arguments:
            points (array-like): The input points to validate and convert.
                Can be a list of lists, a tuple of tuples, or any other
                structure convertible to a numpy array.

        Returns:
            numpy.ndarray: The converted points as a numpy array of floats.

        Raises:
            TypeError: If the input 'points' cannot be converted into a
                numeric numpy array.
        """
        try:
            init_points = np.array(points, dtype=float)
        except (ValueError, TypeError) as e:
            raise TypeError(
                f"Input 'points' could not be converted to a numeric numpy array. Reason: {e}"
            )

        if init_points.ndim != 2:
            raise ValueError(
                f"Input 'points' must be a 2D array-like structure (a list of points), but has {init_points.ndim} dimensions."
            )
        if init_points.shape[0] == 0:
            raise ValueError("Input 'points' cannot be empty.")

        return init_points

    def _createStrategy(self):
        """Selects and instantiates the appropriate strategy based on dim and codim."""
        strategy_map = {
            (1, 0): CSStrat1D,
            (1, 1): CSStrat1D,
            (1, 2): CSStrat1D,
            (2, 0): CSStrat2DCodim0,
            (2, 1): CSStrat2DCodim1,
        }
        key = (self._dim, self._codim)
        strategy_class = strategy_map.get(key)

        if strategy_class is None:
            raise NotImplementedError(
                f"No strategy implemented for dim={self._dim} and codim={self._codim}"
            )

        self._strategy = strategy_class(self._initPoints)

    def computeBary(self):
        """Computes the barycenter of the convex set of points.
        Delegates the computation to the currently selected strategy.

        Returns:
            numpy.ndarray: The coordinates of the barycenter.
        """
        return self._strategy.computeBary()

    def sortPoints(self):
        """Sorts the points of the convex set.
        Delegates the sorting operation to the selected strategy. The points
        are sorted only once.
        """
        if not self._pointSorted:
            self._strategy.sortPoints()
            self._pointSorted = True

    def computeArea(self):
        """Computes the area (or length for 1D) of the convex set.

        Delegates the area computation to the selected strategy.
        """
        return self._strategy.computeArea()

    def plotEdges(self, axis_, colorGiven, linestyleGiven, alphaGiven, dimSpace, label=None):
        """Plots the edges of the object as a closed polygon on the given axis.

        Arguments:
            axis_ (matplotlib.axes.Axes): The axis on which to plot.
            colorGiven (str): The color of the edges.
            linestyleGiven (str): The line style (e.g., '-', '--').
            alphaGiven (float): The transparency level (0.0 to 1.0).
            dimSpace (int): The dimensionality of the plotting space (2 or 3).
            label (str, optional): The label for the plot legend.

        .. warning::
            This function needs to be used in interactive mode in order to
            produce results (use plt.plot)
        """
        if not self._pointSorted:
            self.sortPoints()

        sorted_points = self._strategy.getSortedPoints()
        pointsPlot = np.vstack([sorted_points, sorted_points[0]])

        plot_args = {"color": colorGiven, "linestyle": linestyleGiven, "alpha": alphaGiven}
        if label:
            plot_args["label"] = label

        if dimSpace < 3:
            axis_.plot(pointsPlot[:, 0], pointsPlot[:, 1], **plot_args)
        else:
            axis_.plot(pointsPlot[:, 0], pointsPlot[:, 1], pointsPlot[:, 2], **plot_args)
