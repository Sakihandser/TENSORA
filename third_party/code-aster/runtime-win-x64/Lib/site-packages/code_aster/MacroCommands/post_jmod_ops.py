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

# Responsible Person: Jefri Draup
import numpy as np
import copy
import aster
from ..Cata.Syntax import _F
from ..Messages import UTMESS, MasquerAlarme, RetablirAlarme
from ..Utilities.misc import get_titre_concept
from ..CodeCommands import (
    AFFE_MODELE,
    CALC_CHAMP,
    CALC_TABLE,
    CREA_CHAMP,
    CREA_TABLE,
    CREA_RESU,
    DEFI_GROUP,
    FORMULE,
    POST_ELEM,
    POST_RELEVE_T,
)

# Define global variable to unit test all functions that have been used
# Help with NON-REGRESSION
# Analytic Test
TestUNIT = "YES"
TestUNIT = "NO"


def cross_product(a, b):
    """
    The cross product of two vectors: a x b
    Store in list type
    """

    cross = [
        (a[1] * b[2]) - (a[2] * b[1]),
        (a[2] * b[0]) - (a[0] * b[2]),
        (a[0] * b[1]) - (a[1] * b[0]),
    ]

    return cross


# -----------------------------------------------------------------------------


def syme_point_plan(P1, P2, P3, PM):
    """
    Determine symmetry point of PM through plane P1 P2 P3
    Store in list type
    """

    vec1 = np.array(P3) - np.array(P1)
    vec2 = np.array(P2) - np.array(P1)
    normal = np.cross(vec1, vec2)

    A, B, C = normal
    D = np.dot(normal, np.array(P3)) * -1.0

    t = (A * PM[0] + B * PM[1] + C * PM[2] + D) / (A * A + B * B + C * C) * -1.0

    PM_sym = [2 * (PM[0] + A * t) - PM[0], 2 * (PM[1] + B * t) - PM[1], 2 * (PM[2] + C * t) - PM[2]]

    return PM_sym


# -----------------------------------------------------------------------------


def unit_normal(P0, P1, P2):
    """
    Compute the unit normal vector of plane P0 P1 P2
    Store in list type
    """

    x_co = np.linalg.det([[1, P0[1], P0[2]], [1, P1[1], P1[2]], [1, P2[1], P2[2]]])

    y_co = np.linalg.det([[P0[0], 1, P0[2]], [P1[0], 1, P1[2]], [P2[0], 1, P2[2]]])

    z_co = np.linalg.det([[P0[0], P0[1], 1], [P1[0], P1[1], 1], [P2[0], P2[1], 1]])

    magnitude = (x_co**2 + y_co**2 + z_co**2) ** 0.5

    return [x_co / magnitude, y_co / magnitude, z_co / magnitude]


# -----------------------------------------------------------------------------


def get_contraint(self, __RESU, inst):
    """
    Get contraint
    """

    __SIGF = CREA_CHAMP(
        TYPE_CHAM="ELGA_SIEF_R", OPERATION="EXTR", RESULTAT=__RESU, NOM_CHAM="SIEF_ELGA", INST=inst
    )

    return __SIGF


# -----------------------------------------------------------------------------


def get_deformation(self, __RESU, nom_cham, inst):
    """
    Get deformation
    """

    __EPSI_XX = CREA_CHAMP(
        TYPE_CHAM=nom_cham + "_EPSI_R",
        OPERATION="EXTR",
        RESULTAT=__RESU,
        NOM_CHAM="EPSI_" + nom_cham,
        INST=inst,
    )

    return __EPSI_XX


# -----------------------------------------------------------------------------


def get_displacement(self, __RESU, inst):
    """
    Get displacement
    """

    __DEPINT = CREA_CHAMP(
        TYPE_CHAM="NOEU_DEPL_R", OPERATION="EXTR", RESULTAT=__RESU, NOM_CHAM="DEPL", INST=inst
    )

    return __DEPINT


# -----------------------------------------------------------------------------


def get_strain_energy(self, __RESU, inst):
    """
    Get strain energy
    """

    __WELAS = CREA_CHAMP(
        TYPE_CHAM="ELGA_ENER_R", OPERATION="EXTR", RESULTAT=__RESU, NOM_CHAM="ETOT_ELGA", INST=inst
    )

    return __WELAS


# -----------------------------------------------------------------------------


def display_node_inst(FOND_FISS, iNP, inst, NB_COUCHES, NP, closedCrack):
    """
    Display node and instant being processed
    """

    NOFF = FOND_FISS.getCrackFrontNodes()
    if NOFF is None:
        UTMESS("F", "RUPTURE0_11")

    if closedCrack == "OUI":
        del NOFF[-1]

    NOFF.append("GLOBAL  ")
    texte = (
        "\n"
        + "#"
        + "-" * 78
        + "\n"
        + "# NODE: %s" % NOFF[iNP]
        + " INSTANT: %f" % inst
        + "      NB_COUCHES: %i" % NB_COUCHES
        + "      ("
        + str(iNP + 1)
        + "/"
        + str(NP)
        + ")"
        + "\n"
    )

    aster.affiche("MESSAGE", texte)


# -----------------------------------------------------------------------------


def all_coordinates(self, MAIL):
    """
    Extract the coordinates of all nodes
    Store in dict type
    """

    nodes = [str(node + 1) for node in MAIL.getNodes(localNumbering=True)]
    node_co = np.reshape(MAIL.getCoordinates().getValues(), (len(nodes), 3)).tolist()

    all_co = dict(zip(nodes, node_co))

    return all_co


# -----------------------------------------------------------------------------


def no_fond_fiss(self, FOND_FISS):
    """
    Extract nodes of crack front, number of nodes and crack front type
    Store nodes in dict type
    """

    fond_fiss_no = FOND_FISS.getCrackFrontNodes()
    if fond_fiss_no is None:
        UTMESS("F", "RUPTURE0_11")

    if fond_fiss_no[0] != fond_fiss_no[-1]:
        closedCrack = "NON"
        NP = len(fond_fiss_no)
    else:
        closedCrack = "OUI"
        NP = len(fond_fiss_no) - 1

    TPFISS = dict(zip(range(1, 1 + NP), fond_fiss_no))

    return (NP, TPFISS, closedCrack)


# -----------------------------------------------------------------------------


def no_lips(self, NP, FOND_FISS, NB_COUCHES, is_symmetric, closedCrack):
    """
    Extract the nodes of lips through nodes of crack front
    Store in dict type
    """

    TLIPSUP = {}
    TLIPINF = {}

    nodeNum = 100
    lip_sup_nodes = FOND_FISS.getUpperNormNodes2()

    if lip_sup_nodes is None:
        UTMESS("F", "RUPTURE0_11")

    if not is_symmetric:
        if NB_COUCHES < 10:
            lip_inf_nodes = FOND_FISS.getLowerNormNodes2()
        else:
            lip_inf_nodes = FOND_FISS.getLowerNormNodes2()

        if lip_sup_nodes is None:
            UTMESS("F", "RUPTURE0_11")

    for i in range(NP):
        TLIPSUPX = lip_sup_nodes[nodeNum * i : nodeNum * (i + 1)]
        TLIPSUP[i + 1] = [x.strip() for x in TLIPSUPX if x.strip()]

        if not is_symmetric:
            TLIPINFX = lip_inf_nodes[nodeNum * i : nodeNum * (i + 1)]
            TLIPINF[i + 1] = [x.strip() for x in TLIPINFX if x.strip()]

    if closedCrack == "OUI":
        no_cross_lip_sup = None
        no_cross_lip_inf = None

        for i in TLIPSUP[1]:
            for j in TLIPSUP[2]:
                if i == j:
                    no_cross_lip_sup = i

        if no_cross_lip_sup is not None:
            for iNP in range(NP):
                idx = TLIPSUP[iNP + 1].index(no_cross_lip_sup)
                TLIPSUP[iNP + 1] = TLIPSUP[iNP + 1][: idx + 1]

        if not is_symmetric:
            for i in TLIPINF[1]:
                for j in TLIPINF[2]:
                    if i == j:
                        no_cross_lip_inf = i

            if no_cross_lip_inf is not None:
                for iNP in range(NP):
                    idx = TLIPINF[iNP + 1].index(no_cross_lip_inf)
                    TLIPINF[iNP + 1] = TLIPINF[iNP + 1][: idx + 1]
    return (TLIPSUP, TLIPINF)


# -----------------------------------------------------------------------------


def na_poinsf(self, FOND_FISS, is_symmetric, elemType):
    """
    Get corner node of first element on crack lips
    Store in node name
    """

    lip_sup_nodes = FOND_FISS.getUpperNormNodes2()
    if lip_sup_nodes is None:
        UTMESS("F", "RUPTURE0_11")

    if is_symmetric:
        if elemType == "SEG2":
            poinsf_na = lip_sup_nodes[1]
        else:
            poinsf_na = lip_sup_nodes[2]
    else:
        lip_inf_nodes = FOND_FISS.getLowerNormNodes2()
        if lip_inf_nodes is None:
            UTMESS("F", "RUPTURE0_11")

        if elemType == "SEG2":
            poinsf_na = (lip_sup_nodes[1], lip_inf_nodes[1])
        else:
            poinsf_na = (lip_sup_nodes[2], lip_inf_nodes[2])

    return poinsf_na


# -----------------------------------------------------------------------------


def na_lips(self, MAIL__, FOND_FISS, is_symmetric):
    """
    Extract name of lips
    """

    lipSupName = FOND_FISS.getUpperLipGroupName()

    gr_maS = FOND_FISS.getUpperLipGroupName()
    if not gr_maS:
        UTMESS("F", "RUPTURE0_19")

    lipInfName = None

    if not is_symmetric:
        lipInfName = FOND_FISS.getLowerLipGroupName()

        gr_maI = FOND_FISS.getLowerLipGroupName()
        if not gr_maI:
            UTMESS("F", "RUPTURE0_19")

    return (lipSupName, lipInfName)


# -----------------------------------------------------------------------------


def crea_group_no_from_no(self, MAIL, nameGroupNo, lNode):
    """
    Create node group from node
    """

    DEFI_GROUP(reuse=MAIL, MAILLAGE=MAIL, CREA_GROUP_NO=(_F(NOM=nameGroupNo, NOEUD=lNode),))


# -----------------------------------------------------------------------------


def crea_group_no_from_group_ma(self, MAIL, nameGroupNo, nameGroupMa):
    """
    Create node group from mail group and then delete mail group
    """

    DEFI_GROUP(
        reuse=MAIL, MAILLAGE=MAIL, CREA_GROUP_NO=(_F(NOM=nameGroupNo, GROUP_MA=nameGroupMa),)
    )

    DEFI_GROUP(reuse=MAIL, MAILLAGE=MAIL, DETR_GROUP_MA=_F(NOM=nameGroupMa))


def crea_group_ma_from_list_ma(self, MAIL, listma, nameGroupMa):
    DEFI_GROUP(reuse=MAIL, MAILLAGE=MAIL, CREA_GROUP_MA=_F(NOM=nameGroupMa, MAILLE=listma))


# -----------------------------------------------------------------------------


def crea_group_ma_appui_group_no(self, MAIL, nameGroupMa, nameGroupNo):
    """
    Create mail group supported on node group
    """

    DEFI_GROUP(
        reuse=MAIL,
        MAILLAGE=MAIL,
        CREA_GROUP_MA=_F(
            NOM=nameGroupMa,
            OPTION="APPUI",
            TYPE_MAILLE="3D",
            GROUP_NO=nameGroupNo,
            TYPE_APPUI="AU_MOINS_UN",
        ),
    )


# -----------------------------------------------------------------------------


def crea_group_ma_appui_group_no_2d(self, MAIL, nameGroupMa, nameGroupNo):
    """
    Create mail group supported on node group with mail type in 2D
    """

    DEFI_GROUP(
        reuse=MAIL,
        MAILLAGE=MAIL,
        CREA_GROUP_MA=_F(
            NOM=nameGroupMa,
            OPTION="APPUI",
            TYPE_MAILLE="2D",
            GROUP_NO=nameGroupNo,
            TYPE_APPUI="AU_MOINS_UN",
        ),
    )


# -----------------------------------------------------------------------------


def del_group_ma(self, MAIL, lMail):
    """
    Delete mail group
    """

    DEFI_GROUP(reuse=MAIL, MAILLAGE=MAIL, DETR_GROUP_MA=_F(NOM=lMail))


# -----------------------------------------------------------------------------


def del_group_no(self, MAIL, lGroupNo):
    """
    Delete node group
    """

    DEFI_GROUP(reuse=MAIL, MAILLAGE=MAIL, DETR_GROUP_NO=_F(NOM=lGroupNo))


# -----------------------------------------------------------------------------


def diff_group_ma(self, MAIL, nameGroupMa, lMail1, lMail2):
    """
    Create mail group that is different from two other mail groups
    """

    DEFI_GROUP(reuse=MAIL, MAILLAGE=MAIL, CREA_GROUP_MA=_F(NOM=nameGroupMa, DIFFE=(lMail1, lMail2)))


# -----------------------------------------------------------------------------


def diff_group_no(self, MAIL, nameGroupNo, nameGroupsNoDiff):
    """
    Create node group that is different of many node groups
    """

    DEFI_GROUP(reuse=MAIL, MAILLAGE=MAIL, CREA_GROUP_NO=_F(NOM=nameGroupNo, DIFFE=nameGroupsNoDiff))


# -----------------------------------------------------------------------------


def intersec_group_ma(self, MAIL, nameGroupMa, lMail1, lMail2):
    """
    Intersection of two mail groups
    """

    DEFI_GROUP(
        reuse=MAIL, MAILLAGE=MAIL, CREA_GROUP_MA=_F(NOM=nameGroupMa, INTERSEC=(lMail1, lMail2))
    )


# -----------------------------------------------------------------------------


def intersec_group_no(self, MAIL, nameGroupNo, lNode1, lNode2):
    """
    Intersection of two node groups
    """

    DEFI_GROUP(
        reuse=MAIL, MAILLAGE=MAIL, CREA_GROUP_NO=_F(NOM=nameGroupNo, INTERSEC=(lNode1, lNode2))
    )


# -----------------------------------------------------------------------------


def union_group_ma(self, MAIL, nameGroupMa, lMail1, lMail2):
    """
    Create mail group that is different from two other mail groups
    """

    DEFI_GROUP(reuse=MAIL, MAILLAGE=MAIL, CREA_GROUP_MA=_F(NOM=nameGroupMa, UNION=(lMail1, lMail2)))


# -----------------------------------------------------------------------------


def field_node_to_gauss(self, MODE, __FIELD, nameCmp, nameCmpResu):
    """
    Change nodes to gauss points of field
    """

    __FIELD = CREA_CHAMP(
        OPERATION="ASSE",
        TYPE_CHAM="NOEU_EPSI_R",
        MODELE=MODE,
        ASSE=(_F(TOUT="OUI", CHAM_GD=__FIELD, NOM_CMP=(nameCmp,), NOM_CMP_RESU=(nameCmpResu,)),),
    )

    __FIELD_GAUSS = CREA_CHAMP(
        TYPE_CHAM="ELGA_EPSI_R", OPERATION="DISC", MODELE=MODE, PROL_ZERO="OUI", CHAM_GD=__FIELD
    )

    return __FIELD_GAUSS


# -----------------------------------------------------------------------------


def calc_tvect(self, all_co, TPFISS, VNPF, N1, N2, N3):
    """
    Compute TVECTEUR
    """

    if cross_product([1, 0, 0], [0, 1, 0]) != [0, 0, 1]:
        UTMESS("A", "RUPTURE4_1", valr=cross_product([1, 0, 0], [0, 1, 0]))

    VTFF1 = (np.array(all_co[TPFISS[N2]]) - np.array(all_co[TPFISS[N1]])).tolist()
    VNFF1 = cross_product(VTFF1, VNPF)

    VTFF2 = (np.array(all_co[TPFISS[N3]]) - np.array(all_co[TPFISS[N2]])).tolist()
    VNFF2 = cross_product(VTFF2, VNPF)

    TVECT = (0.5 * (np.array(VNFF1) + np.array(VNFF2))).tolist()

    return TVECT


# -----------------------------------------------------------------------------


def calc_tvect_bord(self, all_co, TPFISS, VNPF, N1, N2, PI):
    """
    Compute TVECTEUR for 2 nodes on board in opened crack front case
    """

    if cross_product([1, 0, 0], [0, 1, 0]) != [0, 0, 1]:
        UTMESS("A", "RUPTURE4_1", valr=cross_product([1, 0, 0], [0, 1, 0]))

    if N1 < N2:
        VECT1X = np.array(all_co[TPFISS[N2]]) - np.array(all_co[TPFISS[N1]])
    else:
        VECT1X = np.array(all_co[TPFISS[N1]]) - np.array(all_co[TPFISS[N2]])

    VECT1X = VECT1X.tolist()
    VECT1 = cross_product(VECT1X, VNPF)

    VPLANX = (np.array(all_co[PI]) - np.array(all_co[TPFISS[N1]])).tolist()
    VPLAN = cross_product(VPLANX, VNPF)

    if -1.0e-10 <= (np.dot(np.array(VPLAN), np.array(VECT1))) <= 1.0e-10:
        TVECT = VECT1

    else:
        PK = (np.array(all_co[TPFISS[N1]]) + np.array(VNPF)).tolist()

        P1 = (np.array(all_co[TPFISS[N1]]) + np.array(VECT1)).tolist()

        P2 = syme_point_plan(all_co[PI], all_co[TPFISS[N1]], PK, P1)

        VECT2 = (np.array(P2) - np.array(all_co[TPFISS[N1]])).tolist()

        TVECT = (np.array(VECT1) + np.array(VECT2)).tolist()

    return TVECT


# -----------------------------------------------------------------------------


def calc_area(self, MAILAREA, nameGroupMa):
    """
    Calculate area of surface
    """

    __MODE = AFFE_MODELE(
        MAILLAGE=MAILAREA, AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="3D")
    )

    __FIELD_AREA = CREA_CHAMP(
        OPERATION="AFFE",
        TYPE_CHAM="ELGA_NEUT_R",
        MODELE=__MODE,
        PROL_ZERO="OUI",
        AFFE=(_F(GROUP_MA=nameGroupMa, NOM_CMP="X1", VALE=1.0),),
    )

    __RESU_AREA = CREA_RESU(
        OPERATION="AFFE",
        TYPE_RESU="EVOL_ELAS",
        AFFE=_F(NOM_CHAM="VARI_ELGA", MODELE=__MODE, INST=0.0, CHAM_GD=__FIELD_AREA),
    )

    __POST_AREA = POST_ELEM(
        RESULTAT=__RESU_AREA,
        MODELE=__MODE,
        INST=0.0,
        INTEGRALE=_F(NOM_CHAM="VARI_ELGA", GROUP_MA=nameGroupMa, NOM_CMP="X1", TYPE_MAILLE="2D"),
    )

    __AREA = __POST_AREA.EXTR_TABLE().values()["INTE_X1"][0]

    del __MODE, __FIELD_AREA, __RESU_AREA, __POST_AREA

    return __AREA


# -----------------------------------------------------------------------------


def calc_vari_area_no_bord(self, MAIL, NB_COUCHES, lNode1, lNode2, NODESBOUGE, lVect, is_symmetric):
    """
    Calculate varied area
    """

    if is_symmetric:
        crea_group_no_from_no(self, MAIL, "NOAREAX", lNode1[1 : len(lNode1) - 1])
        crea_group_no_from_no(self, MAIL, "NOAREAY", lNode2[1 : len(lNode2) - 1])
    else:
        crea_group_no_from_no(
            self,
            MAIL,
            "NOAREAX",
            lNode1[0][1 : len(lNode1[0]) - 1] + lNode1[1][1 : len(lNode1[1]) - 1],
        )
        crea_group_no_from_no(
            self,
            MAIL,
            "NOAREAY",
            lNode2[0][1 : len(lNode2[0]) - 1] + lNode2[1][1 : len(lNode2[1]) - 1],
        )

    crea_group_ma_appui_group_no_2d(self, MAIL, "MAAREAX", "NOAREAX")
    crea_group_ma_appui_group_no_2d(self, MAIL, "MAAREAY", "NOAREAY")

    intersec_group_ma(self, MAIL, "MAAREA", "MAAREAX", "MAAREAY")

    areaIni = calc_area(self, MAIL, "MAAREA")

    del_group_no(self, MAIL, "NOAREAX")
    del_group_no(self, MAIL, "NOAREAY")
    del_group_ma(self, MAIL, "MAAREAX")
    del_group_ma(self, MAIL, "MAAREAY")
    del_group_ma(self, MAIL, "MAAREA")

    coords = MAIL.getCoordinates()

    for iNode in NODESBOUGE:
        node = coords.getNode(iNode)
        node[0] += lVect[0]
        node[1] += lVect[1]
        node[2] += lVect[2]
        coords.setNode(node)

    if is_symmetric:
        crea_group_no_from_no(self, MAIL, "NOAREAX", lNode1[1 : len(lNode1) - 1])
        crea_group_no_from_no(self, MAIL, "NOAREAY", lNode2[1 : len(lNode2) - 1])
    else:
        crea_group_no_from_no(
            self,
            MAIL,
            "NOAREAX",
            lNode1[0][1 : len(lNode1[0]) - 1] + lNode1[1][1 : len(lNode1[1]) - 1],
        )
        crea_group_no_from_no(
            self,
            MAIL,
            "NOAREAY",
            lNode2[0][1 : len(lNode2[0]) - 1] + lNode2[1][1 : len(lNode2[1]) - 1],
        )

    crea_group_ma_appui_group_no_2d(self, MAIL, "MAAREAX", "NOAREAX")
    crea_group_ma_appui_group_no_2d(self, MAIL, "MAAREAY", "NOAREAY")

    intersec_group_ma(self, MAIL, "MAAREA", "MAAREAX", "MAAREAY")

    areaFin = calc_area(self, MAIL, "MAAREA")

    del_group_no(self, MAIL, "NOAREAX")
    del_group_no(self, MAIL, "NOAREAY")
    del_group_ma(self, MAIL, "MAAREAX")
    del_group_ma(self, MAIL, "MAAREAY")
    del_group_ma(self, MAIL, "MAAREA")

    for iNode in NODESBOUGE:
        node = coords.getNode(iNode)
        node[0] -= lVect[0]
        node[1] -= lVect[1]
        node[2] -= lVect[2]
        coords.setNode(node)

    XAIRE = areaFin - areaIni

    if not is_symmetric:
        XAIRE = XAIRE / 2.0

    return XAIRE


# -----------------------------------------------------------------------------


def calc_vari_area_no_midd(
    self,
    MAIL,
    NB_COUCHES,
    lNode,
    NODESBOUGE,
    lVect,
    is_symmetric,
    closedCrack,
    lipSupName,
    lipInfName,
):
    """
    Calculate varied area
    """

    if is_symmetric:
        crea_group_no_from_no(self, MAIL, "NOAREA", lNode[1 : len(lNode) - 1])
    else:
        crea_group_no_from_no(
            self, MAIL, "NOAREA", lNode[0][1 : len(lNode[0]) - 1] + lNode[1][1 : len(lNode[1]) - 1]
        )

    crea_group_ma_appui_group_no_2d(self, MAIL, "MAAREATEM", "NOAREA")
    if is_symmetric:
        intersec_group_ma(self, MAIL, "MAAREA", lipSupName, "MAAREATEM")
    else:
        intersec_group_ma(self, MAIL, "MAAREASUP", lipInfName, "MAAREATEM")
        intersec_group_ma(self, MAIL, "MAAREAINF", lipSupName, "MAAREATEM")
        union_group_ma(self, MAIL, "MAAREA", "MAAREASUP", "MAAREAINF")

    areaIni = calc_area(self, MAIL, "MAAREA")

    del_group_no(self, MAIL, "NOAREA")
    del_group_ma(self, MAIL, "MAAREA")
    del_group_ma(self, MAIL, "MAAREATEM")
    if not is_symmetric:
        del_group_ma(self, MAIL, "MAAREASUP")
        del_group_ma(self, MAIL, "MAAREAINF")

    coords = MAIL.getCoordinates()

    for iNode in NODESBOUGE:
        node = coords.getNode(iNode)
        node[0] += lVect[0]
        node[1] += lVect[1]
        node[2] += lVect[2]
        coords.setNode(node)

    if is_symmetric:
        crea_group_no_from_no(self, MAIL, "NOAREA", lNode[1 : len(lNode) - 1])
    else:
        crea_group_no_from_no(
            self, MAIL, "NOAREA", lNode[0][1 : len(lNode[0]) - 1] + lNode[1][1 : len(lNode[1]) - 1]
        )

    crea_group_ma_appui_group_no_2d(self, MAIL, "MAAREATEM", "NOAREA")

    if is_symmetric:
        intersec_group_ma(self, MAIL, "MAAREA", lipSupName, "MAAREATEM")
    else:
        intersec_group_ma(self, MAIL, "MAAREASUP", lipInfName, "MAAREATEM")
        intersec_group_ma(self, MAIL, "MAAREAINF", lipSupName, "MAAREATEM")
        union_group_ma(self, MAIL, "MAAREA", "MAAREASUP", "MAAREAINF")

    areaFin = calc_area(self, MAIL, "MAAREA")

    del_group_no(self, MAIL, "NOAREA")
    del_group_ma(self, MAIL, "MAAREA")
    del_group_ma(self, MAIL, "MAAREATEM")
    if not is_symmetric:
        del_group_ma(self, MAIL, "MAAREASUP")
        del_group_ma(self, MAIL, "MAAREAINF")

    for iNode in NODESBOUGE:
        node = coords.getNode(iNode)
        node[0] -= lVect[0]
        node[1] -= lVect[1]
        node[2] -= lVect[2]
        coords.setNode(node)

    XAIRE = areaFin - areaIni

    if not is_symmetric:
        XAIRE = XAIRE / 2.0

    return XAIRE


# -----------------------------------------------------------------------------


