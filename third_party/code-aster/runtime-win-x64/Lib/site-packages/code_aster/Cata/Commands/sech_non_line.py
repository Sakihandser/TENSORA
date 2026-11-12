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
from ..Commons.c_comportement import compat_syntax as compat_comport
from ..Language.DataStructure import *
from ..Language.Syntax import *


def compat_syntax(keywords):
    """Update keywords for compatibility"""

    # reuse
    if "reuse" in keywords and "RESULTAT" not in keywords:
        keywords["RESULTAT"] = keywords["reuse"]

    # fix that INCREMENT is mandatory for transitory
    if "TYPE_CALCUL" not in keywords:
        if "ETAT_INIT" not in keywords or "STAT" in keywords["ETAT_INIT"]:
            if "INCREMENT" not in keywords:
                keywords["TYPE_CALCUL"] = "STAT"
                if "ETAT_INIT" in keywords:
                    del keywords["ETAT_INIT"]

    # report default keywords
    if "TYPE_CALCUL" not in keywords or keywords["TYPE_CALCUL"] == "TRAN":
        if "ETAT_INIT" not in keywords:
            keywords["ETAT_INIT"] = {"STAT": "OUI"}

        if "SCHEMA_TEMPS" in keywords and "THETA" in keywords["SCHEMA_TEMPS"]:
            keywords["PARM_THETA"] = keywords["SCHEMA_TEMPS"]["THETA"]
            del keywords["SCHEMA_TEMPS"]

    if "NEWTON" in keywords:
        keywords["NEWTON"]["RESI_LINE_RELA"] = keywords["RECH_LINEAIRE"]["RESI_LINE_RELA"]
        keywords["NEWTON"]["ITER_LINE_MAXI"] = keywords["RECH_LINEAIRE"]["ITER_LINE_MAXI"]
        del keywords["RECH_LINEAIRE"]
        del keywords["NEWTON"]["PREDICTION"]
        del keywords["NEWTON"]["MATRICE"]
        del keywords["NEWTON"]["REAC_INCR"]

    if "MODELE_REDUIT" in keywords:
        del keywords["MODELE_REDUIT"]["REAC_INCR"]

    if "TYPE_CALCUL" in keywords and keywords["TYPE_CALCUL"] == "STAT":
        if "ETAT_INIT" in keywords:
            del keywords["ETAT_INIT"]


SECH_NON_LINE = OPER(
    nom="SECH_NON_LINE",
    op=186,
    sd_prod=evol_sech,
    compat_syntax=compat_union(compat_syntax, compat_comport),
    reentrant="f:RESULTAT",
    fr=tr(
        "Résoudre un problème thermique non linéaire (conditions limites ou comportement matériau)"
        " stationnaire ou transitoire"
    ),
    reuse=SIMP(statut="c", typ=CO),
    RESULTAT=SIMP(
        statut="f", typ=evol_sech, fr=tr("Objet qui sera enrichi des nouveaux instants calculés")
    ),
    MODELE=SIMP(statut="o", typ=(modele_sdaster)),
    CHAM_MATER=SIMP(statut="o", typ=(cham_mater)),
    COMPORTEMENT=C_COMPORTEMENT("SECH_NON_LINE"),
    EXCIT=FACT(
        statut="o",
        max="**",
        CHARGE=SIMP(statut="o", typ=(char_ther, char_cine_ther)),
        FONC_MULT=SIMP(statut="f", typ=(fonction_sdaster, nappe_sdaster, formule)),
        TYPE_CHARGE=SIMP(statut="f", typ="TXM", defaut="FIXE_CSTE", into=("FIXE_CSTE",)),
    ),
    # -------------------------------------------------------------------
    AFFICHAGE=C_AFFICHAGE(),
    # -------------------------------------------------------------------
    METHODE=SIMP(statut="f", typ="TXM", defaut="NEWTON", into=("NEWTON",)),
    b_meth_newton=BLOC(
        condition="""equal_to("METHODE", 'NEWTON')""",
        NEWTON=FACT(
            statut="d",
            REAC_ITER=SIMP(statut="f", typ="I", defaut=0, val_min=0),
            RESI_LINE_RELA=SIMP(statut="f", typ="R", defaut=1.0e-3),
            ITER_LINE_MAXI=SIMP(statut="f", typ="I", defaut=0),
        ),
    ),
    # -------------------------------------------------------------------
    TYPE_CALCUL=SIMP(statut="f", typ="TXM", into=("TRAN",), defaut="TRAN"),
    # -------------------------------------------------------------------
    INCREMENT=C_INCREMENT(),
    # -------------------------------------------------------------------
    b_trans=BLOC(
        condition="""(equal_to("TYPE_CALCUL", 'TRAN'))""",
        PARM_THETA=SIMP(statut="f", typ="R", defaut=0.57, val_min=0.0, val_max=1.0),
        # -------------------------------------------------------------------
        ETAT_INIT=FACT(
            statut="o",
            regles=(EXCLUS("EVOL_SECH", "CHAM_NO", "VALE", "STAT"),),
            STAT=SIMP(statut="f", typ="TXM", into=("OUI",)),
            EVOL_SECH=SIMP(statut="f", typ=evol_sech),
            CHAM_NO=SIMP(statut="f", typ=cham_no_sdaster),
            VALE=SIMP(statut="f", typ="R"),
            b_evol=BLOC(
                condition="""exists("EVOL_SECH")""",
                NUME_ORDRE=SIMP(statut="f", typ="I"),
                INST=SIMP(statut="f", typ="R"),
                b_inst=BLOC(
                    condition="""exists("INST")""",
                    CRITERE=SIMP(
                        statut="f", typ="TXM", defaut="RELATIF", into=("RELATIF", "ABSOLU")
                    ),
                    b_prec_rela=BLOC(
                        condition="""(equal_to("CRITERE", 'RELATIF'))""",
                        PRECISION=SIMP(statut="f", typ="R", defaut=1.0e-6),
                    ),
                    b_prec_abso=BLOC(
                        condition="""(equal_to("CRITERE", 'ABSOLU'))""",
                        PRECISION=SIMP(statut="o", typ="R"),
                    ),
                ),
            ),
        ),
    ),
    # -------------------------------------------------------------------
    b_stat=BLOC(condition="""(equal_to("TYPE_CALCUL", 'STAT'))""", INCREMENT=C_INCREMENT()),
    CONVERGENCE=FACT(
        statut="d",
        RESI_GLOB_MAXI=SIMP(statut="f", typ="R"),
        RESI_GLOB_RELA=SIMP(statut="f", typ="R"),
        ITER_GLOB_MAXI=SIMP(statut="f", typ="I", defaut=10),
    ),
    # -------------------------------------------------------------------
    #        Catalogue commun SOLVEUR
    SOLVEUR=C_SOLVEUR("THER_NON_LINE"),
    # -------------------------------------------------------------------
    ARCHIVAGE=C_ARCHIVAGE(),
    # -------------------------------------------------------------------
    OBSERVATION=C_OBSERVATION("SECHAGE"),
    # -------------------------------------------------------------------
    TITRE=SIMP(statut="f", typ="TXM"),
    INFO=SIMP(statut="f", typ="I", into=(1, 2)),
)
