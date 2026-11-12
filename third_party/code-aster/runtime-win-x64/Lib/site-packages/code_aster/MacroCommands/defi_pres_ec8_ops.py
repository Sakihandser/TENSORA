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


"""Commande DEFI_PRES_EC8"""

import math
from scipy import special
from scipy import integrate
import numpy as np

from ..CodeCommands import FORMULE, CREA_TABLE
from ..Messages import UTMESS


def eps_n(R, r, H, n):
    """Calcul de eps_n=I1/I1'
        avec I1 : fonction de Bessel modifiee du premier ordre) et I1' sa dérivée

    Arguments:
        R (float): Rayon du réservoir
        r (float): Rayon du point courant
        H (float): Hauteur d'eau
        n (int): numéro de la fonction de Bessel (I1(n))

    Returns:
        float
    """

    eps_n = special.iv(1, (2 * n + 1) * math.pi * r / 2 / H) / special.ivp(
        1, (2 * n + 1) * math.pi * R / 2 / H
    )
    return eps_n


def bp_n(R, H, n):
    """
    Arguments:
        R (float): Rayon du réservoir
        H (float): Hauteur d'eau
        n (int): numéro de la fonction de Bessel
    Returns:
        float
    """

    bp_n = (
        8.0
        / math.pi**2
        * (-1) ** n
        * special.iv(1, (2 * n + 1) * math.pi * R / 2 / H)
        / ((2 * n + 1) ** 2 * special.ivp(1, (2 * n + 1) * math.pi * R / 2 / H))
    )
    return bp_n


def d_n(R, H, n):
    """
    Arguments:
        R (float): Rayon du réservoir
        H (float): Hauteur d'eau
        n (int): numéro de la fonction de Bessel
    Returns:
        float
    """

    f1 = lambda z, R, H, n: (
        math.sin(z * math.pi / 2.0 / H) * math.cos((2 * n + 1) * math.pi * z / 2.0 / H)
    )
    d_n = (
        4.0
        / math.pi
        * integrate.quad(f1, 0, H, args=(R, H, n))[0]
        * special.iv(1, (2 * n + 1) * math.pi * R / 2.0 / H)
        / (2 * n + 1)
        / special.ivp(1, (2 * n + 1) * math.pi * R / 2.0 / H)
        / H
    )
    return d_n


def f(H, z):
    """
    Arguments:
        H (float): Hauteur d'eau
        z (float): distance du point courant au fond du réservoir

    Returns:
        float
    """
    f = math.sin(z * math.pi / 2.0 / H)
    return f


def psi_nume0(z, rho_s, rho, H, R, N, Epais):
    """
    Arguments:
        z (float): distance du point courant au fond du réservoir
        rho_s (float): masse volumique de l'acier
        rho (float): masse volumique de l'eau
        H (float): Hauteur d'eau
        R (float): Rayon du réservoir
        N (int): borne supérieure de la sommation
        Epais (float): épaisseur de la virole au point courant

    Returns:
        float
    """

    psi_nume0 = rho_s * Epais / rho / H
    for n in range(0, N + 1):
        psi_nume0 = psi_nume0 + bp_n(R, H, n) * math.cos((2 * n + 1) * math.pi * z / 2 / H)
    return psi_nume0


def psi_denom0(z, rho_s, rho, H, R, N, Epais):
    """
    Arguments:
        z (float): distance du point courant au fond du réservoir
        rho_s (float): masse volumique de l'acier
        rho (float): masse volumique de l'eau
        H (float): Hauteur d'eau
        R (float): Rayon du réservoir
        N (int): borne supérieure de la sommation
        Epais (float): épaisseur de la virole au point courant

    Returns:
        float
    """
    psi_denom0 = rho_s * Epais / rho / H * f(H, z)
    for n in range(0, N + 1):
        psi_denom0 = psi_denom0 + d_n(R, H, n) * math.cos((2 * n + 1) * math.pi * z / 2 / H)
    return psi_denom0


def psi(z, rho_s, rho, H, R, N, Epais):
    """
    Arguments:
        z (float): distance du point courant au fond du réservoir
        rho_s (float): masse volumique de l'acier
        rho (float): masse volumique de l'eau
        H (float): Hauteur d'eau
        R (float): Rayon du réservoir
        N (int): borne supérieure de la sommation
        Epais (float): épaisseur de la virole au point courant

    Returns:
        float
    """
    psi_nume = lambda z, rho_s, rho, H, R, N, Epais: f(H, z) * psi_nume0(
        z, rho_s, rho, H, R, N, Epais
    )
    psi_denom = lambda z, rho_s, rho, H, R, N, Epais: f(H, z) * psi_denom0(
        z, rho_s, rho, H, R, N, Epais
    )
    psi = (
        integrate.quad(psi_nume, 0, H, args=(rho_s, rho, H, R, N, Epais))[0]
        / integrate.quad(psi_denom, 0, H, args=(rho_s, rho, H, R, N, Epais))[0]
    )
    return psi


