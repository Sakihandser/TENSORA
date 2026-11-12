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


from .cata_comportement import LoiComportement

loi = LoiComportement(
    nom="JOINT_MECA_ENDO",
    lc_type=("MECANIQUE",),
    doc="""Relation de comportement de contact, elastique avec resistance a la traction et rupture
             pour modéliser les joints dans les barrages.
             Enfin elle permet de modéliser, avec les éléments de joint HM, un couplage entre
             la mécanique et l'écoulement de fluide dans la fissure""",
    num_lc=47,
    nb_vari=20,
    nom_vari=(
        "LAMBDA",
        "INDIPLAS",
        "DEPPLAS1",
        "DEPPLAS2",
        "DEPPLAS3",
        "ENDO",
        "SAUT_N",
        "SAUT_T1",
        "SAUT_T2",
        "VIDE",
        "SIGN_GLO",
        "GRADP_X",
        "GRADP_Y",
        "GRADP_Z",
        "FH_X",
        "FH_Y",
        "FH_Z",
        "PRESF",
        "SIGM_T1",
        "SIGM_T2",
    ),
    mc_mater=("JOINT_MECA_ENDO",),
    modelisation=("3D", "PLAN", "AXIS", "ELEMJOINT", "EJ_HYME"),
    deformation=("PETIT",),
    algo_inte=("ANALYTIQUE",),
    type_matr_tang=("PERTURBATION", "VERIFICATION"),
    proprietes=("COMP_ELAS",),
    syme_matr_tang=("No",),
    exte_vari=None,
    deform_ldc=("TOTALE",),
    regu_visc=("No",),
    post_incr=None,
)
