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


POST_ROCHE = MACRO(
    nom="POST_ROCHE",
    op=OPS("code_aster.MacroCommands.post_roche_ops.post_roche_ops"),
    sd_prod=evol_noli,
    fr=tr(
        "Méthode Roche de représentation du comportement élasto-plastique des lignes de tuyauteries"
    ),
    reentrant="n",
    VARIANTE=SIMP(statut="f", typ="TXM", into=("RCC_MRX", "ASNR"), defaut="RCC_MRX"),
    b_rccmrx=BLOC(
        condition="""equal_to("VARIANTE", "RCC_MRX") """,
        SIGM_LIM=SIMP(statut="f", typ="TXM", into=("OUI", "NON"), defaut=("OUI")),
        SIGM_ABAT=SIMP(statut="f", typ="TXM", into=("CODE", "REFE_ELAS"), defaut=("CODE")),
        b_no_sigm_lim=BLOC(
            condition="""equal_to("SIGM_LIM", "NON") """,
            TRAC_EPSI=SIMP(statut="f", typ=(fonction_sdaster,)),
        ),
    ),
    b_asnr=BLOC(
        condition="""equal_to("VARIANTE", "ASNR") """,
        TRAC_EPSI=SIMP(statut="f", typ=(fonction_sdaster,)),
    ),
    ZONE_ANALYSE=FACT(
        statut="o",
        max="**",
        regles=(UN_PARMI("TOUT", "GROUP_MA"),),
        TOUT=SIMP(statut="f", typ="TXM", into=("OUI",)),
        GROUP_MA=SIMP(statut="f", typ=grma, validators=NoRepeat(), max="**"),
        GROUP_NO_ORIG=SIMP(statut="o", typ=grno, validators=NoRepeat(), min=1, max=1),
    ),
    COUDE=FACT(
        statut="f",
        max="**",
        GROUP_MA=SIMP(statut="f", typ=grma, validators=NoRepeat(), max="**"),
        ANGLE=SIMP(statut="o", typ="R"),
        RCOURB=SIMP(statut="o", typ="R"),
    ),
    #        pour le cas ou un mode_meca est donné en première occurence
    MODELE=SIMP(statut="f", typ=(modele_sdaster)),
    #        pour le cas ou il n'y a que des CHAM_GD
    CARA_ELEM=SIMP(statut="f", typ=cara_elem),
    CHAM_MATER=SIMP(statut="f", typ=cham_mater),
    INST_TEMP=SIMP(statut="f", typ="R", defaut=0.0),
    RESU_MECA=FACT(
        statut="o",
        max="**",
        TYPE_CHAR=SIMP(
            statut="o", typ="TXM", into=("SISM_INER_SPEC", "DDS", "DILAT_THERM", "POIDS", "DINS")
        ),
        b_sism_iner_spec=BLOC(
            condition="""equal_to("TYPE_CHAR", 'SISM_INER_SPEC') """,
            # RESULTAT=SIMP(statut="o", typ=(mode_meca,)),
            RESULTAT=SIMP(statut="o", typ=(mult_elas, mode_meca)),
            DIRECTION=SIMP(statut="f", typ="TXM", into=("COMBI", "X", "Y", "Z"), defaut="COMBI"),
            TYPE_RESU=SIMP(statut="o", typ="TXM", into=("DYN", "QS")),
        ),
        b_autre=BLOC(
            condition="""not equal_to("TYPE_CHAR", 'SISM_INER_SPEC') """,
            regles=(UN_PARMI("CHAM_GD", "RESULTAT"), UN_PARMI("CHAM_GD", "NUME_ORDRE", "INST")),
            CHAM_GD=SIMP(statut="f", typ=cham_elem),
            RESULTAT=SIMP(statut="f", typ=(evol_elas)),
            NUME_ORDRE=SIMP(statut="f", typ="I", max=1),
            INST=SIMP(statut="f", typ="R", max=1),
            b_inst=BLOC(
                condition="""exists("INST") """,
                CRITERE=SIMP(statut="f", typ="TXM", into=("RELATIF", "ABSOLU"), defaut=("RELATIF")),
                PRECISION=SIMP(statut="f", typ="R", defaut=1e-6),
            ),
        ),
    ),
    PRESSION=FACT(
        statut="f",
        max="**",
        regles=(UN_PARMI("TOUT", "GROUP_MA"),),
        TOUT=SIMP(statut="f", typ="TXM", into=("OUI",)),
        GROUP_MA=SIMP(statut="f", typ=grma, validators=NoRepeat(), max="**"),
        VALE=SIMP(statut="o", typ="R", val_min=0.0),
    ),
    TOUT_CHAM=SIMP(statut="f", typ="TXM", into=("OUI",)),
    b_nom_cham=BLOC(
        condition="""not exists("TOUT_CHAM")""",
        NOM_CHAM=SIMP(
            statut="f",
            typ="TXM",
            validators=NoRepeat(),
            max=2,
            defaut="ROC1_ELNO",
            into=("ROC1_ELNO", "ROC2_ELNO"),
        ),
    ),
)