def pseisc(
    x, y, zreel, R, H, rho, rho_s, Arh, Afhn, Afv, Arv, Ac1, N, Epais, Z0, g, pres_lib, newmark
):
    """Retourne la pression totale sur le réservoir, c'est une composition des
        pressions suivantes :

        pir : pression impulsive rigide (seisme horizontal)
        prv : pression impulsive rigide (seisme vertical)
        pif : pression impulsive flexible (seisme horiontal)
        pfv : pression impulsive flexible (seisme vertical)
        pc1 : pression convective (seisme horizontal)

    Arguments:
        x,y,zreel (float): coordonnées du point
        R (float): Rayon du réservoir
        H (float): Hauteur d'eau
        rho (float): masse volumique de l'eau
        rho_s (float): masse volumique de l'acier
        Arh (float): accéleration à période nulle du spectre horizontal
        Afhn (float): accéleration dans une des directions horizontales
        à la frequence impulsive de mode n, pour un amortissement de 4%
        Afv (float): accéleration verticale sur spectre à 4% d'amortissement
        à la fréquence impulsive verticale
        Arv (float): accéleration à periode nulle du spectre vertical
        Ac1 (float): accéleration horizontale sur le spectre a 0,5% d'amortissement
        à la fréquence convective de mode 1
        N (int): borne supérieure de sommation (utilisé dans calc_pif)
        Epais (float): épaisseur de la virole au point courant
        Z0 (float): coordonnée z du fond du réservoir
        g (float): accélération de la pesenteur
        pres_lib (float): pression à la surface libre
        newmark (str): Mode de combinaison des pressions verticales avec les pressions horizontales
    """

    if zreel < Z0:
        UTMESS("F", "CHARGES7_17", valr=[zreel, Z0])
    if zreel > H + Z0:
        ptot = pres_lib
    else:
        z = zreel - Z0

        # Initialisations
        nEC8 = NodeEC8(x, y, z, Epais, rho_s)

        tol = 0.01
        if nEC8.r > R * (1.0 + tol):
            UTMESS("F", "CHARGES7_19", valr=[nEC8.r, R, tol])

        nEC8.defiReservoir(R, H, rho, N)
        nEC8.defiSeisme(Arh, Afhn, Afv, Arv, Ac1)

        # Calculs
        nEC8.calc_pir()
        nEC8.calc_pif()
        nEC8.calc_pc1()
        nEC8.calc_prv()
        nEC8.calc_pfv()

        ptot = nEC8.calc_ptot(newmark)
        ptot = ptot + pres_lib
        ptot = ptot + nEC8.phydr(g)

    return ptot


