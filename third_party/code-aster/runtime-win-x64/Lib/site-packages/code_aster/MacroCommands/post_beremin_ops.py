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
"""
Compute:
  - Weibull stress
  - Weibull stress**m
  - Probability of failure

  - Strain model -> Stress to consider (6 components: XX, YY, ZZ, XY, XZ, YZ)
      - "PETIT"      -> "SIEF"
      - "PETIT_REAC" -> "SIEF"
      - "GDEF_LOG"   -> "VARI_ELGA"

Integral must be computed on the initial configuration

_biblio : CR-T66-2017-132, Lorentz
"""
from math import exp
import os
import numpy as np
import tempfile

from ..Cata.Syntax import _F
from ..CodeCommands import (
    CALC_CHAM_ELEM,
    CALC_CHAMP,
    CREA_TABLE,
    CALC_TABLE,
    DEFI_FICHIER,
    DEFI_CONSTANTE,
)
from ..CodeCommands import IMPR_RESU
from ..Objects import FieldOnCellsReal, NonLinearResult, Table, Model, Function, FieldOnNodesReal
from ..Utilities import logger, disable_fpe, no_new_attributes
from ..MedUtils.MedConverter import field_converter
from ..Utilities import medcoupling as medc
from ..Messages import UTMESS
from ..Helpers.LogicalUnit import LogicalUnitFile

from .Fracture.post_beremin_utils import CellToPoints, create_mesh_from_groupno


DEBUG = bool(os.environ.get("DEBUG_POST_BEREMIN", ""))


