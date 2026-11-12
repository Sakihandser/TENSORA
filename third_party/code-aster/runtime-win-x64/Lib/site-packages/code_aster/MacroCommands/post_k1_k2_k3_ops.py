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


import copy
from math import pi

import numpy as NP

import aster
from ..Messages import UTMESS, MasquerAlarme

from ..Cata.Syntax import _F
from ..CodeCommands import (
    AFFE_MODELE,
    CALC_TABLE,
    CREA_MAILLAGE,
    CREA_TABLE,
    MACR_LIGN_COUPE,
    POST_RELEVE_T,
    PROJ_CHAMP,
)
from ..Objects import ModeResult
from ..Utilities.misc import get_titre_concept
from .Fracture.post_k_varc import POST_K_VARC


# ---------------------------------------------------------------------------------------------------------------
#                 FONCTIONS UTILITAIRES
# -------------------------------------------------------------------------
# def cross_product(a,b):
#     cross = [0]*3
#     cross[0] = a[1]*b[2]-a[2]*b[1]
#     cross[1] = a[2]*b[0]-a[0]*b[2]
#     cross[2] = a[0]*b[1]-a[1]*b[0]
#     return cross
# -------------------------------------------------------------------------
def normalize(v):
    norm = NP.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    return v / norm


# -------------------------------------------------------------------------


def complete(Tab):
    n = len(Tab)
    for i in range(n):
        if Tab[i] is None:
            Tab[i] = 0.0
    return Tab


# ---------------------------------------------------------------------------------------------------------------
# sam : la methode average(t) ne repond-elle pas au besoin ?
def moy(t):
    m = 0
    for value in t:
        m += value
    return m / len(t)


# -------------------------------------------------------------------------


def InterpolFondFiss(s0, Coorfo):
    # Interpolation des points du fond de fissure (xfem)
    # s0     = abscisse curviligne du point considere
    # Coorfo = Coordonnees du fond (extrait de la sd fiss_xfem)
    # en sortie : xyza = Coordonnees du point et abscisse
    if s0 < Coorfo[3]:
        xyz = [Coorfo[0], Coorfo[1], Coorfo[2], s0]
        return xyz
    if s0 > Coorfo[-1]:
        xyz = [Coorfo[-4], Coorfo[-3], Coorfo[-2], s0]
        return xyz
    i = 1
    while s0 > Coorfo[4 * i + 3]:
        i = i + 1
    xyz = [0.0] * 4
    xyz[0] = (s0 - Coorfo[4 * (i - 1) + 3]) * (Coorfo[4 * i + 0] - Coorfo[4 * (i - 1) + 0]) / (
        Coorfo[4 * i + 3] - Coorfo[4 * (i - 1) + 3]
    ) + Coorfo[4 * (i - 1) + 0]
    xyz[1] = (s0 - Coorfo[4 * (i - 1) + 3]) * (Coorfo[4 * i + 1] - Coorfo[4 * (i - 1) + 1]) / (
        Coorfo[4 * i + 3] - Coorfo[4 * (i - 1) + 3]
    ) + Coorfo[4 * (i - 1) + 1]
    xyz[2] = (s0 - Coorfo[4 * (i - 1) + 3]) * (Coorfo[4 * i + 2] - Coorfo[4 * (i - 1) + 2]) / (
        Coorfo[4 * i + 3] - Coorfo[4 * (i - 1) + 3]
    ) + Coorfo[4 * (i - 1) + 2]
    xyz[3] = s0
    return xyz


# -------------------------------------------------------------------------


def InterpolBaseFiss(s0, Basefo, Coorfo):
    # Interpolation de la base locale en fond de fissure
    # s0     = abscisse curviligne du point considere
    # Basefo = base locale du fond (VNORx,VNORy,VNORz,VDIRx,VDIRy,VDIRz)
    # Coorfo = Coordonnees et abscisses du fond (extrait de la sd fiss_xfem)
    # en sortie : VDIRVNORi = base locale au point considere (6 coordonnes)
    if s0 < Coorfo[3]:
        VDIRVNORi = Basefo[0:6]
        return VDIRVNORi
    if s0 > Coorfo[-1]:
        VDIRVNORi = [Basefo[i] for i in range(-6, 0)]
        return VDIRVNORi
    i = 1
    while s0 > Coorfo[4 * i + 3]:
        i = i + 1
    VDIRVNORi = [0.0] * 6
    for k in range(6):
        VDIRVNORi[k] = (s0 - Coorfo[4 * (i - 1) + 3]) * (
            Basefo[6 * i + k] - Basefo[6 * (i - 1) + k]
        ) / (Coorfo[4 * i + 3] - Coorfo[4 * (i - 1) + 3]) + Basefo[6 * (i - 1) + k]
    return VDIRVNORi


# -------------------------------------------------------------------------


def InterpolScalFiss(s0, Scalfo, Coorfo):
    # Interpolation d'une variable scalaire en fond de fissure
    # s0     = abscisse curviligne du point considere
    # Coorfo = Coordonnees et abscisses du fond (extrait de la sd fiss_xfem)
    # Scalfo = liste des valeurs de la variable scalaire selon les points de Coorfo
    # en sortie : Vale = valeur de la variable scalaire au point considere
    if s0 < Coorfo[3]:
        Vale = Scalfo[0]
        return Vale
    if s0 > Coorfo[-1]:
        Vale = Scalfo[-1]
        return Vale
    i = 1
    while s0 > Coorfo[4 * i + 3]:
        i = i + 1
    Vale = (s0 - Coorfo[4 * (i - 1) + 3]) * (Scalfo[i] - Scalfo[i - 1]) / (
        Coorfo[4 * i + 3] - Coorfo[4 * (i - 1) + 3]
    ) + Scalfo[i - 1]
    return Vale


# -------------------------------------------------------------------------


def expand_values(self, tabout, liste_noeu_a_extr, titre, type_para):
    # Lorsqu'il n'y a pas suffisament de noeud pour le calcul des KJ, on extrapole
    # attention cela n'est valable que pour une seule fissure a la fois

    extrtabout = tabout.EXTR_TABLE()

    # Recuperation des points
    points_expand = extrtabout.values()["NUM_PT"]
    # Recuperation des abscisses
    abscisses_expand = extrtabout.values()["ABSC_CURV"]
    # Recuperation des instants
    instants_expand = extrtabout.values()[type_para]
    # Recuperation des K1,K2,K3,ERR_K1,ERR_K2,ERR_K1,
    size = len(abscisses_expand)
    K1 = extrtabout.values()["K1"]
    ERR_K1 = extrtabout.values()["ERR_K1"]
    K2 = extrtabout.values()["K2"]
    ERR_K2 = extrtabout.values()["ERR_K2"]
    K3 = extrtabout.values()["K3"]
    ERR_K3 = extrtabout.values()["ERR_K3"]
    G = extrtabout.values()["G"]
    # Recuperation de TEMP,NEUT1
    if "TEMP" in extrtabout.para:
        TEMP = extrtabout.values()["TEMP"]
    if "NEUT1" in extrtabout.para:
        NEUT1 = extrtabout.values()["NEUT1"]

    for i in range(size):
        if points_expand[i] - 1 in liste_noeu_a_extr:
            k_retenu = []
            for sign in [-1, 1]:
                trouve = 0
                k = 1 * sign
                while trouve == 0 and i + k < size and k + i > 0:
                    if (
                        points_expand[i + k] - 1 not in liste_noeu_a_extr
                        and instants_expand[i] == instants_expand[i + k]
                    ):
                        k_retenu.append(k + i)
                        trouve = 1
                    k = k + 1 * sign
            assert len(k_retenu) <= 2
            if len(k_retenu) == 2:
                distance_gauche = abs(abscisses_expand[i] - abscisses_expand[k_retenu[0]])
                distance_droite = abs(abscisses_expand[i] - abscisses_expand[k_retenu[1]])
                if distance_gauche < distance_droite:
                    k_retenu = [k_retenu[0]]
                else:
                    k_retenu = [k_retenu[1]]

            K1[i] = K1[k_retenu[0]]
            ERR_K1[i] = ERR_K1[k_retenu[0]]
            K2[i] = K2[k_retenu[0]]
            ERR_K2[i] = ERR_K2[k_retenu[0]]
            K3[i] = K3[k_retenu[0]]
            ERR_K3[i] = ERR_K3[k_retenu[0]]
            G[i] = G[k_retenu[0]]
            if "TEMP" in extrtabout.para:
                TEMP[i] = TEMP[k_retenu[0]]
            if "NEUT1" in extrtabout.para:
                NEUT1[i] = NEUT1[k_retenu[0]]
            liste_noeu_a_extr.remove(points_expand[i] - 1)

    liste = []
    for para, typ in zip(
        (
            "FISSURE",
            "FOND_FISS",
            "NUME_FOND",
            "NUME_ORDRE",
            "INST",
            "FREQ",
            "NOEUD",
            "NUM_PT",
            "COOR_X",
            "COOR_Y",
            "COOR_Z",
            "ABSC_CURV",
        ),
        ("K", "K", "I", "I", "R", "R", "K", "I", "R", "R", "R", "R"),
    ):
        if para in extrtabout.para:
            liste.append({"LISTE_%s" % typ: extrtabout.values()[para], "PARA": para})

    if "TEMP" in extrtabout.para:
        liste.append({"LISTE_R": TEMP, "PARA": "TEMP"})
    if "NEUT1" in extrtabout.para:
        liste.append({"LISTE_R": NEUT1, "PARA": "NEUT1"})
    liste.append({"LISTE_R": G, "PARA": "G"})
    liste.append({"LISTE_R": K1, "PARA": "K1"})
    liste.append({"LISTE_R": ERR_K1, "PARA": "ERR_K1"})
    liste.append({"LISTE_R": K2, "PARA": "K2"})
    liste.append({"LISTE_R": ERR_K2, "PARA": "ERR_K2"})
    liste.append({"LISTE_R": K3, "PARA": "K3"})
    liste.append({"LISTE_R": ERR_K3, "PARA": "ERR_K3"})

    tabout = CREA_TABLE(TITRE=titre, LISTE=liste)

    return tabout


# -------------------------------------------------------------------------


def verif_config_init(FOND_FISS):
    if FOND_FISS.getConfigInit() != "COLLEE":
        UTMESS("F", "RUPTURE0_16")


# -------------------------------------------------------------------------


def get_displacement_name(result):
    """retourne le nom du champ DEPL du resultat à utiliser"""
    if result.getModel().existsHHO():
        return "HHO_DEPL"

    return "DEPL"


# -------------------------------------------------------------------------


def get_noeud_fond_fiss(FOND_FISS):
    """retourne la liste des noeuds de FOND_FISS"""
    Lnoff = FOND_FISS.getCrackFrontNodes()
    if Lnoff is None:
        UTMESS("F", "RUPTURE0_11")
    return Lnoff


# -------------------------------------------------------------------------


