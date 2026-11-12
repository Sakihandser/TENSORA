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
    nom="JONC_ENDO_PLAS",
    lc_type=("MECANIQUE",),
    doc="""Relation de comportement dediee aux jonctions voile-planchers (comportement elasto-plastique endommageable en rotation autour de l'axe z local) pour des elements discrets""",
    num_lc=0,
    nb_vari=9,
    nom_vari=(
        "ROTATOTA",
        "ROTAPLAS",
        "ROTAPLUS",
        "ROTAMOIN",
        "XCIN_MZZ",
        "DISSTOTA",
        "ENDOPLUS",
        "ENDOMOIN",
        "INISEUIL",
    ),
    mc_mater=None,
    modelisation=("DIS_TR"),  # ('DIS_TR','2D_DIS_TR',),
    deformation=("PETIT",),  # ('PETIT','PETIT_REAC','GROT_GDEP',),
    algo_inte=("SPECIFIQUE",),
    type_matr_tang=None,
    proprietes=None,
    syme_matr_tang=("Yes",),
    exte_vari=None,
    deform_ldc=("OLD",),
    regu_visc=("No",),
    post_incr=None,
)
