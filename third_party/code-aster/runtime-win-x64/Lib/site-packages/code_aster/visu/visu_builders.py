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

from math import isclose
from pathlib import Path
from typing import Dict, Tuple, List, Iterable, Sequence, Optional

import numpy as np

from ..Utilities.import_helper import medcoupling as mc
from ..Utilities.logger import logger


class VisuCutBuilder:
    NODE: int = 0
    LINE: int = 1
    SURFACE: int = 2
    VOLUME: int = 3

    def __init__(self, mesh_med: mc.MEDFileUMesh, prefix_output_field_name: Optional[str] = None):
        self.mesh_med: mc.MEDFileUMesh = mesh_med

        self.arrays: Dict[Tuple[str, Optional[int], str], np.ndarray] = {}
        self.instants: Dict[Tuple[str, Optional[int], str], float] = {}
        self.components: Dict[Tuple[str, str], Iterable[str]] = {}
        self.nb_nodes: int = mesh_med.getNumberOfNodes()
        self.prefix_output_field_name: Optional[str] = prefix_output_field_name
        self._all_geo_types: List[int] = self.mesh_med.getAllGeoTypes()
        if len(self._all_geo_types) > 1:
            raise NotImplementedError("Multi level meshes are not handled yet")
        self._max_geo_type: int = max(self._all_geo_types)

    def __str__(self):
        return f"""
        instants: {self.instants}
        components: {self.components}
        arrays: {self.arrays}
        mesh_med: {self.mesh_med}
        nb_nodes: {self.nb_nodes}
        """

    def get_output_field_name(self, field_name: str) -> str:
        if self.prefix_output_field_name is None:
            return field_name
        return f"{self.prefix_output_field_name}_{field_name}"

    @classmethod
    def from_aster_mesh(
        cls, mesh, prefix_output_field_name: Optional[str] = None
    ) -> "VisuCutBuilder":
        mesh_med = mesh.createMedCouplingMesh()
        return cls(mesh_med=mesh_med, prefix_output_field_name=prefix_output_field_name)

    def add_field_on_nodes_from_aster_result_all_timesteps(
        self, aster_result, field_name: str, nodes: List[int], med_field_name: Optional[str] = None
    ):
        nume_ordres = aster_result.getAccessParameters()["NUME_ORDRE"]
        instants = aster_result.getAccessParameters().get("INST", [0])

        # Create field with linearise fields
        if len(instants) != len(nume_ordres):
            raise ValueError(
                f"instants {instants} and nume_ordres {nume_ordres} must have the same lengths"
            )
        for instant, nume_ordre in zip(instants, nume_ordres):
            self.add_field_on_nodes_from_aster_result_1_timestep(
                aster_result=aster_result,
                field_name=field_name,
                nodes=nodes,
                nume_ordre=nume_ordre,
                instant=instant,
                med_field_name=med_field_name,
            )

    def add_field_on_nodes_from_aster_result_1_timestep(
        self,
        aster_result,
        field_name: str,
        nodes: List[int],
        nume_ordre: int,
        instant: float,
        med_field_name: Optional[str] = None,
    ):
        if med_field_name is None:
            med_field_name = field_name
        field = aster_result.getField(field_name, nume_ordre).toSimpleFieldOnNodes()
        # extract values for cut group only
        values = field.getValues()[0][nodes]
        components = field.getComponents()
        self.add_field_on_nodes(
            field_name=med_field_name,
            nodes=nodes,
            values=values,
            components=components,
            nume_ordre=nume_ordre,
            instant=instant,
        )

    def add_field_on_nodes(
        self,
        field_name: str,
        nodes: Sequence[int],
        values: np.ndarray,
        components: Iterable[str],
        nume_ordre: Optional[int] = None,
        instant: Optional[float] = None,
    ):
        assert len(nodes) == values.shape[0]
        stock_address: Tuple[str, Optional[int], str] = (field_name, nume_ordre, mc.ON_NODES)
        already_instanciated_field = stock_address in self.arrays

        if nume_ordre is not None:
            if instant is None:
                raise ValueError("if nume_ordre is defined instant must also be defined")
            if already_instanciated_field:
                previous_instant = self.instants[stock_address]
                if not isclose(previous_instant, instant):
                    raise ValueError(
                        f"{instant} differs from already affected instant {previous_instant}"
                    )
            else:
                self.instants[stock_address] = instant

        if already_instanciated_field:
            previous_components = self.components[(field_name, mc.ON_NODES)]
            if previous_components != components:
                raise ValueError(
                    f"{components} differs from already affected components {previous_components}"
                )

            assert self.arrays[stock_address].shape == (self.nb_nodes, values.shape[1] + 1)
        else:
            self.arrays[stock_address] = np.full(
                shape=(self.nb_nodes, values.shape[1] + 1), fill_value=np.nan
            )
            self.components[(field_name, mc.ON_NODES)] = components

        current_array = self.arrays[stock_address]
        assert max(nodes) <= current_array.shape[0]
        current_array[nodes, 0] = nodes
        current_array[nodes, 1:] = values

    def add_group(self, name: str, ids: Sequence[int], geo_type: int):
        """
        Adds a group to mesh_med
        Args:
            name: Name of the new group
            ids: index of the items (cells or nodes to add to this group)
            geo_type: geometry of target items VisuCutBuilder.NODE, VisuCutBuilder.LINE,
                      VisuCutBuilder.SURFACE, VisuCutBuilder.VOLUME
        """
        # truncate group name because med only allows names length < 80
        grp_name = name[:80]
        group = mc.DataArrayInt(list(ids))
        group.setName(name=grp_name)

        self.mesh_med.addGroup(meshDimRelToMaxExt=self._max_geo_type - geo_type, ids=group)

    def write(self, filepath: Path):
        if not self.arrays:
            logger.warn("Cannot write visu output because no data where set")
            return
        field_files: Dict[Tuple[str, str], mc.MEDFileFieldMultiTS] = {}

        self.mesh_med.write(str(filepath), 2)

        for (field_name, nume_ordre, location), current_array in self.arrays.items():
            if location != mc.ON_NODES:
                raise NotImplementedError(f"location {location} is not implemented yet")
            field_address = (field_name, location)
            output_field_name = self.get_output_field_name(field_name=field_name)

            # Medcoupling field
            field_values = mc.DataArrayDouble(current_array[:, 1:].tolist())
            field_values.setInfoOnComponents(self.components[field_address])
            field_values.setName(name=output_field_name)

            medc_node_field = mc.MEDCouplingFieldDouble(location, mc.ONE_TIME)
            medc_node_field.setName(name=output_field_name)
            medc_node_field.setArray(array=field_values)
            medc_node_field.setNature(nat=mc.IntensiveMaximum)

            medc_node_field.setMesh(mesh=self.mesh_med.getMeshAtLevel(meshDimRelToMax=0))

            medc_node_field.checkConsistencyLight()
            medfield = mc.MEDFileField1TS()
            medfield.setFieldNoProfileSBT(field=medc_node_field)

            if nume_ordre is None:
                # medfield.write(fileName=str(filepath), mode=0)
                medfield.setTime(iteration=1, order=0, val=0)
                # continue
            else:
                instant = self.instants[(field_name, nume_ordre, location)]
                medfield.setTime(iteration=nume_ordre, order=0, val=instant)

            field_multi_ts = field_files.setdefault(field_address, mc.MEDFileFieldMultiTS())
            field_multi_ts.pushBackTimeStep(medfield)

        file_fields = mc.MEDFileFields()
        for i_field, field_file in enumerate(field_files.values()):
            file_fields.setFieldAtPos(i_field, field_file)

        file_fields.write(str(filepath), 0)