class PostBeremin:
    """
    Beremin post-processor

    Arguments:
        resultat (NonLinearResult): Mechanical code_aster result
        group_ma (str): Mesh cells group on which Beremin post-treatment
            is carried out
            Only 1 mesh cells group authorized
        deformation (str): "PETIT", "PETIT_REAC", "GDEF_LOG"
        filtre_sigm (str): "SIGM_ELGA" or "SIGM_ELMOY".
        coef_mult (float): As explained in doc aster u4.81.22 (weibull) p.15

    Returns:
        Table:

            - Weibull stress
            - Weibull stress**m
            - Failure probability

    if SIGM_MAXI in command file, MED file containing:

        - where the plasticity is active : maximum of major principal
          stress
        - where the plasticity is not active : 0
          Result of type ELGA (apply ElgaFieldToSurface filter in
          Paraview to see it)
    """

    # data 2D and 3D
    _result = _zone = _zone_ids = _stress_option = _strain_type = None
    _intvar_idx = _stress_idx = None
    _use_hist = _use_indiplas = _use_FO = _use_function = _use_cham = None
    _use_sigm_corr = None
    _type_seuil = None
    _corr_resu = None
    _coef_mult = None
    _weib_params = None
    _params_dependancy = None
    # data 2D only
    _method_2D = _prec_proj = _model_2D = None
    _groupno = None
    _l_proj_3D_2D = _fondfiss = _dictfondfiss = None
    _l_mesh_proj_2D = _l_name_mesh_2D = _l_mesh_group_no_2D = None
    _l_mesh_proj_2D_mc = _mesh_3D_cells_mc = _d_max_3d = None
    _model_3D_zone = None
    _medfilename_temp = _unite_temp = None
    _rout_2D = None

    # result to compute weibull stress
    _reswb = _rsieq = _rout = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, result: NonLinearResult, strain_type: str, stress_option: str) -> None:
        """Initialization and definition of main arguments.

        Args:
            result (*Result*): Result object of the calculation.
            strain_type (str): Type of strain.
            stress_option (str): Type of stress to be used or calculated.
        """
        self._result = result
        assert stress_option in (
            "SIGM_ELGA",
            "SIGM_ELMOY",
            "SIGM_CORR",
        ), f"unknown value: {stress_option}"
        self._stress_option = stress_option
        self._strain_type = strain_type

    def set_zone(self, group: str) -> None:
        """Define the location where the calculation will be done.

        Args:
            group (str): Mesh group of cells to be used.
        """
        self._zone = group
        list_grou_ma = [x[0] for x in self._result.getMesh().LIST_GROUP_MA()]
        if group not in list_grou_ma:
            UTMESS("F", "RUPTURE4_28", valk=group)
        self._zone_ids = self._result.getMesh().getCells(group)

    def set_projection_parameters(self, args):
        """Define projection parameters when METHODE_2D is used.

        Args:
            args (dict): Keywords for POST_BEREMIN.
        """
        if "METHODE_2D" in args:
            self._method_2D = True
            self._prec_proj = args["METHODE_2D"]["PRECISION"]
            self._l_mesh_proj_2D = args["METHODE_2D"]["MAILLAGE_PLAN"]
            self._l_name_mesh_2D = args["METHODE_2D"]["NOM_MAIL_MED"]
            self._l_mesh_group_no_2D = args["METHODE_2D"]["GROUP_NO_PLAN"]
            self._fondfiss = args["METHODE_2D"]["FISSURE"]
            self._model_2D = args["METHODE_2D"]["MODELISATION"]
            self._l_mesh_proj_2D_mc = []

            ##Model restricted to zone
            fed_all = self._result.getModel().getFiniteElementDescriptor()
            fed_restricted = fed_all.restrict(self._zone_ids)
            self._model_3D_zone = Model("model_3D_zone", fed_restricted)

            if args["METHODE_2D"]["UNITE_RESU"] != 0:
                self._rout_2D = args["METHODE_2D"]["UNITE_RESU"]

            ##Type of 2D mesh input ?
            if self._l_mesh_group_no_2D:
                self._l_mesh_proj_2D = [None] * len(self._l_mesh_group_no_2D)
                self._l_name_mesh_2D = [x for x in self._l_mesh_group_no_2D]
                ##Check if group_no exists
                list_group_no = [x[0] for x in self._result.getMesh().LIST_GROUP_NO()]
                for group_no in self._l_mesh_group_no_2D:
                    if group_no not in list_group_no:
                        UTMESS("F", "RUPTURE4_29", valk=group_no)
                ##Set fond fiss info
                self.set_fondfiss_info()
                self._groupno = True
            else:
                self._l_mesh_group_no_2D = [None] * len(self._l_mesh_proj_2D)

                if (self._l_mesh_proj_2D and not self._l_name_mesh_2D) or (
                    not self._l_mesh_proj_2D and self._l_name_mesh_2D
                ):
                    UTMESS("F", "RUPTURE4_17")

                for mesh_2d in self._l_mesh_proj_2D:
                    if (mesh_2d.isQuadratic() and not self._result.getMesh().isQuadratic()) or (
                        not mesh_2d.isQuadratic() and self._result.getMesh().isQuadratic()
                    ):
                        UTMESS("F", "RUPTURE4_20")

            if self._stress_option != "SIGM_ELMOY":
                UTMESS("F", "RUPTURE4_21")

            if self._rout_2D and len(self._l_mesh_proj_2D) != 1:
                UTMESS("F", "RUPTURE4_19")

    def set_indexes(self, intvar_idx: list = None, stress_idx: list = None) -> None:
        """Define the indexes used to extract the relevant components depending
        of the behaviour.

        Args:
            intvar_idx (list[int], optional): Indexes to access to
                INDIPLAS internal variable.
            stress_idx (list[int], optional): Indexes to extract log stresses
                tensor components.
        """
        if intvar_idx:
            if intvar_idx > 0:
                self._use_indiplas = True
                self._intvar_idx = intvar_idx
            else:
                self._use_indiplas = False
        if stress_idx:
            if len(stress_idx) not in [4, 6]:
                UTMESS("F", "RUPTURE4_18")
            self._stress_idx = stress_idx

    def set_fondfiss_info(self):
        """Define fondfiss information (X Y Z ABSCURV ABSCURVNORM) for table output METHODE_2D"""

        ##If no fondfiss input
        if self._fondfiss is None:
            if len(self._l_mesh_group_no_2D) == 1:
                self._dictfondfiss = {}
                self._dictfondfiss[self._l_name_mesh_2D[0]] = [0.0] * 5
            else:
                UTMESS("F", "RUPTURE4_30")
        else:
            frontnodes = self._fondfiss.getCrackFrontNodes()
            frontnodes = [int(x) - 1 for x in frontnodes]
            frontpos = self._fondfiss.getCrackFrontPosition()
            frontabscurv = self._fondfiss.getCrackFrontAbsCurv()
            abscurvmax = max(frontabscurv)

            self._dictfondfiss = {}
            for group_no, nom_group_no in zip(self._l_mesh_group_no_2D, self._l_name_mesh_2D):
                nodes = self._result.getMesh().getNodes(group_no, localNumbering=True)
                both = set(frontnodes).intersection(nodes)
                both = list(both)
                indexfrontnode = frontnodes.index(both[0])
                pos = frontpos[3 * indexfrontnode : 3 * (indexfrontnode + 1)]
                abscurv = frontabscurv[indexfrontnode]
                # X Y Z ABSCURV ABSCURVNORM
                self._dictfondfiss[nom_group_no] = pos + [abscurv, abscurv / abscurvmax]

    def use_history(self, value: bool) -> None:
        """Enable the use of history or just the current timestep.

        Args:
            value (bool): *True* to use the history since the beginning,
              or *False* to use values on the current timestep.
        """
        self._use_hist = value

    def use_sigm_corr(self, args) -> None:
        """Enable the use of a corrected stress (e.g. with plastic correction).

        Args:
            args (dict): Keywords for POST_BEREMIN.
        """
        self._use_sigm_corr = False
        if "SIGM_CORR" in args:
            self._use_sigm_corr = True
            self._corr_resu = args["SIGM_CORR"]

    def set_coef_mult(self, value: float = 1.0) -> None:
        """Define the multiplicative factor to take symmetric into account.

        Args:
            value (float): Multiplicative factor (see documentation).
        """
        self._coef_mult = value

    def set_weibull_parameters(self, params):
        """Define Weibull parameters.

        Args:
            params (dict): Weibull or Weibull_FO parameters keywords for POST_BEREMIN.
        """

        self._weib_params = params.copy()
        self._type_seuil = params["TYPE_SEUIL"]
        assert self._type_seuil in ["RESTREINT", "REDUIT"]

        if self._use_FO:

            ##Set default values for SIGM_REFE and SIGM_SEUIL
            if params["SIGM_REFE"] is None:
                self._weib_params["SIGM_REFE"] = [DEFI_CONSTANTE(VALE=1.0)]
            else:
                self._weib_params["SIGM_REFE"] = [params["SIGM_REFE"]]
            if params["SIGM_SEUIL"] is None:
                self._weib_params["SIGM_SEUIL"] = [DEFI_CONSTANTE(VALE=0.0)]
            else:
                self._weib_params["SIGM_SEUIL"] = [params["SIGM_SEUIL"]]

            self._use_function = {"SIGM_REFE": False, "SIGM_SEUIL": False}
            self._use_cham = {"SIGM_REFE": False, "SIGM_SEUIL": False}
            for param in ["SIGM_REFE", "SIGM_SEUIL"]:
                if params[param] is None or type(params[param]) is Function:
                    self._use_function[param] = True
                    if type(params[param]) is Function:
                        assert params[param].Parametres()["NOM_PARA"] in [
                            "TEMP",
                            "X",
                            "Y",
                            "Z",
                            "TOUTPARA",
                        ]
                elif type(params[param]) in [FieldOnNodesReal, FieldOnCellsReal]:
                    if "X1" not in params[param].getComponents():
                        UTMESS("F", "RUPTURE4_24", valk=param)
                    self._use_cham[param] = True
                else:
                    assert False
            assert sum(self._use_function.values()) + sum(self._use_cham.values()) in [0, 2]
            if (
                self._use_function["SIGM_SEUIL"] or self._use_cham["SIGM_SEUIL"]
            ) and self._type_seuil == "RESTREINT":
                UTMESS("F", "RUPTURE4_27", valk=param)

        if self._rout:
            for param in ["SIGM_REFE", "M", "SIGM_SEUIL"]:
                if len(self._weib_params[param]) not in [0, 1]:
                    UTMESS("F", "RUPTURE4_19")

    def setup_calc_result(self):
        """Setup the result object to be used to compute the Beremin stress."""
        if self._strain_type == "GDEF_LOG":
            result = self._result
            indexes = result.getIndexes()
            # store VARI_ELGA + log stresses (from VARI_ELGA) as SIEF_ELGA
            dim = result.getMesh().getDimension()
            varn = [f"V{i}" for i in self._stress_idx]
            cmps = ("SIXX", "SIYY", "SIZZ", "SIXY", "SIXZ", "SIYZ")
            if dim == 2:
                cmps = ("SIXX", "SIYY", "SIZZ", "SIXY")
            dconv = dict(zip(varn, cmps))

            rvga = result
            rvga.userName = "rvga____"

            for idx in indexes:
                chvari = result.getField("VARI_ELGA", idx)
                rvga.setField(chvari.asPhysicalQuantity("SIEF_R", dconv), "SIEF_ELGA", idx)
            self._reswb = rvga
        else:
            self._reswb = self._result

    def get_internal_variables(self, idx):
        """Return internal variables.

        Args:
            idx (int): storage index.

        Returns:
            tuple: *ComponentOnCells* objects for INDIPLAS.
        """
        v1 = f"V{self._intvar_idx}"
        chvari = self._result.getField("VARI_ELGA", idx)
        chvari = chvari.toSimpleFieldOnCells()
        indip = chvari.getComponentOnCells(v1)

        return indip

    def get_major_stress(self, idx):
        """Return the major principal stress.

        Args:
            idx (int): storage index.

        Returns:
            *ComponentOnCells*: Major principal stress.
        """
        if not self._rsieq:
            self._rsieq = self.compute_sieq()
        sieq = self._rsieq.getField("SIEQ_ELGA", idx)
        sieq = sieq.toSimpleFieldOnCells()
        return sieq.PRIN_3

    def get_corrected_major_stress(self, idx):
        """Return the major principal stress corrected with a user-defined plastic correction.

        Args:
            idx (int): storage index.

        Returns:
            *ComponentOnCells*: Corrected major principal stress.
        """
        if "UT01_ELGA" not in self._corr_resu.getFieldsNames():
            UTMESS("F", "RUPTURE4_25")
        corr_sig1 = self._corr_resu.getField("UT01_ELGA", idx + 1)
        corr_sig1 = corr_sig1.toSimpleFieldOnCells()
        if "X1" not in corr_sig1.getComponents():
            UTMESS("F", "RUPTURE4_25")
        try:
            corr_sig1.X1.restrict(self._zone_ids)
        except:
            UTMESS("F", "RUPTURE4_26")
        return corr_sig1.X1

    def compute_sieq(self):
        """Compute SIEQ_ELGA stress."""
        # compute fields on all timesteps, add INST/NUME_ORDRE to be limited
        input = self._reswb

        d_group_ma = {}
        if not self._rout or self._method_2D:
            d_group_ma["GROUP_MA"] = self._zone

        if self._stress_option == "SIGM_ELMOY":
            input = CALC_CHAMP(RESULTAT=self._reswb, CONTRAINTE="SIMY_ELGA", **d_group_ma)
            for idx in input.getIndexes():
                simy = input.getField("SIMY_ELGA", idx)
                input.setField(simy, "SIEF_ELGA", idx)

        rsieq = CALC_CHAMP(RESULTAT=input, CRITERES="SIEQ_ELGA", **d_group_ma)

        if self._method_2D and not self._medfilename_temp:
            self._medfilename_temp = tempfile.NamedTemporaryFile(dir=".", suffix=".med").name
            self._unite_temp = DEFI_FICHIER(
                FICHIER=self._medfilename_temp, ACTION="ASSOCIER", TYPE="LIBRE", ACCES="NEW"
            )
            IMPR_RESU(
                UNITE=self._unite_temp,
                PROC0="NON",
                RESU=_F(
                    RESULTAT=rsieq,
                    NOM_CHAM="SIEQ_ELGA",
                    NOM_CMP="PRIN_3",
                    NOM_CHAM_MED="TMP",
                    NUME_ORDRE=1,
                ),
            )
            DEFI_FICHIER(ACTION="LIBERER", UNITE=self._unite_temp)

        if DEBUG:
            for i in rsieq.getIndexes():
                print("NEW: rsieq:", i, np.sum(rsieq.getField("SIEQ_ELGA", i).getValues()))

        return rsieq

    def apply_stress_correction(self, sig1, idx, sigma_thr, sigma_refe):
        """Compute the major principal stress, eventually apply SIGM_CNV/SIGM_REFE
        correction and threshold by SIGM_SEUIL.

        *The values are changed in place.*

        Args:
            sig1 (*ComponentOnCells*): PRIN_3 component of SIEQ_ELGA, changed in place.
            idx (int): Timestep index
            cells_ids (list[int]): Cells list.
            sigma_thr (float): Stress threshold
            sigma_refe (float): sigm_refe parameter
        """

        sigma_mater = {"SIGM_REFE": sigma_refe, "SIGM_SEUIL": sigma_thr}
        sigmat = {}
        temp = None
        val_zone_inte = 0.0

        if self._use_function is not None and sig1.size > 0:
            for param in ["SIGM_REFE", "SIGM_SEUIL"]:
                if self._use_function[param]:
                    if temp is None:
                        temp = self.get_temperature_field(idx)
                    sigmat[param] = temp.apply(sigma_mater[param])
                    sigmat[param].restrict(self._zone_ids)
                if self._use_cham[param]:
                    sigmat[param] = self.build_consistant_field(idx, sigma_mater[param], sig1)
            if self._use_function["SIGM_SEUIL"] or self._use_cham["SIGM_SEUIL"]:
                assert self._type_seuil != "RESTREINT"
            assert abs(sigmat["SIGM_REFE"]).min() > 0.0
            sig1 /= sigmat["SIGM_REFE"]
            if self._weib_params["SIGM_CNV"] > 0.0:
                sig1 *= self._weib_params["SIGM_CNV"]
            sig1 -= sigmat["SIGM_SEUIL"]

        else:
            # apply stress threshold
            if sigma_thr > 0.0:
                if self._type_seuil == "REDUIT":
                    sig1 -= sigma_thr
                if self._type_seuil == "RESTREINT":
                    val_zone_inte = sigma_thr

        def sig_filter(array):
            return np.where(array < val_zone_inte, 0.0, array)

        sig1 = sig1.apply(sig_filter)

        return sig1

    def apply_threshold(self, sig1, indiplas):
        """Apply plastic strain threshold onto major stress.

        NB: *ComponentOnCells* changed in place.

        Args:
            sig1 (*ComponentOnCells*): Major stress.
            indiplas (*ComponentOnCells*): Plastic indicator.
        """
        indip = indiplas.onSupportOf(sig1)

        # * (1 if indip != 0 else 0)
        def toint_sign(array):
            return np.sign(np.array(array, dtype=int))

        indip = indip.apply(toint_sign)
        sig1 *= indip

        return sig1

    def get_temperature_field(self, idx):
        """Return the temperature field.

        Args:
            idx (idx): storage index.

        Returns:
            *ComponentOnCells*: Temperature values.
        """
        varc_elga = CALC_CHAMP(
            RESULTAT=self._result, VARI_INTERNE="VARC_ELGA", NUME_ORDRE=idx, GROUP_MA=self._zone
        )
        varc_elga = varc_elga.getField("VARC_ELGA", idx)
        varc_elga = varc_elga.toSimpleFieldOnCells()

        return varc_elga.TEMP

    def build_consistant_field(self, idx, cham_in, sig1):
        """Build a component field from a field on Nodes / Cells, make its support consistent
        with the component field of major principal stress for further math operations.

        Args:
            idx (int): Timestep index
            cham_in (*FieldOnNodesReal* or *FieldOnCellsReal*): Field of material property (SIGM_REFE or SIGM_SEUIL).
        """

        if type(cham_in) is not FieldOnCellsReal:
            model = self._result.getModel(idx)
            desc = model.getFiniteElementDescriptor()
            cham_in = cham_in.toFieldOnCells(desc, "ELGA")
        cham_out = cham_in.toSimpleFieldOnCells()
        cham_out = cham_out.getComponentOnCells("X1")
        cham_out.restrict(self._zone_ids)
        cham_out = cham_out.onSupportOf(sig1)

        return cham_out

    def compute_intsig1_3D(self, sig1, weight):
        """Compute the values to be added into the result table.

        Args:
            sig1 (*ComponentOnCells*): Major stress ^ M.
            weight (*ComponentOnCells*): Weight of each integration point,
                **changed in place**.

        Returns:
            intsig1pm: integral of major stress ^ M.
        """
        if DEBUG:
            print("NEW: sigpm:", sig1.sum())

        weight = weight.onSupportOf(sig1)
        integ = sig1 * weight
        intsig1pm = integ.sum()

        return intsig1pm

    def build_projector(self, mesh_3D, mesh_2D, group_no_2D):
        """Return the 3D -> 2D projector when METHODE_2D is used

        Args:
            mesh_3D (*Mesh*): Mesh 3D object from result
            mesh_2D (*Mesh*): 2D mesh of plane (if already created, else None)
            group_no_2D (*grno*): Group of nodes to create mesh_2D

        Returns:
            *CellToPoints*: 3D -> 2D projector
        """

        ##Get 3D mesh (gauss to cells)
        if self._mesh_3D_cells_mc is None:
            timeStamps = medc.GetAllFieldIterations(self._medfilename_temp, "TMP")
            filefield_tmp = medc.MEDFileFieldMultiTS.New(self._medfilename_temp, "TMP")
            f_on_gauss = filefield_tmp.getFieldAtLevel(
                medc.ON_GAUSS_PT, timeStamps[-1][0], timeStamps[-1][1], 0
            )
            self._d_max_3d = (
                f_on_gauss.getMesh().computeDiameterField().getArray().getMaxValueInArray()
            )
            with disable_fpe():
                f_on_cells = f_on_gauss.voronoize(1e-12)
            self._mesh_3D_cells_mc = f_on_cells.getMesh()
            if self._mesh_3D_cells_mc.getMeshDimension() != 3:
                UTMESS("F", "RUPTURE4_14")

        ##Get 2D mesh
        if mesh_2D:
            mesh_2D_mc = mesh_2D.createMedCouplingMesh(spacedim_3d=True)[0]
        elif group_no_2D:
            mesh_2D_mc = create_mesh_from_groupno(mesh_3D, group_no_2D)
        self._l_mesh_proj_2D_mc += [mesh_2D_mc]
        if mesh_2D_mc.getMeshDimension() != 2:
            UTMESS("F", "RUPTURE4_15")

        ##Build projector 3D -> points (points = barycenters of 2D mesh gauss cells)
        proj_3D_2D = CellToPoints(
            self._mesh_3D_cells_mc, mesh_2D_mc, self._prec_proj, self._d_max_3d
        )

        return proj_3D_2D

    def convert_to_mc(self, sig1):
        """Convert major stress to medcoupling.

        Args:
            sig1 (*ComponentOnCells*): Major stress 3D

        Returns:
            sigma_a_mc: Major stress 3D (medcoupling array)
        """

        ##3D ComponentOnCells to 3D medcoupling array
        sigma = FieldOnCellsReal(self._model_3D_zone, "ELGA", "SIEF_R")
        sigma.setValues(0.0)
        sigma_sfield = sigma.toSimpleFieldOnCells()
        sixx = sigma_sfield.SIXX
        sixx.restrict(self._zone_ids)
        sixx += sig1
        sigma_sfield.setComponentValues("SIXX", sixx)
        sigma_f_mc, prof = field_converter.toMCFieldAndProfileElem(
            sigma_sfield, self._mesh_3D_cells_mc, "SIEF_ELGA"
        )
        sigma_a_mc = sigma_f_mc.getArray()[:, 0]

        return sigma_a_mc

    def compute_intsig1_2D(self, mc_sig1, pow_m, idx, time, mesh_2D_idx):
        """Projection of sig1 from 3D cells to barycenter of 2D cells
        and computation of 2D integral

        Args:
            mc_sig1 (*medcoupling array*): Major stress 3D
            pow_m (float): current M coefficient
            idx (int): Storage index.
            time (float): Time value.
            mesh_2D_idx(int): Index of current 2D plane mesh

        Returns:
            intsig1pm: integral of major stress ^ M on current 2D plane.
        """

        ##Projection 3D -> points
        sigma_2D_a_mc = self._l_proj_3D_2D[mesh_2D_idx].Eval(mc_sig1)
        sigma_2D_a_mc.setName("SIYY")

        ##Create 2D medcoupling field for integral
        sigma_2D_f_mc = medc.MEDCouplingFieldDouble(medc.ON_CELLS, medc.ONE_TIME)
        if len(sigma_2D_a_mc) == self._l_mesh_proj_2D_mc[mesh_2D_idx].getNumberOfCells():
            sigma_2D_f_mc.setMesh(self._l_mesh_proj_2D_mc[mesh_2D_idx])
        else:
            UTMESS("F", "RUPTURE4_16")
        sigma_2D_f_mc.setTime(time, idx, 0)
        sigma_2D_f_mc.setArray(sigma_2D_a_mc)
        sigma_2D_f_mc.setNature(medc.IntensiveConservation)
        sigma_2D_f_mc.setName("SIEF_ELMOY")
        sigma_2D_f_mc.checkConsistencyLight()

        ##Compute integral
        intsig1pm = sigma_2D_f_mc.integral(0, True)

        ##Output .med
        if self._rout_2D:
            sigma_2D_np = sigma_2D_a_mc.toNumPyArray().reshape((len(sigma_2D_a_mc), 1))
            sigma_2D_np_out = np.concatenate((sigma_2D_np, sigma_2D_np ** (1 / pow_m)), 1)
            sigma_2D_a_mc_out = medc.DataArrayDouble(sigma_2D_np_out)
            sigma_2D_a_mc_out.setInfoOnComponents(["SIXX", "SIYY"])
            sigma_2D_f_mc_out = medc.MEDCouplingFieldDouble(medc.ON_CELLS, medc.ONE_TIME)
            sigma_2D_f_mc_out.setMesh(self._l_mesh_proj_2D_mc[mesh_2D_idx])
            sigma_2D_f_mc_out.setTime(time, idx, 0)
            sigma_2D_f_mc_out.setArray(sigma_2D_a_mc_out)
            sigma_2D_f_mc_out.setNature(medc.IntensiveConservation)
            sigma_2D_f_mc_out.setName("SIEF_ELMOY")
            sigma_2D_f_mc_out.checkConsistencyLight()

            filename = LogicalUnitFile.filename_from_unit(self._rout_2D)
            medc.WriteField(filename, sigma_2D_f_mc_out, True if idx == 0 else False)

        return intsig1pm

    def compute_table_values(self, intsig1pm, pow_m, sigma_refe):
        """Compute the values to be added into the result table.

        Args:
            intsig1pm (float): integral of major stress ^ M.
            pow_m (float): M weibull parameter
            sigma_refe (float): sigm_refe parameter

        Returns:
            tuple: Values for each column.
        """
        coef_volu = self._coef_mult / self._weib_params["VOLU_REFE"]
        inv_m = 1 / pow_m
        sigma_u = self._weib_params["SIGM_CNV"] if self._use_function else sigma_refe

        # intfin(INTE_SIXX) = (COEF_MULT/VOLU_REFE*INTE_SIXX)**(1/bere_m)
        sigma_weibull = (coef_volu * intsig1pm) ** inv_m

        # sigwm(SIGMA_WEIBULL) = SIGMA_WEIBULL**bere_m
        sigma_weibullpm = sigma_weibull**pow_m

        # probaw(SIGMA_WEIBULL) = 1-exp(-SIGMA_WEIBULL**bere_m/sigma_u**bere_m)
        #  avec sigma_u=SIMG_CNV ou SIGM_REFE
        if sigma_u > 0.0:
            proba_weibull = 1.0 - exp(-((sigma_weibull / sigma_u) ** pow_m))
        else:
            proba_weibull = 0.0

        return sigma_weibull, sigma_weibullpm, proba_weibull

    def store_sigm_maxi_3D(self, idx, time, sig1, model, pow_m):
        """Store the major stress ^M into the output result.

        Args:
            idx (int): Storage index.
            time (float): Time value.
            sig1 (*ComponentOnCells*): Major stress ^ M.
            model (*Model*): Model object.
            cells_ids (list[int]): Cells list.
        """
        if not self._rout or self._method_2D:
            return
        if idx == 0:
            self._rout.allocate(self._rsieq.getNumberOfIndexes())
        sigmax = FieldOnCellsReal(model, "ELGA", "SIEF_R")
        sigmax.setValues(0.0)
        sfield = sigmax.toSimpleFieldOnCells()
        ##Major stress ^ M
        sixx = sfield.SIXX
        sixx.restrict(self._zone_ids)
        sixx += sig1
        sfield.setComponentValues("SIXX", sixx.expand())
        ##Major stress
        siyy = sfield.SIYY
        siyy.restrict(self._zone_ids)
        siyy = sig1 ** (1 / pow_m)
        sfield.setComponentValues("SIYY", siyy.expand())
        fed = model.getFiniteElementDescriptor()
        sigmax = sfield.toFieldOnCells(fed, "RAPH_MECA", "PCONTPR")
        self._rout.setField(sigmax, "SIEF_ELGA", idx)
        self._rout.setModel(model, idx)
        self._rout.setTime(time, idx)

    def main(self):
        """Compute Weibull stress and failure probability."""
        result = self._reswb
        model = result.getModel()
        mesh = model.getMesh()
        params = result.getAccessParameters()
        logger.info("extracting integration scheme...")
        coor_elga = CALC_CHAM_ELEM(MODELE=model, OPTION="COOR_ELGA")
        coor_elga = coor_elga.toSimpleFieldOnCells()

        logger.info("starting computation...")

        table = TableBeremin(self._use_function, self._groupno)

        param_mater = [
            [sigma_thr, sigma_refe, pow_m]
            for sigma_thr in self._weib_params["SIGM_SEUIL"]
            for sigma_refe in self._weib_params["SIGM_REFE"]
            for pow_m in self._weib_params["M"]
        ]

        for sigma_thr, sigma_refe, pow_m in param_mater:
            logger.info(
                "M = "
                + str(pow_m)
                + "; SIGM_SEUIL = "
                + str(sigma_thr)
                + "; SIGM_REFE = "
                + str(sigma_refe)
                + " ..."
            )

            id_store = 0
            previous = None

            for idx, time in zip(params["NUME_ORDRE"], params["INST"]):
                if self._use_indiplas:
                    indip = self.get_internal_variables(idx)

                if self._use_sigm_corr:
                    sig1 = self.get_corrected_major_stress(idx)
                else:
                    sig1 = self.get_major_stress(idx)
                    sig1.restrict(self._zone_ids)

                if self._use_indiplas:
                    sig1 = self.apply_threshold(sig1, indip)

                sig1 = self.apply_stress_correction(sig1, idx, sigma_thr, sigma_refe)

                if self._use_hist:
                    if previous is None:
                        previous = sig1.copy()
                    else:
                        sig1.maximum(previous)
                        previous = sig1.copy()

                if DEBUG:
                    print("NEW: sigmax:", id_store, idx, sig1.sum())

                sig1 **= pow_m

                ##SIGMAW 3D
                if not self._method_2D:
                    intsig1pm = self.compute_intsig1_3D(sig1, coor_elga.W)
                    self.store_sigm_maxi_3D(id_store, time, sig1, model, pow_m)

                    strwb, strwb_pm, proba = self.compute_table_values(intsig1pm, pow_m, sigma_refe)

                    table.append(
                        id_store,
                        time,
                        self._zone,
                        pow_m,
                        sigma_refe if not self._use_function else "FONCTION",
                        sigma_thr if not self._use_function else "FONCTION",
                        strwb,
                        strwb_pm,
                        proba,
                    )

                ##SIGMAW 2D
                else:
                    ##Projectors are built only one time
                    if not self._l_proj_3D_2D:
                        self._l_proj_3D_2D = []
                        for mesh_2D, nom_mesh, group_no_2D in zip(
                            self._l_mesh_proj_2D, self._l_name_mesh_2D, self._l_mesh_group_no_2D
                        ):
                            logger.info(
                                "Construction du projecteur pour le maillage 2D " + str(nom_mesh)
                            )
                            self._l_proj_3D_2D += [self.build_projector(mesh, mesh_2D, group_no_2D)]

                    mc_sig1 = self.convert_to_mc(sig1)

                    ##Compute SW2D for every plane
                    for mesh_2D_idx, mesh_2D_name in enumerate(self._l_name_mesh_2D):
                        intsig1pm = self.compute_intsig1_2D(mc_sig1, pow_m, idx, time, mesh_2D_idx)
                        strwb, strwb_pm, proba = self.compute_table_values(
                            intsig1pm, pow_m, sigma_refe
                        )

                        if not self._groupno:
                            table.append(
                                id_store,
                                time,
                                mesh_2D_name,
                                pow_m,
                                sigma_refe if not self._use_function else "FONCTION",
                                sigma_thr if not self._use_function else "FONCTION",
                                strwb,
                                strwb_pm,
                                proba,
                            )
                        else:
                            table.append(
                                id_store,
                                time,
                                mesh_2D_name,
                                self._dictfondfiss[mesh_2D_name][0],
                                self._dictfondfiss[mesh_2D_name][1],
                                self._dictfondfiss[mesh_2D_name][2],
                                self._dictfondfiss[mesh_2D_name][3],
                                self._dictfondfiss[mesh_2D_name][4],
                                pow_m,
                                sigma_refe if not self._use_function else "FONCTION",
                                sigma_thr if not self._use_function else "FONCTION",
                                strwb,
                                strwb_pm,
                                proba,
                            )

                id_store += 1

        return table