def calc_vari_area_no_glob(
    self,
    MAIL,
    NB_COUCHES,
    NPP,
    lNode,
    NODESBOUGE,
    lVect,
    is_symmetric,
    closedCrack,
    lipSupName,
    lipInfName,
):
    """
    Calculate varied area
    """

    Nodes = []

    if is_symmetric:
        if closedCrack != "OUI":
            for iNP in range(2, NPP):
                Nodes = Nodes + lNode[iNP][1 : len(lNode[iNP]) - 1]
        else:
            for iNP in range(1, NPP + 1):
                Nodes = Nodes + lNode[iNP][1 : len(lNode[iNP]) - 1]
    else:
        if closedCrack != "OUI":
            for iNP in range(2, NPP):
                Nodes = (
                    Nodes
                    + lNode[0][iNP][1 : len(lNode[0][iNP]) - 1]
                    + lNode[1][iNP][1 : len(lNode[1][iNP]) - 1]
                )
        else:
            for iNP in range(1, NPP + 1):
                Nodes = (
                    Nodes
                    + lNode[0][iNP][1 : len(lNode[0][iNP]) - 1]
                    + lNode[1][iNP][1 : len(lNode[1][iNP]) - 1]
                )

    crea_group_no_from_no(self, MAIL, "NOAREA", Nodes)
    crea_group_ma_appui_group_no_2d(self, MAIL, "MAAREATEM", "NOAREA")

    if is_symmetric:
        intersec_group_ma(self, MAIL, "MAAREA", lipSupName, "MAAREATEM")
    else:
        intersec_group_ma(self, MAIL, "MAAREASUP", lipInfName, "MAAREATEM")
        intersec_group_ma(self, MAIL, "MAAREAINF", lipSupName, "MAAREATEM")
        union_group_ma(self, MAIL, "MAAREA", "MAAREASUP", "MAAREAINF")

    areaIni = calc_area(self, MAIL, "MAAREA")

    del_group_no(self, MAIL, "NOAREA")
    del_group_ma(self, MAIL, "MAAREA")
    del_group_ma(self, MAIL, "MAAREATEM")
    if not is_symmetric:
        del_group_ma(self, MAIL, "MAAREASUP")
        del_group_ma(self, MAIL, "MAAREAINF")

    coords = MAIL.getCoordinates()

    for iKey in NODESBOUGE.keys():
        for iNode in NODESBOUGE[iKey]:
            node = coords.getNode(iNode)
            node[0] += lVect[iKey][0]
            node[1] += lVect[iKey][1]
            node[2] += lVect[iKey][2]
            coords.setNode(node)

    crea_group_no_from_no(self, MAIL, "NOAREA", Nodes)
    crea_group_ma_appui_group_no_2d(self, MAIL, "MAAREATEM", "NOAREA")

    if is_symmetric:
        intersec_group_ma(self, MAIL, "MAAREA", lipSupName, "MAAREATEM")
    else:
        intersec_group_ma(self, MAIL, "MAAREASUP", lipInfName, "MAAREATEM")
        intersec_group_ma(self, MAIL, "MAAREAINF", lipSupName, "MAAREATEM")
        union_group_ma(self, MAIL, "MAAREA", "MAAREASUP", "MAAREAINF")

    areaFin = calc_area(self, MAIL, "MAAREA")

    del_group_no(self, MAIL, "NOAREA")
    del_group_ma(self, MAIL, "MAAREA")
    del_group_ma(self, MAIL, "MAAREATEM")
    if not is_symmetric:
        del_group_ma(self, MAIL, "MAAREASUP")
        del_group_ma(self, MAIL, "MAAREAINF")

    for iKey in NODESBOUGE.keys():
        for iNode in NODESBOUGE[iKey]:
            node = coords.getNode(iNode)
            node[0] -= lVect[iKey][0]
            node[1] -= lVect[iKey][1]
            node[2] -= lVect[iKey][2]
            coords.setNode(node)

    XAIRE = areaFin - areaIni

    if not is_symmetric:
        XAIRE = XAIRE / 2.0

    return XAIRE


# -----------------------------------------------------------------------------


def calc_vari_area_no_glob_one_elem(
    self, MAIL, NB_COUCHES, NPP, lNode, NODESBOUGE, lVect, is_symmetric
):
    """
    Calculate varied area
    """

    if is_symmetric:
        crea_group_no_from_no(self, MAIL, "NOAREAX", lNode[1][1 : len(lNode[1]) - 1])
        crea_group_no_from_no(self, MAIL, "NOAREAY", lNode[NPP][1 : len(lNode[NPP]) - 1])
    else:
        crea_group_no_from_no(
            self,
            MAIL,
            "NOAREAX",
            lNode[0][1][1 : len(lNode[0][1]) - 1] + lNode[1][1][1 : len(lNode[1][1]) - 1],
        )
        crea_group_no_from_no(
            self,
            MAIL,
            "NOAREAY",
            lNode[0][NPP][1 : len(lNode[0][NPP]) - 1] + lNode[1][NPP][1 : len(lNode[1][NPP]) - 1],
        )

    crea_group_ma_appui_group_no_2d(self, MAIL, "MAAREAX", "NOAREAX")
    crea_group_ma_appui_group_no_2d(self, MAIL, "MAAREAY", "NOAREAY")

    intersec_group_ma(self, MAIL, "MAAREA", "MAAREAX", "MAAREAY")

    areaIni = calc_area(self, MAIL, "MAAREA")

    del_group_no(self, MAIL, "NOAREAX")
    del_group_no(self, MAIL, "NOAREAY")
    del_group_ma(self, MAIL, "MAAREAX")
    del_group_ma(self, MAIL, "MAAREAY")
    del_group_ma(self, MAIL, "MAAREA")

    coords = MAIL.getCoordinates()

    for iKey in NODESBOUGE.keys():
        for iNode in NODESBOUGE[iKey]:
            coords[iNode * 3] = coords[iNode * 3] + lVect[iKey][0]
            coords[iNode * 3 + 1] = coords[iNode * 3 + 1] + lVect[iKey][1]
            coords[iNode * 3 + 2] = coords[iNode * 3 + 2] + lVect[iKey][2]

    if is_symmetric:
        crea_group_no_from_no(self, MAIL, "NOAREAX", lNode[1][1 : len(lNode[1]) - 1])
        crea_group_no_from_no(self, MAIL, "NOAREAY", lNode[NPP][1 : len(lNode[NPP]) - 1])
    else:
        crea_group_no_from_no(
            self,
            MAIL,
            "NOAREAX",
            lNode[0][1][1 : len(lNode[0][1]) - 1] + lNode[1][1][1 : len(lNode[1][1]) - 1],
        )
        crea_group_no_from_no(
            self,
            MAIL,
            "NOAREAY",
            lNode[0][NPP][1 : len(lNode[0][NPP]) - 1] + lNode[1][NPP][1 : len(lNode[1][NPP]) - 1],
        )

    crea_group_ma_appui_group_no_2d(self, MAIL, "MAAREAX", "NOAREAX")
    crea_group_ma_appui_group_no_2d(self, MAIL, "MAAREAY", "NOAREAY")

    intersec_group_ma(self, MAIL, "MAAREA", "MAAREAX", "MAAREAY")

    areaFin = calc_area(self, MAIL, "MAAREA")

    del_group_no(self, MAIL, "NOAREAX")
    del_group_no(self, MAIL, "NOAREAY")
    del_group_ma(self, MAIL, "MAAREAX")
    del_group_ma(self, MAIL, "MAAREAY")
    del_group_ma(self, MAIL, "MAAREA")

    for iKey in NODESBOUGE.keys():
        for iNode in NODESBOUGE[iKey]:
            coords[iNode * 3] = coords[iNode * 3] - lVect[iKey][0]
            coords[iNode * 3 + 1] = coords[iNode * 3 + 1] - lVect[iKey][1]
            coords[iNode * 3 + 2] = coords[iNode * 3 + 2] - lVect[iKey][2]

    XAIRE = areaFin - areaIni

    if not is_symmetric:
        XAIRE = XAIRE / 2.0

    return XAIRE


# -----------------------------------------------------------------------------


def cal_strain_energy(self, MODE, __EPSI_ELGA, __SIGF):
    """
    Calculation strain energy W = 1/2 SIGF * EPSI
    """

    __CHW = CREA_CHAMP(
        OPERATION="ASSE",
        TYPE_CHAM="ELGA_NEUT_R",
        MODELE=MODE,
        PROL_ZERO="OUI",
        ASSE=(
            _F(TOUT="OUI", CHAM_GD=__EPSI_ELGA, NOM_CMP=("EPXX",), NOM_CMP_RESU=("X1",)),
            _F(TOUT="OUI", CHAM_GD=__EPSI_ELGA, NOM_CMP=("EPYY",), NOM_CMP_RESU=("X2",)),
            _F(TOUT="OUI", CHAM_GD=__EPSI_ELGA, NOM_CMP=("EPZZ",), NOM_CMP_RESU=("X3",)),
            _F(TOUT="OUI", CHAM_GD=__EPSI_ELGA, NOM_CMP=("EPXY",), NOM_CMP_RESU=("X4",)),
            _F(TOUT="OUI", CHAM_GD=__EPSI_ELGA, NOM_CMP=("EPXZ",), NOM_CMP_RESU=("X5",)),
            _F(TOUT="OUI", CHAM_GD=__EPSI_ELGA, NOM_CMP=("EPYZ",), NOM_CMP_RESU=("X6",)),
            _F(TOUT="OUI", CHAM_GD=__SIGF, NOM_CMP=("SIXX",), NOM_CMP_RESU=("X7",)),
            _F(TOUT="OUI", CHAM_GD=__SIGF, NOM_CMP=("SIYY",), NOM_CMP_RESU=("X8",)),
            _F(TOUT="OUI", CHAM_GD=__SIGF, NOM_CMP=("SIZZ",), NOM_CMP_RESU=("X9",)),
            _F(TOUT="OUI", CHAM_GD=__SIGF, NOM_CMP=("SIXY",), NOM_CMP_RESU=("X10",)),
            _F(TOUT="OUI", CHAM_GD=__SIGF, NOM_CMP=("SIXZ",), NOM_CMP_RESU=("X11",)),
            _F(TOUT="OUI", CHAM_GD=__SIGF, NOM_CMP=("SIYZ",), NOM_CMP_RESU=("X12",)),
        ),
    )

    __FMULTW = FORMULE(
        NOM_PARA=("X1", "X2", "X3", "X4", "X5", "X6", "X7", "X8", "X9", "X10", "X11", "X12"),
        VALE="(X1*X7/2)+(X2*X8/2)+(X3*X9/2)" + "+(X4*X10)+(X5*X11)+(X6*X12)",
    )

    __CHFMUW = CREA_CHAMP(
        OPERATION="AFFE",
        TYPE_CHAM="ELGA_NEUT_F",
        MODELE=MODE,
        PROL_ZERO="OUI",
        AFFE=_F(TOUT="OUI", NOM_CMP="X13", VALE_F=__FMULTW),
    )

    __WELAS = CREA_CHAMP(
        OPERATION="EVAL", TYPE_CHAM="ELGA_NEUT_R", CHAM_F=__CHFMUW, CHAM_PARA=(__CHW,)
    )

    del __CHW, __FMULTW, __CHFMUW

    return __WELAS


# -----------------------------------------------------------------------------


def field_q_local(self, MAIL, nameGroupNo, nameCmp, value):
    """
    Q field at nodes
    """

    __QX = CREA_CHAMP(
        OPERATION="AFFE",
        TYPE_CHAM="NOEU_DEPL_R",
        MAILLAGE=MAIL,
        AFFE=(
            _F(TOUT="OUI", NOM_CMP=("DX", "DY", "DZ"), VALE=(0.0, 0.0, 0.0)),
            _F(GROUP_NO=nameGroupNo, NOM_CMP=nameCmp[0], VALE=value[0]),
        ),
    )

    __QY = CREA_CHAMP(
        OPERATION="AFFE",
        TYPE_CHAM="NOEU_DEPL_R",
        MAILLAGE=MAIL,
        AFFE=(
            _F(TOUT="OUI", NOM_CMP=("DX", "DY", "DZ"), VALE=(0.0, 0.0, 0.0)),
            _F(GROUP_NO=nameGroupNo, NOM_CMP=nameCmp[1], VALE=value[1]),
        ),
    )

    __QZ = CREA_CHAMP(
        OPERATION="AFFE",
        TYPE_CHAM="NOEU_DEPL_R",
        MAILLAGE=MAIL,
        AFFE=(
            _F(TOUT="OUI", NOM_CMP=("DX", "DY", "DZ"), VALE=(0.0, 0.0, 0.0)),
            _F(GROUP_NO=nameGroupNo, NOM_CMP=nameCmp[2], VALE=value[2]),
        ),
    )

    return (__QX, __QY, __QZ)


# -----------------------------------------------------------------------------


def field_q_global(self, MAIL, NPP, nameCmp, value):
    """
    Q field at nodes
    """

    __tmp = [{"NOM_CMP": ("DX", "DY", "DZ"), "TOUT": "OUI", "VALE": (0.0, 0.0, 0.0)}]

    for iNPP in range(NPP):
        dictTmp = {}
        dictTmp["GROUP_NO"] = "TMBOUGER" + str(iNPP + 1)
        dictTmp["NOM_CMP"] = nameCmp[0]
        dictTmp["VALE"] = value[iNPP + 1][0]
        __tmp.append(dictTmp)

    __QX = CREA_CHAMP(OPERATION="AFFE", TYPE_CHAM="NOEU_DEPL_R", MAILLAGE=MAIL, AFFE=__tmp)

    __tmp = [{"NOM_CMP": ("DX", "DY", "DZ"), "TOUT": "OUI", "VALE": (0.0, 0.0, 0.0)}]

    for iNPP in range(NPP):
        dictTmp = {}
        dictTmp["GROUP_NO"] = "TMBOUGER" + str(iNPP + 1)
        dictTmp["NOM_CMP"] = nameCmp[1]
        dictTmp["VALE"] = value[iNPP + 1][1]
        __tmp.append(dictTmp)

    __QY = CREA_CHAMP(OPERATION="AFFE", TYPE_CHAM="NOEU_DEPL_R", MAILLAGE=MAIL, AFFE=__tmp)

    __tmp = [{"NOM_CMP": ("DX", "DY", "DZ"), "TOUT": "OUI", "VALE": (0.0, 0.0, 0.0)}]

    for iNPP in range(NPP):
        dictTmp = {}
        dictTmp["GROUP_NO"] = "TMBOUGER" + str(iNPP + 1)
        dictTmp["NOM_CMP"] = nameCmp[2]
        dictTmp["VALE"] = value[iNPP + 1][2]
        __tmp.append(dictTmp)

    __QZ = CREA_CHAMP(OPERATION="AFFE", TYPE_CHAM="NOEU_DEPL_R", MAILLAGE=MAIL, AFFE=__tmp)

    return (__QX, __QY, __QZ)


# -----------------------------------------------------------------------------


def grad_u(self, MAIL, MODE, MATE, namePara, DEPL, lInst):
    """
    Gradient of displacement
    """

    __U1 = FORMULE(NOM_PARA=("DX", "DY", "DZ"), VALE=namePara[0])
    __U2 = FORMULE(NOM_PARA=("DX", "DY", "DZ"), VALE=namePara[1])
    __U3 = FORMULE(NOM_PARA=("DX", "DY", "DZ"), VALE=namePara[2])

    __CHU = CREA_CHAMP(
        OPERATION="AFFE",
        TYPE_CHAM="NOEU_NEUT_F",
        MAILLAGE=MAIL,
        AFFE=_F(TOUT="OUI", NOM_CMP=("X1", "X2", "X3"), VALE_F=(__U1, __U2, __U3)),
    )

    __DEPU = CREA_CHAMP(OPERATION="EVAL", TYPE_CHAM="NOEU_NEUT_R", CHAM_F=__CHU, CHAM_PARA=DEPL)

    __DEPU = CREA_CHAMP(
        OPERATION="ASSE",
        MODELE=MODE,
        TYPE_CHAM="NOEU_DEPL_R",
        ASSE=_F(
            CHAM_GD=__DEPU, TOUT="OUI", NOM_CMP=("X1", "X2", "X3"), NOM_CMP_RESU=("DX", "DY", "DZ")
        ),
    )

    __DEPU = CREA_RESU(
        OPERATION="AFFE",
        TYPE_RESU="EVOL_ELAS",
        AFFE=_F(NOM_CHAM="DEPL", CHAM_GD=__DEPU, INST=lInst),
    )

    __GRADEP = CALC_CHAMP(
        reuse=__DEPU, MODELE=MODE, CHAM_MATER=MATE, RESULTAT=__DEPU, DEFORMATION=("EPSI_ELGA")
    )

    __GRADEP = CREA_CHAMP(
        TYPE_CHAM="ELGA_EPSI_R",
        OPERATION="EXTR",
        RESULTAT=__GRADEP,
        NOM_CHAM="EPSI_ELGA",
        INST=lInst,
    )

    del __U1, __U2, __U3, __CHU, __DEPU

    return __GRADEP


# -----------------------------------------------------------------------------


def grad_q(self, MAIL, MODE, MATE, nameGroupNo, nameCmp, value, lInst):
    """
    Gradient of Q
    """

    __DEPQ = CREA_CHAMP(
        OPERATION="AFFE",
        TYPE_CHAM="NOEU_DEPL_R",
        MAILLAGE=MAIL,
        AFFE=(
            _F(TOUT="OUI", NOM_CMP=("DX", "DY", "DZ"), VALE=(0.0, 0.0, 0.0)),
            _F(GROUP_NO=(nameGroupNo), NOM_CMP=nameCmp, VALE=value),
        ),
    )

    __RDEPQ = CREA_RESU(
        OPERATION="AFFE",
        TYPE_RESU="EVOL_ELAS",
        AFFE=_F(NOM_CHAM="DEPL", CHAM_GD=__DEPQ, INST=lInst),
    )

    __RDEPQ = CALC_CHAMP(
        reuse=__RDEPQ, MODELE=MODE, CHAM_MATER=MATE, RESULTAT=__RDEPQ, DEFORMATION=("EPSI_ELGA")
    )

    __GRAQ = CREA_CHAMP(
        TYPE_CHAM="ELGA_EPSI_R",
        OPERATION="EXTR",
        RESULTAT=__RDEPQ,
        NOM_CHAM="EPSI_ELGA",
        INST=lInst,
    )

    del __DEPQ, __RDEPQ

    return __GRAQ


# -----------------------------------------------------------------------------


def grad_q_glob(self, MAIL, MODE, MATE, NPP, nameCmp, value, index, lInst):
    """
    Gradient of Q
    """

    __tmp = [{"NOM_CMP": ("DX", "DY", "DZ"), "TOUT": "OUI", "VALE": (0.0, 0.0, 0.0)}]

    for iNP in range(NPP):
        dictTmp = {}
        dictTmp["NOM_CMP"] = nameCmp
        dictTmp["GROUP_NO"] = "TMBOUGER" + str(iNP + 1)
        dictTmp["VALE"] = value[iNP + 1][index]
        __tmp.append(dictTmp)

    __DEPQ = CREA_CHAMP(OPERATION="AFFE", TYPE_CHAM="NOEU_DEPL_R", MAILLAGE=MAIL, AFFE=__tmp)

    __RDEPQ = CREA_RESU(
        OPERATION="AFFE",
        TYPE_RESU="EVOL_ELAS",
        AFFE=_F(NOM_CHAM="DEPL", CHAM_GD=__DEPQ, INST=lInst),
    )

    __RDEPQ = CALC_CHAMP(
        reuse=__RDEPQ, MODELE=MODE, CHAM_MATER=MATE, RESULTAT=__RDEPQ, DEFORMATION=("EPSI_ELGA")
    )

    __GRAQ = CREA_CHAMP(
        TYPE_CHAM="ELGA_EPSI_R",
        OPERATION="EXTR",
        RESULTAT=__RDEPQ,
        INST=lInst,
        NOM_CHAM="EPSI_ELGA",
    )

    del __DEPQ, __RDEPQ

    return __GRAQ


# -----------------------------------------------------------------------------


def grad_noeu(self, MAIL, MODE, MATE, __FIELD, inst):
    """
    Gradient of NOEU field
    """

    __FIELD_NOEU_X1 = FORMULE(NOM_PARA=("DX"), VALE="DX")
    __FIELD_NOEU_X2 = FORMULE(NOM_PARA=("DX"), VALE="DX*0.")
    __FIELD_NOEU_X3 = FORMULE(NOM_PARA=("DX"), VALE="DX*0.")

    __FIELD_CALX = CREA_CHAMP(
        OPERATION="AFFE",
        TYPE_CHAM="NOEU_NEUT_F",
        MAILLAGE=MAIL,
        AFFE=_F(
            TOUT="OUI",
            NOM_CMP=("X1", "X2", "X3"),
            VALE_F=(__FIELD_NOEU_X1, __FIELD_NOEU_X2, __FIELD_NOEU_X3),
        ),
    )

    __FIELD_CAL = CREA_CHAMP(
        OPERATION="EVAL", TYPE_CHAM="NOEU_NEUT_R", CHAM_F=__FIELD_CALX, CHAM_PARA=__FIELD
    )

    __FIELD_CAL = CREA_CHAMP(
        OPERATION="ASSE",
        MODELE=MODE,
        TYPE_CHAM="NOEU_DEPL_R",
        ASSE=_F(
            CHAM_GD=__FIELD_CAL,
            TOUT="OUI",
            NOM_CMP=("X1", "X2", "X3"),
            NOM_CMP_RESU=("DX", "DY", "DZ"),
        ),
    )

    __RFIELD = CREA_RESU(
        OPERATION="AFFE",
        TYPE_RESU="EVOL_ELAS",
        AFFE=_F(NOM_CHAM="DEPL", CHAM_GD=__FIELD_CAL, INST=inst),
    )

    __GRAD_FIELD = CALC_CHAMP(
        reuse=__RFIELD, MODELE=MODE, CHAM_MATER=MATE, RESULTAT=__RFIELD, DEFORMATION=("EPSI_ELGA")
    )

    __GRAD_FIELD = CREA_CHAMP(
        TYPE_CHAM="ELGA_EPSI_R",
        OPERATION="EXTR",
        RESULTAT=__GRAD_FIELD,
        INST=inst,
        NOM_CHAM="EPSI_ELGA",
    )

    del __FIELD_CAL, __FIELD_NOEU_X1, __FIELD_NOEU_X2, __FIELD_NOEU_X3, __FIELD_CALX, __RFIELD

    return __GRAD_FIELD


# -----------------------------------------------------------------------------


def grad_elno(self, MAIL, MODE, MATE, listElemTMAIL, __EPSI_ELGA, __FIELD_CAL, inst):
    """
    Gradient of ELNO field
    """

    lValues = [iVal for iVal in __FIELD_CAL[0]]
    lMailles = __FIELD_CAL[1][0]

    lMaillesReduce = []
    for iMail in lMailles:
        if iMail not in lMaillesReduce:
            lMaillesReduce.append(iMail)

    dicElemValue = {}
    for iMailR in lMaillesReduce:
        value = []
        for jMail in range(len(lMailles)):
            if lMailles[jMail] == iMailR:
                value.append(lValues[jMail])
        dicElemValue["M" + str(iMailR)] = value

    connect = MAIL.getConnectivity()

    dicAllElems = {}
    for i, cell in enumerate(connect):
        dicAllElems[str(i + 1)] = [str(j + 1) for j in cell]

    dicElemNode = {}
    for iElem in dicAllElems.keys():
        if iElem in listElemTMAIL:
            dicElemNode[iElem] = dicAllElems[iElem]

    dicGrad = {}

    for iElemTMAIL in listElemTMAIL:
        texte = (
            "#"
            + "-" * 55
            + "\n"
            + "# MAILLE: %s" % iElemTMAIL
            + "         ("
            + str(listElemTMAIL.index(iElemTMAIL) + 1)
            + "/"
            + str(len(listElemTMAIL))
            + ")"
        )

        aster.affiche("MESSAGE", texte)

        __tmpLocal = [{"NOM_CMP": ("DX", "DY", "DZ"), "TOUT": "OUI", "VALE": (0.0, 0.0, 0.0)}]

        for iDicElem in range(len(dicElemNode[iElemTMAIL])):
            dictTmp = {}
            dictTmp["NOM_CMP"] = "DX"
            dictTmp["NOEUD"] = dicElemNode[iElemTMAIL][iDicElem]
            dictTmp["VALE"] = dicElemValue[iElemTMAIL][iDicElem]
            __tmpLocal.append(dictTmp)

        __DEPE = CREA_CHAMP(
            OPERATION="AFFE", TYPE_CHAM="NOEU_DEPL_R", MAILLAGE=MAIL, AFFE=__tmpLocal
        )

        __RDEPE = CREA_RESU(
            OPERATION="AFFE",
            TYPE_RESU="EVOL_ELAS",
            AFFE=_F(NOM_CHAM="DEPL", CHAM_GD=__DEPE, INST=inst),
        )

        __RDEPE = CALC_CHAMP(
            reuse=__RDEPE, MODELE=MODE, CHAM_MATER=MATE, RESULTAT=__RDEPE, DEFORMATION=("EPSI_ELGA")
        )

        __GRAE = CREA_CHAMP(
            TYPE_CHAM="ELGA_EPSI_R",
            OPERATION="EXTR",
            INST=inst,
            RESULTAT=__RDEPE,
            NOM_CHAM="EPSI_ELGA",
        )

        dicGrad[str(iElemTMAIL)] = __GRAE

    __tmpGlob = [{"CHAM_GD": (__EPSI_ELGA), "TOUT": "OUI", "CUMUL": ("OUI"), "COEF_R": (0.0)}]

    for ilElem in range(len(listElemTMAIL)):
        dictTmp = {}
        dictTmp["CHAM_GD"] = dicGrad[listElemTMAIL[ilElem]]
        dictTmp["MAILLE"] = listElemTMAIL[ilElem]
        dictTmp["CUMUL"] = "OUI"
        dictTmp["COEF_R"] = 1.0
        __tmpGlob.append(dictTmp)

    __GRAD_FIELD_CAL = CREA_CHAMP(
        TYPE_CHAM="ELGA_EPSI_R", OPERATION="ASSE", MODELE=MODE, ASSE=__tmpGlob
    )

    del __DEPE, __RDEPE, __GRAE

    return __GRAD_FIELD_CAL


# -----------------------------------------------------------------------------


