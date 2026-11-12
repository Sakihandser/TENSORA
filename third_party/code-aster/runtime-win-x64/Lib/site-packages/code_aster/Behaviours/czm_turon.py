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
    nom="CZM_TURON",
    lc_type=("MECANIQUE",),
    doc="""Relation de comportement de type CZM pour modéliser
             le comportement d'une interface isotrope transverse.
             Basée sur le modèle de Turon 2006""",
    num_lc=46,
    nb_vari=16,
    nom_vari=(
        "SAUT_MAX",
        "VARSEUIL",
        "VARIENDO",
        "INDIDISS",
        "INDIENDO",
        "SAUT_N",
        "SAUT_T1",
        "SAUT_T2",
        "SAUTEQUI",
        "SAUTTANG",
        "PCENERDI",
        "ENERDISS",
        "MIXITE_S",
        "MIXITE_G",
        "SAUTINIT",
        "SAUTRUPT",
    ),
    mc_mater=("RUPT_TURON",),
    modelisation=("ELEMJOINT",),
    deformation=("PETIT",),
    algo_inte=("ANALYTIQUE",),
    type_matr_tang=("PERTURBATION", "VERIFICATION"),
    proprietes=("COMP_INCR"),
    syme_matr_tang=("Yes",),
    exte_vari=None,
    deform_ldc=("OLD",),
    regu_visc=("No",),
    post_incr=None,
)