def post_beremin_ops(self, RESULTAT, DEFORMATION, FILTRE_SIGM, **args):
    """Main of POST_BEREMIN command."""

    l_use_FO = False
    if "WEIBULL" in args:
        fkw_weib = args.get("WEIBULL")
    if "WEIBULL_FO" in args:
        fkw_weib = args.get("WEIBULL_FO")
        l_use_FO = True

    assert not (
        ("METHODE_2D" in args) and (len(fkw_weib) > 1)
    ), "Only one occurrence of WEIBULL / WEIBULL_FO is allowed when METHODE_2D is used."

    sdtable0 = TableBeremin(False, False)
    sdtable_ = []
    fkw_comb = []

    for iocc, occ in enumerate(fkw_weib):
        post = PostBeremin(result=RESULTAT, strain_type=DEFORMATION, stress_option=FILTRE_SIGM)
        post.set_zone(occ["GROUP_MA"])
        post._use_FO = l_use_FO
        post.set_indexes(intvar_idx=args["NUME_VARI"])
        if DEFORMATION == "GDEF_LOG":
            post.set_indexes(stress_idx=args["LIST_NUME_SIEF"])
        post.use_history(args["HIST_MAXI"] == "OUI")
        post.use_sigm_corr(args)
        post.set_coef_mult(args["COEF_MULT"])
        post.set_projection_parameters(args)

        if args.get("SIGM_MAXI"):
            post._rout = NonLinearResult()
            self.register_result(post._rout, args["SIGM_MAXI"])

        post.set_weibull_parameters(occ)
        post.setup_calc_result()

        table = post.main()
        sdtable_.append(table.create_table())
        fkw_comb.append(_F(OPERATION="COMB", TABLE=sdtable_[iocc]))

    sdtable = CALC_TABLE(TABLE=sdtable0, ACTION=fkw_comb)

    if post._groupno:
        tri = ("NUME_ORDRE", "M", "SIGM_REFE", "SIGM_SEUIL", "ABSC_CURV_NORM")
    else:
        tri = ("NUME_ORDRE", "M", "SIGM_REFE", "SIGM_SEUIL", "GROUP_MA")

    sdtable = CALC_TABLE(
        reuse=sdtable, TABLE=sdtable, ACTION=_F(OPERATION="TRI", NOM_PARA=tri, ORDRE="CROISSANT")
    )

    return sdtable


