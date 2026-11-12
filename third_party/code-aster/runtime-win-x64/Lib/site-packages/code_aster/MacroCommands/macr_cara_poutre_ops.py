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

from ..Cata.Syntax import _F
from ..CodeCommands import (
    AFFE_CHAR_THER,
    AFFE_CHAR_THER_F,
    AFFE_MATERIAU,
    AFFE_MODELE,
    ASSE_VECTEUR,
    CALC_CHAMP,
    CALC_MATR_ELEM,
    CALC_TABLE,
    CALC_VECT_ELEM,
    COPIER,
    CREA_MAILLAGE,
    CREA_TABLE,
    DEFI_CONSTANTE,
    DEFI_FONCTION,
    DEFI_GROUP,
    DEFI_LIST_REEL,
    DEFI_MATERIAU,
    IMPR_TABLE,
    LIRE_MAILLAGE,
    MACR_LIGN_COUPE,
    NUME_DDL,
    POST_ELEM,
    THER_LINEAIRE,
)
from ..Messages import UTMESS, MasquerAlarme, RetablirAlarme


def removeGroupNo(mesh, name):
    if mesh.hasGroupOfNodes(name):
        DEFI_GROUP(reuse=mesh, MAILLAGE=mesh, DETR_GROUP_NO=_F(NOM=name))


# fmt: off
def TraiteQuadrant(UneSect, NewQuadrant):
    assert NewQuadrant in [1,2,3,4], "Erreur développeur NewQuadrant:%s" % NewQuadrant
    #
    alpha0 = UneSect[ 'ALPHA' ]
    # On cherche le quadrant dans lequel on est : Alpha est en dg
    if ( alpha0 < 0.0 ): alpha0 = 360.0 + alpha0
    #
    quadrant = 0
    if (  0.0 <= alpha0 <  90.0): quadrant = 1
    if ( 90.0 <= alpha0 < 180.0): quadrant = 2
    if (180.0 <= alpha0 < 270.0): quadrant = 3
    if (270.0 <= alpha0 < 360.0): quadrant = 4
    #
    assert quadrant in [1,2,3,4], "Erreur développeur %f" % alpha0
    # Récupération des valeurs qui seront mofifiées par le changement de quadrant
    IY0   = UneSect[ 'IY' ]
    IZ0   = UneSect[ 'IZ' ]
    EY0   = UneSect[ 'EY' ]
    EZ0   = UneSect[ 'EZ' ]
    AY0   = UneSect[ 'AY' ]
    AZ0   = UneSect[ 'AZ' ]
    RY0   = UneSect[ 'RY' ]
    RZ0   = UneSect[ 'RZ' ]
    IYR20 = UneSect[ 'IYR2' ]
    IZR20 = UneSect[ 'IZR2' ]
    # On met tout dans le 1er quadrant
    if (quadrant == 1):
        alpha1 = alpha0
        AY1 = AY0; AZ1 = AZ0
        RY1 = RY0; RZ1 = RZ0
        IY1 = IY0; IZ1 = IZ0
        EY1   =  EY0;   EZ1   =  EZ0
        IYR21 =  IYR20; IZR21 =  IZR20
    elif (quadrant == 2):
        alpha1 = alpha0 - 90.0
        AY1 = AZ0; AZ1 = AY0
        RY1 = RZ0; RZ1 = RY0
        IY1 = IZ0; IZ1 = IY0
        EY1   = -EZ0;   EZ1   =  EY0
        IYR21 = -IZR20; IZR21 =  IYR20
    elif (quadrant == 3):
        alpha1 = alpha0 - 180.0
        AY1 = AY0; AZ1 = AZ0
        RY1 = RY0; RZ1 = RZ0
        IY1 = IY0; IZ1 = IZ0
        EY1   = -EY0;   EZ1   = -EZ0
        IYR21 = -IYR20; IZR21 = -IZR20
    elif (quadrant == 4):
        alpha1 = alpha0 - 270.0
        AY1 = AZ0; AZ1 = AY0
        RY1 = RZ0; RZ1 = RY0
        IY1 = IZ0; IZ1 = IY0
        EY1   =  EZ0;   EZ1   = -EY0
        IYR21 =  IZR20; IZR21 = -IYR20
    #
    # Les valeurs ont toutes été mises dans le quadrant 1
    #   On passe dans NewQuadrant
    if (NewQuadrant == 1):
        alpha = alpha1
        AY = AY1; AZ = AZ1
        RY = RY1; RZ = RZ1
        IY = IY1; IZ = IZ1
        EY   =  EY1;   EZ   =  EZ1
        IYR2 =  IYR21; IZR2 =  IZR21
    elif (NewQuadrant == 2):
        alpha = alpha1 + 90.0
        AY = AZ1; AZ = AY1
        RY = RZ1; RZ = RY1
        IY = IZ1; IZ = IY1
        EY   =  EZ1;   EZ   = -EY1
        IYR2 =  IZR21; IZR2 = -IYR21
    elif (NewQuadrant == 3):
        alpha = alpha1 + 180.0
        AY = AY1; AZ = AZ1
        RY = RY1; RZ = RZ1
        IY = IY1; IZ = IZ1
        EY   = -EY1;   EZ   = -EZ1
        IYR2 = -IYR21; IZR2 = -IZR21
    elif (NewQuadrant == 4):
        alpha =alpha1 + 270.0
        AY = AZ1; AZ = AY1
        RY = RZ1; RZ = RY1
        IY = IZ1; IZ = IY1
        EY   = -EZ1;   EZ   =  EY1
        IYR2 = -IZR21; IZR2 =  IYR21
    #
    resu = {
        "ALPHA" : alpha,
        "IY"    : IY,
        "IZ"    : IZ,
        "EY"    : EY,
        "EZ"    : EZ,
        "AY"    : AY,
        "AZ"    : AZ,
        "RY"    : RY,
        "RZ"    : RZ,
        "IYR2"  : IYR2,
        "IZR2"  : IZR2,
    }
    return resu
# fmt: on


