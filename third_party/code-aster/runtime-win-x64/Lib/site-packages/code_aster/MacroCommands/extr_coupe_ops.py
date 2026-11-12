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

import copy

import numpy as np
from scipy import interpolate
from scipy.stats import norm

from ..CodeCommands import MODI_REPERE, POST_RELEVE_T, PROJ_CHAMP
from ..Objects import ElasticResult, Mesh, NonLinearResult, ThermalResult, TransientResult
from ..Objects import DataStructureDict, ElasticResultDict, NonLinearResultDict, ThermalResultDict
from ..Utilities import medcoupling as mc
from .crea_coupe_ops import TableCoupes

DIM_MESH = 3
DIM_SPACE = 1
EPSILON = 0.0000001
CORR_TYPE_CLASS = {
    "EVOL_ELAS": ElasticResult,
    "EVOL_NOLI": NonLinearResult,
    "EVOL_THER": ThermalResult,
    "EVOL": TransientResult,
}


def extr_coupe_ops(
    self,
    RESULTAT,
    COUPE,
    REPERE,
    LINEARISATION,
    REPARTITION=None,
    NOM_CHAM=None,
    FORMULE=None,
    MOYENNE=None,
    ECART_TYPE=None,
):
    """Execute the command

    Aguments:
        RESULTAT (sd_resutls) : resutls from global model
        COUPE (sd_table) : table with path description
        NOM_CHAM [string] : list of field to project
        REPERE (string) : define if coordinal system is local or global
        LINEARISATION (string) : define if stress are linearise
        REPARTITION (string) : define space discretisation
        FORMULE (sd_formula) : define user space discretisation
        MOYENNE [float] : define mean of normal distribution
        ECART_TYPE [float] : define std deviation of normal distribution

    Retruns :
        resu_coupe : sd_resutls with fields from RESULTAT on path
    """

    table_coupe = COUPE.EXTR_TABLE()
    path_group = {}

    proj_champ = {}

    point_in = []
    point_out = []
    point_repere = []
    path_name = []
    nb_point = []

    # Reading table path informations
    for row in table_coupe.rows:
        name = row[TableCoupes.ALL_KEYWORDS[TableCoupes.NAMES_ID]]
        point_in.append(
            [
                float(row[TableCoupes.ALL_KEYWORDS[TableCoupes.FIRST_POINT_ID]]),
                float(row[TableCoupes.ALL_KEYWORDS[TableCoupes.FIRST_POINT_ID + 1]]),
                float(row[TableCoupes.ALL_KEYWORDS[TableCoupes.FIRST_POINT_ID + 2]]),
            ]
        )
        point_out.append(
            [
                float(row[TableCoupes.ALL_KEYWORDS[TableCoupes.SECOND_POINT_ID]]),
                float(row[TableCoupes.ALL_KEYWORDS[TableCoupes.SECOND_POINT_ID + 1]]),
                float(row[TableCoupes.ALL_KEYWORDS[TableCoupes.SECOND_POINT_ID + 2]]),
            ]
        )
        point_repere.append(
            [
                float(row[TableCoupes.ALL_KEYWORDS[TableCoupes.THIRD_POINT_ID]]),
                float(row[TableCoupes.ALL_KEYWORDS[TableCoupes.THIRD_POINT_ID + 1]]),
                float(row[TableCoupes.ALL_KEYWORDS[TableCoupes.THIRD_POINT_ID + 2]]),
            ]
        )
        path_name.append(name)
        nb_point.append(int(row[TableCoupes.ALL_KEYWORDS[TableCoupes.NUMBER_OF_NODES_ID]]))
        path_group[name] = row[TableCoupes.ALL_KEYWORDS[TableCoupes.GROUPS_ID]].split(" ")

    function_param = {}
    if REPARTITION == "UNIFORME":
        function_param[REPARTITION] = None
    elif REPARTITION == "GAUSSIENNE":
        function_param[REPARTITION] = [MOYENNE, ECART_TYPE]
    elif REPARTITION == "UTILISATEUR":
        function_param[REPARTITION] = FORMULE
    elif LINEARISATION == "OUI":
        function_param["UNIFORME"] = None

    mesh = create_meshes_path(
        path_name, point_in, point_out, nb_point, "NON", function_param, path_group
    )

    # Convert MEDCouplingMesh to aster mesh
    aster_mesh = Mesh()
    aster_mesh.buildFromMedCouplingMesh(mesh)

    # Projection field to path
    proj_champ["MAILLAGE_2"] = aster_mesh
    proj_champ["TOUT_ORDRE"] = "OUI"

    if NOM_CHAM == None:
        proj_champ["TOUT_CHAM"] = "OUI"
    else:
        proj_champ["NOM_CHAM"] = NOM_CHAM

    compo_results = issubclass(type(RESULTAT), DataStructureDict)

    if compo_results:
        if isinstance(RESULTAT, ThermalResultDict):
            resu_coupe = ThermalResultDict("resu1")
        elif isinstance(RESULTAT, ElasticResultDict):
            resu_coupe = ElasticResultDict("resu1")
        elif isinstance(RESULTAT, NonLinearResultDict):
            resu_coupe = NonLinearResultDict("resu1")

        for result_name in RESULTAT.keys():
            result = RESULTAT[result_name]
            global_mesh = result.getMesh()
            proj_champ["MAILLAGE_1"] = global_mesh
            proj_champ["RESULTAT"] = result
            resu_coupe[result_name] = PROJ_CHAMP(**proj_champ)

            if REPERE == "LOCAL":
                resu_coupe[result_name] = modify_coordinate_system(
                    resu_coupe[result_name],
                    table_coupe,
                    path_name,
                    point_in,
                    point_out,
                    point_repere,
                    aster_mesh,
                )

    else:
        global_mesh = RESULTAT.getMesh()
        proj_champ["MAILLAGE_1"] = global_mesh
        proj_champ["RESULTAT"] = RESULTAT
        resu_coupe = PROJ_CHAMP(**proj_champ)

        if REPERE == "LOCAL":
            resu_coupe = modify_coordinate_system(
                resu_coupe, table_coupe, path_name, point_in, point_out, point_repere, aster_mesh
            )

    # Linearise stress
    if LINEARISATION == "OUI":
        mesh_line = create_meshes_path(
            path_name, point_in, point_out, nb_point, LINEARISATION, function_param, path_group
        )
        # Convert MEDCouplingMesh to aster mesh
        aster_mesh_line = Mesh()
        aster_mesh_line.buildFromMedCouplingMesh(mesh_line)

        if compo_results:
            for result_name in resu_coupe.keys():
                result = resu_coupe[result_name]
                resu_coupe[result_name] = line_coupe(result, path_name, mesh_line, aster_mesh_line)
        else:
            resu_coupe = line_coupe(resu_coupe, path_name, mesh_line, aster_mesh_line)

    return resu_coupe


