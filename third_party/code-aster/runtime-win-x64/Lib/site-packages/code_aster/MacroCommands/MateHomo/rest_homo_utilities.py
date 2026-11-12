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
from libaster import Physics, Modelings
from ...Objects import (
    Mesh,
    Model,
    Function,
    ThermalResultDict,
    ElasticResultDict,
    ThermalResult,
    ElasticResult,
    SimpleFieldOnNodesReal,
)
from ...CodeCommands import DEFI_CONSTANTE
from ...Messages import ASSERT, UTMESS
from ...Utilities import SearchList, no_new_attributes
from .rest_homo_proj import MOCK_PROJ_CHAMP
from .syme_homo_corr import BuildFullSymmetryMassif
from .mate_homo_utilities import get_temp_def_alpha_material as get_tda
from .mate_homo_mesh import check_meshpara
from . import HomoType


class RelocManager:
    """
    Main class to manage relocalisation tasks
    """

    _x0 = _y0 = _z0 = _shift = None
    _elas_dict = _ther_dict = _full = None
    _temp_ref = _temp_ref_field = _pres_int = None
    _crit = _prec = None
    _subinsts = _meshver = _meshp0 = _fevol_tp0 = None
    __setattr__ = no_new_attributes(object.__setattr__)

    @property
    def shift(self):
        """Holds the global coordinates shift of the VER mesh (x,y,z)."""

        arr = [0.0, 0.0, 0.0]
        if self._shift:
            arr = [self._x0, self._y0, self._z0]
        return arr

    @property
    def p0(self):
        """Holds the global coordinates of the point P0 (x,y,z)."""

        return [self._x0, self._y0, self._z0]

    @property
    def pres_int(self):
        """Holds the internal pressure function."""

        return self._pres_int

    @property
    def temp_ref(self):
        """Holds the reference temperature value."""

        return self._temp_ref

    @property
    def temp_ref_field(self):
        """Holds the constant field at reference temperature value."""
        if self._temp_ref_field is None:
            constfield = SimpleFieldOnNodesReal(self.ver_mesh, "TEMP_R", ["TEMP"], True)
            values, mask = constfield.toNumpy()
            mask[:, :] = True
            values[:, :] = self._temp_ref
            self._temp_ref_field = constfield.toFieldOnNodes()
        return self._temp_ref_field

    @property
    def corr_meca(self):
        """Holds the elastic corrector results."""

        return self._elas_dict

    @property
    def corr_ther(self):
        """Holds the thermal corrector results."""

        return self._ther_dict

    @property
    def ver_mesh(self):
        """Holds the VER mesh."""

        if self._meshver is None:
            self._createVerMesh()
        return self._meshver

    @property
    def mesh_p0(self):
        """Holds the point P0 mesh."""

        if self._meshp0 is None:
            self._meshp0 = Mesh.buildPointCloud([self.p0], info=0)
        return self._meshp0

    @property
    def type_homo(self):
        """Holds the homogenisation type."""

        htype = HomoType.Bulk
        if any("FLEX" in name for name in self.corr_meca.keys()):
            ASSERT(self.corr_ther is None)
            htype = HomoType.Plate

        return htype

    @property
    def evalTP0(self):
        """Holds the P0 temperature evolution function."""

        ASSERT(self._fevol_tp0 is not None)
        return self._fevol_tp0

    @property
    def precision(self):
        """Holds the search precision."""

        return self._prec

    @property
    def criterion(self):
        """Holds the search criterion."""

        return self._crit

    @property
    def subinsts(self):
        """Holds the reduced list of times."""

        return self._subinsts

    def __init__(self, kwargs):
        """
        Init function.

        Args:
            kwargs (dict) : Arguments dict from aster catalogue.
        """

        self._x0, self._y0, self._z0 = kwargs.get("POSITION")
        self._shift = kwargs.get("TRANSLATION") == "OUI"

        self._elas_dict = kwargs.get("CORR_MECA", {})
        self._ther_dict = kwargs.get("CORR_THER", {})
        self._setup_pression(kwargs.get("PRESSION"))
        self._setup_temp_ref(kwargs.get("AFFE"))
        self._crit = kwargs.get("CRITERE")
        self._prec = kwargs.get("PRECISION")
        self._subinsts = kwargs.get("INST")
        self._meshver = None
        self._meshp0 = None
        self._fevol_tp0 = None
        self._temp_ref_field = None
        self._full = False
        if kwargs.get("COMPLET") == "OUI":
            self._make_full_correctors()

    def _setup_pression(self, p):
        """
        Sets the internal pressure function.

        If `p` is None, a default constant pressure of 0.0 is used.
        """

        if p is None:
            self._pres_int = DEFI_CONSTANTE(VALE=0.0)
        else:
            if p.getProperties()[2] not in ("INST", "TOUTPARA"):
                UTMESS("F", "HOMO1_20")
            self._pres_int = p

    def _setup_temp_ref(self, affe):
        """
        Sets the reference temperature (TEMP_DEF_ALPHA) from given materials.
        """

        stda = set()
        for item in affe:
            mater = item["MATER"]
            tda_current = get_tda(mater)
            stda.add(tda_current)

        ltda = list(stda)
        if len(ltda) > 1:
            UTMESS("F", "HOMO1_14", valk=("TEMP_DEF_ALPHA",))

        self._temp_ref = ltda[0]

    def _make_full_correctors(self):
        """
        Build the full field of correctors.

        CALC_MATE_HOMO computes the corrector fields on a symmetric and periodic mesh.
        When performing relocalisation it is possible to build the full corrector field.

        """
        assert not self._full
        astermesh = None
        mod_ther = None
        mod_elas = None

        elas = self._elas_dict
        if elas is not None:
            corr_meca = ElasticResultDict()
            for name in elas.keys():
                corr_sym = elas[name]
                medcresu = corr_sym.createMedCouplingResult(prefix=f"{name}")
                resuout = BuildFullSymmetryMassif(medcresu)
                if astermesh is None:
                    astermesh = Mesh()
                    astermesh.buildFromMedCouplingMesh(resuout.getMeshes()[0])

                if mod_elas is None:
                    mod_elas = Model(astermesh)
                    mod_elas.addModelingOnMesh(Physics.Mechanics, Modelings.Tridimensional)
                    mod_elas.build()

                corr_meca[name] = ElasticResult.fromMedCouplingResult(resuout, astermesh)
                corr_meca[name].setModel(mod_elas)

            self._elas_dict = corr_meca

        ther = self._ther_dict
        if ther is not None:
            corr_ther = ThermalResultDict()
            for name in ther.keys():
                corr_sym = ther[name]
                medcresu = corr_sym.createMedCouplingResult(prefix=f"{name}")
                resuout = BuildFullSymmetryMassif(medcresu)
                if astermesh is None:
                    astermesh = Mesh()
                    astermesh.buildFromMedCouplingMesh(resuout.getMeshes()[0])

                if mod_ther is None:
                    mod_ther = Model(astermesh)
                    mod_ther.addModelingOnMesh(Physics.Thermal, Modelings.Tridimensional)
                    mod_ther.build()

                corr_ther[name] = ThermalResult.fromMedCouplingResult(resuout, astermesh)
                corr_ther[name].setModel(mod_ther)

            self._ther_dict = corr_ther

        self._full = True

    def getCorrectorMesh(self):
        """Assert that VER mesh is unique and get it from correctors.

        Returns
        -------
            mesh (Mesh) : The VER mesh.
        """
        mmeca = None
        mther = None
        mesh = None

        if self.corr_meca:
            mmeca = list(set(self.corr_meca[key].getMesh() for key in self.corr_meca.keys()))
            ASSERT(len(mmeca) == 1)
            mesh = mmeca[0]

        if self.corr_ther:
            mther = list(set(self.corr_ther[key].getMesh() for key in self.corr_ther.keys()))
            ASSERT(len(mther) == 1)
            mesh = mther[0]

        if mmeca is not None and mther is not None:
            ASSERT(mther[0] is mmeca[0])

        return check_meshpara(mesh)

    def _createVerMesh(self):
        """Internal function. Creates the VER mesh used for field localisation.

        When used to build the local result, VER mesh must be on the cartesian origin.
        This function checks this condition and if successul creates a new mesh shifted.

        Returns
        -------
            mesh (Mesh) : The VER mesh for field localisation.
        """
        ASSERT(self._meshver is None)
        mcmesh = self.getCorrectorMesh().createMedCouplingMesh()
        mcmesh.getCoords()[:] += self.shift

        self._meshver = Mesh()
        self._meshver.buildFromMedCouplingMesh(mcmesh, verbose=0)

    def setConstantTP0Function(self):
        """Set a constant temperature as evolution function for point P0.

        Temperature is set at the reference value.
        """
        self.setEvolTP0Function([1.0], [self.temp_ref], ext=True)

    def getReducedIndexes(self, resu):
        """Get the reduced list of storage indexes from a result.

        The reduced list of time is eventually given by user.
        If present, returns the associated list of storage indexes
        Otherwise returns the full list of NUME_ORDRE

        Args:
            resu (ElasticResult | ThermalResult): Result datastructure

        Returns:
            idx (list[int]): List of storage indexes.

        """
        acpara = resu.getAccessParameters()
        ASSERT("INST" in acpara)
        ASSERT("NUME_ORDRE" in acpara)

        if self.subinsts is None:
            idx = acpara["NUME_ORDRE"]
        else:
            slist = SearchList(acpara["INST"], self.precision, self.criterion)
            idx = [acpara["NUME_ORDRE"][slist.index(i)] for i in self.subinsts]
        return idx

    def setEvolTP0Function(self, x, y, ext=False):
        """Set the temperature evolution function for point P0.

        Temperature values are given as function of time.
        They are then used as access variable (pseudo-time) to interpolate the corrector fields.

        Args:
            x (list[float]): Time values.
            y (list[float]): Temperature values.
            ext (bool): True to set linear extrapolation out of time bounds (default : False)

        """

        ASSERT(self._fevol_tp0 is None)
        evol = Function()
        evol.setParameterName("INST")
        evol.setInterpolation("LIN LIN")
        if ext:
            evol.setExtrapolation("CC")
        else:
            evol.setExtrapolation("EE")
        evol.setValues(x, y)

        self._fevol_tp0 = evol

    def getOneArrayCorrector(self, name, value):
        """Return the corrector field values as numpy ndarray.

        Result is interpolated at the specified parameter value.
        The parameter is temperature, which is used as pseudo-time.

        Args:
            name (str): The corrector field name (e.g. CORR_MECA11).
            value (float): Temperature value for field interpolation.

        Returns:
            array (np.ndarray): The corrector field values.

        """
        ASSERT(self.corr_meca is not None)
        resu = self.corr_meca.get(name)
        var = "DEPL"

        if resu is None:
            ASSERT(self.corr_ther is not None)
            resu = self.corr_ther.get(name)
            var = "TEMP"

        ASSERT(resu is not None)

        sfield = resu.interpolateField(
            var, value, crit=self.criterion, prec=self.precision
        ).toSimpleFieldOnNodes()
        array, mask = sfield.getValues(copy=True)
        ASSERT(mask.all())
        return array

    def getElasticBulkArrays(self, value):
        """Return the elastic bulk corrector field values as list of ndarrays.

        Result is interpolated at the specified parameter value.
        The parameter is temperature, which is used as pseudo-time.

        Args:
            value (float): Value of temperature for interpolation.

        Returns:
            arrays (list[np.ndarray]): List of corrector fields values.
        """

        ASSERT(self.type_homo == HomoType.Bulk)
        ASSERT(self.corr_meca is not None)

        chi_11 = self.getOneArrayCorrector("CORR_MECA11", value)
        chi_22 = self.getOneArrayCorrector("CORR_MECA22", value)
        chi_33 = self.getOneArrayCorrector("CORR_MECA33", value)
        chi_12 = self.getOneArrayCorrector("CORR_MECA12", value)
        chi_23 = self.getOneArrayCorrector("CORR_MECA23", value)
        chi_31 = self.getOneArrayCorrector("CORR_MECA31", value)
        chi_di = self.getOneArrayCorrector("CORR_DILA", value)

        if "CORR_PINT" in self.corr_meca.keys():
            chi_pi = self.getOneArrayCorrector("CORR_PINT", value)
        else:
            chi_pi = np.zeros(shape=chi_di.shape)

        arrays = (chi_11, chi_22, chi_33, chi_12, chi_23, chi_31, chi_di, chi_pi)

        return arrays

    def getThermalBulkArrays(self, value):
        """Return the thermal bulk corrector field values as list of ndarrays.

        Result is interpolated at the specified parameter value.
        The parameter is temperature, which is used as pseudo-time.

        Args:
            value (float): Value of temperature for interpolation.

        Returns:
            arrays (list[np.ndarray]): List of corrector fields values.
        """

        ASSERT(self.type_homo == HomoType.Bulk)
        ASSERT(self.corr_ther is not None)

        chi_1 = self.getOneArrayCorrector("CORR_THER11", value)
        chi_2 = self.getOneArrayCorrector("CORR_THER22", value)
        chi_3 = self.getOneArrayCorrector("CORR_THER33", value)
        arrays = (chi_1, chi_2, chi_3)

        return arrays

    def getP0ElasGlobalEvol(self, resu):
        """Extract the evolution of the elastic global solution at point P0.

        The global solution is the result of a computation using homogeneus parameters.
        Return arrays are intented to be function of time.

        Args:
            resu (ElasticResult): The global solution.

        Returns:
            dp0 (dict): Displacement of point P0 (DEPL).
            epsip0 (dict): Strain of point P0 (EPSI_NOEU).

        """

        ASSERT(isinstance(resu, ElasticResult))

        for name in ("DEPL", "EPSI_NOEU"):
            if name not in resu.getFieldsNames():
                UTMESS("F", "HOMO1_6", valk=(name, resu.getName()))

        resu_p0 = MOCK_PROJ_CHAMP(
            RESULTAT=resu,
            METHODE="COLLOCATION",
            MAILLAGE_1=resu.getMesh(),
            MAILLAGE_2=self.mesh_p0,
            NOM_CHAM=("DEPL", "EPSI_NOEU"),
            TYPE_CHAM="NOEU",
        )

        dp0 = {}
        epsip0 = {}
        nordre = resu.getAccessParameters()["NUME_ORDRE"]

        for n in nordre:
            dp0[n] = np.array(resu_p0.getField("DEPL", n).getValues())

            epxx0, epyy0, epzz0, epxy0, epxz0, epyz0 = resu_p0.getField("EPSI_NOEU", n).getValues()

            epsip0[n] = np.array(
                [[epxx0, epxy0, epxz0], [epxy0, epyy0, epyz0], [epxz0, epyz0, epzz0]]
            )

        return dp0, epsip0

    def getP0TherGlobalEvol(self, resu):
        """Extract the evolution of the thermal global solution at point P0.

        The global solution is the result of a computation using homogeneus parameters.
        Return arrays are intented to be function of time.

        Args:
            resu (ThermalResult): The global solution.

        Returns:
            tp0 (dict): Temperature of point P0 (TEMP).
            gratp0 (dict): Temperature gradient of point P0 (GRAT_NOEU).

        """
        ASSERT(isinstance(resu, ThermalResult))

        for name in ("TEMP", "GRAT_NOEU"):
            if name not in resu.getFieldsNames():
                UTMESS("F", "HOMO1_6", valk=(name, resu.getName()))

        resu_p0 = MOCK_PROJ_CHAMP(
            RESULTAT=resu,
            METHODE="COLLOCATION",
            MAILLAGE_1=resu.getMesh(),
            MAILLAGE_2=self.mesh_p0,
            NOM_CHAM=("TEMP", "GRAT_NOEU"),
            TYPE_CHAM="NOEU",
        )

        tp0 = {}
        gratp0 = {}
        nordre = resu.getAccessParameters()["NUME_ORDRE"]

        for n in nordre:
            tp0[n] = resu_p0.getField("TEMP", n).getValues()[0]

            grtxx0, grtyy0, grtzz0 = resu_p0.getField("GRAT_NOEU", n).getValues()
            gratp0[n] = np.array([grtxx0, grtyy0, grtzz0])

        # Set the temperature evolution function
        insts = resu.getAccessParameters()["INST"]
        self.setEvolTP0Function(insts, [tp0[n] for n in nordre])

        return tp0, gratp0
