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

import os

import numpy as np

from ..MedUtils.medtoasterconnectivity import (
    ASTER_TYPES,
    MED2ASTER_CONNECT,
    MED_TYPES,
    MYMED2ASTER_CONNECT,
    toAsterGeoType,
)
from ..Messages import UTMESS
from ..Objects import MedFileAccessType, MedFileReader
from ..Utilities import MPI, Timer, config, no_new_attributes
from ..Utilities import medcoupling as medc


def sorted_as_aster(fmt, types):
    """Sort a list of cell types (med|medcoupling) using aster order.

    Arguments:
        fmt (str) : med | medcoupling
        types (list): list of medcoupling types.

    Returns:
        list: list of types sorted following aster order.
    """

    if not hasattr(sorted_as_aster, "cache_dict"):
        sorted_as_aster.cache_dict = dict()
        sorted_as_aster.cache_dict["medcoupling"] = dict(
            zip(ASTER_TYPES, map(medc.MEDFileUMesh.ConvertFromMEDFileGeoType, MED_TYPES))
        )
        sorted_as_aster.cache_dict["med"] = dict(zip(ASTER_TYPES, MED_TYPES))

    assert fmt in ("medcoupling", "med")
    if fmt in ("medcoupling",):
        cache = sorted_as_aster.cache_dict["medcoupling"]
    elif fmt in ("med",):
        cache = sorted_as_aster.cache_dict["med"]
    else:
        assert False, "Invalid format"

    sorted_types = [cache[astype] for astype in ASTER_TYPES if cache[astype] in types]
    assert len(sorted_types) == len(types), "Invalid conversion"
    return sorted_types


