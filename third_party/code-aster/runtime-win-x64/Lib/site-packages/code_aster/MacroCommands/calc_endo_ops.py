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

from ..Utilities import no_new_attributes, logger
from ..Messages import UTMESS, MasquerAlarme, RetablirAlarme
from ..Objects import (
    EntityType,
    ExternalVariableTraits,
    ListOfFloats,
    TimesList,
    NonLinearResultDict,
)
from libaster import MechanicalLoadFunction, MechanicalDirichletBC, Function, Formula, Function2D

from ..CodeCommands import (
    DEFI_FONCTION,
    STAT_NON_LINE,
    RECU_TABLE,
    CREA_CHAMP,
    CREA_RESU,
    AFFE_MATERIAU,
    DEFI_LIST_REEL,
)
from .Utils.calc_endo_utils import (
    get_obs_values,
    set_default_observation,
    concatenate_table,
    set_default_listinst,
)

from numpy import isclose, where, array


class CalcEndoLoad:

    charge = type_charge = fonc_mult = None
    has_time_dep = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, args):
        """Initialization of a load

        Args:
            args (dict): User's keywords for EXCIT in CALC_ENDO
        """

        self.charge = args["CHARGE"]
        self.type_charge = args["TYPE_CHARGE"]
        if "FONC_MULT" in args:
            self.fonc_mult = args["FONC_MULT"]

    def check_time_dependency(self):
        """Check if the load is time dependent.
        Raise error message if time dependency is calculated by AFFE_CHAR_MECA_F
        """
        if self.fonc_mult:
            self.has_time_dep = True
        elif isinstance(self.charge, MechanicalLoadFunction) or isinstance(
            self.charge, MechanicalDirichletBC
        ):
            for dependency in self.charge.getDependencies():
                if isinstance(dependency, Function):
                    param_function = dependency.Parametres()["NOM_PARA"]
                    if param_function == "INST":
                        UTMESS("F", "CALCENDO_4")
                if isinstance(dependency, Formula):
                    param_function = dependency.Parametres()["NOM_PARA"]
                    if "INST" in param_function:
                        UTMESS("F", "CALCENDO_4")
                if isinstance(dependency, Function2D):
                    param_nappe = dependency.Parametres()
                    for param_function in param_nappe:
                        if (
                            "INST" in param_function["NOM_PARA"]
                            or "INST" in param_function["NOM_PARA_FONC"]
                        ):
                            UTMESS("F", "CALCENDO_4")

    def eval(self, t_init, t_comp, nume_ordre, is_stab_seq, t_init_ramp):
        """Create syntax for EXCIT in STAT_NON_LINE for a given load sequence

        Args:
            t_init (float): initial physical time of current load sequence
            t_comp (float): end physical time of current load sequence
            nume_ordre (int): local value of NUME_ORDRE
            is_stab_seq (bool): True if stabilisation of current load sequence
            t_init_ramp (float): initial time of the ramp

        Returns:
            excit_snl (dict): Arguments for EXCIT

        """

        excit_snl = {}
        excit_snl["CHARGE"] = self.charge
        excit_snl["TYPE_CHARGE"] = self.type_charge

        ##Chargements autres que "DIDI" et fonction du temps (via FONC_MULT)
        if self.type_charge != "DIDI" and self.has_time_dep:
            ramp_load = DEFI_FONCTION(
                NOM_PARA="INST",
                ABSCISSE=(t_init_ramp, 0),
                ORDONNEE=(self.fonc_mult(t_init), self.fonc_mult(t_comp)),
                PROL_DROITE="CONSTANT",
            )
            excit_snl["FONC_MULT"] = ramp_load

        ##Chargement de type "DIDI" et pas de dépendance au temps
        ##Le chargement est fixé à zero après le premier STAT_NON_LINE
        elif self.type_charge == "DIDI" and not self.has_time_dep:
            if nume_ordre > 0 or is_stab_seq:
                ramp_load = DEFI_FONCTION(
                    NOM_PARA="INST",
                    ABSCISSE=(t_init_ramp, 0),
                    ORDONNEE=(0, 0),
                    PROL_DROITE="CONSTANT",
                )
                excit_snl["FONC_MULT"] = ramp_load

        ##Chargement de type "DIDI" et fonction du temps (via FONC_MULT)
        elif self.type_charge == "DIDI" and self.has_time_dep:
            ##Chargement à zero en phase de stabilisation
            if is_stab_seq:
                ramp_load = DEFI_FONCTION(
                    NOM_PARA="INST",
                    ABSCISSE=(t_init_ramp, 0),
                    ORDONNEE=(0, 0),
                    PROL_DROITE="CONSTANT",
                )
            ##Delta de chargement pendant la rampe
            else:
                ramp_load = DEFI_FONCTION(
                    NOM_PARA="INST",
                    ABSCISSE=(t_init_ramp, 0),
                    ORDONNEE=(0, self.fonc_mult(t_comp) - self.fonc_mult(t_init)),
                    PROL_DROITE="CONSTANT",
                )
            excit_snl["FONC_MULT"] = ramp_load

        return excit_snl


