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

from ..Messages import UTMESS
import numpy as np
import time
from ..Utilities.version import get_version
from ..Helpers import LogicalUnitFile

ORDRE_CONTRAINTES = {
    "PLAN": ["SIXX", "SIZZ", "SIXZ", "SIYY", "SIXY", "SIYZ"],
    "AXIS": ["SIXX", "SIYY", "SIXY", "SIZZ", "SIXZ", "SIYZ"],
    "3D": ["SIXX", "SIYY", "SIZZ", "SIXY", "SIXZ", "SIYZ"],
}

ETIQUETTES = {
    "PRESSION": "SIGM_P",
    "TORSION": "SIGM_T",
    "FLEXION_HP": "SIGM_HP",
    "FLEXION_P": "SIGM_FP",
    "TEMP": "TEMP",
    "CONTRAINTE": "SIGM",
}


class OAR_EF:
    def __init__(self, **args):
        """donnes d entrees : tables issues de la commande MACR_LIGN_COU"""

        self.charg = {
            "PRESSION": None,
            "TORSION": None,
            "FLEXION_HP": None,
            "FLEXION_P": None,
            "TEMP": None,
            "CONTRAINTE": None,
        }

        self.typefic = "meca"  # 2 possibilités : sortie 'meca' ou 'temp'
        self.ficsortie = None
        self.ordre = None
        self.modelisation = None
        self.titre = None

        self.instant_ther_non_imprimes = []
        self.instants_thermomecaniques = []

    def Tablenonvide(self):
        """renvoie une table non vide du dictionnaire des chargements"""
        for key in self.charg.keys():
            if self.charg[key] is not None:
                table = self.charg[key]
                break
        return table

    def supprime_doublons(self, liste_entree):
        """fonction utilitaire permettant de supprimer les doublons
        tout en conservant l'ordre de rencontre"""
        vu = set()
        resultat = []
        for item in liste_entree:
            if item not in vu:
                resultat.append(item)
                vu.add(item)
        return resultat

    def ajoutINST(self):
        """dans le cas d'un MACRO_LIGN_COUPE après MACRO_ELAS_MULT
         il n'y a pas d instants  on ajoute une liste d instants
        factice pour eviter le bug"""
        for key in self.charg.keys():
            if self.charg[key] is not None:
                try:
                    a = self.charg[key].values()["INST"][0]
                except:
                    self.charg[key]["INST"] = np.zeros(len(self.charg[key].values()["ABSC_CURV"]))

    @property
    def azimuts(self):
        """renvoie la liste des azimuts à imprimer sous forme de liste
        d'intitulés"""
        table = self.Tablenonvide()
        return self.supprime_doublons(table.values()["INTITULE"])

    @property
    def instants_thermiques(self):
        # determination liste des instants thermiques
        return self.supprime_doublons(self.charg["TEMP"].values()["INST"])

    def trouve_instants_thermomecaniques(self):
        """Renvoie la liste des instants ayant des contraintes"""
        for instant_ther in self.instants_thermiques:
            if (
                self.contraintes_azim(self.charg["CONTRAINTE"], self.azimuts[0], instant_ther)[
                    "SIXX"
                ].size
                == 0
            ):
                self.instant_ther_non_imprimes.append(instant_ther)
            else:
                self.instants_thermomecaniques.append(instant_ther)

    def abscisse_azim(self, azimut, source=None):
        """Renvoie les abscisses d'un azimut (intitulé de la table aster)"""
        if source:
            table = source
        else:
            table = self.Tablenonvide()
        table_reduite = table.INTITULE == azimut
        return self.supprime_doublons(table_reduite.values()["ABSC_CURV"])

    def contraintes_azim(self, macroc, intitule, instant):
        """renvoie un dictionnaire des contraintes
        pour un azimut/intitule donné"""
        macroreduit = macroc.INST == instant
        macrocr = macroreduit.INTITULE == intitule
        contraintes = {
            "SIXX": None,
            "SIYY": None,
            "SIZZ": None,
            "SIXY": None,
            "SIXZ": None,
            "SIYZ": None,
        }
        for cles in contraintes:
            try:
                contraintes[cles] = np.array(macrocr.values()[cles])
            except:
                # cas axisymétriques : certaines composantes peuvent manquer.
                # on les remplace alors par des listes nulles.
                contraintes[cles] = np.zeros(len(macrocr.values()["ABSC_CURV"]))
        return contraintes

    def temperatures_azim(self, macroc, azimut, instant):
        """renvoie la liste des temperatures
        pour un azimut (intitulé) à un instant donné"""
        macroreduit = macroc.INST == instant
        macrocr = macroreduit.INTITULE == azimut
        temperatures = np.array(macrocr.values()["TEMP"])
        return temperatures

    def ecrire_preambule(self, f):
        """écriture des lignes d'introduction du fichier de sortie"""
        f.write(f"; CODE_ASTER version {get_version()} \n")
        if self.typefic == "meca":
            f.write("; IMPRESSION AU FORMAT OAR - Modélisation mécanique \n")
            # f.write(f"; ORDRE D'IMPRESSION DES CONTRAINTES :{', '.join(ORDRE_CONTRAINTES['3D'])} \n")
        else:
            f.write(
                f"; IMPRESSION AU FORMAT OAR - Modélisation thermo-mécanique {self.modelisation} \n"
            )
            # f.write(f"; ORDRE D'IMPRESSION DES CONTRAINTES :{', '.join(ORDRE_CONTRAINTES[self.modelisation])} \n")
        f.write(f'; CREATION {time.strftime("LE %m/%d/%Y A %H:%M:%S")} \n \n')
        if self.titre is not None:
            f.write("; {} \n \n".format(self.titre))
        f.write("\n \n")

    def ecrire_abs(self, f, liste_abscisse):
        """écriture des abscisses à partir d'une liste d'abscisse dans un fichier de sortie"""
        f.write("ABSC \n ")
        for abscisse in liste_abscisse:
            f.write("  %.6e \n " % (abscisse))
        f.write("\n \n")

    def ecrire_contr(self, f, contraintes, etiquette):
        """écriture des contraintes - cas mécanique"""
        f.write(etiquette + "\n")
        # label = ORDRE_CONTRAINTES[self.modelisation]
        label = ORDRE_CONTRAINTES["3D"]
        header = (
            f";       {label[0]}            {label[1]}"
            + f"            {label[2]}            {label[3]}            {label[4]}"
            + f"            {label[5]} \n"
        )
        f.write(header)

        for i in range(len(contraintes[label[0]])):
            f.write(
                f"{contraintes[label[0]][i]:15.4E} {contraintes[label[1]][i]:15.4E}"
                f" {contraintes[label[2]][i]:15.4E} {contraintes[label[3]][i]:15.4E} "
                f"{contraintes[label[4]][i]:15.4E} {contraintes[label[5]][i]:15.4E} \n"
            )
        f.write("\n")

    def ecrire_temp(self, f, temperatures, contraintes):
        """écriture des températures et contraintes - cas thermique"""
        label = ORDRE_CONTRAINTES[self.modelisation]
        f.write(
            f"; TEMPERATURE             {label[0]}            {label[1]}"
            + f"            {label[2]}            {label[3]}            {label[4]}"
            + f"            {label[5]} \n"
        )
        for i in range(len(contraintes[label[0]])):
            f.write(
                f"    {temperatures[i]:5.1f}         "
                f"{contraintes[label[0]][i]:15.4E} {contraintes[label[1]][i]:15.4E}"
                f" {contraintes[label[2]][i]:15.4E} {contraintes[label[3]][i]:15.4E} "
                f"{contraintes[label[4]][i]:15.4E} {contraintes[label[5]][i]:15.4E} \n"
            )
        f.write("\n")

    def impression(self):
        """Impression proprement dite du rapport de sortie"""
        self.ajoutINST()

        with open(self.ficsortie, "a") as f:
            self.ecrire_preambule(f)

            if self.typefic == "meca":
                for azimut in self.azimuts:
                    f.write("; " + azimut + "\n \n")
                    abscisses = self.abscisse_azim(azimut)
                    self.ecrire_abs(f, abscisses)

                    for key in self.ordre:
                        if self.charg[key] is not None:
                            instant = self.charg[key].values()["INST"][-1]
                            contraintes = self.contraintes_azim(self.charg[key], azimut, instant)
                            self.ecrire_contr(f, contraintes, ETIQUETTES[key])

            if self.typefic == "temp":
                self.trouve_instants_thermomecaniques()
                # impression de la liste des instants
                f.write("; LISTE DES INSTANTS \n \n")
                f.write("INST \n \n")
                for instant in self.instants_thermomecaniques:
                    f.write("{} \n".format(instant))
                f.write("\n \n ; LISTE DES TEMPERATURES ET CONTRAINTES PAR COUPE \n \n")

                # impression
                for azimut in self.azimuts:
                    tableau_abs = self.abscisse_azim(azimut, source=self.charg["TEMP"])
                    f.write("; " + azimut + "\n \n")
                    self.ecrire_abs(f, tableau_abs)
                    f.write("TEMP SIGM \n \n")

                    for instant in self.instants_thermomecaniques:
                        f.write("; INSTANT {} \n \n".format(instant))
                        temperatures = self.temperatures_azim(self.charg["TEMP"], azimut, instant)
                        contraintes_ = self.contraintes_azim(
                            self.charg["CONTRAINTE"], azimut, instant
                        )
                        self.ecrire_temp(f, temperatures, contraintes_)
                        f.write("\n \n")

                if self.instant_ther_non_imprimes:
                    UTMESS("A", "OAR0_4", valk=", ".join(map(str, self.instant_ther_non_imprimes)))


