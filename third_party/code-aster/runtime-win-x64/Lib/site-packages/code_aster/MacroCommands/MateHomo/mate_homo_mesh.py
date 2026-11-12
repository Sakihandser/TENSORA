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

from ...Messages import ASSERT, UTMESS
from ...Objects import Mesh
from ...Utilities import medcoupling as mc
from . import MESH_TOL


def prepare_mesh_syme(meshin, affe_groups, affe_all):
    """
    Prepare a new mesh for homogenisation computations.

    This function retains only the 3D part of the original mesh and its 3D
    groups. It creates a volume group 'BODY' from the list of user material
    prescriptions. Additionally, face groups are created as groups on the
    bounding box.

    Args:
        meshin (Mesh): The user-provided VER mesh.
        affe_groups (list): List of material prescriptions from the user
            command.
        affe_all (bool): True if TOUT='OUI' is used.
    Returns:
        Mesh: The internal VER mesh.
        str: The name of the volume group created.
        DataArrayInt: The volume of the VER mesh.
        DataArrayInt: The thickness of the mesh along plate direction.
    """

    ASSERT(len(affe_groups) > 0 or affe_all)

    m0full = meshin[0]

    body_groups = []

    if affe_all is True:
        body_groups.append(mc.DataArrayInt.Range(0, m0full.getNumberOfCells(), 1))

    else:
        # Les groupes de GROUP_MA doivent exister et leur intersection est vide
        for grp in affe_groups:
            if grp not in meshin.getGroupsOnSpecifiedLev(0):
                UTMESS("F", "HOMO1_4", valk=grp)

        intersection = mc.DataArrayInt.BuildIntersection(
            [meshin.getGroupArr(0, grp) for grp in affe_groups if len(affe_groups) > 1]
        )
        if not len(intersection) == 0:
            UTMESS("F", "HOMO1_5")

        for grp in affe_groups:
            body_groups.append(meshin.getGroupArr(0, grp))

    bodycells = mc.DataArrayInt.BuildUnion(body_groups)
    m0 = m0full[bodycells]
    m0.zipCoords()

    # Conservation de tous les groupes de volume sauf BODY et ajout du groupe bodycells
    group_tout = "BODY"
    preserved_groups = []
    ls_grp_vol = [i for i in meshin.getGroupsOnSpecifiedLev(0) if i != group_tout]
    for gname in ls_grp_vol:
        try:
            grp = meshin.getGroupArr(0, gname)
            ni = bodycells.findIdForEach(grp)
            ni.setName(grp.getName())
            preserved_groups.append(ni)
        except mc.InterpKernelException:
            pass

    fullvolume = mc.DataArrayInt.Range(0, len(bodycells), 1)
    fullvolume.setName(group_tout)
    l0groups = preserved_groups + [fullvolume]

    newmesh = rebuild_with_groups(m0, l0groups)
    volume_ver, ep_ver = get_mesh_size(newmesh)

    mesh = Mesh()
    mesh.buildFromMedCouplingMesh(newmesh)

    return mesh, group_tout, volume_ver, ep_ver


def get_mesh_size(mcmesh):
    """
    Calculate some mesh properties.

    Args:
    -----
        mcmesh (MEDFileUMesh) : Input mesh

    Returns:
    --------
        volume_ver (float): Total volume of the bounding box of the mesh object.
        ep_ver (float) : Thickness along the Z-axis.
    """

    m0 = mcmesh[0]
    bounds = m0.getBoundingBox()
    volume_ver = 1.0
    dirthick = {}

    for idx, dirname in enumerate("x y z".split()):
        vmin, vmax = bounds[idx]
        volume_ver *= vmax - vmin
        dirthick[dirname.upper()] = vmax - vmin

    ep_ver = dirthick["Z"]

    return volume_ver, ep_ver


def check_meshpara(mesh):
    """
    Check the type of mesh and raise an error if the mesh is parallel.
    """
    if mesh.isParallel():
        UTMESS("F", "HOMO1_19", valk=mesh.getName())
    if not mesh.isQuadratic():
        UTMESS("A", "HOMO1_21", valk=mesh.getName())

    return mesh