def macr_cara_poutre_ops(
    self,
    MAILLAGE=None,
    SYME_Y=None,
    SYME_Z=None,
    GROUP_MA_BORD=None,
    GROUP_MA=None,
    ORIG_INER=None,
    TABLE_CARA=None,
    **args,
):
    """
    Ecriture de la macro MACR_CARA_POUTRE
    """
    #
    #
    ImprTable = False
    #
    UNITE = args.get("UNITE") or 20
    if MAILLAGE is not None:
        __nomlma = COPIER(CONCEPT=MAILLAGE)
    else:
        __nomlma = LIRE_MAILLAGE(UNITE=UNITE, FORMAT=args.get("FORMAT"))
    #
    # Dans les tables on retrouve une ligne avec __nomlma.nom. Soit :
    #   - on remplace __nomlma.nom par NomMaillageNew.
    #   - on supprime la ligne
    NomMaillage = (None, __nomlma.getName())
    if "NOM" in args:
        NomMaillage = (args.get("NOM"), __nomlma.getName())
    #
    #
    __nomamo = AFFE_MODELE(
        MAILLAGE=__nomlma, AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="D_PLAN")
    )
    #
    __nomdma = DEFI_MATERIAU(ELAS=_F(E=1.0, NU=0.0, RHO=1.0))
    #
    __nomama = AFFE_MATERIAU(MAILLAGE=__nomlma, AFFE=_F(TOUT="OUI", MATER=__nomdma))
    #
    DLZ = DEFI_LIST_REEL(VALE=(0.0))
    #
    LeQuadrant9 = args.get("QUADRANT") or 0
    #
    # L'utilisateur ne peut rien faire pour éviter ces "Alarmes" donc pas d'impression
    MasquerAlarme("CHARGES2_87")
    MasquerAlarme("CALCULEL_40")
    #
    #
    # calcul des caractéristiques géométriques de la section
    motsimps = {}
    if GROUP_MA:
        motsimps["GROUP_MA"] = GROUP_MA
    if SYME_Y:
        motsimps["SYME_X"] = SYME_Y
    if SYME_Z:
        motsimps["SYME_Y"] = SYME_Z
    motsimps["ORIG_INER"] = ORIG_INER
    mfact = _F(TOUT="OUI", **motsimps)
    __cageo = POST_ELEM(MODELE=__nomamo, CHAM_MATER=__nomama, CARA_GEOM=mfact)
    #
    # Création d'un modèle plan 2D thermique représentant la section
    # de la poutre car on doit résoudre des E.D.P. avec des laplaciens
    #
    # Calcul de la constante de torsion sur tout le maillage
    # du centre de torsion/cisaillement des coefficients de cisaillement
    # de l inertie de gauchissement
    # du rayon de torsion
    #
    if GROUP_MA_BORD and not GROUP_MA:
        # Transformation des GROUP_MA en GROUP_NO sur lesquels
        # on pourra appliquer des conditions de température imposée
        #
        # les groupes doivent exister
        if type(GROUP_MA_BORD) == str:
            l_group_ma_bord = [GROUP_MA_BORD]
        else:
            l_group_ma_bord = GROUP_MA_BORD
        for igr in l_group_ma_bord:
            if not __nomlma.hasGroupOfCells(igr.strip()):
                UTMESS("F", "POUTRE0_20", valk=[igr, "GROUP_MA_BORD"])
        if "GROUP_MA_INTE" in args:
            if args.get("GROUP_MA_INTE") is not None:
                if type(args.get("GROUP_MA_INTE")) is str:
                    l_group_ma_inte = [args.get("GROUP_MA_INTE")]
                else:
                    l_group_ma_inte = args.get("GROUP_MA_INTE")
                for igr in l_group_ma_inte:
                    if not __nomlma.hasGroupOfCells(igr.strip()):
                        UTMESS("F", "POUTRE0_20", valk=[igr, "GROUP_MA_INTE"])
        #
        motscles = {}
        if type(GROUP_MA_BORD) == str:
            motscles["CREA_GROUP_NO"] = _F(GROUP_MA=GROUP_MA_BORD)
        else:
            motscles["CREA_GROUP_NO"] = []
            for grma in GROUP_MA_BORD:
                motscles["CREA_GROUP_NO"].append(_F(GROUP_MA=grma))
        #
        __nomlma = DEFI_GROUP(reuse=__nomlma, MAILLAGE=__nomlma, **motscles)

        # Création d'un maillage identique au premier a ceci près
        # que les coordonnées sont exprimées dans le repère principal
        # d'inertie dont l'origine est le centre de gravite de la section
        __nomapi = CREA_MAILLAGE(MAILLAGE=__nomlma, REPERE=_F(TABLE=__cageo, NOM_ORIG="CDG"))

        # Affectation du phénomène 'thermique' au modèle en vue de
        # la construction d un opérateur laplacien sur ce modèle
        __nomoth = AFFE_MODELE(
            MAILLAGE=__nomapi, AFFE=_F(TOUT="OUI", PHENOMENE="THERMIQUE", MODELISATION="PLAN")
        )

        # Pour la construction du laplacien, on définit un matériau dont les
        # caractéristiques thermiques sont : lambda = 1, rho*cp = 0
        __nomath = DEFI_MATERIAU(THER=_F(LAMBDA=1.0, RHO_CP=0.0))

        # Définition d'un CHAM_MATER à partir du matériau précédent
        __chmath = AFFE_MATERIAU(MAILLAGE=__nomapi, AFFE=_F(TOUT="OUI", MATER=__nomath))

        # CALCUL DE LA CONSTANTE DE TORSION PAR RESOLUTION
        # D UN LAPLACIEN AVEC UN TERME SOURCE EGAL A -2
        # L INCONNUE ETANT NULLE SUR LE CONTOUR DE LA SECTION :
        #     LAPLACIEN(PHI) = -2 DANS LA SECTION
        #     PHI = 0 SUR LE CONTOUR :
        # ------------------------------------------------------------
        #
        #  ON IMPOSE LA VALEUR 0 A L INCONNUE SCALAIRE SUR LE CONTOUR DE LA SECTION
        #  ET ON A UN TERME SOURCE EGAL A -2 DANS TOUTE LA SECTION
        # ------------------------------------------------------------
        motscles = {}
        if "GROUP_MA_INTE" in args:
            if args.get("GROUP_MA_INTE") is not None:
                motscles["LIAISON_UNIF"] = (_F(GROUP_MA=args.get("GROUP_MA_INTE"), DDL="TEMP"),)

        __chart1 = AFFE_CHAR_THER(
            MODELE=__nomoth,
            TEMP_IMPO=_F(GROUP_NO=GROUP_MA_BORD, TEMP=0.0),
            SOURCE=_F(TOUT="OUI", SOUR=2.0),
            **motscles,
        )

        # POUR CHAQUE TROU DE LA SECTION :
        # ON A IMPOSE QUE PHI EST CONSTANT SUR LE CONTOUR INTERIEUR
        # EN FAISANT LE LIAISON_UNIF DANS LE AFFE_CHAR_THER PRECEDENT
        # ON IMPOSE EN PLUS D(PHI)/DN = 2*AIRE(TROU)/L(TROU)
        # OU D/DN DESIGNE LA DERIVEE PAR RAPPORT A LA
        # NORMALE ET L DESIGNE LA LONGUEUR DU BORD DU TROU :
        if "GROUP_MA_INTE" in args:
            lgmaint = args.get("GROUP_MA_INTE")
            if lgmaint is not None:
                __tbaire = POST_ELEM(
                    MODELE=__nomoth, AIRE_INTERNE=_F(GROUP_MA_BORD=args.get("GROUP_MA_INTE"))
                )

                motscles = {}
                motscles["FLUX_REP"] = []

                if type(lgmaint) == str:
                    motscles["FLUX_REP"] = _F(
                        GROUP_MA=args.get("GROUP_MA_INTE"), CARA_TORSION=__tbaire
                    )
                else:
                    motscles["FLUX_REP"] = []
                    for grma in lgmaint:
                        motscles["FLUX_REP"].append(_F(GROUP_MA=grma, CARA_TORSION=__tbaire))
                __chart2 = AFFE_CHAR_THER(MODELE=__nomoth, **motscles)

        # ------------------------------------------------------------
        # RESOLUTION DE LAPLACIEN(PHI) = -2
        # AVEC PHI = 0 SUR LE CONTOUR :
        motscles = {}
        motscles["EXCIT"] = [_F(CHARGE=__chart1)]
        if "GROUP_MA_INTE" in args:
            if lgmaint is not None:
                motscles["EXCIT"].append(_F(CHARGE=__chart2))
        __tempe1 = THER_LINEAIRE(
            MODELE=__nomoth,
            CHAM_MATER=__chmath,
            SOLVEUR=_F(STOP_SINGULIER="NON"),
            TYPE_CALCUL="STAT",
            INCREMENT=_F(LIST_INST=DLZ),
            **motscles,
        )

        # ------------------------------------------------------------
        # CALCUL DU  CENTRE DE TORSION/CISAILLEMENT  -
        # ET DES COEFFICIENTS DE CISAILLEMENT :      -
        #
        # POUR LE CALCUL DES CONSTANTES DE CISAILLEMENT, ON VA DEFINIR
        # UN PREMIER TERME SOURCE, SECOND MEMBRE DE L EQUATION DE LAPLACE
        # PAR UNE FONCTION EGALE A Y :
        __fnsec1 = DEFI_FONCTION(
            NOM_PARA="X",
            VALE=(0.0, 0.0, 10.0, 10.0),
            PROL_DROITE="LINEAIRE",
            PROL_GAUCHE="LINEAIRE",
        )

        __fnsec0 = DEFI_CONSTANTE(VALE=0.0)

        # ------------------------------------------------------------
        # LE TERME SOURCE CONSTITUANT LE SECOND MEMBRE DE L ÉQUATION
        # DE LAPLACE EST PRIS ÉGAL A Y DANS TOUTE LA SECTION :
        mctimpo = {}
        if args.get("GROUP_NO") is not None:
            if len(args.get("GROUP_NO")) != 1:
                UTMESS("F", "POUTRE0_3")
            grthno = args.get("GROUP_NO")[0]
            # Plantage si grthno n'existe pas dans le maillage
            if not __nomapi.hasGroupOfNodes(grthno):
                UTMESS("F", "POUTRE0_8", valk=grthno)

            if len(__nomapi.getNodes(grthno, localNumbering=True)) != 1:
                UTMESS("F", "POUTRE0_3")

            mctimpo["TEMP_IMPO"] = _F(GROUP_NO=grthno, TEMP=__fnsec0)
        #
        __chart2 = AFFE_CHAR_THER_F(
            MODELE=__nomoth, SOURCE=_F(TOUT="OUI", SOUR=__fnsec1), **mctimpo
        )

        # ------------------------------------------------------------
        # RESOLUTION DE   LAPLACIEN(PHI) = -Y
        #                 AVEC D(PHI)/D(N) = 0 SUR LE CONTOUR :
        __tempe2 = THER_LINEAIRE(
            MODELE=__nomoth,
            CHAM_MATER=__chmath,
            EXCIT=_F(CHARGE=__chart2),
            SOLVEUR=_F(STOP_SINGULIER="NON"),
            TYPE_CALCUL="STAT",
            INCREMENT=_F(LIST_INST=DLZ),
        )

        # ------------------------------------------------------------
        # POUR LE CALCUL DES CONSTANTES DE CISAILLEMENT, ON VA DEFINIR
        # UN PREMIER TERME SOURCE, SECOND MEMBRE DE L EQUATION DE LAPLACE
        # PAR UNE FONCTION EGALE A Z :
        __fnsec2 = DEFI_FONCTION(
            NOM_PARA="Y",
            VALE=(0.0, 0.0, 10.0, 10.0),
            PROL_DROITE="LINEAIRE",
            PROL_GAUCHE="LINEAIRE",
        )

        # ------------------------------------------------------------
        # LE TERME SOURCE CONSTITUANT LE SECOND MEMBRE DE L EQUATION
        # DE LAPLACE EST PRIS EGAL A Z DANS TOUTE LA SECTION :
        __chart3 = AFFE_CHAR_THER_F(
            MODELE=__nomoth, SOURCE=_F(TOUT="OUI", SOUR=__fnsec2), **mctimpo
        )

        # ------------------------------------------------------------
        # RESOLUTION DE   LAPLACIEN(PHI) = -Z
        #                 AVEC D(PHI)/D(N) = 0 SUR LE CONTOUR :
        __tempe3 = THER_LINEAIRE(
            MODELE=__nomoth,
            CHAM_MATER=__chmath,
            EXCIT=_F(CHARGE=__chart3),
            SOLVEUR=_F(STOP_SINGULIER="NON"),
            TYPE_CALCUL="STAT",
            INCREMENT=_F(LIST_INST=DLZ),
        )

        # ------------------------------------------------------------
        # CALCUL DU RAYON DE TORSION :
        # CALCUL DU RAYON DE TORSION EXTERNE : rtext
        __tempe1 = CALC_CHAMP(
            reuse=__tempe1, RESULTAT=__tempe1, TOUT_ORDRE="OUI", THERMIQUE="FLUX_ELNO"
        )

        __flun = MACR_LIGN_COUPE(
            RESULTAT=__tempe1,
            NOM_CHAM="FLUX_ELNO",
            LIGN_COUPE=_F(
                TYPE="GROUP_MA",
                MAILLAGE=__nomapi,
                TRAC_NOR="OUI",
                NOM_CMP=("FLUX", "FLUY"),
                OPERATION="MOYENNE",
                INTITULE="FLUX_NORM",
                GROUP_MA=GROUP_MA_BORD,
            ),
        )
        __nomapi = DEFI_GROUP(
            reuse=__nomapi, MAILLAGE=__nomapi, DETR_GROUP_NO=_F(NOM=GROUP_MA_BORD)
        )

        __m1 = abs(__flun["TRAC_NOR", 3])
        __m2 = abs(__flun["TRAC_NOR", 4])
        __rtext = max(__m1, __m2)

        #    CALCUL DU RAYON DE TORSION : rt
        #    rt = max ( rtext , 2*AIRE(TROU)/L(TROU) )
        if "GROUP_MA_INTE" in args:
            if args.get("GROUP_MA_INTE") is not None:
                if type(args.get("GROUP_MA_INTE")) is str:
                    l_group_ma_inte = [args.get("GROUP_MA_INTE")]
                else:
                    l_group_ma_inte = args.get("GROUP_MA_INTE")
                for i in range(0, len(l_group_ma_inte)):
                    __flun = MACR_LIGN_COUPE(
                        RESULTAT=__tempe1,
                        NOM_CHAM="FLUX_ELNO",
                        LIGN_COUPE=_F(
                            TYPE="GROUP_MA",
                            MAILLAGE=__nomapi,
                            TRAC_NOR="OUI",
                            NOM_CMP=("FLUX", "FLUY"),
                            OPERATION="MOYENNE",
                            INTITULE="FLUX_NORM",
                            GROUP_MA=l_group_ma_inte[i],
                        ),
                    )
                    __nomapi = DEFI_GROUP(
                        reuse=__nomapi, MAILLAGE=__nomapi, DETR_GROUP_NO=_F(NOM=l_group_ma_inte[i])
                    )

                    __m1 = (abs(__flun["TRAC_NOR", 3]) + abs(__flun["TRAC_NOR", 4])) / 2.0
                    if __m1 > __rtext:
                        __rtext = __m1
        #
        __rt = __rtext

        # ------------------------------------------------------------
        # CALCUL DE LA CONSTANTE DE TORSION :
        motscles = {}
        lgmaint = args.get("GROUP_MA_INTE")
        if lgmaint is not None:
            motscles["CARA_POUTRE"] = _F(
                CARA_GEOM=__cageo,
                LAPL_PHI=__tempe1,
                RT=__rt,
                TOUT="OUI",
                OPTION="CARA_TORSION",
                GROUP_MA_INTE=args.get("GROUP_MA_INTE"),
            )
        else:
            motscles["CARA_POUTRE"] = _F(
                CARA_GEOM=__cageo, LAPL_PHI=__tempe1, RT=__rt, TOUT="OUI", OPTION="CARA_TORSION"
            )
        #
        __cator = POST_ELEM(MODELE=__nomoth, CHAM_MATER=__chmath, **motscles)

        # ------------------------------------------------------------
        # CALCUL DES COEFFICIENTS DE CISAILLEMENT ET DES COORDONNEES DU
        # CENTRE DE CISAILLEMENT/TORSION :
        __cacis = POST_ELEM(
            MODELE=__nomoth,
            CHAM_MATER=__chmath,
            CARA_POUTRE=_F(
                CARA_GEOM=__cator,
                LAPL_PHI_Y=__tempe2,
                LAPL_PHI_Z=__tempe3,
                TOUT="OUI",
                OPTION="CARA_CISAILLEMENT",
            ),
        )

        # Coordonnées du centre de torsion dans le repère du maillage
        # Dans la TABLE __cacis (PCTY, PCTZ)=(CG) exprimé dans le GYZ
        #   On récupère (CDG_Y_M, CDG_Z_M)
        #   OC = OG + GC = (CDG_Y_M, CDG_Z_M) - (PCTY, PCTZ)
        # print("DBG: Table cisaillement"); IMPR_TABLE(TABLE=__cacis,UNITE=6)
        # On garde la ligne avec LIEU
        __TabTmp = CALC_TABLE(
            TABLE=__cacis,
            TYPE_TABLE="TABLE",
            ACTION=_F(OPERATION="FILTRE", NOM_PARA="LIEU", CRIT_COMP="NON_VIDE"),
        )
        #
        TabTmp = __TabTmp.EXTR_TABLE()
        assert len(TabTmp.rows) == 1, "Erreur : Calcul de PTOC_M_(Y,Z)"
        ligne = TabTmp.rows[0]
        # print("DBG: Traitement ligne : ", ligne)
        #
        ogy, ogz = ligne["CDG_Y_M"], ligne["CDG_Z_M"]
        cgy, cgz = ligne["PCTY"], ligne["PCTZ"]
        ptoc_m_y = ogy - cgy
        ptoc_m_z = ogz - cgz
        # print("DBG: PTOC_M_(Y,Z) : ", ptoc_m_y, ptoc_m_z)

        # ------------------------------------------------------------
        #  CALCUL DE L INERTIE DE GAUCHISSEMENT PAR RESOLUTION  DE  -
        #     LAPLACIEN(OMEGA) = 0     DANS LA SECTION              -
        #     AVEC D(OMEGA)/D(N) = Z*NY-Y*NZ   SUR LE               -
        #     CONTOUR DE LA SECTION                                 -
        #     NY ET NZ SONT LES COMPOSANTES DU VECTEUR N NORMAL     -
        #     A CE CONTOUR                                          -
        #     ET SOMME_S(OMEGA.DS) = 0                              -
        #     OMEGA EST LA FONCTION DE GAUCHISSEMENT                -
        #     L INERTIE DE GAUCHISSEMENT EST SOMME_S(OMEGA**2.DS)   -
        # -----------------------------------------------------------
        #
        #  CREATION D UN MAILLAGE DONT LES COORDONNEES SONT EXPRIMEES
        #  DANS LE REPERE PRINCIPAL D INERTIE MAIS AVEC COMME ORIGINE
        #  LE CENTRE DE TORSION DE LA SECTION, ON VA DONC UTILISER
        #  LE MAILLAGE DE NOM NOMAPI DONT LES COORDONNEES SONT
        #  EXPRIMEES DANS LE REPERE PRINCIPAL D'INERTIE, L'ORIGINE
        #  ETANT LE CENTRE DE GRAVITE DE LA SECTION (QUI EST DONC A CHANGER)
        __nomapt = CREA_MAILLAGE(MAILLAGE=__nomapi, REPERE=_F(TABLE=__cacis, NOM_ORIG="TORSION"))

        # ------------------------------------------------------------
        # AFFECTATION DU PHENOMENE 'THERMIQUE' AU MODELE EN VUE DE
        # LA CONSTRUCTION D UN OPERATEUR LAPLACIEN SUR CE MODELE :
        __nomot2 = AFFE_MODELE(
            MAILLAGE=__nomapt, AFFE=_F(TOUT="OUI", PHENOMENE="THERMIQUE", MODELISATION="PLAN")
        )

        # DEFINITION D UN CHAM_MATER A PARTIR DU MATERIAU PRECEDENT :
        __chmat2 = AFFE_MATERIAU(MAILLAGE=__nomapt, AFFE=_F(TOUT="OUI", MATER=__nomath))

        # POUR LE CALCUL DE L INERTIE DE GAUCHISSEMENT, ON VA DEFINIR
        # LA COMPOSANTE SELON Y DU FLUX A IMPOSER SUR LE CONTOUR
        # PAR UNE FONCTION EGALE A -X :
        __fnsec3 = DEFI_FONCTION(
            NOM_PARA="X",
            VALE=(0.0, 0.0, 10.0, -10.0),
            PROL_DROITE="LINEAIRE",
            PROL_GAUCHE="LINEAIRE",
        )

        # POUR LE CALCUL DE L INERTIE DE GAUCHISSEMENT, ON VA DEFINIR
        # LA COMPOSANTE SELON X DU FLUX A IMPOSER SUR LE CONTOUR
        # PAR UNE FONCTION EGALE A Y :
        __fnsec4 = DEFI_FONCTION(
            NOM_PARA="Y",
            VALE=(0.0, 0.0, 10.0, 10.0),
            PROL_DROITE="LINEAIRE",
            PROL_GAUCHE="LINEAIRE",
        )

        # DANS LE BUT D IMPOSER LA RELATION LINEAIRE ENTRE DDLS
        #  SOMME_SECTION(OMEGA.DS) = 0 ( CETTE CONDITION
        # VENANT DE L EQUATION D EQUILIBRE SELON L AXE DE LA POUTRE
        # N = 0, N ETANT L EFFORT NORMAL)
        # ON CALCULE LE VECTEUR DE CHARGEMENT DU A UN TERME SOURCE EGAL
        # A 1., LES TERMES DE CE VECTEUR SONT EGAUX A
        # SOMME_SECTION(NI.DS) ET SONT DONC LES COEFFICIENTS DE
        # LA RELATION LINEAIRE A IMPOSER.
        # ON DEFINIT DONC UN CHARGEMENT DU A UN TERME SOURCE EGAL A 1 :
        __chart4 = AFFE_CHAR_THER(MODELE=__nomot2, SOURCE=_F(TOUT="OUI", SOUR=1.0))

        # ON CALCULE LE VECT_ELEM DU AU CHARGEMENT PRECEDENT
        # IL S AGIT DES VECTEURS ELEMENTAIRES DONT LE TERME
        # AU NOEUD COURANT I EST EGAL A SOMME_SECTION(NI.DS) :
        __vecel = CALC_VECT_ELEM(CHARGE=__chart4, OPTION="CHAR_THER")

        # ON CALCULE LE MATR_ELEM DES MATRICES ELEMENTAIRES
        # DE CONDUCTIVITE UNIQUEMENT POUR GENERER LE NUME_DDL
        # SUR-LEQUEL S APPUIERA LE CHAMNO UTILISE POUR ECRIRE LA
        # RELATION LINEAIRE ENTRE DDLS :
        __matel = CALC_MATR_ELEM(
            MODELE=__nomot2, CHAM_MATER=__chmat2, CHARGE=__chart4, OPTION="RIGI_THER"
        )

        # ON DEFINIT LE NUME_DDL ASSOCIE AU MATR_ELEM DEFINI
        # PRECEDEMMENT POUR CONSTRUIRE LE CHAMNO UTILISE POUR ECRIRE LA
        # RELATION LINEAIRE ENTRE DDLS :
        __numddl = NUME_DDL(MATR_RIGI=__matel)

        # ON CONSTRUIT LE CHAMNO QUI VA ETRE UTILISE POUR ECRIRE LA
        # RELATION LINEAIRE ENTRE DDLS :
        __chamno = ASSE_VECTEUR(VECT_ELEM=__vecel, NUME_DDL=__numddl)

        # ON IMPOSE LA RELATION LINEAIRE ENTRE DDLS
        #  SOMME_SECTION(OMEGA.DS) = 0 ( CETTE CONDITION
        # VENANT DE L EQUATION D EQUILIBRE SELON L AXE DE LA POUTRE
        # N = 0, N ETANT L EFFORT NORMAL)
        # POUR IMPOSER CETTE RELATION ON PASSE PAR LIAISON_CHAMNO,
        # LES TERMES DU CHAMNO (I.E. SOMME_SECTION(NI.DS))
        # SONT LES COEFFICIENTS DE LA RELATION LINEAIRE :
        __chart5 = AFFE_CHAR_THER(
            MODELE=__nomot2, LIAISON_CHAMNO=_F(CHAM_NO=__chamno, COEF_IMPO=0.0)
        )

        # LE CHARGEMENT EST UN FLUX REPARTI NORMAL AU CONTOUR
        # DONT LES COMPOSANTES SONT +Z (I.E. +Y) ET -Y (I.E. -X)
        # SELON LA DIRECTION NORMALE AU CONTOUR :
        __chart6 = AFFE_CHAR_THER_F(
            MODELE=__nomot2, FLUX_REP=_F(GROUP_MA=GROUP_MA_BORD, FLUX_X=__fnsec4, FLUX_Y=__fnsec3)
        )

        # RESOLUTION DE     LAPLACIEN(OMEGA) = 0
        # AVEC D(OMEGA)/D(N) = Z*NY-Y*NZ   SUR LE CONTOUR DE LA SECTION
        # ET SOMME_SECTION(OMEGA.DS) = 0 ( CETTE CONDITION
        # VENANT DE L EQUATION D EQUILIBRE SELON L AXE DE LA POUTRE
        # N = 0, N ETANT L EFFORT NORMAL)  :
        __tempe4 = THER_LINEAIRE(
            MODELE=__nomot2,
            CHAM_MATER=__chmat2,
            EXCIT=(_F(CHARGE=__chart5), _F(CHARGE=__chart6)),
            SOLVEUR=_F(STOP_SINGULIER="NON", METHODE="LDLT"),
            TYPE_CALCUL="STAT",
            INCREMENT=_F(LIST_INST=DLZ),
        )

        # CALCUL DE L INERTIE DE GAUCHISSEMENT :
        __tabtmp = POST_ELEM(
            MODELE=__nomot2,
            CHAM_MATER=__chmat2,
            CARA_POUTRE=_F(CARA_GEOM=__cacis, LAPL_PHI=__tempe4, TOUT="OUI", OPTION="CARA_GAUCHI"),
        )

    # ==================================================================
    # = CALCUL DE LA CONSTANTE DE TORSION SUR CHAQUE GROUPE            =
    # =     ET DU RAYON DE TORSION SUR CHAQUE GROUPE                   =
    # =        DU  CENTRE DE TORSION/CISAILLEMENT                      =
    # =        DES COEFFICIENTS DE CISAILLEMENT                        =
    # ==================================================================
    if GROUP_MA_BORD and GROUP_MA:
        # CALCUL DES CARACTERISTIQUES GEOMETRIQUES DE LA SECTION :
        l_group_ma_bord = GROUP_MA_BORD
        l_group_ma = GROUP_MA
        l_noeud = None
        #
        if len(l_group_ma) != len(l_group_ma_bord):
            UTMESS("F", "POUTRE0_1")
        #
        # les groupes doivent exister
        for igr in l_group_ma_bord:
            if not __nomlma.hasGroupOfCells(igr.strip()):
                UTMESS("F", "POUTRE0_20", valk=[igr, "GROUP_MA_BORD"])
        #
        for igr in GROUP_MA:
            if not __nomlma.hasGroupOfCells(igr.strip()):
                UTMESS("F", "POUTRE0_20", valk=[igr, "GROUP_MA"])
        #
        if "GROUP_MA_INTE" in args:
            if args.get("GROUP_MA_INTE") is not None:
                if type(args.get("GROUP_MA_INTE")) is str:
                    l_group_ma_inte = [args.get("GROUP_MA_INTE")]
                else:
                    l_group_ma_inte = args.get("GROUP_MA_INTE")
                for igr in l_group_ma_inte:
                    if not __nomlma.hasGroupOfCells(igr.strip()):
                        UTMESS("F", "POUTRE0_20", valk=[igr, "GROUP_MA_INTE"])

        if args.get("GROUP_NO") is not None:
            l_noeud = []
            for grno in args.get("GROUP_NO"):
                if __nomlma.hasGroupOfNodes(grno):
                    l_noeud.extend(__nomlma.getNodes(grno, localNumbering=True))
                else:
                    UTMESS("F", "POUTRE0_8", valk=grno)
            if len(l_group_ma) != len(l_noeud):
                UTMESS("F", "POUTRE0_5")

        # Si len(l_group_ma_bord) > 1, alors il faut donner : 'LONGUEUR', 'MATERIAU', 'LIAISON'
        if len(l_group_ma_bord) > 1:
            if not args.get("LONGUEUR") or not args.get("MATERIAU") or not args.get("LIAISON"):
                UTMESS("F", "POUTRE0_6")
        else:
            if args.get("LONGUEUR") or args.get("MATERIAU") or args.get("LIAISON"):
                UTMESS("A", "POUTRE0_7")

        __catp2 = __cageo
        for i in range(0, len(l_group_ma_bord)):
            # TRANSFORMATION DES GROUP_MA EN GROUP_NO SUR-LESQUELS
            # ON POURRA APPLIQUER DES CONDITIONS DE TEMPERATURE IMPOSEE :
            __nomlma = DEFI_GROUP(
                reuse=__nomlma,
                MAILLAGE=__nomlma,
                DETR_GROUP_NO=_F(NOM=l_group_ma_bord[i]),
                CREA_GROUP_NO=_F(GROUP_MA=l_group_ma_bord[i]),
            )

            # CREATION D UN MAILLAGE IDENTIQUE AU PREMIER A CECI PRES
            # QUE LES COORDONNEES SONT EXPRIMEES DANS LE REPERE PRINCIPAL
            # D INERTIE DONT L ORIGINE EST LE CENTRE DE GRAVITE DE LA SECTION :
            __nomapi = CREA_MAILLAGE(
                MAILLAGE=__nomlma, REPERE=_F(TABLE=__cageo, NOM_ORIG="CDG", GROUP_MA=l_group_ma[i])
            )

            # AFFECTATION DU PHENOMENE 'THERMIQUE' AU MODELE EN VUE DE
            # LA CONSTRUCTION D UN OPERATEUR LAPLACIEN SUR CE MODELE :
            __nomoth = AFFE_MODELE(
                MAILLAGE=__nomapi,
                AFFE=_F(GROUP_MA=l_group_ma[i], PHENOMENE="THERMIQUE", MODELISATION="PLAN"),
            )

            # POUR LA CONSTRUCTION DU LAPLACIEN, ON  DEFINIT UN
            # PSEUDO-MATERIAU DONT LES CARACTERISTIQUES THERMIQUES SONT :
            # LAMBDA = 1, RHO*CP = 0 :
            __nomath = DEFI_MATERIAU(THER=_F(LAMBDA=1.0, RHO_CP=0.0))

            # DEFINITION D UN CHAM_MATER A PARTIR DU MATERIAU PRECEDENT :
            __chmath = AFFE_MATERIAU(MAILLAGE=__nomapi, AFFE=_F(TOUT="OUI", MATER=__nomath))

            # CALCUL DE LA CONSTANTE DE TORSION PAR RESOLUTION         -
            # D UN LAPLACIEN AVEC UN TERME SOURCE EGAL A -2            -
            # L INCONNUE ETANT NULLE SUR LE CONTOUR DE LA SECTION :    -
            #    LAPLACIEN(PHI) = -2 DANS LA SECTION                   -
            #    PHI = 0 SUR LE CONTOUR :                              -
            #
            # ON IMPOSE LA VALEUR 0 A L INCONNUE SCALAIRE SUR LE CONTOUR
            # DE LA SECTION
            # ET ON A UN TERME SOURCE EGAL A -2 DANS TOUTE LA SECTION :
            __chart1 = AFFE_CHAR_THER(
                MODELE=__nomoth,
                TEMP_IMPO=_F(GROUP_NO=l_group_ma_bord[i], TEMP=0.0),
                SOURCE=_F(TOUT="OUI", SOUR=2.0),
            )

            # RESOLUTION DE   LAPLACIEN(PHI) = -2
            #                 AVEC PHI = 0 SUR LE CONTOUR :
            __tempe1 = THER_LINEAIRE(
                MODELE=__nomoth,
                CHAM_MATER=__chmath,
                EXCIT=_F(CHARGE=__chart1),
                SOLVEUR=_F(STOP_SINGULIER="NON"),
                TYPE_CALCUL="STAT",
                INCREMENT=_F(LIST_INST=DLZ),
            )

            # ----------------------------------------------
            # CALCUL DU  CENTRE DE TORSION/CISAILLEMENT
            # ET DES COEFFICIENTS DE CISAILLEMENT :
            #
            # POUR LE CALCUL DES CONSTANTES DE CISAILLEMENT, ON VA DEFINIR
            # UN PREMIER TERME SOURCE, SECOND MEMBRE DE L EQUATION DE LAPLACE
            # PAR UNE FONCTION EGALE A Y :
            __fnsec1 = DEFI_FONCTION(
                NOM_PARA="X",
                VALE=(0.0, 0.0, 10.0, 10.0),
                PROL_DROITE="LINEAIRE",
                PROL_GAUCHE="LINEAIRE",
            )

            __fnsec0 = DEFI_CONSTANTE(VALE=0.0)

            # LE TERME SOURCE CONSTITUANT LE SECOND MEMBRE DE L EQUATION
            # DE LAPLACE EST PRIS EGAL A Y DANS TOUTE LA SECTION :
            __nomapi.setGroupOfNodes("&&MACR_CARA_GNO", [l_noeud[i]])
            __chart2 = AFFE_CHAR_THER_F(
                MODELE=__nomoth,
                TEMP_IMPO=_F(GROUP_NO="&&MACR_CARA_GNO", TEMP=__fnsec0),
                SOURCE=_F(TOUT="OUI", SOUR=__fnsec1),
            )
            removeGroupNo(__nomapi, "&&MACR_CARA_GNO")

            # RESOLUTION DE   LAPLACIEN(PHI) = -Y
            #                 AVEC D(PHI)/D(N) = 0 SUR LE CONTOUR :
            __tempe2 = THER_LINEAIRE(
                MODELE=__nomoth,
                CHAM_MATER=__chmath,
                EXCIT=_F(CHARGE=__chart2),
                SOLVEUR=_F(STOP_SINGULIER="NON"),
                TYPE_CALCUL="STAT",
                INCREMENT=_F(LIST_INST=DLZ),
            )

            # POUR LE CALCUL DES CONSTANTES DE CISAILLEMENT, ON VA DEFINIR
            # UN PREMIER TERME SOURCE, SECOND MEMBRE DE L EQUATION DE LAPLACE
            # PAR UNE FONCTION EGALE A Z :
            __fnsec2 = DEFI_FONCTION(
                NOM_PARA="Y",
                VALE=(0.0, 0.0, 10.0, 10.0),
                PROL_DROITE="LINEAIRE",
                PROL_GAUCHE="LINEAIRE",
            )

            # LE TERME SOURCE CONSTITUANT LE SECOND MEMBRE DE L EQUATION
            # DE LAPLACE EST PRIS EGAL A Z DANS TOUTE LA SECTION :
            __nomapi.setGroupOfNodes("&&MACR_CARA_GNO", [l_noeud[i]])
            __chart3 = AFFE_CHAR_THER_F(
                MODELE=__nomoth,
                TEMP_IMPO=_F(GROUP_NO="&&MACR_CARA_GNO", TEMP=__fnsec0),
                SOURCE=_F(TOUT="OUI", SOUR=__fnsec2),
            )
            removeGroupNo(__nomapi, "&&MACR_CARA_GNO")

            # RESOLUTION DE   LAPLACIEN(PHI) = -Z
            #                 AVEC D(PHI)/D(N) = 0 SUR LE CONTOUR :
            __tempe3 = THER_LINEAIRE(
                MODELE=__nomoth,
                CHAM_MATER=__chmath,
                EXCIT=_F(CHARGE=__chart3),
                SOLVEUR=_F(STOP_SINGULIER="NON"),
                TYPE_CALCUL="STAT",
                INCREMENT=_F(LIST_INST=DLZ),
            )

            # CALCUL DU RAYON DE TORSION :
            # CALCUL DU RAYON DE TORSION EXTERNE : rtext
            __tempe1 = CALC_CHAMP(
                reuse=__tempe1, RESULTAT=__tempe1, TOUT_ORDRE="OUI", THERMIQUE="FLUX_ELNO"
            )

            __flun = MACR_LIGN_COUPE(
                RESULTAT=__tempe1,
                NOM_CHAM="FLUX_ELNO",
                LIGN_COUPE=_F(
                    TYPE="GROUP_MA",
                    MAILLAGE=__nomapi,
                    TRAC_NOR="OUI",
                    NOM_CMP=("FLUX", "FLUY"),
                    OPERATION="MOYENNE",
                    INTITULE="FLUX_NORM",
                    GROUP_MA=l_group_ma_bord[i],
                ),
            )
            __nomapi = DEFI_GROUP(
                reuse=__nomapi, MAILLAGE=__nomapi, DETR_GROUP_NO=_F(NOM=l_group_ma_bord[i])
            )

            __m1 = abs(__flun["TRAC_NOR", 3])
            __m2 = abs(__flun["TRAC_NOR", 4])
            __rtext = max(__m1, __m2)

            # CALCUL DU RAYON DE TORSION : rt
            # rt = max ( rtext , 2*AIRE(TROU)/L(TROU) )
            if "GROUP_MA_INTE" in args:
                if args.get("GROUP_MA_INTE") is not None:
                    if type(args.get("GROUP_MA_INTE")) is str:
                        l_group_ma_inte = [args.get("GROUP_MA_INTE")]
                    else:
                        l_group_ma_inte = args.get("GROUP_MA_INTE")

                    for j in range(0, len(l_group_ma_inte)):
                        __flun = MACR_LIGN_COUPE(
                            RESULTAT=__tempe1,
                            NOM_CHAM="FLUX_ELNO",
                            LIGN_COUPE=_F(
                                TYPE="GROUP_MA",
                                MAILLAGE=__nomapi,
                                TRAC_NOR="OUI",
                                NOM_CMP=("FLUX", "FLUY"),
                                OPERATION="MOYENNE",
                                INTITULE="FLUX_NORM",
                                GROUP_MA=l_group_ma_inte[i],
                            ),
                        )
                        __nomapi = DEFI_GROUP(
                            reuse=__nomapi,
                            MAILLAGE=__nomapi,
                            DETR_GROUP_NO=_F(NOM=l_group_ma_inte[i]),
                        )
                        __m1 = (abs(__flun["TRAC_NOR", 3]) + abs(__flun["TRAC_NOR", 4])) / 2.0
                        if __m1 > __rtext:
                            __rtext = __m1

            __rt = __rtext

            # CALCUL DE LA CONSTANTE DE TORSION :
            __catp1 = POST_ELEM(
                MODELE=__nomoth,
                CHAM_MATER=__chmath,
                CARA_POUTRE=_F(
                    CARA_GEOM=__catp2,
                    LAPL_PHI=__tempe1,
                    RT=__rt,
                    GROUP_MA=l_group_ma[i],
                    OPTION="CARA_TORSION",
                ),
            )

            # CALCUL DES COEFFICIENTS DE CISAILLEMENT ET DES COORDONNEES DU
            # CENTRE DE CISAILLEMENT/TORSION :
            if len(l_group_ma_bord) > 1:
                __catp2 = POST_ELEM(
                    MODELE=__nomoth,
                    CHAM_MATER=__chmath,
                    CARA_POUTRE=_F(
                        CARA_GEOM=__catp1,
                        LAPL_PHI_Y=__tempe2,
                        LAPL_PHI_Z=__tempe3,
                        GROUP_MA=l_group_ma[i],
                        LONGUEUR=args.get("LONGUEUR"),
                        MATERIAU=args.get("MATERIAU"),
                        LIAISON=args.get("LIAISON"),
                        OPTION="CARA_CISAILLEMENT",
                    ),
                )
            else:
                __nomtmp = DEFI_MATERIAU(ELAS=_F(E=1.0, NU=0.123, RHO=1.0))
                __catp2 = POST_ELEM(
                    MODELE=__nomoth,
                    CHAM_MATER=__chmath,
                    CARA_POUTRE=_F(
                        CARA_GEOM=__catp1,
                        LAPL_PHI_Y=__tempe2,
                        LAPL_PHI_Z=__tempe3,
                        GROUP_MA=l_group_ma[i],
                        LONGUEUR=123.0,
                        MATERIAU=__nomtmp,
                        LIAISON="ENCASTREMENT",
                        OPTION="CARA_CISAILLEMENT",
                    ),
                )
            #
        #
        dprod = __catp2.EXTR_TABLE().dict_CREA_TABLE()
        # On remplace dans le TITRE le nom du concept __catp2.getName() par self.sd.getName()
        if "TITRE" in list(dprod.keys()):
            conceptOld = __catp2.getName()
            # FIXME
            conceptNew = conceptOld  # self.sd.getName()
            for ii in range(len(dprod["TITRE"])):
                zz = dprod["TITRE"][ii]
                if conceptOld.strip() in zz:
                    dprod["TITRE"][ii] = zz.replace(conceptOld.strip(), conceptNew.strip())
        #
        __tabtmp = CREA_TABLE(**dprod)
    #
    if not GROUP_MA_BORD:
        __tabtmp = POST_ELEM(MODELE=__nomamo, CHAM_MATER=__nomama, CARA_GEOM=mfact)
    #
    # mise au propre de la table
    #
    # On enlève la ligne avec LIEU='-' et donc les colonnes TYPE_OBJET, NOM_SD
    # on utilise TYPE_TABLE pour forcer le type à table_sdaster et plus table_container
    nomres = CALC_TABLE(
        TABLE=__tabtmp,
        TYPE_TABLE="TABLE",
        ACTION=(_F(OPERATION="FILTRE", NOM_PARA="LIEU", CRIT_COMP="NON_VIDE"),),
    )

    NomMaillageNew, NomMaillageOld = NomMaillage

    # Suppression de la référence à NomMaillageOld, remplacé par NOM = NomMaillageNew
    # Si TABLE_CARA == "OUI" et GROUP_MA la ligne est supprimée
    if not (TABLE_CARA == "OUI" and GROUP_MA):
        TabTmp = nomres.EXTR_TABLE()
        for ii in range(len(TabTmp.rows)):
            zz = TabTmp.rows[ii]["LIEU"]
            if zz.strip() == NomMaillageOld:
                TabTmp.rows[ii]["LIEU"] = NomMaillageNew
        TabTmp = TabTmp.dict_CREA_TABLE()
    else:
        # Une ligne avec LIEU=NomMaillageOld ==> on la supprime
        nomres = CALC_TABLE(
            reuse=nomres,
            TABLE=nomres,
            ACTION=_F(OPERATION="FILTRE", NOM_PARA="LIEU", CRIT_COMP="NE", VALE_K=NomMaillageOld),
        )
        TabTmp = nomres.EXTR_TABLE().dict_CREA_TABLE()
    #
    nomres = CREA_TABLE(**TabTmp)
    #
    # On ajoute dans la table PTOC_M_Y, PTOC_M_Z
    if GROUP_MA_BORD and not GROUP_MA:
        # print("DBG: Ajout PTOC_M_(Y,Z)")
        TabTmp = nomres.EXTR_TABLE()
        assert len(TabTmp.rows) == 1, "Erreur : Ajout PCT_M_(Y,Z)"
        TabTmp["PCT_M_Y"] = [ptoc_m_y]
        TabTmp["PCT_M_Z"] = [ptoc_m_z]
        TabTmp = TabTmp.dict_CREA_TABLE()
        nomres = CREA_TABLE(**TabTmp)
        # print("DBG: : Ajout PTOC_M_(Y,Z) Table après modification"); IMPR_TABLE(TABLE=nomres,UNITE=6)
    #
    # print("DBG: Table avant modification"); IMPR_TABLE(TABLE=nomres,UNITE=6)
    TabTmp = nomres.EXTR_TABLE()
    for ii in range(len(TabTmp.rows)):
        ligne = TabTmp.rows[ii]
        if LeQuadrant9 != 0:
            # print("DBG: LeQuadrant9 : Traitement ligne %d : " % ii, ligne)
            resu = TraiteQuadrant(ligne, LeQuadrant9)
            # print("DBG: LeQuadrant9 : Résultat traitement : ", resu)
            for ikey, ival in resu.items():
                TabTmp.rows[ii][ikey] = ival
    # On refait la table
    TabTmp = TabTmp.dict_CREA_TABLE()
    nomres = CREA_TABLE(**TabTmp)
    # print("DBG: Table après modification"); IMPR_TABLE(TABLE=nomres,UNITE=6)
    #
    # On retourne une table exploitable par AFFE_CARA_ELEM, avec seulement les
    # caractéristiques nécessaires
    if TABLE_CARA == "OUI":
        #
        if GROUP_MA_BORD and not GROUP_MA:
            nomres = CALC_TABLE(
                TABLE=nomres,
                reuse=nomres,
                ACTION=(
                    _F(
                        OPERATION="EXTR",
                        NOM_PARA=(
                            "LIEU",
                            "A",
                            "IY",
                            "IZ",
                            "AY",
                            "AZ",
                            "EY",
                            "EZ",
                            "JX",
                            "JG",
                            "IYR2",
                            "IZR2",
                            "RY",
                            "RZ",
                            "RT",
                            "ALPHA",
                            "CDG_Y",
                            "CDG_Z",
                        ),
                    ),
                ),
            )
        elif GROUP_MA_BORD and GROUP_MA:
            nomres = CALC_TABLE(
                TABLE=nomres,
                reuse=nomres,
                ACTION=(
                    _F(
                        OPERATION="EXTR",
                        NOM_PARA=(
                            "LIEU",
                            "A",
                            "IY",
                            "IZ",
                            "AY",
                            "AZ",
                            "EY",
                            "EZ",
                            "JX",
                            "IYR2",
                            "IZR2",
                            "RY",
                            "RZ",
                            "RT",
                            "ALPHA",
                            "CDG_Y",
                            "CDG_Z",
                        ),
                    ),
                ),
            )
        else:
            nomres = CALC_TABLE(
                TABLE=nomres,
                reuse=nomres,
                ACTION=(
                    _F(
                        OPERATION="EXTR",
                        NOM_PARA=(
                            "LIEU",
                            "A",
                            "IY",
                            "IZ",
                            "IYR2",
                            "IZR2",
                            "RY",
                            "RZ",
                            "ALPHA",
                            "CDG_Y",
                            "CDG_Z",
                        ),
                    ),
                ),
            )
        #
        # Validation des résultats qui doivent toujours être >=0
        TabTmp = nomres.EXTR_TABLE()
        for ii in range(len(TabTmp.rows)):
            ligne = TabTmp.rows[ii]
            # on recherche la bonne ligne
            if ligne["LIEU"].strip() == NomMaillageNew:
                paras = TabTmp.para
                # Vérification des grandeurs qui doivent toujours rester positive
                Lparas = ("A", "IY", "IZ", "AY", "AZ", "JX", "JG")
                iergd = 0
                for unpara in Lparas:
                    if unpara in paras:
                        if ligne[unpara] <= 0:
                            iergd += 1
                if iergd != 0:
                    if not ImprTable:
                        IMPR_TABLE(TABLE=nomres)
                    ImprTable = True
                    for unpara in Lparas:
                        if unpara in paras:
                            if ligne[unpara] <= 0:
                                UTMESS("E", "POUTRE0_10", valk=unpara, valr=ligne[unpara])
                    UTMESS("F", "POUTRE0_11")
                #
                # Vérification que le CDG est l'origine du maillage
                cdgy = ligne["CDG_Y"]
                cdgz = ligne["CDG_Z"]
                dcdg = (cdgy * cdgy + cdgz * cdgz) / ligne["A"]
                if dcdg > 1.0e-08:
                    if not ImprTable:
                        IMPR_TABLE(TABLE=nomres)
                    ImprTable = True
                    NomResultat = "TabCara"
                    UTMESS("A", "POUTRE0_12", valr=[cdgy, cdgz], valk=[NomResultat, NomMaillageNew])
                # Vérification que la section n'est pas tournée
                alpha = ligne["ALPHA"]
                if abs(alpha) > 0.001:
                    if not ImprTable:
                        IMPR_TABLE(TABLE=nomres)
                    ImprTable = True
                    NomResultat = "TabCara"
                    dict_args = dict(valr=[alpha, -alpha], valk=[NomResultat, NomMaillageNew])
                    UTMESS("A", "POUTRE0_13", **dict_args)
    #
    # On retourne une table contenant toutes les caractéristiques calculées
    else:
        if GROUP_MA_BORD and not GROUP_MA:
            nomres = CALC_TABLE(
                TABLE=nomres,
                reuse=nomres,
                ACTION=(
                    _F(
                        OPERATION="EXTR",
                        NOM_PARA=(
                            "LIEU",
                            "ENTITE",
                            "A_M",
                            "CDG_Y_M",
                            "CDG_Z_M",
                            "IY_G_M",
                            "IZ_G_M",
                            "IYZ_G_M",
                            "PCT_M_Y",
                            "PCT_M_Z",
                            "Y_MAX",
                            "Z_MAX",
                            "Y_MIN",
                            "Z_MIN",
                            "R_MAX",
                            "A",
                            "CDG_Y",
                            "CDG_Z",
                            "IY_G",
                            "IZ_G",
                            "IYZ_G",
                            "IY",
                            "IZ",
                            "ALPHA",
                            "Y_P",
                            "Z_P",
                            "IY_P",
                            "IZ_P",
                            "IYZ_P",
                            "JX",
                            "AY",
                            "AZ",
                            "EY",
                            "EZ",
                            "PCTY",
                            "PCTZ",
                            "JG",
                            "KY",
                            "KZ",
                            "IYR2_G",
                            "IZR2_G",
                            "IYR2",
                            "IZR2",
                            "IYR2_P",
                            "IZR2_P",
                            "RY",
                            "RZ",
                            "RT",
                        ),
                    ),
                ),
            )
        elif GROUP_MA_BORD and GROUP_MA:
            nomres = CALC_TABLE(
                TABLE=nomres,
                reuse=nomres,
                ACTION=(
                    _F(
                        OPERATION="EXTR",
                        NOM_PARA=(
                            "LIEU",
                            "ENTITE",
                            "A_M",
                            "CDG_Y_M",
                            "CDG_Z_M",
                            "IY_G_M",
                            "IZ_G_M",
                            "IYZ_G_M",
                            "Y_MAX",
                            "Z_MAX",
                            "Y_MIN",
                            "Z_MIN",
                            "R_MAX",
                            "A",
                            "CDG_Y",
                            "CDG_Z",
                            "IY_G",
                            "IZ_G",
                            "IYZ_G",
                            "IY",
                            "IZ",
                            "ALPHA",
                            "Y_P",
                            "Z_P",
                            "IY_P",
                            "IZ_P",
                            "IYZ_P",
                            "JX",
                            "AY",
                            "AZ",
                            "EY",
                            "EZ",
                            "PCTY",
                            "PCTZ",
                            "KY",
                            "KZ",
                            "IYR2_G",
                            "IZR2_G",
                            "IYR2",
                            "IZR2",
                            "IYR2_P",
                            "IZR2_P",
                            "RY",
                            "RZ",
                            "RT",
                        ),
                    ),
                ),
            )
        else:
            nomres = CALC_TABLE(
                TABLE=nomres,
                reuse=nomres,
                ACTION=(
                    _F(
                        OPERATION="EXTR",
                        NOM_PARA=(
                            "LIEU",
                            "ENTITE",
                            "A_M",
                            "CDG_Y_M",
                            "CDG_Z_M",
                            "IY_G_M",
                            "IZ_G_M",
                            "IYZ_G_M",
                            "Y_MAX",
                            "Z_MAX",
                            "Y_MIN",
                            "Z_MIN",
                            "R_MAX",
                            "A",
                            "CDG_Y",
                            "CDG_Z",
                            "IY_G",
                            "IZ_G",
                            "IYZ_G",
                            "IY",
                            "IZ",
                            "ALPHA",
                            "Y_P",
                            "Z_P",
                            "IY_P",
                            "IZ_P",
                            "IYZ_P",
                            "IYR2_G",
                            "IZR2_G",
                            "IYR2",
                            "IZR2",
                            "IYR2_P",
                            "IZR2_P",
                            "RY",
                            "RZ",
                        ),
                    ),
                ),
            )
    #
    if not ImprTable:
        IMPR_TABLE(TABLE=nomres)
    #
    RetablirAlarme("CHARGES2_87")
    RetablirAlarme("CALCULEL_40")
    return nomres
