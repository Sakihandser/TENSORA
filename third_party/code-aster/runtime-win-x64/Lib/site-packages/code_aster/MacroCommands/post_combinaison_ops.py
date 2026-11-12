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

from collections import Counter, OrderedDict
from itertools import product

import numpy as np
import numpy.matlib

from ..Cata.Syntax import _F
from ..CodeCommands import CALC_TABLE, CREA_RESU, CREA_TABLE, CREA_CHAMP
from ..Messages import UTMESS


def aster_table_to_array(aster_table, without_columns=()):
    """Transform an aster table to np.array containing only numerical values

    Arguments :
        aster_table (table_py): table to be transformed to np.array.
        without_columns (tuple): columns to be excluded for the final array.

    Returns:
        np.array: the np.array table
    """
    return np.array(
        [
            # replace None by 0.
            [x or 0.0 for x in getattr(aster_table, name).values()]
            for name, type_ in zip(aster_table.para, aster_table.type)
            if type_ in ("R", "I") and (name not in without_columns)
        ]
    ).T


def expand_table(coefficients_table, nb_orders):
    """Expand columns and lines of the given table according to nb_orders

    Arguments :
        coefficients_table (table_py): coefficents table to be expanded.
        nb_orders (np.array): max order for each column, i.e., parameter, of the table.

    Returns:
        np.array : the expanded table.
        np.array : the new combination names after table expansion
        np.array : the new columns names after table expansion
    """
    # Transform aster table to a numpy array
    table = aster_table_to_array(coefficients_table)
    # Extract combination names
    combination_names = list(coefficients_table[coefficients_table.para[0]].values().values())[0]
    # Extract parameters names
    parameters_names = coefficients_table.para[1:]

    # Expand coeffcients table according to orders
    n_rows, n_columns = table.shape
    duplication_table = np.matlib.repmat(nb_orders, n_rows, 1)
    # if the value is zero no duplication
    duplication_table[table == 0] = 1
    # the product of the number of duplication of each column given the number
    # of duplication of one row.
    nb_duplication_rows = duplication_table.prod(axis=1)
    final_nb_rows = nb_duplication_rows.sum()
    # the duplication of the columns are only dependant of the nb_orders
    final_nb_columns = nb_orders.sum()
    # empty table to fill with the given table
    final_table = np.zeros((final_nb_rows, final_nb_columns), dtype=float)
    # the cumulative sum of the duplication rows give the positions in the final table
    # add zero at the beginning because it starts at zero
    rows_positions = nb_duplication_rows.cumsum()
    rows_positions = np.insert(rows_positions, 0, 0)
    # same for the columns but here the duplication corresponds to the nb_orders
    columns_positions = nb_orders.cumsum()
    columns_positions = np.insert(columns_positions, 0, 0)
    # final parameters names
    final_parameters_names = [
        parameters_names[i_order] + str(i) if order > 1 else parameters_names[i_order]
        for i_order, order in enumerate(nb_orders)
        for i in range(1, order + 1)
    ]
    # combination_extended_names
    combination_extended_names = [""] * final_nb_rows
    for i_row in range(n_rows):
        r_start = rows_positions[i_row]
        # Iteration over all the combinations possible with the duplicate rows
        # each combination give the index position of the value for of each column
        for i_sub_row, indices in enumerate(product(*map(range, duplication_table[i_row, :]))):
            final_table[r_start + i_sub_row, columns_positions[:-1] + indices] = table[i_row, :]
            combination_extended_names[r_start + i_sub_row] = combination_names[i_row] + "".join(
                "." + str(index + 1)
                for i, index in enumerate(indices)
                if duplication_table[i_row, i] > 1
            )

    return final_table, combination_extended_names, final_parameters_names


def restrain_field(field, model, groups=(), is_node=True):
    """
    Restrain the given field on the specified groups.

    Args:
        field (FieldOnNodes or FieldOnCells): Aster field to be restrained.
        model (Model): Aster model to be used.
        groups (list): List of groups to restrain to (default is empty list).
        is_node (bool): Indicates whether the group is node-based (GROUP_NO)
                        or element-based (GROUP_MA). Defaults to True.

    Returns:
        FieldOnNodes or FieldOnCells: The new restrained field.
    """
    type_cham = f"{field.getFieldType()}_{field.getPhysicalQuantity()}"

    # Initialize the argument dictionary
    crea_champ_args = {"TYPE_CHAM": type_cham, "OPERATION": "ASSE", "MODELE": model, "ASSE": {}}

    # Add group or default based on node/element flag
    if groups:
        group_key = "GROUP_NO" if is_node else "GROUP_MA"
        crea_champ_args["ASSE"][group_key] = groups
    else:
        crea_champ_args["ASSE"]["TOUT"] = "OUI"

    # Add field data
    crea_champ_args["ASSE"]["CHAM_GD"] = field

    # For element-based groups, add zero-prolongation if necessary
    if not is_node and groups:
        crea_champ_args["PROL_ZERO"] = "OUI"

    # Create and return the new field
    return CREA_CHAMP(**crea_champ_args)


