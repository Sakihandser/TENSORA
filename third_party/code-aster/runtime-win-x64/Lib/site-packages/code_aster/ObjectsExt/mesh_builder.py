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
:py:mod:`mesh_builder` --- Simple mesh builder
**********************************************

The :py:mod:`mesh_builder` helps generate simple meshes (ring, square,
tube, cube). The user can indicate the geometrical sizes of the shape
and the mesh fineness using the refine parameter.

The functions are exposed as class-method in the :py:class:`Mesh` class.

"""

import math
import os
import traceback
from functools import wraps

from ..Messages import UTMESS
from ..Utilities import medcoupling as medc
from .medctoaster import MEDCouplingMeshHelper

MEDCTOL = 1.0e-12


def check_medc_error(func):
    """Decorator to highlight medcoupling exceptions as user error message."""

    @wraps(func)
    def wrapper(*args, **kwds):
        """wrapper"""
        try:
            result = func(*args, **kwds)
        except medc.InterpKernelException:
            exc = traceback.format_exc()
            UTMESS("F", "MED_41", valk=exc)
        return result

    return wrapper


@check_medc_error
def buildFromMedCouplingMesh(mesh, mcmesh, verbose=0):
    """Build mesh from medcoupling mesh.

    Arguments:
        mesh (Mesh|ParallelMesh): The Mesh object to be filled.
        mcmesh (*medcoupling.MEDFileUMesh*): The MEDCoupling mesh.
        verbose (int): Verbosity between 0 (a few details) to 2 (more verbosy).
    """
    mreader = MEDCouplingMeshHelper()
    mreader.setMedCouplingMesh(mcmesh)
    mreader.buildMesh(mesh, verbose)


@check_medc_error
def buildFromMedFile(mesh, filename, meshname=None, verbose=0):
    """Build mesh from a MED file.

    Arguments:
        mesh (Mesh|ParallelMesh): The Mesh object to be filled.
        filename (Path|str): Path of the MED file.
        meshname (str): Name of the mesh to be read from file.
        verbose (int): Verbosity between 0 (a few details) to 2 (more verbosy).
    """
    mreader = MEDCouplingMeshHelper()
    mreader.readMedFile(os.fspath(filename), meshname)
    mreader.buildMesh(mesh, verbose)


def rectangle(xmin, xmax, ymin, ymax, nx=1, ny=1):
    """Build the quadrilateral mesh of a square.

    Arguments:
        xmin [float] : min X coord.
        xmax [float] : max X coord.
        ymin [float] : min Y coord.
        ymax [float] : max Y coord.
        nx [int] : number of segments along the x axis (default 1).
        ny [int] : number of segments along the y axis (default 1).
    """

    assert all(isinstance(i, int) for i in (nx, ny)), "Invalid parameter"
    assert nx >= 1, "Invalid geometry"
    assert ny >= 1, "Invalid geometry"
    assert xmax > xmin, "Invalid geometry"
    assert ymax > ymin, "Invalid geometry"

    vx = medc.DataArrayDouble(nx + 1)
    vx.iota()
    vx *= (xmax - xmin) / (nx)
    vx += xmin

    vy = medc.DataArrayDouble(ny + 1)
    vy.iota()
    vy *= (ymax - ymin) / (ny)
    vy += ymin

    # Cartesian mesh
    meshC = medc.MEDCouplingCMesh()
    meshC.setCoords(vx, vy)
    meshU = meshC.buildUnstructured()
    meshU.sortCellsInMEDFileFrmt()

    coords_x = meshU.getCoords()[:, 0]
    coords_y = meshU.getCoords()[:, 1]

    # Mesh 2D
    faces, desc_2d, descIdx_2d, revDesc_2d, revDescIdx_2d = meshU.buildDescendingConnectivity()
    # Contour faces belong only to 1 3D cell
    contour_faces = revDescIdx_2d.deltaShiftIndex().findIdsEqual(1)
    skinU = faces[contour_faces]

    # Groups 2D
    surface = medc.DataArrayInt.Range(0, meshU.getNumberOfCells(), 1)
    surface.setName("SURFACE")

    bottom_nodes = coords_y.findIdsInRange(ymin - MEDCTOL, ymin + MEDCTOL)
    bottom = skinU.getCellIdsLyingOnNodes(bottom_nodes, True)
    bottom.setName("BOTTOM")

    top_nodes = coords_y.findIdsInRange(ymax - MEDCTOL, ymax + MEDCTOL)
    top = skinU.getCellIdsLyingOnNodes(top_nodes, True)
    top.setName("TOP")

    left_nodes = coords_x.findIdsInRange(xmin - MEDCTOL, xmin + MEDCTOL)
    left = skinU.getCellIdsLyingOnNodes(left_nodes, True)
    left.setName("LEFT")

    right_nodes = coords_x.findIdsInRange(xmax - MEDCTOL, xmax + MEDCTOL)
    right = skinU.getCellIdsLyingOnNodes(right_nodes, True)
    right.setName("RIGHT")

    # Groups nodes
    n1 = medc.DataArrayInt.BuildIntersection((left_nodes, top_nodes))
    n1.setName("N1")

    n2 = medc.DataArrayInt.BuildIntersection((right_nodes, top_nodes))
    n2.setName("N2")

    n3 = medc.DataArrayInt.BuildIntersection((left_nodes, bottom_nodes))
    n3.setName("N3")

    n4 = medc.DataArrayInt.BuildIntersection((right_nodes, bottom_nodes))
    n4.setName("N4")

    # Compose med mesh
    mcmesh = medc.MEDFileUMesh()
    mcmesh.setName("RECTANGLE")
    mcmesh[0] = meshU
    mcmesh[-1] = skinU
    mcmesh.setGroupsAtLevel(0, [surface])
    mcmesh.setGroupsAtLevel(-1, [left, right, top, bottom])
    mcmesh.setGroupsAtLevel(1, [n1, n2, n3, n4])

    return mcmesh


def arc(radius, angle, no):
    """Build the mesh of an arc.

    Arguments:
        radius [float] : Arc radius.
        angle [float] : Arc angle in radians.
        no [int] : number of segments along the theta axis.
    """
    assert all(isinstance(i, int) for i in (no,)), "Invalid parameter"
    assert no >= 2, "Invalid geometry"
    assert radius > 0.0, "Invalid geometry"
    assert angle > 0.0, "Invalid geometry"
    assert angle <= 2 * math.pi, "Invalid geometry"

    coords_rad = medc.DataArrayDouble(no)
    coords_rad[:] = radius

    coords_theta = medc.DataArrayDouble(no)
    coords_theta.iota()
    coords_theta /= (no - 1) / angle

    coords_p = medc.DataArrayDouble.Meld((coords_rad, coords_theta))
    coords_c = coords_p.fromPolarToCart()
    meshU = medc.MEDCouplingUMesh.Build1DMeshFromCoords(coords_c)

    arc = medc.DataArrayInt.Range(0, meshU.getNumberOfCells(), 1)
    arc.setName("ARC")

    # Compose med mesh
    mcmesh = medc.MEDFileUMesh()
    mcmesh[0] = meshU
    mcmesh.setName("ARC")
    mcmesh.setGroupsAtLevel(0, [arc])

    return mcmesh


def ring(rmin, rmax, no, nr):
    """Build the mesh of a ring.

    Arguments:
        rmin [float] : min radius.
        rmax [float] : max radius.
        no [int] : number of segments along the theta axis.
        nr [int] : number of segments along the radial axis.
    """

    assert all(isinstance(i, int) for i in (no, nr)), "Invalid parameter"
    assert no >= 4, "Invalid geometry"
    assert nr >= 1, "Invalid geometry"
    assert rmin >= 0.0, "Invalid geometry"
    assert rmax > rmin, "Invalid geometry"

    r_arr = medc.DataArrayDouble(nr + 1)
    r_arr.iota()
    r_arr *= (rmax - rmin) / (nr)
    r_arr += rmin

    theta = medc.DataArrayDouble(no + 1)
    theta.iota()
    theta *= 2 * math.pi / (no)

    # Cartesian mesh
    meshC = medc.MEDCouplingCMesh()
    meshC.setCoords(r_arr, theta)

    # Build disk mesh by reducing one edge to one point
    meshU = meshC.buildUnstructured()
    coords = meshU.getCoords()
    coords[:, :2] = coords[:, :2].fromPolarToCart()
    meshU.setCoords(coords)
    # Remove double nodes
    meshU.mergeNodes(MEDCTOL)
    # Convert degenerated QUAD into TRI
    meshU.convertDegeneratedCells()
    # Make mesh compatible for MED
    meshU.sortCellsInMEDFileFrmt()

    # Mesh 2D
    faces, desc_2d, descIdx_2d, revDesc_2d, revDescIdx_2d = meshU.buildDescendingConnectivity()
    # Contour faces belong only to 1 3D cell
    contour_faces = revDescIdx_2d.deltaShiftIndex().findIdsEqual(1)
    skinU = faces[contour_faces]

    # Groups 2D
    surface = medc.DataArrayInt.Range(0, meshU.getNumberOfCells(), 1)
    surface.setName("SURFACE")

    # Groups 1D
    coords_r = (skinU.getCoords()[:, 0] ** 2 + skinU.getCoords()[:, 1] ** 2) ** 0.5
    rmax_nodes = coords_r.findIdsInRange(rmax - MEDCTOL, rmax + MEDCTOL)
    rmax = skinU.getCellIdsLyingOnNodes(rmax_nodes, True)
    rmax.setName("REXT")

    rmin_nodes = coords_r.findIdsInRange(rmin - MEDCTOL, rmin + MEDCTOL)
    rmin = skinU.getCellIdsLyingOnNodes(rmin_nodes, True)
    rmin.setName("RINT")

    # Compose med mesh
    mcmesh = medc.MEDFileUMesh()
    mcmesh.setName("RING")
    mcmesh[0] = meshU
    mcmesh[-1] = skinU
    mcmesh.setGroupsAtLevel(0, [surface])
    mcmesh.setGroupsAtLevel(-1, [rmin, rmax])

    return mcmesh


def parallelepiped(xmin, xmax, ymin, ymax, zmin, zmax, nx=1, ny=1, nz=1):
    """Build the hexaedral mesh of a cube.

    Arguments:
        xmin [float] : min X coord.
        xmax [float] : max X coord.
        ymin [float] : min Y coord.
        ymax [float] : max Y coord.
        zmin [float] : min Z coord.
        zmax [float] : max Z coord.
        nx [int] : number of segments along the x axis (default 1).
        ny [int] : number of segments along the y axis (default 1).
        nz [int] : number of segments along the z axis (default 1).
    """

    assert all(isinstance(i, int) for i in (nx, ny, nz)), "Invalid parameter"
    assert nx >= 1, "Invalid geometry"
    assert ny >= 1, "Invalid geometry"
    assert nz >= 1, "Invalid geometry"
    assert xmax > xmin, "Invalid geometry"
    assert ymax > ymin, "Invalid geometry"
    assert zmax > zmin, "Invalid geometry"

    vx = medc.DataArrayDouble(nx + 1)
    vx.iota()
    vx *= (xmax - xmin) / (nx)
    vx += xmin

    vy = medc.DataArrayDouble(ny + 1)
    vy.iota()
    vy *= (ymax - ymin) / (ny)
    vy += ymin

    vz = medc.DataArrayDouble(nz + 1)
    vz.iota()
    vz *= (zmax - zmin) / (nz)
    vz += zmin

    # Cartesian mesh
    meshC = medc.MEDCouplingCMesh()
    meshC.setCoords(vx, vy, vz)
    meshU = meshC.buildUnstructured()
    meshU.sortCellsInMEDFileFrmt()

    coords_x = meshU.getCoords()[:, 0]
    coords_y = meshU.getCoords()[:, 1]
    coords_z = meshU.getCoords()[:, 2]

    # Mesh 2D
    faces, desc_2d, descIdx_2d, revDesc_2d, revDescIdx_2d = meshU.buildDescendingConnectivity()
    # Contour faces belong only to 1 3D cell
    contour_faces = revDescIdx_2d.deltaShiftIndex().findIdsEqual(1)
    skinU = faces[contour_faces]

    # Mesh 1D
    edges, desc_1d, descIdx_1d, revDesc_1d, revDescIdx_1d = faces.buildDescendingConnectivity()
    # Contour edges belong only to 2 faces
    contour_edges = revDescIdx_1d.deltaShiftIndex().findIdsEqual(2)
    edgeU = edges[contour_edges]

    # Groups 3D
    volume = medc.DataArrayInt.Range(0, meshU.getNumberOfCells(), 1)
    volume.setName("VOLUME")

    # Groups 2D
    bottom_nodes = coords_z.findIdsInRange(zmin - MEDCTOL, zmin + MEDCTOL)
    bottom = skinU.getCellIdsLyingOnNodes(bottom_nodes, True)
    bottom.setName("BOTTOM")

    top_nodes = coords_z.findIdsInRange(zmax - MEDCTOL, zmax + MEDCTOL)
    top = skinU.getCellIdsLyingOnNodes(top_nodes, True)
    top.setName("TOP")

    left_nodes = coords_y.findIdsInRange(ymin - MEDCTOL, ymin + MEDCTOL)
    left = skinU.getCellIdsLyingOnNodes(left_nodes, True)
    left.setName("LEFT")

    right_nodes = coords_y.findIdsInRange(ymax - MEDCTOL, ymax + MEDCTOL)
    right = skinU.getCellIdsLyingOnNodes(right_nodes, True)
    right.setName("RIGHT")

    front_nodes = coords_x.findIdsInRange(xmax - MEDCTOL, xmax + MEDCTOL)
    front = skinU.getCellIdsLyingOnNodes(front_nodes, True)
    front.setName("FRONT")

    back_nodes = coords_x.findIdsInRange(xmin - MEDCTOL, xmin + MEDCTOL)
    back = skinU.getCellIdsLyingOnNodes(back_nodes, True)
    back.setName("BACK")

    # Groups 1D
    s13_nodes = medc.DataArrayInt.BuildIntersection((bottom_nodes, back_nodes))
    s13 = edgeU.getCellIdsLyingOnNodes(s13_nodes, True)
    s13.setName("S13")

    s24_nodes = medc.DataArrayInt.BuildIntersection((bottom_nodes, front_nodes))
    s24 = edgeU.getCellIdsLyingOnNodes(s24_nodes, True)
    s24.setName("S24")

    s34_nodes = medc.DataArrayInt.BuildIntersection((bottom_nodes, left_nodes))
    s34 = edgeU.getCellIdsLyingOnNodes(s34_nodes, True)
    s34.setName("S34")

    s21_nodes = medc.DataArrayInt.BuildIntersection((bottom_nodes, right_nodes))
    s21 = edgeU.getCellIdsLyingOnNodes(s21_nodes, True)
    s21.setName("S21")

    s51_nodes = medc.DataArrayInt.BuildIntersection((back_nodes, right_nodes))
    s51 = edgeU.getCellIdsLyingOnNodes(s51_nodes, True)
    s51.setName("S51")

    s78_nodes = medc.DataArrayInt.BuildIntersection((top_nodes, left_nodes))
    s78 = edgeU.getCellIdsLyingOnNodes(s78_nodes, True)
    s78.setName("S78")

    s56_nodes = medc.DataArrayInt.BuildIntersection((top_nodes, right_nodes))
    s56 = edgeU.getCellIdsLyingOnNodes(s56_nodes, True)
    s56.setName("S56")

    s84_nodes = medc.DataArrayInt.BuildIntersection((front_nodes, left_nodes))
    s84 = edgeU.getCellIdsLyingOnNodes(s84_nodes, True)
    s84.setName("S84")

    s68_nodes = medc.DataArrayInt.BuildIntersection((front_nodes, top_nodes))
    s68 = edgeU.getCellIdsLyingOnNodes(s68_nodes, True)
    s68.setName("S68")

    s26_nodes = medc.DataArrayInt.BuildIntersection((front_nodes, right_nodes))
    s26 = edgeU.getCellIdsLyingOnNodes(s26_nodes, True)
    s26.setName("S26")

    s75_nodes = medc.DataArrayInt.BuildIntersection((back_nodes, top_nodes))
    s75 = edgeU.getCellIdsLyingOnNodes(s75_nodes, True)
    s75.setName("S75")

    s37_nodes = medc.DataArrayInt.BuildIntersection((back_nodes, left_nodes))
    s37 = edgeU.getCellIdsLyingOnNodes(s37_nodes, True)
    s37.setName("S37")

    # Groups nodes
    n1 = medc.DataArrayInt.BuildIntersection((bottom_nodes, right_nodes, back_nodes))
    n1.setName("N1")

    n2 = medc.DataArrayInt.BuildIntersection((bottom_nodes, right_nodes, front_nodes))
    n2.setName("N2")

    n3 = medc.DataArrayInt.BuildIntersection((bottom_nodes, left_nodes, back_nodes))
    n3.setName("N3")

    n4 = medc.DataArrayInt.BuildIntersection((bottom_nodes, left_nodes, front_nodes))
    n4.setName("N4")

    n5 = medc.DataArrayInt.BuildIntersection((top_nodes, right_nodes, back_nodes))
    n5.setName("N5")

    n6 = medc.DataArrayInt.BuildIntersection((top_nodes, right_nodes, front_nodes))
    n6.setName("N6")

    n7 = medc.DataArrayInt.BuildIntersection((top_nodes, left_nodes, back_nodes))
    n7.setName("N7")

    n8 = medc.DataArrayInt.BuildIntersection((top_nodes, left_nodes, front_nodes))
    n8.setName("N8")

    # Compose med mesh
    mcmesh = medc.MEDFileUMesh()
    mcmesh.setName("PARALLEPIPED")
    mcmesh[0] = meshU
    mcmesh[-1] = skinU
    mcmesh[-2] = edgeU
    mcmesh.setGroupsAtLevel(0, [volume])
    mcmesh.setGroupsAtLevel(-1, [left, right, top, bottom, back, front])
    mcmesh.setGroupsAtLevel(-2, [s13, s24, s34, s21, s51, s78, s56, s84, s68, s26, s75, s37])
    mcmesh.setGroupsAtLevel(1, [n1, n2, n3, n4, n5, n6, n7, n8])

    return mcmesh


def tube(rmin, rmax, zmin, zmax, no, nr, nz):
    """Build the hexaedral mesh of a tube.

    Arguments:
        rmin [float] : min radius.
        rmax [float] : max radius.
        zmin [float] : min Z coord.
        zmax [float] : max Z coord.
        no [int] : number of segments along the theta axis
        nr [int] : number of segments along the radial axis
        nz [int] : number of segments along the z axis
    """

    assert all(isinstance(i, int) for i in (no, nr, nz))
    assert no >= 4, "Invalid geometry"
    assert nr >= 1, "Invalid geometry"
    assert nz >= 1, "Invalid geometry"
    assert rmin >= 0.0, "Invalid geometry"
    assert rmax > rmin, "Invalid geometry"
    assert zmax > zmin, "Invalid geometry"

    r_arr = medc.DataArrayDouble(nr + 1)
    r_arr.iota()
    r_arr *= (rmax - rmin) / (nr)
    r_arr += rmin

    theta = medc.DataArrayDouble(no + 1)
    theta.iota()
    theta *= 2 * math.pi / (no)

    vz = medc.DataArrayDouble(nz + 1)
    vz.iota()
    vz *= (zmax - zmin) / (nz)
    vz += zmin

    # Cartesian mesh
    meshC = medc.MEDCouplingCMesh()
    meshC.setCoords(r_arr, theta, vz)

    # Build disk mesh by reducing one face to one edge
    meshU = meshC.buildUnstructured()
    coords = meshU.getCoords()
    coords[:, :2] = coords[:, :2].fromPolarToCart()
    meshU.setCoords(coords)
    # Remove double nodes
    meshU.mergeNodes(MEDCTOL)
    # Convert degenerated HEXA into PRISM
    meshU.convertDegeneratedCells()
    # Make mesh compatible for MED
    meshU.sortCellsInMEDFileFrmt()

    # Mesh 2D
    faces, desc_2d, descIdx_2d, revDesc_2d, revDescIdx_2d = meshU.buildDescendingConnectivity()
    # Contour faces belong only to 1 3D cell
    contour_faces = revDescIdx_2d.deltaShiftIndex().findIdsEqual(1)
    skinU = faces[contour_faces]

    coords_z = meshU.getCoords()[:, 2]
    coords_r = (skinU.getCoords()[:, 0] ** 2 + skinU.getCoords()[:, 1] ** 2) ** 0.5

    # Groups 3D
    volume = medc.DataArrayInt.Range(0, meshU.getNumberOfCells(), 1)
    volume.setName("VOLUME")

    # Groups 2D
    bottom_nodes = coords_z.findIdsInRange(zmin - MEDCTOL, zmin + MEDCTOL)
    bottom = skinU.getCellIdsLyingOnNodes(bottom_nodes, True)
    bottom.setName("BOTTOM")

    top_nodes = coords_z.findIdsInRange(zmax - MEDCTOL, zmax + MEDCTOL)
    top = skinU.getCellIdsLyingOnNodes(top_nodes, True)
    top.setName("TOP")

    surfext_nodes = coords_r.findIdsInRange(rmax - MEDCTOL, rmax + MEDCTOL)
    surfext = skinU.getCellIdsLyingOnNodes(surfext_nodes, True)
    surfext.setName("SURFEXT")

    surfint_nodes = coords_r.findIdsInRange(rmin - MEDCTOL, rmin + MEDCTOL)
    surfint = skinU.getCellIdsLyingOnNodes(surfint_nodes, True)
    surfint.setName("SURFINT")

    # Compose med mesh
    mcmesh = medc.MEDFileUMesh()
    mcmesh.setName("TUBE")
    mcmesh[0] = meshU
    mcmesh[-1] = skinU
    mcmesh.setGroupsAtLevel(0, [volume])
    mcmesh.setGroupsAtLevel(-1, [surfint, surfext, top, bottom])

    return mcmesh


def pointcloud(coordlist, groups=False):
    """Build the mesh of a point cloud from a set of coordinates.

    Arguments:
        coordlist list[float] : list of points coordinates (1D, 2D, 3D).
        groups [bool] : if True, creates a group for each point, (default False).
    """

    assert len(coordlist) > 0, "Invalid parameter"
    assert len(set(len(c) for c in (coordlist))) == 1, "Invalid parameter"

    coords = medc.DataArrayDouble(coordlist)
    meshU = medc.MEDCouplingUMesh.Build0DMeshFromCoords(coords)
    meshU.setName("CLOUD")

    grp_points = []
    grp_p_all = medc.DataArrayInt.Range(0, meshU.getNumberOfNodes(), 1)
    grp_p_all.setName("NODES")
    grp_points.append(grp_p_all)

    if groups:
        for i in range(meshU.getNumberOfNodes()):
            grp_i = medc.DataArrayInt([i])
            grp_i.setName("N%d" % (i + 1))
            grp_points.append(grp_i)

    mcmesh = medc.MEDFileUMesh()
    mcmesh[0] = meshU
    mcmesh.setGroupsAtLevel(0, grp_points)
    mcmesh.setGroupsAtLevel(1, grp_points)

    return mcmesh


def spline1d(coordlist, groups=False):
    """Build the mesh of a 1D spline from a set of coordinates.

    Arguments:
        coordlist list[float] : list of points coordinates (1D, 2D, 3D).
        groups [bool] : if True, creates a group for each point, (default False).
    """

    assert len(coordlist) > 1, "Invalid parameter"
    assert len(set(len(c) for c in (coordlist))) == 1, "Invalid parameter"

    coords = medc.DataArrayDouble(coordlist)
    meshU = medc.MEDCouplingUMesh.Build1DMeshFromCoords(coords)
    meshU.setName("LINE")

    grp_points = []
    grp_p_all = medc.DataArrayInt.Range(0, meshU.getNumberOfNodes(), 1)
    grp_p_all.setName("NODES")
    grp_points.append(grp_p_all)

    grp_cells = []
    grp_s_all = medc.DataArrayInt.Range(0, meshU.getNumberOfCells(), 1)
    grp_s_all.setName("LINE")
    grp_cells.append(grp_s_all)

    if groups:
        for i in range(meshU.getNumberOfNodes()):
            grp_i = medc.DataArrayInt([i])
            grp_i.setName("N%d" % (i + 1))
            grp_points.append(grp_i)

        for i in range(meshU.getNumberOfCells()):
            grp_i = medc.DataArrayInt([i])
            grp_i.setName("S%d" % (i + 1))
            grp_cells.append(grp_i)

    mcmesh = medc.MEDFileUMesh()
    mcmesh[0] = meshU
    mcmesh.setGroupsAtLevel(0, grp_cells)
    mcmesh.setGroupsAtLevel(1, grp_points)

    return mcmesh