class CalcEndoVarc:

    varc_on_mesh = None
    name = has_time_dep = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, varc_on_mesh):
        """Initialisation of an external state variable"""

        self.name = ExternalVariableTraits.getExternVarTypeStr(varc_on_mesh[0].getType())
        self.varc_on_mesh = varc_on_mesh

    def check_time_dependency(self):
        """Check if the external state variable is time dependent."""

        field = self.varc_on_mesh[0].getField()
        transient = self.varc_on_mesh[0].getTransientResult()
        assert field or transient

        if field:
            UTMESS("I", "CALCENDO_13", valk=(self.name, "indépendante du temps"))

        if transient:
            self.has_time_dep = True
            UTMESS("I", "CALCENDO_13", valk=(self.name, "fonction du temps"))

    def eval(self, t_init, t_comp, model, t_init_ramp, t_fin):
        """Create syntax for the next AFFE_VARC

        Args:
            t_init (float): initial physical time of current load sequence
            t_comp (float): end physical time of current load sequence
            model (*Model*): model
            t_init_ramp (float): initial time of ramp
            t_fin (float): end time of stabilisation sequence

        Returns:
            dict_varc : input for AFFE_VARC in AFFE_MATERIAU

        """

        dict_varc = {}
        extevarc = self.varc_on_mesh[0]
        meshvarc = self.varc_on_mesh[1]

        dict_varc["NOM_VARC"] = self.name

        if meshvarc.getType() == EntityType.GroupOfCellsType:
            dict_varc["GROUP_MA"] = meshvarc.getNames()
        else:
            dict_varc["TOUT"] = "OUI"

        if extevarc.isSetRefe():
            dict_varc["VALE_REF"] = extevarc.getReferenceValue()

        field = extevarc.getField()
        evol = extevarc.getEvolutionParameter()

        if field:
            dict_varc["CHAM_GD"] = field
        if evol:
            transient = evol.getTransientResult()

            ##FONC_INST interdit
            if evol.getTimeFormula() or evol.getTimeFunction():
                UTMESS("F", "CALCENDO_7")

            field_init = transient.interpolateField(
                self.name, t_init, left=evol.getLeftExtension(), right=evol.getRightExtension()
            )
            field_comp = transient.interpolateField(
                self.name, t_comp, left=evol.getLeftExtension(), right=evol.getRightExtension()
            )

            ramp_varc = CREA_RESU(
                OPERATION="AFFE",
                TYPE_RESU=transient.getType(),
                AFFE=(
                    _F(
                        NOM_CHAM=evol.getFieldName(),
                        CHAM_GD=field_init,
                        INST=t_init_ramp,
                        MODELE=model,
                    ),
                    _F(NOM_CHAM=evol.getFieldName(), CHAM_GD=field_comp, INST=0, MODELE=model),
                    _F(NOM_CHAM=evol.getFieldName(), CHAM_GD=field_comp, INST=t_fin, MODELE=model),
                ),
            )
            dict_varc["EVOL"] = ramp_varc

        return dict_varc


