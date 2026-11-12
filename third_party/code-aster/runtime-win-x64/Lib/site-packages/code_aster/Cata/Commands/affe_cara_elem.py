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


from ..Commons import *
from ..Language.DataStructure import *
from ..Language.Syntax import *
from ..Language.SyntaxUtils import deprecate, force_list, force_tuple

import numpy as NP


def affe_cara_elem_prod(
    VERIF,
    POUTRE,
    BARRE,
    COQUE,
    CABLE,
    DISCRET,
    DISCRET_2D,
    GRILLE,
    MASS_REP,
    ORIENTATION,
    RIGI_PARASOL,
    **args,
):
    """Fonction sdprod de AFFE_CARA_ELEM"""
    # phase de typage seul
    if args.get("__only_type__"):
        return cara_elem

    if args.get("__all__"):
        return cara_elem

    # fonctions locales pour le sdprod de AFFE_CARA_ELEM
    def valeurCara(cara, Lcara, Lvale, valdefaut=None):
        """Retourne la valeur de la caractéristiques 'cara' dans 'Lcara'."""
        if cara in Lcara:
            return Lvale[Lcara.index(cara)]
        else:
            if valdefaut is not None:
                return valdefaut
            else:
                raise CataError("Erreur de syntaxe dans la commande")

    def check(cond, message, mcf, occ, prop=None):
        """Vérifie que la condition 'cond' est ok, sinon lève une exception"""
        if not cond:
            fmt = tr("Mot-clé {mcf!r}, occurrence {occ:d}, {text!s}")
            text = str(message).format(**locals())
            msg = str(fmt).format(**locals())
            raise CataError(msg)

    # Si Lst1[ii] in Lst2 ==> plouf
    def AbsentListe(Lst1, Lst2):
        for ii in Lst1:
            if ii in Lst2:
                return False
        return True

    # Si Lst1[ii] not in Lst2 ==> plouf
    def AllInListe(Lst1, Lst2):
        for ii in Lst1:
            if not ii in Lst2:
                return False
        return True

    # Tous ou aucun des Lst1 in Lst2
    def EnsembleInListe(Lst1, Lst2):
        indx = 0
        for ii in Lst1:
            if ii in Lst2:
                indx += 1
        if indx == 0:
            return True
        if indx == len(Lst1):
            return True
        return False

    # Fait-on la vérification des MAILLES
    #   Par défaut OUI
    VerifMaille = True
    if VERIF is not None:
        VerifMaille = not "NON" in VERIF
    #
    # les messages doivent être courts pour être visibles dans eficas
    sizeErr = tr("Les cardinaux de CARA et VALE sont différents.")
    defErr = tr("Mauvaise définition de {prop!r}.")
    # - - - - - - - - - - - - - - -
    if (POUTRE is not None) and VerifMaille:
        for i in range(len(POUTRE)):
            i1 = i + 1
            mclf = POUTRE[i]
            if mclf.get("SECTION") == "CERCLE":
                cara = force_tuple(mclf["CARA"])
                vale = force_tuple(mclf["VALE"])
                check(len(cara) == len(vale), sizeErr, "POUTRE", i1)
                if mclf.get("VARI_SECT") == "CONSTANT":
                    #
                    check(AllInListe(["R"], cara), defErr, "POUTRE", i1, cara)
                    #
                    rayon = valeurCara("R", cara, vale)
                    ep = valeurCara("EP", cara, vale, rayon)
                    check(rayon > 0.0, defErr, "POUTRE", i1, "R")
                    check(0 < ep <= rayon, defErr, "POUTRE", i1, ("R", "EP"))
                elif mclf.get("VARI_SECT") == "HOMOTHETIQUE":
                    #
                    check(AllInListe(["R_DEBUT", "R_FIN"], cara), defErr, "POUTRE", i1, cara)
                    check(EnsembleInListe(["EP_DEBUT", "EP_FIN"], cara), defErr, "POUTRE", i1, cara)
                    #
                    r_debut = valeurCara("R_DEBUT", cara, vale)
                    r_fin = valeurCara("R_FIN", cara, vale)
                    ep_debut = valeurCara("EP_DEBUT", cara, vale, r_debut)
                    ep_fin = valeurCara("EP_FIN", cara, vale, r_fin)
                    check(r_debut > 0.0, defErr, "POUTRE", i1, "R_DEBUT")
                    check(r_fin > 0.0, defErr, "POUTRE", i1, "R_FIN")
                    check(
                        (0.0 < ep_debut <= r_debut), defErr, "POUTRE", i1, ("R_DEBUT", "EP_DEBUT")
                    )
                    check((0.0 < ep_fin <= r_fin), defErr, "POUTRE", i1, ("R_FIN", "EP_FIN"))
            elif mclf.get("SECTION") == "RECTANGLE":
                cara = force_tuple(mclf["CARA"])
                vale = force_tuple(mclf["VALE"])
                check(len(cara) == len(vale), sizeErr, "POUTRE", i1)
                if mclf.get("VARI_SECT") == "CONSTANT":
                    if "H" in cara:
                        #
                        check(
                            AbsentListe(["HY", "HZ", "EPY", "EPZ"], cara),
                            defErr,
                            "POUTRE",
                            i1,
                            cara,
                        )
                        #
                        h = valeurCara("H", cara, vale)
                        ep = valeurCara("EP", cara, vale, h * 0.5)
                        check(h > 0.0, defErr, "POUTRE", i1, "H")
                        check((0.0 < ep <= h * 0.5), defErr, "POUTRE", i1, ("H", "EP"))
                    else:
                        #
                        check(AbsentListe(["H", "EP"], cara), defErr, "POUTRE", i1, cara)
                        check(AllInListe(["HY", "HZ"], cara), defErr, "POUTRE", i1, cara)
                        check(EnsembleInListe(["EPY", "EPZ"], cara), defErr, "POUTRE", i1, cara)
                        #
                        hy = valeurCara("HY", cara, vale)
                        epy = valeurCara("EPY", cara, vale, hy * 0.5)
                        hz = valeurCara("HZ", cara, vale)
                        epz = valeurCara("EPZ", cara, vale, hz * 0.5)
                        check(hy > 0.0, defErr, "POUTRE", i1, "HY")
                        check(hz > 0.0, defErr, "POUTRE", i1, "HZ")
                        check((0 < epy <= hy * 0.5), defErr, "POUTRE", i1, ("HY", "EPY"))
                        check((0 < epz <= hz * 0.5), defErr, "POUTRE", i1, ("HZ", "EPZ"))
                elif mclf.get("VARI_SECT") == "HOMOTHETIQUE":
                    if "H1" in cara:
                        #
                        check(AllInListe(["H1", "H2"], cara), defErr, "POUTRE", i1, cara)
                        check(EnsembleInListe(["EP1", "EP2"], cara), defErr, "POUTRE", i1, cara)
                        check(
                            AbsentListe(
                                ["HY1", "HY2", "HZ1", "HZ2", "EPY1", "EPY2", "EPZ1", "EPZ2"], cara
                            ),
                            defErr,
                            "POUTRE",
                            i1,
                            cara,
                        )
                        #
                        h1 = valeurCara("H1", cara, vale)
                        ep1 = valeurCara("EP1", cara, vale, h1 * 0.5)
                        h2 = valeurCara("H2", cara, vale)
                        ep2 = valeurCara("EP2", cara, vale, h2 * 0.5)
                        check(h1 > 0.0, defErr, "POUTRE", i1, "H1")
                        check(h2 > 0.0, defErr, "POUTRE", i1, "H2")
                        check((0 < ep1 <= h1 * 0.5), defErr, "POUTRE", i1, ("H1", "EP1"))
                        check((0 < ep2 <= h2 * 0.5), defErr, "POUTRE", i1, ("H2", "EP2"))
                    else:
                        #
                        check(
                            AllInListe(["HY1", "HY2", "HZ1", "HZ2"], cara),
                            defErr,
                            "POUTRE",
                            i1,
                            cara,
                        )
                        check(
                            EnsembleInListe(["EPY1", "EPY2", "EPZ1", "EPZ2"], cara),
                            defErr,
                            "POUTRE",
                            i1,
                            cara,
                        )
                        check(
                            AbsentListe(["H1", "H2", "EP1", "EP2"], cara),
                            defErr,
                            "POUTRE",
                            i1,
                            cara,
                        )
                        #
                        hy1 = valeurCara("HY1", cara, vale)
                        epy1 = valeurCara("EPY1", cara, vale, hy1 * 0.5)
                        hy2 = valeurCara("HY2", cara, vale)
                        epy2 = valeurCara("EPY2", cara, vale, hy2 * 0.5)
                        hz1 = valeurCara("HZ1", cara, vale)
                        epz1 = valeurCara("EPZ1", cara, vale, hz1 * 0.5)
                        hz2 = valeurCara("HZ2", cara, vale)
                        epz2 = valeurCara("EPZ2", cara, vale, hz2 * 0.5)
                        check(hy1 > 0.0, defErr, "POUTRE", i1, "HY1")
                        check(hy2 > 0.0, defErr, "POUTRE", i1, "HY2")
                        check(hz1 > 0.0, defErr, "POUTRE", i1, "HZ1")
                        check(hz2 > 0.0, defErr, "POUTRE", i1, "HZ2")
                        check((0 < epy1 <= hy1 * 0.5), defErr, "POUTRE", i1, "EPY1")
                        check((0 < epy2 <= hy2 * 0.5), defErr, "POUTRE", i1, "EPY2")
                        check((0 < epz1 <= hz1 * 0.5), defErr, "POUTRE", i1, "EPZ1")
                        check((0 < epz2 <= hz2 * 0.5), defErr, "POUTRE", i1, "EPZ2")
                elif mclf.get("VARI_SECT") == "AFFINE":
                    #
                    check(AllInListe(["HY", "HZ1", "HZ2"], cara), defErr, "POUTRE", i1, cara)
                    check(
                        EnsembleInListe(["EPY", "EPZ1", "EPZ2"], cara), defErr, "POUTRE", i1, cara
                    )
                    #
                    hy = valeurCara("HY", cara, vale)
                    hz1 = valeurCara("HZ1", cara, vale)
                    hz2 = valeurCara("HZ2", cara, vale)
                    epy = valeurCara("EPY", cara, vale, hy * 0.5)
                    epz1 = valeurCara("EPZ1", cara, vale, hz1 * 0.5)
                    epz2 = valeurCara("EPZ2", cara, vale, hz2 * 0.5)
                    check(hy > 0.0, defErr, "POUTRE", i1, "HY")
                    check(hz1 > 0.0, defErr, "POUTRE", i1, "HZ1")
                    check(hz2 > 0.0, defErr, "POUTRE", i1, "HZ2")
                    check((0 < epy <= hy * 0.5), defErr, "POUTRE", i1, ("HY", "EPY"))
                    check((0 < epz1 <= hz1 * 0.5), defErr, "POUTRE", i1, ("HZ1", "EPZ1"))
                    check((0 < epz2 <= hz2 * 0.5), defErr, "POUTRE", i1, ("HZ2", "EPZ2"))
            elif mclf.get("SECTION") == "GENERALE":
                if mclf.get("VARI_SECT") == "CONSTANT":
                    if mclf.get("CARA") is not None:
                        cara = force_tuple(mclf["CARA"])
                        vale = force_tuple(mclf["VALE"])
                        check(len(cara) == len(vale), sizeErr, "POUTRE", i1)
                        #
                        check(AllInListe(["A", "IY", "IZ", "JX"], cara), defErr, "POUTRE", i1, cara)
                        #
                        for icara in cara:
                            # Ceux qui doivent être > 0
                            if icara in ["A", "IY", "IZ", "JX", "AY", "AZ", "RT"]:
                                ivale = valeurCara(icara, cara, vale)
                                check(ivale > 0.0, defErr, "POUTRE", i1, icara)
                            # Ceux qui doivent être >= 0
                            if icara in ["JG"]:
                                ivale = valeurCara(icara, cara, vale)
                                check(ivale >= 0.0, defErr, "POUTRE", i1, icara)
                        #
                elif mclf.get("VARI_SECT") == "HOMOTHETIQUE":
                    cara = force_tuple(mclf["CARA"])
                    vale = force_tuple(mclf["VALE"])
                    check(len(cara) == len(vale), sizeErr, "POUTRE", i1)
                    #
                    check(
                        AllInListe(["A1", "A2", "IY1", "IY2", "IZ1", "IZ2", "JX1", "JX2"], cara),
                        defErr,
                        "POUTRE",
                        i1,
                        cara,
                    )
                    #
                    for icara in cara:
                        # Ceux qui doivent être > 0
                        if icara in [
                            "A1",
                            "IY1",
                            "IZ1",
                            "JX1",
                            "AY1",
                            "AZ1",
                            "RT1",
                            "A2",
                            "IY2",
                            "IZ2",
                            "JX2",
                            "AY2",
                            "AZ2",
                            "RT2",
                        ]:
                            ivale = valeurCara(icara, cara, vale)
                            check(ivale > 0.0, defErr, "POUTRE", i1, icara)
                        # Ceux qui doivent être >= 0
                        if icara in ["JG1", "JG2"]:
                            ivale = valeurCara(icara, cara, vale)
                            check(ivale >= 0.0, defErr, "POUTRE", i1, icara)
                    #
            # Caractéristiques des coudes
            elif mclf.get("SECTION") == "COUDE":
                for caraCoude in [
                    "INDI_SIGM",
                    "INDI_SIGM_XY",
                    "INDI_SIGM_XZ",
                    "COEF_FLEX",
                    "COEF_FLEX_XY",
                    "COEF_FLEX_XZ",
                ]:
                    if caraCoude in mclf:
                        vale = mclf[caraCoude]
                        check(vale > 0.0, defErr, "POUTRE", i1, caraCoude)
    # - - - - - - - - - - - - - - -
    if BARRE is not None:
        for i in range(len(BARRE)):
            i1 = i + 1
            mclf = BARRE[i]
            if mclf.get("SECTION") == "CERCLE":
                cara = force_tuple(mclf["CARA"])
                vale = force_tuple(mclf["VALE"])
                check(len(cara) == len(vale), sizeErr, "BARRE", i1)
                #
                check(AllInListe(["R"], cara), defErr, "BARRE", i1, cara)
                #
                rayon = valeurCara("R", cara, vale)
                ep = valeurCara("EP", cara, vale, rayon)
                check(rayon > 0.0, defErr, "BARRE", i1, "R")
                check((0.0 < ep <= rayon), defErr, "BARRE", i1, ("R", "EP"))
            elif mclf.get("SECTION") == "RECTANGLE":
                # "H", "EP", "HZ", "HY", "EPY", "EPZ"
                cara = force_tuple(mclf["CARA"])
                vale = force_tuple(mclf["VALE"])
                check(len(cara) == len(vale), sizeErr, "BARRE", i1)
                if "H" in cara:
                    # Règles
                    check(AbsentListe(["HY", "HZ", "EPY", "EPZ"], cara), defErr, "BARRE", i1, cara)
                    #
                    h = valeurCara("H", cara, vale)
                    ep = valeurCara("EP", cara, vale, h * 0.5)
                    check(h > 0.0, defErr, "BARRE", i1, "H")
                    check((0 < ep <= h * 0.5), defErr, "BARRE", i1, ("H", "EP"))
                else:
                    # Règles
                    check(AbsentListe(["H", "EP"], cara), defErr, "BARRE", i1, cara)
                    check(AllInListe(["HY", "HZ"], cara), defErr, "BARRE", i1, cara)
                    check(EnsembleInListe(["EPY", "EPZ"], cara), defErr, "BARRE", i1, cara)
                    #
                    hy = valeurCara("HY", cara, vale)
                    epy = valeurCara("EPY", cara, vale, hy * 0.5)
                    hz = valeurCara("HZ", cara, vale)
                    epz = valeurCara("EPZ", cara, vale, hz * 0.5)
                    check(hy > 0.0, defErr, "BARRE", i1, "HY")
                    check(hz > 0.0, defErr, "BARRE", i1, "HZ")
                    check((0 < epy <= hy * 0.5), defErr, "BARRE", i1, "EPY")
                    check((0 < epz <= hz * 0.5), defErr, "BARRE", i1, "EPZ")
            elif mclf.get("SECTION") == "GENERALE":
                if mclf.get("CARA") is not None:
                    cara = force_tuple(mclf["CARA"])
                    vale = force_tuple(mclf["VALE"])
                    check(len(cara) == len(vale), sizeErr, "BARRE", i1)
                    vale = valeurCara("A", cara, vale)
                    check(vale > 0.0, defErr, "BARRE", i1, "A")
                elif mclf.get("AIRE") is not None:
                    aire = mclf.get("AIRE")
                    check(aire > 0.0, defErr, "BARRE", i1, "AIRE")
    # - - - - - - - - - - - - - - -
    if COQUE is not None:
        for i in range(len(COQUE)):
            i1 = i + 1
            mclf = COQUE[i]
            if mclf["EPAIS"] is not None:
                vale = mclf["EPAIS"]
                check(vale > 0.0, defErr, "COQUE", i1, "EPAIS")
            if mclf["A_CIS"] is not None:
                vale = mclf["A_CIS"]
                check(vale > 0.0, defErr, "COQUE", i1, "A_CIS")
            # if mclf['COEF_RIGI_DRZ'] is not None:
            # vale =  mclf['COEF_RIGI_DRZ']
            # check( vale > 0.0, defErr, 'COQUE', i1, 'COEF_RIGI_DRZ')
            if mclf["COQUE_NCOU"] is not None:
                vale = mclf["COQUE_NCOU"]
                check(vale > 0, defErr, "COQUE", i1, "COQUE_NCOU")
    # - - - - - - - - - - - - - - -
    if CABLE is not None:
        Listemclf1 = ["AIRE", "RAYON", "DIAMETRE"]
        Listemclf2 = ["N_INIT"]
        for i in range(len(CABLE)):
            i1 = i + 1
            mclf = CABLE[i]
            # Tous > 0
            for icl in Listemclf1:
                if icl in mclf:
                    check(mclf[icl] > 0.0, defErr, "CABLE", i1, icl)
            # Tous >= 0
            for icl in Listemclf2:
                if icl in mclf:
                    check(mclf[icl] >= 0.0, defErr, "CABLE", i1, icl)
    # - - - - - - - - - - - - - - -
    if DISCRET is not None:
        pass
    # - - - - - - - - - - - - - - -
    if DISCRET_2D is not None:
        pass
    # - - - - - - - - - - - - - - -
    if GRILLE is not None:
        for i in range(len(GRILLE)):
            i1 = i + 1
            mclf = GRILLE[i]
            if "SECTION" in mclf:
                vale = mclf["SECTION"]
                check(vale >= 0.0, defErr, "GRILLE", i1, "SECTION")
    # - - - - - - - - - - - - - - -
    if MASS_REP is not None:
        for i in range(len(MASS_REP)):
            i1 = i + 1
            mclf = MASS_REP[i]
            if mclf["VALE"] is not None:
                vale = mclf["VALE"]
                check(vale >= 0.0, defErr, "MASS_REP", i1, "VALE")
    # - - - - - - - - - - - - - - -
    if (ORIENTATION is not None) and VerifMaille:
        for i in range(len(ORIENTATION)):
            i1 = i + 1
            mclf = ORIENTATION[i]
            cara = mclf["CARA"]
            if cara in ["VECT_MAIL_Y", "VECT_MAIL_Z", "VECT_Y", "VECT_Z"]:
                vale = NP.array(mclf["VALE"])
                vv = NP.sum(vale * vale)
                check(vv > 0.0, defErr, "ORIENTATION", i1, "VALE")
    ## - - - - - - - - - - - - - - -
    if RIGI_PARASOL is not None:
        sizeErr_RP1 = tr("Les cardinaux de FONC_GROUP et GROUP_MA sont différents.")
        sizeErr_RP2 = tr("Les cardinaux de COEF_GROUP et GROUP_MA sont différents.")
        for i in range(len(RIGI_PARASOL)):
            i1 = i + 1
            mclf = RIGI_PARASOL[i]
            grp_ma = force_tuple(mclf["GROUP_MA"])
            if mclf.get("FONC_GROUP") is not None:
                grp_fc = force_tuple(mclf["FONC_GROUP"])
                if len(grp_fc) > 0:
                    check(len(grp_ma) == len(grp_fc), sizeErr_RP1, "RIGI_PARASOL", i1)
            if mclf.get("COEF_GROUP") is not None:
                grp_fc = force_tuple(mclf["COEF_GROUP"])
                if len(grp_fc) > 0:
                    check(len(grp_ma) == len(grp_fc), sizeErr_RP2, "RIGI_PARASOL", i1)
    #
    # Pour l'instant Tout est ok
    return cara_elem


