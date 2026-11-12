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


from ...Objects import Mesh, SimpleFieldOnNodesReal
from ...Utilities import medcoupling as medc
from .field_converter import getDescriptionInfo


def getNumberOfTimeSteps(medresult):
    """Get the number of stored time steps.

    If several results are available they must have all the same number of time steps.

    Arguments:
        medresult (MEDFileData) : The result in med format ( medcoupling ).

    Returns:
        n (int) : The number of time steps.
    """
    nb_time_steps = list(set(fmts.getNumberOfTS() for fmts in list(medresult.getFields())))
    check_ts = len(nb_time_steps) == 1
    if not check_ts:
        msg = "Results with different time steps are not managed now."
        raise RuntimeError(msg)

    return nb_time_steps[0]


def canConvertMedFileData(medresult):
    """
    Check the MEDFileData to assert if it can be importer as aster result.

    Arguments:
        medresult (MEDFileData) : The result in med format ( medcoupling ).

    Returns :
        check (bool) : True
    """
    if not len(medresult.getMeshes()) == 1:
        msg = "Invalid number of meshes as input data"
        raise RuntimeError(msg)

    if not len(medresult.getFields()) > 0:
        msg = "Result is empty"
        raise RuntimeError(msg)

    nb_time_steps = getNumberOfTimeSteps(medresult)

    nb_ord = [[v[0] for v in fmts.getTimeSteps()] for fmts in list(medresult.getFields())]
    check_ord = all([len(set(i)) == 1 for i in zip(*nb_ord)])
    if not check_ord:
        msg = "Results do not share the same ranks."
        raise RuntimeError(msg)

    nb_time = [[v[2] for v in fmts.getTimeSteps()] for fmts in list(medresult.getFields())]
    check_times = all([len(set(i)) == 1 for i in zip(*nb_time)])
    if not check_times:
        msg = "Results do not share the same time values."
        raise RuntimeError(msg)

    nb_types = [fmts.getTypesOfFieldAvailable() for fmts in list(medresult.getFields())]
    check_disc = all([all(k == 1 for k in list(map(len, i))) for i in nb_types])
    if not check_disc:
        msg = "Fields with multiple space discr not managed !"
        raise RuntimeError(msg)

    nb_pfs = [len(fmts.getPflsReallyUsed()) for fmts in list(medresult.getFields())]
    check_pfs = all([i == 0 for i in nb_pfs])
    if not check_pfs:
        msg = "Profiles are not managed now !"
        raise RuntimeError(msg)

    return True


def fromMedFileData(result, medresult, astermesh):
    """Fill a new result from an existing MED container.

    The import is limited to fields on nodes (Real) without profile.

    Arguments:
        result ( Result ) : The result in Aster format.
        medresult (MEDFileData) : The result in med format ( medcoupling ).
        astermesh, optional (Mesh): The aster support mesh.
    """
    assert not result.exists()

    if not isinstance(medresult, (medc.MEDFileData,)):
        msg = "fromMedCouplingResult() argument must be a MEDFileData, not '{}'"
        raise TypeError(msg.format(type(medresult).__name__))

    assert canConvertMedFileData(medresult)

    medmesh = medresult.getMeshes()[0]
    if not astermesh:
        astermesh = Mesh()
        astermesh.buildFromMedCouplingMesh(medmesh)

    result.allocate(getNumberOfTimeSteps(medresult))
    medmesh = medresult.getMeshes()[0]
    fmtsin = medresult.getFields()

    for fmts in fmtsin:
        steps = fmts.getTimeSteps()
        for i, f1ts in enumerate(fmts):
            rank, it, time = steps[i]
            field_types = f1ts.getTypesOfFieldAvailable()

            assert len(field_types) == 1
            assert len(f1ts.getPflsReallyUsed()) == 0

            if field_types[0] == medc.ON_NODES:
                with f1ts:
                    medcfield = f1ts.field(medmesh)
                    name, phys, scal = getDescriptionInfo(medcfield)
                    assert scal == "R"
                    sfield = SimpleFieldOnNodesReal.fromMedCouplingField(medcfield, astermesh)
                    asterfield = sfield.toFieldOnNodes()
                    result.setField(asterfield, name, rank)
                    result.setTime(time, rank)


def toMedFileData(result, medmesh=None, profile=False, prefix=""):
    """Export the result to a new MED container.

    The export is limited to fields on nodes (Real) only.

    Arguments:
        medmesh, optional (*MEDFileUMesh*): The medcoupling support mesh.
        profile, optional (bool): True to create a MED profile from field mask.
        prefix,  optional (str): Prefix for field names.

    Returns:
        field ( MEDFileData ) : The result in med format ( medcoupling ).
    """

    # Get NUME_ORDRE
    para = result.getAccessParameters()

    ranks = para.get("NUME_ORDRE")
    assert ranks is not None

    # Get the variable to be associated to time in the med file
    times = None
    for i in ("INST", "FREQ", "NUME_MODE"):
        if i in para:
            times = para.get(i)
            break
    assert times is not None

    # Only works for fields on nodes real
    save_fields = result.getFieldsOnNodesRealNames()
    if len(save_fields) == 0:
        msg = "None of the fields can be exported to medcoupling"
        raise RuntimeError(msg)

    # Init medcoupling objets
    medresult = medc.MEDFileData()
    meshes = medc.MEDFileMeshes()
    fields = medc.MEDFileFields()

    # Set mesh
    medmesh = medmesh or result.getMesh().createMedCouplingMesh()
    meshes.pushMesh(medmesh)

    for fname in save_fields:
        fmts = medc.MEDFileFieldMultiTS()
        for rank, time in zip(ranks, times):
            asterfield = result.getField(fname, rank).toSimpleFieldOnNodes()
            medcfield = asterfield.toMedFileField1TS(medmesh, fname, prefix, profile)
            medcfield.setTime(rank, 0, time)
            fmts.pushBackTimeStep(medcfield)
        fields.pushField(fmts)

    medresult.setMeshes(meshes)
    medresult.setFields(fields)
    return medresult