class CalcEndoInitState:
    depl = sief = vari = strx = None
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, depl, sief, vari, strx):

        self.set_init_state(depl, sief, vari, strx)

    def set_init_state(self, depl, sief, vari, strx):
        """
        Set all fields for init state

        Args :
            depl_init (*FieldOnNodes*): depl field initial state
            sief_init (*FieldOnCells*): stress field initial state
            vari_init (*FieldOnCells*): internal variable field initial state
            strx_init (*FieldOnCells*): initial state for a few structural elements

        """

        self.depl = depl
        self.sief = sief
        self.vari = vari
        self.strx = strx

    def set_depl(self, depl):
        """Set depl initial field"""
        self.depl = depl

    def set_sief(self, sief):
        """Set sief initial field"""
        self.sief = sief

    def set_vari(self, vari):
        """Set vari initial field"""
        self.vari = vari

    def set_strx(self, strx):
        """Set strx initial field"""
        self.strx = strx

    def check_etat_init(self):
        """Check if ETAT_INIT is necessary in STAT_NON_LINE

        Returns :
            etat_init (bool): True if ETAT_INIT has to be used in STAT_NON_LINE
        """
        l_etat_init = [self.depl, self.sief, self.vari, self.strx]
        etat_init = sum(x is not None for x in l_etat_init) > 0

        return etat_init