def modify_coordinate_system(
    resu_coupe, table_coupe, path_name, point_in, point_out, point_repere, aster_mesh
):
    """Compute local coordinate system

    Aguments:
        resu_coupe (sd_resutls) : resutls on path
        table_coupe (sd_table) : table with path description
        path_name [string] : list of path name
        point_in [float] : first point coordinates for each path
        point_out [float] : last point coordinates for each path
        point_repere [float] : third point coordinates for each path
        aster_mesh (sd_mesh) : path mesh

    Retruns :
        resu_coupe : sd_resutls with fields from RESULTAT on local coordiante system
    """

    modi_repere = {}

    dim = resu_coupe.getMesh().getDimension()

    typeCham = {2: "VECT_2D", 3: "VECT_3D", 4: "TENS_2D", 6: "TENS_3D"}

    modi_repere["AFFE"] = []
    modi_repere["MODI_CHAM"] = []

    fieldNames = resu_coupe.getFieldsNames()
    for name in fieldNames:
        field = resu_coupe._getFieldOnNodesReal(name, 1)
        field_cmp = field.getComponents()
        order_cmp = reorder_cmp(field_cmp)
        modi_repere["MODI_CHAM"].append(_F(TYPE_CHAM=typeCham[len(field_cmp)], NOM_CHAM=name))

    if dim == 2:
        for iPath in range(len(table_coupe.rows)):
            angle = compute_nautile_angle(point_in[iPath], point_out[iPath], point_repere[iPath])
            modi_repere["AFFE"].append(_F(ANGL_NAUT=angle, GROUP_NO=path_name[iPath]))
    else:
        for iPath in range(len(table_coupe.rows)):
            vect_x, vect_y = compute_repere(point_in[iPath], point_out[iPath], point_repere[iPath])
            modi_repere["AFFE"].append(_F(VECT_X=vect_x, VECT_Y=vect_y, GROUP_NO=path_name[iPath]))

    resu_local = MODI_REPERE(
        RESULTAT=resu_coupe, TOUT_ORDRE="OUI", REPERE="UTILISATEUR", **modi_repere
    )

    resu_local.setMesh(aster_mesh)
    resu_local.build()

    resu_coupe = resu_local

    return resu_coupe


