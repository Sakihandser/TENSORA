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
from ..Commons.c_comportement import compat_syntax as comportement_compat_syntax
from ..Commons.c_convergence import compat_syntax as convergence_compat_syntax


def compat_syntax(keywords):
    """Adapt keywords before syntax checking.

    Arguments:
        keywords (dict): Keywords arguments of user's keywords, changed in place.
    """
    comportement_compat_syntax(keywords)
    convergence_compat_syntax(keywords)


CALC_ENDO = MACRO(
    nom="CALC_ENDO",
    op=OPS("code_aster.MacroCommands.calc_endo_ops.calc_endo_ops"),
    compat_syntax=compat_syntax,
    sd_prod=list,
    fr=tr(
        "Calcul de l'évolution mécanique en quasi-statique"
        "d'une structure en non linéaire nécessitant des phases de stabilisation"
    ),
    reentrant="f:RESULTAT",
    reuse=SIMP(statut="c", typ=CO),
    # -------------------------------------------------------------------
    RESULTAT=SIMP(
        statut="f", typ=evol_noli, fr=tr("Objet qui sera enrichi des nouveaux instants calculés")
    ),
    # -------------------------------------------------------------------
    MODELE=SIMP(statut="o", typ=modele_sdaster),
    # -------------------------------------------------------------------
    CHAM_MATER=SIMP(statut="o", typ=cham_mater),
    # -------------------------------------------------------------------
    CARA_ELEM=SIMP(statut="f", typ=cara_elem),
    # -------------------------------------------------------------------
    EXCIT=FACT(
        statut="f",
        max="**",
        CHARGE=SIMP(statut="o", typ=(char_meca, char_cine_meca)),
        FONC_MULT=SIMP(statut="f", typ=(fonction_sdaster)),
        TYPE_CHARGE=SIMP(
            statut="f", typ="TXM", defaut="FIXE_CSTE", into=("FIXE_CSTE", "SUIV", "DIDI")
        ),
    ),
    # -------------------------------------------------------------------
    CONTACT=SIMP(statut="f", typ=char_contact),
    # -------------------------------------------------------------------
    SCHEMA_THM=C_SCHEMA_THM(),
    # -------------------------------------------------------------------
    COMPORTEMENT=C_COMPORTEMENT("MECA_NON_LINE"),
    # -------------------------------------------------------------------
    ETAT_INIT=C_ETAT_INIT("MECA_NON_LINE", "f"),
    # -------------------------------------------------------------------
    INCREMENT=C_INCREMENT(),
    # -------------------------------------------------------------------
    METHODE=SIMP(
        statut="f", typ="TXM", defaut="NEWTON", into=("NEWTON", "IMPLEX", "NEWTON_KRYLOV")
    ),
    b_meth_newton=BLOC(
        condition="""equal_to("METHODE", 'NEWTON') or equal_to("METHODE", 'NEWTON_KRYLOV')""",
        NEWTON=C_NEWTON(),
    ),
    # -------------------------------------------------------------------
    RECH_LINEAIRE=C_RECH_LINEAIRE(),
    # -------------------------------------------------------------------
    CONVERGENCE=C_CONVERGENCE("STAT_NON_LINE"),
    CONVERGENCE_REFE=C_CONVERGENCE_REFE("MECA_NON_LINE"),
    # -------------------------------------------------------------------
    SOLVEUR=C_SOLVEUR("STAT_NON_LINE"),
    # -------------------------------------------------------------------
    OBSERVATION=C_OBSERVATION("MECANIQUE"),
    # -------------------------------------------------------------------
    MESURE=C_MESURE(),
    # -------------------------------------------------------------------
    SUIVI_DDL=C_SUIVI_DDL(),
    # -------------------------------------------------------------------
    ARCHIVAGE=C_ARCHIVAGE(),
    # ------------------------------------------------------------------
    ENERGIE=FACT(
        statut="f", max=1, CALCUL=SIMP(statut="f", typ="TXM", into=("OUI",), defaut="OUI")
    ),
    # -------------------------------------------------------------------
    ENDO_VISC=FACT(
        statut="o",
        max=1,
        regles=(ENSEMBLE("OBSERVATION", "PREC_STAB")),
        LIST_INST=SIMP(statut="o", typ=(listr8_sdaster, list_inst)),
        OBSERVATION=SIMP(statut="f", typ="TXM", max="**"),
        PREC_STAB=SIMP(statut="f", typ="R", max="**"),
        ARRET=SIMP(statut="f", typ="TXM", into=("OUI", "NON"), defaut="OUI"),
        TABLE=SIMP(statut="f", typ=CO),
        RESULTAT=SIMP(statut="f", typ=CO),
    ),
    ARCHIVAGE_VISC=C_ARCHIVAGE(cmd="CALC_ENDO"),
    # -------------------------------------------------------------------
    AFFICHAGE=C_AFFICHAGE(),
    # -------------------------------------------------------------------
    INFO=SIMP(statut="f", typ="I", into=(1, 2)),
    b_info=BLOC(
        condition="""equal_to("INFO", 2)""",
        fr=tr("filtre les messages émis dans le .mess selon le type de message demandé"),
        INFO_DBG=SIMP(
            statut="f",
            typ="TXM",
            max="**",
            validators=NoRepeat(),
            into=("CONTACT", "MECANONLINE", "PILOTAGE", "FACTOR", "SOLVEUR", "APPARIEMENT"),
        ),
    ),
    TITRE=SIMP(statut="f", typ="TXM"),
)
