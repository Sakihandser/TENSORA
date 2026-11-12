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
import sys
from math import cos, sin

import numpy as np
from libaster import projectionAlongDirection

from ..CodeCommands import CREA_TABLE
from ..Messages import UTMESS
from ..Objects.table_py import Table


def crea_coupe_ops(
    self, COUPE, MAILLAGE, NOM_AUTO, PREFIXE=None, NUME_INIT=None, PAS=None, REVOLUTION=None
):
    """Execute the command.

    Arguments:
        COUPE (sd_table)        : input table
        MAILLAGE(sd_maillage)   : input mesh
        NOM_AUTO(bool)          : automatic naming of paths
        PREFIXE(str)            : common prefix of the path names
        NUME_INIT(int)          : first id of the name of the path
        PAS(int)                : progression in the numerotation between two successive paths
        REVOLUTION(list)        : structure contenant les paramètres pour obtenir des coupes en révolution

    Returns:
        sd_table which descibes paths that begin/end on the skin of the mesh
    """
    table_coupes_py = COUPE.EXTR_TABLE()
    table_coupes = TableCoupes(table_coupes_py)
    table_coupes.change_names(
        auto_name=NOM_AUTO, prefix=PREFIXE, first_num=NUME_INIT, progression=PAS
    )
    table_coupes.check_integrity()
    table_coupes._check_group_maill(MAILLAGE)
    if REVOLUTION:
        table_coupes.check_parameters_revol(REVOLUTION, MAILLAGE)
        table_coupes.create_coupes_revol(REVOLUTION)
        table_coupes.check_path_name(msg="REVO")
    table_coupes.update_position_on_structure_skin(MAILLAGE)
    dic_table = table_coupes.dict_CREA_TABLE()
    table_coupes_aster = CREA_TABLE(**dic_table)

    return table_coupes_aster


