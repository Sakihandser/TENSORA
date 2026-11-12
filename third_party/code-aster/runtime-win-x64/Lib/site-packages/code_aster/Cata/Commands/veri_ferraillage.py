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


def veri_ferraillage_prod(RESULTAT, **args):
    if args.get("__all__"):
        return (evol_elas, evol_noli, dyna_trans, mult_elas)

    if AsType(RESULTAT) is not None:
        return AsType(RESULTAT)
    raise CataError("type de concept resultat non prevu")


VERI_FERRAILLAGE = OPER(
    nom="VERI_FERRAILLAGE",
    op=190,
    sd_prod=veri_ferraillage_prod,
    reentrant="o:RESULTAT",
    fr=tr("vérification d'un ferraillage existant"),
    reuse=SIMP(statut="c", typ=CO),
    RESULTAT=SIMP(statut="o", typ=(evol_elas, evol_noli, dyna_trans, mult_elas)),
    CARA_ELEM=SIMP(statut="o", typ=cara_elem),
    #
    # ====
    # Sélection des numéros d'ordre pour lesquels on fait le calcul :
    # ====
    #
    b_resultat=BLOC(
        condition="""exists('RESULTAT')""",
        regles=(
            EXCLUS(
                "TOUT_ORDRE",
                "NUME_ORDRE",
                "LIST_ORDRE",
                "INST",
                "LIST_INST",
                # "MODE",
                # "LIST_MODE",
                # "FREQ",
                # "LIST_FREQ",
            ),
        ),
        TOUT_ORDRE=SIMP(statut="f", typ="TXM", into=("OUI",)),
        NUME_ORDRE=SIMP(statut="f", typ="I", max="**"),
        LIST_ORDRE=SIMP(statut="f", typ=listis_sdaster),
        INST=SIMP(statut="f", typ="R", max="**"),
        LIST_INST=SIMP(statut="f", typ=listr8_sdaster),
        # MODE=SIMP(statut="f", typ="I", max="**"),
        # LIST_MODE=SIMP(statut="f", typ=listis_sdaster),
        # FREQ=SIMP(statut="f", typ="R", max="**"),
        # LIST_FREQ=SIMP(statut="f", typ=listr8_sdaster),
        b_acce_reel=BLOC(
            condition="""(exists("FREQ"))or(exists("LIST_FREQ"))or(exists("INST"))or(exists("LIST_INST"))""",
            CRITERE=SIMP(statut="f", typ="TXM", defaut="RELATIF", into=("RELATIF", "ABSOLU")),
            b_prec_rela=BLOC(
                condition="""(equal_to("CRITERE", 'RELATIF'))""",
                PRECISION=SIMP(statut="f", typ="R", defaut=1.0e-6),
            ),
            b_prec_abso=BLOC(
                condition="""(equal_to("CRITERE", 'ABSOLU'))""", PRECISION=SIMP(statut="o", typ="R")
            ),
        ),
        #
    ),
    #
    # ====
    # Définition des grandeurs caractéristiques
    # ====
    #
    CHAM_FERR=SIMP(statut="o", typ=cham_elem),
    CHAM_REFE=SIMP(statut="f", typ=(cham_elem, carte_sdaster)),
    TYPE_COMB=SIMP(statut="o", typ="TXM", into=("ELU", "ELS")),
    CODIFICATION=SIMP(statut="f", typ="TXM", defaut="EC2", into=("BAEL91", "EC2")),
    PAS_THETA=SIMP(
        statut="f",
        typ="R",
        val_min=0.0,
        val_max=10.0,
        defaut=5.0,
        fr=(
            "Angle d'itération en degrés pour l'orientation des facettes de la méthode Capra-Maury"
        ),
    ),
    UNITE_CONTRAINTE=SIMP(
        statut="o", typ="TXM", into=("MPa", "Pa"), fr=tr("Unité des contraintes du problème")
    ),
    b_BAEL91=BLOC(
        condition=""" equal_to("CODIFICATION", 'BAEL91')""",
        fr=tr("utilisation du BAEL91"),
        #          mot clé facteur répétable pour assigner les caractéristiques locales par zones topologiques (GROUP_MA)
        AFFE=FACT(
            statut="o",
            max="**",
            regles=(UN_PARMI("TOUT", "GROUP_MA", TOUT="OUI"),),
            TOUT=SIMP(statut="f", typ="TXM", into=("OUI",)),
            GROUP_MA=SIMP(statut="f", typ=grma, validators=NoRepeat(), max="**"),
            TYPE_STRUCTURE=SIMP(
                statut="f", typ="TXM", into=("2D",), fr=tr("Type de Structure 2D"), defaut="2D"
            ),
            C_INF=SIMP(
                statut="o", typ="R", fr=tr("Enrobage des armatures inférieures pour la section 2D")
            ),
            C_SUP=SIMP(
                statut="o", typ="R", fr=tr("Enrobage des armatures supérieures pour la section 2D")
            ),
            N=SIMP(statut="f", typ="R", fr=tr("Coefficient d'équivalence acier/béton (ELS)")),
            FE=SIMP(statut="f", typ="R", fr=tr("La limite d'élasticité de l'acier")),
            FCJ=SIMP(
                statut="f",
                typ="R",
                fr=tr("La résistance caractéristique du béton à la compression"),
            ),
            SIGS_ELS=SIMP(statut="f", typ="R", fr=tr("Contrainte admissible dans l'acier")),
            SIGC_INF_ELS=SIMP(
                statut="f",
                typ="R",
                fr=tr(
                    "Contrainte admissible du béton en fibre inférieure pour la section 2D (ELS)"
                ),
            ),
            SIGC_SUP_ELS=SIMP(
                statut="f",
                typ="R",
                fr=tr(
                    "Contrainte admissible du béton en fibre supérieure pour la section 2D (ELS)"
                ),
            ),
            EYS=SIMP(statut="f", typ="R", fr=tr("Module d'Young de l'acier")),
            TYPE_DIAGRAMME=SIMP(
                statut="f",
                typ="TXM",
                defaut="B2",
                into=("B1", "B2"),
                fr=tr(
                    "Type du diagramme Contrainte-Deformation à utiliser: B1 (Incliné) ou B2 (Horizontal)"
                ),
            ),
            GAMMA_S=SIMP(
                statut="f",
                typ="R",
                fr=tr("Coefficient de sécurité sur la résistance de calcul des aciers à l'ELU"),
            ),
            GAMMA_C=SIMP(
                statut="f",
                typ="R",
                fr=tr("Coefficient de sécurité sur la résistance de calcul du béton à l'ELU"),
            ),
            ALPHA_CC=SIMP(
                statut="f",
                typ="R",
                defaut=0.85,
                fr=tr(
                    "Coefficient de sécurité sur la résistance de calcul du béton en compression (ELU)"
                ),
            ),
        ),
    ),
    b_EC2=BLOC(
        condition=""" equal_to("CODIFICATION", 'EC2')""",
        fr=tr("utilisation de l'eurocode 2"),
        #          mot clé facteur répétable pour assigner les caractéristiques locales par zones topologiques (GROUP_MA)
        AFFE=FACT(
            statut="o",
            max="**",
            regles=(UN_PARMI("TOUT", "GROUP_MA"),),
            TOUT=SIMP(statut="f", typ="TXM", into=("OUI",)),
            GROUP_MA=SIMP(statut="f", typ=grma, validators=NoRepeat(), max="**"),
            TYPE_STRUCTURE=SIMP(
                statut="f", typ="TXM", into=("2D",), fr=tr("Type de Structure 2D"), defaut="2D"
            ),
            C_INF=SIMP(
                statut="o", typ="R", fr=tr("Enrobage des armatures inférieures pour la section 2D")
            ),
            C_SUP=SIMP(
                statut="o", typ="R", fr=tr("Enrobage des armatures supérieures pour la section 2D")
            ),
            ALPHA_E=SIMP(statut="f", typ="R", fr=tr("Coefficient d'équivalence acier/béton (ELS)")),
            FYK=SIMP(
                statut="f", typ="R", fr=tr("Limite d'élasticité caractéristique dans l'acier")
            ),
            FCK=SIMP(
                statut="f",
                typ="R",
                fr=tr("Résistance caractéristique du béton en compression à 28 jours"),
            ),
            SIGS_ELS=SIMP(statut="f", typ="R", fr=tr("Contrainte admissible de l'acier (ELS)")),
            SIGC_INF_ELS=SIMP(
                statut="f",
                typ="R",
                fr=tr(
                    "Contrainte admissible du béton en fibre inférieure pour la section 2D (ELS)"
                ),
            ),
            SIGC_SUP_ELS=SIMP(
                statut="f",
                typ="R",
                fr=tr(
                    "Contrainte admissible du béton en fibre supérieure pour la section 2D (ELS)"
                ),
            ),
            CLASSE_ACIER=SIMP(
                statut="f",
                typ="TXM",
                defaut="B",
                into=("A", "B", "C"),
                fr=tr("Classe de ductilité des aciers"),
            ),
            EYS=SIMP(statut="f", typ="R", fr=tr("Module d'Young de l'acier")),
            TYPE_DIAGRAMME=SIMP(
                statut="f",
                typ="TXM",
                defaut="B2",
                into=("B1", "B2"),
                fr=tr(
                    "Type du diagramme Contrainte-Deformation à utiliser: B1 (Incliné) ou B2 (Horizontal)"
                ),
            ),
            GAMMA_S=SIMP(
                statut="f",
                typ="R",
                fr=tr("Coefficient de sécurité sur la résistance de calcul des aciers à l'ELU"),
            ),
            GAMMA_C=SIMP(
                statut="f",
                typ="R",
                fr=tr("Coefficient de sécurité sur la résistance de calcul du béton à l'ELU"),
            ),
            ALPHA_CC=SIMP(
                statut="f",
                typ="R",
                defaut=0.85,
                fr=tr(
                    "Coefficient de sécurité sur la résistance de calcul du béton en compression (ELU)"
                ),
            ),
        ),
    ),
    INFO=SIMP(statut="f", typ="I", defaut=1, into=(1, 2)),
)

##############################################################################################################
# Remarques :
# -----------
#     l'épaisseur des coques sera récupérée automatiquement via le cara_elem sous-jacent au résultat

#     Le résultat produit est un champ constant par éléments associé à la grandeur MAR2_R
#     qui comporte la composante marge

#     Arrêt en erreur si:
#        - EFGE_ELNO n'a pas été précédemment calculé et n'est donc pas présent dans la structure de données RESULTAT
#        - Un champ de ferraillage n'est pas donné en entrée
