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


import numpy as np
from ...Utilities import medcoupling as medc


def getDescriptionInfo(medfield):
    """
    Get the information stored as description.

    Arguments:
        field (MED*)) : The medcoupling field.

    Returns :
        symbname (str): Symbolic name of field.
        phys (str): Physical quantity.
        scal (str): Scalar type of field.
    """

    internal_desc = medfield.getDescription()
    phys, symbname = internal_desc.split("-")
    quantity, scal = phys.split("_")

    return symbname, phys, scal


def toMCFieldAndProfileNode(asfield, medmesh, symbname, prefix=""):
    """Internal Function. Export the field to a new MEDCoupling field and profile.

    Arguments:
        asfield (*SimpleFieldOnNodes*): The aster field as simple field.
        medmesh (*MEDCouplingUMesh*): The medcoupling support mesh.
        symbname (str): Symbolic name of field (e.g. SIEQ_NOEU).
        prefix,  optional (str): Prefix for field name.

    Returns:
        field ( MEDCouplingFieldDouble ) : The field medcoupling format.

    """
    tname = type(medmesh).__name__
    if not tname in ("MEDFileUMesh", "MEDCouplingUMesh"):
        raise TypeError(f"Invalid argument type '{tname}'")

    # Aster values
    values, mask = asfield.getValues(copy=False)

    # Restrict field based on mask
    restricted_nodes = np.where(np.any(mask, axis=1) == True)[0]
    restricted_values = values[restricted_nodes, :]

    # Names
    physq = asfield.getPhysicalQuantity()
    field_name = "".join((prefix, symbname))
    internal_desc = "-".join((physq, symbname))
    profile_name = "_".join((field_name, "NodesProfile"))

    # Medcoupling field
    field_values = medc.DataArrayDouble(restricted_values)
    field_values.setInfoOnComponents(asfield.getComponents())
    field_values.setName(field_name)

    medc_node_field = medc.MEDCouplingFieldDouble(medc.ON_NODES, medc.ONE_TIME)
    medc_node_field.setName(field_name)
    medc_node_field.setDescription(internal_desc)
    medc_node_field.setArray(field_values)
    medc_node_field.setNature(medc.IntensiveMaximum)

    # Med profile
    # medcoupling DataArrayInt expects INT32 numpy arrays, but np.where() returns
    # int64 on 64-bit platforms. Cast explicitly to int32 for compatibility.
    field_profile = medc.DataArrayInt(restricted_nodes.astype(np.int32))

    # Med support mesh for field ( restricted to profile nodes ) without cells
    field_mesh = medc.MEDCouplingUMesh()
    field_mesh.setName(medmesh.getName())
    field_mesh.setMeshDimension(medmesh.getMeshDimension())
    field_mesh.setCoords(medmesh.getCoords()[field_profile])
    field_mesh.allocateCells()
    medc_node_field.setMesh(field_mesh)

    field_profile.setName(profile_name)
    medc_node_field.checkConsistencyLight()

    return medc_node_field, field_profile


def toMCFieldAndProfileElem(asfield, medmesh, symbname, prefix=""):
    """Export the field to a new MEDCoupling field

    Arguments:
        asfield (*SimpleFieldOnCells*): The aster field as simple field.
        medmesh (*MEDCouplingUMesh*): The medcoupling support mesh.
        symbname (str): Symbolic name of field (e.g. SIEQ_ELGA).
        prefix,  optional (str): Prefix for field names.

    Returns:
        field ( MEDCouplingFieldDouble ) : The field medcoupling format.
    """

    tname = type(medmesh).__name__
    if not tname in ("MEDCouplingUMesh",):
        raise TypeError(f"Invalid argument type '{tname}'")

    values, mask = asfield.getValues(copy=False)

    # Restrict field based on mask
    restricted_cells = np.where(np.any(mask, axis=1))[0]
    restricted_values = values[restricted_cells, :]

    # Names
    physq = asfield.getPhysicalQuantity()
    field_name = "".join((prefix, symbname))
    internal_desc = "-".join((physq, symbname))
    profile_name = "_".join((field_name, "ElemProfile"))

    # Medcoupling field
    field_values = medc.DataArrayDouble(restricted_values)
    field_values.setInfoOnComponents(asfield.getComponents())
    field_values.setName(field_name)
    medc_cell_field = medc.MEDCouplingFieldDouble(medc.ON_CELLS, medc.ONE_TIME)
    medc_cell_field.setName(field_name)
    medc_cell_field.setDescription(internal_desc)
    medc_cell_field.setArray(field_values)
    medc_cell_field.setNature(medc.IntensiveConservation)

    # medcoupling DataArrayInt expects INT32 numpy arrays; cast from int64.
    field_profile = medc.DataArrayInt(restricted_cells.astype(np.int32))
    field_profile.setName(profile_name)

    if len(restricted_cells) == medmesh.getNumberOfCells():
        medc_cell_field.setMesh(medmesh)
    else:
        raise NotImplementedError()

    medc_cell_field.checkConsistencyLight()

    return medc_cell_field, field_profile