def cal_j01(self, MODE, TMAIL, lInst, __WELAS, __GQX, __GQY, __GQZ):
    """
    Calculation term J01 = W * DIV Q
    """

    __CHJ01 = CREA_CHAMP(
        OPERATION="ASSE",
        TYPE_CHAM="ELGA_NEUT_R",
        MODELE=MODE,
        PROL_ZERO="OUI",
        ASSE=(
            _F(GROUP_MA=TMAIL, CHAM_GD=__WELAS, NOM_CMP=("X13",), NOM_CMP_RESU=("X1",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GQX, NOM_CMP=("EPXX",), NOM_CMP_RESU=("X2",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GQY, NOM_CMP=("EPYY",), NOM_CMP_RESU=("X3",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GQZ, NOM_CMP=("EPZZ",), NOM_CMP_RESU=("X4",)),
        ),
    )

    __FMULTJ01 = FORMULE(NOM_PARA=("X1", "X2", "X3", "X4"), VALE="X1*(X2+X3+X4)")

    __CHFMUJ01 = CREA_CHAMP(
        OPERATION="AFFE",
        TYPE_CHAM="ELGA_NEUT_F",
        MODELE=MODE,
        PROL_ZERO="OUI",
        AFFE=_F(GROUP_MA=TMAIL, NOM_CMP="X5", VALE_F=__FMULTJ01),
    )

    __CHJ01INT = CREA_CHAMP(
        OPERATION="EVAL", TYPE_CHAM="ELGA_NEUT_R", CHAM_F=__CHFMUJ01, CHAM_PARA=(__CHJ01,)
    )

    __RESUJ01 = CREA_RESU(
        OPERATION="AFFE",
        TYPE_RESU="EVOL_ELAS",
        AFFE=_F(NOM_CHAM="VARI_ELGA", MODELE=MODE, INST=lInst, CHAM_GD=__CHJ01INT),
    )

    __J01 = POST_ELEM(
        RESULTAT=__RESUJ01,
        MODELE=MODE,
        INST=lInst,
        INTEGRALE=_F(NOM_CHAM="VARI_ELGA", GROUP_MA=TMAIL, NOM_CMP="X5", TYPE_MAILLE="3D"),
    )

    del __CHJ01, __FMULTJ01, __CHFMUJ01, __CHJ01INT, __RESUJ01

    __J01_J = __J01.EXTR_TABLE().values()["INTE_X5"]

    volume = __J01.EXTR_TABLE().values()["VOL"]

    return (__J01_J, volume)


# -----------------------------------------------------------------------------


def cal_j02(self, MODE, TMAIL, lInst, __SIGF, __GDEPX, __GDEPY, __GDEPZ, __GQX, __GQY, __GQZ):
    """
    Calculation term J02 = SIGF * GRAD U * GRAD Q
    """

    __CHGRAUQ = CREA_CHAMP(
        OPERATION="ASSE",
        TYPE_CHAM="ELGA_NEUT_R",
        MODELE=MODE,
        PROL_ZERO="OUI",
        ASSE=(
            _F(GROUP_MA=TMAIL, CHAM_GD=__GDEPX, NOM_CMP=("EPXX",), NOM_CMP_RESU=("X1",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GDEPX, NOM_CMP=("EPXY",), NOM_CMP_RESU=("X2",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GDEPX, NOM_CMP=("EPXZ",), NOM_CMP_RESU=("X3",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GDEPY, NOM_CMP=("EPXY",), NOM_CMP_RESU=("X4",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GDEPY, NOM_CMP=("EPYY",), NOM_CMP_RESU=("X5",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GDEPY, NOM_CMP=("EPYZ",), NOM_CMP_RESU=("X6",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GDEPZ, NOM_CMP=("EPXZ",), NOM_CMP_RESU=("X7",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GDEPZ, NOM_CMP=("EPYZ",), NOM_CMP_RESU=("X8",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GDEPZ, NOM_CMP=("EPZZ",), NOM_CMP_RESU=("X9",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GQX, NOM_CMP=("EPXX",), NOM_CMP_RESU=("X10",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GQX, NOM_CMP=("EPXY",), NOM_CMP_RESU=("X11",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GQX, NOM_CMP=("EPXZ",), NOM_CMP_RESU=("X12",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GQY, NOM_CMP=("EPXY",), NOM_CMP_RESU=("X13",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GQY, NOM_CMP=("EPYY",), NOM_CMP_RESU=("X14",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GQY, NOM_CMP=("EPYZ",), NOM_CMP_RESU=("X15",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GQZ, NOM_CMP=("EPXZ",), NOM_CMP_RESU=("X16",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GQZ, NOM_CMP=("EPYZ",), NOM_CMP_RESU=("X17",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GQZ, NOM_CMP=("EPZZ",), NOM_CMP_RESU=("X18",)),
        ),
    )

    __FMULTGRAUQ_X19 = FORMULE(
        NOM_PARA=("X1", "X2", "X3", "X10", "X13", "X16"),
        VALE="X1*X10+(X2*2)*(X13*2)+(X3*2)*(X16*2)",
    )
    __FMULTGRAUQ_X20 = FORMULE(
        NOM_PARA=("X1", "X2", "X3", "X11", "X14", "X17"),
        VALE="X1*(X11*2)+(X2*2)*X14+(X3*2)*(X17*2)",
    )
    __FMULTGRAUQ_X21 = FORMULE(
        NOM_PARA=("X1", "X2", "X3", "X12", "X15", "X18"),
        VALE="X1*(X12*2)+(X2*2)*(X15*2)+(X3*2)*X18",
    )
    __FMULTGRAUQ_X22 = FORMULE(
        NOM_PARA=("X4", "X5", "X6", "X10", "X13", "X16"),
        VALE="(X4*2)*X10+X5*(X13*2)+(X6*2)*(X16*2)",
    )
    __FMULTGRAUQ_X23 = FORMULE(
        NOM_PARA=("X4", "X5", "X6", "X11", "X14", "X17"),
        VALE="(X4*2)*(X11*2)+X5*X14+(X6*2)*(X17*2)",
    )
    __FMULTGRAUQ_X24 = FORMULE(
        NOM_PARA=("X4", "X5", "X6", "X12", "X15", "X18"),
        VALE="(X4*2)*(X12*2)+X5*(X15*2)+(X6*2)*X18",
    )
    __FMULTGRAUQ_X25 = FORMULE(
        NOM_PARA=("X7", "X8", "X9", "X10", "X13", "X16"),
        VALE="(X7*2)*X10+(X8*2)*(X13*2)+X9*(X16*2)",
    )
    __FMULTGRAUQ_X26 = FORMULE(
        NOM_PARA=("X7", "X8", "X9", "X11", "X14", "X17"),
        VALE="(X7*2)*(X11*2)+(X8*2)*X14+X9*(X17*2)",
    )
    __FMULTGRAUQ_X27 = FORMULE(
        NOM_PARA=("X7", "X8", "X9", "X12", "X15", "X18"),
        VALE="(X7*2)*(X12*2)+(X8*2)*(X15*2)+X9*X18",
    )

    __CHFMUGRAUQ = CREA_CHAMP(
        OPERATION="AFFE",
        TYPE_CHAM="ELGA_NEUT_F",
        MODELE=MODE,
        PROL_ZERO="OUI",
        AFFE=_F(
            GROUP_MA=TMAIL,
            NOM_CMP=("X19", "X20", "X21", "X22", "X23", "X24", "X25", "X26", "X27"),
            VALE_F=(
                __FMULTGRAUQ_X19,
                __FMULTGRAUQ_X20,
                __FMULTGRAUQ_X21,
                __FMULTGRAUQ_X22,
                __FMULTGRAUQ_X23,
                __FMULTGRAUQ_X24,
                __FMULTGRAUQ_X25,
                __FMULTGRAUQ_X26,
                __FMULTGRAUQ_X27,
            ),
        ),
    )

    __CHGRAUMQ = CREA_CHAMP(
        OPERATION="EVAL", TYPE_CHAM="ELGA_NEUT_R", CHAM_F=__CHFMUGRAUQ, CHAM_PARA=(__CHGRAUQ,)
    )

    del (
        __CHGRAUQ,
        __FMULTGRAUQ_X19,
        __FMULTGRAUQ_X20,
        __FMULTGRAUQ_X21,
        __FMULTGRAUQ_X22,
        __FMULTGRAUQ_X23,
        __FMULTGRAUQ_X24,
        __FMULTGRAUQ_X25,
        __FMULTGRAUQ_X26,
        __FMULTGRAUQ_X27,
        __CHFMUGRAUQ,
    )

    __CHJ02 = CREA_CHAMP(
        OPERATION="ASSE",
        TYPE_CHAM="ELGA_NEUT_R",
        MODELE=MODE,
        PROL_ZERO="OUI",
        ASSE=(
            _F(GROUP_MA=TMAIL, CHAM_GD=__CHGRAUMQ, NOM_CMP=("X19",), NOM_CMP_RESU=("X19",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__CHGRAUMQ, NOM_CMP=("X20",), NOM_CMP_RESU=("X20",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__CHGRAUMQ, NOM_CMP=("X21",), NOM_CMP_RESU=("X21",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__CHGRAUMQ, NOM_CMP=("X22",), NOM_CMP_RESU=("X22",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__CHGRAUMQ, NOM_CMP=("X23",), NOM_CMP_RESU=("X23",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__CHGRAUMQ, NOM_CMP=("X24",), NOM_CMP_RESU=("X24",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__CHGRAUMQ, NOM_CMP=("X25",), NOM_CMP_RESU=("X25",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__CHGRAUMQ, NOM_CMP=("X26",), NOM_CMP_RESU=("X26",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__CHGRAUMQ, NOM_CMP=("X27",), NOM_CMP_RESU=("X27",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__SIGF, NOM_CMP=("SIXX",), NOM_CMP_RESU=("X1",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__SIGF, NOM_CMP=("SIXY",), NOM_CMP_RESU=("X2",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__SIGF, NOM_CMP=("SIXZ",), NOM_CMP_RESU=("X3",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__SIGF, NOM_CMP=("SIYY",), NOM_CMP_RESU=("X4",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__SIGF, NOM_CMP=("SIYZ",), NOM_CMP_RESU=("X5",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__SIGF, NOM_CMP=("SIZZ",), NOM_CMP_RESU=("X6",)),
        ),
    )

    __FMULTJ02 = FORMULE(
        NOM_PARA=(
            "X19",
            "X20",
            "X21",
            "X22",
            "X23",
            "X24",
            "X25",
            "X26",
            "X27",
            "X1",
            "X2",
            "X3",
            "X4",
            "X5",
            "X6",
        ),
        VALE="(X19*X1)+(X20*X2)+(X21*X3)+(X22*X2)+"
        + "(X23*X4)+(X24*X5)+(X25*X3)+(X26*X5)+(X27*X6)",
    )

    __CHFMUJ02 = CREA_CHAMP(
        OPERATION="AFFE",
        TYPE_CHAM="ELGA_NEUT_F",
        MODELE=MODE,
        PROL_ZERO="OUI",
        AFFE=_F(GROUP_MA=TMAIL, NOM_CMP="X7", VALE_F=__FMULTJ02),
    )

    __CHJ02INT = CREA_CHAMP(
        OPERATION="EVAL", TYPE_CHAM="ELGA_NEUT_R", CHAM_F=__CHFMUJ02, CHAM_PARA=(__CHJ02,)
    )

    __RESUJ02 = CREA_RESU(
        OPERATION="AFFE",
        TYPE_RESU="EVOL_ELAS",
        AFFE=_F(NOM_CHAM="VARI_ELGA", MODELE=MODE, INST=lInst, CHAM_GD=__CHJ02INT),
    )

    __J02 = POST_ELEM(
        RESULTAT=__RESUJ02,
        MODELE=MODE,
        INST=lInst,
        INTEGRALE=_F(NOM_CHAM="VARI_ELGA", GROUP_MA=TMAIL, NOM_CMP="X7", TYPE_MAILLE="3D"),
    )

    del __CHGRAUMQ, __CHJ02, __FMULTJ02, __CHFMUJ02, __CHJ02INT, __RESUJ02

    __J02_J = __J02.EXTR_TABLE().values()["INTE_X7"]

    return __J02_J


# -----------------------------------------------------------------------------


def cal_j04(
    self,
    MODE,
    TMAIL,
    lInst,
    SIG_CMP,
    EPS_CMP,
    __SIGF,
    dicGradEps,
    __QX_GAUSS,
    __QY_GAUSS,
    __QZ_GAUSS,
):
    """
    Calculation term J04 = SIGF * GRAD EPSI * Q
    """

    __J04_J = [0.0]

    for iSIG, iEPS in zip(SIG_CMP, EPS_CMP):
        __CHJ04 = CREA_CHAMP(
            OPERATION="ASSE",
            TYPE_CHAM="ELGA_NEUT_R",
            MODELE=MODE,
            PROL_ZERO="OUI",
            ASSE=(
                _F(GROUP_MA=TMAIL, CHAM_GD=__SIGF, NOM_CMP=(iSIG,), NOM_CMP_RESU=("X1",)),
                _F(
                    GROUP_MA=TMAIL,
                    CHAM_GD=dicGradEps[iEPS],
                    NOM_CMP=("EPXX",),
                    NOM_CMP_RESU=("X2",),
                ),
                _F(
                    GROUP_MA=TMAIL,
                    CHAM_GD=dicGradEps[iEPS],
                    NOM_CMP=("EPXY",),
                    NOM_CMP_RESU=("X3",),
                ),
                _F(
                    GROUP_MA=TMAIL,
                    CHAM_GD=dicGradEps[iEPS],
                    NOM_CMP=("EPXZ",),
                    NOM_CMP_RESU=("X4",),
                ),
                _F(GROUP_MA=TMAIL, CHAM_GD=__QX_GAUSS, NOM_CMP=("EPXX",), NOM_CMP_RESU=("X5",)),
                _F(GROUP_MA=TMAIL, CHAM_GD=__QY_GAUSS, NOM_CMP=("EPYY",), NOM_CMP_RESU=("X6",)),
                _F(GROUP_MA=TMAIL, CHAM_GD=__QZ_GAUSS, NOM_CMP=("EPZZ",), NOM_CMP_RESU=("X7",)),
            ),
        )

        __FMULTJ04 = FORMULE(
            NOM_PARA=("X1", "X2", "X3", "X4", "X5", "X6", "X7"),
            VALE="(X1*X2*X5)+(X1*(X3*2)*X6)+(X1*(X4*2)*X7)",
        )

        __CHFMUJ04 = CREA_CHAMP(
            OPERATION="AFFE",
            TYPE_CHAM="ELGA_NEUT_F",
            MODELE=MODE,
            PROL_ZERO="OUI",
            AFFE=_F(GROUP_MA=TMAIL, NOM_CMP="X8", VALE_F=__FMULTJ04),
        )

        __CHJ04INT = CREA_CHAMP(
            OPERATION="EVAL", TYPE_CHAM="ELGA_NEUT_R", CHAM_F=__CHFMUJ04, CHAM_PARA=(__CHJ04,)
        )

        __RESUJ04 = CREA_RESU(
            OPERATION="AFFE",
            TYPE_RESU="EVOL_ELAS",
            AFFE=_F(NOM_CHAM="VARI_ELGA", MODELE=MODE, INST=lInst, CHAM_GD=__CHJ04INT),
        )

        __J04 = POST_ELEM(
            RESULTAT=__RESUJ04,
            MODELE=MODE,
            INST=lInst,
            INTEGRALE=_F(NOM_CHAM="VARI_ELGA", GROUP_MA=TMAIL, NOM_CMP="X8", TYPE_MAILLE="3D"),
        )

        del __CHJ04, __FMULTJ04, __CHFMUJ04, __CHJ04INT, __RESUJ04

        __IJ04_J = __J04.EXTR_TABLE().values()["INTE_X8"]

        if iEPS in ["EPXY", "EPXZ", "EPYZ"]:
            __IJ04_J = [iJ04 * 2.0 for iJ04 in __IJ04_J]

        __J04_J = np.array(__J04_J) + np.array(__IJ04_J)

    return __J04_J


# -----------------------------------------------------------------------------


def cal_j05(self, MODE, TMAIL, lInst, __GRAD_WELAS, __QX_GAUSS, __QY_GAUSS, __QZ_GAUSS):
    """
    Calculation term J05 = GRAD W * Q
    """

    __CHJ05 = CREA_CHAMP(
        OPERATION="ASSE",
        TYPE_CHAM="ELGA_NEUT_R",
        MODELE=MODE,
        PROL_ZERO="OUI",
        ASSE=(
            _F(GROUP_MA=TMAIL, CHAM_GD=__GRAD_WELAS, NOM_CMP=("EPXX",), NOM_CMP_RESU=("X1",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GRAD_WELAS, NOM_CMP=("EPXY",), NOM_CMP_RESU=("X2",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__GRAD_WELAS, NOM_CMP=("EPXZ",), NOM_CMP_RESU=("X3",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__QX_GAUSS, NOM_CMP=("EPXX",), NOM_CMP_RESU=("X4",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__QY_GAUSS, NOM_CMP=("EPYY",), NOM_CMP_RESU=("X5",)),
            _F(GROUP_MA=TMAIL, CHAM_GD=__QZ_GAUSS, NOM_CMP=("EPZZ",), NOM_CMP_RESU=("X6",)),
        ),
    )

    __FMULTJ05 = FORMULE(
        NOM_PARA=("X1", "X2", "X3", "X4", "X5", "X6"), VALE="(X1*X4)+((X2*2)*X5)+((X3*2)*X6)"
    )

    __CHFMUJ05 = CREA_CHAMP(
        OPERATION="AFFE",
        TYPE_CHAM="ELGA_NEUT_F",
        MODELE=MODE,
        PROL_ZERO="OUI",
        AFFE=_F(GROUP_MA=TMAIL, NOM_CMP="X7", VALE_F=__FMULTJ05),
    )

    __CHJ05INT = CREA_CHAMP(
        OPERATION="EVAL", TYPE_CHAM="ELGA_NEUT_R", CHAM_F=__CHFMUJ05, CHAM_PARA=(__CHJ05,)
    )

    __RESUJ05 = CREA_RESU(
        OPERATION="AFFE",
        TYPE_RESU="EVOL_ELAS",
        AFFE=_F(NOM_CHAM="VARI_ELGA", MODELE=MODE, INST=lInst, CHAM_GD=__CHJ05INT),
    )

    __J05 = POST_ELEM(
        RESULTAT=__RESUJ05,
        MODELE=MODE,
        INST=lInst,
        INTEGRALE=_F(NOM_CHAM="VARI_ELGA", GROUP_MA=TMAIL, NOM_CMP="X7", TYPE_MAILLE="3D"),
    )

    del __CHJ05, __FMULTJ05, __CHFMUJ05, __CHJ05INT, __RESUJ05

    __J05_J = __J05.EXTR_TABLE().values()["INTE_X7"]

    return __J05_J


# -----------------------------------------------------------------------------


def list_inst_calc(self, dico, NUME_ORDRE, INST, PRECISION):
    """
    Determining the calculated instants
    """

    lInst = list(dico["INST"])
    lOrd = list(dico["NUME_ORDRE"])

    if (NUME_ORDRE is not None) and (INST is None):
        lInstc_comp = list(dico["INST"])
        lInst = [lInstc_comp[dico["NUME_ORDRE"].index(iord)] for iord in NUME_ORDRE]
        lOrd = dico["NUME_ORDRE"]

        if lInst == []:
            UTMESS("F", "RUPTURE4_5")

    elif (NUME_ORDRE is None) and (INST is not None):
        lInst = []
        lOrd = []
        for ii, iinst in enumerate(dico["INST"]):
            for jinst in INST:
                if abs(iinst - jinst) <= PRECISION:
                    lInst.append(iinst)
                    lOrd.append(dico["NUME_ORDRE"][ii])

        if lInst == []:
            UTMESS("F", "RUPTURE4_6")

    return (lOrd, lInst)


# -----------------------------------------------------------------------------


def list_node_calc(self, LIST_NODE, NB_POINT_FOND, TPFISS, NP):
    """
    Determining the calculated nodes of crack front
    """

    if (LIST_NODE is not None) and (NB_POINT_FOND is not None):
        UTMESS("F", "RUPTURE4_7")

    elif (LIST_NODE is not None) and (NB_POINT_FOND is None):
        listNP = []
        for iNode in LIST_NODE:
            for jKeyNode in range(NP):
                if iNode == TPFISS[jKeyNode + 1]:
                    listNP.append(jKeyNode)
            if iNode == "GLOBAL":
                listNP.append(NP)

    elif (LIST_NODE is None) and (NB_POINT_FOND is not None):
        listNP = []
        if (NB_POINT_FOND < 1) or (NB_POINT_FOND > NP):
            UTMESS("F", "RUPTURE4_8")
        else:
            if NB_POINT_FOND == 1:
                listNP.append(range(NP)[0])

            if NB_POINT_FOND == 2:
                listNP.append(range(NP)[0])
                listNP.append(range(NP)[-1])

            if NB_POINT_FOND > 2:
                iSelect = float(NP - 2) / float(NB_POINT_FOND - 1)
                listNP.append(range(NP)[0])
                for i in range(NB_POINT_FOND - 2):
                    listNP.append(range(NP)[1 + int(iSelect * (i + 1))])
                listNP.append(range(NP)[-1])
    else:
        listNP = range(NP)

    return listNP


# -----------------------------------------------------------------------------


def normalize(v):
    norm = np.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    return v / norm


# -----------------------------------------------------------------------------


def get_result2D(
    self, J, __J01, linst, liord, nom_modelisation, NB_COUCHES, e, nu, is_symmetric, TITRE
):
    # CREA_TABLE = self.get_cmd('CREA_TABLE')

    if is_symmetric:
        if nom_modelisation == "D_PLAN":
            K = [np.sqrt(iJ * e / (1.0 - nu**2)) for iJ in J]

        if nom_modelisation == "C_PLAN":
            K = [np.sqrt(iJ * e) for iJ in J]

    RS_modelisation = []
    RS_modelisation.append(nom_modelisation)
    RS_modelisation = RS_modelisation * len(liord)

    RS_volume = __J01.EXTR_TABLE().values()["VOL"]
    RS_volume = RS_volume * len(liord)

    RS_contour = []
    RS_contour.append(NB_COUCHES)
    RS_contour = RS_contour * len(liord)

    tabfact = []
    tabfact.append(_F(PARA="INST", LISTE_R=(linst)))
    tabfact.append(_F(PARA="NUME_ORDRE", LISTE_I=(liord)))
    tabfact.append(_F(PARA="MODE", LISTE_K=(RS_modelisation)))
    tabfact.append(_F(PARA="VOLUME", LISTE_R=(RS_volume)))
    tabfact.append(_F(PARA="NB_COUCHES", LISTE_I=(RS_contour)))

    if is_symmetric and (nom_modelisation != "AXIS"):
        tabfact.append(_F(PARA="K", LISTE_R=(K)))

    tabfact.append(_F(PARA="J", LISTE_R=(J)))

    tab_result = CREA_TABLE(LISTE=tabfact, TITRE=TITRE)

    return tab_result


# -----------------------------------------------------------------------------


def get_result(
    self,
    __J,
    volume,
    NB_COUCHES,
    TITRE,
    TPFISS,
    FOND_FISS,
    iNP,
    NP,
    listNP,
    inst,
    iord,
    tab_result,
    nume,
):
    """
    Print results
    """

    if TITRE is not None:
        titre = TITRE
    else:
        titre = get_titre_concept()

    TPFISS[NP + 1] = "GLOBAL"

    mcfact = []
    mcfact.append(_F(PARA="FOND_FISS", LISTE_K=[FOND_FISS.getName()]))
    mcfact.append(_F(PARA="NUME_FOND", LISTE_I=[1]))
    mcfact.append(_F(PARA="NOEUD_FOND", LISTE_K=[TPFISS[iNP + 1]]))
    mcfact.append(_F(PARA="NUM_PT", LISTE_I=[iNP + 1]))
    mcfact.append(_F(PARA="NB_COUCHES", LISTE_I=(NB_COUCHES)))
    mcfact.append(_F(PARA="VOLUME", LISTE_R=(volume)))
    mcfact.append(_F(PARA="J", LISTE_R=(__J)))
    mcfact = [_F(PARA="NUME_ORDRE", LISTE_I=nume)] + mcfact
    mcfact = [_F(PARA="INST", LISTE_R=[inst])] + mcfact

    params = ()
    params = params + ("FOND_FISS",)
    params = params + ("NUME_FOND",)
    params = params + ("INST",)
    params = params + ("NUME_ORDRE",)
    params = params + ("NOEUD_FOND",)
    params = params + ("NUM_PT",)
    params = params + ("VOLUME",)
    params = params + ("NB_COUCHES",)
    params = params + ("J",)

    if iord == 0 and iNP == listNP[0]:
        tab_result = CREA_TABLE(LISTE=mcfact, TITRE=titre)
        tab_result = CALC_TABLE(
            TABLE=tab_result,
            reuse=tab_result,
            ACTION=(_F(OPERATION="EXTR", NOM_PARA=tuple(params))),
        )
    else:
        __tabi = CREA_TABLE(LISTE=mcfact, TITRE=titre)
        __tabi = CALC_TABLE(
            TABLE=__tabi, reuse=__tabi, ACTION=(_F(OPERATION="EXTR", NOM_PARA=tuple(params)))
        )

        tab_result = CALC_TABLE(
            reuse=tab_result,
            TABLE=tab_result,
            ACTION=_F(TABLE=__tabi, OPERATION="COMB", NOM_PARA=["J", "INST", "NOEUD_FOND"]),
        )

    return tab_result


# -----------------------------------------------------------------------------


def post_jmod_ops(
    self,
    RESULTAT,
    FOND_FISS=None,
    NB_COUCHES=None,
    INST=None,
    NUME_ORDRE=None,
    GROUP_NO=None,
    NB_POINT_FOND=None,
    OPTION=None,
    ETAT_INIT=None,
    TITRE=None,
    **args,
):
    """
    Macro POST_J - Calculate J-integral
    """

    #   --------------------------------------------------------------------------
    #   IGNORE ALARMS
    #
    MasquerAlarme("CALCCHAMP_1")
    MasquerAlarme("CATAMESS_41")
    MasquerAlarme("MAILLAGE1_1")
    MasquerAlarme("MODELISA4_8")
    MasquerAlarme("MODELISA4_9")
    MasquerAlarme("MODELISA8_13")
    MasquerAlarme("MODELISA8_14")
    MasquerAlarme("MODELISA8_15")
    MasquerAlarme("JEVEUX1_64")
    MasquerAlarme("PREPOST2_7")
    MasquerAlarme("MED_67")
    #   --------------------------------------------------------------------------
    #   NOT USER-OPTION
    #
    grad_elno_type_j03 = "NON"
    grad_elno_type_j04 = "NON"
    grad_elno_type_j05 = "NON"

    if OPTION != "JMOD":
        j_correction = "NON"
    else:
        j_correction = "OUI"

    if j_correction == "OUI" and NB_COUCHES <= 3:
        UTMESS("F", "RUPTURE4_9")

    # take into account the additional terms of modified J-intergral

    modified_J = True
    #   --------------------------------------------------------------------------
    #   EXTRACT TABLE OF RESULTS

    tab_result = []

    #   --------------------------------------------------------------------------
    #   GET PARAMETES AND RESULTS OF CALCULATION
    #
    #   Get material and modelisation names

    mater, MODELISATION = aster.postkutil(1, RESULTAT.getName(), FOND_FISS.getName())
    is_symmetric = FOND_FISS.isSymmetric()

    # Affectation de ndim selon le type de modelisation
    assert MODELISATION in ["3D", "AXIS", "D_PLAN", "C_PLAN"]
    if MODELISATION == "3D":
        ndim = 3
    else:
        ndim = 2

    #   Get mesh, model, material and results

    MAIL = RESULTAT.getModel().getMesh()
    MODE = RESULTAT.getModel()
    MATE = RESULTAT.getMaterialField()

    __RESU = RESULTAT
    __RESU = CALC_CHAMP(
        reuse=__RESU,
        RESULTAT=__RESU,
        CONTRAINTE=("SIGM_ELGA"),
        DEFORMATION=("EPSI_ELGA", "EPSI_ELNO", "EPSI_NOEU"),
        ENERGIE=("ETOT_ELGA", "ETOT_ELNO", "ETOT_NOEU"),
    )
    """
    Macro POST_JMOD - Calculate J-integral in 2D
    """

    if ndim == 2:
        # print("Macro POST_JMOD - Calculate J-integral in 2D")
        # get material
        # On recupere le materiau et le nom de la modelisation
        nom_fiss = ""
        if FOND_FISS is not None:
            nom_fiss = FOND_FISS.getName()
        assert nom_fiss != ""
        # si le MCS MATER n'est pas renseigne, on considere le materiau
        # present dans la sd_resultat. Si MATER est renseigne, on ecrase
        # le materiau et on emet une alarme.
        MATER = None
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
            _, MODELISATION = aster.postkutil(0, RESULTAT.getName(), nom_fiss)
            UTMESS("A", "RUPTURE0_1", valk=[MATER.getName()])

        e = MATER.getValueReal("ELAS", "E")
        nu = MATER.getValueReal("ELAS", "NU")

        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # DIRECTION OF VIRTUAL CRACK PROPAGATION
        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        # get crack tip

        Pfiss = FOND_FISS.getCrackFrontNodes()
        Nfiss = len(Pfiss)

        # get crack edges

        PropadirSup = FOND_FISS.getUpperNormNodes2()
        PropadirInf = FOND_FISS.getLowerNormNodes2()

        if (PropadirSup is None) and (PropadirInf is None):
            UTMESS("F", "RUPTURE4_10")

        if PropadirSup is not None:
            # determine top edge nodes

            del PropadirSup[2:]

            PropadirSup = [[Pfiss[i], PropadirSup[i * 2 : (i + 1) * 2]] for i in range(0, Nfiss)]
            PropadirSup = [(i[0], i[1][0:]) for i in PropadirSup]
            PropadirSup = dict(PropadirSup)

            LPfissSup = copy.copy(Pfiss)

            for ino in Pfiss:
                lst = [elem for elem in PropadirSup[ino] if elem != ""]
                LPfissSup += lst

            LPfissSup = list(set(LPfissSup))
            dicLPfissSup = RESULTAT.getAccessParameters()

            __ncoorfisSup = POST_RELEVE_T(
                ACTION=_F(
                    RESULTAT=RESULTAT,
                    OPERATION="EXTRACTION",
                    NOEUD=LPfissSup,
                    NOM_CHAM="DEPL",
                    NOM_CMP=("DX", "DY"),
                    INTITULE="TOP EDGE COORDINATES",
                )
            )

            tcoorfisSup = __ncoorfisSup.EXTR_TABLE().NUME_ORDRE == dicLPfissSup["NUME_ORDRE"][0]

            nbtfisSup = len(tcoorfisSup["NOEUD"].values()["NOEUD"])
            xsfisSup = np.array(tcoorfisSup["COOR_X"].values()["COOR_X"][:nbtfisSup])
            ysfisSup = np.array(tcoorfisSup["COOR_Y"].values()["COOR_Y"][:nbtfisSup])
            zsfisSup = np.zeros(nbtfisSup)

            nsfisSup = tcoorfisSup["NOEUD"].values()["NOEUD"][:nbtfisSup]

            l_coorfisSup = [
                [nsfisSup[i], xsfisSup[i], ysfisSup[i], zsfisSup[i]] for i in range(nbtfisSup)
            ]

            VECTEURSUP = []

            for i in range(2):
                if l_coorfisSup[i][0] == Pfiss[0]:
                    if i == 1:
                        for j in range(3):
                            coorVECTEURSUP = l_coorfisSup[i][j + 1] - l_coorfisSup[i - 1][j + 1]
                            VECTEURSUP.append(coorVECTEURSUP)
                    else:
                        for j in range(3):
                            coorVECTEURSUP = l_coorfisSup[i][j + 1] - l_coorfisSup[i + 1][j + 1]
                            VECTEURSUP.append(coorVECTEURSUP)

        if PropadirInf is not None:
            # determine bottom edge nodes

            del PropadirInf[2:]

            PropadirInf = [[Pfiss[i], PropadirInf[i * 2 : (i + 1) * 2]] for i in range(0, Nfiss)]
            PropadirInf = [(i[0], i[1][0:]) for i in PropadirInf]
            PropadirInf = dict(PropadirInf)

            LPfissInf = copy.copy(Pfiss)

            for ino in Pfiss:
                lst = [elem for elem in PropadirInf[ino] if elem != ""]
                LPfissInf += lst

            LPfissInf = list(set(LPfissInf))
            dicLPfissInf = RESULTAT.getAccessParameters()

            __ncoorfisInf = POST_RELEVE_T(
                ACTION=_F(
                    RESULTAT=RESULTAT,
                    OPERATION="EXTRACTION",
                    NOEUD=LPfissInf,
                    NOM_CHAM="DEPL",
                    NOM_CMP=("DX", "DY"),
                    INTITULE="BOTTOM EDGE COORDINATES",
                )
            )

            tcoorfisInf = __ncoorfisInf.EXTR_TABLE().NUME_ORDRE == dicLPfissInf["NUME_ORDRE"][0]

            nbtfisInf = len(tcoorfisInf["NOEUD"].values()["NOEUD"])
            xsfisInf = np.array(tcoorfisInf["COOR_X"].values()["COOR_X"][:nbtfisInf])
            ysfisInf = np.array(tcoorfisInf["COOR_Y"].values()["COOR_Y"][:nbtfisInf])
            zsfisInf = np.zeros(nbtfisInf)

            nsfisInf = tcoorfisInf["NOEUD"].values()["NOEUD"][:nbtfisInf]

            l_coorfisInf = [
                [nsfisInf[i], xsfisInf[i], ysfisInf[i], zsfisInf[i]] for i in range(nbtfisInf)
            ]

            VECTEURINF = []

            for i in range(2):
                if l_coorfisInf[i][0] == Pfiss[0]:
                    if i == 1:
                        for j in range(3):
                            coorVECTEURINF = l_coorfisInf[i][j + 1] - l_coorfisInf[i - 1][j + 1]
                            VECTEURINF.append(coorVECTEURINF)
                    else:
                        for j in range(3):
                            coorVECTEURINF = l_coorfisInf[i][j + 1] - l_coorfisInf[i + 1][j + 1]
                            VECTEURINF.append(coorVECTEURINF)

        # direction of crack propagation

        if (PropadirSup is not None) and (PropadirInf is None):
            VECTEUR = normalize(VECTEURSUP)

        if (PropadirSup is None) and (PropadirInf is not None):
            VECTEUR = normalize(VECTEURINF)

        if (PropadirSup is not None) and (PropadirInf is not None):
            for i in range(2):
                if l_coorfisSup[i][0] == Pfiss[0]:
                    l_coorPfiss = l_coorfisSup[i]
                    for j in range(2):
                        if j != i:
                            l_coorfisPSup = l_coorfisSup[j]

            for i in range(2):
                if l_coorfisInf[i][0] != Pfiss[0]:
                    l_coorfisPInf = l_coorfisInf[i]

            VECTEURSI = []

            for i in range(3):
                coorVECTEURSI = l_coorPfiss[i + 1] - (
                    (l_coorfisPSup[i + 1] + l_coorfisPInf[i + 1]) / 2.0
                )
                VECTEURSI.append(coorVECTEURSI)

            VECTEUR = normalize(VECTEURSI)

        VALDEPX = VECTEUR[0]
        if is_symmetric:
            VALDEPX = VALDEPX * 2.0

        VALDEPY = VECTEUR[1]

        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # CALCULATION DOMAIN
        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        DEFI_GROUP(
            reuse=MAIL,
            MAILLAGE=MAIL,
            CREA_GROUP_NO=(_F(NOM="NBOUGER", NOEUD=FOND_FISS.getCrackFrontNodes()),),
        )

        DEFI_GROUP(
            reuse=MAIL,
            MAILLAGE=MAIL,
            CREA_GROUP_MA=_F(
                NOM="MBOUGER", OPTION="APPUI", GROUP_NO="NBOUGER", TYPE_APPUI="AU_MOINS_UN"
            ),
        )

        for INB_COUCHE in range(1, NB_COUCHES + 1):
            DEFI_GROUP(
                reuse=MAIL,
                MAILLAGE=MAIL,
                DETR_GROUP_NO=_F(NOM="NBOUGER"),
                CREA_GROUP_NO=(_F(NOM="NBOUGER", GROUP_MA="MBOUGER"),),
            )

            DEFI_GROUP(
                reuse=MAIL,
                MAILLAGE=MAIL,
                DETR_GROUP_MA=_F(NOM="MBOUGER"),
                CREA_GROUP_MA=_F(
                    NOM="MBOUGER", OPTION="APPUI", GROUP_NO="NBOUGER", TYPE_APPUI="AU_MOINS_UN"
                ),
            )

        DEFI_GROUP(reuse=MAIL, MAILLAGE=MAIL, CREA_GROUP_NO=(_F(NOM="NMAIL", GROUP_MA="MBOUGER"),))

        DEFI_GROUP(
            reuse=MAIL,
            MAILLAGE=MAIL,
            CREA_GROUP_MA=_F(
                NOM="MMAIL", OPTION="APPUI", GROUP_NO="NMAIL", TYPE_APPUI="AU_MOINS_UN"
            ),
        )

        if modified_J:
            DEFI_GROUP(
                reuse=MAIL,
                MAILLAGE=MAIL,
                CREA_GROUP_NO=(_F(NOM="NBOUGER_IMPR", NOEUD=FOND_FISS.getCrackFrontNodes()),),
            )

            DEFI_GROUP(
                reuse=MAIL,
                MAILLAGE=MAIL,
                CREA_GROUP_MA=_F(
                    NOM="MBOUGER_IMPR",
                    OPTION="APPUI",
                    GROUP_NO="NBOUGER_IMPR",
                    TYPE_APPUI="AU_MOINS_UN",
                ),
            )

            for INB_COUCHE in range(1, 3):
                DEFI_GROUP(
                    reuse=MAIL,
                    MAILLAGE=MAIL,
                    DETR_GROUP_NO=_F(NOM="NBOUGER_IMPR"),
                    CREA_GROUP_NO=(_F(NOM="NBOUGER_IMPR", GROUP_MA="MBOUGER_IMPR"),),
                )

                DEFI_GROUP(
                    reuse=MAIL,
                    MAILLAGE=MAIL,
                    DETR_GROUP_MA=_F(NOM="MBOUGER_IMPR"),
                    CREA_GROUP_MA=_F(
                        NOM="MBOUGER_IMPR",
                        OPTION="APPUI",
                        GROUP_NO="NBOUGER_IMPR",
                        TYPE_APPUI="AU_MOINS_UN",
                    ),
                )

            DEFI_GROUP(
                reuse=MAIL,
                MAILLAGE=MAIL,
                CREA_GROUP_MA=_F(NOM="MMAIL_IMPR", DIFFE=("MMAIL", "MBOUGER_IMPR")),
            )

        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # PRESENT OF INITIAL STRAIN
        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        if ETAT_INIT is not None:
            DATAINIT = ETAT_INIT[0]

            __INITEPSI = DATAINIT["EPSI"]

            # if __INITEPSI['TYPE_CHAM'] == 'ELGA_EPSI_R':

            __EPS0ELGA = __INITEPSI

            __EPS0NOEU = CREA_CHAMP(
                TYPE_CHAM="NOEU_EPSI_R", OPERATION="DISC", MODELE=MODE, CHAM_GD=__EPS0ELGA
            )

            # if __INITEPSI['TYPE_CHAM'] == 'NOEU_EPSI_R':
            #
            #    __EPS0NOEU = __INITEPSI
            #
            #    __EPS0ELGA = CREA_CHAMP(TYPE_CHAM='ELGA_EPSI_R',
            #                        OPERATION='DISC',
            #                        MODELE=MODE,
            #                        PROL_ZERO='OUI',
            #                        CHAM_GD=__EPS0NOEU)
            #
            # if __INITEPSI['TYPE_CHAM'] == 'ELNO_EPSI_R':
            #
            #    __EPS0NOEU = CREA_CHAMP(TYPE_CHAM='NOEU_EPSI_R',
            #                        OPERATION='DISC',
            #                        MODELE=MODE,
            #                        CHAM_GD=__INITEPSI)
            #
            #    __EPS0ELGA = CREA_CHAMP(TYPE_CHAM='ELGA_EPSI_R',
            #                        OPERATION='DISC',
            #                        MODELE=MODE,
            #                        PROL_ZERO='OUI',
            #                        CHAM_GD=__INITEPSI)

        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # CREATE Q AT GAUSS POINTS
        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        # QX

        __QX_NOEU = CREA_CHAMP(
            OPERATION="AFFE",
            TYPE_CHAM="NOEU_EPSI_R",
            MAILLAGE=MAIL,
            AFFE=(
                _F(TOUT="OUI", NOM_CMP=("EPXX", "EPYY", "EPZZ", "EPXY"), VALE=(0.0, 0.0, 0.0, 0.0)),
                _F(GROUP_MA=("MBOUGER"), NOM_CMP="EPXX", VALE=VALDEPX),
            ),
        )

        __QX_NOEU_GAUSS = CREA_CHAMP(
            OPERATION="DISC", TYPE_CHAM="ELGA_EPSI_R", MODELE=MODE, CHAM_GD=__QX_NOEU
        )

        # QY

        __QY_NOEU = CREA_CHAMP(
            OPERATION="AFFE",
            TYPE_CHAM="NOEU_EPSI_R",
            MAILLAGE=MAIL,
            AFFE=(
                _F(TOUT="OUI", NOM_CMP=("EPXX", "EPYY", "EPZZ", "EPXY"), VALE=(0.0, 0.0, 0.0, 0.0)),
                _F(GROUP_MA=("MBOUGER"), NOM_CMP="EPYY", VALE=VALDEPY),
            ),
        )

        __QY_NOEU_GAUSS = CREA_CHAMP(
            OPERATION="DISC", TYPE_CHAM="ELGA_EPSI_R", MODELE=MODE, CHAM_GD=__QY_NOEU
        )

        del __QX_NOEU, __QY_NOEU

        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # GET COORDINATES IN 2D AXIS
        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        if MODELISATION == "AXIS":
            # get coordinate r

            __CHCOOR_NOEU = CREA_CHAMP(
                OPERATION="EXTR", TYPE_CHAM="NOEU_GEOM_R", NOM_CHAM="GEOMETRIE", MAILLAGE=MAIL
            )

            __CHCOOR_ELGA = CREA_CHAMP(
                OPERATION="DISC", TYPE_CHAM="ELGA_GEOM_R", MODELE=MODE, CHAM_GD=__CHCOOR_NOEU
            )

            # get radial distance from the axis of rotation to the crack tip

            __ncoorCrackTip = POST_RELEVE_T(
                ACTION=_F(
                    RESULTAT=RESULTAT,
                    OPERATION="EXTRACTION",
                    NOEUD=Pfiss,
                    NOM_CHAM="DEPL",
                    NOM_CMP=("DX", "DY"),
                    INTITULE="GET R",
                )
            )

            tcoorCrackTip = __ncoorCrackTip.EXTR_TABLE().NUME_ORDRE == dicLPfissSup["NUME_ORDRE"][0]

            R_CrackTip = tcoorCrackTip["COOR_X"].values()["COOR_X"][0]

        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # GET INSTANTS
        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        dico = __RESU.getAccessParameters()

        if INST is not None:
            PRECISION = args["PRECISION"]
        else:
            PRECISION = None
        liord, linst = list_inst_calc(self, dico, NUME_ORDRE, INST, PRECISION)

        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # LOOP ON THE INSTANTS
        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        J = []

        for iord, inst in zip(liord, linst):
            # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
            # CREATE Q AND CALCUL GRAD Q
            # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

            # GRAD QX,X  QX,Y
            __DEPIX = CREA_CHAMP(
                OPERATION="AFFE",
                TYPE_CHAM="NOEU_DEPL_R",
                MAILLAGE=MAIL,
                AFFE=(
                    _F(TOUT="OUI", NOM_CMP=("DX", "DY"), VALE=(0.0, 0.0)),
                    _F(GROUP_MA=("MBOUGER"), NOM_CMP="DX", VALE=VALDEPX),
                ),
            )

            __RDEPIX = CREA_RESU(
                OPERATION="AFFE",
                TYPE_RESU="EVOL_ELAS",
                AFFE=_F(NOM_CHAM="DEPL", CHAM_GD=__DEPIX, INST=inst),
            )

            __RDEPIX = CALC_CHAMP(
                reuse=__RDEPIX,
                MODELE=MODE,
                CHAM_MATER=MATE,
                RESULTAT=__RDEPIX,
                DEFORMATION=("EPSI_ELGA"),
            )

            __GDEPIX = CREA_CHAMP(
                TYPE_CHAM="ELGA_EPSI_R",
                OPERATION="EXTR",
                RESULTAT=__RDEPIX,
                NOM_CHAM="EPSI_ELGA",
                INST=inst,
            )

            del __DEPIX, __RDEPIX

            # GRAD QY,Y  QY,X

            __DEPIY = CREA_CHAMP(
                OPERATION="AFFE",
                TYPE_CHAM="NOEU_DEPL_R",
                MAILLAGE=MAIL,
                AFFE=(
                    _F(TOUT="OUI", NOM_CMP=("DX", "DY"), VALE=(0.0, 0.0)),
                    _F(GROUP_MA=("MBOUGER"), NOM_CMP="DY", VALE=VALDEPY),
                ),
            )

            __RDEPIY = CREA_RESU(
                OPERATION="AFFE",
                TYPE_RESU="EVOL_ELAS",
                AFFE=_F(NOM_CHAM="DEPL", CHAM_GD=__DEPIY, INST=inst),
            )

            __RDEPIY = CALC_CHAMP(
                reuse=__RDEPIY,
                MODELE=MODE,
                CHAM_MATER=MATE,
                RESULTAT=__RDEPIY,
                DEFORMATION=("EPSI_ELGA"),
            )

            __GDEPIY = CREA_CHAMP(
                TYPE_CHAM="ELGA_EPSI_R",
                OPERATION="EXTR",
                RESULTAT=__RDEPIY,
                NOM_CHAM="EPSI_ELGA",
                INST=inst,
            )

            del __DEPIY, __RDEPIY

            # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
            # GET DISPLACEMENT U AND CALCUL GRAD U
            # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

            # displacement U

            __DEPINT = CREA_CHAMP(
                TYPE_CHAM="NOEU_DEPL_R",
                OPERATION="EXTR",
                RESULTAT=__RESU,
                NOM_CHAM="DEPL",
                NUME_ORDRE=iord,
            )

            # creat (UX,0) and calcul GRAD UX,X  UX,Y

            __UX1 = FORMULE(NOM_PARA=("DX", "DY"), VALE="DX")
            __UX2 = FORMULE(NOM_PARA=("DX", "DY"), VALE="0.")

            __CHUX = CREA_CHAMP(
                OPERATION="AFFE",
                TYPE_CHAM="NOEU_NEUT_F",
                MAILLAGE=MAIL,
                AFFE=_F(TOUT="OUI", NOM_CMP=("X1", "X2"), VALE_F=(__UX1, __UX2)),
            )

            __DEPUX = CREA_CHAMP(
                OPERATION="EVAL", TYPE_CHAM="NOEU_NEUT_R", CHAM_F=__CHUX, CHAM_PARA=__DEPINT
            )

            __DEPUX = CREA_CHAMP(
                OPERATION="ASSE",
                MODELE=MODE,
                TYPE_CHAM="NOEU_DEPL_R",
                ASSE=_F(
                    CHAM_GD=__DEPUX, TOUT="OUI", NOM_CMP=("X1", "X2"), NOM_CMP_RESU=("DX", "DY")
                ),
            )

            __DEPUX = CREA_RESU(
                OPERATION="AFFE",
                TYPE_RESU="EVOL_ELAS",
                AFFE=_F(NOM_CHAM="DEPL", CHAM_GD=__DEPUX, INST=inst),
            )

            __GDEPX = CALC_CHAMP(
                reuse=__DEPUX,
                MODELE=MODE,
                CHAM_MATER=MATE,
                RESULTAT=__DEPUX,
                DEFORMATION=("EPSI_ELGA"),
            )

            __GDEPX = CREA_CHAMP(
                TYPE_CHAM="ELGA_EPSI_R",
                OPERATION="EXTR",
                RESULTAT=__GDEPX,
                NOM_CHAM="EPSI_ELGA",
                INST=inst,
            )

            del __CHUX, __UX1, __UX2, __DEPUX

            # creat (0,UY) and calcul GRAD UY,Y  UY,X

            __UY1 = FORMULE(NOM_PARA=("DX", "DY"), VALE="0.")
            __UY2 = FORMULE(NOM_PARA=("DX", "DY"), VALE="DY")

            __CHUY = CREA_CHAMP(
                OPERATION="AFFE",
                TYPE_CHAM="NOEU_NEUT_F",
                MAILLAGE=MAIL,
                AFFE=_F(TOUT="OUI", NOM_CMP=("X1", "X2"), VALE_F=(__UY1, __UY2)),
            )

            __DEPUY = CREA_CHAMP(
                OPERATION="EVAL", TYPE_CHAM="NOEU_NEUT_R", CHAM_F=__CHUY, CHAM_PARA=__DEPINT
            )

            __DEPUY = CREA_CHAMP(
                OPERATION="ASSE",
                MODELE=MODE,
                TYPE_CHAM="NOEU_DEPL_R",
                ASSE=_F(
                    CHAM_GD=__DEPUY, TOUT="OUI", NOM_CMP=("X1", "X2"), NOM_CMP_RESU=("DX", "DY")
                ),
            )

            __DEPUY = CREA_RESU(
                OPERATION="AFFE",
                TYPE_RESU="EVOL_ELAS",
                AFFE=_F(NOM_CHAM="DEPL", CHAM_GD=__DEPUY, INST=inst),
            )

            __GDEPY = CALC_CHAMP(
                reuse=__DEPUY,
                MODELE=MODE,
                CHAM_MATER=MATE,
                RESULTAT=__DEPUY,
                DEFORMATION=("EPSI_ELGA"),
            )

            __GDEPY = CREA_CHAMP(
                TYPE_CHAM="ELGA_EPSI_R",
                OPERATION="EXTR",
                RESULTAT=__GDEPY,
                NOM_CHAM="EPSI_ELGA",
                INST=inst,
            )

            del __CHUY, __UY1, __UY2, __DEPUY

            # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
            # GET STRESS
            # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

            __RESU = CALC_CHAMP(reuse=__RESU, RESULTAT=__RESU, CONTRAINTE=("SIGM_ELGA"))

            __SIGF = CREA_CHAMP(
                TYPE_CHAM="ELGA_SIEF_R",
                OPERATION="EXTR",
                RESULTAT=__RESU,
                NOM_CHAM="SIEF_ELGA",
                NUME_ORDRE=iord,
            )

            # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
            # GET STRAIN
            # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

            __RESU = CALC_CHAMP(
                reuse=__RESU, RESULTAT=__RESU, DEFORMATION=("EPSI_NOEU", "EPSI_ELGA")
            )

            __EPSNOEU = CREA_CHAMP(
                TYPE_CHAM="NOEU_EPSI_R",
                OPERATION="EXTR",
                RESULTAT=__RESU,
                NOM_CHAM="EPSI_NOEU",
                NUME_ORDRE=iord,
            )

            __EPSELGA = CREA_CHAMP(
                TYPE_CHAM="ELGA_EPSI_R",
                OPERATION="EXTR",
                RESULTAT=__RESU,
                NOM_CHAM="EPSI_ELGA",
                NUME_ORDRE=iord,
            )

            # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
            # GET STRAIN ENERGY
            # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

            if ETAT_INIT is None:
                __RESU = CALC_CHAMP(reuse=__RESU, RESULTAT=__RESU, ENERGIE=("ETOT_ELGA"))

                __WELAS = CREA_CHAMP(
                    TYPE_CHAM="ELGA_ENER_R",
                    OPERATION="EXTR",
                    RESULTAT=__RESU,
                    NOM_CHAM="ETOT_ELGA",
                    NUME_ORDRE=iord,
                )

                __WELAS = CREA_CHAMP(
                    OPERATION="ASSE",
                    TYPE_CHAM="ELGA_NEUT_R",
                    MODELE=MODE,
                    PROL_ZERO="OUI",
                    ASSE=(
                        _F(TOUT="OUI", CHAM_GD=__WELAS, NOM_CMP=("TOTALE",), NOM_CMP_RESU=("X10",)),
                    ),
                )

            else:
                # W = 1/2 * (EPS - EPS_0) * SIG

                __RESU = CALC_CHAMP(reuse=__RESU, RESULTAT=__RESU, DEFORMATION=("EPSI_ELGA"))

                __EPSF = CREA_CHAMP(
                    TYPE_CHAM="ELGA_EPSI_R",
                    OPERATION="EXTR",
                    RESULTAT=__RESU,
                    NOM_CHAM="EPSI_ELGA",
                    NUME_ORDRE=iord,
                )

                __CHW = CREA_CHAMP(
                    OPERATION="ASSE",
                    TYPE_CHAM="ELGA_NEUT_R",
                    MODELE=MODE,
                    PROL_ZERO="OUI",
                    ASSE=(
                        _F(TOUT="OUI", CHAM_GD=__EPSF, NOM_CMP=("EPXX",), NOM_CMP_RESU=("X1",)),
                        _F(TOUT="OUI", CHAM_GD=__EPSF, NOM_CMP=("EPXY",), NOM_CMP_RESU=("X2",)),
                        _F(TOUT="OUI", CHAM_GD=__EPSF, NOM_CMP=("EPYY",), NOM_CMP_RESU=("X3",)),
                        _F(TOUT="OUI", CHAM_GD=__SIGF, NOM_CMP=("SIXX",), NOM_CMP_RESU=("X4",)),
                        _F(TOUT="OUI", CHAM_GD=__SIGF, NOM_CMP=("SIXY",), NOM_CMP_RESU=("X5",)),
                        _F(TOUT="OUI", CHAM_GD=__SIGF, NOM_CMP=("SIYY",), NOM_CMP_RESU=("X6",)),
                        _F(TOUT="OUI", CHAM_GD=__EPS0ELGA, NOM_CMP=("EPXX",), NOM_CMP_RESU=("X7",)),
                        _F(TOUT="OUI", CHAM_GD=__EPS0ELGA, NOM_CMP=("EPXY",), NOM_CMP_RESU=("X8",)),
                        _F(TOUT="OUI", CHAM_GD=__EPS0ELGA, NOM_CMP=("EPYY",), NOM_CMP_RESU=("X9",)),
                    ),
                )

                __FMULTW = FORMULE(
                    NOM_PARA=("X1", "X2", "X3", "X4", "X5", "X6", "X7", "X8", "X9"),
                    VALE="((X1-X7)*X4/2)+((X2-X8)*X5)+((X3-X9)*X6/2)",
                )

                __CHFMUW = CREA_CHAMP(
                    OPERATION="AFFE",
                    TYPE_CHAM="ELGA_NEUT_F",
                    MODELE=MODE,
                    PROL_ZERO="OUI",
                    AFFE=_F(TOUT="OUI", NOM_CMP="X10", VALE_F=__FMULTW),
                )

                __WELAS = CREA_CHAMP(
                    OPERATION="EVAL", TYPE_CHAM="ELGA_NEUT_R", CHAM_F=__CHFMUW, CHAM_PARA=(__CHW,)
                )

                del __CHW, __CHFMUW

            # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
            # CALCUL J
            # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

            # -------------------------------------------------------------
            # J01
            # -------------------------------------------------------------

            # J01 = W * DIVQ

            if MODELISATION != "AXIS":
                __CHJ01 = CREA_CHAMP(
                    OPERATION="ASSE",
                    TYPE_CHAM="ELGA_NEUT_R",
                    MODELE=MODE,
                    PROL_ZERO="OUI",
                    ASSE=(
                        _F(TOUT="OUI", CHAM_GD=__WELAS, NOM_CMP=("X10",), NOM_CMP_RESU=("X1",)),
                        _F(TOUT="OUI", CHAM_GD=__GDEPIX, NOM_CMP=("EPXX",), NOM_CMP_RESU=("X2",)),
                        _F(TOUT="OUI", CHAM_GD=__GDEPIY, NOM_CMP=("EPYY",), NOM_CMP_RESU=("X3",)),
                    ),
                )

                __FMULTJ01 = FORMULE(NOM_PARA=("X1", "X2", "X3"), VALE="X1*(X2+X3)")

            else:
                __CHJ01 = CREA_CHAMP(
                    OPERATION="ASSE",
                    TYPE_CHAM="ELGA_NEUT_R",
                    MODELE=MODE,
                    PROL_ZERO="OUI",
                    ASSE=(
                        _F(TOUT="OUI", CHAM_GD=__WELAS, NOM_CMP=("X10",), NOM_CMP_RESU=("X1",)),
                        _F(TOUT="OUI", CHAM_GD=__GDEPIX, NOM_CMP=("EPXX",), NOM_CMP_RESU=("X2",)),
                        _F(TOUT="OUI", CHAM_GD=__GDEPIY, NOM_CMP=("EPYY",), NOM_CMP_RESU=("X3",)),
                        _F(TOUT="OUI", CHAM_GD=__CHCOOR_ELGA, NOM_CMP=("X",), NOM_CMP_RESU=("X5",)),
                    ),
                )

                __FMULTJ01 = FORMULE(NOM_PARA=("X1", "X2", "X3", "X5"), VALE="(X1*(X2+X3))*X5")

            __CHFMUJ01 = CREA_CHAMP(
                OPERATION="AFFE",
                TYPE_CHAM="ELGA_NEUT_F",
                MODELE=MODE,
                PROL_ZERO="OUI",
                AFFE=_F(TOUT="OUI", NOM_CMP="X4", VALE_F=__FMULTJ01),
            )

            __CHJ01INT = CREA_CHAMP(
                OPERATION="EVAL", TYPE_CHAM="ELGA_NEUT_R", CHAM_F=__CHFMUJ01, CHAM_PARA=(__CHJ01,)
            )

            __RESUJ01 = CREA_RESU(
                OPERATION="AFFE",
                TYPE_RESU="EVOL_ELAS",
                AFFE=_F(NOM_CHAM="VARI_ELGA", MODELE=MODE, INST=inst, CHAM_GD=__CHJ01INT),
            )

            __J01 = POST_ELEM(
                RESULTAT=__RESUJ01,
                MODELE=MODE,
                INST=inst,
                INTEGRALE=_F(
                    NOM_CHAM="VARI_ELGA", GROUP_MA="MMAIL", NOM_CMP="X4", TYPE_MAILLE="2D"
                ),
            )

            del __CHJ01, __FMULTJ01, __CHFMUJ01, __CHJ01INT, __RESUJ01

            __J01_J = __J01.EXTR_TABLE().values()["INTE_X4"]

            __J = -__J01_J[0]

            # -------------------------------------------------------------
            # J02
            # -------------------------------------------------------------

            # GRAD U * GRAD Q

            __CHGRAUQ = CREA_CHAMP(
                OPERATION="ASSE",
                TYPE_CHAM="ELGA_NEUT_R",
                MODELE=MODE,
                PROL_ZERO="OUI",
                ASSE=(
                    _F(TOUT="OUI", CHAM_GD=__GDEPX, NOM_CMP=("EPXX",), NOM_CMP_RESU=("X1",)),
                    _F(TOUT="OUI", CHAM_GD=__GDEPX, NOM_CMP=("EPXY",), NOM_CMP_RESU=("X2",)),
                    _F(TOUT="OUI", CHAM_GD=__GDEPY, NOM_CMP=("EPXY",), NOM_CMP_RESU=("X3",)),
                    _F(TOUT="OUI", CHAM_GD=__GDEPY, NOM_CMP=("EPYY",), NOM_CMP_RESU=("X4",)),
                    _F(TOUT="OUI", CHAM_GD=__GDEPIX, NOM_CMP=("EPXX",), NOM_CMP_RESU=("X5",)),
                    _F(TOUT="OUI", CHAM_GD=__GDEPIX, NOM_CMP=("EPXY",), NOM_CMP_RESU=("X6",)),
                    _F(TOUT="OUI", CHAM_GD=__GDEPIY, NOM_CMP=("EPXY",), NOM_CMP_RESU=("X7",)),
                    _F(TOUT="OUI", CHAM_GD=__GDEPIY, NOM_CMP=("EPYY",), NOM_CMP_RESU=("X8",)),
                ),
            )

            __FMULTGRAUQ_X9 = FORMULE(
                NOM_PARA=("X1", "X2", "X5", "X7"), VALE="(X1*X5)+((X2*2)*(X7*2))"
            )

            __FMULTGRAUQ_X10 = FORMULE(
                NOM_PARA=("X1", "X2", "X6", "X8"), VALE="(X1*(X6*2))+((X2*2)*X8)"
            )

            __FMULTGRAUQ_X11 = FORMULE(
                NOM_PARA=("X3", "X4", "X5", "X7"), VALE="((X3*2)*X5)+(X4*(X7*2))"
            )

            __FMULTGRAUQ_X12 = FORMULE(
                NOM_PARA=("X3", "X4", "X6", "X8"), VALE="((X3*2)*(X6*2))+(X4*X8)"
            )

            __CHFMUGRAUQ = CREA_CHAMP(
                OPERATION="AFFE",
                TYPE_CHAM="ELGA_NEUT_F",
                MODELE=MODE,
                PROL_ZERO="OUI",
                AFFE=_F(
                    TOUT="OUI",
                    NOM_CMP=("X9", "X10", "X11", "X12"),
                    VALE_F=(__FMULTGRAUQ_X9, __FMULTGRAUQ_X10, __FMULTGRAUQ_X11, __FMULTGRAUQ_X12),
                ),
            )

            __CHGRAUMQ = CREA_CHAMP(
                OPERATION="EVAL",
                TYPE_CHAM="ELGA_NEUT_R",
                CHAM_F=__CHFMUGRAUQ,
                CHAM_PARA=(__CHGRAUQ,),
            )

            del (
                __CHGRAUQ,
                __FMULTGRAUQ_X9,
                __FMULTGRAUQ_X10,
                __FMULTGRAUQ_X11,
                __FMULTGRAUQ_X12,
                __CHFMUGRAUQ,
            )

            # SIGMA * (GRAD U * GRAD Q)

            if MODELISATION != "AXIS":
                __CHJ02 = CREA_CHAMP(
                    OPERATION="ASSE",
                    TYPE_CHAM="ELGA_NEUT_R",
                    MODELE=MODE,
                    PROL_ZERO="OUI",
                    ASSE=(
                        _F(TOUT="OUI", CHAM_GD=__CHGRAUMQ, NOM_CMP=("X9",), NOM_CMP_RESU=("X9",)),
                        _F(TOUT="OUI", CHAM_GD=__CHGRAUMQ, NOM_CMP=("X10",), NOM_CMP_RESU=("X10",)),
                        _F(TOUT="OUI", CHAM_GD=__CHGRAUMQ, NOM_CMP=("X11",), NOM_CMP_RESU=("X11",)),
                        _F(TOUT="OUI", CHAM_GD=__CHGRAUMQ, NOM_CMP=("X12",), NOM_CMP_RESU=("X12",)),
                        _F(TOUT="OUI", CHAM_GD=__SIGF, NOM_CMP=("SIXX",), NOM_CMP_RESU=("X13",)),
                        _F(TOUT="OUI", CHAM_GD=__SIGF, NOM_CMP=("SIXY",), NOM_CMP_RESU=("X14",)),
                        _F(TOUT="OUI", CHAM_GD=__SIGF, NOM_CMP=("SIYY",), NOM_CMP_RESU=("X15",)),
                    ),
                )

                __FMULTJ02 = FORMULE(
                    NOM_PARA=("X9", "X10", "X11", "X12", "X13", "X14", "X15"),
                    VALE="(X9*X13)+(X10*X14)+(X11*X14)+(X12*X15)",
                )

            else:
                __CHJ02 = CREA_CHAMP(
                    OPERATION="ASSE",
                    TYPE_CHAM="ELGA_NEUT_R",
                    MODELE=MODE,
                    PROL_ZERO="OUI",
                    ASSE=(
                        _F(TOUT="OUI", CHAM_GD=__CHGRAUMQ, NOM_CMP=("X9",), NOM_CMP_RESU=("X9",)),
                        _F(TOUT="OUI", CHAM_GD=__CHGRAUMQ, NOM_CMP=("X10",), NOM_CMP_RESU=("X10",)),
                        _F(TOUT="OUI", CHAM_GD=__CHGRAUMQ, NOM_CMP=("X11",), NOM_CMP_RESU=("X11",)),
                        _F(TOUT="OUI", CHAM_GD=__CHGRAUMQ, NOM_CMP=("X12",), NOM_CMP_RESU=("X12",)),
                        _F(TOUT="OUI", CHAM_GD=__SIGF, NOM_CMP=("SIXX",), NOM_CMP_RESU=("X13",)),
                        _F(TOUT="OUI", CHAM_GD=__SIGF, NOM_CMP=("SIXY",), NOM_CMP_RESU=("X14",)),
                        _F(TOUT="OUI", CHAM_GD=__SIGF, NOM_CMP=("SIYY",), NOM_CMP_RESU=("X15",)),
                        _F(
                            TOUT="OUI", CHAM_GD=__CHCOOR_ELGA, NOM_CMP=("X",), NOM_CMP_RESU=("X17",)
                        ),
                    ),
                )

                __FMULTJ02 = FORMULE(
                    NOM_PARA=("X9", "X10", "X11", "X12", "X13", "X14", "X15", "X17"),
                    VALE="((X9*X13)+(X10*X14)+(X11*X14)+(X12*X15))*X17",
                )

            __CHFMUJ02 = CREA_CHAMP(
                OPERATION="AFFE",
                TYPE_CHAM="ELGA_NEUT_F",
                MODELE=MODE,
                PROL_ZERO="OUI",
                AFFE=_F(TOUT="OUI", NOM_CMP="X16", VALE_F=__FMULTJ02),
            )

            __CHJ02INT = CREA_CHAMP(
                OPERATION="EVAL", TYPE_CHAM="ELGA_NEUT_R", CHAM_F=__CHFMUJ02, CHAM_PARA=(__CHJ02,)
            )

            __RESUJ02 = CREA_RESU(
                OPERATION="AFFE",
                TYPE_RESU="EVOL_ELAS",
                AFFE=_F(NOM_CHAM="VARI_ELGA", MODELE=MODE, INST=inst, CHAM_GD=__CHJ02INT),
            )

            __J02 = POST_ELEM(
                RESULTAT=__RESUJ02,
                MODELE=MODE,
                INST=inst,
                INTEGRALE=_F(
                    NOM_CHAM="VARI_ELGA", GROUP_MA="MMAIL", NOM_CMP="X16", TYPE_MAILLE="2D"
                ),
            )

            del __CHGRAUMQ, __CHJ02, __FMULTJ02, __CHFMUJ02, __CHJ02INT, __RESUJ02

            __J02_J = __J02.EXTR_TABLE().values()["INTE_X16"]

            __J = __J + __J02_J[0]

            if ETAT_INIT is not None:
                # -------------------------------------------------------------
                # J03
                # -------------------------------------------------------------

                # if ETAT_INIT is given, calculation J03

                # J03 = SIGMA * GRAD EPSI_0 * Q
                #     = SIGMA_{ij} * EPSI_0_{ij,k} * Q_{k}

                SIGCOMP = ["SIXX", "SIYY", "SIZZ", "SIXY"]
                EPSCOMP = ["EPXX", "EPYY", "EPZZ", "EPXY"]

                __J03_J = [0.0]

                for ISIGCOMP, IEPSCOMP in zip(SIGCOMP, EPSCOMP):
                    # GRAD EPSI_0

                    __CHEPS0 = CREA_CHAMP(
                        OPERATION="ASSE",
                        MODELE=MODE,
                        TYPE_CHAM="NOEU_DEPL_R",
                        ASSE=(
                            _F(
                                TOUT="OUI",
                                CHAM_GD=__EPS0NOEU,
                                NOM_CMP=(IEPSCOMP,),
                                NOM_CMP_RESU=("DX",),
                            ),
                        ),
                    )

                    __EPS0NOEUX1 = FORMULE(NOM_PARA=("DX"), VALE="DX")
                    __EPS0NOEUX2 = FORMULE(NOM_PARA=("DX"), VALE="DX*0.")

                    __CHEPS0X = CREA_CHAMP(
                        OPERATION="AFFE",
                        TYPE_CHAM="NOEU_NEUT_F",
                        MAILLAGE=MAIL,
                        AFFE=_F(
                            TOUT="OUI", NOM_CMP=("X1", "X2"), VALE_F=(__EPS0NOEUX1, __EPS0NOEUX2)
                        ),
                    )

                    __CHEPS0 = CREA_CHAMP(
                        OPERATION="EVAL",
                        TYPE_CHAM="NOEU_NEUT_R",
                        CHAM_F=__CHEPS0X,
                        CHAM_PARA=__CHEPS0,
                    )

                    __CHEPS0 = CREA_CHAMP(
                        OPERATION="ASSE",
                        MODELE=MODE,
                        TYPE_CHAM="NOEU_DEPL_R",
                        ASSE=_F(
                            CHAM_GD=__CHEPS0,
                            TOUT="OUI",
                            NOM_CMP=("X1", "X2"),
                            NOM_CMP_RESU=("DX", "DY"),
                        ),
                    )

                    __REPS0 = CREA_RESU(
                        OPERATION="AFFE",
                        TYPE_RESU="EVOL_ELAS",
                        AFFE=_F(NOM_CHAM="DEPL", CHAM_GD=__CHEPS0, INST=inst),
                    )

                    __GREPS0 = CALC_CHAMP(
                        reuse=__REPS0,
                        MODELE=MODE,
                        CHAM_MATER=MATE,
                        RESULTAT=__REPS0,
                        DEFORMATION=("EPSI_ELGA"),
                    )

                    __GREPS0 = CREA_CHAMP(
                        TYPE_CHAM="ELGA_EPSI_R",
                        OPERATION="EXTR",
                        RESULTAT=__GREPS0,
                        NOM_CHAM="EPSI_ELGA",
                        INST=inst,
                    )

                    del __CHEPS0, __EPS0NOEUX1, __EPS0NOEUX2, __CHEPS0X, __REPS0

                    if MODELISATION != "AXIS":
                        # SIGMA*(GRAD EPSI_0*Q)

                        __CHJ03 = CREA_CHAMP(
                            OPERATION="ASSE",
                            TYPE_CHAM="ELGA_NEUT_R",
                            MODELE=MODE,
                            PROL_ZERO="OUI",
                            ASSE=(
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__SIGF,
                                    NOM_CMP=(ISIGCOMP,),
                                    NOM_CMP_RESU=("X1",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__GREPS0,
                                    NOM_CMP=("EPXX",),
                                    NOM_CMP_RESU=("X2",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__GREPS0,
                                    NOM_CMP=("EPXY",),
                                    NOM_CMP_RESU=("X3",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__QX_NOEU_GAUSS,
                                    NOM_CMP=("EPXX",),
                                    NOM_CMP_RESU=("X4",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__QY_NOEU_GAUSS,
                                    NOM_CMP=("EPYY",),
                                    NOM_CMP_RESU=("X5",),
                                ),
                            ),
                        )

                        __FMULTJ03 = FORMULE(
                            NOM_PARA=("X1", "X2", "X3", "X4", "X5"),
                            VALE="(X1*X2*X4)+(X1*(X3*2)*X5)",
                        )

                    else:
                        __CHJ03 = CREA_CHAMP(
                            OPERATION="ASSE",
                            TYPE_CHAM="ELGA_NEUT_R",
                            MODELE=MODE,
                            PROL_ZERO="OUI",
                            ASSE=(
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__SIGF,
                                    NOM_CMP=(ISIGCOMP,),
                                    NOM_CMP_RESU=("X1",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__GREPS0,
                                    NOM_CMP=("EPXX",),
                                    NOM_CMP_RESU=("X2",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__GREPS0,
                                    NOM_CMP=("EPXY",),
                                    NOM_CMP_RESU=("X3",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__QX_NOEU_GAUSS,
                                    NOM_CMP=("EPXX",),
                                    NOM_CMP_RESU=("X4",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__QY_NOEU_GAUSS,
                                    NOM_CMP=("EPYY",),
                                    NOM_CMP_RESU=("X5",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__CHCOOR_ELGA,
                                    NOM_CMP=("X",),
                                    NOM_CMP_RESU=("X7",),
                                ),
                            ),
                        )

                        __FMULTJ03 = FORMULE(
                            NOM_PARA=("X1", "X2", "X3", "X4", "X5", "X7"),
                            VALE="((X1*X2*X4)+(X1*(X3*2)*X5))*X7",
                        )

                    __CHFMUJ03 = CREA_CHAMP(
                        OPERATION="AFFE",
                        TYPE_CHAM="ELGA_NEUT_F",
                        MODELE=MODE,
                        PROL_ZERO="OUI",
                        AFFE=_F(TOUT="OUI", NOM_CMP="X6", VALE_F=__FMULTJ03),
                    )

                    __CHJ03INT = CREA_CHAMP(
                        OPERATION="EVAL",
                        TYPE_CHAM="ELGA_NEUT_R",
                        CHAM_F=__CHFMUJ03,
                        CHAM_PARA=(__CHJ03,),
                    )

                    __RESUJ03 = CREA_RESU(
                        OPERATION="AFFE",
                        TYPE_RESU="EVOL_ELAS",
                        AFFE=_F(NOM_CHAM="VARI_ELGA", MODELE=MODE, INST=inst, CHAM_GD=__CHJ03INT),
                    )

                    __J03 = POST_ELEM(
                        RESULTAT=__RESUJ03,
                        MODELE=MODE,
                        INST=inst,
                        INTEGRALE=_F(
                            NOM_CHAM="VARI_ELGA", GROUP_MA="MMAIL", NOM_CMP="X6", TYPE_MAILLE="2D"
                        ),
                    )

                    del __GREPS0, __CHJ03, __FMULTJ03, __CHFMUJ03, __CHJ03INT, __RESUJ03

                    __IJ03_J = __J03.EXTR_TABLE().values()["INTE_X6"]

                    if IEPSCOMP == "EPXY":
                        __IJ03_J = [iJ03 * 2.0 for iJ03 in __IJ03_J]

                    __J03_J = np.array(__J03_J) + np.array(__IJ03_J)

                __J = __J + __J03_J[0]

            if modified_J:
                # -------------------------------------------------------------
                # J04
                # -------------------------------------------------------------

                # J04 = SIGMA * GRAD EPSI * Q
                #     = SIGMA_{ij} * EPSI_{ij,k} * Q_{k}

                SIGCOMP = ["SIXX", "SIYY", "SIZZ", "SIXY"]
                EPSCOMP = ["EPXX", "EPYY", "EPZZ", "EPXY"]

                __J04_J = [0.0]

                for ISIGCOMP, IEPSCOMP in zip(SIGCOMP, EPSCOMP):
                    # GRAD EPSI

                    if ETAT_INIT is not None:
                        # EPS - EPS0

                        __CHEPSNOEU0 = CREA_CHAMP(
                            OPERATION="ASSE",
                            TYPE_CHAM="NOEU_NEUT_R",
                            MODELE=MODE,
                            ASSE=(
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__EPSNOEU,
                                    NOM_CMP=("EPXX",),
                                    NOM_CMP_RESU=("X1",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__EPSNOEU,
                                    NOM_CMP=("EPYY",),
                                    NOM_CMP_RESU=("X2",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__EPSNOEU,
                                    NOM_CMP=("EPZZ",),
                                    NOM_CMP_RESU=("X3",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__EPSNOEU,
                                    NOM_CMP=("EPXY",),
                                    NOM_CMP_RESU=("X4",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__EPS0NOEU,
                                    NOM_CMP=("EPXX",),
                                    NOM_CMP_RESU=("X5",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__EPS0NOEU,
                                    NOM_CMP=("EPYY",),
                                    NOM_CMP_RESU=("X6",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__EPS0NOEU,
                                    NOM_CMP=("EPZZ",),
                                    NOM_CMP_RESU=("X7",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__EPS0NOEU,
                                    NOM_CMP=("EPXY",),
                                    NOM_CMP_RESU=("X8",),
                                ),
                            ),
                        )

                        __FMULTEPS_EPXX = FORMULE(NOM_PARA=("X1", "X5"), VALE="X1-X5")
                        __FMULTEPS_EPYY = FORMULE(NOM_PARA=("X2", "X6"), VALE="X2-X6")
                        __FMULTEPS_EPZZ = FORMULE(NOM_PARA=("X3", "X7"), VALE="X3-X7")
                        __FMULTEPS_EPXY = FORMULE(NOM_PARA=("X4", "X8"), VALE="X4-X8")

                        __CHFMUEPS = CREA_CHAMP(
                            OPERATION="AFFE",
                            TYPE_CHAM="NOEU_NEUT_F",
                            MODELE=MODE,
                            AFFE=_F(
                                TOUT="OUI",
                                NOM_CMP=("X9", "X10", "X11", "X12"),
                                VALE_F=(
                                    __FMULTEPS_EPXX,
                                    __FMULTEPS_EPYY,
                                    __FMULTEPS_EPZZ,
                                    __FMULTEPS_EPXY,
                                ),
                            ),
                        )

                        __EPSNOEU0 = CREA_CHAMP(
                            OPERATION="EVAL",
                            TYPE_CHAM="NOEU_NEUT_R",
                            CHAM_F=__CHFMUEPS,
                            CHAM_PARA=(__CHEPSNOEU0,),
                        )

                        __EPSNOEU0 = CREA_CHAMP(
                            OPERATION="ASSE",
                            MODELE=MODE,
                            TYPE_CHAM="NOEU_EPSI_R",
                            ASSE=(
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__EPSNOEU0,
                                    NOM_CMP=("X9", "X10", "X11", "X12"),
                                    NOM_CMP_RESU=("EPXX", "EPYY", "EPZZ", "EPXY"),
                                ),
                            ),
                        )

                        del __CHEPSNOEU0, __CHFMUEPS

                        __CHEPS = CREA_CHAMP(
                            OPERATION="ASSE",
                            MODELE=MODE,
                            TYPE_CHAM="NOEU_DEPL_R",
                            ASSE=(
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__EPSNOEU0,
                                    NOM_CMP=(IEPSCOMP,),
                                    NOM_CMP_RESU=("DX",),
                                ),
                            ),
                        )

                    else:
                        # EPS

                        __CHEPS = CREA_CHAMP(
                            OPERATION="ASSE",
                            MODELE=MODE,
                            TYPE_CHAM="NOEU_DEPL_R",
                            ASSE=(
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__EPSNOEU,
                                    NOM_CMP=(IEPSCOMP,),
                                    NOM_CMP_RESU=("DX",),
                                ),
                            ),
                        )

                    __EPSNOEUX1 = FORMULE(NOM_PARA=("DX"), VALE="DX")
                    __EPSNOEUX2 = FORMULE(NOM_PARA=("DX"), VALE="DX*0.")

                    __CHEPSX = CREA_CHAMP(
                        OPERATION="AFFE",
                        TYPE_CHAM="NOEU_NEUT_F",
                        MAILLAGE=MAIL,
                        AFFE=_F(
                            TOUT="OUI", NOM_CMP=("X1", "X2"), VALE_F=(__EPSNOEUX1, __EPSNOEUX2)
                        ),
                    )

                    __CHEPS = CREA_CHAMP(
                        OPERATION="EVAL",
                        TYPE_CHAM="NOEU_NEUT_R",
                        CHAM_F=__CHEPSX,
                        CHAM_PARA=__CHEPS,
                    )

                    __CHEPS = CREA_CHAMP(
                        OPERATION="ASSE",
                        MODELE=MODE,
                        TYPE_CHAM="NOEU_DEPL_R",
                        ASSE=_F(
                            CHAM_GD=__CHEPS,
                            TOUT="OUI",
                            NOM_CMP=("X1", "X2"),
                            NOM_CMP_RESU=("DX", "DY"),
                        ),
                    )

                    __REPS = CREA_RESU(
                        OPERATION="AFFE",
                        TYPE_RESU="EVOL_ELAS",
                        AFFE=_F(NOM_CHAM="DEPL", CHAM_GD=__CHEPS, INST=inst),
                    )

                    __GREPS = CALC_CHAMP(
                        reuse=__REPS,
                        MODELE=MODE,
                        CHAM_MATER=MATE,
                        RESULTAT=__REPS,
                        DEFORMATION=("EPSI_ELGA"),
                    )

                    __GREPS = CREA_CHAMP(
                        TYPE_CHAM="ELGA_EPSI_R",
                        OPERATION="EXTR",
                        RESULTAT=__GREPS,
                        NOM_CHAM="EPSI_ELGA",
                        INST=inst,
                    )

                    del __CHEPS, __EPSNOEUX1, __EPSNOEUX2, __CHEPSX, __REPS

                    if MODELISATION != "AXIS":
                        # SIGMA * (GRAD EPSI * Q)

                        __CHJ04 = CREA_CHAMP(
                            OPERATION="ASSE",
                            TYPE_CHAM="ELGA_NEUT_R",
                            MODELE=MODE,
                            PROL_ZERO="OUI",
                            ASSE=(
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__SIGF,
                                    NOM_CMP=(ISIGCOMP,),
                                    NOM_CMP_RESU=("X1",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__GREPS,
                                    NOM_CMP=("EPXX",),
                                    NOM_CMP_RESU=("X2",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__GREPS,
                                    NOM_CMP=("EPXY",),
                                    NOM_CMP_RESU=("X3",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__QX_NOEU_GAUSS,
                                    NOM_CMP=("EPXX",),
                                    NOM_CMP_RESU=("X4",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__QY_NOEU_GAUSS,
                                    NOM_CMP=("EPYY",),
                                    NOM_CMP_RESU=("X5",),
                                ),
                            ),
                        )

                        __FMULTJ04 = FORMULE(
                            NOM_PARA=("X1", "X2", "X3", "X4", "X5"),
                            VALE="(X1*X2*X4)+(X1*(X3*2)*X5)",
                        )

                    else:
                        __CHJ04 = CREA_CHAMP(
                            OPERATION="ASSE",
                            TYPE_CHAM="ELGA_NEUT_R",
                            MODELE=MODE,
                            PROL_ZERO="OUI",
                            ASSE=(
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__SIGF,
                                    NOM_CMP=(ISIGCOMP,),
                                    NOM_CMP_RESU=("X1",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__GREPS,
                                    NOM_CMP=("EPXX",),
                                    NOM_CMP_RESU=("X2",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__GREPS,
                                    NOM_CMP=("EPXY",),
                                    NOM_CMP_RESU=("X3",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__QX_NOEU_GAUSS,
                                    NOM_CMP=("EPXX",),
                                    NOM_CMP_RESU=("X4",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__QY_NOEU_GAUSS,
                                    NOM_CMP=("EPYY",),
                                    NOM_CMP_RESU=("X5",),
                                ),
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__CHCOOR_ELGA,
                                    NOM_CMP=("X",),
                                    NOM_CMP_RESU=("X7",),
                                ),
                            ),
                        )

                        __FMULTJ04 = FORMULE(
                            NOM_PARA=("X1", "X2", "X3", "X4", "X5", "X7"),
                            VALE="((X1*X2*X4)+(X1*(X3*2)*X5))*X7",
                        )

                    __CHFMUJ04 = CREA_CHAMP(
                        OPERATION="AFFE",
                        TYPE_CHAM="ELGA_NEUT_F",
                        MODELE=MODE,
                        PROL_ZERO="OUI",
                        AFFE=_F(TOUT="OUI", NOM_CMP="X6", VALE_F=__FMULTJ04),
                    )

                    __CHJ04INT = CREA_CHAMP(
                        OPERATION="EVAL",
                        TYPE_CHAM="ELGA_NEUT_R",
                        CHAM_F=__CHFMUJ04,
                        CHAM_PARA=(__CHJ04,),
                    )

                    __RESUJ04 = CREA_RESU(
                        OPERATION="AFFE",
                        TYPE_RESU="EVOL_ELAS",
                        AFFE=_F(NOM_CHAM="VARI_ELGA", MODELE=MODE, INST=inst, CHAM_GD=__CHJ04INT),
                    )

                    __J04 = POST_ELEM(
                        RESULTAT=__RESUJ04,
                        MODELE=MODE,
                        INST=inst,
                        INTEGRALE=_F(
                            NOM_CHAM="VARI_ELGA",
                            GROUP_MA="MMAIL_IMPR",
                            NOM_CMP="X6",
                            TYPE_MAILLE="2D",
                        ),
                    )

                    del __GREPS, __CHJ04, __FMULTJ04, __CHFMUJ04, __CHJ04INT, __RESUJ04

                    __IJ04_J = __J04.EXTR_TABLE().values()["INTE_X6"]

                    if IEPSCOMP == "EPXY":
                        __IJ04_J = [iJ04 * 2.0 for iJ04 in __IJ04_J]

                    __J04_J = np.array(__J04_J) + np.array(__IJ04_J)

                __J = __J + __J04_J[0]

                # -------------------------------------------------------------
                # J05
                # -------------------------------------------------------------

                # J05 = GRAD W * Q

                __WELAS_NOEU = CREA_CHAMP(
                    TYPE_CHAM="NOEU_NEUT_R", OPERATION="DISC", MODELE=MODE, CHAM_GD=__WELAS
                )

                __CHWELASNOEU = CREA_CHAMP(
                    OPERATION="ASSE",
                    MODELE=MODE,
                    TYPE_CHAM="NOEU_DEPL_R",
                    ASSE=(
                        _F(
                            TOUT="OUI", CHAM_GD=__WELAS_NOEU, NOM_CMP=("X10",), NOM_CMP_RESU=("DX",)
                        ),
                    ),
                )

                __WELASNOEUX1 = FORMULE(NOM_PARA=("DX"), VALE="DX")
                __WELASNOEUX2 = FORMULE(NOM_PARA=("DX"), VALE="DX*0.")

                __CHWELASNOEUX = CREA_CHAMP(
                    OPERATION="AFFE",
                    TYPE_CHAM="NOEU_NEUT_F",
                    MAILLAGE=MAIL,
                    AFFE=_F(
                        TOUT="OUI", NOM_CMP=("X1", "X2"), VALE_F=(__WELASNOEUX1, __WELASNOEUX2)
                    ),
                )

                __CHWELASNOEU = CREA_CHAMP(
                    OPERATION="EVAL",
                    TYPE_CHAM="NOEU_NEUT_R",
                    CHAM_F=__CHWELASNOEUX,
                    CHAM_PARA=__CHWELASNOEU,
                )

                __CHWELASNOEU = CREA_CHAMP(
                    OPERATION="ASSE",
                    MODELE=MODE,
                    TYPE_CHAM="NOEU_DEPL_R",
                    ASSE=_F(
                        CHAM_GD=__CHWELASNOEU,
                        TOUT="OUI",
                        NOM_CMP=("X1", "X2"),
                        NOM_CMP_RESU=("DX", "DY"),
                    ),
                )

                __RWELASNOEU = CREA_RESU(
                    OPERATION="AFFE",
                    TYPE_RESU="EVOL_ELAS",
                    AFFE=_F(NOM_CHAM="DEPL", CHAM_GD=__CHWELASNOEU, INST=inst),
                )

                __GRWELAS = CALC_CHAMP(
                    reuse=__RWELASNOEU,
                    MODELE=MODE,
                    CHAM_MATER=MATE,
                    RESULTAT=__RWELASNOEU,
                    DEFORMATION=("EPSI_ELGA"),
                )

                __GRWELAS = CREA_CHAMP(
                    TYPE_CHAM="ELGA_EPSI_R",
                    OPERATION="EXTR",
                    RESULTAT=__GRWELAS,
                    NOM_CHAM="EPSI_ELGA",
                    INST=inst,
                )

                del __CHWELASNOEU, __WELASNOEUX1, __WELASNOEUX2, __CHWELASNOEUX, __RWELASNOEU

                if MODELISATION != "AXIS":
                    # GRAD W * Q

                    __CHJ05 = CREA_CHAMP(
                        OPERATION="ASSE",
                        TYPE_CHAM="ELGA_NEUT_R",
                        MODELE=MODE,
                        PROL_ZERO="OUI",
                        ASSE=(
                            _F(
                                TOUT="OUI",
                                CHAM_GD=__GRWELAS,
                                NOM_CMP=("EPXX",),
                                NOM_CMP_RESU=("X1",),
                            ),
                            _F(
                                TOUT="OUI",
                                CHAM_GD=__GRWELAS,
                                NOM_CMP=("EPXY",),
                                NOM_CMP_RESU=("X2",),
                            ),
                            _F(
                                TOUT="OUI",
                                CHAM_GD=__QX_NOEU_GAUSS,
                                NOM_CMP=("EPXX",),
                                NOM_CMP_RESU=("X3",),
                            ),
                            _F(
                                TOUT="OUI",
                                CHAM_GD=__QY_NOEU_GAUSS,
                                NOM_CMP=("EPYY",),
                                NOM_CMP_RESU=("X4",),
                            ),
                        ),
                    )

                    __FMULTJ05 = FORMULE(
                        NOM_PARA=("X1", "X2", "X3", "X4"), VALE="(X1*X3)+(2*X2*X4)"
                    )

                else:
                    __CHJ05 = CREA_CHAMP(
                        OPERATION="ASSE",
                        TYPE_CHAM="ELGA_NEUT_R",
                        MODELE=MODE,
                        PROL_ZERO="OUI",
                        ASSE=(
                            _F(
                                TOUT="OUI",
                                CHAM_GD=__GRWELAS,
                                NOM_CMP=("EPXX",),
                                NOM_CMP_RESU=("X1",),
                            ),
                            _F(
                                TOUT="OUI",
                                CHAM_GD=__GRWELAS,
                                NOM_CMP=("EPXY",),
                                NOM_CMP_RESU=("X2",),
                            ),
                            _F(
                                TOUT="OUI",
                                CHAM_GD=__QX_NOEU_GAUSS,
                                NOM_CMP=("EPXX",),
                                NOM_CMP_RESU=("X3",),
                            ),
                            _F(
                                TOUT="OUI",
                                CHAM_GD=__QY_NOEU_GAUSS,
                                NOM_CMP=("EPYY",),
                                NOM_CMP_RESU=("X4",),
                            ),
                            _F(
                                TOUT="OUI",
                                CHAM_GD=__CHCOOR_ELGA,
                                NOM_CMP=("X",),
                                NOM_CMP_RESU=("X6",),
                            ),
                        ),
                    )

                    __FMULTJ05 = FORMULE(
                        NOM_PARA=("X1", "X2", "X3", "X4", "X6"), VALE="((X1*X3)+(2*X2*X4))*X6"
                    )

                __CHFMUJ05 = CREA_CHAMP(
                    OPERATION="AFFE",
                    TYPE_CHAM="ELGA_NEUT_F",
                    MODELE=MODE,
                    PROL_ZERO="OUI",
                    AFFE=_F(TOUT="OUI", NOM_CMP="X5", VALE_F=__FMULTJ05),
                )

                __CHJ05INT = CREA_CHAMP(
                    OPERATION="EVAL",
                    TYPE_CHAM="ELGA_NEUT_R",
                    CHAM_F=__CHFMUJ05,
                    CHAM_PARA=(__CHJ05,),
                )

                __RESUJ05 = CREA_RESU(
                    OPERATION="AFFE",
                    TYPE_RESU="EVOL_ELAS",
                    AFFE=_F(NOM_CHAM="VARI_ELGA", MODELE=MODE, INST=inst, CHAM_GD=__CHJ05INT),
                )

                __J05 = POST_ELEM(
                    RESULTAT=__RESUJ05,
                    MODELE=MODE,
                    INST=inst,
                    INTEGRALE=_F(
                        NOM_CHAM="VARI_ELGA", GROUP_MA="MMAIL_IMPR", NOM_CMP="X5", TYPE_MAILLE="2D"
                    ),
                )

                del __CHJ05, __FMULTJ05, __CHFMUJ05, __CHJ05INT, __RESUJ05

                __J05_J = __J05.EXTR_TABLE().values()["INTE_X5"]

                __J = __J - __J05_J[0]

            if MODELISATION == "AXIS":
                # -------------------------------------------------------------
                # J06
                # -------------------------------------------------------------

                # J06 = SIGMA_PhiPhi * (U_r / r) * Q_r

                __DEPINT_NEUT = CREA_CHAMP(
                    OPERATION="ASSE",
                    MODELE=MODE,
                    TYPE_CHAM="NOEU_NEUT_R",
                    ASSE=_F(CHAM_GD=__DEPINT, TOUT="OUI", NOM_CMP=("DX",), NOM_CMP_RESU=("X1",)),
                )

                __DEPINT_ELGA = CREA_CHAMP(
                    TYPE_CHAM="ELGA_NEUT_R",
                    OPERATION="DISC",
                    MODELE=MODE,
                    PROL_ZERO="OUI",
                    CHAM_GD=__DEPINT_NEUT,
                )

                __CHJ06 = CREA_CHAMP(
                    OPERATION="ASSE",
                    TYPE_CHAM="ELGA_NEUT_R",
                    MODELE=MODE,
                    PROL_ZERO="OUI",
                    ASSE=(
                        _F(TOUT="OUI", CHAM_GD=__SIGF, NOM_CMP=("SIZZ",), NOM_CMP_RESU=("X1",)),
                        _F(
                            TOUT="OUI", CHAM_GD=__DEPINT_ELGA, NOM_CMP=("X1",), NOM_CMP_RESU=("X2",)
                        ),
                        _F(TOUT="OUI", CHAM_GD=__CHCOOR_ELGA, NOM_CMP=("X",), NOM_CMP_RESU=("X3",)),
                        _F(
                            TOUT="OUI",
                            CHAM_GD=__QX_NOEU_GAUSS,
                            NOM_CMP=("EPXX",),
                            NOM_CMP_RESU=("X4",),
                        ),
                    ),
                )

                __FMULTJ06 = FORMULE(
                    NOM_PARA=("X1", "X2", "X3", "X4"), VALE="X1*(X2/(X3+1.E-18))*X4"
                )

                __CHFMUJ06 = CREA_CHAMP(
                    OPERATION="AFFE",
                    TYPE_CHAM="ELGA_NEUT_F",
                    MODELE=MODE,
                    PROL_ZERO="OUI",
                    AFFE=_F(TOUT="OUI", NOM_CMP="X5", VALE_F=__FMULTJ06),
                )

                __CHJ06INT = CREA_CHAMP(
                    OPERATION="EVAL",
                    TYPE_CHAM="ELGA_NEUT_R",
                    CHAM_F=__CHFMUJ06,
                    CHAM_PARA=(__CHJ06,),
                )

                __RESUJ06 = CREA_RESU(
                    OPERATION="AFFE",
                    TYPE_RESU="EVOL_ELAS",
                    AFFE=_F(NOM_CHAM="VARI_ELGA", MODELE=MODE, INST=inst, CHAM_GD=__CHJ06INT),
                )

                __J06 = POST_ELEM(
                    RESULTAT=__RESUJ06,
                    MODELE=MODE,
                    INST=inst,
                    INTEGRALE=_F(
                        NOM_CHAM="VARI_ELGA", GROUP_MA="MMAIL", NOM_CMP="X5", TYPE_MAILLE="2D"
                    ),
                )

                del __DEPINT_NEUT, __CHJ06, __FMULTJ06, __CHFMUJ06, __CHJ06INT, __RESUJ06

                __J06_J = __J06.EXTR_TABLE().values()["INTE_X5"]

                __J = __J + __J06_J[0]

                # -------------------------------------------------------------
                # J07
                # -------------------------------------------------------------

                # J07 = W * Q_r

                __CHJ07 = CREA_CHAMP(
                    OPERATION="ASSE",
                    TYPE_CHAM="ELGA_NEUT_R",
                    MODELE=MODE,
                    PROL_ZERO="OUI",
                    ASSE=(
                        _F(TOUT="OUI", CHAM_GD=__WELAS, NOM_CMP=("X10",), NOM_CMP_RESU=("X1",)),
                        _F(
                            TOUT="OUI",
                            CHAM_GD=__QX_NOEU_GAUSS,
                            NOM_CMP=("EPXX",),
                            NOM_CMP_RESU=("X2",),
                        ),
                    ),
                )

                __FMULTJ07 = FORMULE(NOM_PARA=("X1", "X2"), VALE="X1*X2")

                __CHFMUJ07 = CREA_CHAMP(
                    OPERATION="AFFE",
                    TYPE_CHAM="ELGA_NEUT_F",
                    MODELE=MODE,
                    PROL_ZERO="OUI",
                    AFFE=_F(TOUT="OUI", NOM_CMP="X3", VALE_F=__FMULTJ07),
                )

                __CHJ07INT = CREA_CHAMP(
                    OPERATION="EVAL",
                    TYPE_CHAM="ELGA_NEUT_R",
                    CHAM_F=__CHFMUJ07,
                    CHAM_PARA=(__CHJ07,),
                )

                __RESUJ07 = CREA_RESU(
                    OPERATION="AFFE",
                    TYPE_RESU="EVOL_ELAS",
                    AFFE=_F(NOM_CHAM="VARI_ELGA", MODELE=MODE, INST=inst, CHAM_GD=__CHJ07INT),
                )

                __J07 = POST_ELEM(
                    RESULTAT=__RESUJ07,
                    MODELE=MODE,
                    INST=inst,
                    INTEGRALE=_F(
                        NOM_CHAM="VARI_ELGA", GROUP_MA="MMAIL", NOM_CMP="X3", TYPE_MAILLE="2D"
                    ),
                )

                del __CHJ07, __FMULTJ07, __CHFMUJ07, __CHJ07INT, __RESUJ07

                __J07_J = __J07.EXTR_TABLE().values()["INTE_X3"]

                __J = __J - __J07_J[0]

            if MODELISATION == "AXIS":
                __J = __J / R_CrackTip

            J.append(__J)

        DEFI_GROUP(
            reuse=MAIL,
            MAILLAGE=MAIL,
            DETR_GROUP_NO=_F(NOM=("NBOUGER", "NMAIL")),
            DETR_GROUP_MA=_F(NOM=("MBOUGER", "MMAIL")),
        )

        if modified_J:
            DEFI_GROUP(
                reuse=MAIL,
                MAILLAGE=MAIL,
                DETR_GROUP_NO=_F(NOM=("NBOUGER_IMPR")),
                DETR_GROUP_MA=_F(NOM=("MBOUGER_IMPR", "MMAIL_IMPR")),
            )

        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
        # EXTRACT RESULTS
        # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        tab_result = get_result2D(
            self, J, __J01, linst, liord, MODELISATION, NB_COUCHES, e, nu, is_symmetric, TITRE
        )

    """
    Macro MODELISATION - Calculate POST_JMOD-integral in 3D
    """
    if ndim == 3:
        print("Macro POST_JMOD - Calculate J-integral in 3D")

        #   Get symmetry problem
        if is_symmetric:
            XMULT = 2.0
        else:
            XMULT = 1.0

        #   Get element type
        elemType = FOND_FISS.getCrackTipCellsType()

        #   Constraint of number of NB_COUCHES
        if elemType == "SEG2":
            if NB_COUCHES >= 20:
                UTMESS("F", "RUPTURE4_11")

        else:
            if NB_COUCHES >= 10:
                UTMESS("F", "RUPTURE4_12")

        #   --------------------------------------------------------------------------
        #   GET NAME OF LIPS
        #
        lipSupName, lipInfName = na_lips(self, MAIL, FOND_FISS, is_symmetric)
        if lipSupName is None:
            UTMESS("F", "RUPTURE2_4")

        #   --------------------------------------------------------------------------
        #   GET NODES OF CRACK FRONT, NUMBER OF NODES AND CRACK FRONT TYPE
        #
        NP, TPFISS, closedCrack = no_fond_fiss(self, FOND_FISS)
        #   --------------------------------------------------------------------------
        #   GET NODES ON CRACK LIPS THROUGH NODES OF CRACK FRONT
        #
        TLIPSUP, TLIPINF = no_lips(self, NP, FOND_FISS, NB_COUCHES, is_symmetric, closedCrack)
        #   --------------------------------------------------------------------------
        #   GET COORDINATES OF ALL NODES
        #
        all_co = all_coordinates(self, MAIL)
        #   --------------------------------------------------------------------------
        #   DIRECTION OF VIRTUAL CRACK PROPAGATION
        #
        TVECTEUR = {}

        poinsf_na = na_poinsf(self, FOND_FISS, is_symmetric, elemType)
        if is_symmetric:
            POINSF = all_co[poinsf_na]
        else:
            POINSF = (
                (np.array(all_co[poinsf_na[0]]) + np.array(all_co[poinsf_na[1]])) / 2.0
            ).tolist()

        VNPF = unit_normal(POINSF, all_co[TPFISS[1]], all_co[TPFISS[2]])

        if closedCrack != "OUI":
            if elemType == "SEG2":
                PI1 = TLIPSUP[1][1]
                PF1 = TLIPSUP[NP][1]
            else:
                PI1 = TLIPSUP[1][2]
                PF1 = TLIPSUP[NP][2]

            TVECTEUR[1] = calc_tvect_bord(self, all_co, TPFISS, VNPF, 1, 2, PI1)
            TVECTEUR[NP] = calc_tvect_bord(self, all_co, TPFISS, VNPF, NP, NP - 1, PF1)

            if NP > 2:
                for iNP in range(2, NP):
                    TVECTEUR[iNP] = calc_tvect(self, all_co, TPFISS, VNPF, iNP - 1, iNP, iNP + 1)
        else:
            TVECTEUR[1] = calc_tvect(self, all_co, TPFISS, VNPF, NP, 1, 2)
            TVECTEUR[NP] = calc_tvect(self, all_co, TPFISS, VNPF, NP - 1, NP, 1)

            for iNP in range(2, NP):
                TVECTEUR[iNP] = calc_tvect(self, all_co, TPFISS, VNPF, iNP - 1, iNP, iNP + 1)

        COFF = 100.0
        for iNP in range(NP):
            TVECTEUR[iNP + 1] = (np.array(TVECTEUR[iNP + 1]) / COFF).tolist()

        TVECGLOB = {}

        normVect = []
        for iVect in TVECTEUR.keys():
            normVect.append(np.linalg.norm(TVECTEUR[iVect]))

        for iVect in TVECTEUR.keys():
            TVECGLOB[iVect] = (
                np.array(TVECTEUR[iVect]) * (min(normVect) / normVect[iVect - 1])
            ).tolist()

        #   --------------------------------------------------------------------------
        #   DOMAIN CALCULATION AND CRACK PROPAGATION VECTORS
        #
        if NB_COUCHES < 2:
            UTMESS("F", "RUPTURE4_13")

        else:
            #       -----------------------------------
            #       Domain calculation

            lGroupNo_TMAIL = []
            for iNP in range(NP):
                nameGroupNo = "TMBOUGER" + str(iNP + 1)
                lNode = TPFISS[iNP + 1]
                crea_group_no_from_no(self, MAIL, nameGroupNo, lNode)
                lGroupNo_TMAIL.append("TMBOUGER" + str(iNP + 1))

            crea_group_ma_appui_group_no(self, MAIL, "TMAIL", lGroupNo_TMAIL)
            for iCONT in range(1, NB_COUCHES):
                if elemType == "SEG2":
                    for iNP in range(NP):
                        nameGroupNo = "TMBOUGER" + str(iNP + 1)
                        nameGroupMa = "Block_tem" + str(iNP + 1)
                        crea_group_ma_appui_group_no(self, MAIL, nameGroupMa, nameGroupNo)

                else:
                    for iNP in range((NP + 1) // 2):
                        nameGroupNo = "TMBOUGER" + str(2 * iNP + 1)
                        nameGroupMa = "Block_tem" + str(2 * iNP + 1)
                        crea_group_ma_appui_group_no(self, MAIL, nameGroupMa, nameGroupNo)

                if closedCrack != "OUI":
                    crea_group_ma_appui_group_no(self, MAIL, "Block1", "TMBOUGER1")

                    if elemType == "SEG2":
                        for iNP in range(1, NP - 1):
                            nameGroupMa = "Block" + str(iNP + 1)
                            lMail1 = "Block_tem" + str(iNP + 1)
                            lMail2 = "Block" + str(iNP)
                            diff_group_ma(self, MAIL, nameGroupMa, lMail1, lMail2)

                        for iNP in range(NP - 1):
                            nameGroupNo = "Block" + str(iNP + 1)
                            nameGroupMa = "Block" + str(iNP + 1)
                            crea_group_no_from_group_ma(self, MAIL, nameGroupNo, nameGroupMa)

                        for iNP in range(NP):
                            lMail = "Block_tem" + str(iNP + 1)
                            del_group_ma(self, MAIL, lMail)

                    else:
                        for iNP in range(1, (NP - 1) // 2):
                            nameGroupMa = "Block" + str(2 * iNP + 1)
                            lMail1 = "Block_tem" + str(2 * iNP + 1)
                            lMail2 = "Block" + str(2 * iNP - 1)
                            diff_group_ma(self, MAIL, nameGroupMa, lMail1, lMail2)

                        for iNP in range((NP - 1) // 2):
                            nameGroupNo = "Block" + str(2 * iNP + 1)
                            nameGroupMa = "Block" + str(2 * iNP + 1)
                            crea_group_no_from_group_ma(self, MAIL, nameGroupNo, nameGroupMa)

                        for iNP in range((NP + 1) // 2):
                            lMail = "Block_tem" + str(2 * iNP + 1)
                            del_group_ma(self, MAIL, lMail)

                    if elemType == "SEG2":
                        crea_group_ma_appui_group_no_2d(self, MAIL, "TX1", "TMBOUGER1")
                        crea_group_ma_appui_group_no_2d(self, MAIL, "TX2", "TMBOUGER2")
                        crea_group_ma_appui_group_no_2d(self, MAIL, "TX3", "TMBOUGER" + str(NP))
                        crea_group_ma_appui_group_no_2d(self, MAIL, "TX4", "TMBOUGER" + str(NP - 1))
                    else:
                        crea_group_ma_appui_group_no_2d(self, MAIL, "TX1", "TMBOUGER1")
                        crea_group_ma_appui_group_no_2d(self, MAIL, "TX2", "TMBOUGER3")
                        crea_group_ma_appui_group_no_2d(self, MAIL, "TX3", "TMBOUGER" + str(NP))
                        crea_group_ma_appui_group_no_2d(self, MAIL, "TX4", "TMBOUGER" + str(NP - 2))
                    for iNP in range(NP):
                        lGroupNo = "TMBOUGER" + str(iNP + 1)
                        del_group_no(self, MAIL, lGroupNo)
                    diff_group_ma(self, MAIL, "TMBOUGER1", "TX1", "TX2")
                    diff_group_ma(self, MAIL, "TMBOUGER" + str(NP), "TX3", "TX4")

                    crea_group_no_from_group_ma(self, MAIL, "TMBOUGER1", "TMBOUGER1")
                    crea_group_no_from_group_ma(
                        self, MAIL, "TMBOUGER" + str(NP), "TMBOUGER" + str(NP)
                    )

                    for iTX in ["TX1", "TX2", "TX3", "TX4"]:
                        del_group_ma(self, MAIL, iTX)

                    if elemType == "SEG2":
                        if NP > 2:
                            for iNP in range(1, NP - 1):
                                nameGroupNo = "TMBOUGER" + str(iNP + 1)
                                lNode1 = "Block" + str(iNP)
                                lNode2 = "Block" + str(iNP + 1)
                                intersec_group_no(self, MAIL, nameGroupNo, lNode1, lNode2)

                        for iNP in range(NP - 1):
                            lNode = "Block" + str(iNP + 1)
                            del_group_no(self, MAIL, lNode)
                    else:
                        if NP > 3:
                            for iNP in range(1, (NP - 1) // 2):
                                nameGroupNo = "TMBOUGER" + str(2 * iNP + 1)
                                lNode1 = "Block" + str(2 * iNP - 1)
                                lNode2 = "Block" + str(2 * iNP + 1)
                                intersec_group_no(self, MAIL, nameGroupNo, lNode1, lNode2)
                        for iNP in range(1, (NP + 1) // 2):
                            nameGroupNo = "TMBOUGER" + str(2 * iNP)
                            GroupNo1 = "Block" + str(2 * iNP - 1)
                            GroupNo2 = "TMBOUGER" + str(2 * iNP - 1)
                            GroupNo3 = "TMBOUGER" + str(2 * iNP + 1)
                            nameGroupsNoDiff = (GroupNo1, GroupNo2, GroupNo3)
                            diff_group_no(self, MAIL, nameGroupNo, nameGroupsNoDiff)

                        for iNP in range((NP - 1) // 2):
                            lNode = "Block" + str(2 * iNP + 1)
                            del_group_no(self, MAIL, lNode)
                else:
                    if elemType == "SEG2":
                        nameGroupMa = "Block1"
                        lMail1 = "Block_tem" + str(1)
                        lMail2 = "Block_tem" + str(NP)
                        diff_group_ma(self, MAIL, nameGroupMa, lMail1, lMail2)

                        for iNP in range(1, NP):
                            nameGroupMa = "Block" + str(iNP + 1)
                            lMail1 = "Block_tem" + str(iNP + 1)
                            lMail2 = "Block" + str(iNP)
                            diff_group_ma(self, MAIL, nameGroupMa, lMail1, lMail2)

                        for iNP in range(NP):
                            nameGroupNo = "Block" + str(iNP + 1)
                            nameGroupMa = "Block" + str(iNP + 1)
                            crea_group_no_from_group_ma(self, MAIL, nameGroupNo, nameGroupMa)

                        for iNP in range(NP):
                            lMail = "Block_tem" + str(iNP + 1)
                            del_group_ma(self, MAIL, lMail)
                    else:
                        nameGroupMa = "Block1"
                        lMail1 = "Block_tem" + str(1)
                        lMail2 = "Block_tem" + str(NP - 1)
                        diff_group_ma(self, MAIL, nameGroupMa, lMail1, lMail2)

                        for iNP in range(1, (NP + 1) // 2):
                            nameGroupMa = "Block" + str(2 * iNP + 1)
                            lMail1 = "Block_tem" + str(2 * iNP + 1)
                            lMail2 = "Block" + str(2 * iNP - 1)
                            diff_group_ma(self, MAIL, nameGroupMa, lMail1, lMail2)

                        for iNP in range((NP + 1) // 2):
                            nameGroupNo = "Block" + str(2 * iNP + 1)
                            nameGroupMa = "Block" + str(2 * iNP + 1)
                            crea_group_no_from_group_ma(self, MAIL, nameGroupNo, nameGroupMa)

                        for iNP in range((NP + 1) // 2):
                            lMail = "Block_tem" + str(2 * iNP + 1)
                            del_group_ma(self, MAIL, lMail)

                    for iNP in range(NP):
                        lGroupNo = "TMBOUGER" + str(iNP + 1)
                        del_group_no(self, MAIL, lGroupNo)

                    if elemType == "SEG2":
                        nameGroupNo = "TMBOUGER1"
                        lNode1 = "Block1"
                        lNode2 = "Block" + str(NP)
                        intersec_group_no(self, MAIL, nameGroupNo, lNode1, lNode2)

                        for iNP in range(1, NP):
                            nameGroupNo = "TMBOUGER" + str(iNP + 1)
                            lNode1 = "Block" + str(iNP)
                            lNode2 = "Block" + str(iNP + 1)
                            intersec_group_no(self, MAIL, nameGroupNo, lNode1, lNode2)

                        for iNP in range(NP):
                            lNode = "Block" + str(iNP + 1)
                            del_group_no(self, MAIL, lNode)
                    else:
                        nameGroupNo = "TMBOUGER1"
                        lNode1 = "Block1"
                        lNode2 = "Block" + str(NP - 1)
                        intersec_group_no(self, MAIL, nameGroupNo, lNode1, lNode2)

                        for iNP in range(1, (NP + 1) // 2):
                            nameGroupNo = "TMBOUGER" + str(2 * iNP + 1)
                            lNode1 = "Block" + str(2 * iNP - 1)
                            lNode2 = "Block" + str(2 * iNP + 1)
                            intersec_group_no(self, MAIL, nameGroupNo, lNode1, lNode2)

                        for iNP in range(1, (NP + 1) // 2):
                            nameGroupNo = "TMBOUGER" + str(2 * iNP)
                            GroupNo1 = "Block" + str(2 * iNP - 1)
                            GroupNo2 = "TMBOUGER" + str(2 * iNP - 1)
                            GroupNo3 = "TMBOUGER" + str(2 * iNP + 1)
                            nameGroupsNoDiff = (GroupNo1, GroupNo2, GroupNo3)
                            diff_group_no(self, MAIL, nameGroupNo, nameGroupsNoDiff)

                        nameGroupNo = "TMBOUGER" + str(NP)
                        GroupNo1 = "Block" + str(NP - 1)
                        GroupNo2 = "TMBOUGER" + str(1)
                        GroupNo3 = "TMBOUGER" + str(NP - 1)
                        nameGroupsNoDiff = (GroupNo1, GroupNo2, GroupNo3)
                        diff_group_no(self, MAIL, nameGroupNo, nameGroupsNoDiff)

                        for iNP in range((NP + 1) // 2):
                            lNode = "Block" + str(2 * iNP + 1)
                            del_group_no(self, MAIL, lNode)

                del_group_ma(self, MAIL, "TMAIL")
                crea_group_ma_appui_group_no(self, MAIL, "TMAIL", lGroupNo_TMAIL)

                if j_correction == "OUI" and iCONT == 2:
                    crea_group_ma_appui_group_no(self, MAIL, "TMAIL_CONT3", lGroupNo_TMAIL)

            if j_correction == "OUI":
                diff_group_ma(self, MAIL, "TMAIL_IMPR", "TMAIL", "TMAIL_CONT3")

            ElemsTMAIL = MAIL.getCells("TMAIL")
            listElemTMAIL = [str(iElem + 1) for iElem in ElemsTMAIL]

            #       -----------------------------------
            #       Propagation vectors

            TQ = {}
            TQGLOB = {}
            TLIPSUPCAL = {}
            TLIPINFCAL = {}

            if elemType == "SEG2":
                for iNP in range(NP):
                    TLIPSUPCAL[iNP + 1] = TLIPSUP[iNP + 1][0 : NB_COUCHES + 1]

                    if not is_symmetric:
                        TLIPINFCAL[iNP + 1] = TLIPINF[iNP + 1][0 : NB_COUCHES + 1]

            else:
                for iNP in range((NP + 1) // 2):
                    TLIPSUPCAL[2 * iNP + 1] = TLIPSUP[2 * iNP + 1][0 : 2 * NB_COUCHES + 1]

                    if not is_symmetric:
                        TLIPINFCAL[2 * iNP + 1] = TLIPINF[2 * iNP + 1][0 : 2 * NB_COUCHES + 1]

                if closedCrack != "OUI":
                    for iNP in range(1, (NP + 1) // 2):
                        TLIPSUPCAL[2 * iNP] = TLIPSUP[2 * iNP][0 : NB_COUCHES + 1]

                        if not is_symmetric:
                            TLIPINFCAL[2 * iNP] = TLIPINF[2 * iNP][0 : NB_COUCHES + 1]

                else:
                    for iNP in range(1, NP // 2 + 1):
                        TLIPSUPCAL[2 * iNP] = TLIPSUP[2 * iNP][0 : NB_COUCHES + 1]

                        if not is_symmetric:
                            TLIPINFCAL[2 * iNP] = TLIPINF[2 * iNP][0 : NB_COUCHES + 1]

            if elemType == "SEG2":
                if is_symmetric:
                    if closedCrack != "OUI":
                        #                   ---------------
                        #                   TQ[1]

                        NODESBOUGE = [int(iNo) - 1 for iNo in TLIPSUPCAL[1][0:NB_COUCHES]]

                        XAIRE = calc_vari_area_no_bord(
                            self,
                            MAIL,
                            NB_COUCHES,
                            TLIPSUPCAL[1],
                            TLIPSUPCAL[2],
                            NODESBOUGE,
                            TVECTEUR[1],
                            is_symmetric,
                        )

                        TQ[1] = (np.array(TVECTEUR[1]) * XMULT / XAIRE).tolist()

                        #                   ---------------
                        #                   TQ[NP]

                        NODESBOUGE = [int(iNo) - 1 for iNo in TLIPSUPCAL[NP][0:NB_COUCHES]]

                        XAIRE = calc_vari_area_no_bord(
                            self,
                            MAIL,
                            NB_COUCHES,
                            TLIPSUPCAL[NP],
                            TLIPSUPCAL[NP - 1],
                            NODESBOUGE,
                            TVECTEUR[NP],
                            is_symmetric,
                        )

                        TQ[NP] = (np.array(TVECTEUR[NP]) * XMULT / XAIRE).tolist()

                        #                   ---------------
                        #                   TQ[iNP]

                        if NP > 2:
                            for iNP in range(1, NP - 1):
                                NODESBOUGE = [
                                    int(iNo) - 1 for iNo in TLIPSUPCAL[iNP + 1][0:NB_COUCHES]
                                ]

                                XAIRE = calc_vari_area_no_midd(
                                    self,
                                    MAIL,
                                    NB_COUCHES,
                                    TLIPSUPCAL[iNP + 1],
                                    NODESBOUGE,
                                    TVECTEUR[iNP + 1],
                                    is_symmetric,
                                    closedCrack,
                                    lipSupName,
                                    lipInfName,
                                )

                                TQ[iNP + 1] = (np.array(TVECTEUR[iNP + 1]) * XMULT / XAIRE).tolist()

                        #                   ---------------
                        #                   TQ['GLOBAL']

                        NODESBOUGE = {}
                        for iKey in TLIPSUPCAL.keys():
                            NODESBOUGE[iKey] = [
                                int(iNo) - 1 for iNo in TLIPSUPCAL[iKey][0:NB_COUCHES]
                            ]

                        if NP == 2:
                            XAIRE = calc_vari_area_no_glob_one_elem(
                                self,
                                MAIL,
                                NB_COUCHES,
                                NP,
                                TLIPSUPCAL,
                                NODESBOUGE,
                                TVECGLOB,
                                is_symmetric,
                            )
                        else:
                            XAIRE = calc_vari_area_no_glob(
                                self,
                                MAIL,
                                NB_COUCHES,
                                NP,
                                TLIPSUPCAL,
                                NODESBOUGE,
                                TVECGLOB,
                                is_symmetric,
                                closedCrack,
                                lipSupName,
                                lipInfName,
                            )

                        for iKey in TVECGLOB.keys():
                            TQGLOB[iKey] = (np.array(TVECGLOB[iKey]) * XMULT / XAIRE).tolist()

                    else:
                        #                   ---------------
                        #                   TQ[iNP]

                        for iNP in range(NP):
                            NODESBOUGE = [int(iNo) - 1 for iNo in TLIPSUPCAL[iNP + 1][0:NB_COUCHES]]

                            XAIRE = calc_vari_area_no_midd(
                                self,
                                MAIL,
                                NB_COUCHES,
                                TLIPSUPCAL[iNP + 1],
                                NODESBOUGE,
                                TVECTEUR[iNP + 1],
                                is_symmetric,
                                closedCrack,
                                lipSupName,
                                lipInfName,
                            )

                            TQ[iNP + 1] = (np.array(TVECTEUR[iNP + 1]) * XMULT / XAIRE).tolist()

                        #                   ---------------
                        #                   TQ['GLOBAL']

                        NODESBOUGE = {}
                        for iKey in TLIPSUPCAL.keys():
                            NODESBOUGE[iKey] = [
                                int(iNo) - 1 for iNo in TLIPSUPCAL[iKey][0:NB_COUCHES]
                            ]

                        XAIRE = calc_vari_area_no_glob(
                            self,
                            MAIL,
                            NB_COUCHES,
                            NP,
                            TLIPSUPCAL,
                            NODESBOUGE,
                            TVECGLOB,
                            is_symmetric,
                            closedCrack,
                            lipSupName,
                            lipInfName,
                        )

                        for iKey in TVECGLOB.keys():
                            TQGLOB[iKey] = (np.array(TVECGLOB[iKey]) * XMULT / XAIRE).tolist()

                else:
                    if closedCrack != "OUI":
                        #                   ---------------
                        #                   TQ[1]

                        NODESBOUGE = [
                            int(iNo) - 1
                            for iNo in TLIPSUPCAL[1][0:NB_COUCHES] + TLIPINFCAL[1][1:NB_COUCHES]
                        ]

                        XAIRE = calc_vari_area_no_bord(
                            self,
                            MAIL,
                            NB_COUCHES,
                            (TLIPSUPCAL[1], TLIPINFCAL[1]),
                            (TLIPSUPCAL[2], TLIPINFCAL[2]),
                            NODESBOUGE,
                            TVECTEUR[1],
                            is_symmetric,
                        )

                        TQ[1] = (np.array(TVECTEUR[1]) * XMULT / XAIRE).tolist()

                        #                   ---------------
                        #                   TQ[NP]

                        NODESBOUGE = [
                            int(iNo) - 1
                            for iNo in TLIPSUPCAL[NP][0:NB_COUCHES] + TLIPINFCAL[NP][1:NB_COUCHES]
                        ]

                        XAIRE = calc_vari_area_no_bord(
                            self,
                            MAIL,
                            NB_COUCHES,
                            (TLIPSUPCAL[NP], TLIPINFCAL[NP]),
                            (TLIPSUPCAL[NP - 1], TLIPINFCAL[NP - 1]),
                            NODESBOUGE,
                            TVECTEUR[NP],
                            is_symmetric,
                        )

                        TQ[NP] = (np.array(TVECTEUR[NP]) * XMULT / XAIRE).tolist()

                        #                   ---------------
                        #                   TQ[iNP]

                        if NP > 2:
                            for iNP in range(1, NP - 1):
                                NODESBOUGE = [
                                    int(iNo) - 1
                                    for iNo in TLIPSUPCAL[iNP + 1][0:NB_COUCHES]
                                    + TLIPINFCAL[iNP + 1][1:NB_COUCHES]
                                ]

                                XAIRE = calc_vari_area_no_midd(
                                    self,
                                    MAIL,
                                    NB_COUCHES,
                                    (TLIPSUPCAL[iNP + 1], TLIPINFCAL[iNP + 1]),
                                    NODESBOUGE,
                                    TVECTEUR[iNP + 1],
                                    is_symmetric,
                                    closedCrack,
                                    lipSupName,
                                    lipInfName,
                                )

                                TQ[iNP + 1] = (np.array(TVECTEUR[iNP + 1]) * XMULT / XAIRE).tolist()

                        #                   ---------------
                        #                   TQ['GLOBAL']

                        NODESBOUGE = {}
                        for iKey in TLIPSUPCAL.keys():
                            NODESBOUGE[iKey] = [
                                int(iNo) - 1
                                for iNo in TLIPSUPCAL[iKey][0:NB_COUCHES]
                                + TLIPINFCAL[iKey][1:NB_COUCHES]
                            ]

                        if NP == 2:
                            XAIRE = calc_vari_area_no_glob_one_elem(
                                self,
                                MAIL,
                                NB_COUCHES,
                                NP,
                                (TLIPSUPCAL, TLIPINFCAL),
                                NODESBOUGE,
                                TVECGLOB,
                                is_symmetric,
                            )
                        else:
                            XAIRE = calc_vari_area_no_glob(
                                self,
                                MAIL,
                                NB_COUCHES,
                                NP,
                                (TLIPSUPCAL, TLIPINFCAL),
                                NODESBOUGE,
                                TVECGLOB,
                                is_symmetric,
                                closedCrack,
                                lipSupName,
                                lipInfName,
                            )

                        for iKey in TVECGLOB.keys():
                            TQGLOB[iKey] = (np.array(TVECGLOB[iKey]) * XMULT / XAIRE).tolist()

                    else:
                        #                   ---------------
                        #                   TQ[iNP]

                        for iNP in range(NP):
                            NODESBOUGE = [
                                int(iNo) - 1
                                for iNo in TLIPSUPCAL[iNP + 1][0:NB_COUCHES]
                                + TLIPINFCAL[iNP + 1][1:NB_COUCHES]
                            ]

                            XAIRE = calc_vari_area_no_midd(
                                self,
                                MAIL,
                                NB_COUCHES,
                                (TLIPSUPCAL[iNP + 1], TLIPINFCAL[iNP + 1]),
                                NODESBOUGE,
                                TVECTEUR[iNP + 1],
                                is_symmetric,
                                closedCrack,
                                lipSupName,
                                lipInfName,
                            )

                            TQ[iNP + 1] = (np.array(TVECTEUR[iNP + 1]) * XMULT / XAIRE).tolist()

                        #                   ---------------
                        #                   TQ['GLOBAL']

                        NODESBOUGE = {}
                        for iKey in TLIPSUPCAL.keys():
                            NODESBOUGE[iKey] = [
                                int(iNo) - 1
                                for iNo in TLIPSUPCAL[iKey][0:NB_COUCHES]
                                + TLIPINFCAL[iKey][1:NB_COUCHES]
                            ]

                        XAIRE = calc_vari_area_no_glob(
                            self,
                            MAIL,
                            NB_COUCHES,
                            NP,
                            (TLIPSUPCAL, TLIPINFCAL),
                            NODESBOUGE,
                            TVECGLOB,
                            is_symmetric,
                            closedCrack,
                            lipSupName,
                            lipInfName,
                        )

                        for iKey in TVECGLOB.keys():
                            TQGLOB[iKey] = (np.array(TVECGLOB[iKey]) * XMULT / XAIRE).tolist()

            else:
                if is_symmetric:
                    if closedCrack != "OUI":
                        #                   ---------------
                        #                   TQ[1]

                        NODESBOUGE = [int(iNo) - 1 for iNo in TLIPSUPCAL[1][0 : 2 * NB_COUCHES - 1]]

                        XAIRE = calc_vari_area_no_bord(
                            self,
                            MAIL,
                            NB_COUCHES,
                            TLIPSUPCAL[1],
                            TLIPSUPCAL[3],
                            NODESBOUGE,
                            TVECTEUR[1],
                            is_symmetric,
                        )

                        TQ[1] = (np.array(TVECTEUR[1]) * XMULT / XAIRE).tolist()

                        #                   ---------------
                        #                   TQ[NP]

                        NODESBOUGE = [
                            int(iNo) - 1 for iNo in TLIPSUPCAL[NP][0 : 2 * NB_COUCHES - 1]
                        ]

                        XAIRE = calc_vari_area_no_bord(
                            self,
                            MAIL,
                            NB_COUCHES,
                            TLIPSUPCAL[NP],
                            TLIPSUPCAL[NP - 2],
                            NODESBOUGE,
                            TVECTEUR[NP],
                            is_symmetric,
                        )

                        TQ[NP] = (np.array(TVECTEUR[NP]) * XMULT / XAIRE).tolist()

                        #                   ---------------
                        #                   TQ[2*iNP+1]

                        if NP > 3:
                            for iNP in range(1, (NP - 1) // 2):
                                NODESBOUGE = [
                                    int(iNo) - 1
                                    for iNo in TLIPSUPCAL[2 * iNP + 1][0 : 2 * NB_COUCHES - 1]
                                ]

                                XAIRE = calc_vari_area_no_midd(
                                    self,
                                    MAIL,
                                    NB_COUCHES,
                                    TLIPSUPCAL[2 * iNP + 1],
                                    NODESBOUGE,
                                    TVECTEUR[2 * iNP + 1],
                                    is_symmetric,
                                    closedCrack,
                                    lipSupName,
                                    lipInfName,
                                )

                                TQ[2 * iNP + 1] = (
                                    np.array(TVECTEUR[2 * iNP + 1]) * XMULT / XAIRE
                                ).tolist()

                        #                   ---------------
                        #                   TQ[2*iNP]

                        for iNP in range(1, (NP + 1) // 2):
                            NODESBOUGE = [int(iNo) - 1 for iNo in TLIPSUPCAL[2 * iNP][0:NB_COUCHES]]

                            XAIRE = calc_vari_area_no_midd(
                                self,
                                MAIL,
                                NB_COUCHES,
                                TLIPSUPCAL[2 * iNP],
                                NODESBOUGE,
                                TVECTEUR[2 * iNP],
                                is_symmetric,
                                closedCrack,
                                lipSupName,
                                lipInfName,
                            )

                            TQ[2 * iNP] = (np.array(TVECTEUR[2 * iNP]) * XMULT / XAIRE).tolist()

                        #                   ---------------
                        #                   TQ['GLOBAL']

                        NODESBOUGE = {}
                        for iKey in range((NP + 1) // 2):
                            NODESBOUGE[2 * iKey + 1] = [
                                int(iNo) - 1
                                for iNo in TLIPSUPCAL[2 * iKey + 1][0 : 2 * NB_COUCHES - 1]
                            ]
                            if iKey > 0:
                                NODESBOUGE[2 * iKey] = [
                                    int(iNo) - 1 for iNo in TLIPSUPCAL[2 * iKey][0:NB_COUCHES]
                                ]

                        if NP == 3:
                            XAIRE = calc_vari_area_no_glob_one_elem(
                                self,
                                MAIL,
                                NB_COUCHES,
                                NP,
                                TLIPSUPCAL,
                                NODESBOUGE,
                                TVECGLOB,
                                is_symmetric,
                            )
                        else:
                            XAIRE = calc_vari_area_no_glob(
                                self,
                                MAIL,
                                NB_COUCHES,
                                NP,
                                TLIPSUPCAL,
                                NODESBOUGE,
                                TVECGLOB,
                                is_symmetric,
                                closedCrack,
                                lipSupName,
                                lipInfName,
                            )

                        for iKey in TVECGLOB.keys():
                            TQGLOB[iKey] = (np.array(TVECGLOB[iKey]) * XMULT / XAIRE).tolist()

                    else:
                        #                   ---------------
                        #                   TQ[2*iNP+1]

                        for iNP in range((NP + 1) // 2):
                            NODESBOUGE = [
                                int(iNo) - 1
                                for iNo in TLIPSUPCAL[2 * iNP + 1][0 : 2 * NB_COUCHES - 1]
                            ]
                            XAIRE = calc_vari_area_no_midd(
                                self,
                                MAIL,
                                NB_COUCHES,
                                TLIPSUPCAL[2 * iNP + 1],
                                NODESBOUGE,
                                TVECTEUR[2 * iNP + 1],
                                is_symmetric,
                                closedCrack,
                                lipSupName,
                                lipInfName,
                            )

                            TQ[2 * iNP + 1] = (
                                np.array(TVECTEUR[2 * iNP + 1]) * XMULT / XAIRE
                            ).tolist()

                        #                   ---------------
                        #                   TQ[2*iNP]

                        for iNP in range(1, NP // 2 + 1):
                            NODESBOUGE = [int(iNo) - 1 for iNo in TLIPSUPCAL[2 * iNP][0:NB_COUCHES]]

                            XAIRE = calc_vari_area_no_midd(
                                self,
                                MAIL,
                                NB_COUCHES,
                                TLIPSUPCAL[2 * iNP],
                                NODESBOUGE,
                                TVECTEUR[2 * iNP],
                                is_symmetric,
                                closedCrack,
                                lipSupName,
                                lipInfName,
                            )

                            TQ[2 * iNP] = (np.array(TVECTEUR[2 * iNP]) * XMULT / XAIRE).tolist()

                        #                   ---------------
                        #                   TQ['GLOBAL']

                        NODESBOUGE = {}
                        for iKey in range((NP + 1) // 2):
                            NODESBOUGE[2 * iKey + 1] = [
                                int(iNo) - 1
                                for iNo in TLIPSUPCAL[2 * iKey + 1][0 : 2 * NB_COUCHES - 1]
                            ]

                        for iKey in range(1, NP // 2 + 1):
                            NODESBOUGE[2 * iKey] = [
                                int(iNo) - 1 for iNo in TLIPSUPCAL[2 * iKey][0:NB_COUCHES]
                            ]

                        XAIRE = calc_vari_area_no_glob(
                            self,
                            MAIL,
                            NB_COUCHES,
                            NP,
                            TLIPSUPCAL,
                            NODESBOUGE,
                            TVECGLOB,
                            is_symmetric,
                            closedCrack,
                            lipSupName,
                            lipInfName,
                        )

                        for iKey in TVECGLOB.keys():
                            TQGLOB[iKey] = (np.array(TVECGLOB[iKey]) * XMULT / XAIRE).tolist()

                else:
                    if closedCrack != "OUI":
                        #                   ---------------
                        #                   TQ[1]

                        NODESBOUGE = [
                            int(iNo) - 1
                            for iNo in TLIPSUPCAL[1][0 : 2 * NB_COUCHES - 1]
                            + TLIPINFCAL[1][1 : 2 * NB_COUCHES - 1]
                        ]

                        XAIRE = calc_vari_area_no_bord(
                            self,
                            MAIL,
                            NB_COUCHES,
                            (TLIPSUPCAL[1], TLIPINFCAL[1]),
                            (TLIPSUPCAL[3], TLIPINFCAL[3]),
                            NODESBOUGE,
                            TVECTEUR[1],
                            is_symmetric,
                        )

                        TQ[1] = (np.array(TVECTEUR[1]) * XMULT / XAIRE).tolist()

                        #                   ---------------
                        #                   TQ[NP]

                        NODESBOUGE = [
                            int(iNo) - 1
                            for iNo in TLIPSUPCAL[NP][0 : 2 * NB_COUCHES - 1]
                            + TLIPINFCAL[NP][1 : 2 * NB_COUCHES - 1]
                        ]

                        XAIRE = calc_vari_area_no_bord(
                            self,
                            MAIL,
                            NB_COUCHES,
                            (TLIPSUPCAL[NP], TLIPINFCAL[NP]),
                            (TLIPSUPCAL[NP - 2], TLIPINFCAL[NP - 2]),
                            NODESBOUGE,
                            TVECTEUR[NP],
                            is_symmetric,
                        )

                        TQ[NP] = (np.array(TVECTEUR[NP]) * XMULT / XAIRE).tolist()

                        #                   ---------------
                        #                   TQ[2*iNP+1]

                        if NP > 3:
                            for iNP in range(1, (NP - 1) // 2):
                                NODESBOUGE = [
                                    int(iNo) - 1
                                    for iNo in TLIPSUPCAL[2 * iNP + 1][0:NB_COUCHES]
                                    + TLIPINFCAL[2 * iNP + 1][1:NB_COUCHES]
                                ]

                                XAIRE = calc_vari_area_no_midd(
                                    self,
                                    MAIL,
                                    NB_COUCHES,
                                    (TLIPSUPCAL[2 * iNP + 1], TLIPINFCAL[2 * iNP + 1]),
                                    NODESBOUGE,
                                    TVECTEUR[2 * iNP + 1],
                                    is_symmetric,
                                    closedCrack,
                                    lipSupName,
                                    lipInfName,
                                )

                                TQ[2 * iNP + 1] = (
                                    np.array(TVECTEUR[2 * iNP + 1]) * XMULT / XAIRE
                                ).tolist()

                        #                   ---------------
                        #                   TQ[2*iNP]

                        for iNP in range(1, (NP + 1) // 2):
                            NODESBOUGE = [
                                int(iNo) - 1
                                for iNo in TLIPSUPCAL[2 * iNP][0:NB_COUCHES]
                                + TLIPINFCAL[2 * iNP][1:NB_COUCHES]
                            ]

                            XAIRE = calc_vari_area_no_midd(
                                self,
                                MAIL,
                                NB_COUCHES,
                                (TLIPSUPCAL[2 * iNP], TLIPINFCAL[2 * iNP]),
                                NODESBOUGE,
                                TVECTEUR[2 * iNP],
                                is_symmetric,
                                closedCrack,
                                lipSupName,
                                lipInfName,
                            )

                            TQ[2 * iNP] = (np.array(TVECTEUR[2 * iNP]) * XMULT / XAIRE).tolist()

                        #                   ---------------
                        #                   TQ['GLOBAL']

                        NODESBOUGE = {}
                        for iKey in range((NP + 1) // 2):
                            NODESBOUGE[2 * iKey + 1] = [
                                int(iNo) - 1
                                for iNo in TLIPSUPCAL[2 * iKey + 1][0 : 2 * NB_COUCHES - 1]
                                + TLIPINFCAL[2 * iKey + 1][1 : 2 * NB_COUCHES - 1]
                            ]
                            if iKey > 0:
                                NODESBOUGE[2 * iKey] = [
                                    int(iNo) - 1
                                    for iNo in TLIPSUPCAL[2 * iKey][0:NB_COUCHES]
                                    + TLIPINFCAL[2 * iKey][1:NB_COUCHES]
                                ]

                        if NP == 3:
                            XAIRE = calc_vari_area_no_glob_one_elem(
                                self,
                                MAIL,
                                NB_COUCHES,
                                NP,
                                (TLIPSUPCAL, TLIPINFCAL),
                                NODESBOUGE,
                                TVECGLOB,
                                is_symmetric,
                            )
                        else:
                            XAIRE = calc_vari_area_no_glob(
                                self,
                                MAIL,
                                NB_COUCHES,
                                NP,
                                (TLIPSUPCAL, TLIPINFCAL),
                                NODESBOUGE,
                                TVECGLOB,
                                is_symmetric,
                                closedCrack,
                                lipSupName,
                                lipInfName,
                            )

                        for iKey in TVECGLOB.keys():
                            TQGLOB[iKey] = (np.array(TVECGLOB[iKey]) * XMULT / XAIRE).tolist()

                    else:
                        #                   ---------------
                        #                   TQ[2*iNP+1]

                        for iNP in range((NP + 1) // 2):
                            NODESBOUGE = [
                                int(iNo) - 1
                                for iNo in TLIPSUPCAL[2 * iNP + 1][0:NB_COUCHES]
                                + TLIPINFCAL[2 * iNP + 1][1:NB_COUCHES]
                            ]

                            XAIRE = calc_vari_area_no_midd(
                                self,
                                MAIL,
                                NB_COUCHES,
                                (TLIPSUPCAL[2 * iNP + 1], TLIPINFCAL[2 * iNP + 1]),
                                NODESBOUGE,
                                TVECTEUR[2 * iNP + 1],
                                is_symmetric,
                                closedCrack,
                                lipSupName,
                                lipInfName,
                            )

                            TQ[2 * iNP + 1] = (
                                np.array(TVECTEUR[2 * iNP + 1]) * XMULT / XAIRE
                            ).tolist()

                        #                   ---------------
                        #                   TQ[2*iNP]

                        for iNP in range(1, NP // 2 + 1):
                            NODESBOUGE = [
                                int(iNo) - 1
                                for iNo in TLIPSUPCAL[2 * iNP][0:NB_COUCHES]
                                + TLIPINFCAL[2 * iNP][1:NB_COUCHES]
                            ]

                            XAIRE = calc_vari_area_no_midd(
                                self,
                                MAIL,
                                NB_COUCHES,
                                (TLIPSUPCAL[2 * iNP], TLIPINFCAL[2 * iNP]),
                                NODESBOUGE,
                                TVECTEUR[2 * iNP],
                                is_symmetric,
                                closedCrack,
                                lipSupName,
                                lipInfName,
                            )

                            TQ[2 * iNP] = (np.array(TVECTEUR[2 * iNP]) * XMULT / XAIRE).tolist()

                        #                   ---------------
                        #                   TQ['GLOBAL']

                        NODESBOUGE = {}
                        for iKey in range((NP + 1) // 2):
                            NODESBOUGE[2 * iKey + 1] = [
                                int(iNo) - 1
                                for iNo in TLIPSUPCAL[2 * iKey + 1][0 : 2 * NB_COUCHES - 1]
                                + TLIPINFCAL[2 * iKey + 1][1 : 2 * NB_COUCHES - 1]
                            ]

                        for iKey in range(1, NP // 2 + 1):
                            NODESBOUGE[2 * iKey] = [
                                int(iNo) - 1
                                for iNo in TLIPSUPCAL[2 * iKey][0:NB_COUCHES]
                                + TLIPINFCAL[2 * iKey][1:NB_COUCHES]
                            ]

                        XAIRE = calc_vari_area_no_glob(
                            self,
                            MAIL,
                            NB_COUCHES,
                            NP,
                            (TLIPSUPCAL, TLIPINFCAL),
                            NODESBOUGE,
                            TVECGLOB,
                            is_symmetric,
                            closedCrack,
                            lipSupName,
                            lipInfName,
                        )

                        for iKey in TVECGLOB.keys():
                            TQGLOB[iKey] = (np.array(TVECGLOB[iKey]) * XMULT / XAIRE).tolist()

        #   --------------------------------------------------------------------------
        #   GET CALCULATED INSTANTS
        #
        dico = __RESU.getAccessParameters()

        if INST is not None:
            PRECISION = args["PRECISION"]
        else:
            PRECISION = None

        lOrd, lInst = list_inst_calc(self, dico, NUME_ORDRE, INST, PRECISION)

        #   --------------------------------------------------------------------------
        #   GET CALCULATED NODES OF CRACK FRONT
        #
        # GROUP_NO = args['GROUP_NO']
        # print(args)
        # print("GROUP_NO from cmd file",GROUP_NO)

        if GROUP_NO is not None:
            # print("collgrno keys",collgrno.keys())
            # print("collgrno ",collgrno)
            # print("cnom ",cnom)

            for knodes in MAIL.getGroupsOfNodes:
                for incr_gno in range(len(GROUP_NO)):
                    # print("GROUP_NO",GROUP_NO[incr_gno], knodes.strip())
                    # print("incr_gno",incr_gno)

                    if GROUP_NO[incr_gno] == knodes:
                        # print("collgrno[knodes]  ",collgrno[knodes])

                        LIST_NODE__ = [
                            str(node + 1) for node in MAIL.getNodes(knodes, localNumbering=True)
                        ]
                        # print("LIST_NODE__  ",LIST_NODE__)

                        if incr_gno == 0:
                            LIST_NODE = LIST_NODE__
                            # print("LIST_NODE  ",LIST_NODE)
                        elif incr_gno >= 1:
                            LIST_NODE = LIST_NODE.extend(LIST_NODE__)
                            # print("LIST_NODE  ",LIST_NODE)

        else:
            LIST_NODE = None

        # print("LIST_NODE  ",LIST_NODE)
        # print("NB_POINT_FOND  ",NB_POINT_FOND)

        listNP = list_node_calc(self, LIST_NODE, NB_POINT_FOND, TPFISS, NP)

        #   --------------------------------------------------------------------------
        #   COMPUTATION J-INTEGRAL
        #
        #   LOOP ON THE INSTANTS
        #
        SIG_CMP = ["SIXX", "SIYY", "SIZZ", "SIXY", "SIXZ", "SIYZ"]
        EPS_CMP = ["EPXX", "EPYY", "EPZZ", "EPXY", "EPXZ", "EPYZ"]

        for iord, inst in enumerate(lInst):
            __SIGF = get_contraint(self, __RESU, inst)

            __DEPINT = get_displacement(self, __RESU, inst)

            __GDEPX = grad_u(self, MAIL, MODE, MATE, ["DX", "0.", "0."], __DEPINT, inst)
            __GDEPY = grad_u(self, MAIL, MODE, MATE, ["0.", "DY", "0."], __DEPINT, inst)
            __GDEPZ = grad_u(self, MAIL, MODE, MATE, ["0.", "0.", "DZ"], __DEPINT, inst)

            if ETAT_INIT is None:
                __WELAS = get_strain_energy(self, __RESU, inst)

                __WELAS = CREA_CHAMP(
                    OPERATION="ASSE",
                    TYPE_CHAM="ELGA_NEUT_R",
                    MODELE=MODE,
                    PROL_ZERO="OUI",
                    ASSE=(
                        _F(TOUT="OUI", CHAM_GD=__WELAS, NOM_CMP=("TOTALE",), NOM_CMP_RESU=("X13",)),
                    ),
                )

                if OPTION == "JMOD":
                    __EPSI_ELGA = get_deformation(self, __RESU, "ELGA", inst)

            else:
                __EPSI_TOTA = get_deformation(self, __RESU, "ELGA", inst)

                DATA_INIT = ETAT_INIT[0]
                # print ("^^^^^^^^^^^^^^^^^^^^^^")
                # print ("dir EPSI_INIT",dir(DATA_INIT['EPSI']))
                # print ("dir EPSI_INIT",DATA_INIT['EPSI'].keys()))
                # print ("Type EPSI_INIT",type(DATA_INIT['EPSI']))

                __EPSI_INIT = DATA_INIT["EPSI"]
                # print ("Type EPSI_INIT",__EPSI_INIT.getType())
                # print ("Name EPSI_INIT",__EPSI_INIT.getName())

                # __EPSI_INIT = DATA_INIT[DATA_INIT.keys()[0]]

                # if __EPSI_INIT['TYPE_CHAM'][:4] == 'ELGA':
                if __EPSI_INIT.getType() == "CHAM_ELEM":
                    __EPS0_ELGA = __EPSI_INIT

                else:
                    __EPS0_ELGA = CREA_CHAMP(
                        TYPE_CHAM="ELGA_EPSI_R", OPERATION="DISC", MODELE=MODE, CHAM_GD=__EPSI_INIT
                    )

                __EPSI_ELGA = CREA_CHAMP(
                    TYPE_CHAM="ELGA_EPSI_R",
                    OPERATION="ASSE",
                    MODELE=MODE,
                    ASSE=(
                        _F(CHAM_GD=__EPSI_TOTA, TOUT="OUI", CUMUL="OUI", COEF_R=1.0),
                        _F(CHAM_GD=__EPS0_ELGA, TOUT="OUI", CUMUL="OUI", COEF_R=-1.0),
                    ),
                )

                __WELAS = cal_strain_energy(self, MODE, __EPSI_ELGA, __SIGF)

            #       ----------------------------------------------------------------------
            #       INITIAL STRAIN - GRADIENT
            #
            if ETAT_INIT is not None:
                #           ------------------------------------------------------------------
                #           J03: GRAD EPS0

                if grad_elno_type_j03 == "OUI":
                    __EPS0_ELNO = CREA_CHAMP(
                        TYPE_CHAM="ELNO_EPSI_R", OPERATION="DISC", MODELE=MODE, CHAM_GD=__EPS0_ELGA
                    )

                else:
                    __EPS0_NOEU = CREA_CHAMP(
                        TYPE_CHAM="NOEU_EPSI_R", OPERATION="DISC", MODELE=MODE, CHAM_GD=__EPS0_ELGA
                    )

                dicGradEps0 = {}

                for iEPS_CMP in EPS_CMP:
                    if grad_elno_type_j03 == "OUI":
                        __EPS0_CAL = __EPS0_ELNO.getValuesWithDescription(iEPS_CMP, ["TMAIL"])

                        __GRAD_EPS0 = grad_elno(
                            self, MAIL, MODE, MATE, listElemTMAIL, __EPS0_ELGA, __EPS0_CAL, inst
                        )

                    else:
                        __EPS0_CAL = CREA_CHAMP(
                            OPERATION="ASSE",
                            MODELE=MODE,
                            TYPE_CHAM="NOEU_DEPL_R",
                            ASSE=(
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__EPS0_NOEU,
                                    NOM_CMP=(iEPS_CMP,),
                                    NOM_CMP_RESU=("DX",),
                                ),
                            ),
                        )

                        __GRAD_EPS0 = grad_noeu(self, MAIL, MODE, MATE, __EPS0_CAL, inst)

                    dicGradEps0[iEPS_CMP] = __GRAD_EPS0

            #       ----------------------------------------------------------------------
            #       MODIFIED J - GRADIENT
            #
            if OPTION == "JMOD":
                #           ------------------------------------------------------------------
                #           J04: GRAD EPSI

                if grad_elno_type_j04 == "OUI":
                    __EPSI_ELNO = CREA_CHAMP(
                        TYPE_CHAM="ELNO_EPSI_R", OPERATION="DISC", MODELE=MODE, CHAM_GD=__EPSI_ELGA
                    )

                else:
                    __EPSI_NOEU = CREA_CHAMP(
                        TYPE_CHAM="NOEU_EPSI_R", OPERATION="DISC", MODELE=MODE, CHAM_GD=__EPSI_ELGA
                    )

                dicGradEps = {}

                for iEPS_CMP in EPS_CMP:
                    if grad_elno_type_j04 == "OUI":
                        __EPSI_CAL = __EPSI_ELNO.getValuesWithDescription(iEPS_CMP, ["TMAIL"])

                        __GRAD_EPSI = grad_elno(
                            self, MAIL, MODE, MATE, listElemTMAIL, __EPSI_ELGA, __EPSI_CAL, inst
                        )

                    else:
                        __EPSI_CAL = CREA_CHAMP(
                            OPERATION="ASSE",
                            MODELE=MODE,
                            TYPE_CHAM="NOEU_DEPL_R",
                            ASSE=(
                                _F(
                                    TOUT="OUI",
                                    CHAM_GD=__EPSI_NOEU,
                                    NOM_CMP=(iEPS_CMP,),
                                    NOM_CMP_RESU=("DX",),
                                ),
                            ),
                        )

                        __GRAD_EPSI = grad_noeu(self, MAIL, MODE, MATE, __EPSI_CAL, inst)

                    dicGradEps[iEPS_CMP] = __GRAD_EPSI

                #           ------------------------------------------------------------------
                #           J05: GRAD W

                __WELASV = CREA_CHAMP(
                    OPERATION="ASSE",
                    TYPE_CHAM="ELGA_VARI_R",
                    MODELE=MODE,
                    ASSE=(_F(TOUT="OUI", CHAM_GD=__WELAS, NOM_CMP=("X13",), NOM_CMP_RESU=("V1",)),),
                )

                if grad_elno_type_j05 == "OUI":
                    __WELAS_ELNO = CREA_CHAMP(
                        TYPE_CHAM="ELNO_VARI_R", OPERATION="DISC", MODELE=MODE, CHAM_GD=__WELASV
                    )

                    __WELAS_CAL = __WELAS_ELNO.getValuesWithDescription("V1", ["TMAIL"])

                    __GRAD_WELAS = grad_elno(
                        self, MAIL, MODE, MATE, listElemTMAIL, __EPSI_ELGA, __WELAS_CAL, inst
                    )

                else:
                    __WELAS_NOEU = CREA_CHAMP(
                        TYPE_CHAM="NOEU_VAR2_R", OPERATION="DISC", MODELE=MODE, CHAM_GD=__WELASV
                    )

                    __WELAS_CAL = CREA_CHAMP(
                        OPERATION="ASSE",
                        MODELE=MODE,
                        TYPE_CHAM="NOEU_DEPL_R",
                        ASSE=(
                            _F(
                                TOUT="OUI",
                                CHAM_GD=__WELAS_NOEU,
                                NOM_CMP=("V1",),
                                NOM_CMP_RESU=("DX",),
                            ),
                        ),
                    )

                    __GRAD_WELAS = grad_noeu(self, MAIL, MODE, MATE, __WELAS_CAL, inst)

            #       ----------------------------------------------------------------------
            #       LOOP ON THE CALCULATED NODES OF CRACK FRONT
            #
            for iNP in listNP:
                display_node_inst(FOND_FISS, iNP, inst, NB_COUCHES, NP, closedCrack)

                if iNP < NP:
                    __GQX = grad_q(
                        self,
                        MAIL,
                        MODE,
                        MATE,
                        "TMBOUGER" + str(iNP + 1),
                        "DX",
                        TQ[iNP + 1][0],
                        inst,
                    )
                    __GQY = grad_q(
                        self,
                        MAIL,
                        MODE,
                        MATE,
                        "TMBOUGER" + str(iNP + 1),
                        "DY",
                        TQ[iNP + 1][1],
                        inst,
                    )
                    __GQZ = grad_q(
                        self,
                        MAIL,
                        MODE,
                        MATE,
                        "TMBOUGER" + str(iNP + 1),
                        "DZ",
                        TQ[iNP + 1][2],
                        inst,
                    )

                else:
                    __GQX = grad_q_glob(self, MAIL, MODE, MATE, NP, "DX", TQGLOB, 0, inst)
                    __GQY = grad_q_glob(self, MAIL, MODE, MATE, NP, "DY", TQGLOB, 1, inst)
                    __GQZ = grad_q_glob(self, MAIL, MODE, MATE, NP, "DZ", TQGLOB, 2, inst)

                #           ------------------------------------------------------------------
                #           J01 = W * DIV Q
                #
                __J01_J, volume = cal_j01(self, MODE, "TMAIL", inst, __WELAS, __GQX, __GQY, __GQZ)

                __J = -__J01_J[0]

                #           ------------------------------------------------------------------
                #           J02 = SIGF * GRAD U * GRAD Q
                #
                __J02_J = cal_j02(
                    self,
                    MODE,
                    "TMAIL",
                    inst,
                    __SIGF,
                    __GDEPX,
                    __GDEPY,
                    __GDEPZ,
                    __GQX,
                    __GQY,
                    __GQZ,
                )

                __J = __J + __J02_J[0]

                #           ------------------------------------------------------------------
                #           MODIFIED J OR ETAT_INIT
                #
                if OPTION == "JMOD" or ETAT_INIT is not None:
                    if iNP < NP:
                        __QX, __QY, __QZ = field_q_local(
                            self, MAIL, "TMBOUGER" + str(iNP + 1), ["DX", "DY", "DZ"], TQ[iNP + 1]
                        )
                    else:
                        __QX, __QY, __QZ = field_q_global(
                            self, MAIL, NP, ["DX", "DY", "DZ"], TQGLOB
                        )

                    __QX_GA = field_node_to_gauss(self, MODE, __QX, "DX", "EPXX")

                    __QY_GA = field_node_to_gauss(self, MODE, __QY, "DY", "EPYY")

                    __QZ_GA = field_node_to_gauss(self, MODE, __QZ, "DZ", "EPZZ")

                #           ------------------------------------------------------------------
                #           INITIAL STRAIN
                #
                if ETAT_INIT is not None:
                    #               --------------------------------------------------------------
                    #               J03 = SIGF * GRAD EPS0 * Q
                    #
                    __J03_J = cal_j04(
                        self,
                        MODE,
                        "TMAIL",
                        inst,
                        SIG_CMP,
                        EPS_CMP,
                        __SIGF,
                        dicGradEps0,
                        __QX_GA,
                        __QY_GA,
                        __QZ_GA,
                    )

                    __J = __J + __J03_J[0]

                #           ------------------------------------------------------------------
                #           MODIFIED J
                #
                if OPTION == "JMOD":
                    #               --------------------------------------------------------------
                    #               J04 = SIGF * GRAD EPSI * Q
                    #
                    if j_correction != "OUI":
                        __J04_J = cal_j04(
                            self,
                            MODE,
                            "TMAIL",
                            inst,
                            SIG_CMP,
                            EPS_CMP,
                            __SIGF,
                            dicGradEps,
                            __QX_GA,
                            __QY_GA,
                            __QZ_GA,
                        )

                    else:
                        __J04_J = cal_j04(
                            self,
                            MODE,
                            "TMAIL_IMPR",
                            inst,
                            SIG_CMP,
                            EPS_CMP,
                            __SIGF,
                            dicGradEps,
                            __QX_GA,
                            __QY_GA,
                            __QZ_GA,
                        )

                    __J = __J + __J04_J[0]

                    #               --------------------------------------------------------------
                    #               J05 = GRAD W * Q
                    #
                    if j_correction != "OUI":
                        __J05_J = cal_j05(
                            self, MODE, "TMAIL", inst, __GRAD_WELAS, __QX_GA, __QY_GA, __QZ_GA
                        )

                    else:
                        __J05_J = cal_j05(
                            self, MODE, "TMAIL_IMPR", inst, __GRAD_WELAS, __QX_GA, __QY_GA, __QZ_GA
                        )

                    __J = __J - __J05_J[0]

                #           ------------------------------------------------------------------
                #           Extract results
                #
                nume = dico["NUME_ORDRE"][dico["INST"].index(inst)]

                tab_result = get_result(
                    self,
                    __J,
                    volume,
                    NB_COUCHES,
                    TITRE,
                    TPFISS,
                    FOND_FISS,
                    iNP,
                    NP,
                    listNP,
                    inst,
                    iord,
                    tab_result,
                    nume,
                )

        #   --------------------------------------------------------------------------
        #   DELETE 'TMBOUGERI' and 'TMAIL'
        #
        for iNP in range(NP):
            lGroupNo = "TMBOUGER" + str(iNP + 1)
            del_group_no(self, MAIL, lGroupNo)

        del_group_ma(self, MAIL, "TMAIL")

        if j_correction == "OUI":
            del_group_ma(self, MAIL, "TMAIL_CONT3")
            del_group_ma(self, MAIL, "TMAIL_IMPR")

    RetablirAlarme("CALCCHAMP_1")
    RetablirAlarme("CATAMESS_41")
    RetablirAlarme("MAILLAGE1_1")
    RetablirAlarme("MODELISA4_8")
    RetablirAlarme("MODELISA4_9")
    RetablirAlarme("MODELISA8_13")
    RetablirAlarme("MODELISA8_14")
    RetablirAlarme("MODELISA8_15")
    RetablirAlarme("JEVEUX1_64")
    RetablirAlarme("PREPOST2_7")
    RetablirAlarme("MED_67")
    return tab_result