class TableCoupes(Table):
    ALL_KEYWORDS = [
        "COOR_ORIG_X",
        "COOR_ORIG_Y",
        "COOR_ORIG_Z",
        "COOR_EXTR_X",
        "COOR_EXTR_Y",
        "COOR_EXTR_Z",
        "COOR_TROIS_X",
        "COOR_TROIS_Y",
        "COOR_TROIS_Z",
        "NOM",
        "GROUP",
        "GROUP_MA_ORIG",
        "GROUP_MA_EXTR",
        "NB_POINTS",
    ]
    ATTEMPTED_TYPES = [
        ["R", "I"],
        ["R", "I"],
        ["R", "I"],
        ["R", "I"],
        ["R", "I"],
        ["R", "I"],
        ["R", "I"],
        ["R", "I"],
        ["R", "I"],
        ["K24", "I"],
        ["K24", "I"],
        ["K24", "I"],
        ["K24", "I"],
        ["I"],
    ]
    DIMENSION = 3
    FIRST_POINT_ID = 0
    SECOND_POINT_ID = 3
    THIRD_POINT_ID = 6
    NUMBER_OF_NODES_ID = 13
    MAIL_IN_ID = 11
    MAIL_OUT_ID = 12
    NAMES_ID = 9
    GROUPS_ID = 10

    def __init__(self, table=None, rows=None, para=None, typ=None, titr=None, nom=None):
        if table is not None:
            super(TableCoupes, self).__init__(
                rows=table.rows, para=table.para, typ=table.type, titr=table.titr, nom=table.nom
            )
        elif (
            rows is not None
            and para is not None
            and typ is not None
            and titr is not None
            and nom is not None
        ):
            super(TableCoupes, self).__init__(rows=rows, para=para, typ=typ, titr=titr, nom=nom)
        else:
            raise SystemExit("You have to specify at least a table or a set of table parameters")

    def check_integrity(self):
        """Check if the input table has the right format"""
        self.check_keywords()
        self.check_types()
        self.check_path_name()
        self.check_path_nb_nodes()

    def check_keywords(self):
        """Check if the input table has the right column names"""
        for i, key in enumerate(self.para):
            if key.lower() != TableCoupes.ALL_KEYWORDS[i].lower():
                valk = [TableCoupes.ALL_KEYWORDS[i], key, ", ".join(TableCoupes.ALL_KEYWORDS)]
                UTMESS("F", "COUPE_1", vali=(i + 1), valk=valk)

    def check_types(self):
        """Check if each column of the input table has the right type of data"""
        dico_types = {"R": "décimal", "I": "entier", "K24": "chaîne de caractères"}
        for i, typ in enumerate(self.type):
            if typ not in TableCoupes.ATTEMPTED_TYPES[i]:
                valk = [
                    " ou ".join([dico_types[j] for j in TableCoupes.ATTEMPTED_TYPES[i]]),
                    dico_types[typ],
                ]
                UTMESS("F", "COUPE_5", vali=(i + 1), valk=valk)

    def check_path_name(self, msg=""):
        """Check if a name is used several times in the table"""
        already_set_name = []
        for line in self.rows:
            name = str(line[TableCoupes.ALL_KEYWORDS[TableCoupes.NAMES_ID]])
            if name in already_set_name:
                if msg == "REVO":
                    UTMESS("A", "COUPE_12", valk=name)
                else:
                    UTMESS("F", "COUPE_7", valk=name)
            else:
                already_set_name.append(name)

    def check_path_nb_nodes(self):
        """Check if all path have a minimal number of nodes of 2"""
        for line in self.rows:
            nb_nodes = int(line[TableCoupes.ALL_KEYWORDS[TableCoupes.NUMBER_OF_NODES_ID]])
            if nb_nodes < 2:
                UTMESS("F", "COUPE_14", valk=[line[TableCoupes.ALL_KEYWORDS[TableCoupes.NAMES_ID]]])

    def change_names(self, auto_name="NON", prefix=None, first_num=None, progression=None):
        """
        change the names of the section accordingly to the template:
            PREFIX_"SECTION_ID",
        where SECTION_ID is different on each path.
        For the i-th path SECTION_ID=first_num+i*progression
        """
        nb_coupes = len(self.rows)
        key_name = str(TableCoupes.ALL_KEYWORDS[TableCoupes.NAMES_ID])
        if auto_name == "OUI":
            max_num = int(first_num) + (nb_coupes - 1) * int(progression)
            nb_zeros = len(str(max_num))
            for i, val in enumerate(self.rows):
                new_section_name = ""
                if prefix:
                    new_section_name += prefix + "_"
                new_section_name += str(int(first_num) + i * int(progression)).zfill(nb_zeros)
                val[key_name] = new_section_name

    def update_position_on_structure_skin(self, mesh):
        """
        Move the nodes of all paths for being on the mesh skin
        """
        DIMENSION = 3
        connectivity = mesh.getConnectivity()
        dim = mesh.getDimension()
        coordinates = np.reshape(np.array(mesh.getCoordinates().getValues()), (-1, DIMENSION))

        #######HACK#########

        correspondance_types = {
            "POINT1": "PO1",
            "SEG2": "SE2",
            "SEG3": "SE3",
            "SEG4": "SE4",
            "TRIA3": "TR3",
            "TRIA6": "TR6",
            "TRIA7": "TR7",
            "QUAD4": "QU4",
            "QUAD8": "QU8",
            "QUAD9": "QU9",
            "TETRA4": "TE4",
            "TETRA10": "T10",
            "PENTA6": "PE6",
            "PENTA15": "P15",
            "PENTA18": "P18",
            "PYRA5": "PY5",
            "PYRA13": "P13",
            "HEXA8": "HE8",
            "HEXA20": "H20",
            "HEXA27": "H27",
        }
        #######################
        for j, line in enumerate(self.rows):
            surf_in = str(line[TableCoupes.ALL_KEYWORDS[TableCoupes.MAIL_IN_ID]])
            surf_out = str(line[TableCoupes.ALL_KEYWORDS[TableCoupes.MAIL_OUT_ID]])
            direction, length = self.get_direction(j)
            path_name = str(line[TableCoupes.ALL_KEYWORDS[TableCoupes.NAMES_ID]])
            for i in range(2):
                found_projection = False
                beta_old = sys.float_info.max
                if i == 0:
                    surf = surf_in
                    point_id = TableCoupes.FIRST_POINT_ID
                else:
                    surf = surf_out
                    point_id = TableCoupes.SECOND_POINT_ID
                list_elements = mesh.getCells(surf)
                point = [
                    line[self.para[point_id]],
                    line[self.para[point_id + 1]],
                    line[self.para[point_id + 2]],
                ]

                for element in list_elements:
                    element_nodes = connectivity[element]
                    elem_type = correspondance_types[mesh.getCellTypeName(element)]
                    elem_coords = []
                    for node in element_nodes:
                        elem_coords.append(coordinates[node, :].tolist())
                    elem_coords = sum(elem_coords, [])
                    elem_size = _compute_elem_size(elem_coords, DIMENSION)
                    mesh_projection = 1
                    if _check_if_not_null_jacobian(
                        np.array(elem_coords).reshape(-1, DIMENSION), direction, dim
                    ):
                        mesh_projection, beta, ksi1, ksi2 = projectionAlongDirection(
                            type_elem=elem_type,
                            nb_node=len(element_nodes),
                            nb_dim=dim,
                            elem_coor=elem_coords,
                            pt_coor=point,
                            iter_maxi=1000,
                            tole_maxi=1.0e-6,
                            proj_dire=direction,
                        )
                    if mesh_projection < 1:
                        if self._check_if_on_element(elem_type, ksi1, ksi2):
                            # do the projection once if intersection on element border
                            if not found_projection:
                                found_projection = True
                                for k in range(3):
                                    line[self.para[point_id + k]] -= beta * direction[k]
                            if abs(beta_old) < 10 * (
                                np.max(coordinates, axis=None) - np.min(coordinates, axis=None)
                            ):
                                if (
                                    abs(beta - beta_old) > 1e-3 * abs(beta_old)
                                    and abs(beta - beta_old) > 1e-1 * elem_size
                                ):
                                    if max(abs(beta), abs(beta_old)) > 5e-2 * length:
                                        k_values = [surf, path_name]
                                        UTMESS("F", "COUPE_3", valk=k_values)
                            beta_old = beta
                if not found_projection:
                    UTMESS("F", "COUPE_6", valk=[surf, path_name])
                point_in_updated = []
                point_out_updated = []
                for k in range(3):
                    point_in_updated.append(line[self.para[TableCoupes.FIRST_POINT_ID + k]])
                    point_out_updated.append(line[self.para[TableCoupes.SECOND_POINT_ID + k]])

            # Case if updated points are the same
            if np.linalg.norm(np.array(point_in_updated) - np.array(point_out_updated)) < 1e-12:
                UTMESS("F", "COUPE_8", valk=path_name)

    def get_direction(self, line_num):
        """Method for retrieving the projection direction of a path

        Args:
            line_num (int): id of the path

        Returns:
            list[float]: vector of the direction
            float: length of the path

        """
        line = self.rows[line_num]
        point_id = TableCoupes.FIRST_POINT_ID
        points_in = [
            line[self.para[point_id]],
            line[self.para[point_id + 1]],
            line[self.para[point_id + 2]],
        ]
        point_id = TableCoupes.SECOND_POINT_ID
        points_out = [
            line[self.para[point_id]],
            line[self.para[point_id + 1]],
            line[self.para[point_id + 2]],
        ]
        vect_dir = [xout - xin for xin, xout in zip(points_in, points_out)]
        length = np.linalg.norm(np.array(vect_dir))
        vect_dir = [x / length for x in vect_dir]
        return vect_dir, length

    def _check_group_maill(self, mesh):
        """
        Check if all defined inner skin and outer skin mesh groups
        are well defined on the mesh
        """
        lgrma = [gr[0] for gr in mesh.LIST_GROUP_MA()]
        for path in self.rows:
            surf_in = str(path[TableCoupes.ALL_KEYWORDS[TableCoupes.MAIL_IN_ID]])
            surf_out = str(path[TableCoupes.ALL_KEYWORDS[TableCoupes.MAIL_OUT_ID]])
            path_name = str(path[TableCoupes.ALL_KEYWORDS[TableCoupes.NAMES_ID]])
            if surf_in not in lgrma:
                UTMESS("F", "COUPE_2", valk=["d'entrée", surf_in, path_name])
            if surf_out not in lgrma:
                UTMESS("F", "COUPE_2", valk=["de sortie", surf_out, path_name])

    def _check_if_on_element(self, elem_type, ksi, eta):
        """Check if the projected point is inside the found element
        thanks to parametric coordinates

        Args:
            elem_type (str): element type (i.e. QU8, TR3, SE2)
            ksi (float): first coordinate in the reference element
            eta (float): second coordinate in the reference element

        Returns:
            bool: flag that say if the coordinates are inside the element
        """
        on_element = True
        if "SE" in elem_type:
            on_element = on_element and (eta == 0)
            on_element = on_element and (ksi >= -1.0) and (ksi <= 1)
        elif "TR" in elem_type:
            on_element = on_element and (ksi + eta <= 1)
            on_element = on_element and (ksi <= 1) and (ksi >= 0)
            on_element = on_element and (eta <= 1) and (eta >= 0)
        elif "QU" in elem_type:
            on_element = on_element and (ksi <= 1) and (ksi >= -1)
            on_element = on_element and (eta <= 1) and (eta >= -1)
        else:
            on_element = False
            UTMESS("F", "COUPE_4", valk=elem_type)
        return on_element

    def create_coupes_revol(self, revol_list):
        """Function that creates paths by revolution

        Args:
            revol_list (dict): dictionary containing the keywords given by the user
        """
        points_ids = [
            TableCoupes.FIRST_POINT_ID,
            TableCoupes.SECOND_POINT_ID,
            TableCoupes.THIRD_POINT_ID,
        ]
        points_keys = [self.para[point_id : point_id + 3] for point_id in points_ids]
        name_key = str(TableCoupes.ALL_KEYWORDS[TableCoupes.NAMES_ID])
        gr_in_key = str(TableCoupes.ALL_KEYWORDS[TableCoupes.MAIL_IN_ID])
        gr_out_key = str(TableCoupes.ALL_KEYWORDS[TableCoupes.MAIL_OUT_ID])
        coupes_dico = {i: [] for i in range(len(self.rows))}

        for revol in revol_list:
            filtre, filter_key = self._get_filter(revol["NOM_COUPE"], revol["GROUP_COUPE"])

            if revol["ANGLE_AUTO"] == "OUI":
                nombre_intervalles = (
                    revol["NOMBRE"] if abs(revol["ANGLE_MAX"]) == 360.0 else revol["NOMBRE"] - 1
                )
                angles = [
                    revol["ANGLE_MAX"] / nombre_intervalles * i for i in range(revol["NOMBRE"])
                ][1:]
            else:
                angles = revol["ANGLE"]

            axe = revol["AXE"] / np.linalg.norm(revol["AXE"])

            for j, line in enumerate(self.rows):
                if filtre and line[filter_key] not in filtre:
                    continue

                section_name = line[name_key]

                # retrieve points' coordinates
                points = [[line[c] for c in point_keys] for point_keys in points_keys]

                # translate points to center of rotation
                points_transl = np.subtract(points, revol["CENTRE"])

                for angle in angles:
                    line = line.copy()
                    rot_matrix = get_rotation_matrix(axe, np.radians(angle))
                    # rotate and translate back points
                    points_rot = np.add(
                        [np.matmul(rot_matrix, point) for point in points_transl], revol["CENTRE"]
                    )
                    line.update(zip(np.concatenate(points_keys), np.concatenate(points_rot)))
                    angle = abs(angle)
                    angle_str = (
                        str(int(angle))
                        if float(angle).is_integer()
                        else str(round(angle, 1)).replace(".", "-")
                    )
                    line[name_key] = f"{revol['PREFIXE']}{angle_str}-{section_name}"
                    line[gr_in_key] = revol["GROUP_MA_ORIG"]
                    line[gr_out_key] = revol["GROUP_MA_EXTR"]
                    coupes_dico[j].append(line)

        index = 0
        for j in range(len(self.rows)):
            index += 1
            for new_line in coupes_dico[j]:
                self.rows.insert(index, new_line)
                index += 1

    def _get_filter(self, name_filter, group_filter):
        """[summary]

        Args:
            name_filter ([type]): [description]
            group_filter ([type]): [description]

        Returns:
            [type]: [description]
        """
        if name_filter is None and group_filter is None:
            return None, None
        if name_filter:
            return name_filter, str(self.para[TableCoupes.NAMES_ID])
        else:
            return group_filter, str(self.para[TableCoupes.GROUPS_ID])

    def check_parameters_revol(self, revol_list, mesh):
        """Function that checks if parameters of the REVOLUTION keywords are coherent

        Args:
            revol_list (dict): dictionary containing the keywords given by the user
            mesh (libaster.Mesh): the mesh of the structure
        """
        group_mail_list = mesh.getGroupsOfCells()
        missing_name, missing_group = None, None
        name_list = [str(line[self.para[TableCoupes.NAMES_ID]]) for line in self.rows]
        group_list = [str(line[self.para[TableCoupes.GROUPS_ID]]) for line in self.rows]
        for revol in revol_list:
            if revol["ANGLE_MAX"] is not None and revol["ANGLE_MAX"] == 0:
                UTMESS("F", "COUPE_13", valk="ANGLE_MAX")
            elif revol["LISTE_ANGLE"] and 0 in revol["LISTE_ANGLE"]:
                UTMESS("F", "COUPE_13", valk="LISTE_ANGLE")

            missing_mail_group = [
                n
                for n in [revol["GROUP_MA_ORIG"], revol["GROUP_MA_EXTR"]]
                if n not in group_mail_list
            ]
            if missing_mail_group:
                UTMESS("F", "COUPE_9", valk=missing_mail_group[0])

            if revol["NOM_COUPE"]:
                missing_name = [n for n in revol["NOM_COUPE"] if n not in name_list]
                if missing_name:
                    UTMESS("F", "COUPE_10", valk=missing_name[0])
            elif revol["GROUP_COUPE"]:
                missing_group = [n for n in revol["GROUP_COUPE"] if n not in group_list]
                if missing_group:
                    UTMESS("F", "COUPE_11", valk=missing_group[0])


