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


from enum import Enum
from typing import Dict, Tuple, Union

from ..Language.Syntax import tr


class Phenomenon(Enum):
    """Liste tous les phénomènes possibles"""

    CONTRAINTE = 1
    DEFORMATION = 2
    ENERGIE = 3
    CRITERES = 4
    VARI_INTERNE = 5
    HYDRAULIQUE = 6
    THERMIQUE = 7
    ACOUSTIQUE = 8
    FORCE = 9
    ERREUR = 10
    DEPLACEMENT = 11
    METALLURGIE = 12
    PROPRIETES = 13
    AUTRES = 14
    SECHAGE = 15

    @classmethod
    def check_value_iterable(cls, phenomena: Tuple["Phenomenon"]) -> None:
        """Renvoie une erreur si l'itérable en argument a au moins un phénomènes
        qui n'est pas contenu dans l'énumératio

        Args:
            phenomena (Tuple[Phenomenon]): Itérable de phénomènes

        Raises:
            ValueError: Si au moins un phénomène de l'itérable ne correspond pas
        """
        for p in phenomena:
            if not p in Phenomenon:
                raise ValueError(f"Unrecognized phenomenon: {p}")


class NomChamIntoGenerator:
    """Classe contenant l'information sur les champs et permettant de récupérer
    les informations sur les champs, et de filtrer les champs.

    nom_cham_into (Dict[str, Dict[str, Tuple[Tuple, Tuple]]]) : Structure
        contenant toutes les informations relatives aux champs

    nom_cham_to_phenomenon (Dict[str,str]) : Mapping des noms des champs avec
        les phénomènes associés.
    """

    nom_cham_into: Dict[Phenomenon, Dict[str, Tuple[Tuple, Tuple]]] = {
        Phenomenon.CONTRAINTE: {
            "EFGE_ELGA": (("lin", "nonlin", "dyna"), tr("Efforts généralisés aux points de Gauss")),
            "EFGE_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Efforts généralisés aux noeuds par élément, dans le repère local"),
            ),
            "EGRU_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Efforts généralisés aux noeuds par élément, dans le repère utilisateur"),
            ),
            "EFGE_NOEU": (("lin", "nonlin", "dyna"), tr("Efforts généralisés aux noeuds")),
            "SIEF_ELGA": (("lin",), tr("Contraintes et efforts aux points de Gauss")),
            "SIEF_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Contraintes et efforts aux noeuds par élément"),
            ),
            "SIMY_ELGA": (
                ("lin", "nonlin", "dyna"),
                tr("Contraintes moyennées aux points de Gauss"),
            ),
            "SIEF_NOEU": (("lin", "nonlin", "dyna"), tr("Contraintes et efforts aux noeuds")),
            "SIGM_ELGA": (("lin", "nonlin", "dyna"), tr("Contraintes aux points de Gauss")),
            "SIGM_ELNO": (("lin", "nonlin", "dyna"), tr("Contraintes aux noeuds par élément")),
            "SIGM_NOEU": (("lin", "nonlin", "dyna"), tr("Contraintes aux noeuds")),
            "SIPM_ELNO": (
                ("lin", "nonlin"),
                tr("Contraintes aux noeuds par élément pour les éléments de poutre"),
            ),
            "SIPO_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Contraintes aux noeuds par élément pour les éléments de poutre"),
            ),
            "SIPO_NOEU": (
                ("lin", "nonlin", "dyna"),
                tr("Contraintes aux noeuds pour les éléments de poutre"),
            ),
            "SIRO_ELEM": (("lin", "nonlin", "dyna"), tr("Contraintes de rosette par élément")),
            "STRX_ELGA": (
                ("lin",),
                tr("Efforts généralisés à partir des déplacements en linéaire aux points de Gauss"),
            ),
        },
        Phenomenon.DEFORMATION: {
            "DEGE_ELGA": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations généralisées aux points de Gauss"),
            ),
            "DEGE_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations généralisées aux noeuds par élément"),
            ),
            "DEGE_NOEU": (("lin", "nonlin", "dyna"), tr("Déformations généralisées aux noeuds")),
            "EPFD_ELGA": (
                ("nonlin", "dyna"),
                tr("Déformations de fluage de déssication aux points de Gauss"),
            ),
            "EPFD_ELNO": (
                ("nonlin", "dyna"),
                tr("Déformations de fluage de déssication aux noeuds par élément"),
            ),
            "EPFD_NOEU": (
                ("nonlin", "dyna"),
                tr("Déformations de fluage de déssication aux noeuds"),
            ),
            "EPFP_ELGA": (
                ("nonlin", "dyna"),
                tr("Déformations de fluage propre aux points de Gauss"),
            ),
            "EPFP_ELNO": (
                ("nonlin", "dyna"),
                tr("Déformations de fluage propre aux noeuds par élément"),
            ),
            "EPFP_NOEU": (("nonlin", "dyna"), tr("Déformations de fluage propre aux noeuds")),
            "EPME_ELGA": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations mécaniques en petits déplacements aux points de Gauss"),
            ),
            "EPME_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations mécaniques en petits déplacements aux noeuds par élément"),
            ),
            "EPME_NOEU": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations mécaniques en petits déplacements aux noeuds"),
            ),
            "EPMG_ELGA": (
                ("nonlin", "dyna"),
                tr("Déformations mécaniques en grands déplacements aux points de Gauss"),
            ),
            "EPMG_ELNO": (
                ("nonlin", "dyna"),
                tr("Déformations mécaniques en grands déplacements aux noeuds par élément"),
            ),
            "EPMG_NOEU": (
                ("nonlin", "dyna"),
                tr("Déformations mécaniques en grands déplacements aux noeuds"),
            ),
            "EPSG_ELGA": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations de Green-Lagrange aux points de Gauss"),
            ),
            "EPSG_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations de Green-Lagrange aux noeuds par élément"),
            ),
            "EPSG_NOEU": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations de Green-Lagrange aux noeuds"),
            ),
            "EPSI_ELGA": (("lin", "nonlin", "dyna"), tr("Déformations aux points de Gauss")),
            "EPSI_ELNO": (("lin", "nonlin", "dyna"), tr("Déformations aux noeuds par élément")),
            "EPSI_NOEU": (("lin", "nonlin", "dyna"), tr("Déformations aux noeuds")),
            "EPSP_ELGA": (("nonlin", "dyna"), tr("Déformations anélastique aux points de Gauss")),
            "EPSP_ELNO": (
                ("nonlin", "dyna"),
                tr("Déformations anélastique aux noeuds par élément"),
            ),
            "EPSP_NOEU": (("nonlin", "dyna"), tr("Déformations anélastique aux noeuds")),
            "EPVC_ELGA": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations dues aux variables de commande aux points de Gauss"),
            ),
            "EPVC_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations dues aux variables de commande aux noeuds par élément"),
            ),
            "EPVC_NOEU": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations dues aux variables de commande aux noeuds"),
            ),
            "EPSL_ELGA": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations logarithmiques aux points de Gauss"),
            ),
            "EPSL_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations logarithmiques aux noeuds par élément"),
            ),
            "EPSL_NOEU": (("lin", "nonlin", "dyna"), tr("Déformations logarithmiques aux noeuds")),
        },
        Phenomenon.ENERGIE: {
            "DISS_ELEM": (("lin", "nonlin", "dyna"), tr("Énergie de dissipation par élément")),
            "DISS_ELGA": (
                ("lin", "nonlin", "dyna"),
                tr("Densité d'énergie de dissipation aux points de Gauss"),
            ),
            "DISS_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Densité d'énergie de dissipation aux noeuds par élément"),
            ),
            "DISS_NOEU": (
                ("lin", "nonlin", "dyna"),
                tr("Densité d'énergie de dissipation aux noeuds"),
            ),
            "ECIN_ELEM": (("lin",), tr("Énergie cinétique par élément")),
            "ENEL_ELEM": (("lin", "nonlin", "dyna"), tr("Énergie élastique par élément")),
            "ENEL_ELGA": (
                ("lin", "nonlin", "dyna"),
                tr("Densité d'énergie élastique aux points de Gauss"),
            ),
            "ENEL_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Densité d'énergie élastique aux noeuds par élément"),
            ),
            "ENEL_NOEU": (("lin", "nonlin", "dyna"), tr("Densité d'énergie élastique aux noeuds")),
            "ENTR_ELEM": (
                ("lin", "nonlin", "dyna"),
                tr("Énergie élastique modifiée (seulement traction) utilisée par Gp"),
            ),
            "EPOT_ELEM": (("lin",), tr("Énergie potentielle de déformation élastique par élément")),
            "ETOT_ELEM": (
                ("lin", "nonlin", "dyna"),
                tr("Incrément d'énergie de déformation totale par élément"),
            ),
            "ETOT_ELGA": (
                ("lin", "nonlin", "dyna"),
                tr("Incrément de densité d'énergie de déformation totale aux points de Gauss"),
            ),
            "ETOT_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Incrément de densité d'énergie de déformation totale aux noeuds par élément"),
            ),
            "ETOT_NOEU": (
                ("lin", "nonlin", "dyna"),
                tr("Incrément de densité d'énergie de déformation totale aux noeuds"),
            ),
        },
        Phenomenon.CRITERES: {
            "DERA_ELGA": (
                ("nonlin", "dyna"),
                tr("Indicateur local de décharge et de perte de radialité aux points de Gauss"),
            ),
            "DERA_ELNO": (
                ("nonlin", "dyna"),
                tr("Indicateur local de décharge et de perte de radialité aux noeuds par élément"),
            ),
            "DERA_NOEU": (
                ("nonlin", "dyna"),
                tr("Indicateur local de décharge et de perte de radialité aux noeuds"),
            ),
            "ENDO_ELGA": (
                ("nonlin", "dyna"),
                tr("Dommage de Lemaître-Sermage aux points de Gauss"),
            ),
            "ENDO_ELNO": (
                ("nonlin", "dyna"),
                tr("Dommage de Lemaître-Sermage aux noeuds par élément"),
            ),
            "ENDO_NOEU": (("nonlin", "dyna"), tr("Dommage de Lemaître-Sermage aux noeuds")),
            "EPEQ_ELGA": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations équivalentes aux points de Gauss"),
            ),
            "EPEQ_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations équivalentes aux noeuds par élément"),
            ),
            "EPEQ_NOEU": (("lin", "nonlin", "dyna"), tr("Déformations équivalentes aux noeuds")),
            "EPGQ_ELGA": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations équivalentes de Green-Lagrange aux points de Gauss"),
            ),
            "EPGQ_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations équivalentes de Green-Lagrange aux noeuds par élément"),
            ),
            "EPGQ_NOEU": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations équivalentes de Green-Lagrange aux noeuds"),
            ),
            "EPMQ_ELGA": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations mécaniques équivalentes aux points de Gauss"),
            ),
            "EPMQ_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations mécaniques équivalentes aux noeuds par élément"),
            ),
            "EPMQ_NOEU": (
                ("lin", "nonlin", "dyna"),
                tr("Déformations mécaniques équivalentes aux noeuds"),
            ),
            "INDL_ELGA": (("nonlin", "dyna"), tr("Indicateur de localisation aux points de Gauss")),
            "PDIL_ELGA": (("nonlin", "dyna"), tr("Module de rigidité de micro-dilatation")),
            "SIEQ_ELGA": (
                ("lin", "nonlin", "dyna"),
                tr("Contraintes équivalentes aux points de Gauss"),
            ),
            "SIEQ_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Contraintes équivalentes aux noeuds par élément"),
            ),
            "SIEQ_NOEU": (("lin", "nonlin", "dyna"), tr("Contraintes équivalentes aux noeuds")),
        },
        Phenomenon.VARI_INTERNE: {
            "VARC_ELGA": (
                ("lin", "nonlin", "dyna"),
                tr("Variables de commande aux points de Gauss"),
            ),
            "VARC_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Variables de commande aux noeuds par élément"),
            ),
            "VARC_NOEU": (("lin", "nonlin", "dyna"), tr("Variables de commande aux noeuds")),
            "VARI_ELNO": (("nonlin", "dyna"), tr("Variables internes aux noeuds par élément")),
            "VARI_NOEU": (("nonlin", "dyna"), tr("Variables internes aux noeuds")),
        },
        Phenomenon.HYDRAULIQUE: {
            "FLHN_ELGA": (("nonlin", "dyna"), tr("Flux hydrauliques aux points de Gauss"))
        },
        Phenomenon.THERMIQUE: {
            "TEMP_ELGA": ((), tr("Température aux points de Gauss")),
            "FLUX_ELGA": ((), tr("Flux thermique aux points de Gauss")),
            "FLUX_ELNO": ((), tr("Flux thermique aux noeuds par élément")),
            "FLUX_NOEU": ((), tr("Flux thermique aux noeuds")),
            "GRAT_ELGA": ((), tr("Gradient thermique aux points de Gauss")),
            "GRAT_ELNO": ((), tr("Gradient thermique aux noeuds par élément")),
            "GRAT_NOEU": ((), tr("Gradient thermique aux noeuds")),
            "HYDR_ELGA": ((), tr("Hydratation aux points de Gauss")),
            "HYDR_ELNO": ((), tr("Hydratation aux noeuds par élément")),
            "HYDR_NOEU": ((), tr("Hydratation aux noeuds")),
            "SOUR_ELGA": ((), tr("Source de chaleur à partir d'un potentiel électrique")),
            "ETHE_ELEM": ((), tr("Énergie dissipée thermiquement")),
            "HHO_TEMP": ((), tr("Temparature reconstruite aux noeuds pour la modélisation HHO")),
        },
        Phenomenon.SECHAGE: {
            "FLUX_ELGA": ((), tr("Flux de séchage aux points de Gauss")),
            "FLUX_ELNO": ((), tr("Flux de séchage aux noeuds par élément")),
            "FLUX_NOEU": ((), tr("Flux de séchage aux noeuds")),
            "GRAT_ELGA": ((), tr("Gradient thermique aux points de Gauss")),
            "GRAT_ELNO": ((), tr("Gradient thermique aux noeuds par élément")),
            "GRAT_NOEU": ((), tr("Gradient thermique aux noeuds")),
            "DIFF_ELGA": ((), tr("Coefficients de diffusion aux points de Gauss")),
            "DIFF_ELNO": ((), tr("Coefficients de diffusion aux noeuds par élément")),
            "DIFF_NOEU": ((), tr("Coefficients de diffusion aux noeuds")),
            "HYGR_ELGA": ((), tr("Hygrométrie aux points de Gauss")),
            "HYGR_ELNO": ((), tr("Hygrométrie aux noeuds par élément")),
            "HYGR_NOEU": ((), tr("Hygrométrie aux noeuds")),
        },
        Phenomenon.ACOUSTIQUE: {
            "PRAC_ELNO": ((), tr("Pression acoustique aux noeuds par élément")),
            "PRAC_NOEU": ((), tr("Pression acoustique aux noeuds")),
            "PRME_ELNO": ((), tr("Pression aux noeuds par élément pour les éléments FLUIDE")),
            "INTE_ELNO": ((), tr("Intensité acoustique aux noeuds par élément")),
            "INTE_NOEU": ((), tr("Intensité acoustique aux noeuds")),
        },
        Phenomenon.FORCE: {
            "FORC_NODA": ((), tr("Forces nodales")),
            "REAC_NODA": ((), tr("Réactions nodales")),
        },
        Phenomenon.ERREUR: {
            "SIZ1_NOEU": ((), tr("Contraintes lissées de Zhu-Zienkiewicz version 1 aux noeuds")),
            "ERZ1_ELEM": ((), tr("Indicateur d'erreur de Zhu-Zienkiewicz version 1 par élément")),
            "SIZ2_NOEU": ((), tr("Contraintes lissées de Zhu-Zienkiewicz version 2 aux noeuds")),
            "ERZ2_ELEM": ((), tr("Indicateur d'erreur de Zhu-Zienkiewicz version 2 par élément")),
            "ERME_ELEM": ((), tr("Indicateur d'erreur en résidu en mécanique par élément")),
            "ERME_ELNO": (
                (),
                tr("Indicateur d'erreur en résidu en mécanique aux noeuds par élément"),
            ),
            "ERME_NOEU": ((), tr("Indicateur d'erreur en résidu en mécanique aux noeuds")),
            "QIRE_ELEM": (
                (),
                tr("Indicateur d'erreur en quantités d'intérêt en résidu par élément"),
            ),
            "QIRE_ELNO": (
                (),
                tr("Indicateur d'erreur en quantités d'intérêt en résidu aux noeuds par élément"),
            ),
            "QIRE_NOEU": (
                (),
                tr("Indicateur d'erreur en quantités d'intérêt en résidu aux noeuds"),
            ),
            "QIZ1_ELEM": (
                (),
                tr(
                    "Indicateur d'erreur en quantités d'intérêt de Zhu-Zienkiewicz version 1 par élément"
                ),
            ),
            "QIZ2_ELEM": (
                (),
                tr(
                    "Indicateur d'erreur en quantités d'intérêt de Zhu-Zienkiewicz version 2 par élément"
                ),
            ),
            "SING_ELEM": ((), tr("Degré de singularité par élément")),
            "SING_ELNO": ((), tr("Degré de singularité aux noeuds par élément")),
            "ERTH_ELEM": ((), tr("Indicateur d'erreur en résidu en thermique par élément")),
            "ERTH_ELNO": (
                (),
                tr("Indicateur d'erreur en résidu en thermique aux noeuds par élément"),
            ),
            "ERTH_NOEU": ((), tr("Indicateur d'erreur en résidu en thermique aux noeuds")),
        },
        Phenomenon.METALLURGIE: {
            "DURT_ELNO": ((), tr("Dureté aux noeuds par élément")),
            "DURT_NOEU": ((), tr("Dureté aux noeuds")),
            "META_ELNO": ((), tr("Proportion de phases métallurgiques aux noeuds par élément")),
            "META_NOEU": ((), tr("Proportion de phases métallurgiques aux noeuds")),
        },
        Phenomenon.DEPLACEMENT: {
            "ACCE": ((), tr("Accélération aux noeuds")),
            "ACCE_ABSOLU": ((), tr("Accélération absolue aux noeuds")),
            "DEPL": ((), tr("Déplacements aux noeuds")),
            "DEPL_ABSOLU": ((), tr("Déplacements absolus aux noeuds")),
            "HHO_DEPL": ((), tr("Déplacements reconstruits aux noeuds pour la modélisation HHO")),
            "TEMP": ((), tr("Température aux noeuds")),
            "VITE": ((), tr("Vitesse aux noeuds")),
            "HHO_VITE": ((), tr("Vitesse reconstruites aux noeuds pour la modélisation HHO")),
            "HHO_ACCE": ((), tr("Accélération reconstruites aux noeuds pour la modélisation HHO")),
            "CONT_NOEU": ((), tr("Statuts de contact aux noeuds")),
            "CONT_ELEM": ((), tr("Statuts de contact aux éléments (LAC)")),
            "VARI_ELGA": ((), tr("Variables internes aux points de Gauss")),
            "VITE_ABSOLU": ((), tr("Vitesse absolue aux noeuds")),
            "DEPL_ELGA": ((), tr("Déplacements aux sous-points")),
            "SECH": ((), tr("Séchage aux noeuds")),
            "SAUT_ELGA": (
                ("lin", "nonlin", "dyna"),
                tr("Sauts de déplacement aux points de Gauss pour la modélisation *_INTERF_POU"),
            ),
            "SAUT_ELNO": (
                ("lin", "nonlin", "dyna"),
                tr("Sauts de déplacement aux noeuds pour la modélisation *_INTERF_POU"),
            ),
            "SAUT_NOEU": (
                ("lin", "nonlin", "dyna"),
                tr("Sauts de déplacement moyennés aux noeuds pour la modélisation *_INTERF_POU"),
            ),
        },
        Phenomenon.PROPRIETES: {
            "MATE_ELGA": (
                ("lin", "nonlin", "dyna"),
                tr("Valeurs des paramètres matériaux élastiques aux points de Gauss"),
            ),
            "MATE_ELEM": (
                ("lin", "nonlin", "dyna"),
                tr("Valeurs des paramètres matériaux élastiques par élément"),
            ),
        },
        Phenomenon.AUTRES: {
            "COMPORTEMENT": ((), tr("Carte de comportement mécanique")),
            "COMPORTHER": ((), tr("Carte de comportement thermique")),
            "DEPL_VIBR": ((), tr("Déplacement pour mode vibratoire")),
            "DIVU": ((), tr("Déformation volumique en THM")),
            "EPSA_ELNO": ((), tr("Déformations anélastique aux noeuds par élément")),
            "EPSA_NOEU": ((), tr("Déformations anélastique aux noeuds")),
            "FERR_ELEM": (("lin",), tr("Densité de ferraillage")),
            "MARG_ELEM": (("lin",), tr("Marge mécanique - vérification de ferraillage")),
            "FSUR_2D": ((), tr("Chargement de force surfacique en 2D")),
            "FSUR_3D": ((), tr("Chargement de force surfacique en 3D")),
            "FVOL_2D": ((), tr("Chargement de force volumique en 2D")),
            "FVOL_3D": ((), tr("Chargement de force volumique en 3D")),
            "COEF_H": ((), tr("Coefficient d'échange constant par élément")),
            "T_EXT": ((), tr("Température extérieure constante par élément")),
            "IRRA": ((), tr("Irradition aux noeuds")),
            "MODE_FLAMB": ((), tr("Mode de flambement")),
            "MODE_STAB": ((), tr("Mode de stabilité")),
            "NEUT": ((), tr("Variable de commande 'neutre'")),
            "PRES": ((), tr("Chargement de pression")),
            "PRES_NOEU": (("lin", "nonlin"), tr("Pression aux noeuds")),
            "PTOT": ((), tr("Pression totale de fluide en THM")),
            "RESI_NOEU": ((), tr("Residus globaux aux noeuds")),
            "RESI_RELA_NOEU": ((), tr("Residus relatifs aux noeuds")),
            "SISE_ELNO": ((), tr("Contraintes aux noeuds par sous-élément")),
            "VITE_VENT": ((), tr("Chargement vitesse du vent")),
            "ROC1_ELNO": ((), tr("Champ principal issu de POST_ROCHE")),
            "ROC2_ELNO": ((), tr("Champ complémentaire issu de POST_ROCHE")),
            **{
                f"UT{str(i).zfill(2)}_{typ}": ((), tr(f"Champ utilisateur numéro {i}_{typ}"))
                for typ in ("ELGA", "ELNO", "ELEM", "NOEU", "CART")
                for i in range(1, 11)
            },
        },
    }

    nom_cham_to_phenomenon: Dict[str, str] = {
        cham: pheno for pheno, cham_data in nom_cham_into.items() for cham in cham_data
    }

    @classmethod
    def filter(
        cls,
        phenomena: Tuple[Phenomenon],
        category: Union[str, None],
        type_cham: Union[Tuple[str], None],
    ) -> Tuple[str]:
        """Effectue un filtre de tous les champs possibles en fonction des
        arguments fournis.

        Args:
            phenomena (Tuple[Phenomenon]): Phénomènes qui seront retenus dans le résultat.
            category (str | None): Catégorie surlaquelle il faut faire le filtre.
                Si elle vaut None, aucun filtre n'est fait.
            type_cham (Tuple[str] | None): Type de champs surlesquels il faut
                faire le filtre. Si la séquence est comprise dans le nom du
                champ, le champ est retenu. Si vaut None, aucun filtre n'est fait.

        Returns:
            Tuple[str]: Ensemble des champs qui correspondent à tous les filtres
        """

        # Filtre sur les phénomènes et les catégories
        l_cham = []
        for phen in phenomena:
            for cham in cls.nom_cham_into.get(phen):
                if not category or (category in cls.nom_cham_into.get(phen).get(cham)[0]):
                    l_cham.append(cham)

        l_cham = tuple(sorted(l_cham))

        # Filtre sur les type de champs
        if not type_cham:
            return l_cham

        return tuple(
            cham for cham in l_cham if any([t_cham in cham.split("_") for t_cham in type_cham])
        )


