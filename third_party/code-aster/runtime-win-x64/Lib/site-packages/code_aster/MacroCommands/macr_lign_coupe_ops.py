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

import os
import sys
from math import atan2, cos, pi, sin, sqrt
from pathlib import Path
from typing import Dict, Tuple, Union
import numpy as np

from ..Cata.Syntax import _F
from ..CodeCommands import (
    COPIER,
    CREA_CHAMP,
    CREA_RESU,
    CREA_TABLE,
    DEFI_GROUP,
    LIRE_MAILLAGE,
    MODI_REPERE,
    POST_RELEVE_T,
    PROJ_CHAMP,
)
from ..Helpers import FileAccess, LogicalUnitFile
from ..Messages import UTMESS, MasquerAlarme, RetablirAlarme
from ..visu.visu_builders import VisuCutBuilder

#
# script PYTHON de creation du résultat local
#

#
# verification que les points de la ligne de coupe sont dans la matiere


class AxisSystem:
    INITIAL: str = "INITIAL"
    GLOBAL: str = "GLOBAL"
    LOCAL: str = "LOCAL"
    CYLINDRIC: str = "CYLINDRIQUE"
    POLAR: str = "POLAIRE"
    USER: str = "UTILISATEUR"
    UNKNOWN: str = "UNKNOWN"

    @staticmethod
    def is_handled_by_modi_repere(axis: str) -> bool:
        return axis in (AxisSystem.LOCAL, AxisSystem.USER, AxisSystem.CYLINDRIC)


def crea_grp_matiere(groupe, newgrp, iocc, m, __remodr, NOM_CHAM, __macou):
    motscles = {}
    if m["NOM_CMP"]:
        motscles["NOM_CMP"] = m["NOM_CMP"]
    else:
        motscles["TOUT_CMP"] = "OUI"
    motscles["OPERATION"] = "EXTRACTION"

    __tab = POST_RELEVE_T(
        ACTION=_F(
            INTITULE=newgrp, RESULTAT=__remodr, NOM_CHAM=NOM_CHAM, GROUP_NO=groupe, **motscles
        )
    )

    node_by_name = {str(node + 1): node for node in __macou.getNodes(groupe, localNumbering=True)}

    # dictb=table initiale (contenant éventuellement des noeuds hors matière)
    dictb = __tab.EXTR_TABLE()
    # listenoe_b=liste ordonnee des noeuds de la ligne de coupe (avec doublons)
    listenoe_b = dictb.NOEUD.values()

    # dictc=table (extraite de dictb) contenant uniquement des noeuds dans la
    # matière
    if m["NOM_CMP"]:
        dictc = getattr(dictb, m["NOM_CMP"][0]).NON_VIDE()
        lno_c2 = set(dictc.NOEUD.values())
    else:  # TOUT_CMP='OUI'
        # on garde uniquement les composantes pour conserver les noeuds où il y
        # a des valeurs
        a_suppr = set(
            [
                "INTITULE",
                "RESU",
                "NOM_CHAM",
                "NUME_ORDRE",
                "INST",
                "ABSC_CURV",
                "COOR_X",
                "COOR_Y",
                "COOR_Z",
            ]
        )
        new_para = set(dictb.para)
        new_para.difference_update(a_suppr)

        lno_c2 = set()
        for comp in new_para.difference(["NOEUD"]):
            dictc = getattr(dictb, comp).NON_VIDE()
            lno_c2.update(dictc.NOEUD.values())

    # on réordonne la liste des noeuds de lno_c2 (selon leur position dans listenoe_b) => l_matiere
    # l_horsmat=liste des noeuds hors matière
    l_matiere = [j for j in listenoe_b if j in lno_c2]
    nderm = l_matiere.index(l_matiere[len(l_matiere) - 1])
    l_horsmat = [j for j in listenoe_b if j not in lno_c2]

    # si on est en présence de noeuds hors matière,
    # on emet une alarme pour informer l'utilisateur
    nbpoin = m["NB_POINTS"]
    reste = nbpoin - len(l_matiere)
    if len(l_horsmat) > 0:
        nderh = l_horsmat.index(l_horsmat[len(l_horsmat) - 1])
        coord = __macou.getCoordinates()
        indent = os.linesep + " " * 12
        l_surlig = []
        l_horslig = []
        for j in l_matiere[: nderm + 1]:
            node = node_by_name[j]
            text_coordo = "(%f, %f, %f)" % (
                coord.getNode(node).x(),
                coord.getNode(node).y(),
                coord.getNode(node).z(),
            )
            l_surlig.append(text_coordo)
        for j in l_horsmat[: nderh + 1]:
            node = node_by_name[j]
            text_coordo = "(%f, %f, %f)" % (
                coord.getNode(node).x(),
                coord.getNode(node).y(),
                coord.getNode(node).z(),
            )
            l_horslig.append(text_coordo)
        UTMESS("A", "POST0_8", valk=[indent.join(l_surlig), indent.join(l_horslig)])

    elif reste > 0:
        coord = __macou.getCoordinates()
        indent = os.linesep + " " * 12
        l_surlig = []
        for j in l_matiere[: nderm + 1]:
            node = node_by_name[j]
            text_coordo = "(%f, %f, %f)" % (
                coord.getNode(node).x(),
                coord.getNode(node).y(),
                coord.getNode(node).z(),
            )
            l_surlig.append(text_coordo)
        UTMESS("A", "POST0_24", vali=[iocc, reste], valk=[indent.join(l_surlig)])

    __macou = DEFI_GROUP(
        reuse=__macou, MAILLAGE=__macou, CREA_GROUP_NO=_F(NOM=newgrp, NOEUD=l_matiere[: nderm + 1])
    )

    return