def reorder_cmp(field_cmp):
    tmp_cmp = copy.deepcopy(field_cmp)

    order_dict = {
        2: ["X", "Y"],
        3: ["X", "Y", "Z"],
        4: ["XX", "YY", "ZZ", "XY"],
        6: ["XX", "YY", "ZZ", "XY", "XZ", "YZ"],
        8: ["XX", "YY", "XY", "XX", "YY", "XY", "X", "Y"],
    }

    ref_order = order_dict[len(field_cmp)]
    cmp_order = []
    for ref_cmp in ref_order:
        ocmp = list(filter(lambda x: x.endswith(ref_cmp), tmp_cmp))[0]
        tmp_cmp.remove(ocmp)
        cmp_order.append(ocmp)

    return cmp_order


def line_coupe(resu, path_name, mc_mesh, mesh_aster):
    """Linearise fields

    Arguments:
        resu (*DataStructure*) : sd_results from aster
        path_name [string] : list of path names
        mc_mesh (*DataStructure*) : MEDCouplingMesh with path
        mesh_aster (*DataStructure*) : aster mesh with path

    Returns :
        resu_coupe : sd_results with linearise fields
    """

    numeOrdr = resu.getAccessParameters()["NUME_ORDRE"]
    fields_names = resu.getFieldsNames()

    post_releve = {}
    post_releve["ACTION"] = []
    test_releve = {}
    test_releve["ACTION"] = []
    field_cmp = {}
    dico = {}
    moment_0 = {}
    moye_int = {}
    moye_ext = {}

    for field_name in fields_names:
        field = resu.getField(field_name, 1)
        field_cmp[field_name] = field.getComponents()
        dico[field_name] = [0] * len(numeOrdr)

        for path in path_name:
            post_releve["ACTION"].append(
                _F(
                    INTITULE=path,
                    OPERATION="MOYENNE",
                    GROUP_NO=path,
                    RESULTAT=resu,
                    NOM_CHAM=field_name,
                    TOUT_ORDRE="OUI",
                    TOUT_CMP="OUI",
                )
            )

            moment_0[path] = copy.deepcopy(dico)
            moye_int[path] = copy.deepcopy(dico)
            moye_ext[path] = copy.deepcopy(dico)

    table_post = POST_RELEVE_T(**post_releve)
    table = table_post.EXTR_TABLE()

    for row in table.rows:
        path = row["INTITULE"]
        field = row["NOM_CHAM"]
        nume = row["NUME_ORDRE"]
        if row["QUANTITE"] == "MOMENT_0":
            moment_0[path][field][nume - 1] = [row[c] for c in field_cmp[field]]
        elif row["QUANTITE"] == "MOYE_INT":
            moye_int[path][field][nume - 1] = [row[c] for c in field_cmp[field]]
        elif row["QUANTITE"] == "MOYE_EXT":
            moye_ext[path][field][nume - 1] = [row[c] for c in field_cmp[field]]
        else:
            pass

    medresult = mc.MEDFileData()
    meshes = mc.MEDFileMeshes()

    med_fields = mc.MEDFileFields()
    nb_path = len(moment_0.keys())
    iField = 0

    mesh_field = mc_mesh.getMeshAtLevel(0)

    # Create field with linearise fields
    for field_name in fields_names:
        nb_cmp = len(field_cmp[field_name])
        field_file = mc.MEDFileFieldMultiTS()
        for no in numeOrdr:
            sigm_noeu = resu.getField(field_name, no)
            sigm_in = np.zeros((nb_cmp, nb_path))
            sigm_out = np.zeros((nb_cmp, nb_path))

            for iCmp in range(nb_cmp):
                sigm_in[iCmp], _ = sigm_noeu.getValuesWithDescription(
                    field_cmp[field_name][iCmp], groups=["NODES_IN"]
                )
                sigm_out[iCmp], _ = sigm_noeu.getValuesWithDescription(
                    field_cmp[field_name][iCmp], groups=["NODES_OUT"]
                )

            iPath = 0
            sigm = []
            for path in moment_0.keys():
                sigm1 = sigm_in[:, iPath]
                sigm2 = moye_int[path][field_name][no - 1]
                sigm3 = moment_0[path][field_name][no - 1]
                sigm4 = moye_ext[path][field_name][no - 1]
                sigm5 = sigm_out[:, iPath]
                sigm += sigm1.tolist() + sigm2 + sigm3 + sigm4 + sigm5.tolist()
                iPath += 1

            field = mc.MEDCouplingFieldDouble(mc.ON_NODES, mc.ONE_TIME)
            field.setName("Line-" + field_name)
            field.setMesh(mesh_field)
            internal_desc = "-".join((sigm_noeu.getPhysicalQuantity(), field_name))
            field.setDescription(internal_desc)
            ctime = resu.getTime(no)
            field.setTime(ctime, no, no)
            fieldArray = mc.DataArrayDouble(sigm, mesh_field.getNumberOfNodes(), nb_cmp)
            fieldArray.setName(field_name + "_" + str(no))
            for iCmp in range(nb_cmp):
                fieldArray.setInfoOnComponent(iCmp, field_cmp[field_name][iCmp])
            field.setArray(fieldArray)

            field.checkConsistencyLight()

            field_file.appendFieldNoProfileSBT(field)

        med_fields.setFieldAtPos(iField, field_file)
        iField += 1

    meshes.pushMesh(mc_mesh)
    medresult.setMeshes(meshes)
    medresult.setFields(med_fields)

    resu_coupe = resu.__class__.fromMedCouplingResult(medresult, mesh_aster)

    return resu_coupe


