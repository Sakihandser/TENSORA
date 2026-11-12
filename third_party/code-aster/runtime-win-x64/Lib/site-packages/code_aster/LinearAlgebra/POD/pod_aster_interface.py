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
from ...Utilities import PETSc, MPI

comm = MPI.ASTER_COMM_WORLD


# FUNCTIONNALITIES TO EXTRACT SNAPSHOT MATRIX FROM RESULT
def findIndexCHAM(lst, s):
    """Find the index of the first occurrence of an element in a list.

    Arguments:
        lst (list[Any]): The list to search within.
        s (Any): The element to find in the list.

    Returns:
        int | None: The index of the first occurrence of `s` in `lst`, or `None` if the
        element is not present.

    """
    try:
        return lst.index(s)
    except ValueError:
        return None


def extractSnapshotsFromResult(result, chamName, format, indexSteps=None):
    """Extraction of snapshots from a SD RESULTAT.

    Arguments:
        result (SD RESULTAT): code_aster result in which we seek snapshots
        chamName (str): Name of the field in the result (example: DEPL or SIEF_ELGA)
        format (str): Format of the snapshots (should be numpy or PETSc vectors)
        indexSteps (list | None): List of the indices of the snapshots we seek to keep

    Returns:
        numpy.ndarray: Snapshot array. Each column contains a given snapshot (size = number of dofs * number of snapshots).
    """
    AVALAIBLE_FORMAT = ["numpy", "petsc"]
    assert format in AVALAIBLE_FORMAT

    ## - Checks for the extraction procedure
    fieldsNames = result.getFieldsNames()
    if not fieldsNames:
        raise ValueError("Error in extraction procedure: No fields available in RESULTAT")
    chamIndex = findIndexCHAM(fieldsNames, chamName)
    if chamIndex is None:
        raise ValueError("Error in extraction procedure: Couldn't find the asked field in RESULTAT")
    ## - Get proper data-structure for indexSteps : either None, int or list
    # if indexSteps is an integer, should be modified to be a list
    if indexSteps is None:
        # if None, all the timesteps are taken into account
        indStepsList = result.getIndexes()
        if isinstance(indStepsList, int):
            indStepsList = [indStepsList]
    else:
        if isinstance(indexSteps, int):
            indStepsList = [indexSteps]
        else:
            indStepsList = indexSteps
    ## - Extraction of the snapshots
    if format == "numpy":
        snapshots = []

        for idx in indStepsList:
            if idx not in result.getIndexes():
                raise ValueError(
                    f"Error in extraction procedure: Timestep index {idx} is not available in RESULTAT"
                )
            cham = result.getField(chamName, idx)
            values = cham.getValues()
            snapshots.append(np.array(values))

        return np.column_stack(snapshots)
    elif format == "petsc":
        neqg = result.getEquationNumberings()[0].getNumberOfDOFs(local=False)
        ndindices = len(indStepsList)  # result.getNumberOfIndexes()
        snapshotsT = PETSc.Mat().createDense([ndindices, neqg], comm=comm)

        row = 0
        for idx in indStepsList:
            if idx not in result.getIndexes():
                raise ValueError(
                    f"Error in extraction procedure: Timestep index {idx} is not available in RESULTAT"
                )
            cham = result.getField(chamName, idx)
            vec = cham.toPetsc()
            i_start, i_end = vec.getOwnershipRange()
            vec_array = vec.getArray(readonly=True)
            snapshotsT.setValues(
                row,
                np.arange(i_start, i_end, dtype="int32"),
                vec_array,
                addv=PETSc.InsertMode.INSERT_VALUES,
            )
            row += 1
        snapshotsT.assemble()
        return snapshotsT.transpose()
    else:
        raise ValueError(
            f"Snapshot extraction: parameter '{format}' is not valid. Choose format in {AVALAIBLE_FORMAT}."
        )


def transferSnapshotsToPETSC(snapshots):
    """Converts a snapshot matrix (numpy) into a PETSc matrix.

    .. warning::
    This implementation should not be used in parallel distributed
    versions.

    Arguments:
        snapshots (numpy.ndarray): The snapshot matrix to be converted.

    Returns:
        PETSc.Mat: The snapshot matrix in PETSc format.
    """
    snapshots_petsc = PETSc.Mat().createDense(snapshots.shape, array=snapshots, comm=comm)
    snapshots_petsc.assemble()
    return snapshots_petsc
