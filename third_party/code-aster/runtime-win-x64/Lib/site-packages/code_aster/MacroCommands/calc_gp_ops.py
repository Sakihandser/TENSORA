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

import numpy as np
from numpy import cos, pi, sin

from ..Cata.Syntax import _F
from ..CodeCommands import (
    CALC_CHAMP,
    CREA_CHAMP,
    CREA_TABLE,
    DEFI_GROUP,
    DEFI_LIST_REEL,
    FORMULE,
    POST_ELEM,
)
from ..Messages import UTMESS, MasquerAlarme, RetablirAlarme


#
#
# CAS 2D: FORMULES PERMETTANT LA DEFINITION ET LE CALCUL DES COPEAUX DANS LE CAS SS_COPEAU
#           (Pour plus de renseignement, voir CR-AMA-12-272)
#
def SEUIL(X, Y, X0, Y0, R, lc, Nume_cop, ccos, ssin):
    f1 = 0
    f2 = 0
    f3 = 0
    # DY1,DY2,DX3,DX2
    if (
        (-(X - X0) * ccos <= (Y - Y0) * ssin)
        and ((X - X0 - Nume_cop * lc * ccos) * ccos <= -ssin * (Y - Y0 - Nume_cop * lc * ssin))
        and ((Y - Y0 + R * ccos) * ccos >= (X - X0 - R * ssin) * ssin)
        and ((Y - Y0 - R * ccos) * ccos <= (X - X0 + R * ssin) * ssin)
    ):
        f1 = 1
    # C2,DY2
    if ((X - X0 - Nume_cop * lc * ccos) ** 2 + (Y - Y0 - Nume_cop * lc * ssin) ** 2 <= R**2) and (
        (X - X0 - Nume_cop * lc * ccos) * ccos >= -ssin * (Y - Y0 - Nume_cop * lc * ssin)
    ):
        f2 = 1
    # C1,DY1
    if ((X - X0) ** 2 + (Y - Y0) ** 2 <= R**2) and (-(X - X0) * ccos <= (Y - Y0) * ssin):
        f3 = 1
    f = f1 + f2 - f3
    return f


# --


def NRJ(ENEL_ELGA, X, Y, X0, Y0, R, lc, Nume_cop, ccos, ssin):
    nr = ENEL_ELGA * SEUIL(X, Y, X0, Y0, R, lc, Nume_cop, ccos, ssin)
    return nr


#
# CAS 3D: METHODES PERMETTANT LE CALCUL DE LA SURFACE DES MAILLES DU PLAN DE SYMETRIE
#


