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
:py:class:`FieldOnNodesReal` --- Fields defined on nodes of elements
********************************************************************

The *Field On Nodes* object exists for real numbers (:py:class:`FieldOnNodesReal`),
integers (:py:class:`FieldOnNodesLong`),
strings (:py:class:`FieldOnNodesChar8`) and
complex numbers (:py:class:`FieldOnNodesComplex`).
"""

import functools
import operator
import os.path as osp
import subprocess

from libaster import (
    DOFNumbering,
    FieldOnNodesChar8,
    FieldOnNodesComplex,
    FieldOnNodesLong,
    FieldOnNodesReal,
)

from ..Objects import PythonBool
from ..Utilities import MPI, ExecutionParameter, PETSc, config, force_list, injector, SharedTmpdir


@injector(FieldOnNodesReal)
class ExtendedFieldOnNodesReal:
    cata_sdj = "SD.sd_champ.sd_cham_no_class"

    def restrict(self, cmps=[], groupsOfNodes=[], same_rank=None):
        """Return a new field restricted to the list of components and groups of nodes given

        Arguments:
            cmps[list[str]]: filter on list of components
            If empty, all components are used
            groupsOfNodes[list[str]]: filter on list of groups of nodes (default=" ").
            If empty, the full mesh is used
            same_rank : - None: keep all nodes (default: None)
                        - True: keep the nodes which are owned by the current MPI-rank
                        - False: keep the nodes which are not owned by the current MPI-rank

        Returns:
            FieldOnNodesReal: field restricted.
        """

        val = {None: PythonBool.NONE, True: PythonBool.TRUE, False: PythonBool.FALSE}

        return self._restrict(force_list(cmps), force_list(groupsOfNodes), val[same_rank])

    def transfert(self, mesh, cmps=[]):
        """Tranfert the field to an other mesh. One of the mesh has to be a restriction
        to the other one.

        Arguments:
            mesh (Mesh) : mesh to use for transfert.
            cmps [list[str]]: filter on list of components. If empty, all components are used

        Returns:
            FieldOnNodesReal: field transfered to new mesh.
        """

        return self.toSimpleFieldOnNodes().transfert(mesh, cmps).toFieldOnNodes()

    def getValuesWithDescription(self, components=[], groups=[]):
        """Return the values of a component of the field.

        Arguments:
            components (list[str], optional): Extracted component or all components if
                it is empty.
            groups (list[str], optional): The extraction is limited to the given
                groups of nodes.

        Returns:
            tuple(values, description): List of values and description.
            The description provides a tuple with (nodes ids, components).
        """
        description, dofs = self.getDescription().getDOFsWithDescription(
            force_list(components), force_list(groups), local=True
        )
        values = self.getValues(dofs)
        return values, description

    @property
    @functools.lru_cache()
    def __NodeDOF2Row(self):
        """Build the indirection table between (nodeid, dof) and row"""
        ldofNumbering = [dep for dep in self.getDependencies() if isinstance(dep, DOFNumbering)]
        if not ldofNumbering:
            raise RuntimeError("Cannot retrieve dofNumbering")
        dofNumbering = [dep for dep in self.getDependencies() if isinstance(dep, DOFNumbering)][-1]
        # build the indirection table between (nodeid, dof) and row
        indir = {}
        nueq = dofNumbering.getEquationNumbering()
        phys_cmp = [cmp for cmp in dofNumbering.getComponents() if not cmp.startswith("LAGR")]
        for cmp in phys_cmp:
            ldx = nueq.getDOFsWithDescription([f"LAGR:{cmp}"])
            for node, row in enumerate(ldx[-1]):
                indir.setdefault((ldx[0][0][node], cmp), []).append(row)
        return indir

    def plot(self, command="gmsh", local=True, split=False):
        """Plot the field.

        Arguments:
            command (str): Program to be executed to plot the field.
            local (bool): Print in separate files if *True*. Otherwise an unique file is used.
            split (bool): Display the field on each subdomain separately if *True*. Otherwise the global field is displayed.
        """
        comm = MPI.ASTER_COMM_WORLD
        mesh = self.getMesh()
        opt = f"Mesh.VolumeEdges=0;Mesh.VolumeFaces=0;Mesh.SurfaceEdges=0;Mesh.SurfaceFaces=0;View[0].ShowElement=1;View[0].IntervalsType=3;"
        if local and mesh.isParallel():
            with SharedTmpdir("plot") as tmpdir:
                filename = osp.join(tmpdir.path, f"field_{comm.rank}.med")
                self.printMedFile(filename, local=True)
                comm.Barrier()
                if comm.rank == 0:
                    if split:
                        for i in range(comm.size):
                            ff = osp.join(tmpdir.path, f"field_{i}.med")
                            subprocess.run(
                                [
                                    ExecutionParameter().get_option(f"prog:{command}"),
                                    "-string",
                                    opt,
                                    ff,
                                ]
                            )
                    else:
                        files = [osp.join(tmpdir.path, f"field_{i}.med") for i in range(comm.size)]
                        subprocess.run(
                            [ExecutionParameter().get_option(f"prog:{command}"), "-string", opt]
                            + files
                        )
        else:
            with SharedTmpdir("plot") as tmpdir:
                filename = osp.join(tmpdir.path, "field.med")
                self.printMedFile(filename, local=False)
                if comm.rank == 0:
                    subprocess.run(
                        [
                            ExecutionParameter().get_option(f"prog:{command}"),
                            "-string",
                            opt,
                            filename,
                        ]
                    )
                comm.Barrier()
        print("waiting for all plotting processes...")
        comm.Barrier()

    def toPetsc(self, local=False):
        """Convert the field to a PETSc vector object.

        Arguments:
            local (bool): extract only the sequential vector of the subdomain or the global parallel vector (default False)

        Returns:
            PETSc.Vec: PETSc vector.
        """
        mesh = self.getMesh()
        if not config["ASTER_HAVE_PETSC"] or not config["ASTER_HAVE_PETSC4PY"]:
            raise RuntimeError("petsc4py is needed and is not installed")

        if mesh.isParallel():
            comm = MPI.ASTER_COMM_SELF if local else MPI.ASTER_COMM_WORLD
            _vec = PETSc.Vec().create(comm=comm)
            if local:
                _vec.setType("seq")
                val = self.getValues()
                neq = len(val)
                _vec.setSizes(neq)
                _vec.setValues(range(neq), val, PETSc.InsertMode.INSERT_VALUES)
            else:
                _vec.setType("mpi")
                if comm.Get_size() == 1:
                    val = self.getValues()
                    neq = len(val)
                    _vec.setSizes(neq)
                    _vec.setValues(range(neq), val, PETSc.InsertMode.INSERT_VALUES)
                else:
                    globNume = self.getDescription()
                    ownedRows = globNume.getNoGhostDOFs()
                    neql = len(ownedRows)
                    neqg = globNume.getNumberOfDOFs(local=False)
                    _vec.setSizes((neql, neqg))
                    val = self.getValues()
                    l2g = globNume.getLocalToGlobalMapping()
                    extract = operator.itemgetter(*ownedRows)
                    ll2g = extract(l2g)
                    lval = extract(val)
                    _vec.setValues(ll2g, lval, PETSc.InsertMode.INSERT_VALUES)
        else:
            _vec = PETSc.Vec().create()
            _vec.setType("mpi")
            val = self.getValues()
            neq = len(val)
            _vec.setSizes(neq)
            _vec.setValues(range(neq), val, PETSc.InsertMode.INSERT_VALUES)
        _vec.assemble()
        return _vec

    def setDirichletBC(self, **kwargs):
        """Set the values of the Dirichlet boundary conditions of the degrees
        of freedom on the group of nodes or cells.

        Arguments:
            GROUP_MA (str or list(str)): name of the group of cells
            GROUP_NO (str or list(str)): name of the group of nodes.
            NOEUD    (int or list(int)): indices of the nodes.
            DX, DY, ... (float): name and value of the degree of freedom
        """
        ldofNumbering = [dep for dep in self.getDependencies() if isinstance(dep, DOFNumbering)]
        if not ldofNumbering:
            raise RuntimeError("Cannot retrieve dofNumbering")
        dofNumbering = [dep for dep in self.getDependencies() if isinstance(dep, DOFNumbering)][-1]
        mesh = dofNumbering.getMesh()
        if mesh.isParallel():
            raise RuntimeError("No support for ParallelDOFNumbering")
        # build the group of nodes to be processed
        if not (
            "GROUP_MA" in kwargs.keys() or "GROUP_NO" in kwargs.keys() or "NOEUD" in kwargs.keys()
        ):
            raise ValueError(
                "a group of cells (GROUP_MA), a group of nodes (GROUP_NO)"
                " or a list of nodes (NOEUD) must be provided"
            )
        lNodes = []
        if "GROUP_MA" in kwargs.keys():
            lGrpMa = kwargs["GROUP_MA"]
            lGrpMa = [lGrpMa] if isinstance(lGrpMa, str) else lGrpMa
            connec = mesh.getConnectivity()
            for grMa in lGrpMa:
                if mesh.hasGroupOfNodes(grMa):
                    nodes = mesh.getNodes(grMa, localNumbering=True)
                    lNodes += nodes
                elif mesh.hasGroupOfCells(grMa):
                    nodes = [node for cell in mesh.getCells(grMa) for node in connec[cell]]
                    lNodes += nodes
                else:
                    raise ValueError("no {} group of cells".format(grMa))
        if "GROUP_NO" in kwargs.keys():
            lgrNo = kwargs["GROUP_NO"]
            lgrNo = [lgrNo] if isinstance(lgrNo, str) else lgrNo
            for grNo in lgrNo:
                if mesh.hasGroupOfNodes(grNo):
                    nodes = mesh.getNodes(grNo, localNumbering=True)
                    lNodes += nodes
                else:
                    raise ValueError("no {} group of nodes".format(grNo))
        if "NOEUD" in kwargs.keys():
            lNo = kwargs["NOEUD"]
            lNo = [lNo - 1] if isinstance(lNo, int) else [no - 1 for no in lNo]
            lNodes += lNo
        # keep unique node id
        lNodes = list(set(lNodes))
        # change the given values
        assignedDOF = 0
        self.updateValuePointers()  # update Jeveux pointers before assignment
        for node in lNodes:
            for dof, val in kwargs.items():
                if dof in ["GROUP_MA", "GROUP_NO", "NOEUD"]:  # only process DOF here
                    continue
                if (node, dof) in self.__NodeDOF2Row.keys():
                    assignedDOF += 1
                    for row in self.__NodeDOF2Row[(node, dof)]:
                        self[row] = val
        if assignedDOF == 0:
            raise ValueError(
                "No bounday condition has been set - no entity handle the given degree of freedom"
            )


@injector(FieldOnNodesLong)
class ExtendedFieldOnNodesLong:
    cata_sdj = "SD.sd_champ.sd_cham_no_class"


@injector(FieldOnNodesChar8)
class ExtendedFieldOnNodesChar8:
    cata_sdj = "SD.sd_champ.sd_cham_no_class"


@injector(FieldOnNodesComplex)
class ExtendedFieldOnNodesComplex:
    cata_sdj = "SD.sd_champ.sd_cham_no_class"

    def restrict(self, cmps=[], groupsOfNodes=[], same_rank=None):
        """Return a new field restricted to the list of components and groups of nodes given

        Arguments:
            cmps[list[str]]: filter on list of components
            If empty, all components are used
            groupsOfNodes[list[str]]: filter on list of groups of nodes (default=" ").
            If empty, the full mesh is used
            same_rank : - None: keep all nodes (default: None)
                        - True: keep the nodes which are owned by the current MPI-rank
                        - False: keep the nodes which are not owned by the current MPI-rank

        Returns:
            FieldOnNodesComplex: field restricted.
        """

        val = {None: PythonBool.NONE, True: PythonBool.TRUE, False: PythonBool.FALSE}

        return self._restrict(force_list(cmps), force_list(groupsOfNodes), val[same_rank])

    def getValuesWithDescription(self, component=[], groups=[]):
        """Return the values of a component of the field.

        Arguments:
            component (str, optional): Extracted component or all components if
                it is empty.
            groups (list[str], optional): The extraction is limited to the given
                groups of nodes.

        Returns:
            tuple(values, description): List of values and description.
            The description provides a tuple with (nodes ids, components).
        """
        description, dofs = self.getDescription().getDOFsWithDescription(
            force_list(component), force_list(groups), local=True
        )
        values = self.getValues(dofs)
        return values, description
