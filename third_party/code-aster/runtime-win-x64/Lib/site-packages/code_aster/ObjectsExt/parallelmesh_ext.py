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
:py:class:`ParallelMesh` --- Assignment of parallel mesh
************************************************************************
"""

import math
import os
import os.path as osp

import numpy as np

from ..CodeCommands import CREA_MAILLAGE
from ..MedUtils import splitMeshFromMedFile
from ..MedUtils.MedConverter import convertMesh2MedCoupling
from ..Messages import UTMESS
from ..Objects import (
    CommGraph,
    ConnectionMesh,
    IncompleteMesh,
    MedFileAccessType,
    MedFileReader,
    Mesh,
    MeshBalancer,
    MedToAsterReader,
    ParallelMesh,
    PythonBool,
    ResultNaming,
)
from ..Objects.Serialization import InternalStateBuilder
from ..ObjectsExt import mesh_builder
from ..Utilities import MPI, ExecutionParameter, Options, SharedTmpdir, force_list, injector
from .simplefieldonnodes_ext import SimpleFieldOnNodesReal


class ParallelMeshStateBuilder(InternalStateBuilder):
    """Class that returns the internal state of a *ParallelMesh*."""

    def restore(self, mesh):
        """Restore the *DataStructure* content from the previously saved internal
        state.

        Arguments:
            mesh (*DataStructure*): The *DataStructure* object to be restored.
        """
        super().restore(mesh)
        mesh.build()
        mesh._updateGlobalGroupOfNodes()
        mesh._updateGlobalGroupOfCells()


@injector(ParallelMesh)
class ExtendedParallelMesh:
    cata_sdj = "SD.sd_maillage.sd_maillage"
    internalStateBuilder = ParallelMeshStateBuilder

    def getCoordinatesAsSimpleFieldOnNodes(self):
        """Same as :py:meth:`getCoordinates` with a conversion into a *SimpleFieldOnNodes*.

        Returns:
            *SimpleFieldOnNodesReal*: Coordinates as a *SimpleFieldOnNodes*.
        """
        return self.getCoordinates().toFieldOnNodes(self).toSimpleFieldOnNodes()

    def plot(self, command="gmsh", local=True, split=False):
        """Plot the mesh.

        Arguments:
            command (str): Program to be executed to plot the mesh.
            local (bool): Print in separate files if *True*. Otherwise an unique file is used.
            split (bool): Display each subdomain separately if *True*. Otherwise the global mesh is displayed.
        """
        comm = MPI.ASTER_COMM_WORLD
        self.getOwnerField().plot(command=command, local=local, split=split)
        print("waiting for all plotting processes...")
        comm.Barrier()

    def readMedFile(
        self, filename, meshname="", partitioned=False, deterministic=False, ghost=1, verbose=0
    ):
        """Read a MED file containing a mesh and eventually partition it.

        Arguments:
            filename (Path|str): Name of the MED file.
            meshname (str): Name of the mesh to be read from file.
            partitioned (bool): False if the mesh is not yet partitioned and have to
                be partitioned before reading.
            deterministic (bool): True if partitioning must be deterministic
            ghost (int): ghost layer number
            verbose (int): Verbosity between 0 (a few details) to 2 (more verbosy).

        Returns:
            ParallelMesh: the object itself
        """
        if not partitioned:
            returnTuple = splitMeshFromMedFile(
                filename, ghost=ghost, outMesh=self, deterministic=deterministic
            )
            self = returnTuple[0]
            self.show(verbose & 3)
        else:
            mr = MedToAsterReader()
            mr.readParallelMeshFromMedFile(self, os.fspath(filename), meshname, verbose & 3)
        return self

    def checkConsistency(self, filename):
        """Check that the partitioned mesh is consistent, i.e. that all nodes,
           cells and groups are present.

           This method is memory consumption since the sequential mesh is loaded

        Arguments:
            filename (string): name of the full MED file

        Returns:
            bool: True if the partitioned mesh is consistent
        """
        comm = MPI.ASTER_COMM_WORLD
        # read std mesh
        nb_nodes_lc = len(self.getInnerNodes())
        nb_nodes_gl = comm.allreduce(nb_nodes_lc, MPI.SUM)

        nb_cells_lc = len(self.getInnerCells())
        nb_cells_gl = comm.allreduce(nb_cells_lc, MPI.SUM)

        test = True
        if comm.rank == 0:
            mesh = Mesh()
            mesh.readMedFile(filename)

            # tests
            group_no_std = mesh.getGroupsOfNodes(local=False)
            group_no_gl = self.getGroupsOfNodes(local=False)
            test1 = sorted(group_no_std) == sorted(group_no_gl)
            test = test and test1
            if not test1:
                print(
                    f"FAILED {filename} Groups of nodes differ:",
                    sorted(group_no_std),
                    sorted(group_no_gl),
                )

            group_ma_std = mesh.getGroupsOfCells(local=False)
            group_ma_gl = self.getGroupsOfCells(local=False)
            test1 = sorted(group_ma_std) == sorted(group_ma_gl)
            test = test and test1
            if not test1:
                print(
                    f"FAILED {filename} Groups of cells differ:",
                    sorted(group_ma_std),
                    sorted(group_ma_gl),
                )

            nb_nodes_std = mesh.getNumberOfNodes()
            test1 = nb_nodes_std == nb_nodes_gl
            test = test and test1
            if not test1:
                print(f"FAILED {filename} Number of nodes differs:", nb_nodes_std, nb_nodes_gl)

            nb_cells_std = mesh.getNumberOfCells()
            test1 = nb_cells_std == nb_cells_gl
            test = test and test1
            if not test1:
                print(f"FAILED {filename} Number of cells differs:", nb_cells_std, nb_cells_gl)

        return comm.bcast(test, root=0)

    def checkJoints(self):
        """Check joints of parallel mesh

        Returns:
            bool: True if the partitioned mesh is ok
        """
        comm = MPI.ASTER_COMM_WORLD
        l2G = self.getLocalToGlobalNodeIds()
        graph = CommGraph()

        dictProc = {}
        cmpt = 0
        for proc in self.getOppositeDomains():
            graph.addCommunication(proc)
            dictProc[proc] = cmpt
            cmpt += 1
        graph.synchronizeOverProcesses()

        outN = self.getOuterNodes()
        dictOutN = {}
        for nId in outN:
            dictOutN[nId + 1] = 1

        coords = self.getCoordinates()

        matchings = graph.getMatchings()
        toReturn = True
        for procT in matchings:
            proc = procT[1]
            tag = procT[0]
            if proc == -1:
                continue
            numJoint = dictProc[proc]
            fJ = self.getSendJoint(numJoint)
            gFJ = []
            curCoordsFJ = []
            for i in range(int(len(fJ) / 2)):
                nId = fJ[2 * i]
                gFJ.append(l2G[nId - 1])
                curCoordsFJ.append(coords[(nId - 1)])

            sJ = self.getReceiveJoint(numJoint)
            gSJ = []
            curCoordsSJ = []
            for i in range(int(len(sJ) / 2)):
                nId = sJ[2 * i]
                dictOutN.pop(nId)
                gSJ.append(l2G[nId - 1])
                curCoordsSJ.append(coords[(nId - 1)])

            if proc < comm.rank:
                comm.send(gFJ, dest=proc, tag=tag)
                data1 = comm.recv(source=proc, tag=tag)
                if data1 != gFJ:
                    print(
                        f"Rank {comm.rank}: Opposite domain {proc}, Joint number {numJoint}: NOOK"
                    )
                    toReturn = False
                comm.send(curCoordsFJ, dest=proc, tag=tag)
                data2 = comm.recv(source=proc, tag=tag)
                tab1 = np.array(curCoordsFJ)
                tab2 = np.array(data2)
                if np.allclose(tab1, tab2, atol=1e-12) is not True:
                    toReturn = False
                    print("Node joint coordinates are not matching")
            else:
                data1 = comm.recv(source=proc, tag=tag)
                comm.send(gSJ, dest=proc, tag=tag)
                if data1 != gSJ:
                    print(
                        f"Rank {comm.rank}: Opposite domain {proc}, Joint number {numJoint}: NOOK"
                    )
                    toReturn = False
                comm.send(curCoordsSJ, dest=proc, tag=tag)
                data2 = comm.recv(source=proc, tag=tag)
                tab1 = np.array(curCoordsSJ)
                tab2 = np.array(data2)
                if np.allclose(tab1, tab2, atol=1e-12) is not True:
                    toReturn = False
                    print("Node joint coordinates are not matching")
        if len(dictOutN) != 0:
            print("Some outer nodes are not in a joint")
            toReturn = False
        return toReturn

    def refine(self, ntimes=1, info=1):
        """Refine the mesh uniformly. Each edge is split in two.

        Arguments:
            ntimes [int] : the number of times the mesh is to be refined.
            info [int] : verbosity mode (1 or 2). Default 1.

        Returns:
            ParallelMesh: the refined mesh.
        """

        return CREA_MAILLAGE(MAILLAGE=self, RAFFINEMENT=_F(TOUT="OUI", NIVEAU=ntimes), INFO=info)

    def restrict(self, groupsOfCells, info=1):
        """Restrict the mesh to given groups of cells.

        groupsOfCells (list[str]): groups of cells to restrict the mesh on.
            info [int] : verbosity mode (1 or 2). Default 1.

        Returns:
            ParallelMesh: the restricted mesh.
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

    @classmethod
    def buildSquare(cls, l=1, refine=0, ghost=1, info=1, deterministic=False):
        """Build the quadrilateral mesh of a square.

        Arguments:
            l [float] : size of the cube (default 1.).
            refine [int] : number of mesh refinement iterations (default 0).
            info [int] : verbosity mode (1 or 2). (default 1).
        """
        # Refine some levels on whole mesh, the remaining after partitioning
        min_level = 6
        refine_0 = min(min_level, refine)
        refine_1 = refine - refine_0

        with SharedTmpdir("buildSquare") as tmpdir:
            filename = osp.join(tmpdir.path, "buildSquare.med")
            if MPI.ASTER_COMM_WORLD.rank == 0:
                mesh = Mesh.buildSquare(l=l, refine=refine_0, info=info)
                mesh.printMedFile(filename)
            ResultNaming.syncCounter()

            # Mesh creation
            mesh_p = cls()
            mesh_p.readMedFile(filename, deterministic=deterministic, ghost=ghost, verbose=info - 1)
            return mesh_p.refine(refine_1, info)

    @classmethod
    def buildRectangle(
        cls, lx=1, ly=1, nx=1, ny=1, refine=0, ghost=1, info=1, quadratic=False, deterministic=False
    ):
        """Build the quadrilateral mesh of a square.

        Arguments:
            lx [float] : length along the x axis (default 1.).
            ly [float] : length along the y axis (default 1.).
            nx [int] : number of elements along the x axis (default 1).
            ny [int] : number of elements along the y axis (default 1).
            refine [int] : number of mesh refinement iterations (default 0).
            info [int] : verbosity mode (0|1|2). (default 1).
        """
        # Refine some levels on whole mesh, the remaining after partitioning
        min_level = 9
        refine_0 = min(min_level, refine)
        refine_1 = refine - refine_0

        with SharedTmpdir("buildRectangle") as tmpdir:
            filename = osp.join(tmpdir.path, "buildRectangle.med")
            if MPI.ASTER_COMM_WORLD.rank == 0:
                mesh = Mesh.buildRectangle(lx=lx, ly=ly, nx=nx, ny=ny, refine=refine_0, info=info)
                if quadratic:
                    mesh = mesh.convertToQuadratic()
                mesh.printMedFile(filename)
            ResultNaming.syncCounter()

            # Mesh creation
            mesh_p = cls()
            mesh_p.readMedFile(filename, deterministic=deterministic, ghost=ghost, verbose=info - 1)
            return mesh_p.refine(refine_1, info)

    @classmethod
    def buildCheckerboardRectangle(cls, lx=1, ly=1, nx_loc=1, ny_loc=1, ghost=1, info=1):
        """Build the quadrilateral mesh of a rectangle, distributed as a checkerboard
        (aka no use of a partitioner)

        Arguments:
            lx [float] : length along the x axis (default 1.).
            ly [float] : length along the y axis (default 1.).
            nx_loc [int] : number of elements along the x axis in a subdomain (default 1).
            ny_loc [int] : number of elements along the y axis in a subdomain (default 1).
            info [int] : verbosity mode (0|1|2). (default 1).
        """
        size = MPI.ASTER_COMM_WORLD.Get_size()
        rank = MPI.ASTER_COMM_WORLD.Get_rank()
        size_sqrt = math.sqrt(size)
        if (size_sqrt - int(size_sqrt)) != 0:
            raise ValueError(
                (
                    "With a 2D checkerboard mesh, the number of MPI processes must be a power of 2."
                    f" You requested {size} MPI processes which is not of power of 2."
                )
            )
        # number of subdomains in the x-direction
        x_size = int(np.sqrt(size))
        # global sizes
        nx = nx_loc * x_size

        # Compute 2D coordinates of this rank in the process grid
        rx = rank % x_size
        ry = rank // x_size
        loc_nodes = []
        for j in range(ry * ny_loc, (ry + 1) * ny_loc):
            for i in range(rx * nx_loc, (rx + 1) * nx_loc):
                loc_nodes.append(j * nx + i + 1)  # 1-based indexing

        tmpdir = SharedTmpdir("buildRectangle")
        filename = osp.join(tmpdir.path, "buildRectangle.med")
        # Sequential build
        if rank == 0:
            seqMesh = Mesh.buildRectangle(lx=lx, ly=ly, nx=nx - 1, ny=ny_loc * x_size - 1)
            seqMesh.printMedFile(filename)
        else:
            # mandatory so that the meshes that will be created after on the other processes share the same name
            seqMesh = Mesh()
        MPI.ASTER_COMM_WORLD.Barrier()
        # Parallel mesh creation
        fr = MedFileReader()
        fr.openParallel(filename, MedFileAccessType.MedReadOnly)
        inComMesh = IncompleteMesh()
        inComMesh.readMedFile(filename, verbose=0)
        bMesh = MeshBalancer()
        bMesh.buildFromBaseMesh(inComMesh)
        mesh_p = ParallelMesh()
        mesh_p = bMesh.applyBalancingStrategy(loc_nodes, mesh_p, ghost_layer=ghost)

        return mesh_p

    @classmethod
    def buildCheckerboardParallelepiped(
        cls, lx=1, ly=1, lz=1, nx_loc=1, ny_loc=1, nz_loc=1, ghost=1, info=1
    ):
        """Build the hexaedral mesh of a parallelepiped, distributed as a checkerboard
        (aka no use of a partitioner)

        Arguments:
            lx [float] : length along the x axis (default 1.).
            ly [float] : length along the y axis (default 1.).
            lz [float] : length along the z axis (default 1.).
            nx_loc [int] : number of elements along the x axis in a subdomain (default 1).
            ny_loc [int] : number of elements along the y axis in a subdomain (default 1).
            nz_loc [int] : number of elements along the z axis in a subdomain (default 1).
            info [int] : verbosity mode (0|1|2). (default 1).
        """
        size = MPI.ASTER_COMM_WORLD.Get_size()
        rank = MPI.ASTER_COMM_WORLD.Get_rank()
        # use math.cbrt with python>=3.11
        size_cbrt = np.cbrt(size)
        if (size_cbrt - int(size_cbrt)) != 0:
            raise ValueError(
                (
                    "With a 3D checkerboard mesh, the number of MPI processes must be a power of 3."
                    f" You requested {size} MPI processes which is not of power of 3."
                )
            )
        # number of subdomains in the x-direction
        x_size = int(size_cbrt)
        # global sizes
        nx = nx_loc * x_size
        ny = ny_loc * x_size

        # Compute 3D coordinates of this rank in the process grid
        rz = rank // (x_size * x_size)
        rem = rank % (x_size * x_size)
        ry = rem // x_size
        rx = rem % x_size

        loc_nodes = []
        for k in range(rz * nz_loc, (rz + 1) * nz_loc):
            for j in range(ry * ny_loc, (ry + 1) * ny_loc):
                for i in range(rx * nx_loc, (rx + 1) * nx_loc):
                    node_id = k * (ny * nx) + j * nx + i + 1  # 1-based indexing
                    loc_nodes.append(node_id)

        tmpdir = SharedTmpdir("buildParallele")
        filename = osp.join(tmpdir.path, "buildParallele.med")
        # Sequential build
        if rank == 0:
            tempMesh = mesh_builder.parallelepiped(
                xmin=0.0,
                xmax=lx,
                ymin=0.0,
                ymax=ly,
                zmin=0.0,
                zmax=lz,
                nx=nx - 1,
                ny=ny - 1,
                nz=nz_loc * x_size - 1,
            )
            seqMesh = Mesh()
            seqMesh.buildFromMedCouplingMesh(tempMesh)
            seqMesh.printMedFile(filename)
        else:
            # mandatory so that the meshes that will be created after on the other processes share the same name
            seqMesh = Mesh()
        MPI.ASTER_COMM_WORLD.Barrier()
        # Parallel mesh creation
        fr = MedFileReader()
        fr.openParallel(filename, MedFileAccessType.MedReadOnly)
        inComMesh = IncompleteMesh()
        inComMesh.readMedFile(filename, verbose=0)
        bMesh = MeshBalancer()
        bMesh.buildFromBaseMesh(inComMesh)
        mesh_p = ParallelMesh()
        mesh_p = bMesh.applyBalancingStrategy(loc_nodes, mesh_p, ghost_layer=ghost)

        return mesh_p

    @classmethod
    def buildCube(cls, l=1, refine=0, ghost=1, info=1, deterministic=False):
        """Build the quadrilateral mesh of a cube.

        Arguments:
            l [float] : size of the cube (default 1.).
            refine [int] : number of mesh refinement iterations (default 0).
            info [int] : verbosity mode (1 or 2). (default 1).
        """
        # Refine some levels on whole mesh, the remaining after partitioning
        min_level = 7 if MPI.ASTER_COMM_WORLD.size > 512 else 6
        refine_0 = min(min_level, refine)
        refine_1 = refine - refine_0

        with SharedTmpdir("buildCube") as tmpdir:
            filename = osp.join(tmpdir.path, "buildCube.med")
            if MPI.ASTER_COMM_WORLD.rank == 0:
                mesh = Mesh.buildCube(l=l, refine=refine_0, info=info)
                mesh.printMedFile(filename)
            ResultNaming.syncCounter()

            # Mesh creation
            mesh_p = cls()
            mesh_p.readMedFile(filename, deterministic=deterministic, ghost=ghost, verbose=info - 1)
            return mesh_p.refine(refine_1, info)

    @classmethod
    def buildDisk(cls, radius=1, refine=0, ghost=1, info=1, deterministic=False):
        """Build the quadrilateral mesh of a disk.

        Arguments:
            radius [float] : radius of the disk (default 1).
            refine [int] : number of mesh refinement iterations (default 0).
            info [int] : verbosity mode (1 or 2). (default 1).
        """
        # Refine some levels on whole mesh, the remaining after partitioning
        min_level = 6
        refine_0 = min(min_level, refine)
        refine_1 = refine - refine_0

        with SharedTmpdir("buildDisk") as tmpdir:
            filename = osp.join(tmpdir.path, "buildDisk.med")
            if MPI.ASTER_COMM_WORLD.rank == 0:
                mesh = Mesh.buildDisk(radius=radius, refine=refine_0, info=info)
                mesh.printMedFile(filename)
            ResultNaming.syncCounter()

            # Mesh creation
            mesh_p = cls()
            mesh_p.readMedFile(filename, deterministic=deterministic, ghost=ghost, verbose=info - 1)
            return mesh_p.refine(refine_1, info)

    @classmethod
    def buildCylinder(cls, height=3, radius=1, refine=0, ghost=1, info=1, deterministic=False):
        """Build the hexaedral mesh of a cylinder.

        Arguments:
            height [float] : height of the cylinder along the z axis (default 0).
            radius [float] : radius of the cylinder (default 1).
            refine [int] : number of mesh refinement iterations (default 0).
            info [int] : verbosity mode (1 or 2). (default 1).
        """
        # Refine some levels on whole mesh, the remaining after partitioning
        min_level = 6
        refine_0 = min(min_level, refine)
        refine_1 = refine - refine_0

        with SharedTmpdir("buildCylinder") as tmpdir:
            filename = osp.join(tmpdir.path, "buildCylinder.med")
            if MPI.ASTER_COMM_WORLD.rank == 0:
                mesh = Mesh.buildCylinder(height=height, radius=radius, refine=refine_0, info=info)
                mesh.printMedFile(filename)
            ResultNaming.syncCounter()

            # Mesh creation
            mesh_p = cls()
            mesh_p.readMedFile(filename, deterministic=deterministic, ghost=ghost, verbose=info - 1)
            return mesh_p.refine(refine_1, info)

    @classmethod
    def buildRing(cls, rint=0.1, rext=1, refine=0, ghost=1, info=1, deterministic=False):
        """Build the mesh of a ring.

        Arguments:
            rint [float] : internal radius (default 0.1).
            rext [float] : external radius (default 1).
            refine [int] : number of mesh refinement iterations (default 0).
            info [int] : verbosity mode (0|1|2). (default 1).
        """
        # Refine some levels on whole mesh, the remaining after partitioning
        min_level = 6
        refine_0 = min(min_level, refine)
        refine_1 = refine - refine_0

        with SharedTmpdir("buildRing") as tmpdir:
            filename = osp.join(tmpdir.path, "buildRing.med")
            if MPI.ASTER_COMM_WORLD.rank == 0:
                mesh = Mesh.buildRing(rint=rint, rext=rext, refine=refine_0, info=info)
                mesh.printMedFile(filename)
            ResultNaming.syncCounter()

            # Mesh creation
            mesh_p = cls()
            mesh_p.readMedFile(filename, deterministic=deterministic, ghost=ghost, verbose=info - 1)
            return mesh_p.refine(refine_1, info)

    @classmethod
    def buildTube(cls, height=3, rint=0.1, rext=1, refine=0, ghost=1, info=1, deterministic=False):
        """Build the mesh of a tube.

        Arguments:
            height [float] : height along the z axis (default 3).
            rint [float] : internal radius (default 0.1).
            rext [float] : external radius (default 1).
            refine [int] : number of mesh refinement iterations (default 0).
            info [int] : verbosity mode (1 or 2). (default 1).
        """
        # Refine some levels on whole mesh, the remaining after partitioning
        min_level = 6
        refine_0 = min(min_level, refine)
        refine_1 = refine - refine_0

        with SharedTmpdir("buildTube") as tmpdir:
            filename = osp.join(tmpdir.path, "buildTube.med")
            if MPI.ASTER_COMM_WORLD.rank == 0:
                mesh = Mesh.buildTube(
                    height=height, rint=rint, rext=rext, refine=refine_0, info=info
                )
                mesh.printMedFile(filename)
            ResultNaming.syncCounter()

            # Mesh creation
            mesh_p = cls()
            mesh_p.readMedFile(filename, deterministic=deterministic, ghost=ghost, verbose=info - 1)
            return mesh_p.refine(refine_1, info)

    def getNodes(self, group_name=[], localNumbering=False, same_rank=None):
        """Return the list of the indexes of the nodes that belong to a group of nodes.

        Arguments:
            group_name (str): Name of groups (default: [] = all nodes).
            localNumbering (bool) : use local or global numbering (default: True)
            same_rank : - None: keep all nodes (default: None)
                        - True: keep the nodes which are owned by the current MPI-rank
                        - False: keep the nodes which are not owned by the current MPI-rank

        Returns:
            list[int]: Indexes of the nodes of groups.
        """

        val = {None: PythonBool.NONE, True: PythonBool.TRUE, False: PythonBool.FALSE}

        return self._getNodes(force_list(group_name), localNumbering, val[same_rank])

    def getNodesFromCells(self, group_name, localNumbering=False, same_rank=None):
        """Returns the nodes indexes of a group of cells.

        Arguments:
            group_name (str/list[str]): Name of the group.
            localNumbering (bool) : use local or global numbering (default: True)
            same_rank : - None: keep all nodes (default: None)
                        - True keep the nodes which are owned by the current MPI-rank
                        - False: keep the nodes which are not owned by the current MPI-rank

        Returns:
            list[int]: Indexes of the nodes of the group.
        """

        val = {None: PythonBool.NONE, True: PythonBool.TRUE, False: PythonBool.FALSE}

        return self._getNodesFromCells(force_list(group_name), localNumbering, val[same_rank])

    def getOwnerField(self):
        """Returns a field of the ranks that owns the nodes.

        Returns:
            FieldOnNodesReal: The field.
        """

        val = self.getNodesOwner()
        sf = SimpleFieldOnNodesReal(self, "NEUT_R", ["X1"], True)

        for inode, prop in enumerate(val):
            sf[inode, 0] = prop

        f = sf.toFieldOnNodes()

        return f

    def getNumberingField(self):
        """Returns a field of the nodes global numbering.

        Returns:
            FieldOnNodesReal: The field.
        """

        sf = SimpleFieldOnNodesReal(self, "NEUT_R", ["X1"], True)
        l2G = self.getLocalToGlobalNodeIds()

        for inode in range(len(l2G)):
            sf[inode, 0] = l2G[inode]

        f = sf.toFieldOnNodes()

        return f


@injector(ConnectionMesh)
class ExtendedConnectionMesh:
    cata_sdj = "SD.sd_maillage.sd_connection_mesh"


@injector(IncompleteMesh)
class ExtendedIncompleteMesh:
    cata_sdj = "SD.sd_maillage.sd_maillage"

    def readMedFile(self, filename, meshname="", verbose=1):
        """Read a MED file containing a mesh.

        Arguments:
            filename (string): name of the MED file
            meshname (str): Name of the mesh to be read from file.
            verbose (int) : 0 - warnings
                            1 - informations about main steps
                            2 - informations about all steps
        """
        mr = MedToAsterReader()
        mr.readIncompleteMeshFromMedFile(self, os.fspath(filename), meshname, verbose & 3)
