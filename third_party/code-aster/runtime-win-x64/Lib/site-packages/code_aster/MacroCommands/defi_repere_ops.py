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
from typing import Sequence, Any, List, Optional

from math import cos, sin, hypot, atan2, pi
import numpy as np

from ..Objects import FieldOnCellsReal


class TransformToNaut:
    "Class helper to compute the NAUTIQUE angle"

    TOLERANCE = 1e-12

    @staticmethod
    def is_null_vector(v: Sequence[float]) -> bool:
        """Check if a vector magnitude is numerically zero."""
        return np.linalg.norm(v) < TransformToNaut.TOLERANCE

    @staticmethod
    def matrot_eul(angles: Sequence[float]):
        "Rotation matrix from EULER angles"
        a, b, c = angles
        ca = cos(a)
        cb = cos(b)
        cc = cos(c)
        sa = sin(a)
        sb = sin(b)
        sc = sin(c)

        return np.array(
            [
                [cc * ca - sc * cb * sa, -sc * ca - cc * cb * sa, sb * sa],
                [cc * sa + sc * cb * ca, -sc * sa + cc * cb * ca, -sb * ca],
                [sc * sb, cc * sb, cb],
            ]
        )

    @staticmethod
    def matrot_nau(angles: Sequence[float]):
        "Rotation matrix from NAUTIQUE angles"
        a, b, c = angles
        ca = cos(a)
        cb = cos(b)
        cc = cos(c)
        sa = sin(a)
        sb = sin(b)
        sc = sin(c)

        return np.array(
            [
                [cb * ca, cb * sa, -sb],
                [sc * sb * ca - cc * sa, cc * ca + sc * sb * sa, sc * cb],
                [sc * sa + cc * sb * ca, cc * sb * sa - ca * sc, cc * cb],
            ]
        )

    @staticmethod
    def angvx(gx: Sequence[float]) -> tuple[float, float]:
        """
        Compute alpha and beta from vector gx.

        Returns (0, 0) for a null vector since the orientation
        is undefined.
        """
        gx = np.asarray(gx, dtype=float)

        if TransformToNaut.is_null_vector(gx):
            return 0.0, 0.0

        alpha = atan2(gx[1], gx[0])

        p = hypot(gx[0], gx[1])
        beta = -atan2(gx[2], p)

        return alpha, beta

    @staticmethod
    def angvxy(gx: Sequence[float], gn: Sequence[float]) -> np.ndarray:
        """
        Compute the three NAUTIQUE angles from GX and GN.
        """
        alpha, beta = TransformToNaut.angvx(gx)

        angles = np.array([alpha, beta, 0.0])

        gy = TransformToNaut.matrot_nau(angles) @ np.asarray(gn)

        if not TransformToNaut.is_null_vector(gy[1:]):
            angles[2] = atan2(gy[2], gy[1])

        # Normalize angles to be between 0 and 2*pi
        angles %= 2 * pi
        return angles

    @staticmethod
    def eulnau(angeul: Sequence[float]):
        "Transform EULER angles to NAUTIQUE angles"
        # Compute rotation matrix
        mat = TransformToNaut.matrot_eul(np.deg2rad(angeul))

        # Local vectors written in the local system
        xg = mat[:, 0]
        yg = mat[:, 1]

        # Compute new angles
        angnau = TransformToNaut.angvxy(xg, yg)
        return np.rad2deg(angnau)

    @staticmethod
    def cylnau(point: Sequence[float], orig: Sequence[float], angl: Sequence[float]):
        "Transform CYLINDRIQUE system to NAUTIQUE angles"

        # Rewrite values
        point = np.asarray(point)
        orig = np.asarray(orig)
        alpha, beta = np.deg2rad(angl)

        # Compute useful quantities
        dire = np.array([cos(alpha) * cos(beta), sin(alpha) * cos(beta), -sin(beta)])
        v = point - orig
        sca = np.dot(v, dire)

        # Local vectors written in the local system
        xg = dire
        zg = v - sca * dire
        zg /= np.linalg.norm(zg)
        yg = np.cross(zg, xg)

        # Compute new angles
        angnau = TransformToNaut.angvxy(xg, yg)
        return np.rad2deg(angnau)