class NodeEC8:
    def __init__(self, x, y, z, Epais, rho_s):
        """Initialise l'objet avec les informations liées au point

        Arguments:
            x,y,z (float): coordonnées du point par rapport au centre du fond du réservoir
            Epais (float): épaisseur de la virole au point courant
            rho_s (float): masse volumique de l'acier
        """
        self.z = z
        self.ep = Epais
        self.rhoAc = rho_s
        r = (x**2 + y**2) ** 0.5
        self.r = r

        if r**2 > 1.0e-6:
            theta = np.arccos(x / r)
        else:
            theta = 0.0
        self.theta = theta

    def defiReservoir(self, R, H, rho, N):
        """Infos liées au réservoir

        Arguments:
            R (float): Rayon du réservoir
            H (float): Hauteur d'eau
            rho (float): masse volumique de l'eau
            N (int): borne supérieure de sommation (utilisé dans calc_pif)
        """
        self.R = R
        self.H = H
        self.rhoLiq = rho
        self.N = N

    def defiSeisme(self, Arh, Afhn, Afv, Arv, Ac1):
        """Infos liées au séisme

        Arguments:
            Arh (float): accéleration à période nulle du spectre horizontal
            Afhn (float): accéleration dans une des directions horizontales
            à la frequence impulsive de mode n, pour un amortissement de 4%
            Afv (float): accéleration verticale sur spectre à 4% d'amortissement
            à la fréquence impulsive verticale
            Arv (float): accéleration à periode nulle du spectre vertical
            Ac1 (float): accéleration horizontale sur le spectre a 0,5% d'amortissement
            à la fréquence convective de mode 1
        """
        self.Arh = Arh
        self.Afhn = Afhn
        self.Afv = Afv
        self.Arv = Arv
        self.Ac1 = Ac1

    def calc_pir(self):
        """Calcul de la pression impulsive rigide horizontale DERESMA (B.5-53)"""
        self.pir = self.c0() * self.rhoLiq * self.Arh * self.H * math.cos(self.theta)

    def c0(self):
        """Composante de la pression impulsive rigide horizontale"""

        N = 20
        cc0 = 0.0
        if self.z <= self.H:
            for n in range(0, N + 1):
                cc0 = cc0 + 8.0 / math.pi**2 * (-1) ** n / (2 * n + 1) ** 2 * eps_n(
                    self.R, self.r, self.H, n
                ) * math.cos((2 * n + 1) * math.pi * self.z / 2 / self.H)
        return cc0

    def calc_pif(self):
        """
        Calcul  de la pression impulsive flexible générée par la composante horizontale
        du seisme DERESMA (B.5-56)
        """
        pif = 0.0
        if self.z <= self.H:
            for n in range(0, self.N + 1):
                pif = pif + self.rhoLiq * self.H * psi(
                    self.z, self.rhoAc, self.rhoLiq, self.H, self.R, self.N, self.ep
                ) * d_n(self.R, self.H, n) * math.cos(
                    (2 * n + 1) * math.pi * self.z / 2 / self.H
                ) * (
                    self.Afhn - self.Arh
                )

        self.pif = self.r / self.R * pif * math.cos(self.theta)

    def calc_pc1(self):
        """
        Calcul de la pression convective due au ballotement du fluide
        """
        pc1 = (
            0.8371
            * self.rhoLiq
            * self.R
            * math.cosh(1.841 * self.z / self.R)
            * special.jv(1, 1.841 * self.r / self.R)
            / special.jv(1, 1.841)
            / math.cosh(1.841 * self.H / self.R)
            * self.Ac1
        )
        self.pc1 = pc1 * math.cos(self.theta)

    def calc_prv(self):
        """
        Calcul de la pression impulsive rigide verticale DERESMA (B.5-55)
        """
        prv = self.rhoLiq * self.Arv * (self.H - self.z)
        self.prv = prv

    def calc_pfv(self):
        """
        Calcul de la pression impulsive flexible generee par le seisme vertical
        """

        if self.H / self.R > 0.8:
            f2 = 1.078 + 0.274 * math.log(self.H / self.R)
        else:
            f2 = 1.0

        pfv = (
            0.815
            * f2
            * self.H
            * self.rhoLiq
            * math.cos(math.pi * self.z / 2 / self.H)
            * (self.Afv - self.Arv)
        )

        self.pfv = pfv

    def phydr(self, g):
        """
        Calcul de la pression hydrostatique

        Arguments:
            g (float): accélération de la pesanteur

        Returns:
            float
        """
        ph = self.rhoLiq * g * (self.H - self.z)
        return ph

    def calc_ptot(self, newmark):
        """
        Calcul de la pression totale

        Arguments:
            newmark (str): Mode de combinaison des pressions verticales avec les pressions horizontales

        Returns:
            float
        """

        coef_newmark = 0.4
        if newmark == "PC-":
            coef_newmark = -coef_newmark

        ptot = math.copysign(
            ((self.pir + self.pif) ** 2.0 + self.pc1**2.0) ** 0.5, math.cos(self.theta)
        ) + coef_newmark * (self.prv + self.pfv)

        return ptot


