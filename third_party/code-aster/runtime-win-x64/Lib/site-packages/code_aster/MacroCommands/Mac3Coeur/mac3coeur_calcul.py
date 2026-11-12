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
This module defines the different types of calculations
"""

from functools import wraps
from libaster import ConvergenceError


from ...Cata.Syntax import _F
from ...CodeCommands import (
    AFFE_CHAR_CINE,
    AFFE_CHAR_MECA,
    CALC_CHAMP,
    CREA_RESU,
    DEFI_FONCTION,
    MODI_MAILLAGE,
    STAT_NON_LINE,
    POST_ELEM,
)
from ...Objects import FieldOnCellsReal
from ...Messages import UTMESS
from ...Utilities import logger
from .mac3coeur_coeur import CoeurFactory
from .thyc_load import ThycLoadManager


def calc_mac3coeur_ops(self, **kwargs):
    """Fonction d'appel de la macro CALC_MAC3COEUR"""

    analysis = Mac3CoeurCalcul.factory(self, kwargs)
    result = analysis.run()

    return result


# decorator to cache values of properties
NULL = object()


def cached_property(method):
    """Decorator for the 'getter' method of a property
    It returns directly the value without calling the 'getter' method itself if
    it has already been computed (== not NULL).
    The value is cached in the attribute "_ + `method name`" of the instance.
    """

    @wraps(method)
    def wrapper(inst):
        """Real wrapper function"""
        attr = "_%s" % method.__name__
        cached = getattr(inst, attr)
        if cached is not NULL:
            return cached
        computed = method(inst)
        setattr(inst, attr, computed)
        return computed

    return wrapper