def create_meshes_path(path_name, point_in, point_out, nb_point, line, function, path_group):
    """Create mesh for path discretisation

    Arguments:
        path_name [string] : list of names for each path
        point_in [float] : list of coords of first points
        point_out [float] : list of coords of last points
        nb_point [int] : list of nulber of points for each path
        line (string) : value of LINEARISATION keyword if linearisation of stress
        function : dico with parameters to create function of discretisation

    Returns :
        med_file : mesh with all path
    """

    path_mesh = mc.MEDCouplingUMesh("All_path", DIM_MESH)
    path_mesh.setMeshDimension(DIM_SPACE)

    nodalConnPerCell = []
    coords = []
    node_id_beg = []
    node_id_end = []

    if line == "OUI":
        nb_point = [5] * len(path_name)

    for j in range(len(path_name)):
        nb_coords = len(coords) // 3
        for i in range(nb_coords, sum(nb_point[:j]) + nb_point[j] - 1):
            nodalConnPerCell += [mc.NORM_SEG2, i, i + 1]
        if line == "OUI":
            coords += compute_coords_line(point_in[j], point_out[j])
        elif "UNIFORME" in function.keys() or nb_point[j] == 2:
            coords += compute_coords(point_in[j], point_out[j], nb_point[j])
        else:
            coords += compute_coords_func(point_in[j], point_out[j], nb_point[j], function)

        nodalIndex = list(range(0, len(nodalConnPerCell) + 1, 3))

        nodalCellInt = mc.DataArrayInt(nodalConnPerCell, len(nodalConnPerCell), 1)
        nodalIndexInt = mc.DataArrayInt(nodalIndex, len(nodalIndex), 1)

    coordsArr = mc.DataArrayDouble(coords, sum(nb_point), DIM_MESH)

    path_mesh.setConnectivity(nodalCellInt, nodalIndexInt, True)

    path_mesh.setCoords(coordsArr)

    med_file = mc.MEDFileUMesh.New()
    med_file.setMeshAtLevel(0, path_mesh)

    groups = {}
    group_path_list = []
    for key in path_group.keys():
        for val in path_group[key]:
            if val not in groups.keys():
                groups[val] = [[], []]

    # Create groups of nodes and cells
    for k in range(len(path_name)):
        node_list = list(range(sum(nb_point[:k]), sum(nb_point[:k]) + nb_point[k]))
        node_id = mc.DataArrayInt(node_list)
        node_id.setName(path_name[k])
        med_file.addGroup(1, node_id)

        node_id_end += [sum(nb_point[:k]) + nb_point[k] - 1]
        node_id_beg += [sum(nb_point[:k])]

        elem_list = list(range(sum(nb_point[:k]) - k, sum(nb_point[:k]) + nb_point[k] - k - 1))
        elem_id = mc.DataArrayInt(elem_list)
        elem_id.setName(path_name[k])
        med_file.addGroup(0, elem_id)

        for gr_path in path_group[path_name[k]]:
            groups[gr_path][0] += node_list
            groups[gr_path][1] += elem_list

    node_end = mc.DataArrayInt(node_id_end)
    node_end.setName("NODES_OUT")
    node_beg = mc.DataArrayInt(node_id_beg)
    node_beg.setName("NODES_IN")
    med_file.addGroup(1, node_beg)
    med_file.addGroup(1, node_end)

    for group in groups.keys():
        node_group = mc.DataArrayInt(groups[group][0])
        elem_group = mc.DataArrayInt(groups[group][1])

        node_group.setName(group)
        elem_group.setName(group)

        med_file.addGroup(1, node_group)
        med_file.addGroup(0, elem_group)

    med_file.rearrangeFamilies()

    return med_file


