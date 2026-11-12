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
Utilitaires pour CALC_ENDO
"""

from ...Messages import UTMESS
from ...CodeCommands import CALC_TABLE, FORMULE, DEFI_LIST_INST
from ...Behaviours import regu_visc_elas, endo_loca_tc  # , endo_fiss_tc


def get_obs_values(ctrl_resu, name_obs):
    """Get values of a given OBSERVATION

    Args:
        ctrl_resu (*Table*): observation table
        name_obs (str): name of the quantity to extract from the table

    Returns:
        ctrl_obs_values (list): list of obervation table values
    """

    ctrl_obs = CALC_TABLE(
        TABLE=ctrl_resu,
        ACTION=(
            _F(OPERATION="FILTRE", NOM_PARA="NOM_OBSERVATION", VALE_K=name_obs),
            _F(OPERATION="EXTR", NOM_PARA=("INST", "VALE")),
        ),
    )

    ctrl_obs_values = ctrl_obs.EXTR_TABLE().values()["VALE"]

    return ctrl_obs_values


def concatenate_table(table_out, obs_table, t_comp):
    """Create output table for CALC_ENDO

    Args:
        table_out (*Table*): output table of CALC_ENDO
        obs_table (*Table*): observation table
        t_comp (float): physical inst for _obs_table

    Returns:
        obs_table (*Table*): output table of CALC_ENDO
    """

    obs_table = CALC_TABLE(
        TABLE=obs_table,
        ACTION=(
            _F(OPERATION="RENOMME", NOM_PARA=("INST", "INST_VISC")),
            _F(OPERATION="SUPPRIME", NOM_PARA=("NUME_ORDRE")),
        ),
    )

    obs_table = CALC_TABLE(
        reuse=obs_table,
        TABLE=obs_table,
        ACTION=_F(OPERATION="AJOUT_COLONNE", NOM_PARA="INST", VALE=t_comp),
    )

    if table_out:
        table_out = CALC_TABLE(
            reuse=table_out,
            TABLE=table_out,
            ACTION=_F(OPERATION="COMB", TABLE=obs_table, RESTREINT="NON", NOM_PARA="INST"),
        )
        return table_out
    else:
        return obs_table


def get_vari_by_name(bhv, vi_name):
    """
    Return the Vxx name of an internal variable vi_name with respect to the constituive relation bhv

    Args:
        bhv (*Behaviour*): behaviour law
        vi_name (str): name of the internal variable

    Returns:
        num_name (str): number of internal variable

    """
    pos = bhv.loi.get_nom_vari().index(vi_name)
    num = pos + 1
    num_name = "V" + repr(num)
    return num_name


def set_default_observation(kwds):
    """Create default OBSERVATION syntax
    SIGMVISC for ENDO_LOCA_TC and ENDO_FISS_TC
    Viscous stress for REGU_VISC

    Args:
        kwds (*dict*): arguments for CALC_ENDO

    Returns:
        obs_stab_visc (tuple): OBSERVATION syntax for STAT_NON_LINE. Used for evaluation of stabilisation criteria
        crit_stab_visc (list): values of stabilisation criteria
        other_obs (tuple): OBSERVATION syntax for STAT_NON_LINE. NOT used for evaluation of stabilisation criteria

    """

    obs_stab_visc = []
    crit_stab_visc = []
    other_obs = []

    cham_mater = kwds["CHAM_MATER"]
    mat_by_mesh = cham_mater.getMaterialsOnMeshEntities()
    names_mesh_ent = [x[1].getNames() for x in mat_by_mesh]
    num_obs = 0

    for compor in kwds["COMPORTEMENT"]:
        ldc_name = compor["RELATION"]

        if compor["REGU_VISC"] == "OUI" or ldc_name in ["ENDO_LOCA_TC", "ENDO_FISS_TC"]:

            if ldc_name == "ENDO_LOCA_TC":
                ldc = endo_loca_tc
            elif ldc_name == "ENDO_FISS_TC":
                ldc = endo_fiss_tc
            else:
                assert False

            if "GROUP_MA" in compor:
                l_mesh_ent = compor["GROUP_MA"]
                d_mesh_ent = {"GROUP_MA": l_mesh_ent}
            elif "TOUT" in compor:
                l_mesh_ent = [compor["TOUT"]]
                d_mesh_ent = {"TOUT": "OUI"}
            l_ft = []
            mesh_ent_names = " ".join(l_mesh_ent)

            for mesh_ent in l_mesh_ent:
                index_mesh_ent = [names_mesh_ent.index(x) for x in names_mesh_ent if mesh_ent in x]
                assert len(index_mesh_ent) == 1
                mat_on_grp_ma = mat_by_mesh[index_mesh_ent[0]][0][0]
                ft = mat_on_grp_ma.getValueReal(ldc_name, "FT")
                l_ft.append(ft)

            ft_min = min(l_ft)

            if "RESI_REFE_RELA" not in kwds["CONVERGENCE"]:
                UTMESS("F", "CALCENDO_11")
            resi_refe_rela = kwds["CONVERGENCE"]["RESI_REFE_RELA"]

            if compor["REGU_VISC"] == "OUI":

                kvisc_elas = mat_on_grp_ma.getValueReal("VISC_ELAS", "K")
                nbvi_ldc = ldc.loi.get_nb_vari()
                nom_vari_ener_elas = "V%d" % (
                    nbvi_ldc + int(get_vari_by_name(regu_visc_elas, "VISCELAS")[1:])
                )
                f_sigm_visc_elas = FORMULE(
                    NOM_PARA=nom_vari_ener_elas,
                    VALE="(2*k*%s)**0.5" % nom_vari_ener_elas,
                    k=kvisc_elas,
                )

                obs_visc = _F(
                    TITRE="VISCELAS_" + str(num_obs),
                    PAS_OBSE=1,
                    NOM_CHAM="VARI_ELGA",
                    NOM_CMP=nom_vari_ener_elas,
                    EVAL_CMP="FORMULE",
                    FORMULE=f_sigm_visc_elas,
                    EVAL_ELGA="MAX",
                    EVAL_CHAM="MAX",
                    **d_mesh_ent,
                )
                obs_stab_visc.append(obs_visc)
                crit_stab_visc.append(resi_refe_rela * ft_min)
                UTMESS("I", "CALCENDO_5", valk=tuple(["VISCELAS_" + str(num_obs), mesh_ent_names]))

            if ldc_name in ["ENDO_LOCA_TC", "ENDO_FISS_TC"]:
                vari_endotot = get_vari_by_name(ldc, "ENDOTOT")
                obs_endomoy = _F(
                    TITRE="ENDOTOT_" + str(num_obs),
                    PAS_OBSE=1,
                    NOM_CHAM="VARI_ELGA",
                    NOM_CMP=vari_endotot,
                    EVAL_ELGA="MAX",
                    EVAL_CHAM="MOY",
                    **d_mesh_ent,
                )
                other_obs.append(obs_endomoy)

                vari_visc = get_vari_by_name(ldc, "SIGMVISC")
                obs_visc = _F(
                    TITRE="VISCENDO_" + str(num_obs),
                    PAS_OBSE=1,
                    NOM_CHAM="VARI_ELGA",
                    NOM_CMP=vari_visc,
                    EVAL_ELGA="MAX",
                    EVAL_CHAM="MAX",
                    **d_mesh_ent,
                )
                obs_stab_visc.append(obs_visc)
                crit_stab_visc.append(resi_refe_rela * ft_min)

                UTMESS("I", "CALCENDO_5", valk=tuple(["ENDOTOT_" + str(num_obs), mesh_ent_names]))
                UTMESS("I", "CALCENDO_5", valk=tuple(["VISCENDO_" + str(num_obs), mesh_ent_names]))

                num_obs += num_obs

    return tuple(obs_stab_visc), crit_stab_visc, tuple(other_obs)


def set_default_listinst(_kwds, tau, l_fict_endo):
    """Create DEFI_LIST_INST with default parameters

    Args:
        kwds (*dict*): arguments for CALC_ENDO
        tau (float): viscosity time
        l_fict_endo (list): list of timesteps for a load sequence

    Returns:
        visc_list_inst (*list_inst*): list_inst used for a load sequence (ramp and stabilisation)

    """

    l_echec = [_F(EVENEMENT="ERREUR", ACTION="DECOUPE", SUBD_PAS=3, SUBD_PAS_MINI=tau / 3**15)]
    l_adaptation = [_F(EVENEMENT="TOUT_INST", MODE_CALCUL_TPLUS="FIXE", PCENT_AUGM=75)]

    for compor in _kwds["COMPORTEMENT"]:
        ldc_name = compor["RELATION"]
        if ldc_name in ["ENDO_LOCA_TC", "ENDO_FISS_TC"]:

            if ldc_name == "ENDO_LOCA_TC":
                ldc = endo_loca_tc
            elif ldc_name == "ENDO_FISS_TC":
                ldc = endo_fiss_tc

            if "GROUP_MA" in compor:
                d_mesh_ent = {"GROUP_MA": compor["GROUP_MA"]}
            elif "TOUT" in compor:
                d_mesh_ent = {}

            nom_vari = get_vari_by_name(ldc, "HISTTRAC")

            l_echec.append(
                _F(
                    EVENEMENT="DELTA_GRANDEUR",
                    VALE_REF=1.5 * 0.1,
                    NOM_CHAM="VARI_ELGA",
                    NOM_CMP=nom_vari,
                    ACTION="DECOUPE",
                    SUBD_PAS=3,
                    SUBD_PAS_MINI=tau / 3**15,
                    **d_mesh_ent,
                )
            )
            l_adaptation.append(
                _F(
                    EVENEMENT="TOUT_INST",
                    MODE_CALCUL_TPLUS="DELTA_GRANDEUR",
                    VALE_REF=0.1,
                    NOM_CHAM="VARI_ELGA",
                    NOM_CMP=nom_vari,
                    **d_mesh_ent,
                )
            )

    visc_list_inst = DEFI_LIST_INST(
        MODELE=_kwds["MODELE"],
        METHODE="AUTO",
        DEFI_LIST=_F(VALE=l_fict_endo),
        ECHEC=l_echec,
        ADAPTATION=l_adaptation,
    )

    return visc_list_inst