def _get_values_and_description(champ: Any, group_ma: Optional[List[str]]):
    """
    Get values and description of group_ma.
    """
    mesh = champ.getMesh()
    cells = mesh.getCells(group_ma) if group_ma is not None else mesh.getCells()
    cmps = ["C", "ALPHA", "BETA", "KAPPA", "X", "Y", "Z"]
    values, description = champ.getValuesWithDescription(cmps=cmps, cells=cells)
    values = np.reshape(values, (-1, len(cmps)))
    return values, description


def include_cylindrique(
    champ: Any, orig_axe: Sequence[float], angl_axe: Sequence[float], group_ma: Optional[List[str]]
):
    """
    Modify champ to include cylindrique system.
    """
    # Recover mesh connectivity
    mesh = champ.getMesh()
    connectivity = mesh.getConnectivity()

    # Recover coordinates X, Y, Z
    coordinates = mesh.getCoordinates().getValues()
    coordinates = np.reshape(coordinates, (-1, 3))
    X = coordinates[:, 0]
    Y = coordinates[:, 1]
    Z = coordinates[:, 2]

    # Recover values of cham_elem
    values, description = _get_values_and_description(champ, group_ma)
    (v_cells, v_cmps, points, subpoints) = description

    # Loop over the target cells to modify old values
    target_cells = np.reshape(v_cells, values.shape)[:, 0]
    for row, cell in enumerate(target_cells):
        lnoeud = connectivity[cell]
        barycenter = np.array([np.mean(X[lnoeud]), np.mean(Y[lnoeud]), np.mean(Z[lnoeud])])
        angl_nau = TransformToNaut.cylnau(barycenter, orig_axe, angl_axe)
        values[row] = [1, angl_nau[0], angl_nau[1], angl_nau[2], 0.0, 0.0, 0.0]

    # Save new values
    values = values.ravel()
    champ.setValues(v_cells, v_cmps, points, subpoints, values)


def include_cartesien(champ: Any, angl_nau: Sequence[float], group_ma: Optional[List[str]]):
    """
    Modify champ to include cartesian system.
    """
    # Recover values of cham_elem
    values, description = _get_values_and_description(champ, group_ma)
    (v_cells, v_cmps, points, subpoints) = description

    # Modify old values
    values[:] = [1, angl_nau[0], angl_nau[1], angl_nau[2], 0.0, 0.0, 0.0]

    # Save new values
    values = values.ravel()
    champ.setValues(v_cells, v_cmps, points, subpoints, values)


def modify_values_on_field(champ: Any, args_in: dict):
    """
    Reads information in ``args_in`` and include it into ``champ``
    """
    if "TOUT" in args_in:
        group_ma = None
    elif "GROUP_MA" in args_in:
        group_ma = args_in["GROUP_MA"]
    else:
        raise NotImplementedError

    SYST_COOR = args_in["SYST_COOR"]
    if SYST_COOR == "CYLINDRIQUE":
        otmp = args_in["ORIG_AXE"]
        orig = [otmp[0], otmp[1], 0.0]
        if len(otmp) > 2:
            orig[2] = otmp[2]
        atmp = args_in["ANGL_AXE"]
        angl = [atmp[0], atmp[1]]
        include_cylindrique(champ, orig_axe=orig, angl_axe=angl, group_ma=group_ma)

    elif SYST_COOR == "CARTESIEN":
        if "ANGL_NAUT" in args_in:
            angl = args_in["ANGL_NAUT"]
        elif "ANGL_EULER" in args_in:
            eule = args_in["ANGL_EULER"]
            angl = TransformToNaut.eulnau([eule[0], eule[1], eule[2]])
        else:
            raise NotImplementedError
        include_cartesien(champ, angl_nau=angl, group_ma=group_ma)

    else:
        raise NotImplementedError


def defi_repere_ops(self, **kwargs):

    # Recover model
    model = kwargs["MODELE"]

    # Recover defi arguments
    DEFI_ARGS = kwargs["DEFI"]

    if not len(DEFI_ARGS):
        raise NotImplementedError("Empty list")

    # Create CREA_CHAMP datastructure
    field = FieldOnCellsReal(model, "ELEM", "CAMA_R").toSimpleFieldOnCells()

    # Modify field with information in defi arguments
    for args_in in DEFI_ARGS:
        modify_values_on_field(field, args_in)

    return field.toFieldOnCells(model.getFiniteElementDescriptor())