class CalcEndo:
    kwds = None
    tau = visc_list_inst = user_list_inst = None
    t_init_ramp = dt_stab = t_fin = None
    loads = varc = None
    crit_stab_visc = stab = arret = None
    obs_stab_visc = other_obs = None
    arch = arch_visc = None
    resu = resu_visc = tab_out = None

    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, args):
        """Initialization and definition of main arguments.

        Args:
            result (dict): User's keywords.
        """

        self.kwds = args.copy()
        if "OBSERVATION" not in args:
            self.kwds["OBSERVATION"] = ()

        self.visc_list_inst = self.kwds["ENDO_VISC"]["LIST_INST"]
        self.crit_stab_visc = self.kwds["ENDO_VISC"]["PREC_STAB"]
        self.arret = self.kwds["ENDO_VISC"]["ARRET"]
        self.resu_visc = NonLinearResultDict("resu_visc")
        if "ARCHIVAGE_VISC" in self.kwds:
            self.arch_visc = self.kwds["ARCHIVAGE_VISC"]

        if ("ARCHIVAGE_VISC" in self.kwds and "RESULTAT" not in self.kwds["ENDO_VISC"]) or (
            "ARCHIVAGE_VISC" not in self.kwds and "RESULTAT" in self.kwds["ENDO_VISC"]
        ):
            UTMESS("F", "CALCENDO_22")

        if self.crit_stab_visc:
            if len(self.kwds["ENDO_VISC"]["PREC_STAB"]) != len(
                self.kwds["ENDO_VISC"]["OBSERVATION"]
            ):
                UTMESS("F", "CALCENDO_10")

        self.check_consistency()
        self.set_observation()
        self.set_user_list_inst()
        self.set_endo_list_inst()
        self.sort_loads()
        self.sort_varc()

    def set_observation(self):
        """Initialisation of OBSERVATION keyword for STAT_NON_LINE"""

        ##Observations et critères de stabilisation donnés par l'utilisateur
        if self.crit_stab_visc:
            self.obs_stab_visc = ()
            self.other_obs = ()
            titre_obs_visc = self.kwds["ENDO_VISC"]["OBSERVATION"]
            for titre in titre_obs_visc:
                l_obs = [x for x in self.kwds["OBSERVATION"] if titre == x["TITRE"]]
                if len(l_obs) != 1:
                    UTMESS("F", "CALCENDO_3", valk=(titre))
                self.obs_stab_visc = self.obs_stab_visc + tuple(l_obs)
            self.other_obs = tuple(
                [x for x in self.kwds["OBSERVATION"] if x["TITRE"] not in titre_obs_visc]
            )

            ##Si l'utilisateur n'a pas donné en entrée une observation appelée VISCELAS ou VISCENDO
            ##On rajoute les observations par défaut
            if "VISCELAS" not in titre_obs_visc and "VISCENDO" not in titre_obs_visc:
                (defaut_obs_stab_visc, defaut_crit_stab_visc, default_other_obs) = (
                    set_default_observation(self.kwds)
                )
                self.obs_stab_visc = self.obs_stab_visc + defaut_obs_stab_visc
                self.crit_stab_visc = self.crit_stab_visc + defaut_crit_stab_visc
                self.other_obs = self.other_obs + default_other_obs
        else:
            self.obs_stab_visc, self.crit_stab_visc, self.other_obs = set_default_observation(
                self.kwds
            )

    def check_consistency(self):
        """Check consistency of viscosity material parameters."""

        cham_mater = self.kwds["CHAM_MATER"]

        tau_name = {
            "ENDO_LOCA_TC": "TAU_REGU_VISC",
            "ENDO_FISS_TC": "TAU_REGU_VISC",
            "VISC_ELAS": "TAU",
        }
        self.tau = 0.0

        for mater in cham_mater.getVectorOfMaterial():
            for ldc in tau_name:
                if ldc in mater.getMaterialNames():
                    tau = mater.getValueReal(ldc, tau_name[ldc])
                    if abs(tau - 1.0) > 1e-12 and abs(tau) > 1e-12:
                        UTMESS("F", "CALCENDO_1")
                    if tau > self.tau:
                        self.tau = tau

        UTMESS("I", "CALCENDO_14", valr=(self.tau))

        if not self.tau > 0.0:
            UTMESS("F", "CALCENDO_2")

    def set_user_list_inst(self):
        """Create list of physical load sequences and list of physical timestep for archivage"""

        full_user_list = self.kwds["INCREMENT"]["LIST_INST"].getValues()
        self.user_list_inst = full_user_list

        if "NUME_INST_FIN" in self.kwds["INCREMENT"] or "INST_FIN" in self.kwds["INCREMENT"]:
            if "NUME_INST_FIN" in self.kwds["INCREMENT"]:
                nume_inst_fin = self.kwds["INCREMENT"]["NUME_INST_FIN"]
            else:
                tol = self.kwds["INCREMENT"]["PRECISION"]
                inst_fin = self.kwds["INCREMENT"]["INST_FIN"]
                nume_inst_fin = where(isclose(array(full_user_list), inst_fin, rtol=tol))[0][0]
            self.user_list_inst = self.user_list_inst[: nume_inst_fin + 1]
        if "NUME_INST_INIT" in self.kwds["INCREMENT"] or "INST_INIT" in self.kwds["INCREMENT"]:
            if "NUME_INST_INIT" in self.kwds["INCREMENT"]:
                nume_inst_init = self.kwds["INCREMENT"]["NUME_INST_INIT"]
            else:
                tol = self.kwds["INCREMENT"]["PRECISION"]
                inst_init = self.kwds["INCREMENT"]["INST_INIT"]
                nume_inst_init = where(isclose(array(full_user_list), inst_init, rtol=tol))[0][0]
            self.user_list_inst = self.user_list_inst[nume_inst_init:]

        UTMESS("I", "CALCENDO_15", valk=(str(self.user_list_inst)))

        if "PAS_ARCH" in self.kwds["ARCHIVAGE"]:
            self.arch = self.user_list_inst[:: self.kwds["ARCHIVAGE"]["PAS_ARCH"]]
        if "INST" in self.kwds["ARCHIVAGE"]:
            self.arch = self.kwds["ARCHIVAGE"]["INST"]
        if "LIST_INST" in self.kwds["ARCHIVAGE"]:
            self.arch = self.kwds["ARCHIVAGE"]["LIST_INST"].getValues()

    def set_endo_list_inst(self):
        """Create list of timestep for a load sequence (ramp and stabilisation)"""

        values_visc = self.visc_list_inst.getValues()
        if len(values_visc) != 3:
            UTMESS("F", "CALCENDO_9")

        self.t_init_ramp = -self.tau * values_visc[0]

        if abs(self.t_init_ramp) > self.tau:
            rampe = [self.t_init_ramp, self.t_init_ramp + self.tau, 0.0]
        else:
            rampe = [self.t_init_ramp, 0.0]

        self.dt_stab = self.tau * abs(values_visc[1] - values_visc[0])
        nb_stab_max = int(
            abs(values_visc[2] - values_visc[0]) / abs(values_visc[1] - values_visc[0])
        )

        l_fict_endo = rampe + [
            val
            for i in range(nb_stab_max)
            for val in [i * self.dt_stab + self.tau, i * self.dt_stab + self.dt_stab]
        ]
        self.t_fin = l_fict_endo[-1]

        UTMESS("I", "CALCENDO_16", valk=(str(l_fict_endo)))

        if isinstance(self.kwds["ENDO_VISC"]["LIST_INST"], ListOfFloats):
            self.visc_list_inst = set_default_listinst(self.kwds, self.tau, l_fict_endo)
        elif isinstance(self.kwds["ENDO_VISC"]["LIST_INST"], TimesList):
            self.visc_list_inst = self.kwds["ENDO_VISC"]["LIST_INST"].copy()
            self.visc_list_inst.setValues(l_fict_endo)

    def sort_loads(self):
        """Sort loads in two : time dependant loads and other loads"""

        self.loads = []
        nb_time_dep = 0
        nb_fixed = 0
        for excit in self.kwds["EXCIT"]:
            load = CalcEndoLoad(excit)
            load.check_time_dependency()
            self.loads.append(load)
            if load.has_time_dep:
                nb_time_dep += 1
            else:
                nb_fixed += 1

        UTMESS("I", "CALCENDO_17", vali=(nb_time_dep, nb_fixed))

    def sort_varc(self):
        """Sort external state variables in two : time dependant varc and other varc"""

        self.varc = []
        user_mat = self.kwds["CHAM_MATER"]

        if user_mat.hasExternalStateVariable():
            for varc_on_mesh in user_mat.getExtStateVariablesOnMeshEntities():
                calcendo_varc = CalcEndoVarc(varc_on_mesh)
                calcendo_varc.check_time_dependency()
                self.varc.append(calcendo_varc)

    def init_sequence(self, nume_ordre, t_init, t_comp):
        """Initialisation of a new load sequence

        Args:
            nume_ordre (int): nume_ordre of last computed load sequence
            t_init (float): initial time of last computed load sequence
            t_comp (float): end time of new load sequence

        Returns:
            nume_ordre (int): nume_ordre of new load sequence
            t_init (float): initial time of new load sequence

        """

        if nume_ordre is None:
            nume_ordre = 0
            t_init = self.user_list_inst[nume_ordre]
        else:
            nume_ordre += 1
            if t_init is None:
                t_init = self.user_list_inst[nume_ordre]
        self.stab = False

        UTMESS("I", "CALCENDO_18", vali=(nume_ordre), valr=(t_init, t_comp))

        return nume_ordre, t_init

    def set_init_state(self):
        """Prepare initial state of non linear computation

        Returns:
            nume_ordre (int): nume_ordre of new load sequence
            t_init (float): initial time of new load sequence
            init_state (*CalcEndoInitState*): initial state

        """

        nume_ordre = t_init = depl_init = sief_init = vari_init = strx_init = None

        init_state = CalcEndoInitState(depl_init, sief_init, vari_init, strx_init)

        if "ETAT_INIT" in self.kwds:
            if "EVOL_NOLI" in self.kwds["ETAT_INIT"]:
                self.resu = self.kwds["ETAT_INIT"]["EVOL_NOLI"]

                if (
                    "NUME_ORDRE" in self.kwds["ETAT_INIT"]
                    or "INST" in self.kwds["ETAT_INIT"]
                    or "NUME_DIDI" in self.kwds["ETAT_INIT"]
                ):
                    UTMESS("F", "CALCENDO_8")

                if (
                    "NUME_ORDRE" not in self.kwds["ETAT_INIT"]
                    and "INST" not in self.kwds["ETAT_INIT"]
                ):
                    idx = self.resu.getAccessParameters()["NUME_ORDRE"][-1]
                    t_init = self.resu.getAccessParameters()["INST"][-1]
                    depl_init = self.resu.getField("DEPL", idx)
                    sief_init = self.resu.getField("SIEF_ELGA", idx)
                    vari_init = self.resu.getField("VARI_ELGA", idx)
                    if "STRX_ELGA" in self.resu.getFieldsNames():
                        strx_init = self.resu.getField("STRX_ELGA", idx)
                    else:
                        strx_init = None
                    init_state.set_init_state(depl_init, sief_init, vari_init, strx_init)
                    index_init = where(isclose(array(self.user_list_inst), t_init))[0][0]
                    self.user_list_inst = self.user_list_inst[index_init:]
            else:
                if "DEPL" in self.kwds["ETAT_INIT"]:
                    depl_init = self.kwds["ETAT_INIT"]["DEPL"]
                    init_state.set_depl(depl_init)
                if "SIGM" in self.kwds["ETAT_INIT"]:
                    sief_init = self.kwds["ETAT_INIT"]["SIGM"]
                    init_state.set_sief(sief_init)
                if "VARI" in self.kwds["ETAT_INIT"]:
                    vari_init = self.kwds["ETAT_INIT"]["VARI"]
                    init_state.set_vari(vari_init)
                if "STRX" in self.kwds["ETAT_INIT"]:
                    strx_init = self.kwds["ETAT_INIT"]["STRX"]
                    init_state.set_strx(strx_init)

        return nume_ordre, t_init, init_state

    def eval_loads(self, t_init, t_comp, nume_ordre, is_stab_seq):
        """Create syntax for EXCIT in STAT_NON_LINE for a given load sequence

        Args:
            t_init (float): initial physical time of current load sequence
            t_comp (float): end physical time of current load sequence
            nume_ordre (int): local value of NUME_ORDRE
            is_stab_seq (bool): True if stabilisation of current load sequence

        Returns:
            visc_excit (list): Arguments for EXCIT in the next STAT_NON_LINE

        """

        visc_excit = []
        for load in self.loads:
            excit = load.eval(t_init, t_comp, nume_ordre, is_stab_seq, self.t_init_ramp)
            visc_excit.append(_F(excit))

        return visc_excit

    def eval_varc(self, t_init, t_comp):
        """Evaluate external state variables for a given load sequence

        Args:
            t_init (float): initial time of current load sequence
            t_comp (float): end time of current load sequence

        Returns:
            visc_mat_field (*MaterialField*): material field with time dependant varc evaluated at _t_init and _t_comp

        """

        l_affe_varc = []

        for endo_varc in self.varc:
            affe_varc = endo_varc.eval(
                t_init, t_comp, self.kwds["MODELE"], self.t_init_ramp, self.t_fin
            )
            l_affe_varc.append(_F(affe_varc))
        MasquerAlarme("MATERIAL2_61")
        visc_mat_field = AFFE_MATERIAU(
            MODELE=self.kwds["MODELE"], CHAM_MATER=self.kwds["CHAM_MATER"], AFFE_VARC=l_affe_varc
        )
        RetablirAlarme("MATERIAL2_61")

        return visc_mat_field

    def eval_stab_crit(self, evol_endo):
        """Evaluate stabilisation criteria at the last timestep of a given result

        Args:
            evol_endo (*evol_noli*): result of the current load sequence

        """

        current_inst = evol_endo.getAccessParameters()["INST"][-1]
        UTMESS("I", "CALCENDO_19", valr=(current_inst))
        ctrl_resu = RECU_TABLE(CO=evol_endo, NOM_TABLE="OBSERVATION")

        for obs in self.other_obs:
            if ("EVAL_CHAM" in obs) and (obs["EVAL_CHAM"] != "VALE"):
                name_obs = obs["TITRE"]
                v_obs = get_obs_values(ctrl_resu, name_obs)
                UTMESS("I", "CALCENDO_20", valk=(name_obs), valr=(v_obs[-1], v_obs[-1] - v_obs[0]))

        crit = False
        for num_obs, obs_visc in enumerate(self.obs_stab_visc):
            name_obs_visc = obs_visc["TITRE"]
            v_obs_visc = get_obs_values(ctrl_resu, name_obs_visc)
            crit += v_obs_visc[-1] < self.crit_stab_visc[num_obs]
            ratio_v_obs = v_obs_visc[-1] / self.crit_stab_visc[num_obs]
            UTMESS("I", "CALCENDO_21", valk=(name_obs_visc), valr=(v_obs_visc[-1], ratio_v_obs))

        self.stab = crit == len(self.obs_stab_visc)

        if self.arret == "NON" and current_inst == self.t_fin:
            self.stab = True
            UTMESS("A", "CALCENDO_6")

    def compute_ramp(self, state_init, visc_mat_field, visc_excit):
        """Non linear computation during the ramp part of the load sequence

        Args:
            state_init (*CalcEndoInitState*): initial state for ramp non linear computation
            visc_mat_field (*MaterialField*) : material field with time dependant varc evaluated for load sequence
            visc_excit (list): Arguments for EXCIT in STAT_NON_LINE

        Returns:
            evol_endo (*evol_noli*): result of the current load sequence (ramp only)

        """

        params_snl = {
            key: item
            for key, item in self.kwds.items()
            if key
            not in [
                "ENDO_VISC",
                "EXCIT",
                "INCREMENT",
                "ARCHIVAGE",
                "ARCHIVAGE_VISC",
                "ETAT_INIT",
                "OBSERVATION",
                "CHAM_MATER",
                "reuse",
            ]
        }

        params_snl["CHAM_MATER"] = visc_mat_field

        if ("ETAT_INIT" in self.kwds and "EVOL_NOLI" in self.kwds["ETAT_INIT"]) or (
            state_init.check_etat_init()
        ):
            l_ETAT_INIT = _F(
                DEPL=state_init.depl,
                SIGM=state_init.sief,
                VARI=state_init.vari,
                STRX=state_init.strx,
            )
        else:
            l_ETAT_INIT = []

        params_snl["ETAT_INIT"] = l_ETAT_INIT
        params_snl["INCREMENT"] = _F(LIST_INST=self.visc_list_inst, INST_FIN=0.0, NUME_INST_INIT=0)
        params_snl["OBSERVATION"] = self.obs_stab_visc + self.other_obs
        params_snl["EXCIT"] = visc_excit
        if self.arch_visc:
            params_snl["ARCHIVAGE"] = self.arch_visc
        else:
            params_snl["ARCHIVAGE"] = _F(
                LIST_INST=DEFI_LIST_REEL(VALE=self.visc_list_inst.getValues())
            )

        evol_endo = STAT_NON_LINE(**params_snl)
        self.eval_stab_crit(evol_endo)

        return evol_endo

    def is_stab(self):
        """Return current state of stabilisation sequence

        Returns:
            stab(bool): True if stabilisation is achieved, else False
        """

        return self.stab

    def compute_stab(self, evol_endo, visc_mat_field, visc_excit):
        """Non linear computation of one stabilisation sequence

        Args:
            evol_endo (*evol_noli*): result of the current load sequence
            visc_mat_field (*MaterialField*) : material field with time dependant varc evaluated for load sequence
            visc_excit (list): Arguments for EXCIT in STAT_NON_LINE

        Returns:
            evol_endo (*evol_noli*): result of the current load sequence (ramp and stab)

        """
        current_inst = evol_endo.getAccessParameters()["INST"][-1]
        next_inst = current_inst + self.dt_stab

        params_snl = {
            key: item
            for key, item in self.kwds.items()
            if key
            not in [
                "ENDO_VISC",
                "EXCIT",
                "INCREMENT",
                "ARCHIVAGE",
                "ARCHIVAGE_VISC",
                "ETAT_INIT",
                "OBSERVATION",
                "CHAM_MATER",
                "reuse",
            ]
        }

        params_snl["CHAM_MATER"] = visc_mat_field
        params_snl["ETAT_INIT"] = _F(EVOL_NOLI=evol_endo)
        params_snl["INCREMENT"] = _F(LIST_INST=self.visc_list_inst, INST_FIN=next_inst)
        params_snl["OBSERVATION"] = self.obs_stab_visc + self.other_obs

        params_snl["EXCIT"] = visc_excit
        if self.arch_visc:
            params_snl["ARCHIVAGE"] = self.arch_visc
        else:
            params_snl["ARCHIVAGE"] = _F(
                LIST_INST=DEFI_LIST_REEL(VALE=self.visc_list_inst.getValues())
            )
        evol_endo = STAT_NON_LINE(reuse=evol_endo, **params_snl)

        self.eval_stab_crit(evol_endo)

        return evol_endo

    def arch_resu(self, evol_endo, t_comp, state_init):
        """Save results for output

        Args:
            evol_endo (*evol_noli*): result of the current load sequence
            t_comp (float): physical time at the end of current load sequence
            state_init (CalcEndoInitState): Initial state for next STAT_NON_LINE

        Returns:
            t_init (float): reset _t_init to None
        """

        nume = evol_endo.getAccessParameters()["NUME_ORDRE"][-1]
        depl_arch = CREA_CHAMP(
            TYPE_CHAM="NOEU_DEPL_R",
            OPERATION="EXTR",
            NOM_CHAM="DEPL",
            RESULTAT=evol_endo,
            NUME_ORDRE=nume,
        )
        sief_arch = CREA_CHAMP(
            TYPE_CHAM="ELGA_SIEF_R",
            OPERATION="EXTR",
            NOM_CHAM="SIEF_ELGA",
            RESULTAT=evol_endo,
            NUME_ORDRE=nume,
        )
        vari_arch = CREA_CHAMP(
            TYPE_CHAM="ELGA_VARI_R",
            OPERATION="EXTR",
            NOM_CHAM="VARI_ELGA",
            RESULTAT=evol_endo,
            NUME_ORDRE=nume,
        )

        if "STRX_ELGA" in evol_endo.getFieldsNames():
            strx_arch = CREA_CHAMP(
                TYPE_CHAM="ELGA_STRX_R",
                OPERATION="EXTR",
                NOM_CHAM="STRX_ELGA",
                RESULTAT=evol_endo,
                NUME_ORDRE=nume,
            )
        else:
            strx_arch = None

        ctrl_obs = RECU_TABLE(CO=evol_endo, NOM_TABLE="OBSERVATION")
        self.tab_out = concatenate_table(self.tab_out, ctrl_obs, t_comp)

        arch_t_comp = (t_comp == self.user_list_inst[-1]) or (t_comp in self.arch)
        if arch_t_comp:
            d_affe = {"MODELE": self.kwds["MODELE"], "CHAM_MATER": self.kwds["CHAM_MATER"]}
            if "CARA_ELEM" in self.kwds:
                d_affe["CARA_ELEM"] = self.kwds["CARA_ELEM"]

            l_affe = (
                _F(NOM_CHAM="DEPL", CHAM_GD=depl_arch, INST=t_comp, **d_affe),
                _F(NOM_CHAM="SIEF_ELGA", CHAM_GD=sief_arch, INST=t_comp, **d_affe),
                _F(NOM_CHAM="VARI_ELGA", CHAM_GD=vari_arch, INST=t_comp, **d_affe),
            )

            if strx_arch:
                l_affe += _F(NOM_CHAM="STRX_ELGA", CHAM_GD=strx_arch, INST=t_comp, **d_affe)

            self.resu = CREA_RESU(
                reuse=self.resu,
                OPERATION="AFFE",
                TYPE_RESU="EVOL_NOLI",
                AFFE=l_affe,
                COMPORTEMENT=self.kwds["COMPORTEMENT"],
            )

        if self.arch_visc:
            if len(self.resu_visc.keys()) > 0:
                last_nume_arch = sorted(self.resu_visc.keys())[-1]
                nume_ordre_arch = int(int(last_nume_arch[5:]) + 1)
            else:
                nume_ordre_arch = 1
            self.resu_visc["VISC_" + str(nume_ordre_arch)] = evol_endo

        ##Initial state for next STAT_NON_LINE
        state_init.set_init_state(depl_arch, sief_arch, vari_arch, strx_arch)

        return None


