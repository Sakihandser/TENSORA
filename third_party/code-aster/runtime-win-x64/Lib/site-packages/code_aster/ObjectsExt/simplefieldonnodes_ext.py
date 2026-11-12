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
:py:class:`SimpleFieldOnNodesReal`
Simple Fields defined on nodes of elements
********************************************************************
"""
import numpy as np
import numpy.ma as ma

from ..MedUtils.MedConverter import fromMedFileField1TSNodes, toMedCouplingField, toMedFileField1TS
from ..Objects import PythonBool, SimpleFieldOnNodesComplex, SimpleFieldOnNodesReal
from ..Utilities import force_list, injector
from .component import ComponentOnNodes


@injector(SimpleFieldOnNodesReal)
class ExtendedSimpleFieldOnNodesReal:
    cata_sdj = "SD.sd_cham_no_s.sd_cham_no_s"

    @property
    def _cache(self):
        if self._ptr_cache is None:
            self._ptr_cache = dict.fromkeys(["readonly", "val", "msk"])
            self._ptr_cache["readonly"] = None
        if self._ptr_cache["val"] is None:
            self._ptr_cache["val"], self._ptr_cache["msk"] = self.toNumpy()
        return self._ptr_cache

    def __getattr__(self, component):
        """Convenient shortcut to `getComponentOnNodes()`."""
        if component not in self.getComponents():
            raise AttributeError(f"'SimpleFieldOnNodes' object has no attribute {component!r}")
        return self.getComponentOnNodes(component)

    def getComponentOnNodes(self, component):
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
        return ComponentOnNodes(mvalues, ComponentOnNodes.Description(self))

    def setComponentValues(self, component, cfvalue):
        """Assign the values of a component.

        Args:
            component (str): Component name. Raises ValueError if the component
                does not exist in the field.
            cfvalue (ComponentOnNodes): Previously extracted component.
        """
        icmp = self.getComponents().index(component)
        # it directly overwrites '.CNSV' vector in place
        expanded = cfvalue.expand().values
        self._cache["val"][:, icmp] = expanded.data
        self._cache["msk"][:, icmp] = np.logical_not(expanded.mask)

    def getValues(self, copy=True):
        """
        Returns two numpy arrays containing the field values on specific nodes.
        The first array contains the field values while the second one is a mask
        which is `True` if the corresponding value exists, `False` otherwise.
        Array shape is ( number_of_nodes, number_of_components ).

        Args:
            copy (bool): If *True* copy the data, this is the default.

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
            SimpleFieldOnNodesReal: field restricted.
        """

        val = {None: PythonBool.NONE, True: PythonBool.TRUE, False: PythonBool.FALSE}

        return self._restrict(force_list(cmps), force_list(groupsOfNodes), val[same_rank])

    @classmethod
    def fromMedCouplingField(cls, mc_field, astermesh):
        """Import the field to a new MEDCoupling field. Set values in place.

           It assumes that the DataArray contains the list of components and
           its name ends with the physical quantity.

        Arguments:
            field (*MEDCouplingFieldDouble*): The medcoupling field.
            mesh (Mesh) : field support mesh.

        Returns:
            field (*SimpleFieldOnNodes*): The aster field.
        """

        phys, cmps, values = fromMedFileField1TSNodes(mc_field, astermesh)

        field = cls(astermesh)
        field.allocate(phys, cmps)
        field.setValues(values)

        return field

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

    def toMedFileField1TS(self, medmesh, symbname, prefix="", profile=False):
        """Export the field to a new MED field

        Arguments:
            medmesh (*MEDFileUMesh*): The medcoupling support mesh.
            symbname (str): Symbolic name of field.
            prefix, optional (str): Prefix for field names.
            profile, optional (bool): True to create a MED profile from field mask.

        Returns:
            field ( MEDFileField1TS ) : The field in med format ( medcoupling ).
        """

        return toMedFileField1TS(self, medmesh, symbname, prefix, profile)

    def transfert(self, mesh, cmps=[]):
        """Tranfert the field to an other mesh. One of the mesh has to be a restriction
        to the other one.

        Arguments:
            mesh (Mesh) : mesh to use for transfert.
            cmps [list[str]]: filter on list of components. If empty, all components are used

        Returns:
            SimpleFieldOnNodesReal: field transfered to new mesh.
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

        sfield = SimpleFieldOnNodesReal(mesh, self.getPhysicalQuantity(), cmps)

        rest2orig = mesh.getRestrictedToOriginalNodesIds()

        if len(rest2orig) > 0:
            orig2rest = mesh.getOriginalToRestrictedNodesIds()

            values, descr = self.getValuesWithDescription(cmps, rest2orig)

            sfield.setValues([orig2rest[node] for node in descr[0]], descr[1], values)
        else:
            rest2orig = self.getMesh().getRestrictedToOriginalNodesIds()

            values, descr = self.getValuesWithDescription(cmps)

            sfield.setValues([rest2orig[node] for node in descr[0]], descr[1], values)

        return sfield


@injector(SimpleFieldOnNodesComplex)
class ExtendedSimpleFieldOnNodesComplex:
    cata_sdj = "SD.sd_cham_no_s.sd_cham_no_s"

    def getValues(self, copy=False):
        """
        Returns two numpy arrays with shape ( number_of_cells_with_components, number_of_components )
        The first array contains the field values while the second one is a mask
        which is `True` if the corresponding value exists, `False` otherwise.

        Where the mask is `False` the corresponding value is set to zero.

        Args:
            copy (bool): If True copy the data, default: *False*

        Returns:
            ndarray (float): Field values.
            ndarray (bool): Mask for the field values.
        """
        values, mask = self.toNumpy()
        if copy:
            return values.copy(), mask.copy()

        values.setflags(write=False)
        mask.setflags(write=False)

        return values, mask
