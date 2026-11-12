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
    nom="REST_ECRO_CINE",
    lc_type=("DIVERS",),
    doc="""Restauration d'écrouissage""",
    num_lc=0,
    nb_vari=6,
    nom_vari=("ECRO_X1", "ECRO_X2", "ECRO_X3", "ECRO_X4", "ECRO_X5", "ECRO_X6"),
    mc_mater=None,
    modelisation=("3D", "AXIS", "C_PLAN", "D_PLAN"),
    deformation=("PETIT",),
    algo_inte=None,
    type_matr_tang=None,
    proprietes=None,
    syme_matr_tang=("Yes",),
    exte_vari=None,
    deform_ldc=("OLD",),
    post_incr=None,
)
