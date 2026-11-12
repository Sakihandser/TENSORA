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

from ...Utilities import logger, no_new_attributes, SearchList, force_list
from ...Messages import UTMESS
from .bases import EventId, Observer
from .context import ContextMixin

from ...Objects.table_py import Table
from ...CodeCommands import CREA_TABLE


class Observation(ContextMixin, Observer):
    """This object extracts values during a nonlinear process.

    - It contains the definition of the observable values:
      - what (field, components)
      - where (group of cells, nodes)
      - how (extraction, minimal, maximal, mean value)
      - when (during iterations for printing, to valid a time step, to be
        added in a table)
    """

    class Observable:
        """Represent an extraction"""

        field_name = times = location = operation = None
        event = None
        _row = None
        __setattr__ = no_new_attributes(object.__setattr__)

        class Times:
            """When to extract"""

            _timelist = _step = _store_init = None
            __setattr__ = no_new_attributes(object.__setattr__)

            def __init__(self, **kwargs):
                times = None
                if "INST" in kwargs:
                    times = force_list(kwargs["INST"])
                elif "LIST_INST" in kwargs:
                    times = kwargs["LIST_INST"].getValues()
                elif "PAS_OBSE" in kwargs:
                    self._step = kwargs["PAS_OBSE"]
                else:
                    self._step = 1
                self._store_init = kwargs["OBSE_ETAT_INIT"] == "OUI"

                if times is not None:
                    self._timelist = SearchList(
                        times, kwargs.get("PRECISION", 1.0e-6), kwargs["CRITERE"]
                    )
                    assert all(self._timelist.unique(t) for t in times)

            def _to_be_stored(self, idx, time):
                """To known if this time step has to be store.

                Arguments:
                    idx (int): index of the time (restarts at 0 at each new operator).
                    time (float): time step.

                Returns:
                    bool: *True* if the time step has to be store else *False*.
                """
                if idx == 0:
                    return self._store_init
                if self._step is not None:
                    return idx % self._step == 0
                if self._timelist is not None:
                    return time in self._timelist
                return True

        class Location:
            """Where to extract"""

            nodes = cells = components = variNames = None
            eval_elga = points = sub_points = None
            __setattr__ = no_new_attributes(object.__setattr__)

            def __init__(self, mesh, **kwargs):
                field_name = kwargs["NOM_CHAM"]
                if "TOUT" in kwargs:
                    if field_name.endswith("ELEM") or field_name.endswith("ELGA"):
                        self.cells = []
                    else:
                        self.nodes = []
                else:
                    if "GROUP_MA" in kwargs:
                        cells = kwargs["GROUP_MA"]
                        if field_name.endswith("ELEM") or field_name.endswith("ELGA"):
                            self.cells = mesh.getCells(cells)
                        else:
                            self.nodes = mesh.getNodesFromCells(cells, True)
                    elif "MAILLE" in kwargs:
                        cells = kwargs["MAILLE"]
                        if field_name.endswith("ELEM") or field_name.endswith("ELGA"):
                            nb_cells = mesh.getNumberOfCells()
                            self.cells = [
                                cell
                                for cell in [int(cell) - 1 for cell in cells]
                                if cell < nb_cells
                            ]
                        else:
                            raise RuntimeError("MAILLE is not supported")
                    elif "GROUP_NO" in kwargs:
                        self.nodes = mesh.getNodes(kwargs["GROUP_NO"], True)
                    elif "NOEUD" in kwargs:
                        nodes = kwargs["NOEUD"]
                        nb_nodes = mesh.getNumberOfNodes()
                        self.nodes = [
                            node for node in [int(node) - 1 for node in nodes] if node < nb_nodes
                        ]
                    if self.nodes is not None and len(self.nodes) == 0:
                        UTMESS("F", "EXTRACTION_3", field_name)
                    if self.cells is not None and len(self.cells) == 0:
                        UTMESS("F", "EXTRACTION_4", field_name)

                if "NOM_CMP" in kwargs:
                    self.components = kwargs["NOM_CMP"]
                else:
                    self.variNames = kwargs["NOM_VARI"]

                if "EVAL_ELGA" in kwargs:
                    eval_elga = kwargs["EVAL_ELGA"]
                    if eval_elga == "VALE":
                        points = kwargs["POINT"]
                        sub_points = kwargs.get("SOUS_POINT", [1])
                        self.points = [point - 1 for point in points]
                        self.sub_points = [sub_point - 1 for sub_point in sub_points]
                    else:
                        self.eval_elga = eval_elga

            def extract(self, field, behav):
                if self.nodes is not None:
                    logger.debug("** extract observation on field on nodes", field, flush=True)
                    values, (nodes, components) = field.getValuesWithDescription(
                        self.components, self.nodes
                    )
                    values = np.array(values)
                    nodes = np.array(nodes)
                    components = np.array(components)
                    return values, nodes, components, None, None, None

                elif self.cells is not None:
                    logger.debug("** extract observation on field on elem", field, flush=True)
                    if self.variNames is not None:
                        cmpNames = behav.variNameToCmp(self.cells, self.variNames)
                        self.components = list(dict.fromkeys(cmpNames))
                    values, (
                        cells,
                        components,
                        points,
                        sub_points,
                    ) = field.toSimpleFieldOnCells().getValuesWithDescription(
                        self.components, self.cells
                    )
                    values = np.array(values)
                    cells = np.array(cells)
                    components = np.array(components)
                    points = np.array(points)
                    sub_points = np.array(sub_points)
                    variNames = None

                    # filter with NOM_VARI
                    if self.variNames is not None:
                        idx = []
                        i = 0
                        nb_cell = len(self.cells)
                        variNames = np.empty((len(values),), dtype="U16")
                        for i_cell, cell in enumerate(self.cells):
                            idx_cell = np.argwhere(cells == cell)[:, 0]
                            for i_vari, variName in enumerate(self.variNames):
                                component = cmpNames[nb_cell * i_vari + i_cell]
                                idx_component = np.argwhere(components == component)[:, 0]
                                idx_cell_component = np.intersect1d(
                                    idx_cell, idx_component, assume_unique=True
                                )
                                variNames[idx_cell_component] = variName
                                idx.extend(idx_cell_component)
                                i += 1
                        values = values[idx]
                        cells = cells[idx]
                        components = components[idx]
                        variNames = variNames[idx]
                        points = points[idx]
                        sub_points = sub_points[idx]

                    # filter for ELGA
                    if self.eval_elga or self.points is not None:
                        idx = []
                        if self.points is not None:
                            for point in self.points:
                                for sub_point in self.sub_points:
                                    idx_point = np.argwhere(np.array(points) == point)[:, 0]
                                    idx_sub_point = np.argwhere(np.array(sub_points) == sub_point)[
                                        :, 0
                                    ]
                                    idx.extend(
                                        np.intersect1d(idx_point, idx_sub_point, assume_unique=True)
                                    )
                            if not len(idx):
                                raise Exception(
                                    f"OBSERVATION: no values for points {self.points} and sub-points {self.sub_points}"
                                )
                            idx.sort()
                        else:
                            argmax_or_argmin = np.argmax if self.eval_elga == "MAX" else np.argmin
                            for cell in list(dict.fromkeys(cells)):
                                idx_cell = np.argwhere(cells == cell)[:, 0]
                                for component in self.components:
                                    idx_component = np.argwhere(components == component)[:, 0]
                                    idx_cell_component = np.intersect1d(
                                        idx_cell, idx_component, assume_unique=True
                                    )
                                    if not len(idx_cell_component):
                                        raise Exception(
                                            f"OBSERVATION: no values for cell {cell} and component {component}"
                                        )
                                    idx.append(
                                        idx_cell_component[
                                            argmax_or_argmin(values[idx_cell_component])
                                        ]
                                    )
                        idx = np.array(idx)
                        values = values[idx]
                        cells = cells[idx]
                        components = components[idx]
                        if self.variNames is not None:
                            variNames = variNames[idx]
                        if self.points is not None:
                            points = points[idx]
                            sub_points = sub_points[idx]
                        else:
                            points = None
                            sub_points = None
                    return values, cells, components, variNames, points, sub_points

        class Operation:
            """Operations to apply on an extraction"""

            components = variNames = None
            formule = evaluate = None
            absolute = False
            __setattr__ = no_new_attributes(object.__setattr__)

            def __init__(self, **kwargs):
                if "FORMULE" in kwargs:
                    self.formule = kwargs["FORMULE"]
                if "EVAL_CHAM" in kwargs:
                    evaluate = kwargs["EVAL_CHAM"]
                    if evaluate == "MIN":
                        self.evaluate = np.min
                    if evaluate == "MAX":
                        self.evaluate = np.max
                    if evaluate == "MOY":
                        self.evaluate = np.mean
                    if evaluate == "MAXI_ABS":
                        self.evaluate = np.max
                        self.absolute = True
                    if evaluate == "MINI_ABS":
                        self.evaluate = np.min
                        self.absolute = True

                if "NOM_CMP" in kwargs:
                    self.components = kwargs["NOM_CMP"]
                else:
                    self.variNames = kwargs["NOM_VARI"]

            def apply(self, values, nodes_or_cells, components, variNames, points, sub_points):
                # apply FORMULE
                if self.formule:
                    variables = self.formule.getVariables()
                    new_values = []
                    new_nodes_or_cells = []
                    new_points = []
                    new_sub_points = []
                    for node_or_cell in list(dict.fromkeys(nodes_or_cells)):
                        idx = np.argwhere(nodes_or_cells == node_or_cell)[:, 0]
                        if points is not None:
                            for point in list(dict.fromkeys(points)):
                                idx_point = np.argwhere(points == point)[:, 0]
                                idx_point = np.intersect1d(idx, idx_point, assume_unique=True)
                                for sub_point in list(dict.fromkeys(sub_points)):
                                    idx_sub_point = np.argwhere(sub_points == sub_point)[:, 0]
                                    idx_sub_point = np.intersect1d(
                                        idx_point, idx_sub_point, assume_unique=True
                                    )
                                    idx2 = np.searchsorted(components[idx_sub_point], variables)
                                    new_values.append(
                                        self.formule.evaluate(values[idx_sub_point][idx2])[0]
                                    )
                                    new_nodes_or_cells.append(node_or_cell)
                                    new_points.append(point)
                                    new_sub_points.append(sub_point)
                        else:
                            idx2 = np.searchsorted(components[idx], variables)
                            new_values.append(self.formule.evaluate(values[idx][idx2])[0])
                            new_nodes_or_cells.append(node_or_cell)

                    values = np.array(new_values)
                    nodes_or_cells = np.array(new_nodes_or_cells)
                    components = np.array([None] * len(values))
                    if variNames:
                        variNames = np.array([None] * len(values))
                    if points is not None:
                        points = np.array(new_points)
                        sub_points = np.array(new_sub_points)

                # apply EVAL_CHAM
                if self.evaluate:
                    if self.absolute:
                        values = np.abs(values)
                    if self.formule:
                        new_values = [self.evaluate(values)]
                    else:
                        new_values = []
                        if variNames is not None:
                            new_variNames = []
                            for variName in self.variNames:
                                idx = np.argwhere(variNames == variName)[:, 0]
                                new_values.append(self.evaluate(values[idx]))
                                new_variNames.append(variName)
                            variNames = np.array(new_variNames)
                        else:
                            new_components = []
                            for component in self.components:
                                idx = np.argwhere(components == component)[:, 0]
                                if not len(idx):
                                    raise Exception(
                                        f"OBSERVATION: no values for component {component}"
                                    )
                                new_values.append(self.evaluate(values[idx]))
                                new_components.append(component)
                            components = np.array(new_components)
                    values = np.array(new_values)
                    nodes_or_cells = None
                    points = None
                    sub_points = None

                if variNames is not None:
                    components = None

                return values, nodes_or_cells, components, variNames, points, sub_points

        def _init_row(self, i_obs, **kwargs):
            """common values for an observation"""
            self._row = {}
            if "TITRE" in kwargs:
                self._row["NOM_OBSERVATION"] = kwargs["TITRE"]
            else:
                self._row["NOM_OBSERVATION"] = f"OBSERVATION_{i_obs}"
            self._row["TYPE_OBJET"] = "R"
            for key in ("NOM_CHAM", "EVAL_CHAM"):
                self._row[key] = kwargs[key]
            if "EVAL_ELGA" in kwargs:
                if kwargs["EVAL_ELGA"] != "VALE":
                    self._row["EVAL_ELGA"] = kwargs["EVAL_ELGA"]
            if "FORMULE" in kwargs:
                self._row["EVAL_CMP"] = kwargs["FORMULE"].getName()

        def __init__(self, i_obs, mesh, **kwargs):
            self.field_name = kwargs["NOM_CHAM"]
            self._init_row(i_obs, **kwargs)
            self.times = self.Times(**kwargs)
            self.location = self.Location(mesh, **kwargs)
            self.operation = self.Operation(**kwargs)

    __needs__ = ("problem", "state", "keywords")
    _observables = None
    _index = None
    _rows = _para = _typ = None
    _step_idx = None
    _idx_reuse = None
    _event_ids = None
    __setattr__ = no_new_attributes(object.__setattr__)

    @classmethod
    def builder(cls, context):
        """Default builder for :py:class:`Observation` object.

        Args:
            context (Context): Context of the problem.

        Returns:
            instance: New object.
        """
        instance = super().builder(context)
        observations = instance.get_keyword("OBSERVATION")
        if observations:
            table = context.result.getTable("OBSERVATION")
            if table:
                # REUSE : get previous table if it exists
                instance._rows = table.EXTR_TABLE().rows[:]
            mesh = context.problem.getMesh()
            for i_obs, kwargs in enumerate(observations, 1):
                observable = cls.Observable(i_obs, mesh, **kwargs)
                instance._event_ids |= EventId.NonLinearOperator
                observable.event = EventId.NonLinearOperator
                instance._observables.append(observable)

        return instance

    def __init__(self):
        self._observables = []
        self._rows = []
        self._para = [
            "NOM_OBSERVATION",
            "TYPE_OBJET",
            "NUME_REUSE",
            "NUME_OBSE",
            "INST",
            "NOM_CHAM",
            "EVAL_CHAM",
            "NOM_CMP",
            "NOM_VARI",
            "EVAL_CMP",
            "NOEUD",
            "MAILLE",
            "EVAL_ELGA",
            "POINT",
            "SOUS_POINT",
            "VALE",
            "NUME_GLOBAL_NOEUD",
        ]
        self._typ = [
            "K16",
            "K16",
            "I",
            "I",
            "R",
            "K16",
            "K8",
            "K8",
            "K16",
            "K8",
            "K8",
            "K8",
            "K8",
            "I",
            "I",
            "R",
            "I",
        ]
        self._index = 0
        self._idx_reuse = 0
        self._event_ids = 0
        self._step_idx = 0

    def _incr_index(self):
        """Update of NUME_OBSE"""
        self._index += 1
        return self._index

    def notify(self, event):
        """Receive notification from event, store the data from a future use
        by actions.

        Arguments:
            event (EventSource): Object that sends the notification.
        """
        if not event.eid & self._event_ids:
            return
        if event.eid & EventId.IterationSolver:
            logger.debug("+ check for observations during iterations")
            for observable in self._observables:
                if observable.event & EventId.IterationSolver:
                    raise NotImplementedError("archiver le suivi ddl ici")
                self.state.debugPrint(recursive=True)
        elif event.eid & EventId.TimeStepper:
            logger.debug("+ check for observations for time stepper")
            for observable in self._observables:
                if observable.event & EventId.IterationSolver:
                    raise NotImplementedError("faire le delta grandeur ici")
        elif event.eid & EventId.NonLinearOperator:
            logger.debug("+ check for observations at convergence")
            idx = self._step_idx
            self._step_idx += 1
            time = self.state.time_curr
            global_nodes = None
            if self.problem.getMesh().isParallel():
                global_nodes = self.problem.getMesh().getLocalToGlobalNodeIds()
            for observable in self._observables:
                if observable.event & EventId.NonLinearOperator and observable.times._to_be_stored(
                    idx, time
                ):
                    field = self.state.asdict()[observable.field_name]
                    behav = self.problem.getBehaviourProperty()
                    (values, nodes_or_cells, components, variNames, points, sub_points) = (
                        observable.location.extract(field, behav)
                    )
                    (values, nodes_or_cells, components, variNames, points, sub_points) = (
                        observable.operation.apply(
                            values, nodes_or_cells, components, variNames, points, sub_points
                        )
                    )
                    nodes = cells = None
                    if observable.location.nodes:
                        nodes = nodes_or_cells
                    else:
                        cells = nodes_or_cells
                    observable._row["NUME_REUSE"] = self._idx_reuse
                    observable._row["INST"] = time
                    for i, value in enumerate(values):
                        # nmobsz.F90
                        row = observable._row.copy()
                        row["NUME_OBSE"] = self._incr_index()
                        row["VALE"] = value
                        if cells is not None:
                            row["MAILLE"] = str(cells[i] + 1)
                        if nodes is not None:
                            row["NOEUD"] = str(nodes[i] + 1)
                            if global_nodes:
                                row["NUME_GLOBAL_NOEUD"] = global_nodes[nodes[i]]
                        if components is not None:
                            row["NOM_CMP"] = components[i]
                        if variNames is not None:
                            row["NOM_VARI"] = variNames[i]
                        if points is not None:
                            row["POINT"] = points[i] + 1
                            row["SOUS_POINT"] = sub_points[i] + 1
                        self._rows.append(row)
        else:
            raise TypeError(f"unsupported event: eid={event.eid!r}")

    def setReuseIndex(self, idx_reuse):
        """set of NUME_REUSE"""
        self._idx_reuse = idx_reuse

    def getTable(self):
        """return OBSERVATION table, containing all the observations
        to be attached to the nonlinear result"""
        if not self._rows:
            return None
        table_py = Table(self._rows, self._para, self._typ)
        dprod = table_py.dict_CREA_TABLE()
        return CREA_TABLE(**dprod)