def calc_endo_ops(self, **args):
    """Execute the command.

    Arguments:
        **args (dict): User's keywords.

    Returns:
        calc_endo.resu (*evol_noli*): Non linear result (physical time)
        calc_endo.tab_out (*Table*): Observation table
        calc_endo.resu_visc (list): List of evol_noli for fictive time discretisation. Optionnal.

    """

    calc_endo = CalcEndo(args)

    nume_ordre, t_init, state_init = calc_endo.set_init_state()

    for t_comp in calc_endo.user_list_inst[1:]:
        nume_ordre, t_init = calc_endo.init_sequence(nume_ordre, t_init, t_comp)
        visc_excit = calc_endo.eval_loads(t_init, t_comp, nume_ordre, False)
        visc_mat_field = calc_endo.eval_varc(t_init, t_comp)

        evol_endo = calc_endo.compute_ramp(state_init, visc_mat_field, visc_excit)

        if not calc_endo.is_stab():
            visc_excit = calc_endo.eval_loads(t_init, t_comp, nume_ordre, True)

        while not calc_endo.is_stab():
            evol_endo = calc_endo.compute_stab(evol_endo, visc_mat_field, visc_excit)

        t_init = calc_endo.arch_resu(evol_endo, t_comp, state_init)

    if "TABLE" in args["ENDO_VISC"]:
        self.register_result(calc_endo.tab_out, args["ENDO_VISC"]["TABLE"])
    if calc_endo.arch_visc:
        self.register_result(calc_endo.resu_visc, args["ENDO_VISC"]["RESULTAT"])

    return calc_endo.resu
