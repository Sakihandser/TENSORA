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

from ..Cata.Commons import *
from ..Cata.Language.DataStructure import *
from ..Cata.Language.Syntax import *
from ..Supervis import UserMacro
from .defi_cont_ops import defi_cont_ops, _hasFriction


def defi_cont_prod(self, ZONE, **args):
    if args.get("__all__"):
        return (char_cont, char_frot)

    if _hasFriction(ZONE):
        return char_frot

    return char_cont


DEFI_CONT_CATA = MACRO(
    nom="DEFI_CONT",
    op=OPS("code_aster.MacroCommands.defi_cont_ops.defi_cont_ops"),
    sd_prod=defi_cont_prod,
    reentrant="n",
    fr=tr("Définit les zones soumises à des conditions de contact avec ou sans frottement"),
    # en        = "Allows the definition of contact surfaces",
    # ----- PARAMETRES GENERAUX ( NE DEPENDENT PAS DE LA ZONE DE CONTACT)
    MODELE=SIMP(statut="o", typ=modele_sdaster),
    INFO=SIMP(statut="f", typ="I", into=(1, 2), defaut=1),
    ZONE=FACT(
        statut="o",
        max="**",
        # LISSAGE DES NORMALES PAR MOYENNATION AUX NOEUDS
        LISSAGE=SIMP(
            statut="f",
            typ="TXM",
            defaut="NON",
            into=("OUI", "NON"),
            fr=tr("Lissage des normales par moyennation aux noeuds"),
        ),
        # VERIFICATION DE L"ORIENTATION ET DE LA COHERENCE DES NORMALES
        VERI_NORM=SIMP(
            statut="f",
            typ="TXM",
            defaut="OUI",
            into=("OUI", "NON"),
            fr=tr("Vérification de l'orientation (sortante) des normales aux surfaces"),
        ),
        # Method for contact
        ALGO_CONT=SIMP(
            statut="f",
            typ="TXM",
            defaut="LAGRANGIEN",
            into=("LAGRANGIEN", "NITSCHE", "PENALISATION"),
        ),
        b_algo_cont_nitsche=BLOC(
            condition="""is_in("ALGO_CONT", ("NITSCHE",))""",
            SYME=SIMP(statut="f", typ="TXM", defaut="OUI", into=("OUI", "NON")),
            b_vari_syme=BLOC(
                condition="""equal_to("SYME", "NON")""",
                VARIANTE=SIMP(
                    statut="f",
                    typ="TXM",
                    defaut="ROBUSTE",
                    into=("RAPIDE", "ROBUSTE"),
                    fr=tr("Choix de la variante des formulations du contact"),
                ),
            ),
        ),
        b_algo_cont_lag=BLOC(
            condition="""is_in("ALGO_CONT", ("LAGRANGIEN",))""",
            VARIANTE=SIMP(
                statut="f",
                typ="TXM",
                defaut="ROBUSTE",
                into=("CLASSIQUE", "ROBUSTE"),
                fr=tr("Choix de la variante des formulations du contact"),
            ),
            # Managing tangent matrix for LAGRANGE
            b_mat_robu=BLOC(
                condition="""equal_to("VARIANTE", 'ROBUSTE')""",
                TYPE_MATR_TANG=SIMP(
                    statut="f", typ="TXM", defaut="ANALYTIQUE", into=("PERTURBATION", "ANALYTIQUE")
                ),
            ),
            b_mat_clas=BLOC(
                condition="""equal_to("VARIANTE", 'CLASSIQUE')""",
                TYPE_MATR_TANG=SIMP(
                    statut="f", typ="TXM", defaut="PERTURBATION", into=("PERTURBATION",)
                ),
            ),
            b_zone_fric_vari=BLOC(
                condition="""equal_to("FROTTEMENT", "OUI") """,
                # FROTTEMENT
                b_zone_lagr=BLOC(
                    condition="""equal_to("ALGO_CONT", 'LAGRANGIEN') and equal_to("VARIANTE",'ROBUSTE') """,
                    ALGO_FROT=SIMP(
                        statut="f", typ="TXM", defaut="LAGRANGIEN", into=("LAGRANGIEN",)
                    ),
                ),
                b_zone_lagr_std=BLOC(
                    condition="""equal_to("ALGO_CONT", 'LAGRANGIEN') and equal_to("VARIANTE",'CLASSIQUE') """,
                    ALGO_FROT=SIMP(
                        statut="f", typ="TXM", defaut="LAGRANGIEN", into=("LAGRANGIEN",)
                    ),
                    COEF_FROT=SIMP(statut="f", typ="R", defaut=100.0, val_min=0.0),
                ),
            ),
        ),
        b_algo_cont_pena=BLOC(
            condition="""is_in("ALGO_CONT", ("PENALISATION",))""",
            # Managing tangent matrix for LAGRANGE
            TYPE_MATR_TANG=SIMP(
                statut="f", typ="TXM", defaut="ANALYTIQUE", into=("PERTURBATION", "ANALYTIQUE")
            ),
        ),
        # le choix du type de contact implique aussi celui de frottement
        TYPE_CONT=SIMP(
            statut="f",
            typ="TXM",
            defaut="UNILATERAL",
            into=("UNILATERAL", "BILATERAL"),
            fr=tr("Choix d'un modèle de contact"),
        ),
        # le choix du type de methode d integration
        TYPE_INTE=SIMP(
            statut="f",
            typ="TXM",
            defaut="SEG_BASE",
            into=("ELEM_BASE", "SEG_BASE"),
            fr=tr("Choix d'une méthode d'intégration"),
        ),
        # coefficient de nitche, pénalisation ou augmentation en fonction de la méthode de contact
        COEF_CONT=SIMP(statut="f", typ="R", defaut=100.0, val_min=0.0),
        # Pairing options (for segment to segment contact)
        APPARIEMENT=SIMP(statut="f", typ="TXM", defaut="MORTAR", into=("MORTAR",)),
        b_zone_pair_param=BLOC(
            condition="""equal_to("APPARIEMENT", "MORTAR") """,
            APPA_TOLE=SIMP(statut="f", typ="R", defaut=1e-8, val_min=0.0),
            AIRE_TOLE=SIMP(statut="f", typ="R", defaut=1e-8, val_min=0.0),
            TYPE_APPA=SIMP(
                statut="f", typ="TXM", defaut="RAPIDE", into=("RAPIDE", "FORCEBRUTE", "PANG")
            ),
        ),
        COEF_MULT_APPA=SIMP(statut="f", typ="R", defaut=-1.0),
        GROUP_MA_MAIT=SIMP(statut="o", typ=grma, max=1),
        GROUP_MA_ESCL=SIMP(statut="o", typ=grma, max=1),
        # Managing boundary conditions with contact (slave side) que pour la méthode LAGRANGE
        b_cl=BLOC(
            condition="""equal_to("ALGO_CONT", "LAGRANGIEN")""",
            SANS_GROUP_MA=SIMP(statut="f", typ=grma, validators=NoRepeat(), max="**"),
            SANS_GROUP_NO=SIMP(statut="f", typ=grno, validators=NoRepeat(), max="**"),
        ),
        # Initial contact
        CONTACT_INIT=SIMP(
            statut="f", typ="TXM", defaut="INTERPENETRE", into=("OUI", "INTERPENETRE", "NON")
        ),
        # Add suppl. gaps
        DIST_SUPP=SIMP(statut="f", typ=(fonction_sdaster, nappe_sdaster, formule)),
        # À vérifier si l"algo marche pour POUTRE
        CARA_ELEM=SIMP(statut="f", typ=cara_elem),
        b_zone_cara=BLOC(
            condition="""exists("CARA_ELEM")""",
            DIST_POUTRE=SIMP(statut="f", typ="TXM", defaut="NON", into=("OUI", "NON")),
            DIST_COQUE=SIMP(statut="f", typ="TXM", defaut="NON", into=("OUI", "NON")),
        ),
        # Enable friction
        FROTTEMENT=SIMP(
            statut="f",
            typ="TXM",
            defaut="NON",
            into=("NON", "OUI"),
            fr=tr("Activation du frottement"),
        ),
        # ----- définition mot-clé facteur avec frottement
        b_zone_fric=BLOC(
            condition="""equal_to("FROTTEMENT", "OUI") """,
            # FROTTEMENT
            b_cont_nits=BLOC(
                condition="""equal_to("ALGO_CONT", "NITSCHE")""",
                ALGO_FROT=SIMP(statut="f", typ="TXM", defaut="NITSCHE", into=("NITSCHE",)),
            ),
            b_cont_pena=BLOC(
                condition="""equal_to("ALGO_CONT", "PENALISATION")""",
                ALGO_FROT=SIMP(
                    statut="f", typ="TXM", defaut="PENALISATION", into=("PENALISATION",)
                ),
            ),
            TYPE_FROT=SIMP(
                statut="f",
                typ="TXM",
                defaut="SANS",
                into=("SANS", "ADHERENT", "TRESCA", "COULOMB"),
                fr=tr("Choix d'un modèle de frottement"),
            ),
            b_tresca=BLOC(
                condition="""equal_to("TYPE_FROT", "TRESCA")""", TRESCA=SIMP(statut="o", typ="R")
            ),
            b_coulomb=BLOC(
                condition="""equal_to("TYPE_FROT", "COULOMB")""", COULOMB=SIMP(statut="o", typ="R")
            ),
        ),  # fin BLOC
    ),  # fin ZONE
)

DEFI_CONT = UserMacro("DEFI_CONT", DEFI_CONT_CATA, defi_cont_ops)