def Calcul_mesure_3D(maya, nbcop, l_copo_tot, nd_fiss, normale):
    # Calcul de la mesure des mailles appartenant au plan de symetrie
    # On est en petites deformations alors on ne tient pas compte de la deformee
    # lors du calcul de la surface

    connectivity = maya.getConnectivity()
    coordinates = maya.getCoordinates()

    mesure = [0] * len(l_copo_tot)

    # Recuperation des noeuds appartenant a la surface de symetrie
    DEFI_GROUP(
        reuse=maya,
        MAILLAGE=maya,
        CREA_GROUP_NO=_F(
            NOM="Nds_Plan",
            OPTION="PLAN",
            VECT_NORMALE=normale,
            NOEUD_CENTRE=nd_fiss,
            PRECISION=1e-6,
        ),
    )

    # cration des groupes
    crea_group_no = []
    crea_group_ma = []
    detr_group_no = []
    detr_group_ma = []
    for C_k, Copeau_k in enumerate(l_copo_tot):
        # groupe de noeuds appartenant au copeau courant
        crea_group_no.append({"NOM": Copeau_k, "GROUP_MA": Copeau_k})
        detr_group_no.append(Copeau_k)
        crea_group_no.append({"NOM": "Cop_Pl_%s" % C_k, "INTERSEC": (Copeau_k, "Nds_Plan")})
        detr_group_no.append("Cop_Pl_%s" % C_k)
        # groupe de maille de l'interface du copeau avec la fissure
        crea_group_ma.append(
            {
                "NOM": "Mai_Plan_%s" % C_k,
                "OPTION": "APPUI",
                "GROUP_NO": "Cop_Pl_%s" % C_k,
                "TYPE_APPUI": "TOUT",
                "TYPE_MAILLE": "2D",
            }
        )
        detr_group_ma.append("Mai_Plan_%s" % C_k)
    # on regroupe la creation dans un seul appel à DEFI_GROUP pour améliorer les performances
    DEFI_GROUP(reuse=maya, MAILLAGE=maya, CREA_GROUP_NO=crea_group_no)
    DEFI_GROUP(reuse=maya, MAILLAGE=maya, CREA_GROUP_MA=crea_group_ma)

    # calcul de la surface pour chacun des coppeaux
    for C_k, Copeau_k in enumerate(l_copo_tot):
        # Recuperation des coordonnees des noeuds appartenant au copeau courant
        cells = maya.getCells("Mai_Plan_%s" % C_k)
        for cell in cells:
            nodes = connectivity[cell]
            if len(nodes) not in (4, 8):
                UTMESS("F", "RUPTURE1_22")
            # Calcul de la surface de la maille 2D du copeau courant appartenant au plan de symetrie
            coords = [
                np.array(
                    [
                        coordinates.getNode(node).x(),
                        coordinates.getNode(node).y(),
                        coordinates.getNode(node).z(),
                    ]
                )
                for node in nodes[:4]
            ]
            dAB = np.linalg.norm(coords[1] - coords[0])
            dBC = np.linalg.norm(coords[2] - coords[1])
            dCD = np.linalg.norm(coords[3] - coords[2])
            dDA = np.linalg.norm(coords[0] - coords[3])

            if abs(dAB - dCD) / dAB > 0.2 or abs(dDA - dBC) / dDA > 0.2:
                UTMESS("A", "RUPTURE1_29")
            mesure[C_k] += (dAB + dCD) / 2.0 * (dBC + dDA) / 2.0

    # Destruction des groupes de noeuds et de mailles temporaires
    DEFI_GROUP(reuse=maya, MAILLAGE=maya, DETR_GROUP_MA=_F(NOM=detr_group_ma))
    DEFI_GROUP(reuse=maya, MAILLAGE=maya, DETR_GROUP_NO=_F(NOM=detr_group_no))
    DEFI_GROUP(reuse=maya, MAILLAGE=maya, DETR_GROUP_NO=_F(NOM="Nds_Plan"))

    return mesure


def createListFromTableWithoutUnion(Table, para):
    list_return = []
    for row in Table:
        if row["LIEU"] != "UNION_GROUP_MA":
            list_return.append(row[para])

    return list_return


