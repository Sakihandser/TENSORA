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


from .cata_comportement import LoiComportementMFront

loi = LoiComportementMFront(
    nom="HYPER_HILL",
    lc_type=("MECANIQUE",),
    doc="""Relation de comportement compressibles cf.[RX.XX.XX]. """,
    num_lc=58,
    nb_vari=0,
    nom_vari=None,
    mc_mater=None,
    modelisation=("3D", "C_PLAN", "D_PLAN"),
    deformation=("PETIT", "GREEN_LAGRANGE"),
    algo_inte=("ANALYTIQUE",),
    type_matr_tang=None,
    syme_matr_tang=("Yes",),
    exte_vari=None,
    deform_ldc=("MECANIQUE",),
    regu_visc=("No",),
    post_incr=None,
)
