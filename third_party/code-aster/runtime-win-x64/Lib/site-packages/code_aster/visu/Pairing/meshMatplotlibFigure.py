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
from .convexPointSet import ConvexPointSet
import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import Optional
from abc import ABC, abstractmethod
from ...Utilities import no_new_attributes

try:
    import matplotlib

    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt

    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

DEFAULT_FIGURE_SIZE = (11, 9)
DEFAULT_TICKS_SIZE = 12


## -----------------------------------------------------------
#   OPTION AVAILABLE FOR THE VISUALISATION
## -----------------------------------------------------------
# - Enum definition of the options
class OptionMesh(str, Enum):
    """Main options for mesh visualization."""

    DOMAIN = "domain"
    INTERFACE = "interface"
    SELECT_SLV_CELL = "selectSlvCell"


class SubOptionMesh(str, Enum):
    """Sub-options for visualization, specifying the scope."""

    ALL = "all"
    GIVEN_PAIR = "givenPair"
    GIVEN_SLV_INDEX = "givenSlvIndex"


class OptionPair(str, Enum):
    """Rendering options for master/slave cell pairs."""

    MESH_ONLY = "meshOnly"
    PAIRS = "pairs"
    INTE_POINTS = "intePoints"
    QUAD_POINTS = "quadPoints"


class IndexPlane(str, Enum):
    """Projection axes for 3D visualization."""

    X = "X"
    Y = "Y"
    Z = "Z"


OPTION_PAIRING_VISU = {p for p in OptionPair}
OPTION_PAIRING_VISU_DETAILS = OPTION_PAIRING_VISU - {OptionPair.MESH_ONLY}

# - Options developped for now in the module
VALID_COMBINATIONS = {
    # - 2D Cases
    (2, OptionMesh.DOMAIN, SubOptionMesh.ALL): OPTION_PAIRING_VISU,
    (2, OptionMesh.DOMAIN, SubOptionMesh.GIVEN_PAIR): OPTION_PAIRING_VISU_DETAILS,
    (2, OptionMesh.DOMAIN, SubOptionMesh.GIVEN_SLV_INDEX): OPTION_PAIRING_VISU_DETAILS,
    (2, OptionMesh.INTERFACE, SubOptionMesh.ALL): OPTION_PAIRING_VISU,
    (2, OptionMesh.INTERFACE, SubOptionMesh.GIVEN_PAIR): OPTION_PAIRING_VISU_DETAILS,
    (2, OptionMesh.INTERFACE, SubOptionMesh.GIVEN_SLV_INDEX): OPTION_PAIRING_VISU_DETAILS,
    (2, OptionMesh.SELECT_SLV_CELL, SubOptionMesh.GIVEN_SLV_INDEX): OPTION_PAIRING_VISU_DETAILS,
    # - 3D Cases
    (3, OptionMesh.INTERFACE, SubOptionMesh.ALL): OPTION_PAIRING_VISU,
    (3, OptionMesh.INTERFACE, SubOptionMesh.GIVEN_PAIR): OPTION_PAIRING_VISU_DETAILS,
    (3, OptionMesh.INTERFACE, SubOptionMesh.GIVEN_SLV_INDEX): OPTION_PAIRING_VISU_DETAILS,
    (3, OptionMesh.SELECT_SLV_CELL, SubOptionMesh.GIVEN_SLV_INDEX): OPTION_PAIRING_VISU_DETAILS,
}


