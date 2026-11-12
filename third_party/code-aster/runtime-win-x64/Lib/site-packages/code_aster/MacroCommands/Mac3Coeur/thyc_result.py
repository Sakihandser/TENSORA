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


from collections import OrderedDict
import numpy as np
from .mac3coeur_commons import (
    get_first_digit,
    check_centers_and_size as check,
    check_contiguous,
    find_nearest_idx,
    MAC3_ROUND,
)

THYC_EPSILON = 1.0e-6


class ThycResult:
    _Z = "Z(m)"
    _Ep = "ep(m)"
    _K = "K"
    _method_tr = "M2TEN"
    _nozzles_transversal_load = True

    @property
    def method_tr(self):
        return self._method_tr

    @method_tr.setter
    def method_tr(self, v):
        assert v in ("M1DEV", "M2TEN")
        self._method_tr = v

    @property
    def apply_nozzle_transversal_load(self):
        return self._nozzles_transversal_load

    @apply_nozzle_transversal_load.setter
    def apply_nozzle_transversal_load(self, v):
        assert isinstance(v, bool)
        self._nozzles_transversal_load = v

    @property
    def grids_position(self):
        if self._grids_position_meters is None:
            msg = "grids_position not set"
            raise IOError(msg)
        return self._grids_position_meters

    @grids_position.setter
    def grids_position(self, v):
        assert len(v) in (8, 10)
        self._grids_position_meters = v

    @property
    def grids_index(self):
        return [
            find_nearest_idx(i, self.cells_center, self.cells_size) for i in self.grids_position
        ]

    @property
    def nozzles_position(self):
        if self._nozzles_position_meters is None:
            msg = "nozzles_position not set"
            raise IOError(msg)
        return self._nozzles_position_meters

    @nozzles_position.setter
    def nozzles_position(self, v):
        assert len(v) in (2,)
        assert v[0] < v[1]
        self._nozzles_position_meters = v

    @property
    def nozzles_index(self):

        idx_einf = np.where(
            self.cells_center + 0.5 * self.cells_size < self.nozzles_position[0] + THYC_EPSILON
        )
        idx_esup = np.where(
            self.cells_center - 0.5 * self.cells_size > self.nozzles_position[1] - THYC_EPSILON
        )
        return list(np.concatenate((idx_einf[0], idx_esup[0])))

    @property
    def cells_number(self):
        """
        Number of THYC cells
        """
        return self.cells_id.size

    @property
    def cells_center(self):
        """
        Center of mass of the THYC cells
        """
        return self._thyc_mesh[self._Z].round(MAC3_ROUND)

    @property
    def cells_id(self):
        """
        Ids of the THYC cells
        """
        return self._thyc_mesh[self._K].round(MAC3_ROUND)

    @property
    def cells_size(self):
        """
        Axial dimension of the THYC cells
        """
        return self._thyc_mesh[self._Ep].round(MAC3_ROUND)

    @property
    def cells_size_from_center(self):
        """
        Axial dimension of the THYC cells computed from the barycenter
        """
        cells_size = np.zeros(self.cells_center.size)
        cells_size[0] = 2 * self.cells_center[0]
        delta_center = self.cells_center[1:] - self.cells_center[:-1]
        for i in range(delta_center.size):
            cells_size[i + 1] = 2 * delta_center[i] - cells_size[i]
        return cells_size.round(MAC3_ROUND)

    @property
    def fa_positions(self):
        """
        Number of fuel assemblies positions
        """
        pos_ax = self._thyc_data["AXIAL"].keys()
        pos_trx = self._thyc_data[self.method_tr]["X"].keys()
        pos_try = self._thyc_data[self.method_tr]["Y"].keys()
        assert pos_ax == pos_trx == pos_try
        return list(pos_ax)

    @property
    def fa_number(self):
        """
        Number of fuel assemblies positions
        """
        return len(self.fa_positions)

    def axial_force(self, i, j):
        """
        Axial force along the Z(THYC) axis

        Arguments:
            i (int): The X (THYC) position of the assembly
            j (int): The Y (THYC) position of the assembly

        Returns:
            (array): The axial force for the assembly (i,j).

        """
        return self._thyc_data["AXIAL"][i, j][0]

    def _get_transversal_force(self, direction, i, j):
        values = self._thyc_data[self.method_tr][direction][i, j]
        if not self.apply_nozzle_transversal_load:
            values = values.copy()
            values[self.nozzles_index] = 0.0
        return values

    def transversal_force_x(self, i, j):
        """
        Transversal force along the X(THYC) axis

        Arguments:
            i (int): The X (THYC) position of the assembly
            j (int): The Y (THYC) position of the assembly

        Returns:
            (array): The transversal force along the X axis for the assembly (i,j).
        """

        return self._get_transversal_force("X", i, j)

    def transversal_force_y(self, i, j):
        """
        Transversal force along the Y(THYC) axis

        Arguments:
            i (int): The X (THYC) position of the assembly
            j (int): The Y (THYC) position of the assembly

        Returns:
            (array): The transversal force along the Y axis for the assembly (i,j).
        """

        return self._get_transversal_force("Y", i, j)

    def __init__(self):
        self._reset_structures()
        self._grids_position_meters = None

    def _reset_structures(self):
        self._thyc_mesh = OrderedDict()
        self._thyc_data = OrderedDict()
        self._thyc_data["AXIAL"] = OrderedDict()
        self._thyc_data["M2TEN"] = {"X": OrderedDict(), "Y": OrderedDict()}
        self._thyc_data["M1DEV"] = {"X": OrderedDict(), "Y": OrderedDict()}

    def _read_mesh_data(self, thyclines):
        mandatory_kws = [self._K, self._Ep, self._Z]
        for line in thyclines:
            spline = line.split()
            for key_mesh in mandatory_kws:
                if key_mesh.lower() in line.lower() and len(self._thyc_mesh) < 3:
                    idx = get_first_digit(spline)
                    typ = int if key_mesh == "K" else np.float64
                    self._thyc_mesh[key_mesh] = np.array(spline[idx:], dtype=typ)

        # Check mesh data
        for key_mesh in mandatory_kws:
            if key_mesh not in self._thyc_mesh:
                msg = "Mesh %s not found" % key_mesh
                raise IOError(msg)

        if check_contiguous(self._thyc_mesh[self._K]) is False:
            msg = "THYC discretization (K) is not contiguous"
            raise IOError(msg)

        cells_count = list(set([len(i) for i in self._thyc_mesh.values()]))
        if len(cells_count) != 1:
            msg = "Number of items mismatch between %s" % mandatory_kws
            raise IOError(msg)

        if check(self._thyc_mesh[self._Z], self._thyc_mesh[self._Ep], 0) is False:
            # Premier cas, decalage de 1 verifié sur tout l'axe, on corrige
            if check(self._thyc_mesh[self._Z], self._thyc_mesh[self._Ep], 1) is True:
                ep0 = (
                    2 * (self._thyc_mesh[self._Z][1] - self._thyc_mesh[self._Z][0])
                    - self._thyc_mesh[self._Ep][0]
                )
                self._thyc_mesh[self._Ep] = np.roll(self._thyc_mesh[self._Ep], 1)
                self._thyc_mesh[self._Ep][0] = ep0
                if check(self._thyc_mesh[self._Z], self._thyc_mesh[self._Ep], 0) is False:
                    msg = "Invalid THYC file : %s and %s do not match" % (self._Z, self._Ep)
                    raise IOError(msg)
            # Second cas, decalage de 1 vérifié sur 2 positions, on tolere.
            elif check(self._thyc_mesh[self._Z][:2], self._thyc_mesh[self._Ep][:2], 0) is True:
                pass
            else:
                msg = "Invalid THYC file : %s and %s do not match and cannot be repaired" % (
                    self._Z,
                    self._Ep,
                )
                raise IOError(msg)

        # Z shift
        z0mac3 = self._thyc_mesh[self._Z][0] - 0.5 * self._thyc_mesh[self._Ep][0]
        self._thyc_mesh[self._Z] -= z0mac3

    def _read_thyc_data(self, thyclines):
        for line in thyclines:
            spline = line.split()

            # Recherche des blocs dans les lignes *
            if all(i in line for i in ("*", "en (N)")):
                if "AXIAL" in line:
                    key_block = "AXIAL"
                elif "TENSEURS" in line:
                    key_block = "M2TEN"
                elif "DEVELOPPEE" in line:
                    key_block = "M1DEV"
                else:
                    assert False

            # Recherches des valeurs dans les autres lignes
            if "*" not in line.strip() and len(line.strip()) != 0:
                assert key_block is not None

                if "TRANSVERSES" in line:
                    key_dir = spline[-3]
                    assert key_dir in ("X", "Y")

                else:
                    vline = tuple(map(float, spline))
                    i, j = int(vline[0]), int(vline[1])
                    forces = np.array(vline[2:])
                    errmsg = "Items mismatch for position '%s' (%s, %s)"

                    if key_block in ("M2TEN", "M1DEV"):
                        self._thyc_data[key_block][key_dir][i, j] = forces
                        if not len(forces) == self.cells_number:
                            raise IOError(errmsg % (key_block, i, j))
                    elif key_block in ("AXIAL",):
                        self._thyc_data[key_block][i, j] = forces
                        if len(forces) != 1:
                            raise IOError(errmsg % (key_block, i, j))
                    else:
                        assert False

    def read_thyc_file(self, fname):
        """
        Transversal force along the Y(THYC) axis.

        Up to THYC 6.0 the file EFFORTS is buggy, this reader performs a fix  a posteriori.

        Arguments:
            fname (str): Path to the THYC file (EFFORTS)

        """
        self._reset_structures()

        with open(fname) as f:
            all_lines = f.readlines()

        self._read_mesh_data(all_lines)
        # Keep only lines without mesh data
        sub_lines = [
            l
            for l in all_lines
            if not any(x.lower() in l.lower() for x in [self._K, self._Ep, self._Z])
        ]
        self._read_thyc_data(sub_lines)

    def get_transversal_load_profile(self, i, j, direction, coeff):
        """
        Transversal force along the X(THYC) axis

        Arguments:
            i (int): The X (THYC) position of the assembly
            j (int): The Y (THYC) position of the assembly
            direction (str): The load direction (THYC), either X or Y
            coeff (float): Multiplicative coefficient

        Returns:
            (px, py): The load profile along the axial axis.
        """

        assert direction in ("X", "Y")

        force = self._get_transversal_force(direction, i, j)
        epaisseur = self.cells_size_from_center
        cote = self.cells_center

        x_axis = []
        y_axis = []
        applied_force = []

        # Pour aller de l embout inferieur jusqu'a la premiere grille.
        start_eb = 0
        stop_eb = self.grids_index[0]
        som_l = sum(epaisseur[start_eb:stop_eb])
        som_f = sum(coeff * force[start_eb:stop_eb])
        som_feq = som_f / (som_l + 0.25 * epaisseur[stop_eb])

        # Point1
        x1 = cote[start_eb] - 0.5 * epaisseur[start_eb] - THYC_EPSILON
        y1 = som_feq
        # Point2
        x2 = cote[stop_eb] - 0.5 * epaisseur[stop_eb] + THYC_EPSILON
        y2 = som_feq
        # Point3
        x3 = cote[stop_eb]
        y3 = 0.0

        x_axis.extend([x1, x2, x3])
        y_axis.extend([y1, y2, y3])
        applied_force.extend([som_f, som_f, 0.0])

        # Pour aller de la premiere a la derniere grille.
        for g in range(0, len(self.grids_index) - 1):
            start_me = self.grids_index[g]
            stop_me = self.grids_index[g + 1]

            som_l = sum(epaisseur[start_me + 1 : stop_me])
            som_f = sum(coeff * force[start_me + 1 : stop_me])
            som_feq = som_f / (som_l + 0.25 * (epaisseur[start_me] + epaisseur[stop_me]))

            # Point1
            x1 = cote[start_me] + 0.5 * epaisseur[start_me] - THYC_EPSILON
            y1 = som_feq
            # Point2
            x2 = cote[stop_me] - 0.5 * epaisseur[stop_me] + THYC_EPSILON
            y2 = som_feq
            # Point3
            x3 = cote[stop_me]
            y3 = 0.0

            x_axis.extend([x1, x2, x3])
            y_axis.extend([y1, y2, y3])
            applied_force.extend([som_f, som_f, 0.0])

        # Pour aller de la derniere grille jusqu'a l embout superieur.
        start_eh = self.grids_index[-1]
        stop_eh = len(cote) - 1

        som_l = sum(epaisseur[start_eh + 1 : stop_eh + 1])
        som_f = sum(coeff * force[start_eh + 1 : stop_eh + 1])
        som_feq = som_f / (som_l + 0.25 * epaisseur[start_eh])

        x1 = cote[start_eh] + 0.5 * epaisseur[start_eh] - THYC_EPSILON
        y1 = som_feq
        x2 = cote[stop_eh] + 0.5 * epaisseur[stop_eh] + THYC_EPSILON
        y2 = som_feq

        x_axis.extend([x1, x2])
        y_axis.extend([y1, y2])
        applied_force.extend([som_f, som_f])

        x_axis = [round(v, MAC3_ROUND) for v in x_axis]
        y_axis = [round(v, MAC3_ROUND) for v in y_axis]
        applied_force = [round(v, MAC3_ROUND) for v in applied_force]

        return x_axis, y_axis, applied_force
