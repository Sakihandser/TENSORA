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
    nom="KICHENIN_NL",
    lc_type=None,
    doc="""Loi de plasticité / viscoélasticité de Kichenin non linéaire [R5.03.36]""",
    num_lc=77,
    nb_vari=14,
    nom_vari=(
        "EPSPEQ",
        "EPSPXX",
        "EPSPYY",
        "EPSPZZ",
        "EPSPXY",
        "EPSPXZ",
        "EPSPYZ",
        "EPSVEQ",
        "EPVXX",
        "EPVYY",
        "EPVZZ",
        "EPVXY",
        "EPVXZ",
        "EPVYZ",
    ),
    mc_mater=("ELAS", "KICHENIN_NL"),
    modelisation=("3D", "AXIS", "D_PLAN"),
    deformation=("GDEF_LOG", "PETIT"),
    algo_inte="SPECIFIQUE",
    type_matr_tang=("PERTURBATION", "VERIFICATION"),
    proprietes=("COMP_ELAS",),
    syme_matr_tang=("Yes",),
    exte_vari=None,
    deform_ldc=("MECANIQUE",),
    regu_visc=("No",),
    post_incr=None,
)