class Mac3CoeurCalcul:
    """Base class of an analysis, intended to be inherited

    Its factory builds the proper object according to the passed keywords.
    Then, a calculation is just completed using::

        calc = Mac3CoeurCalcul.factory(...)
        calc.run()

    Inherited classes may have to adjust `_prepare_data()` and `_run()` methods.
    There are a lot of cached properties:
        - They should store only some data required by the calculation.
        - They are computed only at the first access (or after being deleted).
        - The cache mecanism allows to build Code_Aster objects or to run long
          operations only if necessary.
        - Prefer use standard properties for scalar values.
    """

    mcfact = None

    @staticmethod
    def factory(macro, args):
        """Factory that returns the calculation object"""
        class_ = None
        if "DEFORMATION" in args and args["DEFORMATION"]:
            class_ = Mac3CoeurDeformation
        if "LAME" in args and args["LAME"]:
            class_ = Mac3CoeurLame
        if "ETAT_INITIAL" in args and args["ETAT_INITIAL"]:
            class_ = Mac3CoeurEtatInitial
        if not class_:
            UTMESS("F", "DVP_1")
        return class_(macro, args)

    def __init__(self, macro, args):
        """Initialization"""
        self.macro = macro
        self.keyw = args
        self.mcf = args[self.mcfact]
        # parameters
        self._niv_fluence = 0.0
        self._subdivis = 1
        self._use_archimede = None
        self.char_init = None
        self.etat_init = None
        self._maintien_grille = None
        self.calc_res_def = False
        self.res_def = None
        self.res_def_keyw = None
        self._dilat_only = None

        # cached properties
        self._init_properties()

    def _init_properties(self):
        """Initialize all the cached properties to NULL"""
        self._coeur = NULL
        self._mesh = NULL
        self._model = NULL
        self._geofib = NULL
        self._carael = NULL
        self._cham_mater_contact = NULL
        self._cham_mater_free = NULL
        self._times = NULL
        self._times_arch = NULL
        self._times_woSubd = NULL
        self._evol_temp = NULL
        self._evol_fluence = NULL
        self._rigid_load = NULL
        self._archimede_load = NULL
        self._gravity_load = NULL
        self._vessel_head_load = NULL
        self._vessel_dilatation_load = NULL
        self._thyc_load = NULL
        self._symetric_cond = NULL
        self._periodic_cond = NULL
        self._vessel_dilatation_load_full = NULL
        self._kinematic_cond = NULL
        self._char_ini_comp = NULL
        self._null_sigma_field = NULL

    def _prepare_data(self, **kwargs):
        """Prepare the data for the calculation"""

        self.coeur.init_from_mesh(self.mesh)
        if not self.coeur.check_groups(self.mesh):
            UTMESS("F", "COEUR0_5", valk=("CU_*",))
        # force the computation of the times to ensure it is done first
        # Note that times depends on niv_fluence and subdivis.
        self.times
        self.times_arch
        self.fluence_cycle = self.keyw.get("FLUENCE_CYCLE")
        self._type_deformation = self.keyw.get("TYPE_DEFORMATION")
        self._option_rigi_geom = "DEFAUT"
        if "RIGI_GEOM" in self._type_deformation:
            self._type_deformation = "PETIT"
            self._option_rigi_geom = "OUI"

        # force computation of null sigma field
        self.null_sigma_field
        logger.debug("<MAC3_CALCUL><TOPLEVEL>: Prepare Data")

    def _run(self, **kwargs):
        """Run the calculation itself"""
        raise NotImplementedError("must be defined in a subclass")

    def run(self, **kwargs):
        """Run all the calculation steps"""
        self._prepare_data(**kwargs)
        self._check_mass()
        return self._run(**kwargs)

    def _check_mass(self):
        self.compute_core_mass()
        for ac in self.coeur.collAC:
            self.compute_ac_mass(ac)

    def compute_core_mass(self):

        MASSE_TOT = POST_ELEM(
            MODELE=self.model,
            CHAM_MATER=self.cham_mater_free,
            CARA_ELEM=self.carael,
            MASS_INER=_F(TOUT="OUI"),
        )
        mtot_core = MASSE_TOT.EXTR_TABLE().values()["MASSE"][0]
        UTMESS("I", "COEUR0_9", valr=mtot_core)

        return mtot_core

    def compute_ac_mass(self, ac):

        pos = ac.pos_aster
        cells_with_mass = [f"CR_{pos}", f"TG_{pos}", f"ES_{pos}", f"EI_{pos}", f"GR_{pos}"]

        MASSE_AC = POST_ELEM(
            MODELE=self.model,
            CHAM_MATER=self.cham_mater_free,
            CARA_ELEM=self.carael,
            MASS_INER=_F(GROUP_MA=cells_with_mass),
        )

        tab_ac = MASSE_AC.EXTR_TABLE().values()
        val_ac = dict(zip(tab_ac["LIEU"], tab_ac["MASSE"]))
        mtot_ac = val_ac.pop("UNION_GROUP_MA")
        mtot_dan = mtot_ac * 9.81 / 10.0

        for comp, mcomp in val_ac.items():
            mcomp_dan = mcomp * 9.81 / 10.0
            logger.debug("<MAC3_CALCUL><MASS>: %s %1.1f kg (%1.1f daN)" % (comp, mcomp, mcomp_dan))

        UTMESS("I", "COEUR0_8", valk=(ac.typeAC, ac.pos_damac), valr=(mtot_ac, mtot_dan))

        return mtot_ac

    def restrict_displacement(self, resu, cmps=None, grps=None):
        """
        Shrink resu for Mac3CoeurEtatInitial
        """
        acpara = resu.getAccessParameters()

        ls_affe = []
        kws_restrict = {}
        if cmps is not None:
            kws_restrict["cmps"] = cmps
        if grps is not None:
            kws_restrict["groupsOfNodes"] = grps

        for idx, time in zip(acpara["NUME_ORDRE"], acpara["INST"]):
            full_field = resu.getField("DEPL", idx)
            restricted_field = full_field.restrict(**kws_restrict)
            ls_affe.append(
                _F(
                    NOM_CHAM="DEPL",
                    CHAM_GD=restricted_field,
                    INST=time,
                    PRECISION=1.0e-08,
                    MODELE=resu.getModel(),
                )
            )

        return CREA_RESU(OPERATION="AFFE", TYPE_RESU="EVOL_NOLI", AFFE=ls_affe)

    @property
    def is_lame_computation(self):
        return self.mcfact in ("LAME",)

    @property
    def is_mono(self):
        return self.keyw.get("TYPE_COEUR").startswith("MONO")

    @property
    def is_row(self):
        return self.keyw.get("TYPE_COEUR").startswith("LIGNE")

    @property
    def lock_grid_rotation(self):
        return self.keyw.get("ROTATION_GRILLE").startswith("NON")

    @property
    def niv_fluence(self):
        """Return the fluence level"""
        return self._niv_fluence

    @niv_fluence.setter
    def niv_fluence(self, value):
        """Set the value of the fluence level"""
        self._niv_fluence = value

    @property
    def subdivis(self):
        """Return the factor of time splitting"""
        return self._subdivis

    @subdivis.setter
    def subdivis(self, value):
        """Set the value of the time splitting"""
        self._subdivis = value

    @property
    def use_archimede(self):
        """Tell if Archimede loadings are enabled or not ('OUI'/'NON')"""
        return self._use_archimede

    @use_archimede.setter
    def use_archimede(self, value):
        """Set the value of the time splitting"""
        self._use_archimede = value

    # cached properties
    @property
    @cached_property
    def coeur(self):
        """Return the `Coeur` object"""
        fcoreargs = {
            "type_coeur": self.keyw["TYPE_COEUR"],
            "sdtab": self.keyw["TABLE_N"],
            "longueur": self.keyw["NB_ASSEMBLAGE"] if self.is_row else None,
        }

        return CoeurFactory.build(**fcoreargs)

    @coeur.setter
    def coeur(self, value):
        """Setter method that ensure that the attribute is NULL"""
        assert self._coeur is NULL, "attribute must be set only once or resetted"
        self._coeur = value

    @coeur.deleter
    def coeur(self):
        """Reset the attribute"""
        self._coeur = NULL

    @property
    @cached_property
    def null_sigma_field(self):
        """Return a null stress field for MAC3"""

        logger.debug("<MAC3_CALCUL><PREPRO>: Start creating a null stress field.")

        sig_nul = FieldOnCellsReal(self.model, "ELGA", "SIEF_R", self.carael)
        sig_nul.setValues(0.0)

        logger.debug("<MAC3_CALCUL><PREPRO>: Null stress field created.")

        return sig_nul

    @null_sigma_field.setter
    def null_sigma_field(self, value):
        """Setter method that ensure that the attribute is NULL"""
        assert self._null_sigma_field is NULL, "attribute must be set only once or resetted"
        self._null_sigma_field = value

    @property
    @cached_property
    def mesh(self):
        """Return the `maillage_sdaster` object"""
        return self.coeur.affectation_maillage(self.keyw.get("MAILLAGE_N"))

    @mesh.setter
    def mesh(self, value):
        """Setter method that ensure that the attribute is NULL"""
        assert self._mesh is NULL, "attribute must be set only once or resetted"
        self._mesh = value

    @mesh.deleter
    def mesh(self):
        """Reset the attribute"""
        self._mesh = NULL

    @property
    @cached_property
    def model(self):
        """Return the `modele_sdaster` object"""
        return self.coeur.affectation_modele(self.mesh)

    @model.setter
    def model(self, value):
        """Setter method that ensure that the attribute is NULL"""
        assert self._model is NULL, "attribute must be set only once or resetted"
        self._model = value

    @model.deleter
    def model(self):
        """Reset the attribute"""
        self._model = NULL

    @property
    @cached_property
    def geofib(self):
        """Return the `geom_fibre` object"""
        return self.coeur.definition_geom_fibre()

    @property
    @cached_property
    def carael(self):
        """Return the `cara_elem` object"""
        return self.coeur.definition_cara_coeur(self.model, self.geofib)

    @carael.setter
    def carael(self, value):
        """Setter method that ensure that the attribute is NULL"""
        assert self._carael is NULL, "attribute must be set only once or resetted"
        self._carael = value

    @carael.deleter
    def carael(self):
        """Reset the attribute"""
        self._carael = NULL

    @property
    @cached_property
    def times(self):
        """Return the list of the time steps"""
        return self.coeur.definition_time(self.niv_fluence, self.subdivis)

    @property
    @cached_property
    def times_arch(self):
        """Return the list of the archive time"""
        return self.coeur.definition_time_arch(self.niv_fluence, self.subdivis)

    @property
    @cached_property
    def times_woSubd(self):
        """Return the list of the time steps"""
        return self.coeur.definition_time(self.niv_fluence, self.subdivis, 1)

    @property
    @cached_property
    def evol_temp(self):
        """Return the evolution of temperature"""
        return self.coeur.definition_champ_temperature(self.mesh)

    @property
    @cached_property
    def evol_fluence(self):
        """Return the evolution of the fluence fields"""
        if self.etat_init:
            assert self.fluence_cycle == 0.0
        return self.coeur.definition_fluence(
            self.niv_fluence, self.mesh, self.fluence_cycle, self.is_lame_computation
        )

    @property
    @cached_property
    def cham_mater_free(self):
        """Return the field of material (without contact)"""
        return self.coeur.definition_materiau(
            self.mesh, self.geofib, self.evol_fluence, self.evol_temp, CONTACT="NON"
        )

    @property
    @cached_property
    def cham_mater_contact(self):
        """Return the field of material (with contact enabled)"""
        return self.coeur.definition_materiau(
            self.mesh, self.geofib, self.evol_fluence, self.evol_temp, CONTACT="OUI"
        )

    def cham_mater_contact_progressif(self, ratio):
        """Return the field of material (with contact enabled)"""
        return self.coeur.definition_materiau(
            self.mesh, self.geofib, self.evol_fluence, self.evol_temp, CONTACT="OUI", RATIO=ratio
        )

    # loadings
    @property
    @cached_property
    def rigid_load(self):
        """Compute the rigid body loading"""

        rigid_loads = self.coeur.cl_rigidite_grille()
        if self.coeur.is_multi_rod:
            rigid_loads.extend(self.coeur.cl_rigidite_embouts())

        grid_lock = AFFE_CHAR_MECA(MODELE=self.model, LIAISON_SOLIDE=rigid_loads)

        return [_F(CHARGE=grid_lock)]

    @property
    @cached_property
    def archimede_load(self):
        """Compute the Archimede loadings"""
        fmult_arch = self.coeur.definition_temp_archimede(self.use_archimede)
        load = [
            _F(CHARGE=self.coeur.definition_archimede_nodal(self.model), FONC_MULT=fmult_arch),
            _F(CHARGE=self.coeur.definition_archimede_poutre(self.model), FONC_MULT=fmult_arch),
        ]
        return load

    @property
    @cached_property
    def gravity_load(self):
        """Return the gravity loading"""
        return [_F(CHARGE=self.coeur.definition_pesanteur(self.model))]

    @property
    @cached_property
    def vessel_head_load(self):
        """Return the loadings due to the pression of
        the vessel head"""

        dicv = self.mcf[0]
        typ = dicv.get("TYPE_MAINTIEN") or "DEPL_PSC"
        force = None
        compression_init = self.fluence_cycle != 0
        if typ == "FORCE":
            force = self.mcf["FORCE_MAINTIEN"]
        char_head = self.coeur.definition_maintien_type(self.model, typ, force, compression_init)
        return [_F(CHARGE=char_head)]

    @property
    @cached_property
    def vessel_dilatation_load(self):
        """Return the loading due to the vessel dilatation"""
        char_dilat_part = self.coeur.dilatation_cuve(
            self.model,
            self.mesh,
            (self.char_init is not None),
            self._maintien_grille,
            T_CONST_CUVE=self._dilat_only,
        )
        return [_F(CHARGE=char_dilat_part)]

    @property
    @cached_property
    def vessel_dilatation_load_full(self):
        """Return the loading due to the vessel dilatation"""
        char_dilat_full = self.coeur.dilatation_cuve(
            self.model, self.mesh, is_char_ini=False, maintien_grille=False, T_CONST_CUVE=None
        )
        return [_F(CHARGE=char_dilat_full)]

    @property
    @cached_property
    def thyc_load(self):
        """Return the loading due to the fluid flow"""

        thyc = ThycLoadManager.from_unit(self.coeur, self.model, self.mcf["UNITE_THYC"])

        coef_mult_thv = self.mcf.get("COEF_MULT_THV", 1.0)
        coef_mult_tht = self.mcf.get("COEF_MULT_THT", 1.0)

        fmult_ax = self.coeur.definition_temp_hydro_axiale(coef_mult_thv)
        fmult_tr = self.coeur.definition_effort_transverse(coef_mult_tht)

        load_ax = [
            _F(CHARGE=thyc.chax_nodal, FONC_MULT=fmult_ax),
            _F(CHARGE=thyc.chax_poutre, FONC_MULT=fmult_ax),
        ]
        load_tr = [
            _F(CHARGE=thyc.chtr_nodal, FONC_MULT=fmult_tr),
            _F(CHARGE=thyc.chtr_poutre, FONC_MULT=fmult_tr),
        ]
        self._thyc_ax = (thyc.chax_nodal, thyc.chax_poutre)
        self._thyc_tr = (thyc.chtr_nodal, thyc.chtr_poutre)
        return (load_ax, load_tr)

    @property
    @cached_property
    def kinematic_cond(self):
        """Define the kinematic conditions from displacement"""

        red_resu = self.restrict_displacement(
            self.char_init, cmps=["DY", "DZ"], grps=["UNLINKED_LOCAL"]
        )
        kine_load = AFFE_CHAR_CINE(MODELE=self.model, EVOL_IMPO=red_resu, NOM_CMP=("DY", "DZ"))
        kine_load_cine = [_F(CHARGE=kine_load)]

        return kine_load_cine

    @property
    @cached_property
    def symetric_cond(self):
        """Define the boundary conditions of symetry"""

        def block(grma=None, grno=None, ddl=None):
            """Block 'ddl' of 'grma/grno' to zero"""
            kddl = {}.fromkeys(ddl, 0.0)
            kddl["GROUP_MA" if grma else "GROUP_NO"] = grma or grno
            return kddl

        if self.lock_grid_rotation:
            ddl_lock_grid = ["DRX", "DRY", "DRZ"]
        else:
            ddl_lock_grid = ["DRX"]

        ddl_impo = [
            block(grma="CRAYON", ddl=["DRX"]),
            block(grno="LISPG", ddl=ddl_lock_grid),
            block(grma=("EBOSUP", "EBOINF"), ddl=["DRX", "DRY", "DRZ"]),
        ]
        _excit = AFFE_CHAR_CINE(MODELE=self.model, MECA_IMPO=ddl_impo)
        return [_F(CHARGE=_excit)]

    @property
    @cached_property
    def periodic_cond(self):
        """Define the boundary conditions of periodicity"""

        def equal(ddl, grno1, grno2):
            """Return keyword to set ddl(grno1) = ddl(grno2)"""
            return _F(
                GROUP_NO_1=grno1,
                GROUP_NO_2=grno2,
                DDL_1=ddl,
                DDL_2=ddl,
                COEF_MULT_1=1.0,
                COEF_MULT_2=-1.0,
                COEF_IMPO=0.0,
            )

        liaison_group = [
            equal("DY", "PMNT_S", "PEBO_S"),
            equal("DZ", "PMNT_S", "PEBO_S"),
            equal("DY", "PSUP", "PEBO_S"),
            equal("DZ", "PSUP", "PEBO_S"),
            equal("DY", "PINF", "FIX"),
            equal("DZ", "PINF", "FIX"),
        ]
        _excit = AFFE_CHAR_MECA(MODELE=self.model, LIAISON_GROUP=liaison_group)
        return [_F(CHARGE=_excit)]

    @property
    @cached_property
    def char_ini_comp(self):
        comp = [
            _F(
                RELATION="MULTIFIBRE",
                GROUP_MA=("CRAYON", "T_GUIDE"),
                PARM_THETA=0.5,
                DEFORMATION=self._type_deformation,
                RIGI_GEOM=self._option_rigi_geom,
            ),
            _F(RELATION="DIS_GRICRA", GROUP_MA="ELA"),
            _F(RELATION="DIS_CHOC", GROUP_MA=("RES_EXT", "RES_CONT")),
            _F(RELATION="ELAS", GROUP_MA=("EBOINF", "EBOSUP", "RIG", "DIL")),
            _F(RELATION="VMIS_ISOT_TRAC", GROUP_MA="MAINTIEN", DEFORMATION="PETIT"),
        ]
        return comp

    def snl(self, **kwds):
        """Return the common keywords for STAT_NON_LINE
        All keywords can be overridden using `kwds`."""

        # FIXME issue33947, issue33519
        nprec = -1 if self.coeur.is_multi_rod else 8
        keywords = {
            "MODELE": self.model,
            "CARA_ELEM": self.carael,
            "CHAM_MATER": self.cham_mater_free,
            "COMPORTEMENT": (
                _F(
                    RELATION="MULTIFIBRE",
                    GROUP_MA=("CRAYON", "T_GUIDE"),
                    PARM_THETA=0.5,
                    DEFORMATION=self._type_deformation,
                    RIGI_GEOM=self._option_rigi_geom,
                ),
                _F(RELATION="DIS_GRICRA", GROUP_MA="ELA"),
                _F(RELATION="DIS_CHOC", GROUP_MA=("CREI", "RES_TOT")),
                _F(
                    RELATION="ELAS", GROUP_MA=("GRIL_I", "GRIL_E", "EBOINF", "EBOSUP", "RIG", "DIL")
                ),
                _F(RELATION="VMIS_ISOT_TRAC", GROUP_MA="MAINTIEN", DEFORMATION="PETIT"),
            ),
            "SUIVI_DDL": _F(
                NOM_CHAM="DEPL", EVAL_CHAM="MAXI_ABS", GROUP_NO="CR_BAS", NOM_CMP=("DX",)
            ),
            "NEWTON": _F(MATRICE="TANGENTE", REAC_ITER=1),
            "CONVERGENCE": _F(ITER_GLOB_MAXI=20, RESI_GLOB_MAXI=1.0e-2, RESI_GLOB_RELA=1.0e-6),
            "SOLVEUR": _F(METHODE="MUMPS", PRETRAITEMENTS="AUTO", NPREC=nprec),
            "ARCHIVAGE": _F(LIST_INST=self.times_arch, PRECISION=1.0e-08),
            "AFFICHAGE": _F(INFO_RESIDU="OUI"),
            "INFO": 1,
        }
        keywords.update(kwds)
        return keywords

    def snl_lame(self, **kwds):
        """Return the common keywords for STAT_NON_LINE
        All keywords can be overridden using `kwds`."""

        lkeys = {"ARCHIVAGE": _F(INST=self.coeur.temps_simu["T1"], PRECISION=1.0e-08)}
        lkeys.update(kwds)
        return self.snl(**lkeys)

    def evaluate_contacts_prediction(self, initial_state_kws, current_load, type_calc, type_load):
        assert type_calc in ("LAME", "DEFORMATION")
        assert type_load in ("LOAD", "UNLOAD")

        logger.info(
            "<MAC3_CALCUL><PREDICTION><%s>: Start activating %s contacts for prediction."
            % (type_calc, type_load)
        )

        if type_load == "LOAD":
            tstart = "T0"
            tend = "T0b"
            ratio = 1.0
            max_test = 5
        else:
            tstart = "T8b"
            tend = "T9"
            ratio = 1.0e-8
            max_test = 9

        if type_calc == "LAME":
            snl_oper = self.snl_lame
        else:
            snl_oper = self.snl

        intermediate_resu_kws = []

        intermediate_resu_kws.append(
            snl_oper(
                EXCIT=current_load,
                CHAM_MATER=self.cham_mater_contact_progressif(ratio),
                ETAT_INIT=initial_state_kws,
                INCREMENT=_F(
                    LIST_INST=self.times_woSubd,
                    PRECISION=1.0e-08,
                    INST_INIT=self.coeur.temps_simu[tstart],
                    INST_FIN=self.coeur.temps_simu[tend],
                ),
            )
        )

        nb_test = 0
        while nb_test < max_test:
            try:
                intermediate_resu = []
                for i, last_kws in enumerate(reversed(intermediate_resu_kws)):
                    if i > 0:
                        # Last computed result is used as prediction
                        last_kws.update(
                            {
                                "NEWTON": _F(
                                    MATRICE="TANGENTE",
                                    PREDICTION="DEPL_CALCULE",
                                    EVOL_NOLI=intermediate_resu[i - 1],
                                    REAC_ITER=1,
                                )
                            }
                        )
                    logger.info(
                        "<MAC3_CALCUL><PREDICTION><%s>: Start computing intermediate result nr %d"
                        % (type_calc, i + 1)
                    )
                    last_resu = STAT_NON_LINE(**last_kws)
                    logger.info(
                        "<MAC3_CALCUL><PREDICTION><%s>: Finish computing intermediate result nr %d"
                        % (type_calc, i + 1)
                    )
                    intermediate_resu.append(last_resu)

                # Si tous les resu intermediaires passent on s'arrete.
                break

            except ConvergenceError:
                logger.info(
                    "<MAC3_CALCUL><PREDICTION><%s>: Failed computing intermediate result"
                    % (type_calc)
                )
                if type_load == "LOAD":
                    ratio = ratio / 10.0
                else:
                    ratio = ratio * 10.0
                intermediate_resu_kws.append(
                    snl_oper(
                        EXCIT=current_load,
                        CHAM_MATER=self.cham_mater_contact_progressif(ratio),
                        ETAT_INIT=initial_state_kws,
                        INCREMENT=_F(
                            LIST_INST=self.times_woSubd,
                            PRECISION=1.0e-08,
                            INST_INIT=self.coeur.temps_simu[tstart],
                            INST_FIN=self.coeur.temps_simu[tend],
                        ),
                    )
                )
            finally:
                nb_test += 1
        else:
            raise ConvergenceError(
                "<MAC3_CALCUL><%s>: No convergence during the application of contacts."
                % (type_calc)
            )

        logger.info(
            "<MAC3_CALCUL><PREDICTION><%s>: Finish activating %s contacts for prediction."
            % (type_calc, type_load)
        )
        return intermediate_resu[-1]


