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


from ..Helpers import adapt_for_mgis_behaviour
from ..Objects import (
    ElasticFourierResult,
    ElasticResult,
    ExternalStateVariablesResult,
    FieldOnCellsComplex,
    FieldOnCellsLong,
    FieldOnCellsReal,
    FieldOnNodesChar8,
    FieldOnNodesComplex,
    FieldOnNodesReal,
    FullHarmonicResult,
    FullTransientResult,
    LoadResult,
    ModeResult,
    ModeResultComplex,
    MultipleElasticResult,
    NonLinearResult,
    ThermalResult,
    DryingResult,
)
from ..Supervis import ExecuteCommand
from ..Utilities import force_list


class ResultCreator(ExecuteCommand):
    """Command that creates evolutive results."""

    command_name = "CREA_RESU"
    # Change the content of the COMPORTEMENT keyword.
    adapt_syntax = adapt_for_mgis_behaviour

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        if "reuse" in keywords:
            self._result = keywords["reuse"]
        else:
            typ = keywords["TYPE_RESU"]
            if typ == "EVOL_CHAR":
                self._result = LoadResult()
            elif typ == "EVOL_THER":
                self._result = ThermalResult()
            elif typ == "EVOL_SECH":
                self._result = DryingResult()
            elif typ == "EVOL_NOLI":
                self._result = NonLinearResult()
            elif typ == "EVOL_ELAS":
                self._result = ElasticResult()
            elif typ == "EVOL_VARC":
                self._result = ExternalStateVariablesResult()
            elif typ == "FOURIER_ELAS":
                self._result = ElasticFourierResult()
            elif typ == "FOURIER_THER":
                self._result = ElasticFourierResult()
            elif typ == "MULT_ELAS":
                self._result = MultipleElasticResult()
            elif typ == "MODE_MECA":
                self._result = ModeResult()
            elif typ == "MODE_MECA_C":
                self._result = ModeResultComplex()
            elif typ == "DYNA_TRANS":
                self._result = FullTransientResult()
            elif typ == "DYNA_HARMO":
                self._result = FullHarmonicResult()
            else:
                raise NotImplementedError("Type of result {0!r} not yet " "implemented".format(typ))

    def post_exec(self, keywords):
        """Hook called after the execution of the command.

        Arguments:
            keywords (dict): User's keywords.
        """
        result = self._result
        get_ = keywords.get

        new_model = None
        new_mater = None
        new_elemcara = None
        new_mesh = None
        for kw in (
            "AFFE",
            "ASSE",
            "PERM_CHAM",
            "PROL_RTZ",
            "PREP_VARC",
            "KUCV",
            "CONV_CHAR",
            "CONV_RESU",
        ):
            if kw in keywords:
                fkw = force_list(keywords[kw])

        if "ASSE" in keywords:
            src = fkw[0]["RESULTAT"]
            new_mesh = src.getMesh()
            new_model = src.getModel()
            new_mater = src.getMaterialField()
            new_elemcara = src.getElementaryCharacteristics()

        # Model, MaterialField... can not change between occurrences,
        # the first found is used.
        if not new_model:
            new_model = [occ["MODELE"] for occ in fkw if occ.get("MODELE")]
            new_model = new_model and new_model[0]
        if not new_mater:
            new_mater = [occ["CHAM_MATER"] for occ in fkw if occ.get("CHAM_MATER")]
            new_mater = new_mater and new_mater[0]
        if not new_elemcara:
            new_elemcara = [occ["CARA_ELEM"] for occ in fkw if occ.get("CARA_ELEM")]
            new_elemcara = new_elemcara and new_elemcara[0]

        matr = get_("MATR_RIGI", get_("MATR_MASS"))
        if matr:
            result.setDOFNumbering(matr.getDOFNumbering())
            if not new_model:
                new_model = matr.getDOFNumbering().getModel()
        if not new_model and get_("ECLA_PG"):
            new_model = keywords["ECLA_PG"]["MODELE_INIT"]
        if not new_model and get_("CONV_CHAR"):
            matr_rigi = keywords["CONV_CHAR"]["MATR_RIGI"]
            new_model = matr_rigi.getDOFNumbering().getModel()
        if not new_model and get_("CONV_RESU"):
            new_model = keywords["CONV_RESU"]["RESU_INIT"].getModel()
        if not new_model and get_("KUCV"):
            new_model = keywords["KUCV"]["RESU_INIT"].getModel()

        if new_mesh:
            result.setMesh(new_mesh)
        if new_model:
            result.setModel(new_model, exists_ok=True)
        elif "reuse" not in keywords:
            # not reuse, at least set the mesh support from AFFE/CHAM_GD or PROL_RTZ
            if get_("PROL_RTZ"):
                result.setMesh(keywords["PROL_RTZ"]["MAILLAGE_FINAL"])
            elif fkw[0].get("CHAM_GD"):
                mesh = fkw[0]["CHAM_GD"].getMesh()
                result.setMesh(mesh)
        if new_elemcara:
            result.setElementaryCharacteristics(new_elemcara, exists_ok=True)
        if new_mater:
            result.setMaterialField(new_mater, exists_ok=True)

        # find ligrel and nume_equa
        feds = []
        fnds = []
        for occ in fkw:
            chamGd = occ["CHAM_GD"]
            if isinstance(chamGd, (FieldOnNodesReal, FieldOnNodesComplex, FieldOnNodesChar8)):
                fnd = chamGd.getDescription()
                if fnd is not None:
                    fnds.append(fnd)
            elif isinstance(chamGd, (FieldOnCellsReal, FieldOnCellsComplex, FieldOnCellsLong)):
                fed = chamGd.getDescription()
                if fed is not None:
                    feds.append(fed)

        if get_("CONV_CHAR"):
            matr_rigi = keywords["CONV_CHAR"]["MATR_RIGI"]
            dofNum = matr_rigi.getDOFNumbering()
            if dofNum:
                if keywords["TYPE_RESU"] == "DYNA_TRANS":
                    result.setDOFNumbering(dofNum)
                else:
                    fnds.append(dofNum.getEquationNumbering())
        if get_("CONV_RESU"):
            matr_rigi = keywords["CONV_RESU"].get("MATR_RIGI")
            if matr_rigi is not None:
                dofNum = matr_rigi.getDOFNumbering()
            else:
                dofNum = keywords["CONV_RESU"]["NUME_DDL"]
            if dofNum:
                if keywords["TYPE_RESU"] == "DYNA_TRANS":
                    result.setDOFNumbering(dofNum)
                else:
                    fnds.append(dofNum.getEquationNumbering())
        if get_("KUCV"):
            dofNum = keywords["KUCV"]["MATR_AMOR"].getDOFNumbering()
            if dofNum:
                fnds.append(dofNum.getEquationNumbering())

        self._result.build(feds, fnds)

    def add_dependencies(self, keywords):
        """Register input *DataStructure* objects as dependencies.

        Arguments:
            keywords (dict): User's keywords.
        """
        super().add_dependencies(keywords)
        self.remove_dependencies(keywords, "AFFE", "CHAM_GD")
        self.remove_dependencies(keywords, "ASSE", "RESULTAT")
        self.remove_dependencies(keywords, "ECLA_PG", "RESU_INIT")
        if keywords["OPERATION"] == "PERM_CHAM":
            self.remove_dependencies(keywords, "RESU_INIT")
            self.remove_dependencies(keywords, "RESU_FINAL")
        self.remove_dependencies(keywords, "PROL_RTZ", "TABLE")
        self.remove_dependencies(keywords, "PREP_VARC", ("CHAM_GD", "ELAS_THER"))
        self.remove_dependencies(keywords, "KUCV", "RESU_INIT")
        self.remove_dependencies(keywords, "CONV_RESU", "RESU_INIT")


CREA_RESU = ResultCreator.run