def _check_if_not_null_jacobian(coords, vect, dim, tole=1.0e-9):
    """
    Check if an intersection is possible between the plane of the element
    and the given direction
    """
    vect /= np.linalg.norm(vect)
    if dim == 3:  # if normal and direction are orthogonal
        norm = np.cross(coords[0] - coords[1], coords[0] - coords[2])
        norm /= np.linalg.norm(norm)
        not_null_jacob = (abs(np.dot(norm, vect))) > tole
    if dim == 2:  # if the direction of the SEG element and direction of projection are colinear
        dire = coords[0] - coords[1]
        dire /= np.linalg.norm(dire)
        not_null_jacob = np.linalg.norm(np.cross(dire, vect)) > tole

    return not_null_jacob


def _compute_elem_size(node_coords, dim):
    """
    Compute the element size as the maximal distance between all points un a given list sorted
    [x1, y1, z1, x2, y2, z2, ..., xn, yn, zn]
    """
    elem_size = 0.0
    node_coords = np.reshape(np.array(node_coords), (-1, dim))
    for i, node_i in enumerate(node_coords):
        for j, node_j in enumerate(node_coords):
            if i <= j:
                continue
            elem_size = max(elem_size, np.linalg.norm(node_i - node_j))

    return elem_size


def get_rotation_matrix(vector, teta):
    """https://en.wikipedia.org/wiki/Rotation_matrix#Rotation_matrix_from_axis_and_angle
    Arguments:
        vector(list(float)) : normalized vector for axis rotation
        teta(float)         : angle of rotation around axis in radians
    """
    ux, uy, uz = vector
    R = [
        [
            cos(teta) + ux**2 * (1 - cos(teta)),
            ux * uy * (1 - cos(teta)) - uz * sin(teta),
            ux * uz * (1 - cos(teta)) + uy * sin(teta),
        ],
        [
            uy * ux * (1 - cos(teta)) + uz * sin(teta),
            cos(teta) + uy**2 * (1 - cos(teta)),
            uy * uz * (1 - cos(teta)) - ux * sin(teta),
        ],
        [
            uz * ux * (1 - cos(teta)) - uy * sin(teta),
            uz * uy * (1 - cos(teta)) + ux * sin(teta),
            cos(teta) + uz**2 * (1 - cos(teta)),
        ],
    ]
    return R
