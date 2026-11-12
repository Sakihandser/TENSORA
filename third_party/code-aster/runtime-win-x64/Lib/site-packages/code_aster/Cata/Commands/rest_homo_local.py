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


def rest_homo_sdprod(self, CORR_MECA, CORR_THER, **kwargs):
    if kwargs.get("__all__"):
        return [evol_elas, evol_ther]

    if CORR_THER is not None and CORR_MECA is None:
        return evol_ther
    else:
        return evol_elas


REST_HOMO_LOCAL = MACRO(
    nom="REST_HOMO_LOCAL",
    op=OPS("code_aster.MacroCommands.MateHomo.rest_homo_ops.rest_homo_ops"),
    sd_prod=rest_homo_sdprod,
    docu="UX.YZ.AB",
    reentrant="n",
    fr=tr("Calcul des champs locaux à partir de la solution homogénéisée."),
    TYPE_HOMO=SIMP(statut="o", typ="TXM", into=("MASSIF",)),
    POSITION=SIMP(statut="o", typ="R", min=3, max=3),
    CORR_MECA=SIMP(statut="f", typ=evol_elas_dict),
    CORR_THER=SIMP(statut="f", typ=evol_ther_dict),
    PRESSION=SIMP(statut="f", typ=fonction_sdaster),
    EVOL_ELAS=SIMP(statut="f", typ=evol_elas),
    EVOL_THER=SIMP(statut="f", typ=evol_ther),
    INST=SIMP(statut="f", typ="R", validators=NoRepeat(), max="**"),
    TOUT_INST=SIMP(statut="f", typ="TXM", into=("OUI",)),
    CRITERE=SIMP(statut="f", typ="TXM", defaut="RELATIF", into=("RELATIF", "ABSOLU")),
    PRECISION=SIMP(statut="f", typ="R", defaut=1.0e-6, val_min=0.0),
    regles=(
        AU_MOINS_UN("CORR_MECA", "CORR_THER"),
        AU_MOINS_UN("EVOL_ELAS", "EVOL_THER"),
        ENSEMBLE("EVOL_THER", "CORR_THER"),
        PRESENT_PRESENT("RESU_THER", "CORR_THER", "EVOL_THER"),
        EXCLUS("TOUT_INST", "INST"),
    ),
    AFFE=FACT(
        statut="o",
        max="**",
        regles=UN_PARMI("TOUT", "GROUP_MA"),
        TOUT=SIMP(statut="f", typ="TXM", into=("OUI",)),
        GROUP_MA=SIMP(statut="f", typ=grma, validators=NoRepeat(), max="**"),
        MATER=SIMP(statut="o", typ=mater_sdaster, max=1),
    ),
    COMPLET=SIMP(statut="f", typ="TXM", into=("OUI", "NON"), defaut="NON", max=1),
    TRANSLATION=SIMP(statut="f", typ="TXM", into=("OUI", "NON"), defaut="NON", max=1),
    INFO=SIMP(statut="f", typ="I", defaut=1, into=(1, 2)),
    b_onlyther=BLOC(
        condition="""exists("CORR_THER") and not exists("CORR_MECA")""",
        OPTION=SIMP(statut="f", typ="TXM", into=("FLUX_ELGA", "SANS"), defaut="SANS", max=1),
    ),
    b_onlymeca=BLOC(
        condition="""exists("CORR_MECA") and not exists("CORR_THER")""",
        OPTION=SIMP(statut="f", typ="TXM", into=("SIEF_ELGA", "SANS"), defaut="SANS", max=1),
    ),
    b_therandmeca=BLOC(
        condition="""exists("CORR_MECA") and exists("CORR_THER")""",
        OPTION=SIMP(
            statut="f", typ="TXM", into=("SIEF_ELGA", "FLUX_ELGA", "SANS"), defaut="SANS", max=2
        ),
    ),
)