def impr_oar_ops(self, **args):
    """
    Macro IMPR_OAR

    """
    resultat = OAR_EF()

    TABL_MECA = args.get("TABL_MECA")
    TABL_THER = args.get("TABL_THER")
    resultat.titre = args.get("TITRE")

    try:
        unite = args["UNITE"]
    except:
        UTMESS("F", "OAR0_1")

    resultat.ficsortie = LogicalUnitFile.filename_from_unit(unite)
    open(resultat.ficsortie, "w").close()  # on vide le fichier

    if (TABL_MECA is not None) and (TABL_THER is not None):
        UTMESS("F", "OAR0_2")

    if TABL_MECA is not None:
        resultat.modelisation = "3D"
        resultat.ordre = TABL_MECA[0].keys()
        for key in resultat.ordre:
            resultat.charg[key] = TABL_MECA[0][key].EXTR_TABLE()
        resultat.typefic = "meca"
        resultat.impression()

    if TABL_THER is not None:
        # ordre des contraintes
        modele = args.get("MODELE")
        if not modele.isMechanical():
            UTMESS("F", "OAR0_3")
        modelisation = modele.getModelisationName()
        if "PLAN" in modelisation:
            resultat.modelisation = "PLAN"
        elif "AXIS" in modelisation:
            resultat.modelisation = "AXIS"
        else:
            resultat.modelisation = "3D"

        resultat.charg["TEMP"] = TABL_THER[0]["TEMP"].EXTR_TABLE()
        resultat.charg["CONTRAINTE"] = TABL_THER[0]["CONTRAINTE"].EXTR_TABLE()
        resultat.typefic = "temp"
        resultat.impression()
