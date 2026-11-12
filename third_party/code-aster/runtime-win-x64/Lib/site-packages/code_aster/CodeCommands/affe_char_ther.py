# coding: utf-8

# Copyright (C) 1991 - 2026  EDF www.code-aster.org
#
# This file is part of Code_Aster.
#
# Code_Aster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Code_Aster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Code_Aster.  If not, see <http://www.gnu.org/licenses/>.


from ..Cata.Language.SyntaxObjects import FactorKeyword
from ..Objects import ThermalLoadReal, ParallelThermalLoadReal, ConnectionMesh, Model
from ..Supervis import ExecuteCommand
from ..Utilities import force_list


class ThermalLoadDefinition(ExecuteCommand):
    """Command that creates the :class:`~code_aster.Objects.ThermalLoadReal`"""

    command_name = "AFFE_CHAR_THER"
    neumannLoads = [
        "FLUX_REP",
        "RAYONNEMENT",
        "ECHANGE",
        "SOURCE",
        "PRE_GRAD_TEMP",
        "ECHANGE_PAROI",
        "CONVECTION",
        "FLUX_NL",
        "SOUR_NL",
        "EVOL_CHAR",
        "LIAISON_CHAMNO",
    ]
    dirichletLoads = [
        "TEMP_IMPO",
        "LIAISON_DDL",
        "LIAISON_GROUP",
        "LIAISON_MAIL",
        "LIAISON_UNIF",
        "LIAISON_CHAMNO",
    ]

    @classmethod
    def _hasDirichletLoadings(cls, keywords):
        """return True if instance has Dirichlet loadings"""
        for key in cls.dirichletLoads:
            if keywords.get(key):
                return True
        return False

    @classmethod
    def _hasNeumannLoadings(cls, keywords):
        """return True if instance has Neumann loadings"""
        for key in cls.neumannLoads:
            if keywords.get(key):
                return True
        return False

    @classmethod
    def _isOnAllEntities(cls, keywords):
        """return True if instance has Neumann loadings"""
        for key in keywords:
            occ = keywords.get(key)
            if isinstance(occ, (list, tuple)):
                for occ2 in occ:
                    if occ2.get("TOUT") is not None:
                        return True
        return False

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        model = keywords["MODELE"]
        l_para = model.getMesh().isParallel()
        l_all = self._isOnAllEntities(keywords)
        if l_para and l_all:
            raise TypeError("Not allowed to mix up parallel mesh and TOUT='OUI'")
        l_neum = self._hasNeumannLoadings(keywords)
        l_diri = self._hasDirichletLoadings(keywords)
        if not model.getMesh().isParallel():
            self._result = ThermalLoadReal(model)
        else:
            if l_neum:
                if l_diri:
                    raise TypeError(
                        "Not allowed to mix up Dirichlet and Neumann \
                        loadings in the same parallel AFFE_CHAR_THER"
                    )
                else:
                    self._result = ThermalLoadReal(model)

    def exec_(self, keywords):
        """Override default _exec in case of parallel load"""
        if isinstance(self._result, ThermalLoadReal):
            super(ThermalLoadDefinition, self).exec_(keywords)
        else:
            model = keywords.pop("MODELE")
            nodeGroups, cellGroups = _getGroups(self._cata, keywords)
            connectionMesh = ConnectionMesh(model.getMesh(), nodeGroups, cellGroups)

            connectionModel = Model(connectionMesh)
            connectionModel.setFrom(model)

            keywords["MODELE"] = connectionModel
            partialThermalLoad = AFFE_CHAR_THER(**keywords)
            keywords["MODELE"] = model
            self._result = ParallelThermalLoadReal(partialThermalLoad, model)

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """

        self._result.build()

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Arguments:
            keywords (dict): User's keywords.
        """
        super().add_dependencies(keywords)
        self.remove_dependencies(keywords, "MODELE")


AFFE_CHAR_THER = ThermalLoadDefinition.run


def _addGroup(mcf, groups, keys):
    for name in keys:
        mc = mcf.get(name)
        if mc:
            groups.update(force_list(mc))


def _excludeGroup(mcf, keys):
    for name in keys:
        if mcf.get(name):
            raise RuntimeError("Keyword %s not accepted in parallel AFFE_CHAR_THER" % name)


def _getGroups(cata, keywords):
    """for parallel load, return all node and cells groups present in AFFE_CHAR_THER, in order to define the connection mesh"""
    load_types = [
        key for key in list(cata.keywords.keys()) if isinstance(cata.keywords[key], FactorKeyword)
    ]
    nodeGroups = set()
    cellGroups = set()
    for key in list(keywords.keys()):
        if key in ("TEMP_IMPO",):
            for mcf in keywords[key]:
                _addGroup(mcf, nodeGroups, ("GROUP_NO", "SANS_GROUP_NO"))
                _addGroup(mcf, cellGroups, ("GROUP_MA", "SANS_GROUP_MA"))
                _excludeGroup(mcf, ("NOEUD", "MAILLE"))
        elif key in ("LIAISON_DDL",):
            for mcf in keywords[key]:
                _addGroup(mcf, nodeGroups, ("GROUP_NO",))
                _excludeGroup(mcf, ("NOEUD",))
        elif key in ("LIAISON_GROUP"):
            for mcf in keywords[key]:
                _addGroup(mcf, nodeGroups, ("GROUP_NO_1", "GROUP_NO_2", "SANS_GROUP_NO"))
                _addGroup(mcf, cellGroups, ("GROUP_MA_1", "GROUP_MA_2"))
                _excludeGroup(mcf, ("NOEUD_1", "NOEUD_2", "SANS_NOEUD", "MAILLE_1"))
        elif key in ("LIAISON_MAIL",):
            for mcf in keywords[key]:
                _addGroup(mcf, nodeGroups, ("GROUP_NO_ESCL",))
                _addGroup(mcf, cellGroups, ("GROUP_MA_MAIT", "GROUP_MA_ESCL"))
        elif key in ("LIAISON_UNIF",):
            for mcf in keywords[key]:
                _addGroup(mcf, nodeGroups, ("GROUP_NO",))
                _addGroup(mcf, cellGroups, ("GROUP_MA",))
                _excludeGroup(mcf, ("NOEUD", "MAILLE"))
        elif key in load_types:
            raise NotImplementedError(
                "Type of load {0!r} not yet " "implemented in parallel".format(key)
            )
    # must be sorted to be identical on all procs
    return sorted(list(nodeGroups)), sorted(list(cellGroups))