def extract_results_values_by_field(
    results, orders, field_names, model=None, cells_groups=(), nodes_groups=()
):
    """Extract values from each result by field name

    Arguments:
        results (list): list of results to be used for extraction.
        orders (np.array): array with the maximum order for each result.
        field_names(list): list of fields to be extracted by their names.
        model (sd_model): model to be used.
        cells_groups (list): list of groups of cells in case of a field restriction.
        nodes_groups (list): list of groups of nodes in case of a field restriction.

    Returns:
        dict:  values by field name.
        dict:  masks by field name.
    """
    values_by_field = {}
    for field_name in field_names:
        field = results[0].getField(field_name, 1)
        field_type = field.getType()[:7]
        counter = 0
        field_array = list()
        for i, order in enumerate(orders):
            for rank in order:
                field = results[i].getField(field_name, rank)
                if field_type == "CHAM_NO":
                    field_array.append(restrain_field(field, model, nodes_groups, True))
                else:
                    if cells_groups:
                        field_array.append(
                            restrain_field(field, model, cells_groups, is_node=False)
                        )
                    else:
                        field_array.append(field)
                counter += 1
        values_by_field[field_name] = field_array

    return values_by_field


def count_nb_nodes(table, coupure_name):
    """Count the number of nodes for a given coupure by its name in the given table.

    Arguments:
        table (table_py): table containing the data for the coupure name.
        coupure_name (str) : name of the coupure to be treated.

    Returns:
        int : number of nodes for the coupure.
    """
    nb_nodes_by_order = tuple(
        set(
            Counter(
                rank
                for rank, label in zip(table.values()["NUME_ORDRE"], table.values()["INTITULE"])
                if label == coupure_name
            ).values()
        )
    )
    if len(nb_nodes_by_order) == 1:
        return nb_nodes_by_order[0]
    else:
        UTMESS("F", "PCOMB_11", valk=coupure_name, vali=nb_nodes_by_order[0])


def extract_coefficents_column_names(coefficients_table, affe):
    """Extract the names of columns from coefficients table
    Arguments:
        coefficients_table (table_py): table with coefficients for each combination
            and each column name
        affe (list) : list of the results or tables to be combined.

    Returns:
        list[str] : list of the column names.

    Raises:
        PCOMB_4 : if a given result or table has a name that is not in the
            coefficients table.
        PCOMB_5 : if a column name from coefficients table refers to a
            non-existant result or table.
    """
    column_names = [
        column_name
        for column_name, type_ in zip(coefficients_table.para, coefficients_table.type)
        if type_ == "R" or type_ == "I"
    ]
    # check if the column names of the table are identical to the case names
    case_names = []
    for i, a in enumerate(affe):
        case_name = a.get("NOM_CAS")
        if case_name not in column_names:
            UTMESS("F", "PCOMB_4", valk=case_name, vali=i)
        case_names.append(case_name)
    for column_name in column_names:
        if column_name not in case_names:
            UTMESS("F", "PCOMB_5", valk=column_name)
    return column_names


