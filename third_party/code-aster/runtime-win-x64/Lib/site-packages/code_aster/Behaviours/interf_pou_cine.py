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
    nom="INTERF_POU_CINE",
    lc_type=("MECANIQUE",),
    doc="""Loi à écrouissage linéaire cinématique pour l'élément d'interface sol-pieu (3D_INTERF_POU)""",
    num_lc=2,  # ==> 9502
    nb_vari=3,
    nom_vari=("SAUT_PLAS_X", "SAUT_PLAS_Y", "SAUT_PLAS_Z"),
    mc_mater=("INTERF_POU_CINE",),
    modelisation=("3D", "INTSOLPI"),
    deformation=("PETIT",),
    algo_inte="SPECIFIQUE",
    type_matr_tang=("VERIFICATION",),
    proprietes=("COMP_ELAS",),
    syme_matr_tang=("Yes",),
    exte_vari=None,
    deform_ldc=("TOTALE",),
    regu_visc=("No",),
    post_incr=None,
)