def compat_syntax(keywords):
    """Adapt keywords *BEFORE* syntax checking.

    Arguments:
        keywords (dict): Keywords arguments of user's keywords, changed in place.
    """
    #
    lesClefs = keywords.keys()
    # ---------------------------------------------------------------- CABLE
    if "CABLE" in lesClefs:
        keywords["CABLE"] = force_list(keywords.get("CABLE", []))
        for ioc in range(len(keywords["CABLE"])):
            LesCables = keywords["CABLE"][ioc].keys()
            if "SECTION" in LesCables:
                LaVale = keywords["CABLE"][ioc].pop("SECTION")
                keywords["CABLE"][ioc]["AIRE"] = LaVale
                deprecate("SECTION", case=3, help="Use 'AIRE' instead")
                #


AFFE_CARA_ELEM = OPER(
    nom="AFFE_CARA_ELEM",
    sd_prod=affe_cara_elem_prod,
    compat_syntax=compat_syntax,
    op=19,
    fr=tr("Affectation de caractéristiques à des éléments de structure"),
    reentrant="n",
    regles=(
        AU_MOINS_UN(
            "BARRE",
            "CABLE",
            "COQUE",
            "DISCRET",
            "DISCRET_2D",
            "GRILLE",
            "MASSIF",
            "MASS_REP",
            "MEMBRANE",
            "MULTIFIBRE",
            "POUTRE",
            "RIGI_PARASOL",
        ),
        PRESENT_PRESENT("MULTIFIBRE", "GEOM_FIBRE"),
        EXCLUS("DISCRET", "DISCRET_2D"),
    ),
    MODELE=SIMP(statut="o", typ=modele_sdaster),
    INFO=SIMP(statut="f", typ="I", defaut=1, into=(1, 2)),
    VERIF=SIMP(statut="f", typ="TXM", max=1, into=("OUI", "NON")),
    #
    # ==============================================================================
    POUTRE=FACT(
        statut="f",
        max="**",
        SECTION=SIMP(statut="o", typ="TXM", into=("GENERALE", "RECTANGLE", "CERCLE", "COUDE")),
        b_generale=BLOC(
            condition=""" equal_to("SECTION", 'GENERALE')""",
            GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
            VARI_SECT=SIMP(
                statut="f", typ="TXM", into=("CONSTANT", "HOMOTHETIQUE"), defaut="CONSTANT"
            ),
            b_constant=BLOC(
                condition="""equal_to("VARI_SECT", 'CONSTANT')""",
                regles=(
                    PRESENT_ABSENT("TABLE_CARA", "CARA"),
                    PRESENT_PRESENT("TABLE_CARA", "NOM_SEC"),
                    PRESENT_PRESENT("CARA", "VALE"),
                ),
                TABLE_CARA=SIMP(statut="f", typ=table_sdaster),
                NOM_SEC=SIMP(statut="f", typ="TXM", validators=LongStr(1, 8)),
                # Pour que tout reste aligné
                CARA=SIMP(
                    statut="f",
                    typ="TXM",
                    min=4,
                    max=15,
                    fr=tr("A,IY,IZ,JX sont des paramètres obligatoires"),
                    validators=NoRepeat(),
                    into=(
                        "A",
                        "IY",
                        "IZ",
                        "AY",
                        "AZ",
                        "EY",
                        "EZ",
                        "JX",
                        "RY",
                        "RZ",
                        "RT",
                        "JG",
                        "IYR2",
                        "IZR2",
                        "AI",
                    ),
                ),
                VALE=SIMP(statut="f", typ="R", min=4, max=15),
            ),
            b_homothetique=BLOC(
                condition="""equal_to("VARI_SECT", 'HOMOTHETIQUE')""",
                # Pour que tout reste aligné : 1 section début
                #                              2 section fin
                CARA=SIMP(
                    statut="o",
                    typ="TXM",
                    min=8,
                    max=28,
                    fr=tr("A1,A2,IY1,IY2,IZ1,IZ2,JX1,JX2 sont des paramètres obligatoires"),
                    validators=NoRepeat(),
                    into=(
                        "A1",
                        "IY1",
                        "IZ1",
                        "AY1",
                        "AZ1",
                        "EY1",
                        "EZ1",
                        "JX1",
                        "RY1",
                        "RZ1",
                        "A2",
                        "IY2",
                        "IZ2",
                        "AY2",
                        "AZ2",
                        "EY2",
                        "EZ2",
                        "JX2",
                        "RY2",
                        "RZ2",
                        "RT1",
                        "JG1",
                        "IYR21",
                        "IZR21",
                        "RT2",
                        "JG2",
                        "IYR22",
                        "IZR22",
                    ),
                ),
                VALE=SIMP(statut="o", typ="R", min=8, max=30),
            ),
        ),
        b_rectangle=BLOC(
            condition="""equal_to("SECTION", 'RECTANGLE')""",
            GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
            VARI_SECT=SIMP(
                statut="f",
                typ="TXM",
                into=("CONSTANT", "HOMOTHETIQUE", "AFFINE"),
                defaut="CONSTANT",
            ),
            b_constant=BLOC(
                condition="""equal_to("VARI_SECT", 'CONSTANT')""",
                CARA=SIMP(
                    statut="o",
                    typ="TXM",
                    min=1,
                    max=4,
                    validators=NoRepeat(),
                    into=("H", "EP", "HY", "HZ", "EPY", "EPZ"),
                ),
                VALE=SIMP(statut="o", typ="R", min=1, max=4),
            ),
            b_homothetique=BLOC(
                condition="""equal_to("VARI_SECT", 'HOMOTHETIQUE')""",
                # Pour que tout reste aligné : 1 section début
                #                              2 section fin
                CARA=SIMP(
                    statut="o",
                    typ="TXM",
                    min=2,
                    max=8,
                    validators=NoRepeat(),
                    into=(
                        "H1",
                        "HZ1",
                        "HY1",
                        "EP1",
                        "EPY1",
                        "EPZ1",
                        "H2",
                        "HZ2",
                        "HY2",
                        "EP2",
                        "EPY2",
                        "EPZ2",
                    ),
                ),
                VALE=SIMP(statut="o", typ="R", min=2, max=8),
            ),
            b_affine=BLOC(
                condition="""equal_to("VARI_SECT", 'AFFINE')""",
                CARA=SIMP(
                    statut="o",
                    typ="TXM",
                    min=3,
                    max=6,
                    validators=NoRepeat(),
                    into=("HY", "EPY", "HZ1", "EPZ1", "HZ2", "EPZ2"),
                ),
                VALE=SIMP(statut="o", typ="R", min=3, max=6),
            ),
        ),
        b_cercle=BLOC(
            condition=""" equal_to("SECTION", 'CERCLE')""",
            VARI_SECT=SIMP(
                statut="f", typ="TXM", into=("CONSTANT", "HOMOTHETIQUE"), defaut="CONSTANT"
            ),
            b_constant=BLOC(
                condition="""equal_to("VARI_SECT", 'CONSTANT')""",
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                CARA=SIMP(
                    statut="o",
                    typ="TXM",
                    min=1,
                    max=2,
                    validators=NoRepeat(),
                    fr=tr("R est obligatoire"),
                    into=("R", "EP"),
                ),
                VALE=SIMP(statut="o", typ="R", min=1, max=2),
            ),
            b_homothetique=BLOC(
                condition="""equal_to("VARI_SECT", 'HOMOTHETIQUE')""",
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                CARA=SIMP(
                    statut="o",
                    typ="TXM",
                    min=2,
                    max=4,
                    validators=NoRepeat(),
                    fr=tr("R_DEBUT, R_FIN sont obligatoires"),
                    into=("R_DEBUT", "R_FIN", "EP_DEBUT", "EP_FIN"),
                ),
                VALE=SIMP(statut="o", typ="R", min=2, max=4),
            ),
            MODI_METRIQUE=SIMP(statut="f", typ="TXM", defaut="NON", into=("OUI", "NON")),
            FCX=SIMP(statut="f", typ=(fonction_sdaster, nappe_sdaster, formule)),
            TUYAU_NSEC=SIMP(statut="f", typ="I", val_max=32, val_min=8, defaut=16),
            TUYAU_NCOU=SIMP(statut="f", typ="I", val_max=10, val_min=1, defaut=3),
        ),
        b_coude=BLOC(
            condition=""" equal_to("SECTION", 'COUDE')""",
            regles=(
                EXCLUS("COEF_FLEX", "COEF_FLEX_XY"),
                EXCLUS("COEF_FLEX", "COEF_FLEX_XZ"),
                EXCLUS("INDI_SIGM", "INDI_SIGM_XY"),
                EXCLUS("INDI_SIGM", "INDI_SIGM_XZ"),
                PRESENT_PRESENT("COEF_FLEX_XY", "COEF_FLEX_XZ"),
                PRESENT_PRESENT("INDI_SIGM_XY", "INDI_SIGM_XZ"),
            ),
            GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
            COEF_FLEX=SIMP(statut="f", typ="R", val_min=0.0),
            INDI_SIGM=SIMP(statut="f", typ="R", val_min=0.0),
            COEF_FLEX_XY=SIMP(statut="f", typ="R", val_min=0.0),
            INDI_SIGM_XY=SIMP(statut="f", typ="R", val_min=0.0),
            COEF_FLEX_XZ=SIMP(statut="f", typ="R", val_min=0.0),
            INDI_SIGM_XZ=SIMP(statut="f", typ="R", val_min=0.0),
        ),
    ),
    #
    # ==============================================================================
    BARRE=FACT(
        statut="f",
        max="**",
        GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
        SECTION=SIMP(statut="o", typ="TXM", into=("GENERALE", "RECTANGLE", "CERCLE")),
        b_generale=BLOC(
            condition="""equal_to("SECTION", 'GENERALE')""",
            regles=(
                PRESENT_PRESENT("TABLE_CARA", "NOM_SEC"),
                PRESENT_PRESENT("CARA", "VALE"),
                PRESENT_ABSENT("AIRE", "TABLE_CARA", "CARA"),
                UN_PARMI("AIRE", "TABLE_CARA", "CARA"),
            ),
            #
            TABLE_CARA=SIMP(statut="f", typ=table_sdaster),
            NOM_SEC=SIMP(statut="f", typ="TXM", validators=LongStr(1, 8)),
            #
            CARA=SIMP(statut="f", typ="TXM", into=("A",)),
            VALE=SIMP(statut="f", typ="R", min=1, max=1),
            #
            AIRE=SIMP(statut="f", typ="R"),
        ),
        b_rectangle=BLOC(
            condition="""equal_to("SECTION", 'RECTANGLE')""",
            CARA=SIMP(
                statut="o",
                typ="TXM",
                min=1,
                max=4,
                validators=NoRepeat(),
                into=("H", "EP", "HZ", "HY", "EPY", "EPZ"),
            ),
            VALE=SIMP(statut="o", typ="R", min=1, max=4),
        ),
        b_cercle=BLOC(
            condition="""equal_to("SECTION", 'CERCLE')""",
            #
            CARA=SIMP(statut="o", typ="TXM", validators=NoRepeat(), min=1, max=2, into=("R", "EP")),
            VALE=SIMP(statut="o", typ="R", min=1, max=2),
            #
        ),
        FCX=SIMP(statut="f", typ=(fonction_sdaster, nappe_sdaster, formule)),
    ),
    #
    # ==============================================================================
    COQUE=FACT(
        statut="f",
        max="**",
        regles=(
            EXCLUS("ANGL_REP", "VECTEUR"),
            PRESENT_PRESENT("EXCENTREMENT", "INER_ROTA"),
            PRESENT_PRESENT("EXCENTREMENT_FO", "INER_ROTA"),
            UN_PARMI("EPAIS", "EPAIS_FO"),
            EXCLUS("EXCENTREMENT", "EXCENTREMENT_FO"),
        ),
        GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
        EPAIS=SIMP(statut="f", typ="R"),
        EPAIS_FO=SIMP(statut="f", typ=(fonction_sdaster, nappe_sdaster, formule)),
        ANGL_REP=SIMP(statut="f", typ="R", min=2, max=2),
        VECTEUR=SIMP(statut="f", typ="R", min=3, max=3),
        A_CIS=SIMP(statut="f", typ="R", defaut=0.8333333e0),
        COEF_RIGI_DRZ=SIMP(statut="f", typ="R", defaut=1.0e-5),
        COQUE_NCOU=SIMP(statut="f", typ="I", defaut=1),
        EXCENTREMENT=SIMP(statut="f", typ="R"),
        EXCENTREMENT_FO=SIMP(statut="f", typ=(fonction_sdaster, nappe_sdaster, formule)),
        INER_ROTA=SIMP(statut="f", typ="TXM", into=("OUI",)),
        MODI_METRIQUE=SIMP(statut="f", typ="TXM", defaut="NON", into=("OUI", "NON")),
    ),
    #
    # ==============================================================================
    CABLE=FACT(
        statut="f",
        max="**",
        regles=(UN_PARMI("AIRE", "RAYON", "DIAMETRE"),),
        GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
        #
        CARA=SIMP(statut="c", typ="TXM", min=2, max=4),
        VALE=SIMP(statut="c", typ="R", min=2, max=4),
        #
        N_INIT=SIMP(statut="o", typ="R"),
        #
        AIRE=SIMP(statut="f", typ="R"),
        RAYON=SIMP(statut="f", typ="R"),
        DIAMETRE=SIMP(statut="f", typ="R"),
        #
        FCX=SIMP(statut="f", typ=(fonction_sdaster, nappe_sdaster, formule)),
    ),
    #
    # ==============================================================================
    DISCRET=FACT(
        statut="f",
        max="**",
        REPERE=SIMP(statut="f", typ="TXM", into=("LOCAL", "GLOBAL"), defaut="GLOBAL"),
        AMOR_HYST=SIMP(statut="f", typ="R"),
        SYME=SIMP(statut="f", typ="TXM", defaut="OUI", into=("OUI", "NON")),
        b_SYME_OUI=BLOC(
            condition="""equal_to("SYME", 'OUI')""",
            fr=tr(
                "SYMETRIQUE: Affectation de matrices de rigidité, de masse ou d'amortissement à des mailles"
            ),
            # Pour que tout reste aligné
            CARA=SIMP(
                statut="f",
                typ="TXM",
                max=1,
                into=(
                    "K_T_D_N",
                    "K_T_D_L",
                    "K_TR_D_N",
                    "K_TR_D_L",
                    "K_T_N",
                    "K_T_L",
                    "K_TR_N",
                    "K_TR_L",
                    "M_T_D_N",
                    "M_T_D_L",
                    "M_TR_D_N",
                    "M_TR_D_L",
                    "M_T_N",
                    "M_T_L",
                    "M_TR_N",
                    "M_TR_L",
                    "A_T_D_N",
                    "A_T_D_L",
                    "A_TR_D_N",
                    "A_TR_D_L",
                    "A_T_N",
                    "A_T_L",
                    "A_TR_N",
                    "A_TR_L",
                ),
            ),
            #  Affection des caractéristiques de RIGIDITE/AMORTISSEMENT/MASSE
            b_AK_T_D_N=BLOC(
                condition="""((equal_to("CARA", 'K_T_D_N')or(equal_to("CARA", 'A_T_D_N'))))""",
                fr=tr("POI1: 3 valeurs (triangulaire supérieure par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=3, max=3),
            ),
            b_AK_T_D_L=BLOC(
                condition="""((equal_to("CARA", 'K_T_D_L')or(equal_to("CARA", 'A_T_D_L'))))""",
                fr=tr("SEGMENT: 3 valeurs (triangulaire supérieure par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=3, max=3),
            ),
            b_AK_TR_D_N=BLOC(
                condition="""((equal_to("CARA", 'K_TR_D_N')or(equal_to("CARA", 'A_TR_D_N'))))""",
                fr=tr("POI1: 6 valeurs (triangulaire supérieure par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=6, max=6),
            ),
            b_AK_TR_D_L=BLOC(
                condition="""((equal_to("CARA", 'K_TR_D_L')or(equal_to("CARA", 'A_TR_D_L'))))""",
                fr=tr("SEGMENT: 6 valeurs (triangulaire supérieure par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=6, max=6),
            ),
            b_MAK_T_N=BLOC(
                condition="""((equal_to("CARA", 'K_T_N')or(equal_to("CARA", 'A_T_N')or(equal_to("CARA", 'M_T_N')))))""",
                fr=tr("POI1: 6 valeurs (triangulaire supérieure par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=6, max=6),
            ),
            b_MAK_T_L=BLOC(
                condition="""((equal_to("CARA", 'K_T_L')or(equal_to("CARA", 'A_T_L')or(equal_to("CARA", 'M_T_L')))))""",
                fr=tr("SEGMENT: 21 valeurs (triangulaire supérieure par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=21, max=21),
            ),
            b_MAK_TR_N=BLOC(
                condition="""((equal_to("CARA", 'K_TR_N')or(equal_to("CARA", 'A_TR_N')or(equal_to("CARA", 'M_TR_N')))))""",
                fr=tr("POI1: 21 valeurs (triangulaire supérieure par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=21, max=21),
            ),
            b_MAK_TR_L=BLOC(
                condition="""((equal_to("CARA", 'K_TR_L')or(equal_to("CARA", 'A_TR_L')or(equal_to("CARA", 'M_TR_L')))))""",
                fr=tr("SEGMENT: 78 valeurs (triangulaire supérieure par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=78, max=78),
            ),
            #  Affection des caractéristiques de MASSE
            b_M_T_D_N=BLOC(
                condition="""(equal_to("CARA", 'M_T_D_N'))""",
                fr=tr("POI1: 1 valeur de masse"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=1, max=1),
            ),
            b_M_T_D_L=BLOC(
                condition="""(equal_to("CARA", 'M_T_D_L'))""",
                fr=tr("SEGMENT: 1 valeur de masse"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=1, max=1),
            ),
            b_M_TR_D_N=BLOC(
                condition="""(equal_to("CARA", 'M_TR_D_N'))""",
                fr=tr(
                    "POI1: 1 valeur de masse, 6 valeurs du tenseur d'inertie, 3 composantes du vecteur d'excentrement"
                ),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=10, max=10),
            ),
            b_M_TR_D_L=BLOC(
                condition="""(equal_to("CARA", 'M_TR_D_L'))""",
                fr=tr("SEGMENT: 1 valeur de masse, 3 valeurs du tenseur d'inertie"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=4, max=4),
            ),
        ),
        #     éléments à matrice non-symétrique
        #        b_MAK_T_N_NS       'K_T_N'     'A_T_N'    'M_T_N'
        #        b_MAK_T_L_NS       'K_T_L'     'A_T_L'    'M_T_L'
        #        b_MAK_TR_N_NS      'K_TR_N'    'A_TR_N'   'M_TR_N'
        #        b_MAK_TR_L_NS      'K_TR_L'    'A_TR_L'   'M_TR_L'
        b_SYME_NON=BLOC(
            condition="""equal_to("SYME", 'NON')""",
            fr=tr(
                "NON-SYMETRIQUE: Affectation de matrices de rigidité, de masse ou d'amortissement à des mailles"
            ),
            # Pour que tout reste aligné
            CARA=SIMP(
                statut="f",
                typ="TXM",
                max=1,
                into=(
                    "K_T_N",
                    "K_T_L",
                    "K_TR_N",
                    "K_TR_L",
                    "M_T_N",
                    "M_T_L",
                    "M_TR_N",
                    "M_TR_L",
                    "A_T_N",
                    "A_T_L",
                    "A_TR_N",
                    "A_TR_L",
                ),
            ),
            #  Affection des caractéristiques de RIGIDITE/AMORTISSEMENT/MASSE : NON-SYMETRIQUE
            b_MAK_T_N_NS=BLOC(
                condition="""((equal_to("CARA", 'K_T_N')or(equal_to("CARA", 'A_T_N')or(equal_to("CARA", 'M_T_N')))))""",
                fr=tr("POI1: 9 valeurs (matrice pleine par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=9, max=9),
            ),
            b_MAK_T_L_NS=BLOC(
                condition="""((equal_to("CARA", 'K_T_L')or(equal_to("CARA", 'A_T_L')or(equal_to("CARA", 'M_T_L')))))""",
                fr=tr("SEGMENT: 36 valeurs (matrice pleine par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=36, max=36),
            ),
            b_MAK_TR_N_NS=BLOC(
                condition="""((equal_to("CARA", 'K_TR_N')or(equal_to("CARA", 'A_TR_N')or(equal_to("CARA", 'M_TR_N')))))""",
                fr=tr("POI1: 36 valeurs (matrice pleine par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=36, max=36),
            ),
            b_MAK_TR_L_NS=BLOC(
                condition="""((equal_to("CARA", 'K_TR_L')or(equal_to("CARA", 'A_TR_L')or(equal_to("CARA", 'M_TR_L')))))""",
                fr=tr("SEGMENT: 144 valeurs (matrice pleine par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=144, max=144),
            ),
        ),
    ),
    #
    # ==============================================================================
    DISCRET_2D=FACT(
        statut="f",
        max="**",
        REPERE=SIMP(statut="f", typ="TXM", into=("LOCAL", "GLOBAL"), defaut="GLOBAL"),
        AMOR_HYST=SIMP(statut="f", typ="R"),
        SYME=SIMP(statut="f", typ="TXM", defaut="OUI", into=("OUI", "NON")),
        b_SYME_OUI=BLOC(
            condition="""equal_to("SYME", 'OUI')""",
            fr=tr(
                "SYMETRIQUE: Affectation de matrices de rigidité, de masse ou d'amortissement à des mailles"
            ),
            # Pour que tout reste aligné
            CARA=SIMP(
                statut="f",
                typ="TXM",
                max=1,
                into=(
                    "K_T_D_N",
                    "K_T_D_L",
                    "K_TR_D_N",
                    "K_TR_D_L",
                    "K_T_N",
                    "K_T_L",
                    "K_TR_N",
                    "K_TR_L",
                    "M_T_D_N",
                    "M_T_D_L",
                    "M_TR_D_N",
                    "M_TR_D_L",
                    "M_T_N",
                    "M_T_L",
                    "M_TR_N",
                    "M_TR_L",
                    "A_T_D_N",
                    "A_T_D_L",
                    "A_TR_D_N",
                    "A_TR_D_L",
                    "A_T_N",
                    "A_T_L",
                    "A_TR_N",
                    "A_TR_L",
                ),
            ),
            #  Affection des caractéristiques de RIGIDITE/AMORTISSEMENT/MASSE
            b_AK_T_D_N=BLOC(
                condition="""((equal_to("CARA", 'K_T_D_N')or(equal_to("CARA", 'A_T_D_N'))))""",
                fr=tr("POI1: 2 valeurs (triangulaire supérieure par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=2, max=2),
            ),
            b_AK_T_D_L=BLOC(
                condition="""((equal_to("CARA", 'K_T_D_L')or(equal_to("CARA", 'A_T_D_L'))))""",
                fr=tr("SEGMENT: 2 valeurs (triangulaire supérieure par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=2, max=2),
            ),
            b_AK_TR_D_N=BLOC(
                condition="""((equal_to("CARA", 'K_TR_D_N')or(equal_to("CARA", 'A_TR_D_N'))))""",
                fr=tr("POI1: 3 valeurs (triangulaire supérieure par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=3, max=3),
            ),
            b_AK_TR_D_L=BLOC(
                condition="""((equal_to("CARA", 'K_TR_D_L')or(equal_to("CARA", 'A_TR_D_L'))))""",
                fr=tr("SEGMENT: 3 valeurs (triangulaire supérieure par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=3, max=3),
            ),
            b_MAK_T_N=BLOC(
                condition="""((equal_to("CARA", 'K_T_N')or(equal_to("CARA", 'A_T_N')or(equal_to("CARA", 'M_T_N')))))""",
                fr=tr("POI1: 3 valeurs (triangulaire supérieure par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=3, max=3),
            ),
            b_MAK_T_L=BLOC(
                condition="""((equal_to("CARA", 'K_T_L')or(equal_to("CARA", 'A_T_L')or(equal_to("CARA", 'M_T_L')))))""",
                fr=tr("SEGMENT: 10 valeurs (triangulaire supérieure par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=10, max=10),
            ),
            b_MAK_TR_N=BLOC(
                condition="""((equal_to("CARA", 'K_TR_N')or(equal_to("CARA", 'A_TR_N')or(equal_to("CARA", 'M_TR_N')))))""",
                fr=tr("POI1: 6 valeurs (triangulaire supérieure par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=6, max=6),
            ),
            b_MAK_TR_L=BLOC(
                condition="""((equal_to("CARA", 'K_TR_L')or(equal_to("CARA", 'A_TR_L')or(equal_to("CARA", 'M_TR_L')))))""",
                fr=tr("SEGMENT: 21 valeurs (triangulaire supérieure par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=21, max=21),
            ),
            #  Affection des caractéristiques de MASSE
            b_M_T_D_N=BLOC(
                condition="""(equal_to("CARA", 'M_T_D_N'))""",
                fr=tr("POI1: 1 valeur de masse"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=1, max=1),
            ),
            b_M_T_D_L=BLOC(
                condition="""(equal_to("CARA", 'M_T_D_L'))""",
                fr=tr("SEGMENT: 1 valeur de masse"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=1, max=1),
            ),
            b_M_TR_D_N=BLOC(
                condition="""(equal_to("CARA", 'M_TR_D_N'))""",
                fr=tr(
                    "POI1: 1 valeur de masse, 1 valeur d'inertie, 2 composantes du vecteur d'excentrement"
                ),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=4, max=4),
            ),
            b_M_TR_D_L=BLOC(
                condition="""(equal_to("CARA", 'M_TR_D_L'))""",
                fr=tr("SEGMENT: 1 valeur de masse, 1 valeur d'inertie"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=2, max=2),
            ),
        ),
        #     éléments à matrice non-symétrique
        #        b_MAK_T_N_NS       'K_T_N'     'A_T_N'    'M_T_N'
        #        b_MAK_T_L_NS       'K_T_L'     'A_T_L'    'M_T_L'
        #        b_MAK_TR_N_NS      'K_TR_N'    'A_TR_N'   'M_TR_N'
        #        b_MAK_TR_L_NS      'K_TR_L'    'A_TR_L'   'M_TR_L'
        b_SYME_NON=BLOC(
            condition="""equal_to("SYME", 'NON')""",
            fr=tr(
                "NON-SYMETRIQUE: Affectation de matrices de rigidité, de masse ou d'amortissement à des mailles"
            ),
            # Pour que tout reste aligné
            CARA=SIMP(
                statut="f",
                typ="TXM",
                max=1,
                into=(
                    "K_T_N",
                    "K_T_L",
                    "K_TR_N",
                    "K_TR_L",
                    "M_T_N",
                    "M_T_L",
                    "M_TR_N",
                    "M_TR_L",
                    "A_T_N",
                    "A_T_L",
                    "A_TR_N",
                    "A_TR_L",
                ),
            ),
            #  Affection des caractéristiques de RIGIDITE/AMORTISSEMENT/MASSE : NON-SYMETRIQUE
            b_MAK_T_N_NS=BLOC(
                condition="""((equal_to("CARA", 'K_T_N')or(equal_to("CARA", 'A_T_N')or(equal_to("CARA", 'M_T_N')))))""",
                fr=tr("POI1: 4 valeurs (matrice pleine par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=4, max=4),
            ),
            b_MAK_T_L_NS=BLOC(
                condition="""((equal_to("CARA", 'K_T_L')or(equal_to("CARA", 'A_T_L')or(equal_to("CARA", 'M_T_L')))))""",
                fr=tr("SEGMENT: 16 valeurs (matrice pleine par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=16, max=16),
            ),
            b_MAK_TR_N_NS=BLOC(
                condition="""((equal_to("CARA", 'K_TR_N')or(equal_to("CARA", 'A_TR_N')or(equal_to("CARA", 'M_TR_N')))))""",
                fr=tr("POI1: 9 valeurs (matrice pleine par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=9, max=9),
            ),
            b_MAK_TR_L_NS=BLOC(
                condition="""((equal_to("CARA", 'K_TR_L')or(equal_to("CARA", 'A_TR_L')or(equal_to("CARA", 'M_TR_L')))))""",
                fr=tr("SEGMENT: 36 valeurs (matrice pleine par colonne)"),
                GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
                VALE=SIMP(statut="o", typ="R", min=36, max=36),
            ),
        ),
    ),
    #
    # ==============================================================================
    ORIENTATION=FACT(
        statut="f",
        max="**",
        CARA=SIMP(
            statut="o",
            typ="TXM",
            into=(
                "VECT_Y",
                "VECT_Z",
                "ANGL_VRIL",
                "VECT_X_Y",
                "ANGL_NAUT",
                "GENE_TUYAU",
                "VECT_MAIL_Y",
                "VECT_MAIL_Z",
            ),
        ),
        b_cara_vect_y=BLOC(
            condition="""(equal_to("CARA", 'VECT_Y'))""",
            fr=tr("Maille de longueur non nulle."),
            GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
            VALE=SIMP(
                statut="o",
                typ="R",
                max=3,
                min=3,
                fr=tr(
                    "Vecteur dont la projection sur le plan normal à l'axe X local donne l'axe Y local."
                ),
            ),
            PRECISION=SIMP(
                statut="f",
                typ="R",
                fr=tr("valeur en-dessous de laquelle la maille est considérée de longueur nulle"),
            ),
        ),
        b_cara_vect_z=BLOC(
            condition="""(equal_to("CARA", 'VECT_Z'))""",
            fr=tr("Maille de longueur non nulle."),
            GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
            VALE=SIMP(
                statut="o",
                typ="R",
                max=3,
                min=3,
                fr=tr(
                    "Vecteur dont la projection sur le plan normal à l'axe X local donne l'axe Z local."
                ),
            ),
            PRECISION=SIMP(
                statut="f",
                typ="R",
                fr=tr("valeur en-dessous de laquelle la maille est considérée de longueur nulle"),
            ),
        ),
        # VECT_MAIL_Y et VECT_MAIL_Z
        b_cara_vect_mail_y=BLOC(
            condition="""(equal_to("CARA", 'VECT_MAIL_Y'))""",
            fr=tr("Maille de longueur non nulle."),
            GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
            TABLE_CARA=SIMP(statut="o", typ=table_sdaster),
            NOM_SEC=SIMP(statut="o", typ="TXM", validators=LongStr(1, 8)),
            VALE=SIMP(
                statut="o",
                typ="R",
                max=3,
                min=3,
                fr=tr(
                    """Vecteur dont la projection sur le plan normal à l'axe X local
                            donne l'axe y du maillage de la section."""
                ),
            ),
            PRECISION=SIMP(
                statut="f",
                typ="R",
                fr=tr("valeur en-dessous de laquelle la maille est considérée de longueur nulle"),
            ),
        ),
        b_cara_vect_mail_z=BLOC(
            condition="""(equal_to("CARA", 'VECT_MAIL_Z'))""",
            fr=tr("Maille de longueur non nulle."),
            GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
            TABLE_CARA=SIMP(statut="o", typ=table_sdaster),
            NOM_SEC=SIMP(statut="o", typ="TXM", validators=LongStr(1, 8)),
            VALE=SIMP(
                statut="o",
                typ="R",
                max=3,
                min=3,
                fr=tr(
                    """Vecteur dont la projection sur le plan normal à l'axe X local
                            donne l'axe z du maillage de la section."""
                ),
            ),
            PRECISION=SIMP(
                statut="f",
                typ="R",
                fr=tr("valeur en-dessous de laquelle la maille est considérée de longueur nulle"),
            ),
        ),
        #
        b_cara_angl_vril=BLOC(
            condition="""(equal_to("CARA", 'ANGL_VRIL'))""",
            fr=tr("Maille de longueur non nulle."),
            GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
            VALE=SIMP(
                statut="o", typ="R", fr=tr("Angle de rotation du repère autour de l'axe X local.")
            ),
            PRECISION=SIMP(
                statut="f",
                typ="R",
                fr=tr(
                    "valeur en-dessous de laquelle la maille est considérée comme de longueur nulle"
                ),
            ),
        ),
        b_cara_vect_x_y=BLOC(
            condition="""(equal_to("CARA", 'VECT_X_Y'))""",
            fr=tr("Maille de longueur nulle."),
            GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
            VALE=SIMP(
                statut="o",
                typ="R",
                max=6,
                min=6,
                fr=tr("Les 2 vecteurs formant les axes X et Y locaux."),
            ),
            PRECISION=SIMP(
                statut="f",
                typ="R",
                fr=tr(
                    "valeur en-dessous de laquelle la maille est considérée comme de longueur nulle"
                ),
            ),
        ),
        b_cara_angl_naut=BLOC(
            condition="""(equal_to("CARA", 'ANGL_NAUT'))""",
            fr=tr("Maille de longueur nulle."),
            GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
            VALE=SIMP(
                statut="o",
                typ="R",
                max=3,
                min=3,
                fr=tr("Les 3 angles nautiques alpha, beta, gamma."),
            ),
            PRECISION=SIMP(
                statut="f",
                typ="R",
                fr=tr(
                    "valeur en-dessous de laquelle la maille est considérée comme de longueur nulle"
                ),
            ),
        ),
        b_cara_gene_tuyau=BLOC(
            condition="""(equal_to("CARA", 'GENE_TUYAU'))""",
            fr=tr("Orientation des tuyaux."),
            GROUP_NO=SIMP(statut="o", typ=grno, validators=NoRepeat(), max=1),
            VALE=SIMP(
                statut="o",
                typ="R",
                max=3,
                min=3,
                fr=tr("Vecteur donnant la position de la génératrice."),
            ),
            PRECISION=SIMP(statut="f", typ="R", defaut=1.0e-4),
            CRITERE=SIMP(statut="f", typ="TXM", defaut="RELATIF", into=("RELATIF", "ABSOLU")),
        ),
    ),
    #
    # ==============================================================================
    MASSIF=FACT(
        statut="f",
        max="**",
        regles=(
            UN_PARMI("GROUP_MA", "TOUT"),
            UN_PARMI("ANGL_REP", "ORIG_AXE", "ANGL_EULER", "CHAM_ORIE"),
            PRESENT_PRESENT("ANGL_AXE", "ORIG_AXE"),
            ENSEMBLE("TOUT", "CHAM_ORIE"),
        ),
        GROUP_MA=SIMP(statut="f", typ=grma, validators=NoRepeat(), max="**"),
        TOUT=SIMP(statut="f", typ="TXM", validators=NoRepeat(), into=("OUI",)),
        CHAM_ORIE=SIMP(statut="f", typ=(cham_no_sdaster, carte_sdaster, cham_elem)),
        ANGL_REP=SIMP(statut="f", typ="R", min=1, max=3, fr=tr("Un angle en 2D, 3 angles en 3D.")),
        ANGL_EULER=SIMP(
            statut="f", typ="R", min=1, max=3, fr=tr("Un angle en 2D, 3 angles en 3D.")
        ),
        ANGL_AXE=SIMP(statut="f", typ="R", min=2, max=2),
        ORIG_AXE=SIMP(
            statut="f", typ="R", min=2, max=3, fr=tr("2 valeurs en 2D, 3 valeurs en 3D.")
        ),
    ),
    #
    # ==============================================================================
    POUTRE_FLUI=FACT(
        statut="f",
        max="**",
        GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
        B_T=SIMP(statut="o", typ="R"),
        B_N=SIMP(statut="o", typ="R"),
        B_TN=SIMP(statut="f", typ="R", defaut=0.0e0),
        A_FLUI=SIMP(statut="o", typ="R"),
        A_CELL=SIMP(statut="o", typ="R"),
        COEF_ECHELLE=SIMP(statut="o", typ="R"),
    ),
    #
    # ==============================================================================
    GRILLE=FACT(
        statut="f",
        max="**",
        regles=(
            UN_PARMI("ANGL_REP_1", "ANGL_REP_2", "VECT_1", "VECT_2"),
            UN_PARMI("SECTION", "SECTION_FO"),
            EXCLUS("EXCENTREMENT", "EXCENTREMENT_FO"),
        ),
        GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
        SECTION=SIMP(statut="f", typ="R"),
        SECTION_FO=SIMP(statut="f", typ=(fonction_sdaster, nappe_sdaster, formule)),
        ANGL_REP_1=SIMP(
            statut="f",
            typ="R",
            min=2,
            max=2,
            fr=tr("Angles de rotation permettant de définir l'axe local x."),
        ),
        ANGL_REP_2=SIMP(
            statut="f",
            typ="R",
            min=2,
            max=2,
            fr=tr("Angles de rotation permettant de définir l'axe local y."),
        ),
        EXCENTREMENT=SIMP(statut="f", typ="R"),
        EXCENTREMENT_FO=SIMP(statut="f", typ=(fonction_sdaster, nappe_sdaster, formule)),
        VECT_1=SIMP(
            statut="f",
            typ="R",
            min=3,
            max=3,
            fr=tr("La projection de ce vecteur sert à définir l'axe local x."),
        ),
        VECT_2=SIMP(
            statut="f",
            typ="R",
            min=3,
            max=3,
            fr=tr("La projection de ce vecteur sert à définir l'axe local y."),
        ),
        REPERE=SIMP(statut="f", typ="TXM", into=("CYLINDRIQUE", "GLOBAL"), defaut="GLOBAL"),
        b_repere=BLOC(
            condition="""(equal_to("REPERE", "CYLINDRIQUE"))""",
            ORIGINE=SIMP(statut="o", typ="R", min=3, max=3),
            AXE_Z=SIMP(statut="o", typ="R", min=3, max=3),
        ),
        COEF_RIGI_DRZ=SIMP(statut="f", typ="R", defaut=1.0e-10),
    ),
    #
    # ==============================================================================
    MEMBRANE=FACT(
        statut="f",
        max="**",
        regles=(EXCLUS("ANGL_REP_1", "ANGL_REP_2", "VECT_1", "VECT_2"),),
        GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
        EPAIS=SIMP(
            statut="o",
            typ="R",
            val_min=0.0,
            fr=tr(
                "Epaisseur de la membrane ; donnée utilisée uniquement dans le cas non linéaire."
            ),
        ),
        ANGL_REP_1=SIMP(
            statut="f",
            typ="R",
            min=2,
            max=2,
            fr=tr("Angles de rotation permettant de définir l'axe local x."),
        ),
        ANGL_REP_2=SIMP(
            statut="f",
            typ="R",
            min=2,
            max=2,
            fr=tr("Angles de rotation permettant de définir l'axe local y."),
        ),
        VECT_1=SIMP(
            statut="f",
            typ="R",
            min=3,
            max=3,
            fr=tr("La projection de ce vecteur sert à définir l'axe local x."),
        ),
        VECT_2=SIMP(
            statut="f",
            typ="R",
            min=3,
            max=3,
            fr=tr("La projection de ce vecteur sert à définir l'axe local y."),
        ),
        N_INIT=SIMP(
            statut="f",
            typ="R",
            defaut=0.0,
            val_min=0.0,
            fr=tr("Pré-tension initiale ; donnée utilisée uniquement dans le cas non-linéaire."),
        ),
    ),
    #
    # ==============================================================================
    RIGI_PARASOL=FACT(
        statut="f",
        max="**",
        regles=(
            UN_PARMI("COEF_GROUP", "FONC_GROUP"),
            UN_PARMI("COOR_CENTRE", "GROUP_NO_CENTRE"),
            UN_PARMI("GROUP_MA_POI1", "GROUP_MA_SEG2"),
        ),
        GROUP_MA=SIMP(
            statut="o",
            typ=grma,
            validators=NoRepeat(),
            max="**",
            fr=tr("Surface servant à répartir les caractéristiques des discrets"),
        ),
        GROUP_MA_POI1=SIMP(
            statut="f", typ=grma, max=1, fr=tr("Mailles POINT correspondant aux discrets")
        ),
        GROUP_MA_SEG2=SIMP(
            statut="f", typ=grma, max=1, fr=tr("Mailles SEGMENT correspondant aux discrets")
        ),
        FONC_GROUP=SIMP(statut="f", typ=(fonction_sdaster, nappe_sdaster, formule), max="**"),
        COEF_GROUP=SIMP(statut="f", typ="R", max="**"),
        REPERE=SIMP(statut="f", typ="TXM", into=("LOCAL", "GLOBAL"), defaut="GLOBAL"),
        METHODE=SIMP(statut="f", typ="TXM", into=("DIAG", "UNIFORME"), defaut="DIAG"),
        # Pour que tout reste aligné
        CARA=SIMP(
            statut="o",
            typ="TXM",
            validators=NoRepeat(),
            max=2,
            into=(
                "K_TR_D_N",
                "K_T_D_N",
                "K_TR_D_L",
                "K_T_D_L",
                "A_TR_D_N",
                "A_T_D_N",
                "A_TR_D_L",
                "A_T_D_L",
            ),
            fr=tr("Choix des types de discrets du tapis de ressorts."),
        ),
        b_cara=BLOC(
            condition="""exists("CARA") and (len(CARA)==1 or (len(CARA)==2 and CARA[0][2:]==CARA[1][2:]))""",
            fr=tr("Valeurs pour les discrets du tapis de ressorts."),
            VALE=SIMP(
                statut="o",
                typ="R",
                max="**",
                fr=tr("Valeurs pour les discrets du tapis de ressorts."),
            ),
        ),
        GROUP_NO_CENTRE=SIMP(statut="f", typ=grno, max=1),
        COOR_CENTRE=SIMP(statut="f", typ="R", min=2, max=3),
        UNITE=SIMP(statut="f", typ=UnitType(), inout="out"),
    ),
    #
    # ==============================================================================
    RIGI_GRILLE=FACT(
        statut="f",
        max="**",
        GROUP_MA_SEG2=SIMP(
            statut="o",
            typ=grma,
            min=5,
            max=5,
            fr=tr("Mailles de type seg2 correspondant aux discrets"),
        ),
        GROUP_MA=SIMP(
            statut="o",
            typ=grma,
            validators=NoRepeat(),
            max=1,
            fr=tr("Surface servant à répartir les caractéristiques des discrets"),
        ),
        GROUP_NO_CENTRE=SIMP(statut="o", typ=grno, min=5, max=5),
        OPTION=SIMP(statut="f", typ="TXM", into=("RIGI",), defaut="RIGI"),
        METHODE=SIMP(statut="f", typ="TXM", into=("DIAG", "UNIFORME"), defaut="DIAG"),
        VALE=SIMP(
            statut="o",
            typ="R",
            min=5,
            max=5,
            fr=tr("Valeurs pour les discrets du tapis de ressorts."),
        ),
    ),
    #
    # ==============================================================================
    RIGI_MISS_3D=FACT(
        statut="f",
        max=1,
        GROUP_MA_POI1=SIMP(statut="o", typ=grma, max=1),
        GROUP_MA_SEG2=SIMP(statut="f", typ=grma, max=1),
        FREQ_EXTR=SIMP(statut="o", typ="R", max=1),
        UNITE_RESU_IMPE=SIMP(statut="f", typ=UnitType(), defaut=30, inout="in"),
    ),
    #
    # ==============================================================================
    MASS_AJOU=FACT(
        statut="f",
        max=1,
        GROUP_MA=SIMP(
            statut="o",
            typ=grma,
            max=1,
            fr=tr("Surface servant à répartir les caractéristiques des discrets"),
        ),
        GROUP_MA_POI1=SIMP(
            statut="o", typ=grma, max=1, fr=tr("Mailles de type point correspondant aux discrets")
        ),
        FONC_GROUP=SIMP(statut="o", max=1, typ=(fonction_sdaster, nappe_sdaster, formule)),
    ),
    #
    # ==============================================================================
    MASS_REP=FACT(
        statut="f",
        max="**",
        fr=tr("Masse répartie sur des POI1, pondérée par la surface des mailles connectées."),
        GROUP_MA=SIMP(
            statut="o", typ=grma, max=1, fr=tr("Surface ou ligne servant à répartir la masse")
        ),
        GROUP_MA_POI1=SIMP(
            statut="o", typ=grma, max=1, fr=tr("Mailles de type POI1 correspondant aux masses.")
        ),
        VALE=SIMP(
            statut="o",
            typ="R",
            max=1,
            fr=tr("Valeur de la masse à répartir sur les mailles de GROUP_MA."),
        ),
        TYPE=SIMP(
            statut="o",
            typ="TXM",
            max=1,
            into=("TOTALE", "LINEIQUE", "SURFACIQUE"),
            fr=tr("Type de la masse à répartir."),
        ),
        FONC_MULT=SIMP(
            statut="f",
            typ=(fonction_sdaster, nappe_sdaster, formule),
            max=1,
            fr=tr("Fonction (X,Y,Z) multiplicatrice de la masse."),
        ),
    ),
    #
    # ==============================================================================
    GEOM_FIBRE=SIMP(
        statut="f",
        max=1,
        typ=gfibre_sdaster,
        fr=tr(
            "Donner le nom de la SD regroupant tous les groupes de fibres (issue de DEFI_GEOM_FIBRE)"
        ),
    ),
    #
    # ==============================================================================
    MULTIFIBRE=FACT(
        statut="f",
        max="**",
        GROUP_MA=SIMP(statut="o", typ=grma, validators=NoRepeat(), max="**"),
        GROUP_FIBRE=SIMP(statut="o", typ="TXM", max="**"),
        PREC_AIRE=SIMP(statut="f", typ="R", defaut=0.01),
        PREC_INERTIE=SIMP(statut="f", typ="R", defaut=0.1),
    ),
)