def crea_resu_local(dime, NOM_CHAM, m, resin):
    epsi = 0.00000001

    if NOM_CHAM == "DEPL":
        if dime == 2:
            TYPE_CHAM = "VECT_2D"
        elif dime == 3:
            TYPE_CHAM = "VECT_3D"
    elif NOM_CHAM in ("SIGM_NOEU", "SIEF_ELNO", "SIGM_ELNO"):
        if dime == 2:
            TYPE_CHAM = "TENS_2D"
        elif dime == 3:
            TYPE_CHAM = "TENS_3D"
    elif NOM_CHAM in ("FLUX_ELNO", "FLUX_NOEU"):
        if dime == 2:
            TYPE_CHAM = "VECT_2D"
        elif dime == 3:
            TYPE_CHAM = "VECT_3D"
        else:
            assert 0
    else:
        assert 0

    modi_champ_args = [_F(NOM_CHAM=NOM_CHAM, TYPE_CHAM=TYPE_CHAM)]

    repere_cut = m["REPERE"]
    type_cut = m["TYPE"]

    if type_cut == "SEGMENT" and repere_cut == AxisSystem.LOCAL:
        if dime == 3 and not m["VECT_Y"]:
            UTMESS("F", "POST0_50")
        elif dime == 2 and m["VECT_Y"]:
            UTMESS("A", "POST0_58")

        # --- determination des angles nautiques
        cx1 = m["COOR_EXTR"][0] - m["COOR_ORIG"][0]
        cx2 = m["COOR_EXTR"][1] - m["COOR_ORIG"][1]
        cx3 = 0.0
        if dime == 3:
            cx3 = m["COOR_EXTR"][2] - m["COOR_ORIG"][2]
        nvx = sqrt(cx1**2 + cx2**2 + cx3**2)
        if abs(nvx) < epsi:
            UTMESS("F", "POST0_1")
        cx1 = cx1 / nvx
        cx2 = cx2 / nvx
        cx3 = cx3 / nvx
        if dime == 3:
            cy1 = m["VECT_Y"][0]
            cy2 = m["VECT_Y"][1]
            cy3 = m["VECT_Y"][2]
            nvy = sqrt(cy1**2 + cy2**2 + cy3**2)
            if abs(nvy) < epsi:
                UTMESS("F", "POST0_2")
            cy1 = cy1 / nvy
            cy2 = cy2 / nvy
            cy3 = cy3 / nvy

            if (abs(cx1 - cy1) < epsi and abs(cx2 - cy2) < epsi and abs(cx3 - cy3) < epsi) or (
                abs(cx1 + cy1) < epsi and abs(cx2 + cy2) < epsi and abs(cx3 + cy3) < epsi
            ):
                UTMESS("F", "POST0_3")

            args_affe = [_F(VECT_X=(cx1, cx2, cx3), VECT_Y=(cy1, cy2, cy3), TOUT="OUI")]
        else:
            # MODI_REPERE can't handle VECT_Y for 2d results -> convert to ANGL_NAUT
            alpha = atan2(cx2, cx1) * 180 / pi
            args_affe = [_F(ANGL_NAUT=[alpha], TOUT="OUI")]

        __remodr = MODI_REPERE(
            RESULTAT=resin, REPERE=AxisSystem.USER, AFFE=args_affe, MODI_CHAM=modi_champ_args
        )

    elif type_cut == "SEGMENT" and repere_cut == AxisSystem.USER:
        alpha = m["ANGL_NAUT"][0]
        beta = m["ANGL_NAUT"][1]
        gamma = m["ANGL_NAUT"][2]
        ANGL_NAUT = []
        ANGL_NAUT.append(alpha)
        if dime == 3:
            ANGL_NAUT.append(beta)
            ANGL_NAUT.append(gamma)
        __remodr = MODI_REPERE(
            RESULTAT=resin,
            REPERE=AxisSystem.USER,
            AFFE=[_F(ANGL_NAUT=ANGL_NAUT, TOUT="OUI")],
            MODI_CHAM=modi_champ_args,
        )
    elif type_cut == "ARC" and repere_cut != AxisSystem.CYLINDRIC:
        UTMESS("F", "POST0_5", valk=[type_cut, repere_cut])
    elif type_cut == "ARC":
        ORIGINE = [m["CENTRE"][0], m["CENTRE"][1]]
        if dime == 3:
            ORIGINE.append(m["CENTRE"][2])
            affe_args = [
                _F(ORIGINE=ORIGINE, AXE_Z=[m["DNOR"][0], m["DNOR"][1], m["DNOR"][2]], TOUT="OUI")
            ]
        elif dime == 2:
            affe_args = [_F(ORIGINE=ORIGINE, TOUT="OUI")]
        __remodr = MODI_REPERE(
            RESULTAT=resin, REPERE=AxisSystem.CYLINDRIC, MODI_CHAM=modi_champ_args, AFFE=affe_args
        )

    elif type_cut[:5] == "GROUP" and repere_cut == AxisSystem.LOCAL:
        # disabled in #35098 because of a lack of test coverage
        UTMESS("F", "POST0_57")

    elif (type_cut[:5] == "GROUP" or type_cut == "SEGMENT") and repere_cut == AxisSystem.CYLINDRIC:
        if dime == 3:
            affe_args = [_F(ORIGINE=m["ORIGINE"], AXE_Z=m["AXE_Z"], TOUT="OUI")]
        elif dime == 2:
            affe_args = [_F(ORIGINE=m["ORIGINE"], TOUT="OUI")]
        __remodr = MODI_REPERE(
            RESULTAT=resin, REPERE=AxisSystem.CYLINDRIC, MODI_CHAM=modi_champ_args, AFFE=affe_args
        )
    elif (type_cut[:5] == "GROUP" or type_cut == "SEGMENT") and repere_cut == AxisSystem.USER:
        alpha = m["ANGL_NAUT"][0]
        beta = m["ANGL_NAUT"][1]
        gamma = m["ANGL_NAUT"][2]
        ANGL_NAUT = []
        ANGL_NAUT.append(alpha)
        if dime == 3:
            ANGL_NAUT.append(beta)
            ANGL_NAUT.append(gamma)

        __remodr = MODI_REPERE(
            RESULTAT=resin,
            REPERE=AxisSystem.USER,
            MODI_CHAM=modi_champ_args,
            AFFE=[_F(ANGL_NAUT=ANGL_NAUT, TOUT="OUI")],
        )
    else:
        raise ValueError(f"{type_cut} using {repere_cut} not handled")

    return __remodr