def get_noeud_a_calculer(Lnoff, ndim, FOND_FISS, MAILLAGE, EnumTypes, args):
    """retourne la liste des noeuds de FOND_FISS a calculer"""
    GROUP_NO = args.get("GROUP_NO")
    SANS_GROUP_NO = args.get("SANS_GROUP_NO")
    TOUT = args.get("TOUT")

    if ndim == 2:
        Lnocal = Lnoff
        assert len(Lnocal) == 1

    elif ndim == 3:
        #        construction de la liste des noeuds "AVEC" et des noeuds "SANS"
        NO_SANS = []
        NO_AVEC = []

        if GROUP_NO is not None:
            if type(GROUP_NO) not in EnumTypes:
                GROUP_NO = (GROUP_NO,)

            for grpno in GROUP_NO:
                if grpno not in MAILLAGE.getGroupsOfNodes():
                    UTMESS("F", "RUPTURE0_13", valk=grpno)
                for node in MAILLAGE.getNodes(grpno, localNumbering=True):
                    NO_AVEC.append(str(node + 1))
            NO_AVEC = list(map(lambda x: x.rstrip(), NO_AVEC))
        else:
            if (MAILLAGE.isQuadratic()) and (TOUT is None):
                NO_AVEC = Lnoff[::2]
            else:
                NO_AVEC = Lnoff

        if SANS_GROUP_NO is not None:
            if type(SANS_GROUP_NO) not in EnumTypes:
                SANS_GROUP_NO = (SANS_GROUP_NO,)
            for grpno in SANS_GROUP_NO:
                if grpno not in MAILLAGE.getGroupsOfNodes():
                    UTMESS("F", "RUPTURE0_13", valk=grpno)
                for node in MAILLAGE.getNodes(grpno, localNumbering=True):
                    NO_SANS.append(str(node + 1))
            NO_SANS = list(map(lambda x: x.rstrip(), NO_SANS))

        # verification que les noeuds "AVEC" et "SANS" appartiennent au fond de
        # fissure
        set_tmp = set(NO_AVEC) - set(Lnoff)
        if set_tmp:
            UTMESS("F", "RUPTURE0_15", valk=list(set_tmp)[0])
        set_tmp = set(NO_SANS) - set(Lnoff)
        if set_tmp:
            UTMESS("F", "RUPTURE0_15", valk=list(set_tmp)[0])

        #       Creation de la liste des noeuds a garder reeordonnee selon l'ordre de Lnoff
        Lnocal = tuple([val for val in Lnoff if (val in NO_AVEC) and (val not in NO_SANS)])

    return Lnocal


# -------------------------------------------------------------------------


def get_coor_libre(self, Lnoff, RESULTAT, ndim):
    """retourne les coordonnees des noeuds de FOND_FISS en dictionnaire"""

    __NCOFON = POST_RELEVE_T(
        ACTION=_F(
            INTITULE="Tab pour coordonnees noeuds du fond",
            NOEUD=Lnoff,
            RESULTAT=RESULTAT,
            NOM_CHAM=get_displacement_name(RESULTAT),
            NUME_ORDRE=1,
            NOM_CMP=("DX",),
            OPERATION="EXTRACTION",
        )
    )

    tcoorf = __NCOFON.EXTR_TABLE()
    nbt = len(tcoorf["NOEUD"].values()["NOEUD"])
    xs = NP.array(tcoorf["COOR_X"].values()["COOR_X"][:nbt])
    ys = NP.array(tcoorf["COOR_Y"].values()["COOR_Y"][:nbt])
    if ndim == 2:
        zs = NP.zeros(nbt)
    elif ndim == 3:
        zs = NP.array(tcoorf["COOR_Z"].values()["COOR_Z"][:nbt])
    ns = tcoorf["NOEUD"].values()["NOEUD"][:nbt]
    ns = list(map(lambda x: x.rstrip(), ns))
    l_coorf = [[ns[i], xs[i], ys[i], zs[i]] for i in range(0, nbt)]
    l_coorf = [(i[0], i[1:]) for i in l_coorf]
    return dict(l_coorf)


# -------------------------------------------------------------------------