class TableBeremin(Table):
    """Helper object to build the result table."""

    types = None
    cols = None
    data = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, use_function, group_no):
        Table.__init__(self)
        self.data = {}
        if not group_no:
            self.cols = [
                "NUME_ORDRE",
                "INST",
                "GROUP_MA",
                "M",
                "SIGM_REFE",
                "SIGM_SEUIL",
                "SIGMA_WEIBULL",
                "SIGMA_WEIBULL**M",
                "PROBA_WEIBULL",
            ]
        else:
            self.cols = [
                "NUME_ORDRE",
                "INST",
                "GROUP_MA",
                "COOR_X",
                "COOR_Y",
                "COOR_Z",
                "ABSC_CURV",
                "ABSC_CURV_NORM",
                "M",
                "SIGM_REFE",
                "SIGM_SEUIL",
                "SIGMA_WEIBULL",
                "SIGMA_WEIBULL**M",
                "PROBA_WEIBULL",
            ]

        for col in self.cols:
            self.data.setdefault(col, [])

        if not group_no:
            if use_function:
                self.types = "IRKRKKRRR"
            else:
                self.types = "IRKRRRRRR"
        else:
            if use_function:
                self.types = "IRKRRRRRRKKRRR"
            else:
                self.types = "IRKRRRRRRRRRRR"

    def append(self, *values):
        """Append the values of a row (columns order must match the definition).

        Args:
            values (list[misc]): Values of the row for each parameter.
        """
        assert len(values) == len(self.cols)
        for col, value in zip(self.cols, values):
            self.data[col].append(value)

    def create_table(self):
        """Create and return the Table datastructure.

        Returns:
            Table/table_sdaster: Table datastructure.
        """
        list_kws = []
        for col, typ in zip(self.cols, self.types):
            if typ != "K":
                new_col = {"PARA": col, "LISTE_" + typ: self.data[col]}
            else:
                new_col = {"PARA": col, "LISTE_" + typ: self.data[col], "TYPE_K": "K24"}
            list_kws.append(new_col)
        tab = CREA_TABLE(LISTE=list_kws)
        return tab