def C_NOM_CHAM_INTO(
    phenomene: Union[Phenomenon, Tuple[Phenomenon]] = None,
    categorie: str = None,
    type_cham: Union[str, Tuple[str]] = None,
    additional_fields: Tuple[str] = None,
) -> Tuple[str]:
    """Renvoie un iterable de tous les "into" possibles pour le mot-clé NOM_CHAM
    C'est-à-dire les noms des champs des SD RESULTAT (DATA de la routine RSCRSD).
    Il est possible de filtrer les résultats.

    Args:
        phenomene (Phenomenon | Tuple[Phenomenon], optional): Phénomènes surlequels
        il faut faire un filtre. Si None est passé ou que la liste est vide,
        aucun filtre n'est fait. Defaults to None.

        categorie (str, optional): Une catégorie surlaquelle il faut faire un filtre.
        Si None est passé, aucun filtre n'est fait. Defaults to None.

        type_cham (Tuple[str], optional): Type de champs surlesquels il faut
        faire le filtre. Si la séquence est comprise dans le nom du champ, le
        champ est retenu. Si vaut None, aucun filtre n'est fait. Defaults to None.

        additional_fields (Tuple[str], optional): Champs supplémentaires à fournir
        dans le "into". Si None est passé, aucun champ n'est ajouté. Defaults to None.

    Returns:
        Tuple[str] | Dict[str, Tuple[str, Tuple[str], str]]:
            Résultat de la fonction en fonction du mode de fonctionnement demandé
    """

    # --------- Gestion / Vérification des arguments ----------------------------

    # On vérifie que les phénomènes sont cohérents. Si aucun n'est donné, on
    #   les prends tous.
    if phenomene:
        _phenomena = (phenomene,) if isinstance(phenomene, Phenomenon) else phenomene
        Phenomenon.check_value_iterable(phenomena=_phenomena)
    else:
        _phenomena = tuple(Phenomenon)

    # Cast de type_cham dans un tuple
    _type_cham = (type_cham,) if isinstance(type_cham, str) else type_cham

    # ---------------------------- Filtrer les champs  -------------------------

    filtered_cham = NomChamIntoGenerator.filter(
        phenomena=_phenomena, category=categorie, type_cham=_type_cham
    )

    if not additional_fields:
        return filtered_cham

    # Renvoie les champs filtrés + les champs additionels s'ils existent
    return tuple(set(filtered_cham + tuple(nom_cham for nom_cham in additional_fields)))