class Mac3CoeurDeformation(Mac3CoeurCalcul):
    """Compute the strain of the assemblies"""

    mcfact = "DEFORMATION"

    def __init__(self, macro, args, char_init=None):
        """Initialization"""
        super().__init__(macro, args)
        self.char_init = char_init

    def _prepare_data(self, **kwargs):
        """Prepare the data for the calculation"""
        self.niv_fluence = self.mcf["NIVE_FLUENCE"]
        if self.is_mono:
            self.subdivis = 5
        if self.mcf["TEMP_IMPO"]:
            self._dilat_only = self.mcf["TEMP_IMPO"]
        self.use_archimede = self.mcf["ARCHIMEDE"]
        self._maintien_grille = self.mcf["MAINTIEN_GRILLE"] == "OUI"
        super()._prepare_data(**kwargs)
        logger.debug("<MAC3_CALCUL><DEFORMATION>: Prepare Data")

    @property
    @cached_property
    def mesh(self):
        """Return the `maillage_sdaster` object"""
        mesh = self.keyw.get("MAILLAGE_N")

        if self.char_init:
            resu_init = None
        else:
            resu_init = self.mcf["RESU_INIT"]
        if not (mesh or resu_init or self.char_init):
            UTMESS("F", "COEUR0_4")
        elif resu_init:
            if mesh:
                UTMESS("I", "COEUR0_1")
            self.etat_init = _F(EVOL_NOLI=resu_init)
            mesh = resu_init.getModel().getMesh()
        elif self.char_init:
            if mesh:
                UTMESS("I", "COEUR0_1")
            mesh = self.char_init.getModel().getMesh()
        else:
            mesh = super().mesh
        return mesh

    @property
    @cached_property
    def model(self):
        """Return the `modele_sdaster` object"""

        if self.char_init:
            resu_init = None
        else:
            resu_init = self.mcf["RESU_INIT"]
        if resu_init:
            model = resu_init.getModel()
        elif self.char_init:
            model = self.char_init.getModel()
        else:
            model = super().model
        return model

    @property
    @cached_property
    def carael(self):
        """Return the `cara_elem` object"""

        if self.char_init:
            resu_init = None
        else:
            resu_init = self.mcf["RESU_INIT"]
        if resu_init:
            assert resu_init.getElementaryCharacteristics() is not None
            carael = resu_init.getElementaryCharacteristics()
        elif self.char_init:
            assert self.char_init.getElementaryCharacteristics() is not None
            carael = self.char_init.getElementaryCharacteristics()
        else:
            carael = super().carael
        return carael

    def vessel_head_unload(self, RESU):
        CALC_CHAMP(
            reuse=RESU,
            RESULTAT=RESU,
            PRECISION=1.0e-08,
            CRITERE="RELATIF",
            INST=self.coeur.temps_simu["T8"],
            FORCE=("FORC_NODA",),
        )

        forc_noda = RESU.getField(
            "FORC_NODA", value=self.coeur.temps_simu["T8"], para="INST", prec=1.0e-8
        )

        mesh = RESU.getModel().getMesh()
        gnodes = mesh.getNodes("PMNT_S", localNumbering=True)

        sfield = forc_noda.toSimpleFieldOnNodes()
        fvalues, fmask = sfield.getValues()
        fx = fvalues.T[0]
        list_args = [_F(NOEUD=str(n + 1), FX=f) for (n, f) in zip(gnodes, fx[gnodes])]

        head_unload = AFFE_CHAR_MECA(MODELE=self.model, FORCE_NODALE=list_args)

        time_func = DEFI_FONCTION(
            NOM_PARA="INST",
            PROL_DROITE="CONSTANT",
            VALE=(self.coeur.temps_simu["T8"], 1.0, self.coeur.temps_simu["T8b"], 0.0),
        )

        return [_F(CHARGE=head_unload, FONC_MULT=time_func)]

    def _run(self, **kwargs):
        """Run the main part of the calculation"""

        if self.is_mono:
            chmat_contact = self.cham_mater_free
        else:
            chmat_contact = self.cham_mater_contact

        __RESULT = None

        # T0 - T8
        if self.char_init:
            logger.info(
                "<MAC3_CALCUL><DEFORMATION><CHAR_INIT>: Start Computation with an initial load."
            )

            logger.info(
                "<MAC3_CALCUL><DEFORMATION><CHAR_INIT>: Start computing boundary conditions T0-T5."
            )
            loads_chin_t0_t5 = (
                self.archimede_load
                + self.gravity_load
                + self.symetric_cond
                + self.vessel_head_load
                + self.vessel_dilatation_load
                + self.kinematic_cond
                + self.rigid_load
                + self.thyc_load[0]
            )
            logger.info(
                "<MAC3_CALCUL><DEFORMATION><CHAR_INIT>: Finish computing boundary conditions T0-T5."
            )

            logger.info("<MAC3_CALCUL><DEFORMATION><CHAR_INIT>: Start computing evolution T0-T5.")
            __RESULT = STAT_NON_LINE(
                **self.snl(
                    CHAM_MATER=self.cham_mater_free,
                    INCREMENT=_F(
                        LIST_INST=self.times,
                        INST_INIT=self.coeur.temps_simu["T0"],
                        PRECISION=1.0e-08,
                        INST_FIN=self.coeur.temps_simu["T5"],
                    ),
                    COMPORTEMENT=self.char_ini_comp,
                    EXCIT=loads_chin_t0_t5,
                    ETAT_INIT=_F(SIGM=self.null_sigma_field),
                )
            )
            logger.info("<MAC3_CALCUL><DEFORMATION><CHAR_INIT>: Finish computing evolution T0-T5.")

            logger.info(
                "<MAC3_CALCUL><DEFORMATION><CHAR_INIT>: Start computing boundary conditions T5-T8."
            )
            loads_chin_t5_t8 = (
                self.archimede_load
                + self.gravity_load
                + self.symetric_cond
                + self.vessel_head_load
                + self.vessel_dilatation_load_full
                + self.periodic_cond
                + self.rigid_load
                + self.thyc_load[0]
            )
            logger.info(
                "<MAC3_CALCUL><DEFORMATION><CHAR_INIT>: Finish computing boundary conditions T5-T8."
            )

            logger.info("<MAC3_CALCUL><DEFORMATION><CHAR_INIT>: Start computing evolution T5-T8.")
            __RESULT = STAT_NON_LINE(
                **self.snl(
                    reuse=__RESULT,
                    RESULTAT=__RESULT,
                    CHAM_MATER=self.cham_mater_free,
                    INCREMENT=_F(
                        LIST_INST=self.times,
                        PRECISION=1.0e-08,
                        INST_INIT=__RESULT.getLastTime(),
                        INST_FIN=self.coeur.temps_simu["T8"],
                    ),
                    COMPORTEMENT=self.char_ini_comp,
                    EXCIT=loads_chin_t5_t8,
                    ETAT_INIT=_F(EVOL_NOLI=__RESULT),
                )
            )
            logger.info("<MAC3_CALCUL><DEFORMATION><CHAR_INIT>: Finish computing evolution T5-T8.")

            logger.info(
                "<MAC3_CALCUL><DEFORMATION><CHAR_INIT>: Start computing boundary conditions T8-Tf."
            )
            loads_chin_t8_t9 = (
                self.archimede_load
                + self.gravity_load
                + self.symetric_cond
                + self.vessel_head_unload(__RESULT)
                + self.vessel_dilatation_load_full
                + self.periodic_cond
                + self.rigid_load
            )
            logger.info(
                "<MAC3_CALCUL><DEFORMATION><CHAR_INIT>: Start computing boundary conditions T8-Tf."
            )

            logger.info("<MAC3_CALCUL><DEFORMATION><CHAR_INIT>: Start computing evolution T8-Tf.")
            __RESULT = STAT_NON_LINE(
                **self.snl(
                    reuse=__RESULT,
                    RESULTAT=__RESULT,
                    CHAM_MATER=self.cham_mater_free,
                    ETAT_INIT=_F(EVOL_NOLI=__RESULT),
                    EXCIT=loads_chin_t8_t9,
                    INCREMENT=_F(
                        LIST_INST=self.times, INST_INIT=__RESULT.getLastTime(), PRECISION=1e-8
                    ),
                    COMPORTEMENT=self.char_ini_comp,
                )
            )
            logger.info("<MAC3_CALCUL><DEFORMATION><CHAR_INIT>: Finish computing evolution T8-Tf.")
            logger.info(
                "<MAC3_CALCUL><DEFORMATION><CHAR_INIT>: Finish Computation with an initial load."
            )

        elif self._dilat_only:
            logger.info(
                "<MAC3_CALCUL><DEFORMATION><DILAT_ONLY>: Start Computation with dilatation only."
            )

            logger.info(
                "<MAC3_CALCUL><DEFORMATION><DILAT_ONLY>: Start computing boundary conditions."
            )
            loads_donly1 = (
                self.archimede_load
                + self.gravity_load
                + self.symetric_cond
                + self.vessel_head_load
                + self.vessel_dilatation_load
                + self.periodic_cond
                + self.rigid_load
            )
            logger.info(
                "<MAC3_CALCUL><DEFORMATION><DILAT_ONLY>: Finish computing boundary conditions."
            )

            logger.info("<MAC3_CALCUL><DEFORMATION><DILAT_ONLY>: Start computing evolution T0-T4.")
            __RESULT = STAT_NON_LINE(
                **self.snl(
                    CHAM_MATER=self.cham_mater_free,
                    INCREMENT=_F(
                        LIST_INST=self.times,
                        PRECISION=1.0e-08,
                        INST_INIT=self.coeur.temps_simu["T0"],
                        INST_FIN=self.coeur.temps_simu["T4"],
                    ),
                    EXCIT=loads_donly1,
                    ETAT_INIT=_F(SIGM=self.null_sigma_field),
                )
            )
            logger.info("<MAC3_CALCUL><DEFORMATION><DILAT_ONLY>: Finish computing evolution T0-T4.")

            logger.info(
                "<MAC3_CALCUL><DEFORMATION><DILAT_ONLY>: Finish Computation with dilatation only."
            )

        else:
            logger.info("<MAC3_CALCUL><DEFORMATION>: Start Computation.")

            logger.info("<MAC3_CALCUL><DEFORMATION>: Start computing boundary conditions T0-T8.")
            loads_def_t0_t8 = (
                self.archimede_load
                + self.gravity_load
                + self.symetric_cond
                + self.vessel_head_load
                + self.vessel_dilatation_load
                + self.periodic_cond
                + self.rigid_load
                + self.thyc_load[0]
                + self.thyc_load[1]
            )
            logger.info("<MAC3_CALCUL><DEFORMATION>: Finish computing boundary conditions T0-T8.")

            __RESULT = None
            if not self.etat_init:
                logger.info("<MAC3_CALCUL><DEFORMATION>: Start computing initial state T0.")
                __RESULT = STAT_NON_LINE(
                    **self.snl(
                        CHAM_MATER=self.cham_mater_free,
                        INCREMENT=_F(
                            LIST_INST=self.times,
                            PRECISION=1.0e-08,
                            INST_FIN=self.coeur.temps_simu["T0"],
                        ),
                        EXCIT=loads_def_t0_t8,
                        ETAT_INIT=_F(SIGM=self.null_sigma_field),
                    )
                )
                self.etat_init = _F(EVOL_NOLI=__RESULT)
                logger.info("<MAC3_CALCUL><DEFORMATION>: Finish computing initial state T0.")

            c_prediction = self.evaluate_contacts_prediction(
                self.etat_init, loads_def_t0_t8, "DEFORMATION", "LOAD"
            )
            logger.info(
                "<MAC3_CALCUL><DEFORMATION>: Start activation of contacts T0-T0b using prediction."
            )

            __RESULT = STAT_NON_LINE(
                **self.snl(
                    reuse=__RESULT,
                    RESULTAT=__RESULT,
                    NEWTON=_F(
                        MATRICE="TANGENTE",
                        PREDICTION="DEPL_CALCULE",
                        EVOL_NOLI=c_prediction,
                        REAC_ITER=1,
                    ),
                    CHAM_MATER=self.cham_mater_contact,
                    INCREMENT=_F(
                        LIST_INST=self.times_woSubd,
                        PRECISION=1.0e-08,
                        INST_INIT=self.coeur.temps_simu["T0"],
                        INST_FIN=self.coeur.temps_simu["T0b"],
                    ),
                    EXCIT=loads_def_t0_t8,
                    ETAT_INIT=self.etat_init,
                )
            )
            logger.info(
                "<MAC3_CALCUL><DEFORMATION>: Finish activation of contacts T0-T0b using prediction."
            )

            logger.info("<MAC3_CALCUL><DEFORMATION>: Start computing evolution T0b - T8.")
            __RESULT = STAT_NON_LINE(
                **self.snl(
                    reuse=__RESULT,
                    RESULTAT=__RESULT,
                    CHAM_MATER=chmat_contact,
                    INCREMENT=_F(
                        LIST_INST=self.times,
                        PRECISION=1.0e-08,
                        INST_INIT=__RESULT.getLastTime(),
                        INST_FIN=self.coeur.temps_simu["T8"],
                    ),
                    EXCIT=loads_def_t0_t8,
                    ETAT_INIT=_F(EVOL_NOLI=__RESULT),
                )
            )
            logger.info("<MAC3_CALCUL><DEFORMATION>: Finish computing evolution T0b - T8.")

            logger.info("<MAC3_CALCUL><DEFORMATION>: Start computing boundary conditions T8-T8b.")
            loads_def_t8_t8b = (
                self.archimede_load
                + self.gravity_load
                + self.symetric_cond
                + self.vessel_head_unload(__RESULT)
                + self.vessel_dilatation_load
                + self.periodic_cond
                + self.rigid_load
            )
            logger.info("<MAC3_CALCUL><DEFORMATION>: Finish computing boundary conditions T8-T8b.")

            logger.info("<MAC3_CALCUL><DEFORMATION>: Start computing evolution T8-T8b.")
            __RESULT = STAT_NON_LINE(
                **self.snl(
                    reuse=__RESULT,
                    RESULTAT=__RESULT,
                    CHAM_MATER=chmat_contact,
                    ETAT_INIT=_F(EVOL_NOLI=__RESULT),
                    EXCIT=loads_def_t8_t8b,
                    INCREMENT=_F(
                        LIST_INST=self.times,
                        PRECISION=1.0e-08,
                        INST_INIT=__RESULT.getLastTime(),
                        INST_FIN=self.coeur.temps_simu["T8b"],
                    ),
                )
            )
            logger.info("<MAC3_CALCUL><DEFORMATION>: Finish computing evolution T8-T8b.")

            logger.info("<MAC3_CALCUL><DEFORMATION>: Start computing boundary conditions T8b-T9.")
            loads_def_t8b_t9 = (
                self.archimede_load
                + self.gravity_load
                + self.symetric_cond
                + self.vessel_dilatation_load
                + self.periodic_cond
                + self.rigid_load
            )
            logger.info("<MAC3_CALCUL><DEFORMATION>: Finish computing boundary conditions T8b-T9.")

            logger.info(
                "<MAC3_CALCUL><DEFORMATION>: Start computing evolution T8b-T9 (vessel opening)."
            )

            c_prediction = self.evaluate_contacts_prediction(
                _F(EVOL_NOLI=__RESULT), loads_def_t8b_t9, "DEFORMATION", "UNLOAD"
            )

            logger.info("<MAC3_CALCUL><DEFORMATION>: Start vessel opening using prediction.")
            __RESULT = STAT_NON_LINE(
                **self.snl(
                    reuse=__RESULT,
                    RESULTAT=__RESULT,
                    NEWTON=_F(
                        MATRICE="TANGENTE",
                        PREDICTION="DEPL_CALCULE",
                        EVOL_NOLI=c_prediction,
                        REAC_ITER=1,
                    ),
                    CHAM_MATER=self.cham_mater_free,
                    INCREMENT=_F(
                        LIST_INST=self.times_woSubd,
                        PRECISION=1.0e-08,
                        INST_INIT=__RESULT.getLastTime(),
                        INST_FIN=self.coeur.temps_simu["T9"],
                    ),
                    EXCIT=loads_def_t8b_t9,
                    ETAT_INIT=_F(EVOL_NOLI=__RESULT),
                )
            )

            logger.info("<MAC3_CALCUL><DEFORMATION>: Finish vessel opening using prediction.")
            logger.debug(
                "%s (%s), %s",
                self.cham_mater_free,
                self.cham_mater_free.getName(),
                __RESULT.getMaterialField(__RESULT.getLastIndex()),
            )
        return __RESULT