def compute_coords(point_in, point_out, nb_point):
    """Computing coordinates of points from paths for uniform discretisation

    Arguments:
        point_in [float] : list of coordinates from first points
        point_out [float] : list of coordinates from last points
        nb_point [int] : number of points in path

    Returns:
        list_coords [float] : list of coordinates from all points in each path
    """

    p_first = np.array(point_in).reshape((1, 3))
    p_last = np.array(point_out).reshape((1, 3))

    delta = (p_last - p_first) / (nb_point - 1)

    points = np.zeros((nb_point - 1, 3))
    points += np.arange(nb_point - 1).reshape((nb_point - 1, 1))
    list_point = p_first + delta * points

    list_coord = sum(list_point.tolist(), [])

    list_coord += point_out

    return list_coord


def compute_coords_func(point_in, point_out, nb_point, function):
    """Computing coordinates of points from paths for general discretisation

    Arguments:
        point_in [float] : list of coordinates from first points
        point_out [float] : list of coordinates from last points
        nb_point [int] : number of points in path
        function : dico with parameters to create function of discretisation

    Returns:
        list_coords [float] : list of coordinates from all points in each path
    """

    epsilon = 0.000000000001
    x = np.arange(nb_point - 1) / (nb_point - 2)
    if "GAUSSIENNE" in function.keys():
        f = f_gauss(x, function["GAUSSIENNE"][0], function["GAUSSIENNE"][1])
    else:
        i = 0
        f = np.zeros(nb_point - 1)
        for val in x:
            f[i] = function["UTILISATEUR"](val)
            i += 1
        f -= np.min(f)
    f = f.reshape((nb_point - 1, 1))

    y = np.zeros((nb_point - 1))

    for i in range(nb_point - 2):
        y[i + 1] = y[i] + (1 / 2) * ((f[i] + f[i + 1]) * (x[i + 1] - x[i])) + epsilon

    y /= y[-1]

    p_first = np.array(point_in).reshape((1, 3))
    p_last = np.array(point_out).reshape((1, 3))

    inter = interpolate.interp1d(y, x, fill_value="extrapolate", bounds_error=False)

    list_point = (p_first * (1 - inter(x.reshape(nb_point - 1, 1)))) + (
        p_last * inter(x.reshape(nb_point - 1, 1))
    )

    list_coord = sum(list_point.tolist(), [])

    list_coord += point_out

    return list_coord


def compute_coords_line(point_in, point_out):
    """Computing coordinates of points from paths for linearisation

    Arguments:
        point_in [float] : list of coordinates from first points
        point_out [float] : list of coordinates from last points

    Returns:
        list_coords [float] : list of coordinates from all points in each path
    """

    p_first = np.array(point_in)
    p_last = np.array(point_out)

    direction = p_last - p_first
    norm = np.linalg.norm(direction)
    delta = direction * EPSILON / norm

    mid_point = (p_first + p_last) / 2

    point_line_in = p_first + delta
    point_line_out = p_last - delta

    list_coord = (
        point_in + point_line_in.tolist() + mid_point.tolist() + point_line_out.tolist() + point_out
    )

    return list_coord


def compute_repere(x, y, z):
    """Computing vector to define local coordinate system in 3D space

    Arguments :
        x [float] : coordinates from first point to define new system
        y [float] : coordinates from second point to define new system
        z [float] : coordinates from third point to define new system

    Returns:
        vect_1 [float] : first vector to create new coordinate system
        vect_2 [float] : second vector to create new coordinate system
    """

    vect_1 = [y[0] - x[0], y[1] - x[1], y[2] - x[2]]
    vect_2 = [z[0] - x[0], z[1] - x[1], z[2] - x[2]]

    return vect_1, vect_2


def compute_nautile_angle(point_in, point_out, third_point):
    """Compute angle to pass from global coordinate system to a local one in 2D space

    Arguments :
        point_in [float] : coordinates from first point of path
        point_out [float] : coordinates from last point of path

    Returns :
        angle (float) : angles for rotation of 2D coordinate system
    """

    p_in = np.array(point_in)
    p_out = np.array(point_out)

    vect_path = p_out - p_in
    x_axis = np.array([1, 0, 0])

    angle = np.degrees(
        np.arccos(np.dot(x_axis, vect_path) / (np.linalg.norm(x_axis) * np.linalg.norm(vect_path)))
    )

    return angle


def f_gauss(x, nu, sig):
    """define normal distribution

    Arguments:
       x (float) : varible from function
       nu (float) : mean from normal distribution
       sig (float) : variance from normal distribution

    Results:
       value (float) : value computing
    """

    value = norm.pdf(x, loc=nu, scale=sig)

    return value
