# coding: utf-8

# Copyright (C) 1991 - 2026  EDF www.code-aster.org
#
# This file is part of Code_Aster.
#
# Code_Aster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Code_Aster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Code_Aster.  If not, see <http://www.gnu.org/licenses/>.

from ..Messages import UTMESS
from ..Objects import ElementaryCharacteristics
from ..Supervis import ExecuteCommand
from ..Utilities import force_list
import numpy as np


class EltCharacteristicsAssignment(ExecuteCommand):
    """Command that assigns
    :class:`~code_aster.Objects.ElementaryCharacteristics` on a model.
    """

    command_name = "AFFE_CARA_ELEM"

    def create_result(self, keywords):
        """Initialize the result.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords.
        """
        self._result = ElementaryCharacteristics(keywords["MODELE"])

    # Retourne la valeur ou valdefaut : la même que dans affe_cara_elem
    def valeurCara(self, cara, Lcara, Lvale, valdefaut=None):
        """Retourne la valeur de la caractéristiques 'cara' dans 'Lcara'."""
        if cara in Lcara:
            return Lvale[Lcara.index(cara)]
        else:
            if valdefaut is not None:
                return valdefaut
            else:
                raise TypeError("Erreur de syntaxe dans la commande")

    def adapt_syntax(self, keywords):
        """Hook to adapt syntax *AFTER* syntax checking.

        Arguments:
            keywords (dict): Keywords arguments of user's keywords, changed
                in place.
        """
        # ---------------------------------------------------------------- MASSIF
        # Check that MASSIF appears once only if there is TOUT in MASSIF simple keywords
        if "MASSIF" in keywords:
            # Check that MASSIF appears once only if there is TOUT in MASSIF simple keywords
            l_dic_kws = keywords.get("MASSIF")
            if type(l_dic_kws) == tuple:  # il y a plus d'une occurrence de MASSIF
                for dic in l_dic_kws:
                    if "TOUT" in dic.keys():
                        UTMESS("F", "AFFECARAELEM_1")
        #
        # ---------------------------------------------------------------- CABLE
        # Création de VALE et CARA
        if "CABLE" in keywords:
            keywords["CABLE"] = force_list(keywords.get("CABLE", []))
            for ioc in range(len(keywords["CABLE"])):
                LesCables = keywords["CABLE"][ioc]
                if "AIRE" in LesCables:
                    aire = LesCables["AIRE"]
                    rayon = np.sqrt(aire / np.pi)
                    diame = rayon * 2.0
                if "RAYON" in LesCables:
                    rayon = LesCables["RAYON"]
                    aire = np.pi * np.square(rayon)
                    diame = rayon * 2.0
                if "DIAMETRE" in LesCables:
                    diame = LesCables["DIAMETRE"]
                    rayon = diame * 0.5
                    aire = np.pi * np.square(rayon)
                #
                n_init = LesCables["N_INIT"]
                #
                keywords["CABLE"][ioc]["CARA"] = ("AIRE", "RAYON", "DIAMETRE", "N_INIT")
                keywords["CABLE"][ioc]["VALE"] = (aire, rayon, diame, n_init)
        # ---------------------------------------------------------------- BARRE
        # Modification de VALE et CARA
        if "BARRE" in keywords:
            keywords["BARRE"] = force_list(keywords.get("BARRE", []))
            for ioc in range(len(keywords["BARRE"])):
                LaForme = keywords["BARRE"][ioc]["SECTION"]
                if LaForme == "CERCLE":
                    LesCara = force_list(keywords["BARRE"][ioc]["CARA"])
                    LesVale = force_list(keywords["BARRE"][ioc]["VALE"])
                    if "EP" not in LesCara:
                        LeRayon = LesVale[LesCara.index("R")]
                        LesCara.append("EP")
                        LesVale.append(LeRayon)
                        keywords["BARRE"][ioc]["CARA"] = LesCara
                        keywords["BARRE"][ioc]["VALE"] = LesVale
                elif LaForme == "RECTANGLE":
                    # "H", "EP", "HZ", "HY", "EPY", "EPZ"
                    LesCara = force_list(keywords["BARRE"][ioc]["CARA"])
                    LesVale = force_list(keywords["BARRE"][ioc]["VALE"])
                    if "H" in LesCara:
                        H = self.valeurCara("H", LesCara, LesVale)
                        EP = self.valeurCara("EP", LesCara, LesVale, H * 0.5)
                        HZ = H
                        HY = H
                        EPY = EP
                        EPZ = EP
                        LesCara = ["HZ", "HY", "EPY", "EPZ"]
                        LesVale = [HZ, HY, EPY, EPZ]
                        keywords["BARRE"][ioc]["CARA"] = LesCara
                        keywords["BARRE"][ioc]["VALE"] = LesVale
                    else:
                        HY = self.valeurCara("HY", LesCara, LesVale)
                        HZ = self.valeurCara("HZ", LesCara, LesVale)
                        EPY = self.valeurCara("EPY", LesCara, LesVale, HY * 0.5)
                        EPZ = self.valeurCara("EPZ", LesCara, LesVale, HZ * 0.5)
                        LesCara = ["HZ", "HY", "EPY", "EPZ"]
                        LesVale = [HZ, HY, EPY, EPZ]
                        keywords["BARRE"][ioc]["CARA"] = LesCara
                        keywords["BARRE"][ioc]["VALE"] = LesVale
                elif LaForme == "GENERALE":
                    IsAire = keywords["BARRE"][ioc].get("AIRE")
                    if IsAire:
                        Aire = keywords["BARRE"][ioc]["AIRE"]
                        LesCara = ["A"]
                        LesVale = [Aire]
                        keywords["BARRE"][ioc]["CARA"] = LesCara
                        keywords["BARRE"][ioc]["VALE"] = LesVale
        # ----------------------------------------------------------------


AFFE_CARA_ELEM = EltCharacteristicsAssignment.run
