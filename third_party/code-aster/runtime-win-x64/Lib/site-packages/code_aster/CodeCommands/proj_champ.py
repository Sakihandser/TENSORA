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


from ..Cata.SyntaxUtils import mixedcopy
from ..Messages import UTMESS
from ..Objects import (
    ConnectionMesh,
    FieldOnCellsReal,
    FullResult,
    MeshesMapping,
    ParallelMesh,
    SimpleFieldOnNodesReal,
)
from ..Supervis import ExecuteCommand, loop_on_dsdict
from ..Utilities import force_list


def _addGroup(mcf, groups, keys):
    for name in keys:
        mc = mcf.get(name)
        if mc:
            groups.update(force_list(mc))


def _excludeGroup(mcf, keys):
    for name in keys:
        if mcf.get(name):
            raise RuntimeError("Keyword %s not accepted in parallel AFFE_CHAR_MECA" % name)


def _getGroups(keywords):
    """for parallel load, return all node and cells groups present in AFFE_CHAR_MECA, in order to define the connection mesh"""
    nodeGroups = set()
    cellGroups = set()
    for key in list(keywords.keys()):
        if key in ("VIS_A_VIS",):
            for mcf in keywords[key]:
                _addGroup(mcf, nodeGroups, ("GROUP_NO_1", "GROUP_NO_2"))
                _addGroup(mcf, cellGroups, ("GROUP_MA_1", "GROUP_MA_2"))
                _excludeGroup(mcf, ("NOEUD", "SANS_NOEUD", "MAILLE"))
    # must be sorted to be identical on all procs
    return sorted(list(nodeGroups)), sorted(list(cellGroups))


