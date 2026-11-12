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
:py:class:`FieldOnCellsReal` --- Fields defined on nodes of elements
********************************************************************

The *Field On Nodes* object exists for real numbers (:py:class:`FieldOnCellsReal`),
integers (:py:class:`FieldOnCellsLong`),
strings (:py:class:`FieldOnCellsChar8`) and
complex numbers (:py:class:`FieldOnCellsComplex`).
"""

import os.path as osp
import subprocess

from libaster import FieldOnCellsReal, FieldOnCellsLong, FieldOnCellsChar8, FieldOnCellsComplex
from ..Utilities import injector, force_list
from ..Utilities import MPI, ExecutionParameter, SharedTmpdir


@injector(FieldOnCellsReal)
class ExtendedFieldOnCellsReal:
    cata_sdj = "SD.sd_champ.sd_cham_elem_class"

    def getValuesWithDescription(self, components=[], groups=[]):
        """Return the values of a component of the field.

        Arguments:
            components (list[str]): Extracted components.
            groups (list[str], optional): The extraction is limited to the given
                groups of cells.

        Returns:
            tuple(values, description): List of values and description.
            The description provides a tuple with identifiers of
            (cells, points, subpoints).
        """

        return self.toSimpleFieldOnCells().getValuesWithDescription(force_list(components), groups)

    def plot(self, command="gmsh", local=True, split=False):
        """Plot the field.

        Arguments:
            command (str): Program to be executed to plot the field.
            local (bool): Print in separate files if *True*. Otherwise an unique file is used.
            split (bool): Display the field on each subdomain separately if *True*. Otherwise the global field is displayed.
        """
        comm = MPI.ASTER_COMM_WORLD
        mesh = self.getMesh()
        opt = "Mesh.VolumeEdges = 0;Mesh.VolumeFaces=0;Mesh.SurfaceEdges=0;Mesh.SurfaceFaces=0;View[0].ShowElement = 1;"
        if (local and mesh.isParallel()) or (split and mesh.isParallel()):
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
        print("waiting for all plotting processes...")
        comm.Barrier()

    def asPhysicalQuantity(self, physQuantity, map_cmps, fed=None):
        """Return a new field with a new physical quantity and renamed components.

        Arguments:
            physQuantity [str]: name of the new physical quantity
            map_cmps [dict[str, str]]: dict to rename components
                (only renamed components will be keeped)
            fed [FiniteElementDescriptor] : FED used to convert the field if
                the one present in the field is not appropriate (default: None)

        Returns:
            FieldOnCellsReal: field with name physical quantity.
        """
        fcs = self.toSimpleFieldOnCells().asPhysicalQuantity(physQuantity, map_cmps)
        ligrel = self.getDescription()
        if fed:
            ligrel = fed
        return fcs.toFieldOnCells(ligrel)


@injector(FieldOnCellsLong)
class ExtendedFieldOnCellsLong:
    cata_sdj = "SD.sd_champ.sd_cham_elem_class"


@injector(FieldOnCellsChar8)
class ExtendedFieldOnCellsChar8:
    cata_sdj = "SD.sd_champ.sd_cham_elem_class"


@injector(FieldOnCellsComplex)
class ExtendedFieldOnCellsComplex:
    cata_sdj = "SD.sd_champ.sd_cham_elem_class"