#
# script PYTHON de creation des noeuds d'une ligne de coupe 'arc'


def crea_noeu_lig_coup(dimension, pt1, pt2, anglj, dnor):
    a = pt1[0] - pt2[0]
    b = pt1[1] - pt2[1]
    eps = 0.00000001
    anglr = anglj * pi / 180.0
    if dimension == 2:
        r = sqrt(a**2 + b**2)
        if abs(r) < eps:
            UTMESS("F", "POST0_6")
        x = pt2[0] + a * cos(anglr) - b * sin(anglr)
        y = pt2[1] + b * cos(anglr) + a * sin(anglr)
        return x, y
    elif dimension == 3:
        c = pt1[2] - pt2[2]
        r = sqrt(a**2 + b**2 + c**2)
        if abs(r) < eps:
            UTMESS("F", "POST0_6")
        d1 = dnor[0]
        d2 = dnor[1]
        d3 = dnor[2]
        d = sqrt(d1**2 + d2**2 + d3**2)
        if abs(r) < eps:
            UTMESS("F", "POST0_7")
        x = pt2[0] + a * cos(anglr) + sin(anglr) * (c * d2 - b * d3) / d
        y = pt2[1] + b * cos(anglr) + sin(anglr) * (a * d3 - c * d1) / d
        z = pt2[2] + c * cos(anglr) + sin(anglr) * (b * d1 - a * d2) / d
        return x, y, z


#
# determination de la distance min entre 2 points consécutifs de la ligne
# de coupe


def dist_min_deux_points(mail):
    nno = mail.getNumberOfNodes()
    coordinates = mail.getCoordinates()
    l_coor1 = []
    l_coor2 = []
    for i in range(nno - 1):
        l_coor1 = coordinates[i]
        l_coor2 = coordinates[i + 1]
        d = sqrt(
            (l_coor1[0] - l_coor2[0]) ** 2
            + (l_coor1[1] - l_coor2[1]) ** 2
            + (l_coor1[2] - l_coor2[2]) ** 2
        )
        if i == 0:
            dist = d
        else:
            dist = min(d, dist)
    return dist


#
# script PYTHON de creation d un maillage de ligne de coupe


def crea_mail_lig_coup(dimension, lignes, groups, arcs):
    # construction du maillage au format Aster des segments de lignes de coupe

    resu = []
    nblig = len(lignes)
    nbngr = len(groups)
    nbarc = len(arcs)

    resu.append("TITRE")
    resu.append("FINSF")
    resu.append("COOR_%dD" % dimension)
    epsi = 0.00000001

    # creation des noeuds
    nbno = 0
    for i in range(nblig):
        pt1 = lignes[i][0]
        pt2 = lignes[i][1]
        nbp_lig_coupe = lignes[i][2]
        for j in range(nbp_lig_coupe):
            if dimension == 2:
                x = pt1[0] + j * (pt2[0] - pt1[0]) / (nbp_lig_coupe - 1)
                y = pt1[1] + j * (pt2[1] - pt1[1]) / (nbp_lig_coupe - 1)
                nbno = nbno + 1
                noeud = "N%d %21.14E %21.14E" % (nbno, x, y)
                resu.append(noeud)
            elif dimension == 3:
                x = pt1[0] + j * (pt2[0] - pt1[0]) / (nbp_lig_coupe - 1)
                y = pt1[1] + j * (pt2[1] - pt1[1]) / (nbp_lig_coupe - 1)
                z = pt1[2] + j * (pt2[2] - pt1[2]) / (nbp_lig_coupe - 1)
                nbno = nbno + 1
                noeud = "N%d %21.14E %21.14E %21.14E" % (nbno, x, y, z)
                resu.append(noeud)
    for i in range(nbngr):
        for pt in groups[i][1:]:
            if dimension == 2:
                nbno = nbno + 1
                noeud = "N%d %21.14E %21.14E" % (nbno, pt[0], pt[1])
                resu.append(noeud)
            elif dimension == 3:
                nbno = nbno + 1
                noeud = "N%d %21.14E %21.14E %21.14E" % (nbno, pt[0], pt[1], pt[2])
                resu.append(noeud)
    angles = [None] * nbarc
    for i in range(nbarc):
        pt1 = arcs[i][0]
        pt2 = arcs[i][1]
        nbp_lig_coupe = arcs[i][2]
        angle = arcs[i][3]
        if abs(angle - 360.0) < epsi:
            nbpt = nbp_lig_coupe + 1
        else:
            nbpt = nbp_lig_coupe
        if dimension == 3:
            dnor = arcs[i][4]
        angles[i] = []
        for j in range(nbp_lig_coupe):
            anglj = j * angle / (nbpt - 1)
            angles[i].append(anglj)
            if dimension == 2:
                nbno = nbno + 1
                x, y = crea_noeu_lig_coup(dimension, pt1, pt2, anglj, dnor=[])
                noeud = "N%d %21.14E %21.14E" % (nbno, x, y)
                resu.append(noeud)
            elif dimension == 3:
                nbno = nbno + 1
                x, y, z = crea_noeu_lig_coup(dimension, pt1, pt2, anglj, dnor)
                noeud = "N%d %21.14E %21.14E %21.14E" % (nbno, x, y, z)
                resu.append(noeud)
    resu.append("FINSF")

    # creation des mailles
    nbma = 0
    for i in range(nblig):
        nbp_lig_coupe = lignes[i][2]
        resu.append("SEG2")
        for j in range(nbp_lig_coupe - 1):
            nbma = nbma + 1
            maille = "M%d N%d N%d" % (nbma, nbma + i, nbma + 1 + i)
            resu.append(maille)
        resu.append("FINSF")
    for i in range(nbngr):
        resu.append("SEG2")
        for pt in groups[i][1:-1]:
            nbma = nbma + 1
            maille = "M%d N%d N%d" % (nbma, nbma + nblig + i, nbma + nblig + 1 + i)
            resu.append(maille)
        resu.append("FINSF")
    nprec = 0

    for i in range(nbarc):
        nbp_lig_coupe = arcs[i][2]
        angle = arcs[i][3]
        resu.append("SEG2")
        nbmai = nbma + nblig + nbngr + nprec + i + 1
        for j in range(nbp_lig_coupe - 1):
            nbma = nbma + 1
            maille = "M%d N%d N%d" % (
                nbma,
                nbma + nblig + nbngr + nprec + i,
                nbma + nblig + nbngr + nprec + 1 + i,
            )
            resu.append(maille)
        if abs(angle - 360.0) < epsi:
            nbma = nbma + 1
            maille = "M%d N%d N%d" % (nbma, nbma + nblig + nbngr + nprec + i, nbmai)
            nprec = nprec - 1
            resu.append(maille)
        resu.append("FINSF")

    # creation des groupes de mailles (1 par ligne de coupe)
    nbma = 0
    for i in range(nblig):
        resu.append("GROUP_MA")
        resu.append("  LICOU%d" % (i + 1))
        nbp_lig_coupe = lignes[i][2]
        for j in range(nbp_lig_coupe - 1):
            nbma = nbma + 1
            resu.append("  M%d" % nbma)
        resu.append("")
        resu.append("FINSF")
    for i in range(nbngr):
        resu.append("GROUP_MA")
        resu.append(groups[i][0])
        nbp_lig_coupe = len(groups[i]) - 1
        for j in range(nbp_lig_coupe - 1):
            nbma = nbma + 1
            resu.append("  M%d" % nbma)
        resu.append("")
        resu.append("FINSF")
    arcgma = []
    for i in range(nbarc):
        resu.append("GROUP_MA")
        k = nblig + i
        resu.append("  LICOU%d" % (k + 1))
        arcgma.append("LICOU%d" % (k + 1))
        nbp_lig_coupe = arcs[i][2]
        angle = arcs[i][3]
        if abs(angle - 360.0) < epsi:
            nbpt = nbp_lig_coupe + 1
        else:
            nbpt = nbp_lig_coupe
        for j in range(nbpt - 1):
            nbma = nbma + 1
            resu.append("  M%d" % nbma)
        resu.append("")
        resu.append("FINSF")
    resu.append("FIN")
    resu.append("")

    return resu, arcgma, angles, nbno