def post_combinaison_ops(self, TABLE_COEF_FIN=None, **args):
    """Command to combine results of separate calculations on the structure."""
    affe = args.get("AFFE")
    combination_type = args.get("TYPE_COMB")
    field_names = args.get("NOM_CHAM")
    model = args.get("MODELE")
    coefficients_table = args.get("TABLE_COEF").EXTR_TABLE()
    table_resu = args.get("TABLE_COEF_RESU")
    cells_groups = args.get("GROUP_MA")
    if cells_groups is None:
        cells_groups = ()
    nodes_groups = args.get("GROUP_NO")
    if nodes_groups is None:
        nodes_groups = ()

    coefficients_column_names = extract_coefficents_column_names(coefficients_table, affe)
    output_result = None
    if combination_type == "RESULTAT":
        # |------------------------------------|
        # | 1 - Verification of data coherence |
        # |------------------------------------|
        # Get the results
        results_by_name = {affe_i.get("NOM_CAS"): affe_i.get("RESULTAT") for affe_i in affe}
        results = [results_by_name[result_name] for result_name in coefficients_column_names]
        # Get the mesh
        mesh = results[0].getMesh()
        # Check if all the meshes are identical
        if any(result.getMesh() is not mesh for result in results[1:]):
            UTMESS("F", "PCOMB_2")
        # If the combination is restrained on elements groups
        if cells_groups is not None:
            for group_name in cells_groups:
                if not mesh.hasGroupOfCells(group_name):
                    UTMESS("F", "PCOMB_10", valk=group_name)
        # Check if all wanted fields exist in all given results
        if field_names is None:
            field_names = results[0].getFieldsNames()
        for i, result in enumerate(results):
            for field_name in field_names:
                if field_name not in result.getFieldsNames():
                    UTMESS("F", "PCOMB_1", valk=field_name, vali=i + 1)
        # Get the orders of each result
        nb_orders = np.array([len(result.getIndexes()) for result in results])
        orders_by_result = [result.getIndexes() for result in results]
        # transform all results into a numpy array with 3 dimensions (nb_cases, n_order, nb_fields)
        results_by_field = extract_results_values_by_field(
            results,
            orders_by_result,
            field_names,
            model=model,
            cells_groups=cells_groups,
            nodes_groups=nodes_groups,
        )
        # |------------------------------------|
        # | 2 - Coefficients table resu        |
        # |------------------------------------|
        (expanded_coefficients_table, expanded_combination_names, expanded_parameters_names) = (
            expand_table(coefficients_table, nb_orders)
        )
        # |------------------------------------------|
        # | 3 - multiplication by the coefficients   |
        # |------------------------------------------|
        combination_results = {}
        for field_name, field_values in results_by_field.items():
            combination_results[field_name] = []
            for idx in range(expanded_coefficients_table.shape[0]):
                count = 0
                comb_resu = None
                for k, v in zip(expanded_coefficients_table[idx, :], field_values):
                    if count == 0:
                        comb_resu = float(k) * v
                        count += 1
                    else:
                        comb_resu += float(k) * v
                combination_results[field_name].append(comb_resu)
        # |------------------------------------|
        # | 4 - Build mult_elas  resu          |
        # |------------------------------------|
        # Create fields for the mutl_elas result
        for field_name in combination_results:
            # fill field with values
            l_affe = []
            for rank in range(len(combination_results[field_name])):
                # Generate empty field
                l_affe.append(
                    _F(
                        NOM_CHAM=field_name,
                        CHAM_GD=combination_results[field_name][rank],
                        NOM_CAS=expanded_combination_names[rank],
                        MODELE=model,
                    )
                )
            # Create result for the first field occurence
            kwargs = {"AFFE": l_affe, "OPERATION": "AFFE", "TYPE_RESU": "MULT_ELAS"}
            if output_result is not None:
                kwargs["reuse"] = output_result
            output_result = CREA_RESU(**kwargs)
    elif combination_type == "TABLE":
        # Initialisation of filtered tables
        tables_by_name = {affe_i.get("NOM_CAS"): affe_i.get("TABLE") for affe_i in affe}
        # Apply filters on each table
        if args.get("FILTRE") is not None:
            filter_action = tuple(
                _F(OPERATION="FILTRE", **filter_) for filter_ in args.get("FILTRE")
            )
        else:
            filter_action = None
        filtered_tables = [
            (
                CALC_TABLE(TABLE=tables_by_name[table_name], ACTION=filter_action)
                if filter_action is not None
                else tables_by_name[table_name]
            )
            for table_name in coefficients_column_names
        ]
        # # Check all columns are the same between tables
        for i, table in enumerate(filtered_tables):
            column_names = table.get_nom_para()
            # column INST isn't part of the post-processing and isn't
            # available in all tables
            try:
                column_names.remove("INST")
            except ValueError:
                pass
            # column NOM_CAS isn't part of the post-processing and isn't
            # available in all tables
            try:
                column_names.remove("NOM_CAS")
            except ValueError:
                pass
            if i == 0:
                columns_ref = column_names
            elif sorted(columns_ref) != sorted(column_names):
                UTMESS("F", "PCOMB_3", vali=i + 1)
        # Transform tables from aster format to a tablePy format
        tables_extracted = [table.EXTR_TABLE() for table in filtered_tables]

        # Get the unique list of the names of the 'coupure'
        coupure_names = np.fromiter(
            OrderedDict.fromkeys(tables_extracted[0].values()["NOM"]).keys(), dtype="<U24"
        )
        # Check if each table has the same coupure
        for i, table in enumerate(tables_extracted):
            for coupure_name in coupure_names:
                if coupure_name not in table.values()["NOM"]:
                    UTMESS("F", "PCOMB_6", valk=coupure_name, vali=i + 1)

        nb_nodes = np.ones(len(coupure_names), dtype=int)
        # Extract ranks and orders for each table
        if "NUME_ORDRE" in column_names:
            ranks = [np.array(table.values()["NUME_ORDRE"]) for table in tables_extracted]
            orders = np.array(list(map(max, ranks)), dtype=int)
        else:
            ranks = [np.ones(len(table), dtype=int) for table in tables_extracted]
            orders = np.ones(len(tables_extracted), dtype=int)
        # Create one datas table with all entry tables
        excluded_columns = [
            "NUME_ORDRE",
            "NOM_CAS",
            "NOM",
            "INST",
            "ABSC_CURV",
            "COOR_X",
            "COOR_Y",
            "COOR_Z",
        ]
        column_names = [cl_name for cl_name in column_names if cl_name not in excluded_columns]
        raw_tables = [
            aster_table_to_array(table, without_columns=excluded_columns)
            for table in tables_extracted
        ]
        nb_components = raw_tables[0].shape[1]

        datas_table = np.concatenate(
            [
                table[rank.argsort(kind="mergesort"), :].T.reshape(nb_components, order, -1)
                for table, rank, order in zip(raw_tables, ranks, orders)
            ],
            axis=1,
        )

        # |------------------------------------|
        # | 2 - Coefficients table resu        |
        # |------------------------------------|
        (expanded_coefficients_table, expanded_combination_names, expanded_parameters_names) = (
            expand_table(coefficients_table, orders)
        )

        # |------------------------------------|
        # | 3 - Matrix multiplication          |
        # |------------------------------------|
        combination_results = np.dot(expanded_coefficients_table, datas_table)

        # |------------------------------------|
        # | 4 - Build results table            |
        # |------------------------------------|
        nb_nodes_cumsum = nb_nodes.cumsum()
        nb_nodes_cumsum = np.insert(nb_nodes_cumsum, 0, 0)
        # column_names.extend(['NOM', 'NOM_CAS'])
        columns_k = []
        columns_r = []

        # Components columns
        for j, column_name in enumerate(column_names):
            sorted_indices = np.tile(
                np.repeat(np.arange(nb_nodes.shape[0]), nb_nodes), combination_results.shape[0]
            ).argsort(kind="mergesort")
            column_values = combination_results[:, j, :].flatten()[sorted_indices]
            columns_r.append(_F(LISTE_R=column_values, PARA=column_name))

        # Add 'NOM_CAS' to column_names
        # INTITULE (coupure names)
        nb_rows_by_coupure = nb_nodes * combination_results.shape[0]
        columns_k.append(
            _F(LISTE_K=np.repeat(coupure_names, nb_rows_by_coupure), PARA="NOM", TYPE_K="K24")
        )
        # NOM_CAS
        tiled_expanded_combination_names = np.tile(
            expanded_combination_names, (len(coupure_names), 1)
        )
        repeated_combination_names = [
            coupure_result
            for j, nb in enumerate(coupure_names)
            for coupure_result in np.repeat(
                tiled_expanded_combination_names[j], np.array(nb_nodes)[j]
            )
        ]
        columns_k.append(_F(LISTE_K=repeated_combination_names, PARA="NOM_CAS", TYPE_K="K24"))
        output_result = CREA_TABLE(LISTE=columns_k + columns_r)

    # Generate coefficients table as an aster table
    table_coef_resu = CREA_TABLE(
        LISTE=(
            (_F(LISTE_K=expanded_combination_names, PARA="Cmb", TYPE_K="K24"),)
            + tuple(
                _F(LISTE_R=expanded_coefficients_table[:, j], PARA=name)
                for j, name in enumerate(expanded_parameters_names)
            )
        )
    )

    if table_resu:
        self.register_result(table_coef_resu, table_resu)
    return output_result
