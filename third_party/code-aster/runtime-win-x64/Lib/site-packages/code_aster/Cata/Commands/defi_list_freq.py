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


from ..Commons import *
from ..Language.DataStructure import *
from ..Language.Syntax import *


def defi_list_freq_prod(self, **args):
    if args.get("EQUI_MODES", None) is not None:
        return table_sdaster
    else:
        return listr8_sdaster


DEFI_LIST_FREQ = MACRO(
    nom="DEFI_LIST_FREQ",
    op=OPS("code_aster.MacroCommands.defi_list_freq_ops.defi_list_freq_ops"),
    sd_prod=defi_list_freq_prod,
    fr=tr("Définir une liste de fréquences strictement croissante"),
    reentrant="n",
    regles=(
        UN_PARMI("VALE", "DEBUT", "EQUI_MODES"),
        EXCLUS("VALE", "INTERVALLE"),
        ENSEMBLE("DEBUT", "INTERVALLE"),
        EXCLUS("VALE", "EQUI_MODES"),
        EXCLUS("DEBUT", "EQUI_MODES"),
    ),
    VALE=SIMP(statut="f", typ="R", max="**"),
    DEBUT=SIMP(statut="f", typ="R"),
    INTERVALLE=FACT(
        statut="f",
        max="**",
        regles=(UN_PARMI("NOMBRE", "PAS"),),
        JUSQU_A=SIMP(statut="o", typ="R"),
        NOMBRE=SIMP(statut="f", typ="I"),
        PAS=SIMP(statut="f", typ="R"),
    ),
    RAFFINEMENT=FACT(
        statut="f",
        LIST_RAFFINE=SIMP(statut="o", typ="R", max="**"),
        NB_POINTS=SIMP(statut="f", typ="I", defaut=5),
        PAS_MINI=SIMP(statut="f", typ="R", defaut=0.001),
        CRITERE=SIMP(
            statut="f", typ="TXM", defaut="RELATIF", into=("RELATIF", "ABSOLU", "LARGEUR_3DB")
        ),
        b_crit_rela_abs=BLOC(
            condition="""(equal_to("CRITERE", 'RELATIF') or equal_to("CRITERE", 'ABSOLU'))""",
            DISPERSION=SIMP(statut="f", typ="R", defaut=0.01),
        ),
        b_crit_larg=BLOC(
            condition="""(equal_to("CRITERE", 'LARGEUR_3DB'))""",
            regles=UN_PARMI("AMOR_REDUIT", "LIST_AMOR"),
            AMOR_REDUIT=SIMP(statut="f", typ="R", max="**"),
            LIST_AMOR=SIMP(statut="f", typ=listr8_sdaster),
        ),
    ),
    EQUI_MODES=FACT(
        statut="f",
        TYPE_SAISIE=SIMP(statut="f", typ="TXM", defaut="LISTE", into=("LISTE", "MATR_ASSE")),
        FREQ_MIN=SIMP(statut="o", typ="R"),
        FREQ_MAX=SIMP(statut="o", typ="R"),
        b_matr_asse=BLOC(
            condition="""(equal_to("TYPE_SAISIE", 'MATR_ASSE'))""",
            MATR_RIGI=SIMP(statut="o", typ=matr_asse_depl_r),
            MATR_MASS=SIMP(statut="o", typ=matr_asse_depl_r),
        ),
        b_listr=BLOC(
            condition="""(equal_to("TYPE_SAISIE", 'LISTE'))""",
            LIST_FREQ=SIMP(statut="o", typ="R", max="**"),
        ),
        TOLERANCE=SIMP(statut="f", typ="R", defaut=0.1),
        NB_POINTS_INIT=SIMP(statut="f", typ="I", defaut=10),
        NB_POINTS_SUPP=SIMP(statut="f", typ="I", defaut=1),
        ITER_MAXI=SIMP(statut="f", typ="I", defaut=20),
        NB_MODES=SIMP(statut="f", typ="I", defaut=40),
    ),
    INFO=SIMP(statut="f", typ="I", defaut=1, into=(1, 2)),
    TITRE=SIMP(statut="f", typ="TXM"),
)