class MEDCouplingMeshHelper:
    """This object extracts properties from a medcoupling mesh as expected
    to create or manipulate a code_aster mesh.
    """

    _mesh = _mesh_name = _file_name = _dim = _timer = None
    _coords = _groups_of_cells = _groups_of_nodes = _connectivity_aster = _cell_types = None
    _domains = _djoints = _nodesOwner = _gNodesNumbering = _node_range = _cell_range = None
    _cell_family = _node_family = _families = None
    _medc2aster_connect = {}

    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self):
        self._mesh = None
        self._mesh_name = ""
        self._file_name = ""
        self._dim = 0
        self._coords = None
        self._groups_of_cells = {}
        self._groups_of_nodes = {}
        self._connectivity_aster = []
        self._cell_types = []
        self._node_range = []
        self._cell_range = []
        # for the joints
        self._domains = []
        self._djoints = {}
        self._nodesOwner = []
        self._gNodesNumbering = []
        self._timer = Timer(title="medcoupling conversion")
        self._cell_family = []
        self._node_family = []
        self._families = {}

    def setMedCouplingMesh(self, medmesh):
        """Define the medcoupling mesh to be converted.

        Arguments:
            medmesh (medc.MEDFileUMesh): medcoupling mesh object.
        """
        self._mesh = medmesh
        self._mesh_name = medmesh.getName()

    def readMedFile(self, path: str, meshname: str = None):
        """Define the medcoupling mesh by reading a MED file.

        Arguments:
            path (Path|str): Path to the med file.
            meshname (str): Name of the mesh to be read from file.
        """
        self.setMedCouplingMesh(medc.MEDFileUMesh(os.fspath(path), meshname))
        self._file_name = path

    def buildMesh(self, mesh, verbose=0):
        """Convert the MEDCoupling mesh.

        Arguments:
            mesh (Mesh|ParallelMesh|IncompleteMesh): The Mesh object to be filled.
            verbose (int): Verbosity between 0 (a few details) to 2 (more verbosy).

        Returns:
            Mesh: The same Mesh/ParallelMesh object completed.
        """
        assert mesh.getDimension() == 0, "the mesh object is not empty"
        UTMESS("I", "MED_10", valk=self.name)
        timer = self._timer
        with timer("medcoupling parsing"):
            self.parse(mesh)
        if verbose & 4:
            self.debugPrint()
        with timer("nodes, connectivity"):
            mesh._initDefinition(
                max(self._dim, 2),
                self.coordinates,
                self.connectivity,
                self.types,
                len(self._groups_of_cells),
                len(self._groups_of_nodes),
            )
        if mesh.isIncomplete():
            mesh._setNodeFamily(self.nodeFamilies)
            mesh._setCellFamily(self.cellFamilies)
            fam = self.families
            for famId in fam:
                mesh._addFamily(famId, fam[famId])
        else:
            groups = self.groupsOfCells
            if groups:
                with timer("groups of cells"):
                    mesh._addGroupsOfCells(*groups)
            groups = self.groupsOfNodes
            if groups:
                with timer("groups of nodes"):
                    mesh._addGroupsOfNodes(*groups)
        if mesh.isParallel():
            with timer("creating joints"):
                mesh._create_joints(
                    self.domains, self.globalNodeIds, self.nodesOwner, [], self.getAllJoints(), 1
                )
        with timer("completion"):
            if not mesh.isIncomplete():
                mesh._endDefinition()
            else:
                mesh._setNodeRange(self._node_range)
                mesh._setCellRange(self._cell_range)
        # cheat code for debugging and detailed time informations: 1989
        with timer("show details"):
            mesh.show(verbose & 3)
        if verbose & 4:
            print(repr(timer), flush=True)
        return mesh

    def debugPrint(self):
        """Print internal content for debugging."""

        def _info_grp(groups, label):
            if not groups:
                return
            names, groups = groups
            cumsize = sum(map(len, groups))
            minsize = min(map(len, groups))
            meansize = cumsize / len(groups)
            maxsize = max(map(len, groups))
            etc = "..." if len(groups) > 10 else ""
            print(f"+ number of groups of {label}: {len(groups)}, first 10: {names[:10]}{etc}")
            print(f"+ cumsize of groups of {label}: {cumsize}")
            print(f"+ size of groups of {label} (min/mean/max): {minsize}/{meansize:.1f}/{maxsize}")

        print(f"+ mesh name: {self.name}")
        print(f"+ number of cells: {self.numberOfCells}")
        print(f"+ number of nodes: {self.numberOfNodes}")
        _info_grp(self.groupsOfCells, "cells")
        _info_grp(self.groupsOfNodes, "nodes")
        print(f"+ domains: {self.domains}")
        for key, jts in self._djoints.items():
            print(f"+ joints: {key}, size {len(jts)}: {jts[:10]}...")
        print(f"+ number of joints: {len(self._djoints) // 2}", flush=True)

    def parse(self, mesh):
        """Walk the medcoupling mesh to extract informations.

        Arguments:
            mesh (Mesh|ParallelMesh|IncompleteMesh): The Mesh object to be filled.
        """
        inc = mesh.isIncomplete()
        if self._file_name:
            min_vers = "3.0.0" if inc else "2.0.0"
            check_medfile_version(self._file_name, min_vers)
        if not inc:
            self.parseMesh()
        else:
            self.parseIncomplete()
        if not inc:
            with self._timer("extracting joints"):
                self.extract_joints()

    def parseMesh(self):
        """Walk the medcoupling mesh to extract informations."""
        mesh = self._mesh
        self._dim = mesh.getSpaceDimension()

        nbNodes = mesh.getNumberOfNodes()
        nodes_mc = mesh.getCoords().toNumPyArray()
        nodes_mc.shape = (nbNodes, self._dim)
        self._coords = np.zeros(shape=(nbNodes, 3))
        self._coords[:, : self._dim] = nodes_mc[:, : self._dim]

        non_empty_levels = mesh.getNonEmptyLevels()
        level_shift = 0  # Variable pour la creation d'une numérotation globale

        # Sortie groupes
        # Groupes de cells
        self._groups_of_cells = {}
        self._groups_of_nodes = {}

        self._connectivity_aster = []
        self._cell_types = []
        # groups = mesh.getGroupsNames()
        # NB: `mesh.getGroupsOnSpecifiedLev()` is necessary to avoid segfault
        #     without group of nodes/cells

        # Loop sur les niveaux
        for level in sorted(non_empty_levels):
            mesh_level = mesh[level]

            # Loop sur toutes les types du niveau
            types_at_level = sorted_as_aster("medcoupling", mesh_level.getAllGeoTypesSorted())
            for medcoupling_cell_type in types_at_level:
                # Cells du meme type
                cells_current_type = mesh_level.giveCellsWithType(medcoupling_cell_type)

                # Maillage 1 Single Geo Type (connectivité simple)
                mesh_current_type = medc.MEDCoupling1SGTUMesh(mesh_level[cells_current_type])

                # Type MED
                med_current_type = medc.MEDFileUMesh.ConvertToMEDFileGeoType(medcoupling_cell_type)

                # Nombre de noeuds du type
                number_of_nodes_current_type = (
                    medc.MEDCouplingUMesh.GetNumberOfNodesOfGeometricType(medcoupling_cell_type)
                )

                # Remise en forme en tableau
                connectivity_current_type = (
                    mesh_current_type.getNodalConnectivity()
                    .toNumPyArray()
                    .reshape(mesh_current_type.getNumberOfCells(), number_of_nodes_current_type)
                )

                if medcoupling_cell_type != medc.NORM_POINT1:
                    connectivity_current_type = connectivity_current_type[
                        :, self.getConnectivityMedToAster(medcoupling_cell_type)
                    ]

                # Shift de 1
                connectivity_current_type += 1

                # Sauvegarde de la connectivité aster au km
                self._connectivity_aster.extend(connectivity_current_type)
                # Sauvegarde du type med
                self._cell_types.extend([med_current_type] * mesh_current_type.getNumberOfCells())

            # Groupes de cells au niveau
            with self._timer(". store groups of cells"):
                groups = mesh.getGroupsOnSpecifiedLev(level)
                need_group_renumbering = types_at_level != mesh_level.getAllGeoTypesSorted()
                if need_group_renumbering and len(groups) != 0:
                    medc_cells_aster_order = medc.DataArrayInt.Aggregate(
                        [mesh_level.giveCellsWithType(t) for t in types_at_level]
                    )
                    n2o = medc_cells_aster_order.invertArrayO2N2N2O(mesh_level.getNumberOfCells())
                for group in groups:
                    if len(group) > 24:
                        UTMESS("A", "MED_7", valk=group)
                        continue
                    group_cells = mesh.getGroupArr(level, group).deepCopy()
                    if not group_cells:
                        continue
                    if need_group_renumbering:
                        group_cells.transformWithIndArr(n2o)
                    group_cells += 1
                    group_cells += level_shift
                    self._groups_of_cells.setdefault(group, [])
                    self._groups_of_cells[group].extend(group_cells.toNumPyArray())

            # Shift pour numeroration globale
            level_shift += mesh_level.getNumberOfCells()

        # Groupes de noeuds
        with self._timer(". store groups of nodes"):
            groups = mesh.getGroupsOnSpecifiedLev(1)
            for group in groups:
                if len(group) > 24:
                    UTMESS("A", "MED_7", valk=group)
                    continue
                group_nodes = mesh.getGroupArr(1, group).deepCopy()
                if not group_nodes:
                    continue
                group_nodes += 1
                self._groups_of_nodes.setdefault(group, [])
                self._groups_of_nodes[group].extend(group_nodes.toNumPyArray())

    def parseIncomplete(self):
        """Walk the medcoupling mesh to extract informations."""
        if not config.get("ASTER_HAVE_MED"):
            raise NotImplementedError("MED is required for this feature!")
        filename = self._file_name

        def splitElem(nodeNb, size, rank):
            nbNodesProc = int(nodeNb / size)
            startNode = nbNodesProc * rank
            endNode = nbNodesProc * (rank + 1)
            if rank == size - 1:
                endNode = nodeNb
            return [startNode, endNode]

        rank = MPI.ASTER_COMM_WORLD.Get_rank()
        size = MPI.ASTER_COMM_WORLD.Get_size()

        fr = MedFileReader()
        fr.openParallel(filename, MedFileAccessType.MedReadOnly)
        curMesh = fr.getMesh(0)
        seq = curMesh.getSequence(0)
        nodeNb = curMesh.getNodeNumberAtSequence(seq[0], seq[1])
        self._node_range = splitElem(nodeNb, size, rank)

        nbNodes = self._node_range[1] - self._node_range[0]
        nodes_mc = np.array(curMesh.readCoordinates(seq[0], seq[1]))
        self._dim = curMesh.getDimension()
        nodes_mc.shape = (nbNodes, self._dim)
        self._coords = np.zeros(shape=(nbNodes, 3))
        self._coords[:, : self._dim] = nodes_mc[:, : self._dim]
        cellTypes = curMesh.getGeometricTypesAtSequence(seq[0], seq[1])
        cellTypes = sorted_as_aster("med", cellTypes)
        self._connectivity_aster = []
        self._cell_types = []
        self._node_family = curMesh.getNodeFamilyAtSequence(seq[0], seq[1])
        families = curMesh.getFamilies()
        self._families = {}
        for curFam in families:
            self._families[curFam.getId()] = curFam.getGroups()
        totCellNb = 0
        for i in cellTypes:
            cellNb = curMesh.getCellNumberForGeometricTypeAtSequence(seq[0], seq[1], i)
            localSplit = splitElem(cellNb, size, rank)
            self._cell_range.append([localSplit[0] + totCellNb, localSplit[1] + totCellNb])
            curConn = curMesh.getConnectivityForGeometricTypeAtSequence(seq[0], seq[1], i)
            curConn = np.array(curConn)
            nbNodesForGeoT = curMesh.getNodeNumberForGeometricType(i)
            nbElem = int(len(curConn) / nbNodesForGeoT)
            curConn.shape = (nbElem, nbNodesForGeoT)
            curConn = curConn[:, MYMED2ASTER_CONNECT[i]]
            self._connectivity_aster.extend(curConn)
            self._cell_types.extend([i] * nbElem)
            curFam = curMesh.getCellFamilyForGeometricTypeAtSequence(seq[0], seq[1], i)
            self._cell_family.extend(curFam)
            totCellNb += cellNb

    def extract_joints(self):
        """Extract informations about joints between domains."""
        # _testrank is reserved for testcases, only with one process
        rank = MPI.ASTER_COMM_WORLD.Get_rank()
        self._nodesOwner = np.ones(self._mesh.getNumberOfNodes(), int) * rank
        domains = set()
        self._djoints = {}
        joints = self._mesh.getJoints()
        if joints:
            for name in joints.getJointsNames():
                joint = joints.getJointWithName(name)
                remote = joint.getDomainNumber()
                # assert remote < size and remote != rank # only in parallel!
                domains.add(remote)
                d_in, d_out = [int(i) for i in name.split()]
                assert rank in (
                    d_in,
                    d_out,
                ), f"inconsistent domains: {rank} not in ({d_in}, {d_out})"
                key = ("R" if d_in == rank else "E") + f"{remote:x}".upper()
                assert joint.getNumberOfSteps() == 1, "unexpected value"
                assert joint[0].getNumberOfCorrespondences() == 1, "unexpected value"
                values = joint[0][0].getCorrespondence().toNumPyArray().ravel()
                self._djoints[key] = values.tolist()
                if d_in == rank:
                    values.shape = (len(values) // 2, 2)
                    self._nodesOwner[values[:, 0] - 1] = -1

        self._domains = sorted(domains)
        globNumbNodes = self._mesh.getGlobalNumFieldAtLevel(1)
        if globNumbNodes:
            self._gNodesNumbering = globNumbNodes.toNumPyArray().tolist()

    def getAllJoints(self):
        """Return the definition of all the joints.

        Returns:
            list[list[int]]: Contains the definition of the joints E/R for the
            first domain, E/R for the second, etc. (`2 * number of domains`
            lists of integers).
        """
        if not self._domains:
            return []
        retlist = []
        for dom in self._domains:
            for typ in "ER":
                key = f"{typ}{dom:x}".upper()
                retlist.append(self._djoints[key])
        return retlist

    @property
    def domains(self):
        """list[int]: List of the remote domains."""
        return self._domains

    @property
    def globalNodeIds(self):
        """list[int]: List of the global number of each node."""
        return self._gNodesNumbering

    @property
    def nodesOwner(self):
        """list[int]: List of the owner of each node."""
        return self._nodesOwner

    @property
    def mesh(self):
        """medc.MEDFileUMesh: The medcoupling mesh."""
        return self._mesh

    @property
    def name(self):
        """str: The mesh name."""
        return self._mesh_name

    @property
    def numberOfNodes(self):
        """int: Number of nodes."""
        return self._coords.shape[0]

    @property
    def numberOfCells(self):
        """int: Number of cells."""
        return len(self._connectivity_aster)

    @property
    def coordinates(self):
        """list[float]: List of coordinates of each node."""
        return self._coords.flatten().tolist()

    @property
    def connectivity(self):
        """list[list[int]]: Connectivity as a list of lists."""
        return [cell.tolist() for cell in self._connectivity_aster]

    @property
    def families(self):
        """list[int]: Dictionary of families ."""
        return self._families

    @property
    def medtypes(self):
        """list[int]: List of med type for each cell."""
        return self._cell_types

    @property
    def types(self):
        """list[int]: List of code_aster type for each cell."""
        return [toAsterGeoType(i) for i in self._cell_types]

    @property
    def groupsOfCells(self):
        """dict: Dict of cells contained in each group of cells."""
        return list(zip(*self._groups_of_cells.items()))

    @property
    def groupsOfNodes(self):
        """dict: Dict of nodes contained in each group of nodes."""
        return list(zip(*self._groups_of_nodes.items()))

    @property
    def cellFamilies(self):
        """list[int]: List of family for each cells."""
        return self._cell_family

    @property
    def nodeFamilies(self):
        """list[int]: List of family for each nodes."""
        return self._node_family

    @classmethod
    def getConnectivityMedToAster(cls, medcoupling_type):
        """Return the code_aster connectivity of a medcoupling mesh type.

        Arguments:
            medcoupling_type (int): medcoupling type.

        Returns:
            list[int]: List of nodes.
        """
        if not cls._medc2aster_connect:
            cls._medc2aster_connect = {
                getattr(medc, "NORM_%s" % elem): nodes for elem, nodes in MED2ASTER_CONNECT.items()
            }
        return cls._medc2aster_connect[medcoupling_type]


def check_medfile_version(file_name, min_vers):
    """Check MED file version.

    Arguments:
        file_name (str): Path to the MED file.
        min_vers (str): Minimal required version (ex.: 3.0.0).
    """

    def _vers2tupl(verstr):
        res = []
        for i in verstr.split("."):
            try:
                num = int(i)
            except ValueError:
                num = i
            res.append(num)
        return tuple(res)

    med_vers_min = _vers2tupl(min_vers)
    med_vers_num = _vers2tupl(medc.MEDFileVersionOfFileStr(file_name))
    if med_vers_num < med_vers_min:
        UTMESS("F", "MED_20", valk=(min_vers, medc.MEDFileVersionOfFileStr(file_name)))