@dataclass(frozen=True)
class PlotConfig:
    """
    Groups and validates all plot configuration options.

    This dataclass ensures that only valid configuration states can be created.

    Attributes:
        dimMatPlot (int): The dimension of the plot (2 or 3).
        optionMesh (OptionMesh): The main mesh option.
        suboptionMesh (SubOptionMesh): The mesh sub-option.
        optionPair (OptionPair): The pair rendering option.
        addNodeLabel (bool): If True, display node labels.
        addMeshNodes (bool): If True, display mesh nodes.
        addLegend (bool): If True, display the legend.
        index (Optional[int]): Required index for certain sub-options (e.g., GIVEN_PAIR).
        indexPlaneProjected (Optional[IndexPlane]): The plane for 3D projection.
    """

    dimMatPlot: int
    optionMesh: OptionMesh
    suboptionMesh: SubOptionMesh
    optionPair: OptionPair
    addNodeLabel: bool = False
    addMeshNodes: bool = False
    addLegend: bool = True
    index: Optional[int] = None
    indexPlaneProjected: Optional[IndexPlane] = None

    def __post_init__(self):
        """
        Validation method called automatically after initialization.

        Raises:
            ValueError: If the configuration (PlotConfig object) is invalid.
        """
        key = (self.dimMatPlot, self.optionMesh, self.suboptionMesh)
        valid_pairing_options = VALID_COMBINATIONS.get(key)

        if valid_pairing_options is None:
            raise ValueError(
                f"The combination (dim={self.dimMatPlot}, optionMesh='{self.optionMesh.value}', "
                f"suboptionMesh='{self.suboptionMesh.value}') is not supported."
            )

        if self.optionPair not in valid_pairing_options:
            raise ValueError(
                f"The render option '{self.optionPair.value}' is not valid for the combination "
                f"(dim={self.dimMatPlot}, optionMesh='{self.optionMesh.value}', suboptionMesh='{self.suboptionMesh.value}').\n"
                f"Valid options are: {[opt.value for opt in valid_pairing_options]}"
            )

        if (
            self.suboptionMesh in {SubOptionMesh.GIVEN_PAIR, SubOptionMesh.GIVEN_SLV_INDEX}
            and self.index is None
        ):
            raise ValueError(
                f"The 'index' argument is required when suboptionMesh is "
                f"'{SubOptionMesh.GIVEN_PAIR.value}' or '{SubOptionMesh.GIVEN_SLV_INDEX.value}'."
            )


## -----------------------------------------------------------
#   PLOTTING STRATEGIES DIFFERENT ACCORDING TO THE DATASTRUCTURE
## -----------------------------------------------------------


class PlottingStrategy(ABC):
    """Abstract base class for a plotting strategy."""

    _ax = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, ax=None):
        """Initializes the plotting strategy.

        Arguments:
            ax (Optional[plt.Axes]): The matplotlib axes object to draw on.
        """
        self._ax = ax

    @abstractmethod
    def generateAxis(self):
        """Generates and returns the figure and axis objects."""
        pass

    @abstractmethod
    def scatter(self, coords, color, s, marker="o"):
        """Draws scatter points.

        Arguments:
            coords (np.ndarray): The coordinates of the points.
            color (str): The color of the points.
            s (int): The marker size.
            marker (str): The marker style.
        """
        pass

    @abstractmethod
    def text(self, coords, label, color):
        """Draws text labels.

        Arguments:
            coords (np.ndarray): The coordinates of the text label.
            label (str): The text content of the label.
            color (str): The color of the text.
        """
        pass

    @abstractmethod
    def plotEdges(self, cell, color, linestyle, alpha, label):
        """Plots the edges of a given cell object.

        Arguments:
            cell (Any): The cell object with a `plotEdges` method.
            color (str): The color of the edges.
            linestyle (str): The line style of the edges.
            alpha (float): The transparency of the edges.
            label (str): The label for the legend.
        """
        pass

    @abstractmethod
    def plotLine(self, start_coords, end_coords, color, linestyle):
        """Draws a single line between two points.

        Arguments:
            start_coords (np.ndarray): The starting point coordinates.
            end_coords (np.ndarray): The ending point coordinates.
            color (str): The color of the line.
            linestyle (str): The style of the line.
        """
        pass


class PlottingStrategy2D(PlottingStrategy):
    """Plotting strategy for 2D geometries."""

    def generateAxis(self):
        fig, ax = plt.subplots(figsize=DEFAULT_FIGURE_SIZE)
        ax.tick_params(axis="both", labelsize=DEFAULT_TICKS_SIZE)
        self._ax = ax
        return fig, ax

    def scatter(self, coords, color, s, marker="o"):
        self._ax.scatter(coords[:, 0], coords[:, 1], color=color, s=s, marker=marker)

    def text(self, coords, label, color):
        factor = 1.01
        self._ax.text(
            factor * coords[0], factor * coords[1], f"{label}", size=15, zorder=2, color=color
        )

    def plotEdges(self, cell, color, linestyle, alpha, label):
        """Plots the 2D edges of a cell.

        Arguments:
            cell (Any): The cell object with a `plotEdges` method.
            color (str): The color of the edges.
            linestyle (str): The line style of the edges.
            alpha (float): The transparency of the edges.
            label (str): The label for the legend.
        """
        cell.plotEdges(self._ax, color, linestyle, alpha, 2, label)

    def plotLine(self, start_coords, end_coords, color, linestyle):
        self._ax.plot(
            [start_coords[0], end_coords[0]],
            [start_coords[1], end_coords[1]],
            color=color,
            linestyle=linestyle,
        )