def get_coor(LIGN_COUPE, position, coord, mesh):
    """
    Extrait les coordonnées du noeud ORIG ou EXTR à partir des coordonnées
    ou bien d'un groupe de noeuds ne contenant qu'un seul noeud.
    """
    assert position in ("ORIG", "EXTR")
    if "GROUP_NO_" + position in LIGN_COUPE:
        group = LIGN_COUPE["GROUP_NO_" + position]
        if not mesh.hasGroupOfNodes(group):
            UTMESS("F", "POST0_13", valk=[group, mesh.getName()])
        nodes = mesh.getNodes(group, localNumbering=True)
        if len(nodes) != 1:
            UTMESS("F", "POST0_27", valk=group, vali=len(nodes))
        node = nodes[0]
        coor = [coord.getNode(node).x(), coord.getNode(node).y(), coord.getNode(node).z()]
        # only COOR_xxxx can be used further
        LIGN_COUPE["COOR_" + position] = coor
    elif "COOR_" + position in LIGN_COUPE:
        coor = LIGN_COUPE["COOR_" + position]
    else:
        # Utilisation impossible d'après le catalogue
        assert False
    return coor


def get_result_axis_system(
    origin_field_in_global_axis: bool, cut_axis_system: str, field_name: str
) -> str:
    if not origin_field_in_global_axis:
        return AxisSystem.UNKNOWN
    if cut_axis_system == AxisSystem.INITIAL:
        return AxisSystem.GLOBAL
    if cut_axis_system == AxisSystem.POLAR or AxisSystem.is_handled_by_modi_repere(
        axis=cut_axis_system
    ):
        # only few fields are handled for axis modifications
        if field_name in ("DEPL", "SIEF_ELNO", "SIGM_NOEU", "SIGM_ELNO", "FLUX_ELNO", "FLUX_NOEU"):
            return cut_axis_system
        UTMESS("A", "POST0_17", valk=[field_name, cut_axis_system])
        return AxisSystem.GLOBAL
    raise NotImplementedError(f"{cut_axis_system} is not implemented")


def get_axis_config_for_dimension(
    dimension: int,
) -> Union[
    Tuple[Dict[str, Tuple[float, float]], Tuple[str, str]],
    Tuple[Dict[str, Tuple[float, float, float]], Tuple[str, str, str]],
]:
    if dimension == 2:
        return {"X": (1.0, 0.0), "Y": (0.0, 1.0)}, ("DX", "DY")
    return {"X": (1.0, 0.0, 0.0), "Y": (0.0, 1.0, 0.0), "Z": (0.0, 0.0, 1.0)}, ("DX", "DY", "DZ")


