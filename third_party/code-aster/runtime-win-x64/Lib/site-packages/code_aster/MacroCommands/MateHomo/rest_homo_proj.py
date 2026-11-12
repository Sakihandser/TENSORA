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

from ...CodeCommands import PROJ_CHAMP, AFFE_MODELE
from ...Messages import UTMESS
from ...Objects import Mesh
from ...Utilities import MPI


class MockField:
    """
    A mock class to emulate the behavior of an aster field.

    """

    def __init__(self, values):
        """
        Initializes the MockField with a list of values.

        Args:
            values (list): A list of values to initialize the mock field.
        """
        self._values = values

    def getValues(self):
        """
        Retrieves the values stored in the mock field.

        Returns:
            list: The list of values stored in the mock field.
        """
        return self._values


class MockResult:
    """
    A mock class to emulate the behavior of an aster result.

    """

    def __init__(self, values):
        """
        Initializes the MockResult with a dictionary of values.

        Args:
            values (dict): A dictionary where each key maps to a list of values.
        """
        self._values = values

    def getField(self, field, n):
        """
        Retrieves a specific field's value from the mock result.

        Args:
            field (str): The field name.
            n (int): The storage index.

        Returns:
            MockField: An instance of MockField.
        """
        return MockField(self._values[field][n])


def MOCK_PROJ_CHAMP(RESULTAT, METHODE, MAILLAGE_1, MAILLAGE_2, NOM_CHAM, TYPE_CHAM):
    """
    Projects a field from one mesh to another using specified methods and parameters.

    Args:
        RESULTAT: The result object containing the data to be projected.
        METHODE: The method used for projection.
        MAILLAGE_1: The source mesh.
        MAILLAGE_2: The target mesh.
        NOM_CHAM: The name of the field to be projected.
        TYPE_CHAM: The type of the field.

    Returns:
        Result: The projected result.

    This function performs a projection from a parallel mesh to a unique point. It uses the
    PROJ_CHAMP function with the maximum distance parameter to check if the point is inside the domain.
    If the mesh contains a single point and this point is not found within the domain, it can
    generate a deadlock. To avoid this, a temporary mesh containing the target point and a second
    point (which will always be present) is created.
    """

    assert isinstance(NOM_CHAM, (list, tuple))

    if MAILLAGE_1.isParallel():
        rank = MPI.ASTER_COMM_WORLD.Get_rank()

        coords1 = MAILLAGE_1.getCoordinates().toNumpy()
        coords2 = MAILLAGE_2.getCoordinates().toNumpy()

        # The target point
        p0 = coords2[0].tolist()

        # Another point guaranteed to be a corner node
        random_id = next(cell[0] for cell in MAILLAGE_1.getConnectivity() if len(cell) > 1)
        p1 = coords1[random_id].tolist()

        # Build a new point cloud mesh from the coordinate points
        MP0 = Mesh.buildPointCloud([p0, p1], info=0)

        # Define the mechanical model for the source mesh
        MOD_3D = AFFE_MODELE(
            MAILLAGE=MAILLAGE_1, AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION=("3D",))
        )

        # Define the mechanical model for the new point cloud mesh
        MOD_0D = AFFE_MODELE(
            MAILLAGE=MP0,
            DISTRIBUTION=_F(METHODE="CENTRALISE"),
            AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION=("DIS_T",)),
        )

        # Project the field from the source model to the target model
        resu_proj = PROJ_CHAMP(
            RESULTAT=RESULTAT,
            METHODE=METHODE,
            MODELE_1=MOD_3D,
            MODELE_2=MOD_0D,
            NOM_CHAM=NOM_CHAM,
            TYPE_CHAM=TYPE_CHAM,
            DISTANCE_MAX=1.0e-6,
        )

        # Determine the rank that succeeded
        refe_field = resu_proj.getField(
            NOM_CHAM[0], resu_proj.getFirstIndex()
        ).toSimpleFieldOnNodes()
        refe_values_mask = refe_field.toNumpy()[1]

        root0 = -1
        if refe_values_mask.all():
            root0 = rank

        roots = MPI.ASTER_COMM_WORLD.allreduce([root0], MPI.SUM)

        found_ranks = [r for r in roots if r != -1]
        n_found = len(found_ranks)

        if n_found == 0:
            UTMESS("F", "HOMO1_22")

        if n_found > 1:
            UTMESS("A", "HOMO1_18", vali=n_found)

        # Collect values from the projected result
        values = {}
        nordre = RESULTAT.getAccessParameters()["NUME_ORDRE"]
        for fld in NOM_CHAM:
            values[fld] = {}
            for n in nordre:
                field = resu_proj.getField(fld, n).toSimpleFieldOnNodes()
                v, m = field.getValues()
                # Index 0 since p0 was set first into the temporary mesh
                if m[0].all():
                    values[fld][n] = v[0].tolist()

        # Broadcast the collected values to all processes from the highest rank proc
        root = max(found_ranks)
        valbcast = MPI.ASTER_COMM_WORLD.bcast(values, root=root)
        resu = MockResult(valbcast)

    else:
        # Directly project the field if the source mesh is not parallel
        resu = PROJ_CHAMP(
            RESULTAT=RESULTAT,
            METHODE=METHODE,
            MAILLAGE_1=MAILLAGE_1,
            MAILLAGE_2=MAILLAGE_2,
            NOM_CHAM=NOM_CHAM,
            TYPE_CHAM=TYPE_CHAM,
            DISTANCE_MAX=1.0e-6,
        )

    return resu