class Mac3CoeurLame(Mac3CoeurCalcul):
    """Compute the thinkness of water from deformed assemblies"""

    mcfact = "LAME"

    def _init_properties(self):
        """Initialize all the cached properties to NULL"""
        super()._init_properties()
        self._damac_load = NULL
        logger.debug("<MAC3_CALCUL><LAME>: Init properties")

    @property
    @cached_property
    def damac_load(self):
        """Return the loading due to the displacements of the water layer"""
        return [_F(CHARGE=self.coeur.affe_char_lame(self.model))]

    def update_coeur(self, resu):
        """Update the `Coeur` object from the given `Table` and result"""

        # Preserve the already computed field
        null_sf = self.null_sigma_field

        self._init_properties()
        self.mesh = resu.getModel().getMesh()
        self.model = resu.getModel()
        self.carael = resu.getElementaryCharacteristics()

        # initializations
        self.coeur.init_from_mesh(self.mesh)
        self.times
        self.null_sigma_field = null_sf

    def deform_mesh_inplace(self, depl):
        _mesh = MODI_MAILLAGE(
            reuse=self.mesh, MAILLAGE=self.mesh, DEFORME=_F(OPTION="TRAN", DEPL=depl)
        )
        del self.mesh
        self.mesh = _mesh
        logger.info("<MAC3_CALCUL><LAME>: Mesh deformed inplace.")

    def asseChamp(self, depl1, depl2):
        cmps = "DX DY DZ".split()
        dtot = depl1.restrict(cmps) + depl2.restrict(cmps)
        dtot.setValues({"DX": 0.0})

        logger.debug("<MAC3_CALCUL><LAME>: Assembly displacement field.")
        return dtot

    def output_resdef(self, resu, depl_deformed, tinit, tfin):
        """save the result to be used by a next calculation"""
        _pdt_ini = self.coeur.temps_simu["T1"]
        _pdt_fin = self.coeur.temps_simu["T4"]

        if (not tinit) and (not tfin):
            _pdt_ini_out = _pdt_ini
            _pdt_fin_out = _pdt_fin
        else:
            _pdt_ini_out = tinit
            _pdt_fin_out = tfin

        depl_ini = resu.getField("DEPL", value=_pdt_ini, para="INST", prec=1.0e-08)
        depl_fin = resu.getField("DEPL", value=_pdt_fin, para="INST", prec=1.0e-08)

        depl_tot_ini = self.asseChamp(depl_deformed, depl_ini)
        depl_tot_fin = self.asseChamp(depl_deformed, depl_fin)

        depl_reversed = depl_deformed.copy()
        depl_reversed *= -1
        self.deform_mesh_inplace(depl_reversed)

        self.res_def = CREA_RESU(
            OPERATION="AFFE",
            TYPE_RESU="EVOL_NOLI",
            AFFE=(
                _F(
                    NOM_CHAM="DEPL",
                    CHAM_GD=depl_tot_ini,
                    INST=_pdt_ini_out,
                    PRECISION=1.0e-08,
                    MODELE=self.model,
                    CARA_ELEM=self.carael,
                    CHAM_MATER=self.cham_mater_free,
                ),
                _F(
                    NOM_CHAM="DEPL",
                    CHAM_GD=depl_tot_fin,
                    INST=_pdt_fin_out,
                    PRECISION=1.0e-08,
                    MODELE=self.model,
                    CARA_ELEM=self.carael,
                    CHAM_MATER=self.cham_mater_free,
                ),
            ),
        )
        logger.info("<MAC3_CALCUL><LAME>: Output result created.")

        if self.res_def_keyw:
            self.macro.register_result(self.res_def, self.res_def_keyw)

    def _prepare_data(self, **kwargs):
        """Prepare the data for the calculation"""
        self.use_archimede = "OUI"
        self._maintien_grille = False
        noresu = kwargs.get("noresu", False)
        if not noresu:
            self.res_def_keyw = self.keyw.get("RESU_DEF")
            if self.res_def_keyw is not None:
                self.calc_res_def = True
        super()._prepare_data(**kwargs)
        logger.debug("<MAC3_CALCUL><LAME>: Prepare Data")

    def _run(self, **kwargs):
        """Run the main part of the calculation"""

        # calcul de deformation d'apres DAMAC / T0 - T1
        logger.info("<MAC3_CALCUL><LAME>: Start computing boundary conditions.")
        loads_lame_base = (
            self.archimede_load
            + self.gravity_load
            + self.symetric_cond
            + self.vessel_head_load
            + self.vessel_dilatation_load
            + self.periodic_cond
            + self.rigid_load
        )

        loads_lame_damac = loads_lame_base + self.damac_load
        loads_lame_thyc = loads_lame_base + self.thyc_load[0] + self.thyc_load[1]
        logger.info("<MAC3_CALCUL><LAME>: Finish computing boundary conditions.")

        logger.info("<MAC3_CALCUL><LAME>: Start computing DAMAC load.")
        snl_damac = STAT_NON_LINE(
            **self.snl_lame(
                INCREMENT=_F(
                    LIST_INST=self.times,
                    PRECISION=1.0e-08,
                    INST_INIT=self.coeur.temps_simu["T0"],
                    INST_FIN=self.coeur.temps_simu["T1"],
                ),
                EXCIT=loads_lame_damac,
                ETAT_INIT=_F(SIGM=self.null_sigma_field),
            )
        )
        logger.info("<MAC3_CALCUL><LAME>: Finish computing DAMAC load.")

        # Update core to force the re-computation of the BC
        self.update_coeur(snl_damac)
        logger.info("<MAC3_CALCUL><LAME>: Re-init core.")

        # On fait l'irradiation historique sur assemblages droits
        # WARNING: element characteristics and the most of the loadings must be
        # computed on the initial (not deformed) mesh
        # please keep the call to deform_mesh after the computation of keywords

        logger.info("<MAC3_CALCUL><LAME>: Start computing state at T0 (undeformed mesh).")
        snl_lame_unloaded = STAT_NON_LINE(
            **self.snl_lame(
                INCREMENT=_F(
                    LIST_INST=self.times, PRECISION=1.0e-08, INST_FIN=self.coeur.temps_simu["T0"]
                ),
                EXCIT=loads_lame_base,
                ETAT_INIT=_F(SIGM=self.null_sigma_field),
            )
        )
        logger.info("<MAC3_CALCUL><LAME>: Finish computing state at T0 (undeformed mesh).")

        # On deforme le maillage
        depl_t1 = snl_damac.getField(
            "DEPL", value=self.coeur.temps_simu["T1"], para="INST", prec=1.0e-08
        )

        self.deform_mesh_inplace(depl_t1)
        logger.info("<MAC3_CALCUL><LAME>: Mesh is deformed.")

        c_prediction = self.evaluate_contacts_prediction(
            _F(EVOL_NOLI=snl_lame_unloaded), loads_lame_thyc, "LAME", "LOAD"
        )

        logger.info(
            "<MAC3_CALCUL><LAME>: Start activation of contacts T0-T0b using prediction (deformed mesh)."
        )
        snl_lame = STAT_NON_LINE(
            **self.snl_lame(
                reuse=snl_lame_unloaded,
                RESULTAT=snl_lame_unloaded,
                NEWTON=_F(
                    MATRICE="TANGENTE",
                    PREDICTION="DEPL_CALCULE",
                    EVOL_NOLI=c_prediction,
                    REAC_ITER=1,
                ),
                CHAM_MATER=self.cham_mater_contact,
                INCREMENT=_F(
                    LIST_INST=self.times_woSubd,
                    PRECISION=1.0e-08,
                    INST_INIT=snl_lame_unloaded.getLastTime(),
                    INST_FIN=self.coeur.temps_simu["T0b"],
                ),
                EXCIT=loads_lame_thyc,
                ETAT_INIT=_F(EVOL_NOLI=snl_lame_unloaded),
            )
        )

        logger.info(
            "<MAC3_CALCUL><LAME>: Finish activation of contacts T0-T0b using prediction (deformed mesh)."
        )

        logger.info("<MAC3_CALCUL><LAME>: Start computing evolution T0b - T4 (deformed mesh)")
        snl_lame = STAT_NON_LINE(
            **self.snl_lame(
                reuse=snl_lame,
                RESULTAT=snl_lame,
                CHAM_MATER=self.cham_mater_contact,
                INCREMENT=_F(
                    LIST_INST=self.times,
                    PRECISION=1.0e-08,
                    INST_INIT=snl_lame.getLastTime(),
                    INST_FIN=self.coeur.temps_simu["T4"],
                ),
                EXCIT=loads_lame_thyc,
                ETAT_INIT=_F(EVOL_NOLI=snl_lame),
            )
        )
        logger.info("<MAC3_CALCUL><LAME>: Finish computing evolution T0b - T4 (deformed mesh)")

        if self.calc_res_def:
            tinit = kwargs.get("tinit")
            tfin = kwargs.get("tfin")
            self.output_resdef(snl_lame, depl_t1, tinit, tfin)
        logger.info("<MAC3_CALCUL><LAME>: Computation done. Mesh is back undeformed.")
        return snl_lame


