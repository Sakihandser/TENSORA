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
from ..Objects import (
    ConnectionMesh,
    CouplingMethod,
    CouplingPairing,
    CouplingZonePairing,
    MechanicalLoadReal,
    Model,
    PairingAlgo,
    PairingMethod,
    PairingParameter,
    ParallelMechanicalLoadReal,
    SyntaxSaver,
)
from ..Supervis import ExecuteCommand
from ..Utilities import deprecate, force_list


class MechanicalLoadDefinition(ExecuteCommand):
    """Command that defines :class:`~code_aster.Objects.MechanicalLoadReal`."""

    command_name = "AFFE_CHAR_MECA"
    neumannLoads = [
        "PESANTEUR",
        "ROTATION",
        "FORCE_FACE",
        "FORCE_ARETE",
        "FORCE_CONTOUR",
        "FORCE_INTERNE",
        "PRE_SIGM",
        "PRES_REP",
        "EFFE_FOND",
        "PRE_EPSI",
        "FORCE_POUTRE",
        "FORCE_TUYAU",
        "FORCE_COQUE",
        "FORCE_ELEC",
        "INTE_ELEC",
        "VITE_FACE",
        "ONDE_FLUI",
        "ONDE_PLANE",
        "FLUX_THM_REP",
        "FORCE_SOL",
        "FORCE_NODALE",
        "EVOL_CHAR",
        "VECT_ASSE",
    ]
    dirichletLoads = [
        "DDL_IMPO",
        "DDL_POUTRE",
        "FACE_IMPO",
        "CHAMNO_IMPO",
        "ARETE_IMPO",
        "LIAISON_DDL",
        "LIAISON_OBLIQUE",
        "LIAISON_GROUP",
        "LIAISON_MAIL",
        "LIAISON_PROJ",
        "LIAISON_CYCL",
        "LIAISON_SOLIDE",
        "LIAISON_ELEM",
        "LIAISON_UNIF",
        "LIAISON_CHAMNO",
        "LIAISON_RBE3",
        "LIAISON_INTERF",
        "LIAISON_COQUE",
        "RELA_CINE_BP",
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
    def _hasOnlyDDL_IMPO(cls, keywords):
        """No need to create ConnectionMesh for DDL_IMPO"""
        for key in cls.dirichletLoads:
            mc = keywords.get(key)
            if mc and key != "DDL_IMPO":
                return False
        # Not enabled for the moment
        return False
        # return True

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        model = keywords["MODELE"]
        l_neum = self._hasNeumannLoadings(keywords)
        l_diri = self._hasDirichletLoadings(keywords)
        if not model.getMesh().isParallel():
            self._result = MechanicalLoadReal(model)
        else:
            if l_neum:
                if l_diri:
                    raise TypeError(
                        "Not allowed to mix up Dirichlet and Neumann \
                        loadings in the same parallel AFFE_CHAR_MECA"
                    )
                else:
                    self._result = MechanicalLoadReal(model)
            if "LIAISON_MASSIF" in keywords.keys():
                if l_neum or l_diri:
                    raise TypeError(
                        "LIAISON_MASSIF has to be the only \
                                            loading in the same parallel AFFE_CHAR_MECA"
                    )
            if self._hasOnlyDDL_IMPO(keywords):
                self._result = MechanicalLoadReal(model)

    def exec_(self, keywords):
        """Override default _exec in case of parallel load"""
        if isinstance(self._result, MechanicalLoadReal):
            super(MechanicalLoadDefinition, self).exec_(keywords)

            if "LIAISON_MASSIF" in keywords.keys():
                assert len(keywords["LIAISON_MASSIF"]) == 1
                _cpl_method = {
                    "LAGRANGIEN": CouplingMethod.Lagrangian,
                    "PENALISATION": CouplingMethod.Penalization,
                    "NITSCHE": CouplingMethod.Nitsche,
                }
                _pair_method = {
                    "RAPIDE": PairingMethod.Fast,
                    "FORCEBRUTE": PairingMethod.BrutForce,
                    "PANG": PairingMethod.Legacy,
                }

                _algo_pair = {"MORTAR": PairingAlgo.Mortar}

                cpl = CouplingPairing(keywords["MODELE"], keywords["INFO"])
                for item in keywords["LIAISON_MASSIF"]:
                    zone = CouplingZonePairing(keywords["MODELE"].getMesh(), keywords["INFO"])
                    zone.setCoefficient(item["COEF_PENA"])
                    zone.setMethod(_cpl_method[item["METHODE"]])
                    zone.setSlaveGroupsOfCells(item["GROUP_MA_ESCL"])
                    zone.setMasterGroupsOfCells(item["GROUP_MA_MAIT"])

                    # pairing parameters
                    pairParam = PairingParameter()
                    pairParam.setAlgorithm(_algo_pair[item["APPARIEMENT"]])

                    if item["APPARIEMENT"] == "MORTAR":
                        pairParam.setPairingTolerance(item["APPA_TOLE"])
                        pairParam.setAreaIntersectionTolerance(item["AIRE_TOLE"])
                        pairParam.setPairingMethod(_pair_method[item["TYPE_APPA"]])

                    zone.setPairingParameters(pairParam)
                    zone.build()

                    if keywords["VERI_NORM"] == "OUI":
                        zone.check(keywords["MODELE"])

                    cpl.addZone(zone)
                cpl.compute()
                self._result.setPairingData(cpl.getData())
        else:
            model = keywords.pop("MODELE")
            if "LIAISON_PROJ" in list(keywords.keys()):
                matr_proj = keywords["LIAISON_PROJ"][0]["MATR_PROJECTION"]
                connectionMesh = matr_proj.getSecondMesh()
                for key in list(keywords.keys()):
                    if key in (
                        "LIAISON_DDL",
                        "DDL_IMPO",
                        "LIAISON_OBLIQUE",
                        "LIAISON_UNIF",
                        "LIAISON_SOLIDE",
                        "DDL_POUTRE",
                        "FACE_IMPO",
                        "ARETE_IMPO",
                        "LIAISON_RBE3",
                        "LIAISON_MAIL",
                        "LIAISON_MASSIF",
                        "LIAISON_GROUP",
                        "LIAISON_COQUE",
                        "LIAISON_ELEM",
                    ):
                        raise NameError("LIAISON_PROJ in HPC must be alone in AFFE_CHAR_MECA")
            else:
                nodeGroups, cellGroups = _getGroups(self._cata, keywords)
                connectionMesh = ConnectionMesh(model.getMesh(), nodeGroups, cellGroups)

            connectionModel = Model(connectionMesh)
            connectionModel.setFrom(model)

            keywords["MODELE"] = connectionModel
            partialMechanicalLoad = AFFE_CHAR_MECA(**keywords)
            keywords["MODELE"] = model
            self._result = ParallelMechanicalLoadReal(partialMechanicalLoad, model)
            if keywords.get("SYNTAXE") == "OUI":
                toSave = SyntaxSaver(self.command_name, 7, keywords)
                self._result.setRebuildParameters(toSave, nodeGroups, cellGroups)

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


AFFE_CHAR_MECA = MechanicalLoadDefinition.run


def _addGroup(mcf, groups, keys):
    for name in keys:
        mc = mcf.get(name)
        if mc:
            groups.update(force_list(mc))


def _excludeGroup(mcf, keys):
    for name in keys:
        if mcf.get(name):
            raise RuntimeError("Keyword %s not accepted in parallel AFFE_CHAR_MECA" % name)


def _getGroups(cata, keywords):
    """for parallel load, return all node and cells groups present in AFFE_CHAR_MECA, in order to define the connection mesh"""
    load_types = [
        key for key in list(cata.keywords.keys()) if isinstance(cata.keywords[key], FactorKeyword)
    ]
    nodeGroups = set()
    cellGroups = set()
    for key in list(keywords.keys()):
        if key in (
            "LIAISON_DDL",
            "DDL_IMPO",
            "LIAISON_OBLIQUE",
            "LIAISON_UNIF",
            "LIAISON_SOLIDE",
            "DDL_POUTRE",
            "FACE_IMPO",
            "ARETE_IMPO",
        ):
            for mcf in keywords[key]:
                _addGroup(mcf, nodeGroups, ("GROUP_NO", "SANS_GROUP_NO"))
                _addGroup(mcf, cellGroups, ("GROUP_MA", "SANS_GROUP_MA"))
                _excludeGroup(mcf, ("NOEUD", "SANS_NOEUD", "MAILLE"))
        elif key in ("LIAISON_GROUP", "LIAISON_COQUE", "LIAISON_ELEM"):
            for mcf in keywords[key]:
                _addGroup(mcf, nodeGroups, ("GROUP_NO_1", "GROUP_NO_2", "SANS_GROUP_NO"))
                _addGroup(mcf, cellGroups, ("GROUP_MA_1", "GROUP_MA_2"))
                _excludeGroup(mcf, ("NOEUD_1", "NOEUD_2", "SANS_NOEUD"))
        elif key in ("LIAISON_RBE3", "LIAISON_MAIL", "LIAISON_MASSIF"):
            for mcf in keywords[key]:
                _addGroup(mcf, nodeGroups, ("GROUP_NO_MAIT", "GROUP_NO_ESCL"))
                _addGroup(mcf, cellGroups, ("GROUP_MA_MAIT", "GROUP_MA_ESCL"))
        elif key in ("LIAISON_PROJ",):
            pass
        elif key in load_types:
            raise NotImplementedError(
                "Type of load {0!r} not yet " "implemented in parallel".format(key)
            )
    # must be sorted to be identical on all procs
    return sorted(list(nodeGroups)), sorted(list(cellGroups))