def macr_lign_coupe_ops(
    self,
    LIGN_COUPE,
    REPERE_INIT=None,
    RESULTAT=None,
    CHAM_GD=None,
    NOM_CHAM=None,
    MODELE=None,
    VIS_A_VIS=None,
    UNITE_MAILLAGE=None,
    UNITE_RESU=None,
    **args,
):
    """
    Ecriture de la macro MACR_LIGN_COUPE
    """

    # La valeur par défaut n'est pas dans le catalogue, sinon le mot-clé devient
    # obligatoire dans AsterStudy
    if UNITE_MAILLAGE is None:
        logical_unit = LogicalUnitFile.new_free(access=FileAccess.New)
        UNITE_MAILLAGE = logical_unit.unit

    write_visu = UNITE_RESU is not None

    # On importe les definitions des commandes a utiliser dans la macro

    #
    MasquerAlarme("ALGORITH12_43")
    MasquerAlarme("MODELISA5_53")
    MasquerAlarme("MODELE1_58")
    MasquerAlarme("MODELE1_63")
    MasquerAlarme("MODELE1_64")

    mcORDR = {}

    model = MODELE
    mesh = None

    l_mode_meca_sans_modele = False

    if RESULTAT:
        if "NUME_ORDRE" in args:
            mcORDR["NUME_ORDRE"] = args["NUME_ORDRE"]
        elif "NUME_MODE" in args:
            mcORDR["NUME_MODE"] = args["NUME_MODE"]
        elif "LIST_ORDRE" in args:
            mcORDR["LIST_ORDRE"] = args["LIST_ORDRE"]
        elif "INST" in args:
            mcORDR["INST"] = args["INST"]
            mcORDR["CRITERE"] = args["CRITERE"]
            mcORDR["PRECISION"] = args["PRECISION"]
        elif "LIST_INST" in args:
            mcORDR["LIST_INST"] = args["LIST_INST"]
            mcORDR["CRITERE"] = args["CRITERE"]
            mcORDR["PRECISION"] = args["PRECISION"]
        else:
            mcORDR["TOUT_ORDRE"] = "OUI"

        type_resu = RESULTAT.getType().lower()
        model_resu = RESULTAT.getModel()

        if (not model_resu) or (model_resu.getName() in ("", "#AUCUN")):
            if not MODELE:
                if type_resu != "mode_meca":
                    UTMESS("F", "POST0_9", valk=RESULTAT.getName())
                # si le résultat en entrée est un mode_meca et qu'il ne contient pas de modèle (il est obtenu par sous-structuration, par exemple)
                # on passe le message fatal et on récupérera directement le
                # maillage (ou squelette)
                else:
                    l_mode_meca_sans_modele = True
                    mesh = RESULTAT.getMesh()
                    UTMESS("I", "POST0_23", valk=RESULTAT.getName())
            else:
                mesh = MODELE.getMesh()
        else:
            mesh = model_resu.getMesh()
            if not MODELE:
                model = model_resu

        if not mesh:
            raise Exception("Empty mesh")

    elif CHAM_GD:
        mcORDR["TOUT_ORDRE"] = "OUI"
        if not MODELE:
            UTMESS("F", "POST0_10")

        # récupération de la grandeur du champ
        nomgd = CHAM_GD.getPhysicalQuantity()

        # détermination du type de résultat à créer
        if nomgd[:6] == "TEMP_R":
            TYPE_RESU = "EVOL_THER"
            if not NOM_CHAM:
                NOM_CHAM = "TEMP"
        elif nomgd[:6] == "DEPL_R":
            TYPE_RESU = "EVOL_ELAS"
            if not NOM_CHAM:
                NOM_CHAM = "DEPL"
        elif nomgd[:6] == "NEUT_R":
            TYPE_RESU = "EVOL_VARC"
            if not NOM_CHAM:
                NOM_CHAM = "NEUT"
        elif nomgd[:6] == "EPSI_R":
            TYPE_RESU = "EVOL_ELAS"
        elif nomgd[:6] == "VAR2_R":
            TYPE_RESU = "EVOL_NOLI"
        elif nomgd[:6] == "VARI_R":
            TYPE_RESU = "EVOL_NOLI"
        elif nomgd[:6] == "SIEF_R":
            if not NOM_CHAM:
                TYPE_RESU = "EVOL_ELAS"
                NOM_CHAM = "DEPL"
            elif NOM_CHAM[:4] == "SIGM":
                TYPE_RESU = "EVOL_ELAS"
            elif NOM_CHAM[:4] == "SIEF":
                TYPE_RESU = "EVOL_NOLI"
        else:
            assert 0, "grandeur imprevue : " + nomgd

        # création d'un concept résultat à partir du champ CHAM_GD
        __resuch = CREA_RESU(
            OPERATION="AFFE",
            TYPE_RESU=TYPE_RESU,
            AFFE=_F(NOM_CHAM=NOM_CHAM, CHAM_GD=CHAM_GD, INST=0.0, MODELE=MODELE),
        )
        RESULTAT = __resuch

    assert NOM_CHAM is not None

    if REPERE_INIT is None and not NOM_CHAM.endswith(("ELGA", "ELNO", "ELEM")):
        REPERE_INIT = AxisSystem.GLOBAL

    origin_field_in_global_axis = REPERE_INIT == AxisSystem.GLOBAL

    at_least_1_axis_not_initial = any(
        line_def["REPERE"] != AxisSystem.INITIAL for line_def in LIGN_COUPE
    )
    if not origin_field_in_global_axis and at_least_1_axis_not_initial:
        if REPERE_INIT is None:
            UTMESS("F", "POST0_55", valk=[NOM_CHAM])

        # This field may be defined in a local axis system, currently we cannot access
        # to this information, results will be expressed in the same axis system
        UTMESS("F", "POST0_56", valk=[NOM_CHAM, REPERE_INIT])

    # Maillage sur lequel s'appuie le résultat à projeter
    if not mesh:
        mesh = model.getMesh()
    # le maillage est-il 2D ou 3D ?
    dime = mesh.getDimension()
    coord = mesh.getCoordinates()
    lignes = []
    groups = []
    arcs = []
    minidim = dime

    for m in LIGN_COUPE:
        cut_axis_system = m["REPERE"]
        cut_type = m["TYPE"]
        if cut_type == "SEGMENT":
            coor_orig = get_coor(m, "ORIG", coord, mesh)
            coor_extr = get_coor(m, "EXTR", coord, mesh)
            lignes.append((coor_orig, coor_extr, m["NB_POINTS"]))
            minidim = min(minidim, len(coor_orig), len(coor_extr))
            if minidim != dime:
                UTMESS("F", "POST0_11")

        elif cut_type == "ARC":
            minidim = min(minidim, len(m["COOR_ORIG"]), len(m["CENTRE"]))
            if minidim != dime:
                UTMESS("F", "POST0_11")
            if dime == 2:
                arcs.append((m["COOR_ORIG"], m["CENTRE"], m["NB_POINTS"], m["ANGLE"]))
            elif dime == 3:
                if str(m["DNOR"]) == "None":
                    UTMESS("F", "POST0_12")
                arcs.append((m["COOR_ORIG"], m["CENTRE"], m["NB_POINTS"], m["ANGLE"], m["DNOR"]))

        elif cut_type == "GROUP_NO":
            group = m["GROUP_NO"]
            if not mesh.hasGroupOfNodes(group):
                UTMESS("F", "POST0_13", valk=[group, mesh.getName()])
            l_coor_group = [group]
            for node in mesh.getNodes(group, localNumbering=True):
                l_coor_group.append(
                    [coord.getNode(node).x(), coord.getNode(node).y(), coord.getNode(node).z()]
                )
            groups.append(l_coor_group)

        elif cut_type == "GROUP_MA":
            group = m["GROUP_MA"]
            if not mesh.hasGroupOfCells(group):
                UTMESS("F", "POST0_14", valk=[group, mesh.getName()])
            for cell in mesh.getCells(group):
                if mesh.getCellTypeName(cell)[:3] != "SEG":
                    UTMESS("F", "POST0_15", valk=[group, str(cell + 1)])
            __mailla = COPIER(CONCEPT=m["MAILLAGE"])

            m2 = m
            argsup = {}
            if m2.get("GROUP_NO_ORIG"):
                argsup["GROUP_NO_ORIG"] = m2.get("GROUP_NO_ORIG")
            if m2.get("GROUP_NO_EXTR"):
                argsup["GROUP_NO_EXTR"] = m2.get("GROUP_NO_EXTR")
            if m2.get("VECT_ORIE"):
                argsup["VECT_ORIE"] = m2.get("VECT_ORIE")

            __mailla = DEFI_GROUP(
                reuse=__mailla,
                MAILLAGE=__mailla,
                DETR_GROUP_NO=_F(NOM=str(m["GROUP_MA"])),
                CREA_GROUP_NO=_F(
                    OPTION="NOEUD_ORDO",
                    NOM=str(m["GROUP_MA"]),
                    GROUP_MA=m["GROUP_MA"],
                    ORIGINE="SANS",
                    **argsup,
                ),
            )

            l_coor_group = [group]
            for node in __mailla.getNodes(group, localNumbering=True):
                l_coor_group.append(
                    [coord.getNode(node).x(), coord.getNode(node).y(), coord.getNode(node).z()]
                )
            groups.append(l_coor_group)

    if arcs and (lignes or groups):
        UTMESS("F", "POST0_16")

    # Création du maillage des NB_POINTS segments entre COOR_ORIG et COOR_EXTR
    # ainsi que des segments reliant les noeuds issus des group_no demandés
    # par appel au script python crea_mail_lig_coup
    # le maillage est ensuite recopié dans l unité logique UNITE_MAILLAGE

    resu_mail, arcgma, angles, nbno = crea_mail_lig_coup(dime, lignes, groups, arcs)

    nomFichierSortie = LogicalUnitFile.filename_from_unit(UNITE_MAILLAGE)

    # On Windows, the Fortran runtime's OPEN statement acquires an exclusive
    # file lock that prevents Python's open() from accessing the same file,
    # causing PermissionError.  Release the Fortran handle only when the unit
    # was auto-allocated (registered with LogicalUnitFile); user-specified
    # units are not opened by Fortran at this point so no release is needed.
    _win_released = False
    if sys.platform == "win32":
        _fileobj = LogicalUnitFile.from_number(UNITE_MAILLAGE)
        if _fileobj is not None:
            LogicalUnitFile.release_from_number(UNITE_MAILLAGE)
            _win_released = True

    with open(nomFichierSortie, "w") as fproc:
        # Use "\n".join, not os.linesep.join: Python text mode translates \n
        # to \r\n on Windows automatically.  os.linesep.join inserts \r\n,
        # which text mode then doubles to \r\r\n, corrupting the mesh file.
        fproc.write("\n".join(resu_mail))

    if _win_released:
        # Re-open the file on a Fortran logical unit for LIRE_MAILLAGE.
        logical_unit = LogicalUnitFile.open(nomFichierSortie, access=FileAccess.Old)
        UNITE_MAILLAGE = logical_unit.unit

    # Lecture du maillage de seg2 contenant toutes les lignes de coupe
    __macou = LIRE_MAILLAGE(FORMAT="ASTER", UNITE=UNITE_MAILLAGE)
    LogicalUnitFile.release_from_number(UNITE_MAILLAGE)

    motscles = {}
    iocc = 1
    motscles["CREA_GROUP_NO"] = []
    for m in LIGN_COUPE:
        cut_type = m["TYPE"]
        if cut_type in ("GROUP_NO", "GROUP_MA"):
            motscles["CREA_GROUP_NO"].append(_F(GROUP_MA=m[cut_type].ljust(24)))
        else:
            motscles["CREA_GROUP_NO"].append(_F(GROUP_MA="LICOU" + str(iocc)))
            iocc = iocc + 1

    __macou = DEFI_GROUP(reuse=__macou, MAILLAGE=__macou, **motscles)

    # issue27543 : l'utilisation d'un modèle n'est pas utile et elle
    # engendrait dans le cas thermique l'émission des alarmes MODELE1_3 et MODELE1_53
    # Dans le cas où il y aurait besoin de réintroduire les modèles, j'ai remplacé
    # la modélisation PLAN par COQUE (laissée en commentaire) ce qui permet également
    # de supprimer les alarmes.

    motscles = {}
    motscles.update(mcORDR)
    motscles["VIS_A_VIS"] = []
    if VIS_A_VIS is not None:
        for v in VIS_A_VIS:
            if v["GROUP_MA_1"]:
                motscles["VIS_A_VIS"].append(_F(GROUP_MA_1=v["GROUP_MA_1"], TOUT_2="OUI"))
            elif v["MAILLE_1"]:
                motscles["VIS_A_VIS"].append(_F(MAILLE_1=v["MAILLE_1"], TOUT_2="OUI"))

    if NOM_CHAM[5:9] == "ELGA":
        UTMESS("A", "POST0_18", valk=[NOM_CHAM])

    if l_mode_meca_sans_modele:
        motscles["MAILLAGE_1"] = mesh
    else:
        motscles["MODELE_1"] = model

    # On récupère les minimum des DISTANCE_MAX et DISTANCE_ALARME, ces valeurs
    # serviront pour le PROJ_CHAMP pour toutes les coupes

    all_distance_max = [m.get("DISTANCE_MAX") for m in LIGN_COUPE if m.get("DISTANCE_MAX")]
    all_distance_alarme = [m.get("DISTANCE_ALARME") for m in LIGN_COUPE if m.get("DISTANCE_ALARME")]

    min_distance_max = min(all_distance_max, default=0.0)
    min_distance_alarme = min(all_distance_alarme, default=0.0)

    # On émet une alarme dès qu'au moins une des valeurs des DISTANCE_MAX
    # ou DISTANCE_ALARME est différente de la valeur retenue

    if not all(dist == min_distance_max for dist in all_distance_max):
        UTMESS("A", "POST0_53", valr=[min_distance_max])

    if not all(dist == min_distance_alarme for dist in all_distance_alarme):
        UTMESS("A", "POST0_54", valr=[min_distance_alarme])

    __recou = PROJ_CHAMP(
        METHODE="COLLOCATION",
        RESULTAT=RESULTAT,
        DISTANCE_MAX=min_distance_max,
        DISTANCE_ALARME=min_distance_alarme,
        # issue27543 #MODELE_2=__mocou,
        MAILLAGE_2=__macou,
        TYPE_CHAM="NOEU",
        NOM_CHAM=NOM_CHAM,
        **motscles,
    )

    __remodr = __recou
    ioc2 = 0
    mcACTION = []

    if RESULTAT.getType().lower() not in (
        "evol_ther",
        "evol_sech",
        "evol_elas",
        "evol_noli",
        "mode_meca",
        "evol_varc",
        "comb_fourier",
        "mult_elas",
        "fourier_elas",
        "dyna_trans",
    ):
        assert 0

    # modify mesh before loading VisuCutBuilder
    cut_to_group: Dict[int, Tuple[str, str]] = {}
    for iocc, m in enumerate(LIGN_COUPE):
        cut_type = m["TYPE"]
        if cut_type in ("GROUP_NO", "GROUP_MA"):
            groupe = m[cut_type].ljust(8)
        else:
            ioc2 += 1
            groupe = f"LICOF{ioc2}"
            crea_grp_matiere(f"LICOU{ioc2}", groupe, iocc, m, __remodr, NOM_CHAM, __macou)
        # on definit l'intitulé
        if m["INTITULE"]:
            intitl = m["INTITULE"]
        elif cut_type in ("GROUP_NO", "GROUP_MA"):
            intitl = groupe
        else:
            intitl = f"l.coupe{ioc2}"
        cut_to_group[iocc] = groupe, intitl

    if write_visu:
        unit_depl_configs, compo_depl_unit = get_axis_config_for_dimension(dimension=dime)

        resu_unit_depl = {}
        for direction, vect_unit in unit_depl_configs.items():
            FIELD_DEPL_1 = CREA_CHAMP(
                MAILLAGE=__macou,
                MODELE=__recou.getModel(),
                OPERATION="AFFE",
                TYPE_CHAM="NOEU_DEPL_R",
                AFFE=(_F(TOUT="OUI", NOM_CMP=compo_depl_unit, VALE=vect_unit),),
            )
            resu_unit_depl[direction] = CREA_RESU(
                OPERATION="AFFE",
                TYPE_RESU="EVOL_ELAS",
                AFFE=_F(NOM_CHAM="DEPL", INST=0.0, CHAM_GD=FIELD_DEPL_1),
            )
        visu_cut = VisuCutBuilder.from_aster_mesh(mesh=__macou, prefix_output_field_name="CUT")

    for iocc, m in enumerate(LIGN_COUPE):
        motscles = {}
        motscles["OPERATION"] = m["OPERATION"]
        if m["NOM_CMP"]:
            motscles["NOM_CMP"] = m["NOM_CMP"]
            if m["TRAC_NOR"]:
                motscles["TRAC_NOR"] = m["TRAC_NOR"]
            elif m["TRAC_DIR"]:
                motscles["TRAC_DIR"] = m["TRAC_DIR"]
                motscles["DIRECTION"] = m["DIRECTION"]
        elif m["INVARIANT"]:
            motscles["INVARIANT"] = m["INVARIANT"]
        elif m["RESULTANTE"]:
            motscles["RESULTANTE"] = m["RESULTANTE"]
            if m["MOMENT"]:
                motscles["MOMENT"] = m["MOMENT"]
                motscles["POINT"] = m["POINT"]
        elif m["ELEM_PRINCIPAUX"]:
            motscles["ELEM_PRINCIPAUX"] = m["ELEM_PRINCIPAUX"]
        else:
            motscles["TOUT_CMP"] = "OUI"

        groupe, intitl = cut_to_group[iocc]

        current_resu = __recou

        result_axis_system = get_result_axis_system(
            origin_field_in_global_axis=origin_field_in_global_axis,
            cut_axis_system=cut_axis_system,
            field_name=NOM_CHAM,
        )

        if result_axis_system in (AxisSystem.GLOBAL, AxisSystem.UNKNOWN):
            # Expression des contraintes aux noeuds ou des déplacements dans le
            # repere d'origine du champ
            mcACTION.append(
                _F(
                    INTITULE=intitl,
                    RESULTAT=__recou,
                    GROUP_NO=groupe,
                    NOM_CHAM=NOM_CHAM,
                    **motscles,
                )
            )
        elif result_axis_system == AxisSystem.POLAR:
            mcACTION.append(
                _F(
                    INTITULE=intitl,
                    RESULTAT=__remodr,
                    REPERE=cut_axis_system,
                    GROUP_NO=groupe,
                    NOM_CHAM=NOM_CHAM,
                    **motscles,
                )
            )
        elif AxisSystem.is_handled_by_modi_repere(axis=result_axis_system):
            __remodr = crea_resu_local(dime, NOM_CHAM, m, __recou)
            current_resu = __remodr
            mcACTION.append(
                _F(
                    INTITULE=intitl,
                    RESULTAT=__remodr,
                    GROUP_NO=groupe,
                    NOM_CHAM=NOM_CHAM,
                    **motscles,
                )
            )

        else:
            raise ValueError(f"{result_axis_system} not handled")

        if write_visu:
            # ATTENTION si CHANGEMENT DE REPERE les noms de CHAMP PEUVENT CHANGER
            fields_names = current_resu.getFieldsNames()
            assert len(fields_names) == 1

            field_name = fields_names[0]

            node_ids = __macou.getNodes(groupe)

            visu_cut.add_field_on_nodes_from_aster_result_all_timesteps(
                aster_result=current_resu, field_name=field_name, nodes=node_ids
            )

            same_axes_for_all_cut = True
            add_axe_mask = True
            if result_axis_system == AxisSystem.GLOBAL:
                for axis_name, vect in unit_depl_configs.items():
                    visu_cut.add_field_on_nodes(
                        field_name=f"AXE_{axis_name}",
                        nodes=node_ids,
                        values=np.array([vect] * len(node_ids)),
                        components=compo_depl_unit,
                    )
            elif AxisSystem.is_handled_by_modi_repere(axis=result_axis_system):
                # transfer matrix from local to global system
                transfer_matrix: np.ndarray = np.full(
                    (len(node_ids), dime, dime), fill_value=np.nan
                )
                for axis_name, resu_in_unit_direction in resu_unit_depl.items():
                    axis_index = compo_depl_unit.index(f"D{axis_name}")
                    axis_glob_in_local_system_tmp = crea_resu_local(
                        dime=dime, NOM_CHAM="DEPL", m=m, resin=resu_in_unit_direction
                    )

                    field = axis_glob_in_local_system_tmp.getField("DEPL", 1).toSimpleFieldOnNodes()
                    transfer_matrix[:, axis_index] = field.getValues()[0][node_ids]

                # evaluate local axis in global coordinate system
                for axis_name, vect_unit in unit_depl_configs.items():
                    if (
                        dime == 2
                        and resu_in_unit_direction == AxisSystem.CYLINDRIC
                        and axis_name == "Y"
                    ):
                        # it's not possible to acces to Y axis field in 2d results for cylindric
                        # axis system because theta axis is mapped to Z
                        continue
                    unit_axis = np.array(vect_unit)
                    local_axis_in_global_system = transfer_matrix @ unit_axis
                    visu_cut.add_field_on_nodes(
                        field_name=f"AXE_{axis_name}",
                        nodes=node_ids,
                        values=local_axis_in_global_system,
                        components=compo_depl_unit,
                    )

                    same_axes_for_all_cut = (
                        same_axes_for_all_cut
                        and np.unique(local_axis_in_global_system, axis=0).shape[0] == 1
                    )
            else:
                add_axe_mask = False

            # Add mask to only display one node in paraview when every axes are the same
            if add_axe_mask:
                if same_axes_for_all_cut:
                    # mask every node except last one
                    axis_base_mask = np.full(shape=(len(node_ids), 1), fill_value=0, dtype=int)
                    axis_base_mask[-1, 0] = 1
                else:
                    # show every node
                    axis_base_mask = np.full(shape=(len(node_ids), 1), fill_value=1, dtype=int)
                visu_cut.add_field_on_nodes(
                    field_name="AXE_MASK",
                    nodes=node_ids,
                    values=axis_base_mask,
                    components=("SHOW",),
                )

            group_name = f"CUT_{intitl}"
            visu_cut.add_group(name=group_name, ids=node_ids, geo_type=VisuCutBuilder.NODE)

    if write_visu:
        visu_filepath = Path(LogicalUnitFile.filename_from_unit(unit=UNITE_RESU))
        visu_cut.write(filepath=visu_filepath)

    __tabitm = POST_RELEVE_T(ACTION=mcACTION)

    # on repasse par les tables python pour supprimer les paramètres inutiles
    # NOEUD (car il est propre au maillage de la ligne) et RESU

    dictab = __tabitm.EXTR_TABLE()
    # Ajout de la colonne theta
    if len(arcgma) > 0 and "ABSC_CURV" in dictab.para:
        val = dictab["ABSC_CURV"].values()["ABSC_CURV"]
        nbi = len(val) // nbno
        nba = len(angles)
        tmp = []
        for k in range(nba):
            for j in range(nbi):
                for i in range(len(angles[k])):
                    tmp.append(angles[k][i])
        dictab["ANGLE"] = tmp

    if "RESU" in dictab.para:
        del dictab["RESU"]
    if "NOEUD" in dictab.para:
        del dictab["NOEUD"]
    dprod = dictab.dict_CREA_TABLE()
    # Remove TITRE key from the dictionary so that the newly created table uses
    # the user-given concept name in its title
    dprod.pop("TITRE")

    nomres = CREA_TABLE(**dprod)

    RetablirAlarme("ALGORITH12_43")
    RetablirAlarme("MODELISA5_53")
    RetablirAlarme("MODELE1_58")
    RetablirAlarme("MODELE1_63")
    RetablirAlarme("MODELE1_64")
    return nomres
