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
:py:class:`SimpleFieldOnCellsReal`
Simple Fields defined on cells of elements
********************************************************************
"""

import numpy as np
import numpy.ma as ma

from ..MedUtils.MedConverter import fromMedFileField1TSCells, toMedCouplingField
from ..Objects import SimpleFieldOnCellsReal
from ..Utilities import injector
from .component import ComponentOnCells


@injector(SimpleFieldOnCellsReal)
class ExtendedSimpleFieldOnCellsReal:
    cata_sdj = "SD.sd_cham_elem_s.sd_cham_elem_s"

    @property
    def _cache(self):
        if self._ptr_cache is None:
            self._ptr_cache = dict.fromkeys(["readonly", "val", "msk", "idx", "nbpt"])
            self._ptr_cache["readonly"] = None
        if self._ptr_cache["val"] is None:
            self._ptr_cache["val"], self._ptr_cache["msk"], addr = self.toNumpy()
            nbcells = addr[0]
            dims = addr[5:]
            dims.shape = nbcells, 4
            self._ptr_cache["nbpt"] = dims[:, 0:2]  # number of points, subpoints
            nbval = self._ptr_cache["nbpt"].prod(axis=1)  # nbval by cells (for one component)
            start = np.append([0], nbval.cumsum()[:-1])
            end = start + nbval
            indexes = np.ones((nbcells, nbval.max()), dtype=int) * -1
            for iv in range(nbcells):
                indexes[iv, : nbval[iv]] = np.arange(start[iv], end[iv])
            self._ptr_cache["idx"] = indexes
        return self._ptr_cache

    def __getattr__(self, component):
        """Convenient shortcut to `getComponentOnCells()`."""
        if component not in self.getComponents():
            raise AttributeError(f"'SimpleFieldOnCells' object has no attribute {component!r}")
        return self.getComponentOnCells(component)

    def getComponentOnCells(self, component):
        """Extract the values of a component.

        Args:
            component (str): Component name. Raises ValueError if the component
                does not exist in the field.
        """
        if self._cache["readonly"]:
            self._ptr_cache = None
        icmp = self.getComponents().index(component)
        self._cache["readonly"] = False
        mvalues = ma.array(
            self._cache["val"][:, icmp].copy(), mask=np.logical_not(self._cache["msk"][:, icmp])
        )
        return ComponentOnCells(
            mvalues, ComponentOnCells.Description(self, self._cache["idx"], self._cache["nbpt"])
        )

    def toMedCouplingField(self, medmesh, symbname, prefix=""):
        """Export the field to a new MEDCoupling field

        Arguments:
            medmesh (*MEDCouplingUMesh*): The medcoupling support mesh.
            symbname (str): Symbolic name of field.
            prefix,  optional (str): Prefix for field names.

        Returns:
            field ( MEDCouplingFieldDouble ) : The field medcoupling format.
        """

        return toMedCouplingField(self, medmesh, symbname, prefix)

    def setComponentValues(self, component, cfvalue):
        """Assign the values of a component.

        Args:
            component (str): Component name. Raises ValueError if the component
                does not exist in the field.
            cfvalue (ComponentOnCells): Previously extracted component.
        """
        icmp = self.getComponents().index(component)
        # it directly overwrites '.CESV' vector in place
        expanded = cfvalue.expand().values
        self._cache["val"][:, icmp] = expanded.data
        self._cache["msk"][:, icmp] = np.logical_not(expanded.mask)

    def getValues(self, copy=True):
        """
        Returns two numpy arrays containing the field values on specific cells.

        The first array contains the field values while the second one is a mask
        which is `True` if the corresponding value exists, `False` otherwise.
        Array shape is ( number_of_cells_with_components, number_of_components ).

        Args:
            copy (bool): If *True* the data are copied, the is the default.

        Returns:
            ndarray (float): Field values.
            ndarray (bool): Mask for the field values.
        """
        values, mask = self._cache["val"], self._cache["msk"]
        if copy or self._cache["readonly"] is False:
            return values.copy(), mask.copy()

        self._cache["readonly"] = True
        values.setflags(write=False)
        mask.setflags(write=False)
        return values, mask

    def getValuesOnCell(self, idcell):
        """
        Returns two numpy arrays containing the field values on specific cells.

        The first array contains the field values while the second one is a mask
        which is `True` if the corresponding value exists, `False` otherwise.
        Each array contains `number_of_cells * number_of_components` values.
        Array shape is ( number_of_cells_with_components, number_of_components ).

        Args:
            idcell (int): The cell id.

        Returns:
            ndarray (float): Field values.
            ndarray (bool): Mask for the field values.
        """

        istart = sum(
            [
                self.getNumberOfPointsOfCell(i) * self.getNumberOfSubPointsOfCell(i)
                for i in range(idcell)
            ]
        )

        iend = istart + self.getNumberOfPointsOfCell(idcell) * self.getNumberOfSubPointsOfCell(
            idcell
        )

        values, mask = self.getValues()

        return values[istart:iend], mask[istart:iend]

    def transfert(self, mesh, cmps=[]):
        """Tranfert the field to an other mesh. One of the mesh has to be a restriction
        to the other one.

        Arguments:
            mesh (Mesh) : mesh to use for transfert.
            cmps [list[str]]: filter on list of components. If empty, all components are used

        Returns:
            SimpleFieldOnCellsReal: field transfered to new mesh.
        """

        if len(cmps) == 0:
            cmps = self.getComponents()
        else:
            cmps_red = []
            all_cmps = self.getComponents()
            for cmp in cmps:
                if cmp in all_cmps:
                    cmps_red.append(cmp)
            cmps = cmps_red

        sfield = SimpleFieldOnCellsReal(
            mesh, self.getLocalization(), self.getPhysicalQuantity(), cmps
        )

        rest2orig = mesh.getRestrictedToOriginalCellsIds()

        if len(rest2orig) > 0:
            orig2rest = mesh.getOriginalToRestrictedCellsIds()

            values, descr = self.getValuesWithDescription(cmps, rest2orig)

            sfield.setValues(
                [orig2rest[cell] for cell in descr[0]], descr[1], descr[2], descr[3], values
            )
        else:
            rest2orig = self.getMesh().getRestrictedToOriginalCellsIds()

            values, descr = self.getValuesWithDescription(cmps)

            sfield.setValues(
                [rest2orig[cell] for cell in descr[0]], descr[1], descr[2], descr[3], values
            )

        return sfield

    @classmethod
    def fromMedCouplingField(cls, mc_field, astermesh):
        """Import the field to a new MEDCoupling field. Set values in place.

            It assumes that the DataArray contains the list of components and
            its names is the physical quantity.

        Arguments:
            field (*MEDCouplingFieldDouble*): The medcoupling field.
        """

        phys, cmps, values = fromMedFileField1TSCells(mc_field, astermesh)

        field = cls(astermesh)
        field.allocate("ELEM", phys, cmps, 1, 1)
        field.setValues(values)

        return field