#
# DEBUT DE LA MACRO PROPREMENT DITE
#
def calc_gp_ops(self, **args):
    """Corps de CALC_GP"""
    MasquerAlarme("CALCCHAMP_1")
    global DEFI_GROUP
    # On importe les definitions des commandes a utiliser dans la macro
    #

    #
    # RECUPERATION DU MODELE, DU MAILLAGE ET DU MATERIAU A PARTIR DU RESULTAT
    #

    __RESU = args["RESULTAT"]

    #  modele
    __model = __RESU.getModel()
    # Dimension du modele
    ndim = __model.getMesh().getDimension()
    #
    #  maillage
    __maillage = __model.getMesh()
    #
    __cham_mater = __RESU.getMaterialField()

    #
    # RECUPERATION DES DONNEES DE SYMETRIE ET DU FOND DE FISSURE
    #

    # mult=Coefficient multiplicatif suivant la symetrie du probleme
    mult = 1.0
    if "TRANCHE_2D" in args:
        TRANCHE_2D = args["TRANCHE_2D"]
        if ndim != 2:
            UTMESS("F", "RUPTURE1_19", ["TRANCHE_2D", "2D"])
        #    symetrie
        if args["SYME"] == "OUI":
            mult = 2.0
    else:
        TRANCHE_3D = args["TRANCHE_3D"]
        if ndim != 3:
            UTMESS("F", "RUPTURE1_19", ["TRANCHE_3D", "3D"])

        #    liste des noeuds du fond de fissure
        l_noeuds_fissure = args["FOND_FISS"].getCrackFrontNodes()

        #    normale au plan de la fissure
        lnormale = args["FOND_FISS"].getNormal()
        if lnormale is None:
            UTMESS("F", "POST0_39")

        #    symetrie
        is_symmetric = args["FOND_FISS"].isSymmetric()
        if is_symmetric:
            mult = 2

    #
    # VERIFICATION DE LA LISTE DES INSTANTS
    #

    # Verification que les instants demandes sont bien dans le resultat
    # Construction des instants de calcul par la meme occasion
    list_inst = __RESU.getAccessParameters()["INST"]
    l_inst_final = []

    for inst in args["LIST_INST"].getValues():
        if args["CRITERE"] == "ABSOLU":
            prec = args["PRECISION"]
        elif args["CRITERE"] == "RELATIF":
            prec = args["PRECISION"] * inst

        match = [x for x in list_inst if ((x + prec >= inst) and (x - prec <= inst))]
        if len(match) == 0:
            UTMESS("F", "RUPTURE0_38", valr=inst)
        if len(match) >= 2:
            UTMESS("F", "RUPTURE0_39", valr=inst)

        l_inst_final.append(match[0])

    nb_inst = len(l_inst_final)
    __linstr8 = DEFI_LIST_REEL(VALE=l_inst_final)

    #
    # PREPARATION DES SORTIES SI GPMAX
    #

    # Definition du concept sortant systematique dans le contexte de la macro
    # L'eventuel champ de copeaux est cree plus tard si besoin

    # Definition de la sortie facultative GP_MAX
    GPMAX = None
    if "GPMAX" in args:
        GPMAX = args["GPMAX"]
        # Creation des colonnes de la table de sortie gpmax
        tabinstmax = []
        tabcopmax = []
        tabenelmax = []
        tablcopmax = []
        tabgpmax = []

    #

    #
    # CALCUL DES GP
    #

    #
    #                      1/ CAS 2D
    #

    if ndim == 2:
        #
        # 1.1/ CAS OU L UTILISATEUR A DEFINI DES GROUPES DE MAILLE COPEAU
        #      IL SUFFIT ALORS DE CALCULER L ENERGIE DANS CES GROUPES ET D EN DEDUIRE LE GP
        #
        if TRANCHE_2D["ZONE_MAIL"] == "OUI":
            lgroupma = TRANCHE_2D["GROUP_MA"]
            lcopeau = TRANCHE_2D["TAILLE"].getValues()
            if len(lgroupma) != len(lcopeau):
                UTMESS("F", "RUPTURE1_21")
            nbcop = len(lcopeau)

            tabmax = [0] * nbcop * nb_inst
            tabcop = lgroupma * nb_inst
            tablcop = lcopeau * nb_inst

            __enertemp = POST_ELEM(
                MODELE=__model,
                RESULTAT=__RESU,
                LIST_INST=__linstr8,
                ENER_ELTR=_F(GROUP_MA=lgroupma),
            )
            enerel = __enertemp.EXTR_TABLE()
            enerel_TOTALE = createListFromTableWithoutUnion(enerel, "TOTALE")
            tabenel = [mult * x for x in enerel_TOTALE]
            tabgp = [tabenel[x] / tablcop[x] for x in range(len(tabenel))]
            tabinst = createListFromTableWithoutUnion(enerel, "INST")

            for i in range(nb_inst):
                maxinst = max(tabgp[i * nbcop : (i + 1) * nbcop])
                index1 = tabgp[i * nbcop : (i + 1) * nbcop].index(maxinst)
                index = index1 + i * nbcop
                tabmax[index] = 1
                if GPMAX is not None:
                    tabinstmax.append(tabinst[index])
                    tabcopmax.append(tabcop[index])
                    tabenelmax.append(tabenel[index])
                    tablcopmax.append(tablcop[index])
                    tabgpmax.append(tabgp[index])

        #
        # 1.2/ CAS OU L UTILISATEUR N A PAS DEFINI DES GROUPES DE MAILLE COPEAU
        #      IL FAUT CREER UN DES COPEAUX PAR ENSEMBLE DE POINTS DE GAUSS ET JOUER AVEC
        #
        elif TRANCHE_2D["ZONE_MAIL"] == "NON":
            nbcop = TRANCHE_2D["NB_ZONE"]
            theta = TRANCHE_2D["ANGLE"]
            taille = TRANCHE_2D["TAILLE"]
            nom_cmp = ["X%d" % k for k in range(1, nbcop + 1)]
            nom_cop = ["COPS_%d" % k for k in range(1, nbcop + 1)]

            # champ de geometrie et de points de gauss (coordonnees des points de gauss)
            __CHXN = CREA_CHAMP(
                OPERATION="EXTR", TYPE_CHAM="NOEU_GEOM_R", NOM_CHAM="GEOMETRIE", MAILLAGE=__maillage
            )

            __CHXG = CREA_CHAMP(
                OPERATION="DISC", TYPE_CHAM="ELGA_GEOM_R", MODELE=__model, CHAM_GD=__CHXN
            )

            ccos = cos(theta * pi / 180.0)
            ssin = sin(theta * pi / 180.0)
            # construction du champ copeau pour visualisation par utilisateur s'il le
            # souhaite
            if TRANCHE_2D["CHAMP_VISU"] != 0:
                __seuil = [None for i in range(nbcop)]
                for cop in range(nbcop):
                    __seuil[cop] = FORMULE(
                        VALE="""SEUIL(X,Y,origine[0],origine[1],rayon,taille,%d,ccos,ssin)"""
                        % (cop + 1),
                        NOM_PARA=("X", "Y"),
                        origine=TRANCHE_2D["CENTRE"],
                        rayon=TRANCHE_2D["RAYON"],
                        taille=taille,
                        theta=theta,
                        SEUIL=SEUIL,
                        ccos=ccos,
                        ssin=ssin,
                    )

                __formule_seuil = CREA_CHAMP(
                    TYPE_CHAM="ELGA_NEUT_F",
                    MODELE=__model,
                    OPERATION="AFFE",
                    PROL_ZERO="OUI",
                    AFFE=_F(TOUT="OUI", NOM_CMP=nom_cmp, VALE_F=__seuil),
                )

                chp_cop = CREA_CHAMP(
                    TYPE_CHAM="ELGA_NEUT_R",
                    OPERATION="EVAL",
                    CHAM_F=__formule_seuil,
                    CHAM_PARA=(__CHXG),
                )
                self.register_result(chp_cop, TRANCHE_2D["CHAMP_VISU"])

            # calcul des energies et du gp
            __ener = [None for cop in range(nbcop)]
            for cop in range(nbcop):
                __ener[cop] = FORMULE(
                    VALE="""NRJ(TOTALE,X,Y,origine[0],origine[1],rayon,taille,%d,ccos,ssin)"""
                    % (cop + 1),
                    NOM_PARA=("TOTALE", "X", "Y"),
                    origine=TRANCHE_2D["CENTRE"],
                    rayon=TRANCHE_2D["RAYON"],
                    taille=taille,
                    NRJ=NRJ,
                    ccos=ccos,
                    ssin=ssin,
                )

            __formule_ener = CREA_CHAMP(
                TYPE_CHAM="ELGA_NEUT_F",
                MODELE=__model,
                OPERATION="AFFE",
                PROL_ZERO="OUI",
                AFFE=_F(TOUT="OUI", NOM_CMP=nom_cmp, VALE_F=__ener),
            )

            __RESU = CALC_CHAMP(
                reuse=__RESU, RESULTAT=__RESU, LIST_INST=__linstr8, ENERGIE=("ENEL_ELGA")
            )

            tabmax = [0] * nbcop * nb_inst
            tabcop = nom_cop * nb_inst
            tablcop = [taille * (cop + 1) for cop in range(nbcop)] * nb_inst
            tabinst = []
            tabenel = []
            tabgp = []

            for i, inst in enumerate(l_inst_final):
                __energa = CREA_CHAMP(
                    OPERATION="EXTR",
                    TYPE_CHAM="ELGA_ENER_R",
                    NOM_CHAM="ENEL_ELGA",
                    RESULTAT=__RESU,
                    INST=inst,
                )

                __resinter = CREA_CHAMP(
                    TYPE_CHAM="ELGA_NEUT_R",
                    OPERATION="EVAL",
                    CHAM_F=__formule_ener,
                    CHAM_PARA=(__energa, __CHXG),
                )

                __tabnrj = POST_ELEM(
                    CHAM_GD=__resinter,
                    MODELE=__model,
                    CHAM_MATER=__cham_mater,
                    INTEGRALE=_F(
                        TOUT="OUI",
                        NOM_CHAM="ENEL_ELGA",
                        NOM_CMP=nom_cmp,
                        DEJA_INTEGRE="NON",
                        TYPE_MAILLE="2D",
                    ),
                )

                tabenerel = __tabnrj.EXTR_TABLE().values()

                tabinst = tabinst + [inst] * nbcop

                enerel = [mult * tabenerel["INTE_X%d" % (cop + 1)][0] for cop in range(nbcop)]
                tabenel += enerel
                gp = [enerel[cop] / (taille * (cop + 1)) for cop in range(nbcop)]
                tabgp += gp

                maxinst = max(tabgp[i * nbcop : (i + 1) * nbcop])
                index1 = tabgp[i * nbcop : (i + 1) * nbcop].index(maxinst)
                index = index1 + i * nbcop
                tabmax[index] = 1
                if GPMAX is not None:
                    tabinstmax.append(tabinst[index])
                    tabcopmax.append(tabcop[index])
                    tabenelmax.append(tabenel[index])
                    tablcopmax.append(tablcop[index])
                    tabgpmax.append(tabgp[index])

    #
    #                      2/ CAS 3D
    #
    elif ndim == 3:
        #    liste des copeaux
        l_copo_tot = []
        for tmpocc in TRANCHE_3D:
            dMCT = tmpocc
            l_copo_tot += dMCT["GROUP_MA"]

        # le nombre de copeaux est suppose identique sur toutes les tranches
        nbcoptot = len(l_copo_tot)
        nbcop = nbcoptot // len(TRANCHE_3D)

        # calcul de la surface des mailles appartenant au plan de symetrie de
        # l'entaille
        mesure = Calcul_mesure_3D(__maillage, nbcop, l_copo_tot, l_noeuds_fissure[0], lnormale)

        # calcul des energies et du gp
        __enertemp = POST_ELEM(
            MODELE=__model,
            RESULTAT=__RESU,
            LIST_INST=__linstr8,
            ENER_ELTR=_F(GROUP_MA=l_copo_tot),
            TITRE="Energie elastique de traction",
        )

        enerel = __enertemp.EXTR_TABLE()

        tabcop = createListFromTableWithoutUnion(enerel, "LIEU")
        enerel_TOTALE = createListFromTableWithoutUnion(enerel, "TOTALE")
        tabenel = [mult * x for x in enerel_TOTALE]
        tabinst = createListFromTableWithoutUnion(enerel, "INST")
        tablcop = mesure * nb_inst
        tabgp = [tabenel[x] / tablcop[x] for x in range(len(tabenel))]

        tabmax = [0] * nbcoptot * nb_inst
        for i in range(nb_inst):
            maxinst = max(tabgp[nbcoptot * i : nbcoptot * (i + 1)])
            index1 = tabgp[nbcoptot * i : nbcoptot * (i + 1)].index(maxinst)
            index = index1 + i * nbcoptot
            tabmax[index] = 1
            if GPMAX is not None:
                tabinstmax.append(tabinst[index])
                tabcopmax.append(tabcop[index])
                tabenelmax.append(tabenel[index])
                tablcopmax.append(tablcop[index])
                tabgpmax.append(tabgp[index])

    #

    #
    # CREATION DE LA TABLE DE SORTIE
    #

    tabout = CREA_TABLE(
        LISTE=(
            _F(PARA="INST", LISTE_R=tabinst),
            _F(PARA="ZONE", LISTE_K=tabcop),
            _F(PARA="ENER ELAS", LISTE_R=tabenel),
            _F(PARA="DELTA L", LISTE_R=tablcop),
            _F(PARA="GP", LISTE_R=tabgp),
            _F(PARA="MAX_INST", LISTE_I=tabmax),
        )
    )
    if GPMAX is not None:
        tabgpmax = CREA_TABLE(
            LISTE=(
                _F(PARA="INST", LISTE_R=tabinstmax),
                _F(PARA="ZONE", LISTE_K=tabcopmax),
                _F(PARA="ENER ELAS", LISTE_R=tabenelmax),
                _F(PARA="DELTA L", LISTE_R=tablcopmax),
                _F(PARA="GP", LISTE_R=tabgpmax),
            )
        )
        self.register_result(tabgpmax, GPMAX)
    RetablirAlarme("CALCCHAMP_1")
    return tabout
