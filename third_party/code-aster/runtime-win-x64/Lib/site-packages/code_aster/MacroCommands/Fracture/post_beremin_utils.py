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
Outils d'interpolation en correction de fonctionnalités incomplètes de medcoupling
"""
import numpy as np

from ...Utilities import logger
from ...Utilities import medcoupling as medc
from ...Messages import UTMESS


class CellToPoints:
    """
    GetCellsContainingPoints may fail in the presence of non-planar faces.
    We propose here a robust strategy to transition from P0 values (on cells)
    to a point cloud. At each point, we retain the field value in the cell to
    which the point belongs. If the point belongs to multiple cells (precision),
    we take the arithmetic mean of the concerned cells. Note that precision is
    understood as a relative value: multiplied by the size of the bounding box
    of the cell, it provides the (absolute) radius of the ball for cell
    detection or relative. If the point does not belong to any cell,
    we try to increase this precision. If no cell is found, an error is thrown"""

    def __init__(self, mesh_3D, mesh_2D, prec_rel, d_max_3d, ampl=1.5):
        """
        Args:
            mesh_3D(*UMesh*): 3D cell mesh (the one on which the fields to be projected will also be defined)
            mesh_2D(*UMesh*): 2D mesh on which the fields will be projected
            prec_rel(float): minimum relative precision with respect to the mesh size of the 2D mesh
            d_max_3d(float): maximum size of 3D elements
            ampl(float): amplification factor of the precision when no cells corresponding to a point are found
        """

        self.mesh = mesh_3D
        self.coor = mesh_2D.computeIsoBarycenterOfNodesPerCell()
        self.nbr = len(self.coor)

        self.prec = None
        self.cells = None
        self.pos = None
        self.pt_idx = None

        self.ComputeRelativePrecision(mesh_2D, prec_rel, d_max_3d)
        self.Build(ampl)

    def ComputeRelativePrecision(self, mesh_2D, prec_rel, d_max_3D):
        """
        Estimates the relative precision of identifying cells corresponding to points
        based on the size of the 2D mesh and the relative precision provided as input

        Args:
            mesh_2D(*UMesh*): 2D mesh on which the fields will be projected
            prec_rel(float): minimum relative precision with respect to the mesh size of the 2D mesh
            d_max_3d(float): maximum size of 3D elements
        """
        prec_abs = prec_rel * mesh_2D.computeDiameterField().getArray().getMinValueInArray()
        self.prec = prec_abs / d_max_3D

    def Build(self, ampl):
        """
        Construction of the projector, i.e., the link point -> corresponding cells
        Identical to GetCellsContainingPoints but more robust in terms of precision
        because we progressively increase (ampl factor) the precision (at most 5 times)

        """

        # ------------------------------------------------------------------------------------------
        # 1 - The mesh supporting the field is divided into tetrahedra.
        # ------------------------------------------------------------------------------------------

        meshT4 = self.mesh.deepCopy()

        if not meshT4.getAllGeoTypes() == [medc.NORM_TETRA4]:
            (meshT4, transfer, ibid) = meshT4.tetrahedrize(medc.PLANAR_FACE_6)  # non conformal mesh
        else:
            transfer = medc.DataArrayInt(np.arange(meshT4.getNumberOfCells()).tolist())
        meshT4 = meshT4.buildUnstructured()  # Bug medcoupling otherwise

        # ------------------------------------------------------------------------------------------
        # 2- We identify the T4 cells containing the points with a progressive increase in precision (5 times at most)
        # ------------------------------------------------------------------------------------------

        prec = self.prec
        pt_idx_inv = medc.DataArrayInt([])
        cells = medc.DataArrayInt([])
        pos = medc.DataArrayInt([0])
        nook_idx = medc.DataArrayInt(np.arange(self.nbr).tolist())

        # loop on precision
        nb_iter = 0
        while 1:

            logger.info("Construction du projecteur : itération " + str(nb_iter))
            logger.info(
                "Precision courante = précision initiale multiplée par " + str(1.5**nb_iter)
            )

            coor_nook = self.coor[nook_idx].toNumPyArray().ravel().tolist()
            (cells_prec, pos_prec) = meshT4.getCellsContainingPoints(coor_nook, prec)
            nbCells = pos_prec[1:] - pos_prec[:-1]

            # Amplification of precision
            prec = ampl * prec
            nb_iter += 1

            # nb_iter max = 5
            if nb_iter > 5:
                UTMESS("F", "RUPTURE4_23")

            # If there are no new OK points, we continue with degraded precision.
            if nbCells.getMaxValueInArray() == 0:
                continue

            # Index of new points for which cells are identified
            found = nbCells.findIdsNotEqual(0)
            ok_idx = nook_idx[found]
            logger.info("On a trouvé " + str(len(ok_idx)) + str(" nouveaux points."))
            logger.info("")
            # Concatenation of points and cells
            pt_idx_inv.aggregate(ok_idx)
            pos = pos[:-1]
            pos.aggregate(pos_prec[found] + len(cells))
            cells.aggregate(cells_prec)
            pos.aggregate(medc.DataArrayInt([len(cells)]))

            # Have all points found their corresponding cells?
            if nbCells.getMinValueInArray() > 0:
                break

            # Residual points that still have not found their corresponding cells
            notFound = nbCells.findIdsEqual(0)
            nook_idx = nook_idx[notFound]
            logger.info("Il reste " + str(len(nook_idx)) + str(" points à trouver."))
            logger.info("")

        if nb_iter > 1:
            UTMESS("A", "RUPTURE4_22")

        # Swapping the indexing of points: user point number -> projector point number
        self.pt_idx = medc.DataArrayInt([-1] * self.nbr)
        self.pt_idx[pt_idx_inv] = medc.DataArrayInt(np.arange(self.nbr).tolist())

        # Original mesh cells for each of the points
        self.cells = transfer[cells]
        self.pos = pos

        # Verifications
        assert (
            self.pos[1:] - self.pos[:-1]
        ).getMinValueInArray() > 0  # on a bien trouvé au moins une cellule pour chaque point
        assert len(self.pos) == self.nbr + 1

    def Eval(self, fieldValues):
        """
        Evaluation of the scalar field P0 on the sampling points (a DataArrayDouble)
        """

        # Weighting coefficient specific to each cell
        nbCells = self.pos[1:] - self.pos[:-1]
        weights = medc.DataArrayDouble((1.0 / nbCells.toNumPyArray()).tolist())

        # Calculation of arithmetic means in the projector's specific point numbering
        offset = 0
        values = medc.DataArrayDouble(self.nbr, fieldValues.getNumberOfComponents())
        values.fillWithValue(0.0)

        while nbCells.getMaxValueInArray() > 0:
            # Points for which cells still need to be calculated
            active_idx = nbCells.findIdsGreaterOrEqualTo(1)

            # Contribution of the current cells to the average
            cells = self.cells[self.pos[active_idx] + offset]
            values[active_idx] = values[active_idx] + weights[active_idx] * fieldValues[cells]

            # Preparation of pointers for the following terms
            nbCells = nbCells - 1
            offset += 1

        # Indexing of values in the user's numbering
        values = values[self.pt_idx]

        return values


def create_mesh_from_groupno(mesh_3D, group_no):
    """Create a 2D mesh object from a 3D mesh and a GROUP_NO"""

    logger.info("Création du maillage 2D sur la base du GROUP_NO " + str(group_no))

    mc_mesh_3D = mesh_3D.createMedCouplingMesh()

    ##Restrict medcoupling mesh to 2D faces
    a_group_no = mc_mesh_3D.getNodeGroupArr(group_no)
    mc_mesh_2D = mc_mesh_3D.getMeshAtLevel(0).buildFacePartOfMySelfNode(a_group_no, fullyIn=True)

    return mc_mesh_2D
