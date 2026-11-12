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
from ...Objects import MeshPairing
import os
import numpy as np
import pickle
from pathlib import Path
from libaster import Mesh, PairingMethod
from ...Utilities import no_new_attributes

## -----------------------------------------------------------
#   AVAILABLE METHODS FOR PAIRING AND MORTAR COMPUTATIONS
## -----------------------------------------------------------
AVAILABLE_PAIRING_METHODS = ["BrutForce", "Fast", "Legacy"]


class AsterPairingProcess:
    """
    Interfaces with code_aster to run the mesh pairing process.

    This class is the main entry point for a computation. It wraps the
    native code_aster methods..
    """

    _METHOD_MAP = {
        "BrutForce": PairingMethod.BrutForce,
        "Fast": PairingMethod.Fast,
        "Legacy": PairingMethod.Legacy,
    }

    _groupMaSlv = _groupMaMas = _asterMesh = _method = None
    _coords = _asterConnectivity = None
    _listPairs = _intePointsList = _quadPointsList = None
    _hasRun = None
    _meshPair = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, groupMaSlv, groupMaMas, asterMesh):
        """Constructor.

        Arguments:
            groupMaSlv (str): Name of the group of the contact slave interface.
            groupMaMas (str): Name of the group of the contact master interface.
            asterMesh (libaster.Mesh): aster Mesh considered for pairing.
        """
        self._checkConsistency(groupMaSlv, groupMaMas, asterMesh)
        self._groupMaSlv = groupMaSlv
        self._groupMaMas = groupMaMas
        self._asterMesh = asterMesh
        self._method = None
        # - datastructures initialize to None
        self._coords = None
        self._asterConnectivity = None
        self._listPairs = None
        self._intePointsList = None
        self._quadPointsList = None
        self._hasRun = False
        self._meshPair = None

    def _checkConsistency(self, groupMaSlv, groupMaMas, asterMesh):
        """Test the consistency of the provided arguments"""
        if not isinstance(groupMaSlv, str):
            raise TypeError(f"groupMaSlv must be a string, not {type(groupMaSlv).__name__}")
        if not isinstance(groupMaMas, str):
            raise TypeError(f"groupMaMas must be a string, not {type(groupMaMas).__name__}")
        if not isinstance(asterMesh, Mesh):
            raise TypeError(
                f"asterMesh must be a libaster.Mesh object, not {type(asterMesh).__name__}"
            )

    def setMethod(self, method="BrutForce"):
        """Choose the pairing method. Mandatory to run the computation.

        Arguments:
            method (str): Name of the pairing method used in `code_aster`.
                Should be chosen between BrutForce, Legacy, and Fast.
        """
        if method not in AVAILABLE_PAIRING_METHODS:
            raise ValueError(
                f"Method '{method}' not available. Choose from {AVAILABLE_PAIRING_METHODS}"
            )

        self._method = method
        self._hasRun = False  # the method has changed, then no pairing has been computed

    def computePairing(self):
        """Compute pairing procedure"""

        if self._method is None:
            raise NameError("No pairing method is set: use setMethod before")

        # - Set MeshPairing and compute pairing
        meshPair = MeshPairing()
        meshPair.setMesh(self._asterMesh)
        meshPair.setPair(self._groupMaSlv, self._groupMaMas)
        meshPair.setMethod(self._METHOD_MAP[self._method])
        meshPair.compute()
        # - Save MeshPairing
        self._meshPair = meshPair

    def _getPointsFromPairsList(self, getter_method_name):
        """Private helper to extract points (intersection or quadrature) for all pairs."""
        nbPairs = self._meshPair.getNumberOfPairs()
        points_list = []
        for iPair in range(nbPairs):
            # getattr permet d'appeler une méthode par son nom
            points = getattr(self._meshPair, getter_method_name)(iPair)
            points_current = [tuple(pt) for pt in points]
            points_list.append(points_current)
        return points_list

    def extractData(self):
        """Extract the list of pairs, the list of intersection points and the computed quadrature points coordinates.
        Store them within the datastructure"""
        if not self._hasRun:
            raise ValueError(
                "Cannot extract data before running the computation. Call run() first."
            )
        self._listPairs = self._meshPair.getListOfPairs()
        self._intePointsList = self._getPointsFromPairsList("getIntersectionPoints")
        self._quadPointsList = self._getPointsFromPairsList("getQuadraturePoints")

    def run(self):
        """Main method: compute the pairing and save the needed data"""
        # - Compute Pairing
        self.computePairing()
        # - Flag to show that one pairing process has been computed
        self._hasRun = True
        # - Extract available data
        self.extractData()

    def extractMeshInfosFromAsterMesh(self):
        """Extract the connecitivity and the node coordinates from the mesh"""
        # - get aster connectivity
        asterConnectivity = self._asterMesh.getConnectivity()
        nbNodes = self._asterMesh.getNumberOfNodes()
        # - get node coordinates for each cell
        coordsFull = self._asterMesh.getCoordinates().getValues()
        coords = np.reshape(coordsFull, (nbNodes, 3))
        # - Save data
        self._coords = coords
        self._asterConnectivity = asterConnectivity

    def computeIndicesMeshFromGroup(self, groupName):
        """Returns the indices of the cells belonging to a given group.

        Arguments:
            groupName (str): Name of the group.

        Returns:
            numpy.ndarray: List of the cells indices in the group.
        """
        return self._asterMesh.getCells(groupName)

    def _dumpPickle(self, data, filepath):
        """Private helper to dump data to a pickle file."""
        with open(filepath, "wb") as f:
            pickle.dump(data, f)

    def dumpDataGroupCells(self, groupName, repoSave, nameFile):
        """Dump the cell indices of a group in a given directory.

        Arguments:
            groupName (str): Name of the group in the considered mesh.
            repoSave (str): Name of the directory in which we want to save the file.
            nameFile (str): Name of the output file (without the .pkl extension).
        """
        indices = self.computeIndicesMeshFromGroup(groupName)
        save_path = Path(repoSave)
        save_path.mkdir(parents=True, exist_ok=True)
        self._dumpPickle(indices, save_path / f"{nameFile}.pkl")

    def dumpData(self, repoSave, pairData=True, meshData=True):
        """Dump the pairing data in a given directory.

        Arguments:
            repoSave (str): Path to the directory where the files will be saved.
            pairData (bool): If True, saves pairing data (pairs, points).
            meshData (bool): If True, saves mesh data (connectivity and node coordinates).
        """
        save_path = Path(repoSave)
        save_path.mkdir(parents=True, exist_ok=True)

        if meshData:
            if self._coords is None or self._asterConnectivity is None:
                raise ValueError(
                    "Mesh data not extracted. Call extractMeshInfosFromAsterMesh() first."
                )
            self._dump_pickle(self._coords, save_path / "coords.pkl")
            self._dump_pickle(self._asterConnectivity, save_path / "asterConnectivity.pkl")

        if pairData:
            if not self._hasRun:
                raise ValueError("Pairing data not computed. Call run() first.")
            if self._listPairs is not None:
                self._dump_pickle(self._listPairs, save_path / "listPairs.pkl")
            if self._intePointsList is not None:
                self._dump_pickle(self._intePointsList, save_path / "intePointsList.pkl")
            if self._quadPointsList is not None:
                self._dump_pickle(self._quadPointsList, save_path / "quadPointsList.pkl")
