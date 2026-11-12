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


from ...Cata.Syntax import _F
from ...Objects import PhysicalProblem, FieldOnCellsReal, FieldOnNodesReal
from ...CodeCommands import CREA_RESU
from ...Messages import UTMESS
from ...Utilities import logger
from .mac3coeur_ac_permute import MACRO_AC_PERMUTE
from .mac3coeur_coeur import CoeurFactory


def perm_mac3coeur_ops(self, **args):
    """Corps principal de la macro pour la permutation des AC dans MAC3COEUR"""

    type_core_start = args.get("TYPE_COEUR_N")
    type_core_perm = args.get("TYPE_COEUR_NP1")
    sz_row_start = args.get("NB_ASSEMBLAGE_N")
    sz_row_perm = args.get("NB_ASSEMBLAGE_NP1")

    assert bool(sz_row_start) == type_core_start.startswith("LIGNE")
    assert bool(sz_row_perm) == type_core_perm.startswith("LIGNE")

    datamac_start = args.get("TABLE_N")
    datamac_perm = args.get("TABLE_NP1")

    list_resu_start = args.get("RESU_N")
    assert len(datamac_start) == len(list_resu_start)

    core_perm = CoeurFactory.build(type_core_perm, datamac_perm, sz_row_perm)

    mesh_perm_user = args.get("MAILLAGE_NP1")
    mesh_perm = core_perm.affectation_maillage(mesh_perm_user)
    model_perm = core_perm.affectation_modele(mesh_perm)
    core_perm.init_from_mesh(mesh_perm)
    gfibre_perm = core_perm.definition_geom_fibre()
    caraelem_perm = core_perm.definition_cara_coeur(model_perm, gfibre_perm)

    fluence_level = 0.0
    timeline_perm = core_perm.definition_time(fluence_level)
    fluence_perm = core_perm.definition_fluence(fluence_level, mesh_perm, 0.0)
    tempfield_perm = core_perm.definition_champ_temperature(mesh_perm)
    material_perm = core_perm.definition_materiau(
        mesh_perm, gfibre_perm, fluence_perm, tempfield_perm, CONTACT="NON"
    )

    compor = (
        _F(
            RELATION="MULTIFIBRE",
            GROUP_MA=("CRAYON", "T_GUIDE"),
            PARM_THETA=0.5,
            DEFORMATION="PETIT",
        ),
        _F(RELATION="DIS_GRICRA", GROUP_MA="ELA"),
        _F(RELATION="DIS_CHOC", GROUP_MA=("CREI", "RES_TOT")),
        _F(RELATION="ELAS", GROUP_MA=("EBOINF", "EBOSUP", "RIG", "DIL")),
        _F(RELATION="VMIS_ISOT_TRAC", GROUP_MA="MAINTIEN", DEFORMATION="PETIT"),
    )

    phys_pb = PhysicalProblem(model_perm, material_perm, caraelem_perm)
    phys_pb.computeBehaviourProperty(compor)
    bhv_prop = phys_pb.getBehaviourProperty()

    depl_perm = FieldOnNodesReal(model_perm)
    depl_perm.setValues(0.0)

    sief_perm = FieldOnCellsReal(model_perm, "ELGA", "SIEF_R", bhv_prop, caraelem_perm)
    sief_perm.setValues(0.0)

    vari_perm = FieldOnCellsReal(model_perm, "ELGA", "VARI_R", bhv_prop, caraelem_perm)
    vari_perm.setValues(0.0)

    strx_perm = FieldOnCellsReal(model_perm, "ELGA", "STRX_R", bhv_prop, caraelem_perm)
    strx_perm.setValues(0.0)

    RESU_PERM = CREA_RESU(
        OPERATION="AFFE",
        TYPE_RESU="EVOL_NOLI",
        COMPORTEMENT=compor,
        AFFE=_F(
            NOM_CHAM="DEPL",
            CHAM_GD=depl_perm,
            INST=0.0,
            CHAM_MATER=material_perm,
            CARA_ELEM=caraelem_perm,
            MODELE=model_perm,
        ),
    )

    CREA_RESU(
        reuse=RESU_PERM,
        RESULTAT=RESU_PERM,
        COMPORTEMENT=compor,
        OPERATION="AFFE",
        TYPE_RESU="EVOL_NOLI",
        AFFE=_F(
            NOM_CHAM="SIEF_ELGA",
            CHAM_GD=sief_perm,
            INST=0.0,
            CHAM_MATER=material_perm,
            CARA_ELEM=caraelem_perm,
            MODELE=model_perm,
        ),
    )

    CREA_RESU(
        reuse=RESU_PERM,
        RESULTAT=RESU_PERM,
        COMPORTEMENT=compor,
        OPERATION="AFFE",
        TYPE_RESU="EVOL_NOLI",
        AFFE=_F(
            NOM_CHAM="VARI_ELGA",
            CHAM_GD=vari_perm,
            CHAM_MATER=material_perm,
            CARA_ELEM=caraelem_perm,
            INST=0.0,
            MODELE=model_perm,
        ),
    )

    CREA_RESU(
        reuse=RESU_PERM,
        RESULTAT=RESU_PERM,
        COMPORTEMENT=compor,
        OPERATION="AFFE",
        TYPE_RESU="EVOL_NOLI",
        AFFE=_F(
            NOM_CHAM="STRX_ELGA",
            CHAM_GD=strx_perm,
            CHAM_MATER=material_perm,
            CARA_ELEM=caraelem_perm,
            INST=0.0,
            MODELE=model_perm,
        ),
    )

    tran_x = 0.0
    indice = 0

    for ac_perm in core_perm.collAC:
        for i, (datamac_i, resu_i) in enumerate(zip(datamac_start, list_resu_start)):
            core_i = CoeurFactory.build(type_core_start, datamac_i, sz_row_start)
            last_i = resu_i.getAccessParameters()["INST"][-1]
            mesh_i = resu_i.getModel().getMesh()

            core_i_named = {ac.name: ac for ac in core_i.collAC}
            ac_start = core_i_named.get(ac_perm.name)

            if ac_start is not None:

                idx_z_perm, idx_y_perm = core_perm.get_pos_index(ac_perm.pos_aster)
                idx_z_start, idx_y_start = core_perm.get_pos_index(ac_start.pos_aster)

                tran_z = core_perm.pas_assemblage * (idx_z_perm - idx_z_start)
                tran_y = core_perm.pas_assemblage * (idx_y_perm - idx_y_start)

                RESU_PERM = MACRO_AC_PERMUTE(
                    POS_INIT=ac_start.pos_aster,
                    POS_FIN=ac_perm.pos_aster,
                    RESU_INI=resu_i,
                    RESU_FIN=RESU_PERM,
                    MAILLAGE_INIT=mesh_i,
                    INSTANT=last_i,
                    MAILLAGE_FINAL=mesh_perm,
                    MODELE_FINAL=model_perm,
                    TRAN=(tran_x, tran_y, tran_z),
                )
                logger.debug("<MAC3_PERM>: Name '%s' -> '%s'" % (ac_start.name, ac_perm.name))
                logger.debug(
                    "<MAC3_PERM>: Position '%s' -> '%s'" % (ac_start.pos_damac, ac_perm.pos_damac)
                )
                logger.debug("<MAC3_PERM>: Index Z '%s' -> '%s'" % (idx_z_start, idx_z_perm))
                logger.debug("<MAC3_PERM>: Index Y '%s' -> '%s'" % (idx_y_start, idx_y_perm))
                logger.debug("<MAC3_PERM>: Tran(Z,Y,X) = (%s, %s, %s)" % (tran_z, tran_y, tran_x))

                UTMESS("I", "COEUR0_3", valk=(ac_start.pos_damac, ac_perm.pos_damac))
                indice += 1
                break

    UTMESS("I", "COEUR0_2", vali=(indice))

    return RESU_PERM