@loop_on_dsdict("RESULTAT")
class FieldProjector(ExecuteCommand):
    """Command that allows to project fields."""

    command_name = "PROJ_CHAMP"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        method = keywords.get("METHODE")
        resultat = keywords.get("RESULTAT")
        chamGd = keywords.get("CHAM_GD")
        if resultat is None and chamGd is None:
            self._result = MeshesMapping()
            return
        if resultat:
            self._result = type(keywords["RESULTAT"])()
            return
        if chamGd and method == "SOUS_POINT":
            self._result = FieldOnCellsReal()
            return
        self._result = type(chamGd)()

    def exec_legacy(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        method = keywords.get("METHODE")
        if keywords.get("RESULTAT") and method == "ECLA_PG":
            kwargs = mixedcopy(keywords)
            # check arguments
            try:
                result_in = kwargs.pop("RESULTAT")
                names = force_list(kwargs.pop("NOM_CHAM"))
                assert kwargs["PROJECTION"] == "OUI"
                kwargs["MODELE_2"]  # must exist for ECLA_PG
            except (AssertionError, KeyError):
                UTMESS("F", "CALCULEL5_9")
            result_out = self.result
            params = result_in.getAccessParameters()
            indexes = result_in.getIndexesFromKeywords(params, keywords)
            result_out.allocate(len(indexes))
            result_out.setModel(kwargs["MODELE_2"])
            # reduce verbosity: kwargs["INFO"] = 0 !

            # Determine if RESULTAT contains FREQ or INST
            para = "INST" if "INST" in params else "FREQ"

            # Filter the keywords that are specific to RESULTAT
            supported_kw_result = (
                "TOUT_ORDRE",
                "NUME_ORDRE",
                "LIST_ORDRE",
                "INST",
                "FREQ",
                "LIST_INST",
                "LIST_FREQ",
            )
            for kw in supported_kw_result:
                kwargs.pop(kw, None)

            # Create a dictionnary with ALARME="NON" to call PROJ_CHAMP with
            #   after the first iteration
            kwargs_no_alarm = dict(kwargs)
            kwargs_no_alarm["ALARME"] = "NON"

            for n_idx, (idx, value) in enumerate(zip(indexes, params[para])):
                for field_name in names:
                    try:
                        field = result_in.getField(field_name, idx)
                    except KeyError:
                        continue
                    kwargs_to_use = kwargs if n_idx == 0 else kwargs_no_alarm
                    field_out = PROJ_CHAMP(CHAM_GD=field, **kwargs_to_use)
                    result_out.setField(field_out, field_name, idx)

                result_out.setParameterValue(para, value, idx)
        else:
            super().exec_(keywords)

    def exec_(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        hpc = keywords.get("DISTRIBUTION") == "OUI"
        if not hpc:
            self.exec_legacy(keywords)
        else:
            if "CHAM_GD" in keywords:
                maillage_1 = keywords.pop("MAILLAGE_1")
                maillage_2 = keywords.pop("MAILLAGE_2")
                nodeGroups, cellGroups = _getGroups(keywords)
                if type(maillage_1) is ParallelMesh:
                    connectionMesh_1 = ConnectionMesh(maillage_1, nodeGroups, cellGroups)
                    pField_1 = keywords.pop("CHAM_GD")
                    connectField_1 = pField_1.transfertToConnectionMesh(connectionMesh_1)
                else:
                    connectionMesh_1 = maillage_1
                if type(maillage_2) is ParallelMesh:
                    connectionMesh_2 = ConnectionMesh(maillage_2, nodeGroups, cellGroups)
                else:
                    connectionMesh_2 = maillage_2

                keywords["MAILLAGE_1"] = connectionMesh_1
                keywords["MAILLAGE_2"] = connectionMesh_2
                keywords["CHAM_GD"] = connectField_1
                keywords.pop("DISTRIBUTION")

                resu = PROJ_CHAMP(**keywords)

                keywords.pop("MAILLAGE_1")
                keywords.pop("MAILLAGE_2")
                keywords.pop("CHAM_GD")
                keywords["MAILLAGE_1"] = maillage_1
                keywords["MAILLAGE_2"] = maillage_2
                keywords["CHAM_GD"] = pField_1
                keywords["DISTRIBUTION"] = "OUI"

                self._result = resu.transferFromConnectionToParallelMesh(maillage_2)

            elif keywords["PROJECTION"] == "NON":
                maillage_1 = keywords.pop("MAILLAGE_1")
                maillage_2 = keywords.pop("MAILLAGE_2")
                nodeGroups, cellGroups = _getGroups(keywords)
                if type(maillage_1) is ParallelMesh:
                    connectionMesh_1 = ConnectionMesh(maillage_1, nodeGroups, cellGroups)
                else:
                    connectionMesh_1 = maillage_1
                if type(maillage_2) is ParallelMesh:
                    if maillage_1 == maillage_2:
                        connectionMesh_2 = connectionMesh_1
                    else:
                        connectionMesh_2 = ConnectionMesh(maillage_2, nodeGroups, cellGroups)
                else:
                    connectionMesh_2 = maillage_2

                keywords["MAILLAGE_1"] = connectionMesh_1
                keywords["MAILLAGE_2"] = connectionMesh_2
                keywords.pop("DISTRIBUTION")

                resu = PROJ_CHAMP(**keywords)

                keywords["DISTRIBUTION"] = "OUI"
                self._result = resu

            else:
                UTMESS("F", "ALGORITH7_76")

    def post_exec(self, keywords):
        """Execute the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        if self.exception:
            return
        dofNum = keywords.get("NUME_DDL")
        if dofNum is not None:
            if isinstance(self._result, FullResult):
                self._result.setDOFNumbering(dofNum)
            else:
                self._result.addEquationNumbering(dofNum.getEquationNumbering())

        if "RESULTAT" in keywords:
            if "MODELE_2" in keywords:
                self._result.setModel(keywords["MODELE_2"])
            elif "MAILLAGE_2" in keywords:
                self._result.setMesh(keywords["MAILLAGE_2"])
            elif "MATR_PROJECTION" in keywords:
                self._result.setMesh(keywords["MATR_PROJECTION"].getSecondMesh())
            else:
                self._result.setMesh(keywords["RESULTAT"].getMesh())
            self._result.build()
        elif "CHAM_GD" in keywords:
            if self._result.getType().startswith("CHAM_EL"):
                if "MODELE_2" in keywords:
                    self._result.setDescription(keywords["MODELE_2"].getFiniteElementDescriptor())
                self._result.build()
            else:
                if "MODELE_2" in keywords:
                    mesh = keywords["MODELE_2"].getMesh()
                elif "MAILLAGE_2" in keywords:
                    mesh = keywords["MAILLAGE_2"]
                elif "MATR_PROJECTION" in keywords:
                    mesh = keywords["MATR_PROJECTION"].getSecondMesh()
                else:
                    mesh = None
                if isinstance(self._result, SimpleFieldOnNodesReal):
                    self._result.build()
                else:
                    self._result.build(mesh)
        else:
            if "MAILLAGE_1" in keywords:
                self._result.setFirstMesh(keywords["MAILLAGE_1"])
            if "MAILLAGE_2" in keywords:
                self._result.setSecondMesh(keywords["MAILLAGE_2"])
            if "MODELE_1" in keywords:
                self._result.setFirstMesh(keywords["MODELE_1"].getMesh())
            if "MODELE_2" in keywords:
                self._result.setSecondMesh(keywords["MODELE_2"].getMesh())

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Arguments:
            keywords (dict): User's keywords.
        """
        super().add_dependencies(keywords)
        self.remove_dependencies(keywords, "RESULTAT")
        self.remove_dependencies(keywords, "CHAM_GD")
        self.remove_dependencies(keywords, "CHAM_NO_REFE")
        self.remove_dependencies(keywords, "MATR_PROJECTION")


PROJ_CHAMP = FieldProjector.run