def toMCFieldAndProfile(asfield, medmesh, symbname, prefix=""):
    """Export the field to a new MEDCoupling field

    Arguments:
        asfield (*SimpleField*): The aster field as simple field.
        medmesh (*MEDCouplingUMesh*): The medcoupling support mesh.
        symbname (str): Symbolic name of field (e.g. SIEQ_ELGA).
        prefix,  optional (str): Prefix for field names.

    Returns:
        field ( MEDCouplingFieldDouble ) : The field medcoupling format.
    """

    loc = asfield.getLocalization()
    if loc == "NOEU":
        field, profile = toMCFieldAndProfileNode(asfield, medmesh, symbname, prefix)
    elif loc == "ELEM":
        field, profile = toMCFieldAndProfileElem(asfield, medmesh, symbname, prefix)
    else:
        raise NotImplementedError(loc)

    return field, profile


def toMedCouplingField(asfield, medmesh, symbname, prefix=""):
    """Export the field to a new MEDCoupling field

    Arguments:
        asfield (*SimpleFieldOnNodes*): The aster field as simple field.
        medmesh (*MEDCouplingUMesh*): The medcoupling support mesh.
        symbname (str): Symbolic name of field (e.g. SIEQ_ELGA).
        prefix,  optional (str): Prefix for field names.

    Returns:
        field ( MEDCouplingFieldDouble ) : The field medcoupling format.
    """

    medc_field, field_profile = toMCFieldAndProfile(asfield, medmesh, symbname, prefix)

    return medc_field


def toMedFileField1TS(asfield, medmesh, symbname, prefix="", profile=False):
    """Export the field to a new MED field

    Arguments:
        asfield (*SimpleFieldOnNodes*): The aster field as simple field.
        medmesh (*MEDFileUMesh*): The medcoupling support mesh.
        symbname (str): Symbolic name of field (e.g. SIEQ_ELGA).
        prefix,  optional (str): Prefix for field names.
        profile, optional (bool): True to create a MED profile from field mask.

    Returns:
        field ( MEDFileField1TS ) : The field in med format ( medcoupling ).
    """
    medc_node_field, field_profile = toMCFieldAndProfile(asfield, medmesh, symbname, prefix)

    # Med field with profile
    medfield = medc.MEDFileField1TS()
    if profile:
        medfield.setFieldProfile(medc_node_field, medmesh, 1, field_profile)
    else:
        medfield.setFieldNoProfileSBT(medc_node_field)

    return medfield


def fromMedFileField1TSNodes(mc_field, astermesh):
    """Export the field information to create a new aster field.

    Arguments:
        field (*MEDCouplingFieldDouble*): The medcoupling field.
        mesh (Mesh) : field support mesh.

    Returns:
        phys (str) : Physical quantity name
        cmps (list[str]) : Name of components
        values (list[float]) : Field values

    """
    tname = type(mc_field).__name__
    if not tname in ("MEDCouplingFieldDouble",):
        raise TypeError(f"Invalid argument type '{tname}'")

    if mc_field.getTypeOfField() not in (medc.ON_NODES, medc.ON_NODES_FE):
        raise RuntimeError("Field is not defined on nodes.")

    src, target = mc_field.getMesh().getNumberOfNodes(), astermesh.getNumberOfNodes()
    if src != target:
        raise RuntimeError(
            "Meshes have an incompatible number of nodes (%d != %d)." % (src, target)
        )

    arr = mc_field.getArray()
    cmps = arr.getInfoOnComponents()
    name, phys, scal = getDescriptionInfo(mc_field)
    values = arr.getValues()

    return phys, cmps, values


def fromMedFileField1TSCells(mc_field, astermesh):
    """Export the field information to create a new aster field.

    Arguments:
        field (*MEDCouplingFieldDouble*): The medcoupling field.
        mesh (Mesh) : field support mesh.

    Returns:
        phys (str) : Physical quantity name
        cmps (list[str]) : Name of components
        values (list[float]) : Field values

    """

    tname = type(mc_field).__name__
    if not tname in ("MEDCouplingFieldDouble",):
        raise TypeError(f"Invalid argument type '{tname}'")

    if mc_field.getTypeOfField() != medc.ON_CELLS:
        raise RuntimeError("Field is not defined on cells.")

    src, target = mc_field.getMesh().getNumberOfCells(), astermesh.getNumberOfCells()
    if src != target:
        raise RuntimeError(
            "Meshes have an incompatible number of cells (%d != %d)." % (src, target)
        )

    arr = mc_field.getArray()
    cmps = arr.getInfoOnComponents()
    name, phys, scal = getDescriptionInfo(mc_field)
    values = arr.getValues()

    return phys, cmps, values