class Mac3CoeurEtatInitial(Mac3CoeurLame):
    """Compute Initial State"""

    mcfact = "LAME"

    def __init__(self, macro, args):
        """Initialization"""
        self.args_lame = {}
        self.args_defo = {}
        for el in args:
            if el == "ETAT_INITIAL":
                self.args_lame["LAME"] = args[el]
                self.args_defo["DEFORMATION"] = args[el]
            else:
                if el not in ["LAME", "DEFORMATION"]:
                    self.args_lame[el] = args[el]
                    self.args_defo[el] = args[el]
        super().__init__(macro, self.args_lame)
        self.calc_res_def = True

    def _prepare_data(self, **kwargs):
        """Prepare the data for the calculation"""
        self.niv_fluence = self.mcf["NIVE_FLUENCE"]
        assert not self.is_mono
        super()._prepare_data(noresu=True)
        logger.debug("<MAC3_CALCUL><ETAT_INIT>: Prepare Data")

    def _run(self, **kwargs):
        tinit = self.coeur.temps_simu["T0"]
        tfin = self.coeur.temps_simu["T5"]

        logger.info(
            "<MAC3_CALCUL><ETAT_INIT>: Start Initial LAME computation (T0 = %f, T5 = %f)"
            % (tinit, tfin)
        )
        resu_lame = super()._run(tinit=tinit, tfin=tfin)
        logger.info(
            "<MAC3_CALCUL><ETAT_INIT>: End Initial LAME computation (T0 = %f, T5 = %f)"
            % (tinit, tfin)
        )

        logger.info("<MAC3_CALCUL><ETAT_INIT>: Setup deformation computation with initial state.")
        self.defo = Mac3CoeurDeformation(self.macro, self.args_defo, self.res_def)

        logger.info(
            "<MAC3_CALCUL><ETAT_INIT>: Start the deformation computation with initial state."
        )
        resu_def = self.defo.run()
        logger.info(
            "<MAC3_CALCUL><ETAT_INIT>: Finish the deformation computation with initial state."
        )

        return resu_def