class PlottingStrategy3D(PlottingStrategy):
    """Plotting strategy for 3D geometries."""

    def generateAxis(self):
        """
        Generates a 3D interactive axis.

        This implementation creates a matplotlib axis with a '3d' projection
        and enables interactive mode (`plt.ion()`).
        """
        plt.ion()
        fig = plt.figure(figsize=DEFAULT_FIGURE_SIZE)
        ax = plt.axes(projection="3d")
        ax.tick_params(axis="both", labelsize=DEFAULT_TICKS_SIZE)
        self._ax = ax
        return fig, ax

    def scatter(self, coords, color, s, marker="o"):
        self._ax.scatter(coords[:, 0], coords[:, 1], coords[:, 2], color=color, s=s, marker=marker)

    def text(self, coords, label, color):
        factor = 1.01
        self._ax.text(
            factor * coords[0],
            factor * coords[1],
            factor * coords[2],
            f"{label}",
            size=15,
            zorder=2,
            color=color,
        )

    def plotEdges(self, cell, color, linestyle, alpha, label):
        """
        Plots the 3D edges of a cell.

        Arguments:
            cell (Any): The cell object with a `plotEdges` method.
            color (str): The color of the edges.
            linestyle (str): The line style of the edges.
            alpha (float): The transparency of the edges.
            label (str): The label for the legend.
        """
        cell.plotEdges(self._ax, color, linestyle, alpha, 3, label)

    def plotLine(self, start_coords, end_coords, color, linestyle):
        self._ax.plot(
            [start_coords[0], end_coords[0]],
            [start_coords[1], end_coords[1]],
            [start_coords[2], end_coords[2]],
            color=color,
            linestyle=linestyle,
        )


class PlottingStrategy3DProjected(PlottingStrategy):
    """Plotting strategy for 3D geometries by projection onto a 2D plane."""

    _index_ppx = _index_ppy = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, index_ppx, index_ppy):
        """
        Initializes the 3D projected plotting strategy.

        The behavior of all plotting methods will depend on the indices provided
        here to project 3D coordinates onto a 2D plane.

        Arguments:
            projection_axis_x_idx (int): Index of the 3D coordinate for the plane's X-axis (0, 1, or 2).
            projection_axis_y_idx (int): Index of the 3D coordinate for the plane's Y-axis (0, 1, or 2).
        """
        super().__init__()
        self._index_ppx = index_ppx
        self._index_ppy = index_ppy

    def generateAxis(self):
        """Generates a 2D axis for the projected plot."""
        fig, ax = plt.subplots(figsize=DEFAULT_FIGURE_SIZE)
        ax.tick_params(axis="both", labelsize=DEFAULT_TICKS_SIZE)
        ax.set_aspect("equal", adjustable="box")
        self._ax = ax
        return fig, ax

    def scatter(self, coords, color, s, marker="o"):
        """
        Draws a 2D scatter plot of projected 3D coordinates.

        Arguments:
            coords (np.ndarray): The 3D coordinates of the points.
            color (str): The color of the points.
            s (int): The marker size.
            marker (str): The marker style.
        """
        self._ax.scatter(
            coords[:, self._index_ppx], coords[:, self._index_ppy], color=color, s=s, marker=marker
        )

    def text(self, coords, label, color):
        """
        Draws a text label at a projected 3D coordinate.

        Arguments:
            coords (np.ndarray): The 3D coordinates of the text label.
            label (str): The text content of the label.
            color (str): The color of the text.
        """
        factor = 1.01
        self._ax.text(
            factor * coords[self._index_ppx],
            factor * coords[self._index_ppy],
            f"{label}",
            size=15,
            zorder=2,
            color=color,
        )

    def plotEdges(self, cell, color, linestyle, alpha, label):
        """
        Plots the projected 2D edges of a cell.

        Arguments:
            cell (Any): The cell object with a `plotEdges` method.
            color (str): The color of the edges.
            linestyle (str): The line style of the edges.
            alpha (float): The transparency of the edges.
            label (str): The label for the legend.
        """
        cell.plotEdges(self._ax, color, linestyle, alpha, 2, label)

    def plotLine(self, start_coords, end_coords, color, linestyle):
        """
        Draws a 2D line between two projected 3D points.

        Arguments:
            start_coords (np.ndarray): The starting 3D point coordinates.
            end_coords (np.ndarray): The ending 3D point coordinates.
            color (str): The color of the line.
            linestyle (str): The style of the line.
        """
        self._ax.plot(
            [start_coords[self._index_ppx], end_coords[self._index_ppx]],
            [start_coords[self._index_ppy], end_coords[self._index_ppy]],
            color=color,
            linestyle=linestyle,
        )


