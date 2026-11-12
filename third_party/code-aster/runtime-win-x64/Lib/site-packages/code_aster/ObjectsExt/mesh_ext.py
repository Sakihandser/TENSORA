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
:py:class:`Mesh` --- Assignment of mesh
************************************************************************
"""

import os
import subprocess
import tempfile

from ..CodeCommands import CREA_MAILLAGE
from ..MedUtils.MedConverter import convertMesh2MedCoupling
from ..Objects import Mesh, MedToAsterReader, PythonBool
from ..Objects.Serialization import InternalStateBuilder
from ..Utilities import ExecutionParameter, force_list, injector
from . import mesh_builder


class MeshStateBuilder(InternalStateBuilder):
    """Class that returns the internal state of a *Mesh*."""

    def restore(self, mesh):
        """Restore the *DataStructure* content from the previously saved internal
        state.

        Arguments:
            mesh (*DataStructure*): The *DataStructure* object to be restored.
        """
        super().restore(mesh)
        mesh.build()


@injector(Mesh)
class ExtendedMesh:
    cata_sdj = "SD.sd_maillage.sd_maillage"
    internalStateBuilder = MeshStateBuilder

    def getCoordinatesAsSimpleFieldOnNodes(self):
        """Same as :py:meth:`getCoordinates` with a conversion into a *SimpleFieldOnNodes*.

        Returns:
            *SimpleFieldOnNodesReal*: Coordinates as a *SimpleFieldOnNodes*.
        """
        return self.getCoordinates().toFieldOnNodes(self).toSimpleFieldOnNodes()

    @classmethod
    def buildRectangle(cls, lx=1.0, ly=1.0, nx=1, ny=1, refine=0, info=1):
        """Build the quadrilateral mesh of a rectangle.

        Arguments:
            lx [float] : length along the x axis (default 1.).
            ly [float] : length along the y axis (default 1.).
            nx [int] : number of elements along the x axis (default 1).
            ny [int] : number of elements along the y axis (default 1).
            refine [int] : number of mesh refinement iterations (default 0).
            info [int] : verbosity mode (0|1|2). (default 1).
        """

        assert info in (0, 1, 2, 4), "Invalid parameter"
        assert isinstance(refine, int), "Invalid parameter"

        # Take into account refine level before creating mesh
        nb_seg_x = nx * (2**refine)
        nb_seg_y = ny * (2**refine)

        mcmesh = mesh_builder.rectangle(
            xmin=0.0, xmax=lx, ymin=0.0, ymax=ly, nx=nb_seg_x, ny=nb_seg_y
        )

        # Convert to aster mesh
        mesh = cls()
        mesh.buildFromMedCouplingMesh(mcmesh, verbose=info)

        return mesh

    @classmethod
    def buildSquare(cls, l=1, refine=0, info=1):
        """Build the quadrilateral mesh of a square.

        Arguments:
            l [float] : size of the cube (default 1.).
            refine [int] : number of mesh refinement iterations (default 0).
            info [int] : verbosity mode (0|1|2). (default 1).
        """
        return cls.buildRectangle(lx=l, ly=l, refine=refine, info=info)

    @classmethod
    def buildArc(cls, radius=1, angle=1, refine=0, info=1):
        """Build the mesh of an arc.

        Arguments:
            radius [float] : Arc radius (default 1).
            angle [float] : Arc angle in radians (default 1).
            refine [int] : number of mesh refinement iterations (default 0).
            info [int] : verbosity mode (0|1|2). (default 1).
        """
        assert info in (0, 1, 2, 4), "Invalid parameter"
        assert isinstance(refine, int), "Invalid parameter"

        # Take into account refine level before creating mesh
        nb_seg_orth = 2 * (2**refine)

        mcmesh = mesh_builder.arc(radius=radius, angle=angle, no=nb_seg_orth)

        # Convert to aster mesh
        mesh = cls()
        mesh.buildFromMedCouplingMesh(mcmesh, verbose=info)

        return mesh

    @classmethod
    def buildRing(cls, rint=0.1, rext=1, refine=0, info=1):
        """Build the mesh of a ring.

        Arguments:
            rint [float] : internal radius (default 0.1).
            rext [float] : external radius (default 1).
            refine [int] : number of mesh refinement iterations (default 0).
            info [int] : verbosity mode (0|1|2). (default 1).
        """
        assert info in (0, 1, 2, 4), "Invalid parameter"
        assert isinstance(refine, int), "Invalid parameter"

        # Take into account refine level before creating mesh
        nb_seg_orth = 8 * (2**refine)
        nb_seg_radial = 2 * (2**refine)

        mcmesh = mesh_builder.ring(rmin=rint, rmax=rext, no=nb_seg_orth, nr=nb_seg_radial)

        # Convert to aster mesh
        mesh = cls()
        mesh.buildFromMedCouplingMesh(mcmesh, verbose=info)

        return mesh

    @classmethod
    def buildDisk(cls, radius=1, refine=0, info=1):
        """Build the mesh of a disk.

        Arguments:
            radius [float] : radius of the disk (default 1).
            refine [int] : number of mesh refinement iterations (default 0).
            info [int] : verbosity mode (0|1|2). (default 1).
        """
        return cls.buildRing(rint=0.0, rext=radius, refine=refine, info=info)

    @classmethod
    def buildParallelepiped(cls, lx=1, ly=1, lz=1, refine=0, info=1):
        """Build the quadrilateral mesh of a parallelepiped.

        Arguments:
            lx [float] : length along the x axis (default 1.).
            ly [float] : length along the y axis (default 1.).
            lz [float] : length along the z axis (default 1.).
            refine [int] : number of mesh refinement iterations (default 0).
            info [int] : verbosity mode (0|1|2). (default 1).
        """

        assert info in (0, 1, 2, 4), "Invalid parameter"
        assert isinstance(refine, int), "Invalid parameter"

        # Take into account refine level before creating mesh
        nb_seg_x = 1 * (2**refine)
        nb_seg_y = 1 * (2**refine)
        nb_seg_z = 1 * (2**refine)

        mcmesh = mesh_builder.parallelepiped(
            xmin=0.0,
            xmax=lx,
            ymin=0.0,
            ymax=ly,
            zmin=0.0,
            zmax=lz,
            nx=nb_seg_x,
            ny=nb_seg_y,
            nz=nb_seg_z,
        )

        # Convert to aster mesh
        mesh = cls()
        mesh.buildFromMedCouplingMesh(mcmesh, verbose=info)

        return mesh

    @classmethod
    def buildCube(cls, l=1, refine=0, info=1):
        """Build the quadrilateral mesh of a cube.

        Arguments:
            l [float] : size of the cube (default 1.).
            refine [int] : number of mesh refinement iterations (default 0).
            info [int] : verbosity mode (0|1|2). (default 1).
        """
        return cls.buildParallelepiped(lx=l, ly=l, lz=l, refine=refine, info=info)

    @classmethod
    def buildTube(cls, height=3, rint=0.1, rext=1, refine=0, info=1):
        """Build the mesh of a tube.

        Arguments:
            height [float] : height along the z axis (default 3).
            rint [float] : internal radius (default 0.1).
            rext [float] : external radius (default 1).
            refine [int] : number of mesh refinement iterations (default 0).
            info [int] : verbosity mode (1 or 2). (default 1).
        """
        assert info in (0, 1, 2, 4), "Invalid parameter"
        assert isinstance(refine, int), "Invalid parameter"

        # Take into account refine level before creating mesh
        nb_seg_orth = 8 * (2**refine)
        nb_seg_radial = 2 * (2**refine)
        nb_seg_axial = 1 * (2**refine)

        mcmesh = mesh_builder.tube(
            rmin=rint,
            rmax=rext,
            zmin=0,
            zmax=height,
            no=nb_seg_orth,
            nr=nb_seg_radial,
            nz=nb_seg_axial,
        )

        # Convert to aster mesh
        mesh = cls()
        mesh.buildFromMedCouplingMesh(mcmesh, verbose=info)

        return mesh

    @classmethod
    def buildCylinder(cls, height=3, radius=1, refine=0, info=1):
        """Build the mesh of a cylinder.

        Arguments:
            height [float] : height of the cylinder along the z axis (default 0).
            radius [float] : radius of the cylinder (default 1).
            refine [int] : number of mesh refinement iterations (default 0).
            info [int] : verbosity mode (1 or 2). (default 1).
        """
        return cls.buildTube(height=height, rint=0, rext=radius, refine=refine, info=info)

    @classmethod
    def buildPointCloud(cls, coordlist, groups=False, info=1):
        """Build the mesh of a point cloud from a set of coordinates.

        Arguments:
            coordlist list[float] : list of points coordinates (1D, 2D, 3D).
            groups [bool] : if True, creates a group for each point,(default False).
            info [int] : verbosity mode (1 or 2), (default 1).
        """
        assert info in (0, 1, 2, 4), "Invalid parameter"

        mcmesh = mesh_builder.pointcloud(coordlist=coordlist, groups=groups)

        # Convert to aster mesh
        mesh = cls()
        mesh.buildFromMedCouplingMesh(mcmesh, verbose=info)

        return mesh

    @classmethod
    def buildSpline1D(cls, coordlist, groups=False, info=1):
        """Build the mesh of a 1D spline from a set of coordinates.

        Arguments:
            coordlist list[float] : list of points coordinates (1D, 2D, 3D).
            groups [bool] : if True, creates a group for each point,(default False).
            info [int] : verbosity mode (1 or 2), (default 1).
        """
        assert info in (0, 1, 2, 4), "Invalid parameter"

        mcmesh = mesh_builder.spline1d(coordlist=coordlist, groups=groups)

        # Convert to aster mesh
        mesh = cls()
        mesh.buildFromMedCouplingMesh(mcmesh, verbose=info)

        return mesh

    def LIST_GROUP_NO(self):
        """Retourne la liste des groupes de noeuds sous la forme :
        [ (gno1, nb noeuds  gno1), ...]"""
        node_groups = self.getGroupsOfNodes()
        if not node_groups:
            return []
        return [(node_group, len(self.getNodes(node_group, True))) for node_group in node_groups]

    def LIST_GROUP_MA(self):
        """Retourne la liste des groupes de mailles sous la forme :
        [ (gma1, nb mailles gma1), ...]"""
        cell_groups = self.getGroupsOfCells()
        if not cell_groups:
            return []
        ngpma = []
        for grp in cell_groups:
            cells = self.getCells(grp)
            ngpma.append((grp.strip(), len(cells)))
        return ngpma

    def buildFromMedCouplingMesh(self, mcmesh, verbose=0):
        """Build mesh from medcoupling mesh.

        Arguments:
            mcmesh (*medcoupling.MEDFileUMesh*): The MEDCoupling mesh.
            verbose (int) : 0 - warnings
                            1 - informations about main steps
                            2 - informations about all steps
        """
        mesh_builder.buildFromMedCouplingMesh(self, mcmesh, verbose)

    def plot(self, command="gmsh", local=True):
        """Plot the mesh.

        Arguments:
            command (str): Program to be executed to plot the mesh.
            local (bool): Only used for a *ParallelMesh*.
        """
        # the file will be removed when 'tmpf' object will be deleted
        tmpf = tempfile.NamedTemporaryFile(suffix=".med")
        filename = tmpf.name
        # to avoid the warning on existing file
        os.remove(filename)
        self.printMedFile(filename)
        subprocess.run([ExecutionParameter().get_option(f"prog:{command}"), filename])

    def readMedFile(self, filename, meshname="", verbose=1):
        """Read a MED file containing a mesh.

        Arguments:
            filename (Path|[str): Name of the MED file
            meshname (str): Name of the mesh to be read from file.
            verbose (int): 0 - warnings, 1 - informations about main steps,
                2 - informations about all steps

        Returns:
            ParallelMesh: the object itself
        """
        mr = MedToAsterReader()
        mr.readMeshFromMedFile(self, os.fspath(filename), meshname, verbose & 3)
        return self

    def refine(self, ntimes=1, info=1):
        """Refine the mesh uniformly. Each edge is split in two.

        Arguments:
            ntimes [int] : the number of times the mesh is to be refined.
            info [int] : verbosity mode (1 or 2). Default 1.

        Returns:
            Mesh: the refined mesh.
        """

        new_mesh = CREA_MAILLAGE(
            MAILLAGE=self, RAFFINEMENT=_F(TOUT="OUI", NIVEAU=ntimes), INFO=info
        )
        return new_mesh

    def restrict(self, groupsOfCells, info=1):
        """Restrict the mesh to given groups of cells.

        groupsOfCells (list[str]): groups of cells to restrict the mesh on.
            info [int] : verbosity mode (1 or 2). Default 1.

        Returns:
            Mesh: the restricted mesh.
        """

        return CREA_MAILLAGE(
            MAILLAGE=self,
            RESTREINT=_F(GROUP_MA=groupsOfCells, TOUT_GROUP_MA="OUI", TOUT_GROUP_NO="OUI"),
            INFO=info,
        )

    def createMedCouplingMesh(self, spacedim_3d=False):
        """Returns the MEDCoupling unstructured mesh associated to the current mesh.

        Arguments:
            spacedim_3d (*bool*): if true, space dimension of mc mesh is forced to 3

        Returns:
            Mesh: The MEDCoupling unstructured mesh associated to the current mesh.
        """

        return convertMesh2MedCoupling(self, spacedim_3d)

    def getNodes(self, group_name=[], localNumbering=False, same_rank=None):
        """Return the list of the indexes of the nodes that belong to a group of nodes.

        Arguments:
            group_name (list[str]): Name of groups (default: []).
            localNumbering (bool): not used (for compatibilty with ParallelMesh)
            same_rank (bool): not used (for compatibilty with ParallelMesh)

        Returns:
            list[int]: Indexes of the nodes of groups.
        """

        val = {None: PythonBool.NONE, True: PythonBool.TRUE, False: PythonBool.FALSE}

        return self._getNodes(force_list(group_name), localNumbering, val[same_rank])

    def getNodesFromCells(self, group_name, localNumbering=False, same_rank=None):
        """Returns the nodes indexes of a group of cells.

        Arguments:
            group_name (str/list[str]): Name of the groups.
            localNumbering (bool): not used (for compatibilty with ParallelMesh)
            same_rank (bool): not used (for compatibilty with ParallelMesh)

        Returns:
            list[int]: Indexes of the nodes of the group.
        """

        val = {None: PythonBool.NONE, True: PythonBool.TRUE, False: PythonBool.FALSE}

        return self._getNodesFromCells(force_list(group_name), localNumbering, val[same_rank])

    def _getGroupsOfCellsContainingIds(self, idcell):
        """Returns the list of groups of cells containing the cell ids.

        *For debugging only, performance issues.*

        Arguments:
            idcell (int/list[int]): Cell idS to find.

        Returns:
            list[str]: Names of groups containing the cell ids.
        """

        return [
            grp
            for grp in self.getGroupsOfCells()
            if any(ids in self.getCells(grp) for ids in force_list(idcell))
        ]

    def _getGroupsOfNodesContainingIds(self, idnode):
        """Returns the list of groups of nodes containing the node ids.

        *For debugging only, performance issues.*

        Arguments:
            idnode (int/list[int]): Node idS to find.

        Returns:
            list[str]: Names of groups containing the node ids.
        """

        return [
            grp
            for grp in self.getGroupsOfNodes()
            if any(ids in self.getNodes(grp, True) for ids in force_list(idnode))
        ]