def check_meshdim(m0):
    """
    Perform dimensional checks on the input user mesh.

    This function ensures that the mesh meets specific dimensional criteria:
    - The mesh must consist of a single zone.
    - The mesh must have a dimension of 3.
    - The mesh must be in a 3-dimensional space.
    - The minimum bounding box coordinates must be within a specified tolerance.

    Args:
        m0 (Mesh): The input user mesh to be checked.

    Returns:
        bool: True if all checks pass, otherwise raises an error.
    """

    nb_zones = len(m0.partitionBySpreadZone())
    if not nb_zones == 1:
        UTMESS("F", "HOMO1_1", vali=nb_zones)

    if not m0.getMeshDimension() == 3:
        UTMESS("F", "HOMO1_2", vali=m0.getMeshDimension())

    if not m0.getSpaceDimension() == 3:
        UTMESS("F", "HOMO1_3", vali=m0.getSpaceDimension())

    bounds = m0.getBoundingBox()
    vmins = [v[0] for v in bounds]
    for vmin in vmins:
        if abs(vmin) > MESH_TOL:
            UTMESS("F", "HOMO1_15", valr=vmins)

    return True


def rebuild_with_groups(m0, l0groups):
    """
    Rebuild the mesh while preserving 3D groups and creating new 2D and 1D
    groups.

    This function computes the skin of the mesh, sets groups at different
    levels, and creates face and node groups based on the bounding box of the
    mesh.

    Args:
        m0 (Mesh): The original 3D mesh.
        l0groups (list): List of 3D groups to be preserved in the new mesh.

    Returns:
        tuple: A tuple containing:
            float: The volume of the VER mesh.
            dict: The thickness in each direction (x, y, z).
            MEDFileUMesh: The new mesh with preserved and newly created groups.
    """

    try:
        m0.orientCorrectly3DCells()
        # FIXME : remove the try except since function exists now.
    except AttributeError:
        ids = m0.getMeasureField(False).getArray().findIdsLowerThan(0.0)
        meshToInvert = m0[ids]
        meshToInvert.invertOrientationOfAllCells()
        m0[ids] = meshToInvert

    skin = m0.computeSkin()

    newmesh = mc.MEDFileUMesh()
    newmesh.setName(m0.getName())
    newmesh[0] = m0
    newmesh[-1] = skin

    newmesh.setGroupsAtLevel(0, l0groups)

    # Recherche des faces à xmin,xmax,ymin,ymax,zmin,zmax et creation des groupes
    bounds = m0.getBoundingBox()
    tol = MESH_TOL
    face_groups = []
    face_nodes = {}

    for idx, dirname in enumerate("x y z".split()):
        vmin, vmax = bounds[idx]

        ndsmin = m0.getCoords()[:, idx].findIdsInRange(vmin - tol, vmin + tol)
        cellsmin = skin.getCellIdsLyingOnNodes(ndsmin, True)
        grpname = "face_%smin" % dirname
        if len(cellsmin) == 0:
            UTMESS("F", "HOMO1_7", valk=grpname)
        cellsmin.setName(grpname)
        face_groups.append(cellsmin)
        face_nodes[grpname] = ndsmin

        ndsmax = m0.getCoords()[:, idx].findIdsInRange(vmax - tol, vmax + tol)
        cellsmax = skin.getCellIdsLyingOnNodes(ndsmax, True)
        grpname = "face_%smax" % dirname
        if len(cellsmax) == 0:
            UTMESS("F", "HOMO1_7", valk=grpname)
        cellsmax.setName(grpname)
        face_groups.append(cellsmax)
        face_nodes[grpname] = ndsmax

    skin_cells = mc.DataArrayInt.Range(0, skin.getNumberOfCells(), 1)
    bbox_cells = mc.DataArrayInt.BuildUnion(face_groups)
    internal_skin_cells = skin_cells.buildSubstraction(bbox_cells)
    grpname = "face_int"
    internal_skin_cells.setName(grpname)
    if len(internal_skin_cells) > 0:
        face_groups.append(internal_skin_cells)

    newmesh.setGroupsAtLevel(-1, face_groups)

    node_groups = []

    int_zmin_xmin = mc.DataArrayInt.BuildIntersection(
        (face_nodes["face_zmin"], face_nodes["face_xmin"])
    )
    int_zmin_xmin.setName("int_zmin_xmin")
    node_groups.append(int_zmin_xmin)
    int_zmin_ymin = mc.DataArrayInt.BuildIntersection(
        (face_nodes["face_zmin"], face_nodes["face_ymin"])
    )
    int_zmin_ymin.setName("int_zmin_ymin")
    node_groups.append(int_zmin_ymin)
    int_zmin_xmax = mc.DataArrayInt.BuildIntersection(
        (face_nodes["face_zmin"], face_nodes["face_xmax"])
    )
    int_zmin_xmax.setName("int_zmin_xmax")
    node_groups.append(int_zmin_xmax)
    int_zmin_ymax = mc.DataArrayInt.BuildIntersection(
        (face_nodes["face_zmin"], face_nodes["face_ymax"])
    )
    int_zmin_ymax.setName("int_zmin_ymax")
    node_groups.append(int_zmin_ymax)

    int_zmax_xmin = mc.DataArrayInt.BuildIntersection(
        (face_nodes["face_zmax"], face_nodes["face_xmin"])
    )
    int_zmax_xmin.setName("int_zmax_xmin")
    node_groups.append(int_zmax_xmin)
    int_zmax_ymin = mc.DataArrayInt.BuildIntersection(
        (face_nodes["face_zmax"], face_nodes["face_ymin"])
    )
    int_zmax_ymin.setName("int_zmax_ymin")
    node_groups.append(int_zmax_ymin)
    int_zmax_xmax = mc.DataArrayInt.BuildIntersection(
        (face_nodes["face_zmax"], face_nodes["face_xmax"])
    )
    int_zmax_xmax.setName("int_zmax_xmax")
    node_groups.append(int_zmax_xmax)
    int_zmax_ymax = mc.DataArrayInt.BuildIntersection(
        (face_nodes["face_zmax"], face_nodes["face_ymax"])
    )
    int_zmax_ymax.setName("int_zmax_ymax")
    node_groups.append(int_zmax_ymax)

    low_edges_nodes = mc.DataArrayInt.BuildUnion(
        (int_zmin_xmin, int_zmin_ymin, int_zmin_xmax, int_zmin_ymax)
    )
    low_edges_nodes.setName("edges_face_zmin")
    node_groups.append(low_edges_nodes)

    up_edges_nodes = mc.DataArrayInt.BuildUnion(
        (int_zmax_xmin, int_zmax_ymin, int_zmax_xmax, int_zmax_ymax)
    )
    up_edges_nodes.setName("edges_face_zmax")
    node_groups.append(up_edges_nodes)

    face_zmin_no_edges = face_nodes["face_zmin"].buildSubstraction(low_edges_nodes)
    face_zmin_no_edges.setName("face_zmin_no_edges")
    node_groups.append(face_zmin_no_edges)

    face_zmax_no_edges = face_nodes["face_zmax"].buildSubstraction(up_edges_nodes)
    face_zmax_no_edges.setName("face_zmax_no_edges")
    node_groups.append(face_zmax_no_edges)

    nds_zsym = m0.getCoords()[:, 2].findIdsInRange(0.0 - tol, 0.0 + tol)
    int_zsym_ymin = mc.DataArrayInt.BuildIntersection((face_nodes["face_ymin"], nds_zsym))
    node_se = int_zsym_ymin[m0.getCoords()[int_zsym_ymin][:, 0].getMinValue()[1]]
    lock_rigi_node = mc.DataArrayInt((node_se,))
    lock_rigi_node.setName("lock_rigi")
    node_groups.append(lock_rigi_node)

    newmesh.setGroupsAtLevel(1, node_groups)

    return newmesh
