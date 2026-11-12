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

from ..Utilities import no_new_attributes

from ..Objects import Mesh
from ..Utilities import medcoupling as medc


class CreaGrille:
    """Add SEG2 and POI1 to the mesh for RIGI_GRILLE"""

    _distance = _prefixe = _coor_centre = None
    _nb_dofs = _mcmesh = _dim = _group_ma = _group_nodes = None
    _nb_nodes = _nb_cells_1d = _nb_cells_0d = None
    _seg2_nodes = _poi1_nodes = None

    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, **args):
        mesh = args["MAILLAGE"]
        group_ma = args["GROUP_MA"]
        self._distance = args["DISTANCE"]
        self._prefixe = args["PREFIXE"]
        self._coor_centre = args.get("COOR_CENTRE", None)

        self._nb_dofs = len(self._prefixe)
        self._mcmesh = mesh.createMedCouplingMesh(True)
        self._dim = self._mcmesh.getMeshDimension()

        levels = self._mcmesh.getNonEmptyLevels()
        if (2 - self._dim) not in levels or group_ma not in self._mcmesh.getGroupsOnSpecifiedLev(
            2 - self._dim
        ):
            raise Exception(f"The surface group {group_ma} is not found")

        self._group_ma = self._mcmesh.getGroup(2 - self._dim, group_ma)
        self._group_nodes = self._group_ma.computeFetchedNodeIds()
        self._nb_nodes = self._mcmesh.getNumberOfNodes()
        if (1 - self._dim) in levels:
            self._nb_cells_1d = self._mcmesh.getNumberOfCellsAtLevel(1 - self._dim)
        else:
            self._nb_cells_1d = 0
        if (0 - self._dim) in levels:
            self._nb_cells_0d = self._mcmesh.getNumberOfCellsAtLevel(0 - self._dim)
        else:
            self._nb_cells_0d = 0

        # pour les SEG2
        self._seg2_nodes = medc.DataArrayInt(len(self._group_nodes) * self._nb_dofs + self._nb_dofs)
        self._seg2_nodes.iota()
        self._seg2_nodes += self._nb_nodes
        # pour les POI1
        self._poi1_nodes = medc.DataArrayInt(self._nb_dofs)
        self._poi1_nodes.iota()
        self._poi1_nodes += self._nb_nodes + len(self._seg2_nodes)

    def _get_coords(self):
        """Return coordinates as DataArrayDouble
        * add of coordinates of nodes for raideurs SEG2
        * add of coordinates of nodes for centers POI1 and SEG2"""

        # pour les seg2
        coords = self._mcmesh.getCoords()
        group_coords = coords[self._group_nodes]
        group_coords[:, 2] -= self._distance

        # pour les poi1
        if self._coor_centre is not None:
            center = medc.DataArrayDouble([self._coor_centre])
        else:
            barycenters = self._group_ma.computeCellCenterOfMass()
            areas = self._group_ma.getMeasureField(True).getArray()
            center = (
                medc.DataArrayDouble([(barycenters * areas).accumulate()]) / areas.accumulate()[0]
            )
            center[:, 2] -= self._distance
        center2 = center.deepCopy()
        center2[:, 2] -= self._distance

        return medc.DataArrayDouble.Aggregate(
            [coords]
            + [group_coords] * self._nb_dofs
            + [center2] * self._nb_dofs
            + [center] * self._nb_dofs
        )

    def _get_node_groups(self):
        """return the node groups
        * add groups with prefix+"_RESSORT" for the SEG2 stiffness
        * add groups with prefix+"_CENTRE2" for the SEG2 centers
        * add groups with prefix+"_CENTRE" for the POI1 centers
        """
        groups = [
            self._mcmesh.getGroupArr(1, name) for name in self._mcmesh.getGroupsOnSpecifiedLev(1)
        ]
        for i_dof, prefix in enumerate(self._prefixe):
            group = self._seg2_nodes[
                i_dof * len(self._group_nodes) : (i_dof + 1) * len(self._group_nodes)
            ]
            group.setName(prefix + "_RESSORT")
            groups.append(group)
            group = self._seg2_nodes[
                self._nb_dofs * len(self._group_nodes)
                + i_dof : self._nb_dofs * len(self._group_nodes)
                + i_dof
                + 1
            ]
            print(group)
            group.setName(prefix + "_CENTRE2")
            groups.append(group)
            group = self._poi1_nodes[i_dof : i_dof + 1]
            group.setName(prefix + "_CENTRE")
            groups.append(group)
        return groups

    def _get_connectivity_1d(self, mcmesh_level):
        """Return connectivity (connect, connectI) for 1D mesh as DataArrayDouble, add of SEG2"""
        connect = mcmesh_level.getNodalConnectivity()
        new_connect = medc.DataArrayInt()
        new_connect.alloc(len(self._seg2_nodes), 3)
        new_connect[:, 0] = medc.NORM_SEG2
        new_connect[:, 1] = self._seg2_nodes
        new_connect[:, 2] = medc.DataArrayInt.Aggregate(
            [self._group_nodes] * self._nb_dofs + [self._poi1_nodes]
        )
        new_connect.rearrange(1)
        connect = medc.DataArrayInt.Aggregate([connect, new_connect])

        connectI = mcmesh_level.getNodalConnectivityIndex()
        if connectI is None:
            connectI = medc.DataArrayInt([0])
        new_connectI = medc.DataArrayInt(len(self._seg2_nodes))
        new_connectI.iota()
        new_connectI *= 3
        new_connectI += connectI[-1] + 3
        connectI = medc.DataArrayInt.Aggregate([connectI, new_connectI])

        return connect, connectI

    def _get_1d_groups(self):
        """return the 1D groups, add groups with prefix+"_RESSORT" and prefix+"_CENTRE2" """
        if self._nb_cells_1d:
            groups = [
                self._mcmesh.getGroupArr(1 - self._dim, name)
                for name in self._mcmesh.getGroupsOnSpecifiedLev(1 - self._dim)
            ]
        else:
            groups = []
        for i_dof, prefix in enumerate(self._prefixe):
            group = medc.DataArrayInt(len(self._group_nodes))
            group.iota()
            group += self._nb_cells_1d + i_dof * len(self._group_nodes)
            group.setName(prefix + "_RESSORT")
            groups.append(group)
        for i_dof, prefix in enumerate(self._prefixe):
            group = medc.DataArrayInt(1)
            group[0] = self._nb_cells_1d + self._nb_dofs * len(self._group_nodes) + i_dof
            group.setName(prefix + "_CENTRE2")
            groups.append(group)
        return groups

    def _get_connectivity_0d(self, mcmesh_level):
        """Return connectivity (connect, connectI) for 0D mesh as DataArrayDouble, add of POI1"""
        connect = mcmesh_level.getNodalConnectivity()
        new_connect = medc.DataArrayInt()
        new_connect.alloc(len(self._poi1_nodes), 2)
        new_connect[:, 0] = medc.NORM_POINT1
        new_connect[:, 1] = self._poi1_nodes
        new_connect.rearrange(1)
        connect = medc.DataArrayInt.Aggregate([connect, new_connect])

        connectI = mcmesh_level.getNodalConnectivityIndex()
        if connectI is None:
            connectI = medc.DataArrayInt([0])
        new_connectI = medc.DataArrayInt(len(self._poi1_nodes))
        new_connectI.iota()
        new_connectI *= 2
        new_connectI += connectI[-1] + 2
        connectI = medc.DataArrayInt.Aggregate([connectI, new_connectI])

        return connect, connectI

    def _get_0d_groups(self):
        """return the 0D groups, add groups with prefix+"_CENTRE" """
        if self._nb_cells_0d:
            groups = [
                self._mcmesh.getGroupArr(0 - self._dim, name)
                for name in self._mcmesh.getGroupsOnSpecifiedLev(0 - self._dim)
            ]
        else:
            groups = []
        for i_dof, prefix in enumerate(self._prefixe):
            group = medc.DataArrayInt(1)
            group[0] = self._nb_cells_0d + i_dof
            group.setName(prefix + "_CENTRE")
            groups.append(group)
        return groups

    def get(self):
        """return the Mesh with added SEG2 and POI1"""

        # NODES
        coords = self._get_coords()
        groups = self._get_node_groups()
        self._mcmesh.setCoords(coords)
        self._mcmesh.setGroupsAtLevel(1, groups)

        # SEG2
        if self._nb_cells_1d:
            mcmesh_level = self._mcmesh.getMeshAtLevel(1 - self._dim)
        else:
            mcmesh_level = medc.MEDCouplingUMesh.New()
            mcmesh_level.setMeshDimension(1)
        connect, connectI = self._get_connectivity_1d(mcmesh_level)
        mcmesh_level.setConnectivity(connect, connectI)
        mcmesh_level.setCoords(coords)
        mcmesh_level.checkConsistencyLight()
        groups = self._get_1d_groups()

        self._mcmesh.setMeshAtLevel(1 - self._dim, mcmesh_level)
        self._mcmesh.setGroupsAtLevel(1 - self._dim, groups)

        # POI1
        if self._nb_cells_0d:
            mcmesh_level = self._mcmesh.getMeshAtLevel(0 - self._dim)
        else:
            mcmesh_level = medc.MEDCouplingUMesh.New()
            mcmesh_level.setMeshDimension(0)
        connect, connectI = self._get_connectivity_0d(mcmesh_level)
        mcmesh_level.setConnectivity(connect, connectI)
        mcmesh_level.setCoords(coords)
        mcmesh_level.checkConsistencyLight()
        groups = self._get_0d_groups()

        self._mcmesh.setMeshAtLevel(0 - self._dim, mcmesh_level)
        self._mcmesh.setGroupsAtLevel(0 - self._dim, groups)

        mesh = Mesh()
        mesh.buildFromMedCouplingMesh(self._mcmesh)
        return mesh


def crea_grille_ops(self, **args):
    return CreaGrille(**args).get()