## -----------------------------------------------------------
#   CLASS MESH MATPLOTLIB FIGURE
## -----------------------------------------------------------
class MeshMatplotlibFigure:
    """
    Class to generate a Matplotlib figure based on a validated PlotConfig.
    """

    _pairingAnalysis = _config = _strategy = None
    _dim = _codim = None
    _indexPPx = _indexPPy = _indexPPz = None
    _fig = _ax = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, pairingAnalysisInstance, config: PlotConfig):
        """
        Constructor

        Arguments
        ---------
        pairingAnalysisInstance : PairingObject
            Previously computed AsterPairingProcess object.

        config: PlotConfig
            A valid plot configuration object
        """
        self._pairingAnalysis = pairingAnalysisInstance
        self._config = config

        # - Create the right plotting strategy
        self._strategy = self.createPlottingStrategy()

        # - Initialize variables
        self._dim = None
        self._codim = None
        self._indexPPx, self._indexPPy, self._indexPPz = None, None, None

        # - Compute information (geometry and index for the arrays)
        self.computeDimCodim()
        self.setIndicesProjected()

        # - Initialize attributes for the figure
        self._fig = None
        self._ax = None

    def createPlottingStrategy(self):
        """Factory method to create the appropriate plotting strategy."""
        dim = self._config.dimMatPlot
        plane = self._config.indexPlaneProjected

        if dim == 2:
            return PlottingStrategy2D()
        elif dim == 3:
            if plane is None:
                return PlottingStrategy3D()
            else:
                indices = {"X": (1, 2), "Y": (0, 2), "Z": (0, 1)}
                idx_x, idx_y = indices[plane.value]
                return PlottingStrategy3DProjected(idx_x, idx_y)
        else:
            raise ValueError(f"Plotting dimension {dim} is not supported.")

    def computeDimCodim(self):
        """Method to compute dimension and codimension."""
        if self._config.optionMesh == OptionMesh.DOMAIN:
            self._dim = self._config.dimMatPlot
            self._codim = 0
        elif self._config.optionMesh == OptionMesh.INTERFACE:
            self._dim = self._config.dimMatPlot
            self._codim = 1
        elif self._config.optionMesh == OptionMesh.SELECT_SLV_CELL:
            self._dim = self._config.dimMatPlot
            self._codim = 1

        print(f"Computed dim={self._dim}, codim={self._codim}")

    def setIndicesProjected(self):
        """
        Given the option provided, defines the coordinates to be selected
        for a 3D plot projected onto a plane.
        """
        plane = self._config.indexPlaneProjected

        if plane == IndexPlane.X:
            self._indexPPx, self._indexPPy, self._indexPPz = 1, 2, 0
        elif plane == IndexPlane.Y:
            self._indexPPx, self._indexPPy, self._indexPPz = 0, 2, 1
        elif plane == IndexPlane.Z:
            self._indexPPx, self._indexPPy, self._indexPPz = 0, 1, 2

        if plane:
            print(f"Projection indices set for plane '{plane.value}'.")

    ## - Plot methods call the right PlottingStrategy methods
    def _generateAxis(self):
        """Delegates axis generation to the current strategy."""
        self._fig, self._ax = self._strategy.generateAxis()

    def _addNodes(self, nodes_coords, color, s):
        """Delegates scatter plotting to the current strategy.

        Arguments:
            nodes_coords (np.ndarray): Array of node coordinates.
            color (str): The color for the nodes.
            s (int): The marker size for the nodes.
        """
        self._strategy.scatter(nodes_coords, color, s)

    def _addNodeLabels(self, node_coords, node_indices, color):
        """Delegates text plotting to the current strategy.

        Arguments:
            node_coords (np.ndarray): Array of node coordinates.
            node_indices (list[int]): List of integer indices for each node.
            color (str): The color for the text labels.
        """
        for i, node_index in enumerate(node_indices):
            self._strategy.text(node_coords[i], node_index, color)

    def _addEdges(self, cell_indices, color, linestyle, alpha, label_str):
        """Delegates edge plotting to the current strategy.

        Arguments:
            cell_indices (list[int]): List of cell indices to plot.
            color (str): The color for the edges.
            linestyle (str): The line style for the edges (e.g., '-', '--').
            alpha (float): The transparency of the lines.
            label_str (str): The label for the legend.
        """
        is_projected = isinstance(self._strategy, PlottingStrategy3DProjected)

        for i, index in enumerate(cell_indices):
            nodes, _ = self._pairingAnalysis.getNodesCoordsFromCellIndices([index])

            # - When projection is used, one should get the right coordinates
            if is_projected:
                indices_proj = [self._strategy._index_ppx, self._strategy._index_ppy]
                nodes_projected = np.zeros_like(nodes)
                nodes_projected[:, :2] = nodes[:, indices_proj]
                cell = ConvexPointSet(self._dim - self._codim, nodes_projected, 0)
            else:
                cell = ConvexPointSet(self._dim - self._codim, nodes, self._codim)

            label = label_str if self._config.addLegend and i == 0 else None
            self._strategy.plotEdges(cell, color, linestyle, alpha, label)

    def _set_legend(self):
        """Adds a legend to the figure if requested."""
        if self._config.addLegend:
            ncol = 4 if self._config.optionPair != OptionPair.MESH_ONLY else 2
            self._ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.1), ncol=ncol)

    ## - Plot method
    def plot(self, s=50):
        """Main plotting method. Acts as a dispatcher based on the configuration.

        Arguments:
            s (int): Base marker size for points.
        """
        if self._config.optionMesh == OptionMesh.SELECT_SLV_CELL:
            self._plotSelectSlaveCell(s)
            return

        if self._config.optionPair == OptionPair.MESH_ONLY:
            self._plotMeshOnly(s)
            return

        if self._config.suboptionMesh == SubOptionMesh.ALL:
            all_pairs = self._pairingAnalysis._listPairs
            for i in range(len(all_pairs)):
                self._drawFullPlotForOnePair(i, s)

        elif self._config.suboptionMesh == SubOptionMesh.GIVEN_PAIR:
            self._drawFullPlotForOnePair(self._config.index, s)

        elif self._config.suboptionMesh == SubOptionMesh.GIVEN_SLV_INDEX:
            slv_index = self._config.index
            for i, (pair_slv, _) in enumerate(self._pairingAnalysis._listPairs):
                if pair_slv == slv_index:
                    self._drawFullPlotForOnePair(i, s)

    def _plotMeshOnly(self, s):
        """Plots only the base mesh structure.

        Arguments:
            s (int): Base marker size for nodes if they are plotted.
        """
        self._generateAxis()
        plot_params = self._getPlotParams()
        self._plotMeshStructure(plot_params, s)
        self._set_legend()
        plt.show(block=True)

    def _drawFullPlotForOnePair(self, pair_index, s):
        """
        Worker method: Generates a complete plot for a single specified pair.
        This is the core logic reused by multiple dispatch methods.

        Arguments:
            pair_index (int): The index of the pair in `_pairingAnalysis._listPairs`.
            s (int): Base marker size for point
        """
        self._generateAxis()
        plot_params = self._getPlotParams()

        # - Plot basic structure
        self._plotMeshStructure(plot_params, s)

        # - Plot the specific pair
        pair_slv_ind, pair_mas_ind = self._pairingAnalysis._listPairs[pair_index]
        self._plotASinglePair(pair_slv_ind, pair_mas_ind, plot_params)

        # - Add intersection or quadrature points if needed
        if self._config.optionPair == OptionPair.INTE_POINTS:
            self._plotIntersectionPoints(pair_index, s)
        elif self._config.optionPair == OptionPair.QUAD_POINTS:
            self._plotQuadraturePoints(pair_index, int(s / 3))

        self._set_legend()
        plt.show(block=True)

    def _plotSelectSlaveCell(self, s):
        """
        Special case: plots only the cells involved in pairs with a given slave cell,
        without the rest of the mesh.

        Arguments:
            s (int): Base marker size for points.
        """
        self._generateAxis()
        plot_params = {
            "SlvInt": {"color": "blue", "linestyle": "--", "alpha": 0.25},
            "MasInt": {"color": "red", "linestyle": "--", "alpha": 0.25},
        }
        slv_index_to_find = self._config.index
        found_at_least_one = False

        for pair_index, (pair_slv_ind, pair_mas_ind) in enumerate(self._pairingAnalysis._listPairs):
            if pair_slv_ind == slv_index_to_find:
                found_at_least_one = True
                # - Plot pair
                self._plotASinglePair(pair_slv_ind, pair_mas_ind, plot_params)

                # - Add node and their labels if needed
                if self._config.addMeshNodes or self._config.addNodeLabel:
                    slv_coords, slv_node_idx = self._pairingAnalysis.getNodesCoordsFromCellIndices(
                        [pair_slv_ind]
                    )
                    mas_coords, mas_node_idx = self._pairingAnalysis.getNodesCoordsFromCellIndices(
                        [pair_mas_ind]
                    )
                    if self._config.addMeshNodes:
                        self._addNodes(slv_coords, "blue", s)
                        self._addNodes(mas_coords, "red", s)
                    if self._config.addNodeLabel:
                        self._addNodeLabels(slv_coords, slv_node_idx, "blue")
                        self._addNodeLabels(mas_coords, mas_node_idx, "red")

                # - Add intersection or quadrature points if needed
                if self._config.optionPair == OptionPair.INTE_POINTS:
                    self._plotIntersectionPoints(pair_index, s)
                elif self._config.optionPair == OptionPair.QUAD_POINTS:
                    self._plotQuadraturePoints(pair_index, int(s / 3))

        if found_at_least_one:
            self._set_legend()
            plt.show(block=True)
        else:
            print(f"Warning: No pairs found for slave cell index {slv_index_to_find}.")

    def _getPlotParams(self):
        """Determines the color and style parameters based on the configuration.

        Returns:
            dict: A dictionary containing style parameters like 'color',
                  'linestyle', and 'alpha' for different mesh components.
        """
        if self._config.optionPair == OptionPair.MESH_ONLY:
            return {
                "Slv": {"color": "blue", "linestyle": "-", "alpha": 1.0},
                "Mas": {"color": "red", "linestyle": "-", "alpha": 1.0},
            }
        else:
            return {
                "Slv": {"color": "blue", "linestyle": "-", "alpha": 0.15},
                "Mas": {"color": "red", "linestyle": "-", "alpha": 0.15},
                "SlvInt": {"color": "orange", "linestyle": "-", "alpha": 1.0},
                "MasInt": {"color": "green", "linestyle": "-", "alpha": 1.0},
            }

    def _plotMeshStructure(self, plot_params, s):
        """Plots the base mesh structure (slave and master cells).

        Arguments:
            plot_params (dict): A dictionary of styles.
            s (int): Marker size for nodes if they are plotted.
        """
        # - Get cell indices to plot
        if self._config.optionMesh == OptionMesh.DOMAIN:
            slv_indices = self._pairingAnalysis._indicesSlaveDomain
            mas_indices = self._pairingAnalysis._indicesMasterDomain
        elif self._config.optionMesh in {OptionMesh.INTERFACE, OptionMesh.SELECT_SLV_CELL}:
            slv_indices = self._pairingAnalysis._indicesSlaveInterface
            mas_indices = self._pairingAnalysis._indicesMasterInterface
        else:
            return

        # - Get the node coordinates
        nodes_slv_coords, nodes_slv_indices = self._pairingAnalysis.getNodesCoordsFromCellIndices(
            slv_indices
        )
        nodes_mas_coords, nodes_mas_indices = self._pairingAnalysis.getNodesCoordsFromCellIndices(
            mas_indices
        )

        # - Add node and their labels if needed
        if self._config.addMeshNodes:
            self._addNodes(nodes_slv_coords, plot_params["Slv"]["color"], s)
            self._addNodes(nodes_mas_coords, plot_params["Mas"]["color"], s)
        if self._config.addNodeLabel:
            self._addNodeLabels(nodes_slv_coords, nodes_slv_indices, plot_params["Slv"]["color"])
            self._addNodeLabels(nodes_mas_coords, nodes_mas_indices, plot_params["Mas"]["color"])

        # - Add edges of the mesh cells if needed
        self._addEdges(
            slv_indices,
            plot_params["Slv"]["color"],
            plot_params["Slv"]["linestyle"],
            plot_params["Slv"]["alpha"],
            "slave",
        )
        self._addEdges(
            mas_indices,
            plot_params["Mas"]["color"],
            plot_params["Mas"]["linestyle"],
            plot_params["Mas"]["alpha"],
            "master",
        )

    def _plotASinglePair(self, pair_slv_ind, pair_mas_ind, plot_params):
        """Plots a single slave/master pair.

        Arguments:
            pair_slv_ind (int): The index of the slave cell in the pair.
            pair_mas_ind (int): The index of the master cell in the pair.
            plot_params (dict): A dictionary of styles
        """
        self._addEdges(
            [pair_slv_ind],
            plot_params["SlvInt"]["color"],
            plot_params["SlvInt"]["linestyle"],
            plot_params["SlvInt"]["alpha"],
            f"cell={pair_slv_ind}",
        )
        self._addEdges(
            [pair_mas_ind],
            plot_params["MasInt"]["color"],
            plot_params["MasInt"]["linestyle"],
            plot_params["MasInt"]["alpha"],
            f"cell={pair_mas_ind}",
        )

    def _plotIntersectionPoints(self, pair_index, s):
        """Plots the intersection points for a given pair.

        Arguments:
            pair_index (int): The index of the pair.
            s (int): Marker size for the points.
        """
        inte_convex_set = np.array(self._pairingAnalysis._listIntersectionPts[pair_index])

        # - Plot the points (only)
        self._strategy.scatter(inte_convex_set, color="black", s=s)

        # - Plot edges for the intersection cells
        if isinstance(self._strategy, PlottingStrategy3DProjected):
            indices_proj = [self._strategy._index_ppx, self._strategy._index_ppy]
            nodes_projected = np.zeros_like(inte_convex_set)
            nodes_projected[:, :2] = inte_convex_set[:, indices_proj]
            cell = ConvexPointSet(self._dim - self._codim, nodes_projected, 0)
        else:
            cell = ConvexPointSet(self._dim - self._codim, inte_convex_set, self._codim)
        self._strategy.plotEdges(cell, "black", "-", 1.0, None)

    def _plotQuadraturePoints(self, pair_index, s):
        """
        Plots the quadrature points for a given pair, including the intersection
        boundary and lines to its barycenter.

        Arguments:
            pair_index (int): The index of the pair.
            s (int): Marker size for the points.
        """
        quad_points = np.array(self._pairingAnalysis._listQuadraturePts[pair_index])
        inte_convex_set_coords = np.array(self._pairingAnalysis._listIntersectionPts[pair_index])

        # - Plot the quadrature points
        self._strategy.scatter(quad_points, color="red", s=s, marker="x")

        # - Add some information to visualize the integration domain
        is_projected = isinstance(self._strategy, PlottingStrategy3DProjected)
        if is_projected:
            indices_proj = [self._strategy._index_ppx, self._strategy._index_ppy]
            nodes_projected = np.zeros_like(inte_convex_set_coords)
            nodes_projected[:, :2] = inte_convex_set_coords[:, indices_proj]
            cell = ConvexPointSet(self._dim - self._codim, nodes_projected, 0)
        else:
            cell = ConvexPointSet(self._dim - self._codim, inte_convex_set_coords, self._codim)

        barycenter = cell.computeBary()

        for vertex_coords in inte_convex_set_coords:
            self._strategy.plotLine(
                start_coords=vertex_coords, end_coords=barycenter, color="black", linestyle="dashed"
            )