def defi_pres_ec8_ops(
    self,
    Z_FOND,
    RAYON,
    HAUT_EAU,
    ACCE_SP_H,
    ACCE_FLEX_H_N,
    ACCE_FLEX_V,
    ACCE_SP_V,
    ACCE_CONV_H,
    RHO_EAU,
    PRES_SURF_LIBR,
    GRAVITE,
    NEWMARK,
    EVAL=None,
):
    """
    Macro-commande DEFI_PRES_EC8

    Arguments:
        Z_FOND (float): coordonnée Z du fond du réservoir
        RAYON (float): rayon du réservoir
        HAUT_EAU (float): hauteur d'eau dans le résevoir
        RHO_EAU (float): masse volumique de l'eau
        ACCE_SP_H (float): accélération à période nulle du spectre horizontal
        ACCE_FLEX_H_N (float): accélération à fréquence mode impulsif flexible horizontal n
        ACCE_FLEX_V (float): accélération à fréquence mode flexible vertical
        ACCE_SP_V (float): accélération à période nulle du spectre vertical
        ACCE_CONV_H (float): accélération à fréquence mode 1 convectif horizontale
        GRAVITE (float): accélération de la pesanteur
        NEWMARK (str): type de combinaison des pressions verticales avec les pressions horizontales
        EVAL (_F): information pour la construction des tables d'évaluation

    Returns:
        objet formule

    """

    # N est la borne supérieure de la sommation effectuée pour le
    # calcul de la pression impulsive flexible horizontale
    # on met N à 1 pour le moment bien que cela soit un point à
    # analyser. D'après les premiers tests, il serait plus précis d'aller
    # jusqu'à 10

    p_seis = FORMULE(
        VALE="pseisc(X,Y,Z,R,H,rho_l,RHO,Arh,Afhn,Afv,Arv,Ac1,1,EP,Z0,g,pres_lib,newmark)",
        NOM_PARA=("X", "Y", "Z", "EP", "RHO"),
        pseisc=pseisc,
        R=RAYON,
        H=HAUT_EAU,
        Arh=ACCE_SP_H,
        Afhn=ACCE_FLEX_H_N,
        Afv=ACCE_FLEX_V,
        Arv=ACCE_SP_V,
        Ac1=ACCE_CONV_H,
        rho_l=RHO_EAU,
        Z0=Z_FOND,
        g=GRAVITE,
        pres_lib=PRES_SURF_LIBR,
        newmark=NEWMARK,
    )

    if EVAL is not None:
        EVAL = list(EVAL)
        for ii, ev in enumerate(EVAL):
            list_ep = ev["LIST_EPAIS"]
            theta = ev["THETA"] * math.pi / 180.0

            if "LIST_H" in ev:
                list_H = ev["LIST_H"]
                if len(list_H) != len(list_ep):
                    UTMESS("F", "CHARGES7_18", vali=ii + 1)
                list_R = [RAYON] * len(list_H)
            else:
                list_R = ev["LIST_R_FOND"]
                if len(list_R) != len(list_ep):
                    UTMESS("F", "CHARGES7_18", vali=ii + 1)
                list_H = [0.0] * len(list_R)

            rho_s = ev["RHO"]

            list_pir = []
            list_pif = []
            list_pc1 = []
            list_prv = []
            list_pfv = []
            list_ptot = []
            list_phydr = []

            for i, h in enumerate(list_H):

                x = list_R[i] * math.cos(theta)
                y = list_R[i] * math.sin(theta)

                phydr = 0.0
                ptot = PRES_SURF_LIBR

                if h > HAUT_EAU:
                    nEC8 = NodeEC8(x, y, h, 0, rho_s)
                    nEC8.pir = 0.0
                    nEC8.pif = 0.0
                    nEC8.pc1 = 0.0
                    nEC8.prv = 0.0
                    nEC8.pfv = 0.0

                else:

                    # Initialisations
                    Epais = list_ep[i]

                    nEC8 = NodeEC8(x, y, h, Epais, rho_s)
                    nEC8.defiReservoir(RAYON, HAUT_EAU, RHO_EAU, 1)
                    nEC8.defiSeisme(ACCE_SP_H, ACCE_FLEX_H_N, ACCE_FLEX_V, ACCE_SP_V, ACCE_CONV_H)

                    # Calculs
                    nEC8.calc_pir()
                    nEC8.calc_pif()
                    nEC8.calc_pc1()
                    nEC8.calc_prv()
                    nEC8.calc_pfv()
                    phydr = nEC8.phydr(GRAVITE)
                    ptot = ptot + nEC8.calc_ptot(NEWMARK) + phydr

                list_phydr.append(phydr)
                list_pir.append(nEC8.pir)
                list_pif.append(nEC8.pif)
                list_pc1.append(nEC8.pc1)
                list_prv.append(nEC8.prv)
                list_pfv.append(nEC8.pfv)
                list_ptot.append(ptot)

            crea_table = [
                {"PARA": "H", "LISTE_R": list_H},
                {"PARA": "R", "LISTE_R": list_R},
                {"PARA": "THETA", "LISTE_R": [ev["THETA"]] * len(list_H)},
                {"PARA": "PIR", "LISTE_R": list_pir},
                {"PARA": "PIF", "LISTE_R": list_pif},
                {"PARA": "PC1", "LISTE_R": list_pc1},
                {"PARA": "PRV", "LISTE_R": list_prv},
                {"PARA": "PFV", "LISTE_R": list_pfv},
                {"PARA": "PHYDR", "LISTE_R": list_phydr},
                {"PARA": "PSURFLIB", "LISTE_R": [PRES_SURF_LIBR] * len(list_H)},
                {"PARA": "PTOT", "LISTE_R": list_ptot},
            ]

            tab = CREA_TABLE(LISTE=crea_table)

            self.register_result(tab, ev["TABLE"])

    return p_seis
