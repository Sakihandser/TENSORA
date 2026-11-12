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


import libaster
from ...Utilities import medcoupling as medc


def convertMesh2MedCoupling(asmesh, spacedim_3d=False):
    """Convert a *Mesh* into a MEDCoupling mesh.

    Arguments:
        asmesh (*Mesh*): Mesh object to be converted.
        spacedim_3d (*bool*): if true, space dimension of mc mesh is forced to 3

    Returns:
        *MEDCouplingMesh*: MEDCoupling object.
    """

    cells, groups_c, groups_n = libaster.getMedCouplingConversionData(asmesh)

    if spacedim_3d:
        spacedim = 3
    else:
        spacedim = asmesh.getDimension()

    mcmesh = medc.MEDFileUMesh()
    coords = medc.DataArrayDouble(
        asmesh.getCoordinates().getValues(), asmesh.getNumberOfNodes(), 3
    )[:, :spacedim]
    coords.setInfoOnComponents(["{} [INCONNU]".format(chr(ord("X") + i)) for i in range(spacedim)])

    maxdim = max(cells.keys())
    levels = {i: i - maxdim for i in range(maxdim, -1, -1)}

    # Creation du maillage par niveau, depart par le plus haut (0)
    for dim in sorted(cells.keys())[::-1]:

        mesh_at_current_level = medc.MEDCouplingUMesh(asmesh.getName(), dim)
        mesh_at_current_level.setCoords(coords)

        conn, connI, ids = cells[dim]
        mesh_at_current_level.setConnectivity(medc.DataArrayInt(conn), medc.DataArrayInt(connI))

        aster_ids_cur_dim = medc.DataArrayInt(ids)

        o2n = mesh_at_current_level.sortCellsInMEDFileFrmt()
        aster_ids_cur_dim.renumberInPlace(o2n)
        mesh_at_current_level.checkConsistencyLight()
        mcmesh.setMeshAtLevel(levels[dim], mesh_at_current_level)
        mcmesh.setRenumFieldArr(levels[dim], aster_ids_cur_dim)

        # Groupes de mailles
        try:
            groups_c_at_level = []
            for group_name, group_cells in groups_c[dim].items():
                group_medcoupling = medc.DataArrayInt(group_cells)
                group_medcoupling.transformWithIndArr(o2n)
                group_medcoupling.setName(group_name)
                groups_c_at_level.append(group_medcoupling)
            mcmesh.setGroupsAtLevel(levels[dim], groups_c_at_level)

        except KeyError:
            # Pas de groupes à ce niveau
            pass

    # Groupes de noeuds au niveau 1
    groups_n_at_level = []
    for group_name, group_nodes in groups_n.items():
        group_medcoupling = medc.DataArrayInt(group_nodes)
        group_medcoupling.setName(group_name)
        groups_n_at_level.append(group_medcoupling)
    mcmesh.setGroupsAtLevel(1, groups_n_at_level)

    mcmesh.setName(asmesh.getName())
    mcmesh.rearrangeFamilies()

    return mcmesh