def get_direction(Nnoff, ndim, Lnoff, FOND_FISS, MAILLAGE):
    """retourne les normales en chaque point du fond (VNOR)
    et les vecteurs de direction de propagation (VDIR)"""

    # cette fonction retourne 2 dictionnaires, il faudrait mettre
    # en conformite avec get_direction_xfem

    # On récupère ces informations dans BASELOC
    # Attendtion à l'odre des veccteurs dans BASELOC
    basloc = FOND_FISS.getCrackFrontNodeBasis().getValues()

    # extraction, à partir de baseloc, un objet basefon reduit aux noeud
    # du fonr tde fissure.
    nb_comp_basloc = 3 * ndim
    # suppresion des coordonnées du projeté du noeud, non utilisées ici
    basloc = NP.array(basloc).reshape((len(basloc) // nb_comp_basloc), nb_comp_basloc)[:, ndim:]
    #   recuperation des valeurs dans baseloc en indexant sur les noeuds du fond de fissure
    index_by_nodename = {str(i + 1): i for i in MAILLAGE.getNodes(localNumbering=True)}
    Basefo = basloc[[index_by_nodename[nodename] for nodename in Lnoff], :].flatten()

    VNOR = [None] * Nnoff
    VDIR = [None] * Nnoff

    if ndim == 2:
        VDIR[0] = NP.array([Basefo[0], Basefo[1], 0.0])
        VNOR[0] = NP.array([Basefo[2], Basefo[3], 0.0])
        dicVDIR = dict([(Lnoff[0], VDIR[0])])
        dicVNOR = dict([(Lnoff[0], VNOR[0])])
    elif ndim == 3:
        VNOR[0] = NP.array([Basefo[3], Basefo[4], Basefo[5]])
        VDIR[0] = NP.array([Basefo[0], Basefo[1], Basefo[2]])

        for i in range(1, Nnoff - 1):
            VDIR[i] = NP.array([Basefo[6 * i], Basefo[6 * i + 1], Basefo[6 * i + 2]])
            VNOR[i] = NP.array([Basefo[3 + 6 * i], Basefo[3 + 6 * i + 1], Basefo[3 + 6 * i + 2]])

        i = Nnoff - 1
        VNOR[i] = NP.array([Basefo[3 + 6 * i], Basefo[3 + 6 * i + 1], Basefo[3 + 6 * i + 2]])
        VDIR[i] = NP.array([Basefo[6 * i], Basefo[6 * i + 1], Basefo[6 * i + 2]])

        dicVDIR = dict([(Lnoff[i], VDIR[i]) for i in range(Nnoff)])
        dicVNOR = dict([(Lnoff[i], VNOR[i]) for i in range(Nnoff)])

    return (dicVDIR, dicVNOR)


# -------------------------------------------------------------------------


def get_tab_dep(
    self,
    Lnocal,
    Nnocal,
    d_coor,
    dicVDIR,
    RESULTAT,
    MODEL,
    gr_maS,
    gr_maI,
    NB_NOEUD_COUPE,
    hmax,
    is_symmetric,
    PREC_VIS_A_VIS,
):
    """retourne les tables des deplacements sup et inf pour les noeuds perpendiculaires pour
    tous les points du fond de fissure"""

    dmax = hmax * PREC_VIS_A_VIS

    mcfact = []
    for i in range(Nnocal):
        Porig = NP.array(d_coor[Lnocal[i]])
        Pextr = Porig - hmax * dicVDIR[Lnocal[i]]

        mcfact.append(
            _F(
                NB_POINTS=NB_NOEUD_COUPE,
                COOR_ORIG=(Porig[0], Porig[1], Porig[2]),
                TYPE="SEGMENT",
                COOR_EXTR=(Pextr[0], Pextr[1], Pextr[2]),
                DISTANCE_MAX=dmax,
            )
        )

    __TlibS = MACR_LIGN_COUPE(
        RESULTAT=RESULTAT,
        NOM_CHAM=get_displacement_name(RESULTAT),
        MODELE=MODEL,
        VIS_A_VIS=_F(GROUP_MA_1=gr_maS),
        LIGN_COUPE=mcfact,
    )

    if not is_symmetric:
        __TlibI = MACR_LIGN_COUPE(
            RESULTAT=RESULTAT,
            NOM_CHAM=get_displacement_name(RESULTAT),
            MODELE=MODEL,
            VIS_A_VIS=_F(GROUP_MA_1=gr_maI),
            LIGN_COUPE=mcfact,
        )
        result = __TlibI.EXTR_TABLE()
    else:
        result = None

    return (__TlibS.EXTR_TABLE(), result)


# -------------------------------------------------------------------------


def get_dico_levres(lev, FOND_FISS, ndim, Lnoff, Nnoff):
    "retourne ???" ""
    if lev == "sup":
        Nnorm = FOND_FISS.getUpperNormNodes()
        if not Nnorm:
            UTMESS("F", "RUPTURE0_19")
    elif lev == "inf":
        Nnorm = FOND_FISS.getLowerNormNodes()

    # pourquoi modifie t-on Nnoff dans ce cas, alors que rien n'est fait pour
    # les maillages libres ?
    if Lnoff[0] == Lnoff[-1] and ndim == 3:
        Nnoff = Nnoff - 1  # Cas fond de fissure ferme
    Nnorm = [[Lnoff[i], Nnorm[i * 20 : (i + 1) * 20]] for i in range(0, Nnoff)]
    Nnorm = [(i[0], i[1][0:]) for i in Nnorm]
    return dict(Nnorm)


# -------------------------------------------------------------------------


def get_coor_regle(self, RESULTAT, ndim, Lnoff, Lnocal, dicoS, is_symmetric, dicoI):
    """retourne le dictionnaire des coordonnees des noeuds des lèvres pour les maillages regles"""

    #        a eclaircir
    Ltot = copy.copy(Lnoff)
    for ino in Lnocal:
        l = [elem for elem in dicoS[ino] if elem != ""]
        Ltot += l
    if not is_symmetric:
        for ino in Lnocal:
            l = [elem for elem in dicoI[ino] if elem != ""]
            Ltot += l

    Ltot = list(set(Ltot))

    dico = RESULTAT.getAccessParameters()

    if ndim == 2:
        nomcmp = ("DX", "DY")
    elif ndim == 3:
        nomcmp = ("DX", "DY", "DZ")

    __NCOOR = POST_RELEVE_T(
        ACTION=_F(
            INTITULE="Tab pour coordonnees noeuds des levres",
            NOEUD=Ltot,
            RESULTAT=RESULTAT,
            NOM_CHAM=get_displacement_name(RESULTAT),
            NOM_CMP=nomcmp,
            OPERATION="EXTRACTION",
        )
    )

    tcoor = __NCOOR.EXTR_TABLE().NUME_ORDRE == dico["NUME_ORDRE"][0]

    nbt = len(tcoor["NOEUD"].values()["NOEUD"])
    xs = NP.array(tcoor["COOR_X"].values()["COOR_X"][:nbt])
    ys = NP.array(tcoor["COOR_Y"].values()["COOR_Y"][:nbt])
    if ndim == 2:
        zs = NP.zeros(nbt)
    elif ndim == 3:
        zs = NP.array(tcoor["COOR_Z"].values()["COOR_Z"][:nbt])
    ns = tcoor["NOEUD"].values()["NOEUD"][:nbt]
    ns = list(map(lambda x: x.rstrip(), ns))
    l_coor = [[ns[i], xs[i], ys[i], zs[i]] for i in range(nbt)]
    l_coor = [(i[0], i[1:]) for i in l_coor]
    return (dict(l_coor), __NCOOR.EXTR_TABLE())


# -------------------------------------------------------------------------


def get_absfon(Lnoff, Nnoff, d_coor):
    """retourne le dictionnaire des Abscisses curvilignes du fond"""
    absfon = [0]
    for i in range(Nnoff - 1):
        Pfon1 = NP.array([d_coor[Lnoff[i]][0], d_coor[Lnoff[i]][1], d_coor[Lnoff[i]][2]])
        Pfon2 = NP.array(
            [d_coor[Lnoff[i + 1]][0], d_coor[Lnoff[i + 1]][1], d_coor[Lnoff[i + 1]][2]]
        )
        absf = NP.sqrt(NP.dot(NP.transpose(Pfon1 - Pfon2), Pfon1 - Pfon2)) + absfon[i]
        absfon.append(absf)
    return dict([(Lnoff[i], absfon[i]) for i in range(Nnoff)])


# -------------------------------------------------------------------------


def get_noeuds_perp_regle(Lnocal, d_coor, dicoS, dicoI, Lnoff, PREC_VIS_A_VIS, hmax, is_symmetric):
    """retourne la liste des noeuds du fond (encore ?), la liste des listes des noeuds perpendiculaires"""

    NBTRLS = 0
    NBTRLI = 0
    Lnosup = [None] * len(Lnocal)
    Lnoinf = [None] * len(Lnocal)
    Nbnofo = 0
    Lnofon = []

    rmprec = hmax * (1.0 + PREC_VIS_A_VIS / 10.0)
    precn = PREC_VIS_A_VIS * hmax

    for ino in Lnocal:
        Pfon = NP.array([d_coor[ino][0], d_coor[ino][1], d_coor[ino][2]])
        Tmpsup = []
        Tmpinf = []
        itots = 0
        itoti = 0
        NBTRLS = 0
        NBTRLI = 0
        for k in range(20):
            if dicoS[ino][k] != "":
                itots = itots + 1
                Nsup = dicoS[ino][k]
                Psup = NP.array([d_coor[Nsup][0], d_coor[Nsup][1], d_coor[Nsup][2]])
                abss = NP.sqrt(NP.dot(NP.transpose(Pfon - Psup), Pfon - Psup))
                if abss < rmprec:
                    NBTRLS = NBTRLS + 1
                    Tmpsup.append(dicoS[ino][k])
            if not is_symmetric:
                if dicoI[ino][k] != "":
                    itoti = itoti + 1
                    Ninf = dicoI[ino][k]
                    Pinf = NP.array([d_coor[Ninf][0], d_coor[Ninf][1], d_coor[Ninf][2]])
                    #                 On verifie que les noeuds sont en vis a vis
                    if abss < rmprec:
                        dist = NP.sqrt(NP.dot(NP.transpose(Psup - Pinf), Psup - Pinf))
                        if dist > precn:
                            UTMESS("A", "RUPTURE0_21", valk=ino)
                        else:
                            NBTRLI = NBTRLI + 1
                            Tmpinf.append(dicoI[ino][k])
        #        On verifie qu il y a assez de noeuds
        if NBTRLS < 3:
            UTMESS("A+", "RUPTURE0_22", valk=ino)
            if ino == Lnoff[0] or ino == Lnoff[-1]:
                UTMESS("A+", "RUPTURE0_23")
            if itots < 3:
                UTMESS("A", "RUPTURE0_24")
            else:
                UTMESS("A", "RUPTURE0_25")
        elif (not is_symmetric) and (NBTRLI < 3):
            UTMESS("A+", "RUPTURE0_26", valk=ino)
            if ino == Lnoff[0] or ino == Lnoff[-1]:
                UTMESS("A+", "RUPTURE0_23")
            if itoti < 3:
                UTMESS("A", "RUPTURE0_24")
            else:
                UTMESS("A", "RUPTURE0_25")
        else:
            Lnosup[Nbnofo] = Tmpsup
            if not is_symmetric:
                Lnoinf[Nbnofo] = Tmpinf
            Lnofon.append(ino)
            Nbnofo = Nbnofo + 1
    if Nbnofo == 0:
        UTMESS("F", "RUPTURE0_30")

    return (Lnofon, Lnosup, Lnoinf)


# -------------------------------------------------------------------------


def verif_resxfem(self, RESULTAT):
    """verifie que le resultat est bien compatible avec X-FEM et renvoie xcont et MODEL"""

    MODEL = RESULTAT.getModel()
    xcont = MODEL.getXfemContact()
    return (xcont, MODEL)


# -------------------------------------------------------------------------


def get_resxfem(self, xcont, RESULTAT, MODELISATION, MODEL):
    """retourne le resultat"""

    if xcont != 3:
        __RESX = RESULTAT

    #     XFEM + contact : il faut reprojeter sur le maillage lineaire
    elif xcont == 3:
        __mail1 = RESULTAT.getModel().getMesh()
        __mail2 = CREA_MAILLAGE(MAILLAGE=__mail1, QUAD_LINE=_F(TOUT="OUI"))

        __MODLINE = AFFE_MODELE(
            MAILLAGE=__mail2,
            AFFE=(_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION=MODELISATION),),
        )

        __RESX = PROJ_CHAMP(
            METHODE="COLLOCATION",
            TYPE_CHAM="NOEU",
            NOM_CHAM="DEPL",
            RESULTAT=RESULTAT,
            MODELE_1=MODEL,
            MODELE_2=__MODLINE,
        )

    # Rq : on ne peut pas détruire __MODLINE ici car on en a besoin lors du
    # MACR_LIGN_COUP qui suivra
    return __RESX


# -------------------------------------------------------------------------


def get_coor_xfem(args, FISSURE, ndim):
    """retourne la liste des coordonnees des points du fond, la base locale en fond et le nombre de points"""

    Listfo = FISSURE.getCrackTipCoords()
    Basefo = FISSURE.getCrackTipBasis()
    NB_POINT_FOND = args.get("NB_POINT_FOND")

    #     Traitement des fonds fermés
    TypeFond = FISSURE.getTipType()

    #     Traitement du cas fond multiple
    Fissmult = FISSURE.getCrackTipMultiplicity()
    Nbfiss = len(Fissmult) // 2
    Numfiss = args.get("NUME_FOND")
    if Numfiss <= Nbfiss and (Nbfiss > 1 or TypeFond == "FERME"):
        Ptinit = Fissmult[2 * (Numfiss - 1)]
        Ptfin = Fissmult[2 * (Numfiss - 1) + 1]
        Listfo2 = Listfo[((Ptinit - 1) * 4) : (Ptfin * 4)]
        Listfo = Listfo2
        Basefo2 = Basefo[((Ptinit - 1) * (2 * ndim)) : (Ptfin * (2 * ndim))]
        Basefo = Basefo2
    elif Numfiss > Nbfiss:
        UTMESS("F", "RUPTURE1_38", vali=[Nbfiss, Numfiss])

    if NB_POINT_FOND is not None and ndim == 3:
        Nnoff = NB_POINT_FOND
        absmax = Listfo[-1]
        Coorfo = [None] * 4 * Nnoff
        Vpropa = [None] * 3 * Nnoff
        for i in range(Nnoff):
            absci = i * absmax / (Nnoff - 1)
            Coorfo[(4 * i) : (4 * (i + 1))] = InterpolFondFiss(absci, Listfo)
            Vpropa[(6 * i) : (6 * (i + 1))] = InterpolBaseFiss(absci, Basefo, Listfo)
    else:
        Coorfo = Listfo
        Vpropa = Basefo
        Nnoff = len(Coorfo) // 4

    return (Coorfo, Vpropa, Nnoff)


# -------------------------------------------------------------------------


def get_direction_xfem(Nnoff, Vpropa, Coorfo, ndim):
    """retourne la direction de propagation, la normale a la surface de la fissure,
    et l'abscisse curviligne en chaque point du fond"""

    VDIR = [None] * Nnoff
    VNOR = [None] * Nnoff
    absfon = [0]

    i = 0
    if ndim == 3:
        VNOR[0] = NP.array([Vpropa[0], Vpropa[1], Vpropa[2]])
        VDIR[0] = NP.array([Vpropa[3 + 0], Vpropa[3 + 1], Vpropa[3 + 2]])
        for i in range(1, Nnoff - 1):
            absf = Coorfo[4 * i + 3]
            absfon.append(absf)
            VNOR[i] = NP.array([Vpropa[6 * i], Vpropa[6 * i + 1], Vpropa[6 * i + 2]])
            VDIR[i] = NP.array([Vpropa[3 + 6 * i], Vpropa[3 + 6 * i + 1], Vpropa[3 + 6 * i + 2]])
            verif = NP.dot(NP.transpose(VNOR[i]), VNOR[i - 1])
            if abs(verif) < 0.98:
                UTMESS("A", "RUPTURE1_35", vali=[i - 1, i])
        i = Nnoff - 1
        absf = Coorfo[4 * i + 3]
        absfon.append(absf)

        VNOR[i] = NP.array([Vpropa[6 * i], Vpropa[6 * i + 1], Vpropa[6 * i + 2]])
        VDIR[i] = NP.array([Vpropa[3 + 6 * i], Vpropa[3 + 6 * i + 1], Vpropa[3 + 6 * i + 2]])
    elif ndim == 2:
        for i in range(0, Nnoff):
            VNOR[i] = NP.array([Vpropa[0 + 4 * i], Vpropa[1 + 4 * i], 0.0])
            VDIR[i] = NP.array([Vpropa[2 + 4 * i], Vpropa[3 + 4 * i], 0.0])
    return (VDIR, VNOR, absfon)


# -------------------------------------------------------------------------


def get_sauts_xfem(self, Nnoff, Coorfo, VDIR, hmax, NB_NOEUD_COUPE, dmax, __RESX):
    """retourne la table des sauts"""

    mcfact = []
    for i in range(Nnoff):
        Porig = NP.array([Coorfo[4 * i], Coorfo[4 * i + 1], Coorfo[4 * i + 2]])
        Pextr = Porig - hmax * VDIR[i]

        mcfact.append(
            _F(
                NB_POINTS=NB_NOEUD_COUPE,
                COOR_ORIG=(Porig[0], Porig[1], Porig[2]),
                TYPE="SEGMENT",
                COOR_EXTR=(Pextr[0], Pextr[1], Pextr[2]),
                DISTANCE_MAX=dmax,
            )
        )

    __TSo = MACR_LIGN_COUPE(RESULTAT=__RESX, NOM_CHAM="DEPL", LIGN_COUPE=mcfact)

    return __TSo.EXTR_TABLE()


# -------------------------------------------------------------------------


def affiche_xfem(self, INFO, Nnoff, VNOR, VDIR):
    """affiche des infos"""

    if INFO == 2:
        mcfact = []
        mcfact.append(_F(PARA="NUM_PT", LISTE_I=list(range(Nnoff))))
        mcfact.append(_F(PARA="VN_X", LISTE_R=[VNOR[i][0] for i in range(Nnoff)]))
        mcfact.append(_F(PARA="VN_Y", LISTE_R=[VNOR[i][1] for i in range(Nnoff)]))
        mcfact.append(_F(PARA="VN_Z", LISTE_R=[VNOR[i][2] for i in range(Nnoff)]))
        mcfact.append(_F(PARA="VP_X", LISTE_R=[VDIR[i][0] for i in range(Nnoff)]))
        mcfact.append(_F(PARA="VP_Y", LISTE_R=[VDIR[i][1] for i in range(Nnoff)]))
        mcfact.append(_F(PARA="VP_Z", LISTE_R=[VDIR[i][2] for i in range(Nnoff)]))
        __resu2 = CREA_TABLE(
            LISTE=mcfact,
            TITRE=" " * 13 + "VECTEUR NORMAL A LA FISSURE    -   DIRECTION DE PROPAGATION",
        )
        aster.affiche("MESSAGE", __resu2.EXTR_TABLE().__repr__())


# -------------------------------------------------------------------------


def affiche_traitement(FOND_FISS, Lnofon, ino):
    if FOND_FISS:
        texte = "\n\n--> TRAITEMENT DU NOEUD DU FOND DE FISSURE: %s" % Lnofon[ino]
        aster.affiche("MESSAGE", texte)
    else:
        texte = "\n\n--> TRAITEMENT DU POINT DU FOND DE FISSURE NUMERO %s" % (ino + 1)
        aster.affiche("MESSAGE", texte)


# -------------------------------------------------------------------------


def get_tab(self, lev, ino, Tlib, Lno, TTSo, FOND_FISS, TYPE_MAILLAGE, tabl_depl, is_symmetric):
    """retourne la table des deplacements des noeuds perpendiculaires"""
    if lev == "sup" or (lev == "inf" and (not is_symmetric) and FOND_FISS):
        if FOND_FISS:
            if TYPE_MAILLAGE == "LIBRE":
                tab = Tlib.INTITULE == "l.coupe%i" % (ino + 1)
            else:
                Ls = [Lno[ino][i].ljust(8) for i in range(len(Lno[ino]))]
                tab = tabl_depl.NOEUD == Ls

        else:
            tab = TTSo.INTITULE == "l.coupe%i" % (ino + 1)

    else:
        tab = None

    return tab


# -------------------------------------------------------------------------


def get_liste_inst(tabsup, args):
    """retourne la liste d'instants"""

    l_inst = None
    l_inst_tab = tabsup["INST"].values()["INST"]
    l_inst_tab = list(dict([(i, 0) for i in l_inst_tab]).keys())  # elimine les doublons
    l_inst_tab.sort()
    if args.get("LIST_ORDRE") is not None or args.get("NUME_ORDRE") is not None:
        l_ord_tab = tabsup["NUME_ORDRE"].values()["NUME_ORDRE"]
        l_ord_tab.sort()
        l_ord_tab = list(dict([(i, 0) for i in l_ord_tab]).keys())
        d_ord_tab = [[l_ord_tab[i], l_inst_tab[i]] for i in range(0, len(l_ord_tab))]
        d_ord_tab = [(i[0], i[1]) for i in d_ord_tab]
        d_ord_tab = dict(d_ord_tab)
        if args.get("NUME_ORDRE") is not None:
            l_ord = args.get("NUME_ORDRE")
        elif args.get("LIST_ORDRE") is not None:
            l_ord = args.get("LIST_ORDRE").getValues()
        l_inst = []
        for ord in l_ord:
            if ord in l_ord_tab:
                l_inst.append(d_ord_tab[ord])
            else:
                UTMESS("F", "RUPTURE0_37", vali=ord)
        PRECISION = 1.0e-6
        CRITERE = "ABSOLU"
    elif args.get("INST") is not None or args.get("LIST_INST") is not None:
        CRITERE = args.get("CRITERE")
        PRECISION = args.get("PRECISION")
        if args.get("INST") is not None:
            l_inst = args.get("INST")
        elif args.get("LIST_INST") is not None:
            l_inst = args.get("LIST_INST").getValues()

        if type(l_inst) is tuple:
            l_inst = list(l_inst)

        for i, inst in enumerate(l_inst):
            if CRITERE == "RELATIF" and inst != 0.0:
                match = [x for x in l_inst_tab if abs((inst - x) / inst) < PRECISION]
            else:
                match = [x for x in l_inst_tab if abs(inst - x) < PRECISION]
            if len(match) == 0:
                UTMESS("F", "RUPTURE0_38", valr=inst)
            if len(match) >= 2:
                UTMESS("F", "RUPTURE0_39", valr=inst)
            l_inst[i] = match[0]
    else:
        l_inst = l_inst_tab
        PRECISION = 1.0e-6
        CRITERE = "ABSOLU"

    return (l_inst, PRECISION, CRITERE)


# -------------------------------------------------------------------------


def get_liste_freq(tabsup, args):
    """retourne la liste des fréquences"""

    l_freq = None
    l_freq_tab = tabsup["FREQ"].values()["FREQ"]
    l_freq_tab = list(dict([(i, 0) for i in l_freq_tab]).keys())  # elimine les doublons
    l_freq_tab.sort()
    if args.get("LIST_ORDRE") is not None or args.get("NUME_ORDRE") is not None:
        l_ord_tab = tabsup["NUME_ORDRE"].values()["NUME_ORDRE"]
        l_ord_tab.sort()
        l_ord_tab = list(dict([(i, 0) for i in l_ord_tab]).keys())
        d_ord_tab = [(l_ord_tab[i], l_freq_tab[i]) for i in range(0, len(l_ord_tab))]
        d_ord_tab = dict(d_ord_tab)
        if args.get("NUME_ORDRE") is not None:
            l_ord = list(args.get("NUME_ORDRE"))
        elif args.get("LIST_ORDRE") is not None:
            l_ord = args.get("LIST_ORDRE").getValues()
        l_freq = []
        for ord in l_ord:
            if ord in l_ord_tab:
                l_freq.append(d_ord_tab[ord])
            else:
                UTMESS("F", "RUPTURE0_37", vali=ord)
        PRECISION = 1.0e-6
        CRITERE = "ABSOLU"
    elif args.get("LIST_MODE") is not None or args.get("NUME_MODE") is not None:
        l_mod_tab = tabsup["NUME_MODE"].values()["NUME_MODE"]
        l_mod_tab.sort()
        l_mod_tab = list(dict([(i, 0) for i in l_mod_tab]).keys())
        d_mod_tab = [(l_mod_tab[i], l_freq_tab[i]) for i in range(0, len(l_mod_tab))]
        d_mod_tab = dict(d_mod_tab)
        if args.get("NUME_MODE") is not None:
            l_mod = args.get("NUME_MODE")
        elif args.get("LIST_MODE") is not None:
            l_mod = args.get("LIST_MODE").getValues()
        l_freq = []
        for mod in l_mod:
            if mod in l_mod_tab:
                l_freq.append(d_mod_tab[mod])
            else:
                UTMESS("F", "RUPTURE0_74", vali=mod)
        PRECISION = 1.0e-6
        CRITERE = "ABSOLU"
    elif args.get("FREQ") is not None or args.get("LIST_FREQ") is not None:
        CRITERE = args.get("CRITERE")
        PRECISION = args.get("PRECISION")
        if args.get("FREQ") is not None:
            l_freq = list(args.get("FREQ"))
        elif args.get("LIST_FREQ") is not None:
            l_freq = args.get("LIST_FREQ").getValues()

        if type(l_freq) is tuple:
            l_freq = list(l_freq)

        for i, freq in enumerate(l_freq):
            if CRITERE == "RELATIF" and freq != 0.0:
                match = [x for x in l_freq_tab if abs((freq - x) / freq) < PRECISION]
            else:
                match = [x for x in l_freq_tab if abs(freq - x) < PRECISION]

            if len(match) == 0:
                UTMESS("F", "RUPTURE0_88", valr=freq)
            if len(match) >= 2:
                UTMESS("F", "RUPTURE0_89", valr=freq)
            l_freq[i] = match[0]
    else:
        l_freq = l_freq_tab
        PRECISION = 1.0e-6
        CRITERE = "ABSOLU"

    return (l_freq, PRECISION, CRITERE)


# -------------------------------------------------------------------------


def affiche_instant(inst, type_para):
    if inst is not None:
        if type_para == "FREQ":
            texte = "#" + "=" * 80 + "\n" + "==> FREQUENCE: %f" % inst
        else:
            texte = "#" + "=" * 80 + "\n" + "==> INSTANT: %f" % inst
        aster.affiche("MESSAGE", texte)


# -------------------------------------------------------------------------


def get_tab_inst(lev, inst, FISSURE, is_symmetric, PRECISION, CRITERE, tabsup, tabinf, type_para):
    """retourne la table des deplacements des noeuds à l'instant courant"""
    tab = None
    assert lev == "sup" or lev == "inf"

    if lev == "sup":
        tabres = tabsup
    elif lev == "inf":
        if not is_symmetric and not FISSURE:
            tabres = tabinf
        else:
            return tab

    if inst == 0.0:
        crit = "ABSOLU"
    else:
        crit = CRITERE
    if type_para == "FREQ":
        tab = tabres.FREQ.__eq__(VALE=inst, CRITERE=crit, PRECISION=PRECISION)
    else:
        tab = tabres.INST.__eq__(VALE=inst, CRITERE=crit, PRECISION=PRECISION)

    return tab


# -------------------------------------------------------------------------


def get_propmat_varc_fem(
    self, RESULTAT, MAILLAGE, MATER, MODELISATION, Lnofon, ino, inst, para_fonc
):
    """cas fem : retourne les proprietes materiaux en fonction de la variable de commande au noeud ino à l'instant demandé"""

    # extraction du cham_no de varc a l'instant considere
    __CHNOVRC = POST_K_VARC(RESULTAT=RESULTAT, INST=inst, NOM_VARC=para_fonc)

    # seules les varc TEMP et NEUT1 sont autorisees
    nomgd_2_nompar = {"TEMP_R": "TEMP", "NEUT_R": "NEUT1"}
    nomgd_2_nomcmp = {"TEMP_R": "TEMP", "NEUT_R": "X1"}
    nomgd = __CHNOVRC.getPhysicalQuantity()
    assert nomgd in list(nomgd_2_nompar.keys())
    ChnoVrcVale, description = __CHNOVRC.getValuesWithDescription()
    ChnoVrcNoeu = description[0]
    ChnoVrcComp = description[1]
    assert list(set(ChnoVrcComp)) in [["TEMP"], ["X1"]]

    # blindage sur le nombre de noeuds du champ / nombre de noeuds du maillage
    # -> permet de se premunir de l'oubli du couple (OP.INIT_VARC.PVARCNO, LC.ZVARCNO)
    #    en para_out de l'option INIT_VARC d'un catalogue EF
    NbNoMa = MAILLAGE.getNumberOfNodes()
    if len(ChnoVrcNoeu) != NbNoMa:
        UTMESS("F", "RUPTURE0_2", valk=para_fonc, vali=[len(ChnoVrcNoeu), NbNoMa])

    # extraction d'une table contenant les valeurs de la varc en fond de fissure
    __VARC = POST_RELEVE_T(
        ACTION=_F(
            INTITULE="varc en fond de fissure",
            NOEUD=Lnofon,
            TOUT_CMP="OUI",
            CHAM_GD=__CHNOVRC,
            OPERATION="EXTRACTION",
        )
    )
    tabvarc = __VARC.EXTR_TABLE()

    # valeur de la varc en ino
    nompar = nomgd_2_nompar[nomgd]
    nomcmp = nomgd_2_nomcmp[nomgd]
    varcno = tabvarc.NOEUD == Lnofon[ino]
    varcno = varcno.values()
    valpar = varcno[nomcmp][0]
    assert type(valpar) is float

    # valeur des parametres elastiques fonctions de la varc
    nomres = ["E", "NU"]
    valres, _ = MATER.RCVALE("ELAS", nompar, valpar, nomres, 2)
    e = valres[0]
    nu = valres[1]

    coefd3 = 0.0
    coefd = e * NP.sqrt(2.0 * pi)
    unmnu2 = 1.0 - nu**2
    unpnu = 1.0 + nu
    if MODELISATION == "3D":
        coefd = coefd / (8.0 * unmnu2)
        coefd3 = e * NP.sqrt(2 * pi) / (8.0 * unpnu)
        coefg = unmnu2 / e
        coefg3 = unpnu / e
    elif MODELISATION == "AXIS":
        coefd = coefd / (8.0 * unmnu2)
        coefg = unmnu2 / e
        coefg3 = unpnu / e
    elif MODELISATION == "D_PLAN":
        coefd = coefd / (8.0 * unmnu2)
        coefg = unmnu2 / e
        coefg3 = unpnu / e
    elif MODELISATION == "C_PLAN":
        coefd = coefd / 8.0
        coefg = 1.0 / e
        coefg3 = unpnu / e

    return (coefd, coefd3, coefg, coefg3, valpar)


# -------------------------------------------------------------------------


def get_propmat_varc_xfem(
    self, args, RESULTAT, MAILLAGE, MATER, MODELISATION, FISSURE, ndim, ipt, inst, para_fonc
):
    """cas xfem : retourne les proprietes materiaux en fonction de la variable de commande au point ipt à l'instant demandé"""

    # extraction du cham_no de varc a l'instant considere
    __CHNOVRC = POST_K_VARC(RESULTAT=RESULTAT, INST=inst, NOM_VARC=para_fonc)

    # seules les varc TEMP et NEUT1 sont autorisees
    nomgd_2_nompar = {"TEMP_R": "TEMP", "NEUT_R": "NEUT1"}
    nomgd = __CHNOVRC.getPhysicalQuantity()
    assert nomgd in list(nomgd_2_nompar.keys())
    ChnoVrcVale, description = __CHNOVRC.getValuesWithDescription()
    ChnoVrcNoeu = description[0]
    ChnoVrcComp = description[1]
    assert list(set(ChnoVrcComp)) in [["TEMP"], ["X1"]]

    # blindage sur le nombre de noeuds du champ / nombre de noeuds du maillage
    # -> permet de se premunir de l'oubli du couple (OP.INIT_VARC.PVARCNO, LC.ZVARCNO)
    #    en para_out de l'option INIT_VARC d'un catalogue EF
    NbNoMa = MAILLAGE.getNumberOfNodes()
    if len(ChnoVrcNoeu) != NbNoMa:
        UTMESS("F", "RUPTURE0_2", valk=para_fonc, vali=[len(ChnoVrcNoeu), NbNoMa])

    # extraction des vecteurs :
    #  - FISSURE.FONDFISS (coords des points du fond)
    #  - FISSURE.NOFACPTFON (numeros des noeuds des faces des elements
    #    parents qui contiennent les points du fond de fissure
    Listfo = FISSURE.getCrackTipCoords()
    L_NoFacPtFon = FISSURE.getCrackTipNodeFacesField()
    assert len(Listfo) % 4 == 0
    assert len(Listfo) == len(L_NoFacPtFon)

    # calcul de ValeVrc_Listfo : valeur de la varc en tous les points de Listfo
    # -> moyenne arithmetique des valeurs nodales sur la face contenant le point
    ValeVrc_Listfo = []
    for i in range(0, len(Listfo) // 4):
        vale = 0.0
        NbNoFa = 3
        for k in range(NbNoFa):
            vale += ChnoVrcVale[L_NoFacPtFon[k + 4 * i] - 1]
        # si la face est quadrangulaire
        if L_NoFacPtFon[3 + 4 * i] > 0:
            NbNoFa = 4
            vale += ChnoVrcVale[L_NoFacPtFon[3 + 4 * i] - 1]
        vale = vale / float(NbNoFa)
        ValeVrc_Listfo.append(vale)

    # Traitement des fonds fermés
    TypeFond = FISSURE.getTipType()

    # Traitement du cas fond multiple
    Fissmult = FISSURE.getCrackTipMultiplicity()
    Nbfiss = len(Fissmult) // 2
    Numfiss = args.get("NUME_FOND")
    if Numfiss <= Nbfiss and (Nbfiss > 1 or TypeFond == "FERME"):
        Ptinit = Fissmult[2 * (Numfiss - 1)]
        Ptfin = Fissmult[2 * (Numfiss - 1) + 1]
        ValeVrc_Listfo2 = ValeVrc_Listfo[Ptinit - 1 : Ptfin]
        ValeVrc_Listfo = ValeVrc_Listfo2
    elif Numfiss > Nbfiss:
        UTMESS("F", "RUPTURE1_38", vali=[Nbfiss, Numfiss])

    # Si NB_POINT_FOND est renseigne : interpolation de la varc
    NB_POINT_FOND = args.get("NB_POINT_FOND")
    if NB_POINT_FOND is not None and ndim == 3:
        Nnoff = NB_POINT_FOND
        absmax = Listfo[-1]
        ValeVrc = [None] * Nnoff
        for i in range(Nnoff):
            absci = i * absmax / (Nnoff - 1)
            ValeVrc[i] = InterpolScalFiss(absci, ValeVrc_Listfo, Listfo)
    # Sinon : on utilise directement ValeVrc_Listfo
    else:
        ValeVrc = ValeVrc_Listfo

    # valeur des parametres elastiques fonctions de la varc en ipt
    nompar = nomgd_2_nompar[nomgd]
    valpar = ValeVrc[ipt]
    nomres = ["E", "NU"]
    valres, _ = MATER.RCVALE("ELAS", nompar, valpar, nomres, 2)
    e = valres[0]
    nu = valres[1]
    coefd3 = 0.0
    coefd = e * NP.sqrt(2.0 * pi)
    unmnu2 = 1.0 - nu**2
    unpnu = 1.0 + nu
    if MODELISATION == "3D":
        coefd = coefd / (8.0 * unmnu2)
        coefd3 = e * NP.sqrt(2 * pi) / (8.0 * unpnu)
        coefg = unmnu2 / e
        coefg3 = unpnu / e
    elif MODELISATION == "AXIS":
        coefd = coefd / (8.0 * unmnu2)
        coefg = unmnu2 / e
        coefg3 = unpnu / e
    elif MODELISATION == "D_PLAN":
        coefd = coefd / (8.0 * unmnu2)
        coefg = unmnu2 / e
        coefg3 = unpnu / e
    elif MODELISATION == "C_PLAN":
        coefd = coefd / 8.0
        coefg = 1.0 / e
        coefg3 = unpnu / e

    return (coefd, coefd3, coefg, coefg3, valpar)


# -------------------------------------------------------------------------


def get_depl_sup(FOND_FISS, tabsupi, ndim, Lnofon, d_coor, ino, TYPE_MAILLAGE):
    """retourne les déplacements sup"""

    abscs = getattr(tabsupi, "ABSC_CURV").values()

    if FOND_FISS:
        nbval = len(abscs)

        if TYPE_MAILLAGE != "LIBRE":
            coxs = NP.array(tabsupi["COOR_X"].values()["COOR_X"][:nbval])
            coys = NP.array(tabsupi["COOR_Y"].values()["COOR_Y"][:nbval])
            if ndim == 2:
                cozs = NP.zeros(nbval)
            elif ndim == 3:
                cozs = NP.array(tabsupi["COOR_Z"].values()["COOR_Z"][:nbval])

            Pfon = NP.array(
                [d_coor[Lnofon[ino]][0], d_coor[Lnofon[ino]][1], d_coor[Lnofon[ino]][2]]
            )
            abscs = NP.sqrt((coxs - Pfon[0]) ** 2 + (coys - Pfon[1]) ** 2 + (cozs - Pfon[2]) ** 2)
            tabsupi["Abs_fo"] = abscs
            tabsupi.sort("Abs_fo")
            abscs = getattr(tabsupi, "Abs_fo").values()

        abscs = NP.array(abscs[:nbval])

        dxs = NP.array(tabsupi["DX"].values()["DX"][:nbval])
        dys = NP.array(tabsupi["DY"].values()["DY"][:nbval])
        if ndim == 2:
            dzs = NP.zeros(nbval)
        elif ndim == 3:
            dzs = NP.array(tabsupi["DZ"].values()["DZ"][:nbval])

    #     ---  CAS FISSURE X-FEM ---
    else:
        # Bricolage temporaire pour post_k1_k2_k3 ::
        #   on néglige les termes singuliers en interpolant le champ de déplacement
        #   compte-tenu du shift des fonctions singulières, cela revient à mettre les termes
        #   singuliers à zéro
        H1 = getattr(tabsupi, "H1X").values()
        nbval = len(H1)
        H1 = complete(H1)
        dxs = 2.0 * (H1 + NP.zeros(nbval))
        H1 = getattr(tabsupi, "H1Y").values()
        H1 = complete(H1)
        dys = 2.0 * (H1 + NP.zeros(nbval))
        H1 = getattr(tabsupi, "H1Z").values()
        H1 = complete(H1)
        dzs = 2.0 * (H1 + NP.zeros(nbval))
        abscs = NP.array(abscs[:nbval])

    ds = NP.asarray([dxs, dys, dzs])

    return (abscs, ds)


# -------------------------------------------------------------------------


def get_depl_inf(FOND_FISS, tabinfi, ndim, Lnofon, is_symmetric, d_coor, ino, TYPE_MAILLAGE):
    """retourne les déplacements inf"""

    if not is_symmetric and FOND_FISS:
        absci = getattr(tabinfi, "ABSC_CURV").values()

        nbval = len(absci)
        if TYPE_MAILLAGE != "LIBRE":
            coxi = NP.array(tabinfi["COOR_X"].values()["COOR_X"][:nbval])
            coyi = NP.array(tabinfi["COOR_Y"].values()["COOR_Y"][:nbval])
            if ndim == 2:
                cozi = NP.zeros(nbval)
            elif ndim == 3:
                cozi = NP.array(tabinfi["COOR_Z"].values()["COOR_Z"][:nbval])

            Pfon = NP.array(
                [d_coor[Lnofon[ino]][0], d_coor[Lnofon[ino]][1], d_coor[Lnofon[ino]][2]]
            )
            absci = NP.sqrt((coxi - Pfon[0]) ** 2 + (coyi - Pfon[1]) ** 2 + (cozi - Pfon[2]) ** 2)
            tabinfi["Abs_fo"] = absci
            tabinfi.sort("Abs_fo")
            absci = getattr(tabinfi, "Abs_fo").values()

        absci = NP.array(absci[:nbval])

        dxi = NP.array(tabinfi["DX"].values()["DX"][:nbval])
        dyi = NP.array(tabinfi["DY"].values()["DY"][:nbval])
        if ndim == 2:
            dzi = NP.zeros(nbval)
        elif ndim == 3:
            dzi = NP.array(tabinfi["DZ"].values()["DZ"][:nbval])

        di = NP.asarray([dxi, dyi, dzi])

    else:
        absci = []
        di = []

    return (absci, di)


# -------------------------------------------------------------------------


def get_pgl(is_symmetric, FISSURE, ino, VDIR, VNOR, dicVDIR, dicVNOR, Lnofon, ndim):
    """retourne la matrice du changement de repère"""

    # attention en 2d, la base (VDIR, VNOR) issue BASEFOND n'est pas forcement dans le
    # sens trigo :
    # VNOR est dans le sens des level sets normales croissantes pour X-FEM
    #          tel que K1 soit defini comme DepLevSup - DepLevInf pour FEM
    # VDIR est dans la direction de propagation

    if FISSURE:
        v1 = VNOR[ino]
        v2 = VDIR[ino]

    elif not FISSURE:
        v1 = dicVNOR[Lnofon[ino]]
        v2 = dicVDIR[Lnofon[ino]]

    v1 = normalize(v1)
    v2 = normalize(v2)

    v3 = NP.cross(v1, v2)
    v3 = normalize(v3)
    # v2 = NP.cross(v3, v1)

    if ndim == 2:
        # on prend comme vecteur de direction de propa une rotation de -90 du
        # vecteur normal
        v2 = NP.array([v1[1], -v1[0], 0])
        v3 = NP.cross(v1, v2)

    pgl = NP.asarray([v1, v2, v3])

    return pgl


# -------------------------------------------------------------------------


def get_saut(self, pgl, ds, di, INFO, FISSURE, is_symmetric, abscs, ndim):
    """retourne le saut de déplacements dans le nouveau repère"""

    dpls = NP.dot(pgl, ds)

    if FISSURE:
        saut = dpls
    elif not is_symmetric:
        dpli = NP.dot(pgl, di)
        saut = dpls - dpli
    else:
        dpli = [NP.multiply(dpls[0], -1.0), dpls[1], dpls[2]]
        saut = dpls - dpli

    if INFO == 2:
        mcfact = []
        mcfact.append(_F(PARA="ABSC_CURV", LISTE_R=abscs.tolist()))
        if not FISSURE:
            mcfact.append(_F(PARA="DEPL_SUP_1", LISTE_R=dpls[0].tolist()))
            mcfact.append(_F(PARA="DEPL_INF_1", LISTE_R=dpli[0].tolist()))
        mcfact.append(_F(PARA="SAUT_1", LISTE_R=saut[0].tolist()))
        if not FISSURE:
            mcfact.append(_F(PARA="DEPL_SUP_2", LISTE_R=dpls[1].tolist()))
            mcfact.append(_F(PARA="DEPL_INF_2", LISTE_R=dpli[1].tolist()))
        mcfact.append(_F(PARA="SAUT_2", LISTE_R=saut[1].tolist()))
        if ndim == 3:
            if not FISSURE:
                mcfact.append(_F(PARA="DEPL_SUP_3", LISTE_R=dpls[2].tolist()))
                mcfact.append(_F(PARA="DEPL_INF_3", LISTE_R=dpli[2].tolist()))
            mcfact.append(_F(PARA="SAUT_3", LISTE_R=saut[2].tolist()))
        __resu0 = CREA_TABLE(LISTE=mcfact, TITRE="--> SAUTS")
        aster.affiche("MESSAGE", __resu0.EXTR_TABLE().__repr__())

    return saut


# -------------------------------------------------------------------------


def get_kgsig(saut, nbval, coefd, coefd3):
    """retourne des trucs...."""

    isig = NP.sign(NP.transpose(NP.resize(saut[:, -1], (nbval - 1, 3))))
    isig = NP.sign(isig + 0.001)
    saut2 = saut * NP.array([[coefd] * nbval, [coefd] * nbval, [coefd3] * nbval])
    saut2 = saut2**2
    ksig = isig[:, 1]
    ksig = NP.array([ksig, ksig])
    ksig = NP.transpose(ksig)
    kgsig = NP.resize(ksig, (1, 6))[0]

    return (isig, kgsig, saut2)


# -------------------------------------------------------------------------


def get_meth1(self, abscs, coefg, coefg3, kgsig, isig, saut2, INFO, ndim):
    """retourne kg1"""

    nabs = len(abscs)

    x1 = abscs[1:-1]
    x2 = abscs[2:nabs]
    y1 = saut2[:, 1:-1] / x1
    y2 = saut2[:, 2:nabs] / x2
    k = abs(y1 - x1 * (y2 - y1) / (x2 - x1))
    g = coefg * (k[0] + k[1]) + coefg3 * k[2]
    kg1 = [max(k[0]), min(k[0]), max(k[1]), min(k[1]), max(k[2]), min(k[2])]
    kg1 = NP.sqrt(kg1) * kgsig
    kg1 = NP.concatenate([kg1, [max(g), min(g)]])
    vk = NP.sqrt(k) * isig[:, :-1]
    if INFO == 2:
        mcfact = []
        mcfact.append(_F(PARA="ABSC_CURV_1", LISTE_R=x1.tolist()))
        mcfact.append(_F(PARA="ABSC_CURV_2", LISTE_R=x2.tolist()))
        mcfact.append(_F(PARA="K1", LISTE_R=vk[0].tolist()))
        mcfact.append(_F(PARA="K2", LISTE_R=vk[1].tolist()))
        if ndim == 3:
            mcfact.append(_F(PARA="K3", LISTE_R=vk[2].tolist()))
        mcfact.append(_F(PARA="G", LISTE_R=g.tolist()))
        __resu1 = CREA_TABLE(LISTE=mcfact, TITRE="--> METHODE 1")
        aster.affiche("MESSAGE", __resu1.EXTR_TABLE().__repr__())

    return kg1


# -------------------------------------------------------------------------


def get_meth2(self, abscs, coefg, coefg3, kgsig, isig, saut2, INFO, ndim):
    """retourne kg2"""

    nabs = len(abscs)
    x1 = abscs[1:nabs]
    y1 = saut2[:, 1:nabs]
    k = abs(y1 / x1)
    g = coefg * (k[0] + k[1]) + coefg3 * k[2]
    kg2 = [max(k[0]), min(k[0]), max(k[1]), min(k[1]), max(k[2]), min(k[2])]
    kg2 = NP.sqrt(kg2) * kgsig
    kg2 = NP.concatenate([kg2, [max(g), min(g)]])
    vk = NP.sqrt(k) * isig
    if INFO == 2:
        mcfact = []
        mcfact.append(_F(PARA="ABSC_CURV", LISTE_R=x1.tolist()))
        mcfact.append(_F(PARA="K1", LISTE_R=vk[0].tolist()))
        mcfact.append(_F(PARA="K2", LISTE_R=vk[1].tolist()))
        if ndim == 3:
            mcfact.append(_F(PARA="K3", LISTE_R=vk[2].tolist()))
        mcfact.append(_F(PARA="G", LISTE_R=g.tolist()))
        __resu2 = CREA_TABLE(LISTE=mcfact, TITRE="--> METHODE 2")
        aster.affiche("MESSAGE", __resu2.EXTR_TABLE().__repr__())

    return kg2


# -------------------------------------------------------------------------


def get_meth3(self, abscs, coefg, coefg3, kgsig, isig, saut2, INFO, ndim):
    """retourne kg3"""

    nabs = len(abscs)
    x1 = abscs[:-1]
    x2 = abscs[1:nabs]
    y1 = saut2[:, :-1]
    y2 = saut2[:, 1:nabs]
    k = (NP.sqrt(y2) * NP.sqrt(x2) + NP.sqrt(y1) * NP.sqrt(x1)) * (x2 - x1)
    #     attention, ici, il faut NP.sum et pas sum tout court
    k = NP.sum(NP.transpose(k), axis=0)
    de = abscs[-1]
    vk = (k / de**2) * isig[:, 0]
    g = coefg * (vk[0] ** 2 + vk[1] ** 2) + coefg3 * vk[2] ** 2
    kg3 = NP.concatenate([[vk[0]] * 2, [vk[1]] * 2, [vk[2]] * 2, [g] * 2])
    if INFO == 2:
        mcfact = []
        mcfact.append(_F(PARA="K1", LISTE_R=vk[0]))
        mcfact.append(_F(PARA="K2", LISTE_R=vk[1]))
        if ndim == 3:
            mcfact.append(_F(PARA="K3", LISTE_R=vk[2]))
        mcfact.append(_F(PARA="G", LISTE_R=g))
        __resu3 = CREA_TABLE(LISTE=mcfact, TITRE="--> METHODE 3")
        aster.affiche("MESSAGE", __resu3.EXTR_TABLE().__repr__())

    return kg3


# -------------------------------------------------------------------------


def get_erreur(self, ndim, __tabi, type_para):
    """retourne l'erreur selon les méthodes.
    En FEM/X-FEM, on ne retient que le K_MAX de la méthode 1."""

    labels = ["K1_MAX", "K1_MIN", "K2_MAX", "K2_MIN", "K3_MAX", "K3_MIN"]
    index = 2
    if ndim == 3:
        index = 3
    py_tab = __tabi.EXTR_TABLE()

    nlines = len(py_tab.values()[list(py_tab.values().keys())[0]])
    err = NP.zeros((index, nlines // 3))
    kmax = [0.0] * index
    kmin = [0.0] * index
    for i in range(nlines // 3):
        for j in range(index):
            kmax[j] = max(
                __tabi[labels[2 * j], 3 * i + 1],
                __tabi[labels[2 * j], 3 * i + 2],
                __tabi[labels[2 * j], 3 * i + 3],
            )
            kmin[j] = min(
                __tabi[labels[2 * j + 1], 3 * i + 1],
                __tabi[labels[2 * j + 1], 3 * i + 2],
                __tabi[labels[2 * j + 1], 3 * i + 3],
            )
        kmaxmax = max(kmax)
        if NP.fabs(kmaxmax) > 1e-15:
            for j in range(index):
                err[j, i] = (kmax[j] - kmin[j]) / kmaxmax

    # filter method 1 line
    imeth = 1
    __tabi = CALC_TABLE(
        TABLE=__tabi,
        reuse=__tabi,
        ACTION=_F(OPERATION="FILTRE", CRIT_COMP="EQ", VALE=imeth, NOM_PARA="METHODE"),
    )

    # rename k parameters
    __tabi = CALC_TABLE(
        TABLE=__tabi,
        reuse=__tabi,
        ACTION=(
            _F(OPERATION="RENOMME", NOM_PARA=("K1_MAX", "K1")),
            _F(OPERATION="RENOMME", NOM_PARA=("K2_MAX", "K2")),
            _F(OPERATION="RENOMME", NOM_PARA=("G_MAX", "G")),
        ),
    )
    if ndim == 3:
        __tabi = CALC_TABLE(
            TABLE=__tabi, reuse=__tabi, ACTION=_F(OPERATION="RENOMME", NOM_PARA=("K3_MAX", "K3"))
        )

    # create error
    if ndim != 3:
        __tini = CREA_TABLE(
            LISTE=(
                _F(LISTE_R=(tuple(__tabi.EXTR_TABLE().values()["G_MIN"])), PARA="G_MIN"),
                _F(LISTE_R=(tuple(err[0].tolist())), PARA="ERR_K1"),
                _F(LISTE_R=(tuple(err[1].tolist())), PARA="ERR_K2"),
            )
        )
    else:
        __tini = CREA_TABLE(
            LISTE=(
                _F(LISTE_R=(tuple(__tabi.EXTR_TABLE().values()["G_MIN"])), PARA="G_MIN"),
                _F(LISTE_R=(tuple(err[0].tolist())), PARA="ERR_K1"),
                _F(LISTE_R=(tuple(err[1].tolist())), PARA="ERR_K2"),
                _F(LISTE_R=(tuple(err[2].tolist())), PARA="ERR_K3"),
            )
        )

    # add error
    __tabi = CALC_TABLE(
        TABLE=__tabi,
        reuse=__tabi,
        ACTION=(_F(OPERATION="COMB", NOM_PARA="G_MIN", TABLE=__tini)),
        INFO=1,
    )

    # remove kj_min + sort data
    params = []
    tabi_para = __tabi.EXTR_TABLE().para
    for para in (
        "FISSURE",
        "FOND_FISS",
        "NUME_FOND",
        "NUME_ORDRE",
        "INST",
        "FREQ",
        "NOEUD",
        "NUM_PT",
        "COOR_X",
        "COOR_Y",
        "COOR_Z",
        "ABSC_CURV",
        "TEMP",
        "NEUT1",
    ):
        if para in tabi_para:
            params.append(para)
    params.append("G")
    params.extend(["K1", "ERR_K1", "K2", "ERR_K2"])
    if ndim == 3:
        params.extend(["K3", "ERR_K3"])

    __tabi = CALC_TABLE(
        TABLE=__tabi,
        reuse=__tabi,
        ACTION=(_F(OPERATION="EXTR", NOM_PARA=tuple(params))),
        TITRE="CALCUL DES FACTEURS D'INTENSITE DES CONTRAINTES PAR LA METHODE POST_K1_K2_K3",
    )

    return __tabi


# -------------------------------------------------------------------------


def get_tabout(
    self,
    kg,
    args,
    TITRE,
    FOND_FISS,
    MODELISATION,
    FISSURE,
    ndim,
    ino,
    inst,
    iord,
    Lnofon,
    dicoF,
    absfon,
    Nnoff,
    tabout,
    type_para,
    nume,
    para_fonc,
    para,
    d_coor,
):
    """retourne la table de sortie"""

    mcfact = []

    if TITRE is not None:
        titre = TITRE
    else:
        titre = get_titre_concept()

    if FOND_FISS and MODELISATION == "3D":
        mcfact.append(_F(PARA="FOND_FISS", LISTE_K=[FOND_FISS.getName()] * 3))
        mcfact.append(_F(PARA="NUME_FOND", LISTE_I=[1] * 3))
        mcfact.append(_F(PARA="NOEUD", LISTE_K=[Lnofon[ino]] * 3))
        mcfact.append(_F(PARA="NUM_PT", LISTE_I=[ino + 1] * 3))
        mcfact.append(_F(PARA="ABSC_CURV", LISTE_R=[dicoF[Lnofon[ino]]] * 3))

    if FISSURE and MODELISATION == "3D":
        mcfact.append(_F(PARA="FISSURE", LISTE_K=[FISSURE.getName()] * 3))
        mcfact.append(_F(PARA="NUME_FOND", LISTE_I=[args.get("NUME_FOND")] * 3))
        mcfact.append(_F(PARA="NUM_PT", LISTE_I=[ino + 1] * 3))
        mcfact.append(_F(PARA="ABSC_CURV", LISTE_R=[absfon[ino]] * 3))

    if FISSURE and MODELISATION != "3D" and Nnoff != 1:
        mcfact.append(_F(PARA="FISSURE", LISTE_K=[FISSURE.getName()] * 3))
        mcfact.append(_F(PARA="NUM_PT", LISTE_I=[ino + 1] * 3))

    mcfact.append(_F(PARA="METHODE", LISTE_I=(1, 2, 3)))
    mcfact.append(_F(PARA="K1_MAX", LISTE_R=kg[0].tolist()))
    mcfact.append(_F(PARA="K1_MIN", LISTE_R=kg[1].tolist()))
    mcfact.append(_F(PARA="K2_MAX", LISTE_R=kg[2].tolist()))
    mcfact.append(_F(PARA="K2_MIN", LISTE_R=kg[3].tolist()))

    if ndim == 3:
        mcfact.append(_F(PARA="K3_MAX", LISTE_R=kg[4].tolist()))
        mcfact.append(_F(PARA="K3_MIN", LISTE_R=kg[5].tolist()))

    mcfact.append(_F(PARA="G_MAX", LISTE_R=kg[6].tolist()))
    mcfact.append(_F(PARA="G_MIN", LISTE_R=kg[7].tolist()))

    if para_fonc:
        mcfact.append(_F(PARA=para_fonc, LISTE_R=[para] * 3))

    if d_coor:
        if Lnofon:
            coor = d_coor[Lnofon[ino]]
        else:
            coor = d_coor[ino]
        mcfact.append(_F(PARA="COOR_X", LISTE_R=[coor[0]] * 3))
        mcfact.append(_F(PARA="COOR_Y", LISTE_R=[coor[1]] * 3))
        mcfact.append(_F(PARA="COOR_Z", LISTE_R=[coor[2]] * 3))

    if (ino == 0 and iord == 0) and inst is None:
        tabout = CREA_TABLE(LISTE=mcfact, TITRE=titre)
        tabout = get_erreur(self, ndim, tabout, type_para)
    elif iord == 0 and ino == 0 and inst is not None:
        mcfact = [_F(PARA="NUME_ORDRE", LISTE_I=nume)] + mcfact
        mcfact = [_F(PARA=type_para, LISTE_R=[inst] * 3)] + mcfact
        tabout = CREA_TABLE(LISTE=mcfact, TITRE=titre)
        tabout = get_erreur(self, ndim, tabout, type_para)
    else:
        if inst is not None:
            mcfact = [_F(PARA="NUME_ORDRE", LISTE_I=nume)] + mcfact
            mcfact = [_F(PARA=type_para, LISTE_R=[inst] * 3)] + mcfact
        __tabi = CREA_TABLE(LISTE=mcfact)
        npara = ["K1"]
        if inst is not None:
            npara.append(type_para)
        if not FISSURE and MODELISATION == "3D":
            npara.append("NOEUD")
        elif FISSURE and MODELISATION == "3D":
            npara.append("NUM_PT")
        if para:
            npara.append(para_fonc)

        tabout2 = get_erreur(self, ndim, __tabi, type_para)
        tabout = CALC_TABLE(
            reuse=tabout,
            TABLE=tabout,
            TITRE=titre,
            ACTION=_F(OPERATION="COMB", NOM_PARA=npara, TABLE=tabout2),
        )

    return tabout


# -------------------------------------------------------------------------


def is_present_varc(RESULTAT):
    """
    retourne true si presence de variables de commande dans la sd_cham_mater
    contenue dans la sd_resultat RESULTAT, retourne false sinon.
    """

    chamat = RESULTAT.getMaterialField()
    assert chamat.getName() not in ["#AUCUN", "#PLUSIEURS"]
    return chamat.hasExternalStateVariable()


# ---------------------------------------------------------------------------------------------------------------
#                 CORPS DE LA MACRO POST_K1_K2_K3
# -------------------------------------------------------------------------
def post_k1_k2_k3_ops(
    self,
    RESULTAT,
    FOND_FISS=None,
    FISSURE=None,
    MATER=None,
    ABSC_CURV_MAXI=None,
    PREC_VIS_A_VIS=None,
    INFO=None,
    TITRE=None,
    **args,
):
    """
    Macro POST_K1_K2_K3
    Calcul des facteurs d'intensité de contraintes en 2D et en 3D
    par extrapolation des sauts de déplacements sur les lèvres de
    la fissure. Produit une table.
    """
    EnumTypes = (list, tuple)

    tabout = []
    liste_noeu_a_extr = []

    # On importe les definitions des commandes a utiliser dans la macro
    # Le nom de la variable doit etre obligatoirement le nom de la commande

    # On recupere le materiau et le nom de la modelisation
    nom_fiss = ""
    if FOND_FISS is not None:
        nom_fiss = FOND_FISS.getName()
    if FISSURE is not None:
        nom_fiss = FISSURE.getName()
    assert nom_fiss != ""

    # si le MCS MATER n'est pas renseigne, on considere le materiau
    # present dans la sd_resultat. Si MATER est renseigne, on ecrase
    # le materiau et on emet une alarme.
    CHAM_MATER = None
    if MATER is None:
        mater, MODELISATION = aster.postkutil(1, RESULTAT.getName(), nom_fiss)
        if RESULTAT.getNumberOfIndexes() == 0:
            RESULTAT.updateInternalState()
        if RESULTAT.getNumberOfIndexes() > 0:
            cham_maters = []
            for j in RESULTAT.getIndexes():
                if RESULTAT.hasMaterialField(j):
                    cham_maters += [RESULTAT.getMaterialField(j)]
            if len(cham_maters):
                CHAM_MATER = cham_maters[0]
            else:
                CHAM_MATER = None
        else:
            CHAM_MATER = None
        test = CHAM_MATER.getVectorOfMaterial()
        for curMater in test:
            if curMater.getName() == mater:
                MATER = curMater
                break
    else:
        bid, MODELISATION = aster.postkutil(0, RESULTAT.getName(), nom_fiss)
        UTMESS("A", "RUPTURE0_1", valk=[MATER.getName()])

    # Affectation de ndim selon le type de modelisation
    assert MODELISATION in ["3D", "AXIS", "D_PLAN", "C_PLAN"]
    if MODELISATION == "3D":
        ndim = 3
    else:
        ndim = 2

    # presence / absence de variables de commande
    present_varc = is_present_varc(RESULTAT)

    #  on masque cette alarme, voire explication fiche 18070
    MasquerAlarme("CALCULEL4_9")

    #   ------------------------------------------------------------------
    #                               MAILLAGE
    #   ------------------------------------------------------------------
    try:
        MAILLAGE = RESULTAT.getModel().getMesh()
    except:
        MAILLAGE = CHAM_MATER.getMesh()

    #   ------------------------------------------------------------------
    #                         CARACTERISTIQUES MATERIAUX
    #   ------------------------------------------------------------------
    matph = MATER.getMaterialNames()
    matElas = [i for i in matph if i.startswith("ELAS")]
    if not matElas:
        UTMESS("F", "RUPTURE0_5")

    mater_fonc = MATER.getFunction("ELAS", "E") is not None
    e = MATER.getFunction("ELAS", "E")
    nu = MATER.getFunction("ELAS", "NU")
    if not mater_fonc:
        e = MATER.getValueReal("ELAS", "E")
        nu = MATER.getValueReal("ELAS", "NU")

    #   ---
    #   Materiau fonction
    #   ---
    if mater_fonc:
        # erreur fatale si le MCS MATER est renseigne car on n'autorise que la
        # surcharge par un materiau constant
        if args.get("MATER") is not None:
            UTMESS("F", "RUPTURE0_6", valk=MATER.userName)

        prop_e = e.getProperties()
        prop_nu = nu.getProperties()

        #       on verifie que les fonctions ne dependent bien que de TEMP ou NEUT1
        authorized_para = ["TEMP", "NEUT1"]
        if (prop_e[2] not in authorized_para and prop_e[0] != "CONSTANT") or (
            prop_nu[2] not in authorized_para and prop_nu[0] != "CONSTANT"
        ):
            UTMESS("F", "RUPTURE1_67")

        #       on verifie que le nom de parametre est le meme pour e et nu
        assert prop_e[2] == prop_nu[2]
        para_fonc = prop_e[2]

        #       la presence de variables de commande est obligatoire (verif a priori inutile, car on aurait deja du planter
        #       en amont dans STAT_NON_LINE / MECA_STATIQUE (rcvalb))
        assert present_varc

    #   ---
    #   Sinon il s'agit d'un materiau constant
    #   ---
    else:
        if e == 0.0:
            UTMESS("F", "RUPTURE0_53")

        coefd3 = 0.0
        coefd = e * NP.sqrt(2.0 * pi)
        unmnu2 = 1.0 - nu**2
        unpnu = 1.0 + nu
        if MODELISATION == "3D":
            coefd = coefd / (8.0 * unmnu2)
            coefd3 = e * NP.sqrt(2 * pi) / (8.0 * unpnu)
            coefg = unmnu2 / e
            coefg3 = unpnu / e
        elif MODELISATION == "AXIS":
            coefd = coefd / (8.0 * unmnu2)
            coefg = unmnu2 / e
            coefg3 = unpnu / e
        elif MODELISATION == "D_PLAN":
            coefd = coefd / (8.0 * unmnu2)
            coefg = unmnu2 / e
            coefg3 = unpnu / e
        elif MODELISATION == "C_PLAN":
            coefd = coefd / 8.0
            coefg = 1.0 / e
            coefg3 = unpnu / e
        para_fonc = None
    try:
        TYPE_MAILLAGE = args.get("TYPE_MAILLAGE")
    except KeyError:
        TYPE_MAILLAGE = []

    #   TYPE_MAILLAGE n'a de sens qu'en 3D, meme si ce MC existe qd meme pour
    #   les modelisations 2D
    if (TYPE_MAILLAGE != []) and (MODELISATION != "3D"):
        TYPE_MAILLAGE = []

    #  ------------------------------------------------------------------
    #  I. CAS FOND_FISS
    #  ------------------------------------------------------------------
    if FOND_FISS:
        NB_NOEUD_COUPE = args.get("NB_NOEUD_COUPE")

        #     Verification que les levres sont bien en configuration initiale collees
        #     -----------------------------------------------------------------------

        verif_config_init(FOND_FISS)

        #     Recuperation de la liste des noeuds du fond issus de la sd_fond_fissure : Lnoff, de longueur Nnoff
        #     --------------------------------------------------------------------

        Lnoff = get_noeud_fond_fiss(FOND_FISS)
        Nnoff = len(Lnoff)

        #     Creation de la liste des noeuds du fond a calculer : Lnocal, de longueur Nnocal
        #     (obtenue par restriction de Lnoff avec TOUT, NOEUD, SANS_NOEUD)
        #     --------------------------------------------------------------------

        Lnocal = get_noeud_a_calculer(Lnoff, ndim, FOND_FISS, MAILLAGE, EnumTypes, args)
        Nnocal = len(Lnocal)

        #     Recuperation de la liste des mailles de la lèvre supérieure
        #     ------------------------------------------------------------

        gr_maS = FOND_FISS.getUpperLipGroupName()

        if not gr_maS:
            UTMESS("F", "RUPTURE0_19")

        #     Verification de la presence de symetrie
        #     ----------------------------------

        is_symmetric = FOND_FISS.isSymmetric()

        #     Recuperation de la liste des tailles de maille en chaque noeud du fond
        #     ----------------------------------------------------------------------

        if not ABSC_CURV_MAXI:
            list_tail = FOND_FISS.getCrackFrontRadius()
            tailmax = max(list_tail)
            hmax = tailmax * 4
            UTMESS("I", "RUPTURE0_32", valr=hmax)
            tailmin = min(list_tail)
            if tailmax > 2 * tailmin:
                UTMESS("A", "RUPTURE0_17", vali=4, valr=[tailmin, tailmax])
        else:
            hmax = ABSC_CURV_MAXI

        #     ------------------------------------------------------------------
        #     I.1 SOUS-CAS MAILLAGE LIBRE
        #     ------------------------------------------------------------------

        #     creation des directions normales et macr_lign_coup
        if TYPE_MAILLAGE == "LIBRE":
            if not is_symmetric:
                gr_maI = FOND_FISS.getLowerLipGroupName()
            else:
                gr_maI = None

            #        Dictionnaire des coordonnees des noeuds du fond
            d_coor = get_coor_libre(self, Lnoff, RESULTAT, ndim)
            #        Dictionnaire des vecteurs normaux (allant de la levre inf vers la levre sup) et
            #        dictionnaire des vecteurs de propagation
            (dicVDIR, dicVNOR) = get_direction(Nnoff, ndim, Lnoff, FOND_FISS, MAILLAGE)

            #        Abscisse curviligne du fond
            if ndim == 3:
                dicoF = get_absfon(Lnoff, Nnoff, d_coor)

            #        Extraction dep sup/inf sur les normales
            MODEL = RESULTAT.getModel()

            (__TlibS, __TlibI) = get_tab_dep(
                self,
                Lnocal,
                Nnocal,
                d_coor,
                dicVDIR,
                RESULTAT,
                MODEL,
                gr_maS,
                gr_maI,
                NB_NOEUD_COUPE,
                hmax,
                is_symmetric,
                PREC_VIS_A_VIS,
            )

            #        A eclaircir
            Lnofon = Lnocal
            Nbnofo = Nnocal

        #     ------------------------------------------------------------------
        #     I.2 SOUS-CAS MAILLAGE REGLE
        #     ------------------------------------------------------------------

        else:
            #        Dictionnaires des levres
            dicoS = get_dico_levres("sup", FOND_FISS, ndim, Lnoff, Nnoff)
            dicoI = {}
            if not is_symmetric:
                dicoI = get_dico_levres("inf", FOND_FISS, ndim, Lnoff, Nnoff)

            #        Dictionnaire des coordonnees et tableau des deplacements
            (d_coor, __tabl_depl) = get_coor_regle(
                self, RESULTAT, ndim, Lnoff, Lnocal, dicoS, is_symmetric, dicoI
            )
            #        Dictionnaire des vecteurs normaux (allant de la levre inf vers la levre sup) et
            #        dictionnaire des vecteurs de propagation
            (dicVDIR, dicVNOR) = get_direction(Nnoff, ndim, Lnoff, FOND_FISS, MAILLAGE)

            #        Abscisse curviligne du fond
            if ndim == 3:
                dicoF = get_absfon(Lnoff, Nnoff, d_coor)

            #        Noeuds LEVRE_SUP et LEVRE_INF
            (Lnofon, Lnosup, Lnoinf) = get_noeuds_perp_regle(
                Lnocal, d_coor, dicoS, dicoI, Lnoff, PREC_VIS_A_VIS, hmax, is_symmetric
            )

            Nbnofo = len(Lnofon)

    #  ------------------------------------------------------------------
    #  II. CAS X-FEM
    #  ------------------------------------------------------------------

    elif FISSURE:
        #     Recuperation de la liste des tailles de maille en chaque noeud du fond
        if not ABSC_CURV_MAXI:
            list_tail = FISSURE.getCrackFrontRadius()
            tailmax = max(list_tail)
            hmax = tailmax * 5
            UTMESS("I", "RUPTURE0_32", valr=hmax)
            tailmin = min(list_tail)
            if tailmax > 2 * tailmin:
                UTMESS("A", "RUPTURE0_17", vali=5, valr=[tailmin, tailmax])
        else:
            hmax = ABSC_CURV_MAXI

        dmax = PREC_VIS_A_VIS * hmax

        (xcont, MODEL) = verif_resxfem(self, RESULTAT)
        # incohérence entre le modèle et X-FEM
        if xcont == -1:
            UTMESS("F", "RUPTURE0_4")

        #     Recuperation du resultat
        __RESX = get_resxfem(self, xcont, RESULTAT, MODELISATION, MODEL)

        # Recuperation des coordonnees des points du fond de fissure
        # (x,y,z,absc_curv)
        (Coorfo, Vpropa, Nnoff) = get_coor_xfem(args, FISSURE, ndim)

        d_coor = {i: [Coorfo[4 * i], Coorfo[4 * i + 1], Coorfo[4 * i + 2]] for i in range(Nnoff)}

        #     Calcul de la direction de propagation en chaque point du fond
        (VDIR, VNOR, absfon) = get_direction_xfem(Nnoff, Vpropa, Coorfo, ndim)

        #     Extraction des sauts sur la fissure
        NB_NOEUD_COUPE = args.get("NB_NOEUD_COUPE")
        TTSo = get_sauts_xfem(self, Nnoff, Coorfo, VDIR, hmax, NB_NOEUD_COUPE, dmax, __RESX)

        Lnofon = []
        Nbnofo = Nnoff

        #     menage du resultat projete
        del __RESX

        affiche_xfem(self, INFO, Nnoff, VNOR, VDIR)

    #  ------------------------------------------------------------------

    #  creation des objets vides s'ils n'existent pas
    #  de maniere a pouvoir les passer en argument des fonctions
    # c'est pas terrible : il faudrait harmoniser les noms entre les
    # différents cas
    if "__TlibS" not in locals():
        __TlibS = []
    if "__TlibI" not in locals():
        __TlibI = []
    if "Lnosup" not in locals():
        Lnosup = []
    if "Lnoinf" not in locals():
        Lnoinf = []
    if "TTSo" not in locals():
        TTSo = []
    if "VDIR" not in locals():
        VDIR = []
    if "VNOR" not in locals():
        VNOR = []
    if "dicoF" not in locals():
        dicoF = []
    if "dicVDIR" not in locals():
        dicVDIR = []
    if "dicVNOR" not in locals():
        dicVNOR = []
    if "absfon" not in locals():
        absfon = []
    if "d_coor" not in locals():
        assert False
    if "__tabl_depl" not in locals():
        __tabl_depl = []
    if "is_symmetric" not in locals():
        is_symmetric = False

    #  ------------------------------------------------------------------
    #  V. BOUCLE SUR NOEUDS DU FOND
    #  ------------------------------------------------------------------

    if isinstance(RESULTAT, ModeResult):
        type_para = "FREQ"
    else:
        type_para = "INST"

    dico_list_var = RESULTAT.getAccessParameters()

    for ino in range(0, Nbnofo):
        if INFO == 2:
            affiche_traitement(FOND_FISS, Lnofon, ino)

        #     table 'depsup' et 'depinf'
        tabsup = get_tab(
            self,
            "sup",
            ino,
            __TlibS,
            Lnosup,
            TTSo,
            FOND_FISS,
            TYPE_MAILLAGE,
            __tabl_depl,
            is_symmetric,
        )
        tabinf = get_tab(
            self,
            "inf",
            ino,
            __TlibI,
            Lnoinf,
            TTSo,
            FOND_FISS,
            TYPE_MAILLAGE,
            __tabl_depl,
            is_symmetric,
        )

        #     les instants de post-traitement : creation de l_inst
        if type_para == "FREQ":
            (l_inst, PRECISION, CRITERE) = get_liste_freq(tabsup, args)
        else:
            (l_inst, PRECISION, CRITERE) = get_liste_inst(tabsup, args)

        #     récupération de la matrice de changement de repère
        pgl = get_pgl(is_symmetric, FISSURE, ino, VDIR, VNOR, dicVDIR, dicVNOR, Lnofon, ndim)

        #     ------------------------------------------------------------------
        #                         BOUCLE SUR LES INSTANTS/FREQUENCES
        #     ------------------------------------------------------------------
        for iord, inst in enumerate(l_inst):
            #        impression de l'instant de calcul
            if INFO == 2:
                affiche_instant(inst, type_para)

            #        recuperation de la table au bon instant : tabsupi (et tabinfi)
            tabsupi = get_tab_inst(
                "sup", inst, FISSURE, is_symmetric, PRECISION, CRITERE, tabsup, tabinf, type_para
            )
            tabinfi = get_tab_inst(
                "inf", inst, FISSURE, is_symmetric, PRECISION, CRITERE, tabsup, tabinf, type_para
            )

            #        recupération des déplacements sup et inf : ds et di
            (abscs, ds) = get_depl_sup(FOND_FISS, tabsupi, ndim, Lnofon, d_coor, ino, TYPE_MAILLAGE)
            (_, di) = get_depl_inf(
                FOND_FISS, tabinfi, ndim, Lnofon, is_symmetric, d_coor, ino, TYPE_MAILLAGE
            )

            #        TESTS NOMBRE DE NOEUDS
            nbval = len(abscs)

            para = None
            if nbval < 3:
                UTMESS("A+", "RUPTURE0_46")
                if FOND_FISS:
                    UTMESS("A+", "RUPTURE0_47", valk=Lnofon[ino])
                if FISSURE:
                    UTMESS("A+", "RUPTURE0_99", vali=ino + 1)
                UTMESS("A", "RUPTURE0_25")
                kg1 = [0.0] * 8
                kg2 = [0.0] * 8
                kg3 = [0.0] * 8
                liste_noeu_a_extr.append(ino)
                if mater_fonc:
                    para = 0.0

            else:
                #           SI NBVAL >= 3 :

                #            récupération des valeurs des propriétés materiau fonctions des variables de commande
                if mater_fonc:
                    if FOND_FISS:
                        (coefd, coefd3, coefg, coefg3, para) = get_propmat_varc_fem(
                            self,
                            RESULTAT,
                            MAILLAGE,
                            MATER,
                            MODELISATION,
                            Lnofon,
                            ino,
                            inst,
                            para_fonc,
                        )
                    elif FISSURE:
                        (coefd, coefd3, coefg, coefg3, para) = get_propmat_varc_xfem(
                            self,
                            args,
                            RESULTAT,
                            MAILLAGE,
                            MATER,
                            MODELISATION,
                            FISSURE,
                            ndim,
                            ino,
                            inst,
                            para_fonc,
                        )

                #           calcul du saut de déplacements dans le nouveau repère
                saut = get_saut(self, pgl, ds, di, INFO, FISSURE, is_symmetric, abscs, ndim)

                #           CALCUL DES K1, K2, K3
                (isig, kgsig, saut2) = get_kgsig(saut, nbval, coefd, coefd3)

                #           calcul des K et de G par les methodes 1, 2 et 3
                kg1 = get_meth1(self, abscs, coefg, coefg3, kgsig, isig, saut2, INFO, ndim)
                kg2 = get_meth2(self, abscs, coefg, coefg3, kgsig, isig, saut2, INFO, ndim)
                kg3 = get_meth3(self, abscs, coefg, coefg3, kgsig, isig, saut2, INFO, ndim)

            #        creation de la table
            kg = NP.array([kg1, kg2, kg3])
            kg = NP.transpose(kg)

            nume = dico_list_var["NUME_ORDRE"][dico_list_var[type_para].index(inst)]

            tabout = get_tabout(
                self,
                kg,
                args,
                TITRE,
                FOND_FISS,
                MODELISATION,
                FISSURE,
                ndim,
                ino,
                inst,
                iord,
                Lnofon,
                dicoF,
                absfon,
                Nnoff,
                tabout,
                type_para,
                nume,
                para_fonc,
                para,
                d_coor,
            )

    #     Fin de la boucle sur les instants

    #  Fin de la boucle sur les noeuds du fond de fissure

    # Si le nombre de noeuds dans la direction normale au fond de fissure est
    # insuffisant, on extrapole
    if (ndim == 3) and liste_noeu_a_extr != []:
        tabout = expand_values(self, tabout, liste_noeu_a_extr, TITRE, type_para)

    #  Tri de la table si nécessaire
    if len(l_inst) != 1 and ndim == 3:
        if type_para == "FREQ":
            tabout = CALC_TABLE(
                reuse=tabout,
                TABLE=tabout,
                ACTION=_F(OPERATION="TRI", NOM_PARA=("FREQ", "ABSC_CURV"), ORDRE="CROISSANT"),
            )
        else:
            tabout = CALC_TABLE(
                reuse=tabout,
                TABLE=tabout,
                ACTION=_F(OPERATION="TRI", NOM_PARA=("INST", "ABSC_CURV"), ORDRE="CROISSANT"),
            )

    return tabout
