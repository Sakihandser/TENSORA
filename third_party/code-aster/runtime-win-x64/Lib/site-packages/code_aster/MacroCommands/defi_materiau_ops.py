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

import numpy
from libaster import AsterError, createEnthalpy, resetFortranLoggingLevel, setFortranLoggingLevel

from ..Cata.Syntax import _F
from ..Messages import UTMESS
from ..Objects import Function, Material
from ..Helpers import check_dis_choc_elas


def defi_materiau_ops(self, **args):
    """Execute the command.

    Arguments:
        **args (dict): User's keywords.
    """

    args = _F(args)
    setFortranLoggingLevel(args["INFO"])

    # reuse, copy from or new object
    if args.get("reuse"):
        assert args["reuse"] == args["MATER"]
        mater = args["MATER"]
    elif args.get("MATER"):
        mater = Material(args["MATER"])
    else:
        mater = Material()

    # In this function, we can check the value of keywords and add some properties
    check_keywords(args)

    visit = mater.Builder(mater)
    self._cata.accept(visit, args)

    resetFortranLoggingLevel()
    check_young_consistency(mater)
    if args["INFO"] == 2:
        mater.debugPrint()

    return mater


def check_young_consistency(mater):
    """Check the consistency between E provided as a constant under 'ELAS'
    and the first point of the 'TRACTION' function.

    Arguments:
        mater (Material): Object to be checked.
    """

    def _check(valP, name, young, point):
        slope = point[len(point) // 2] / point[0]
        if abs(young - slope) > 0.01 * young:
            if valP is None:
                UTMESS("F", "MATERIAL1_5", valr=slope)
            else:
                UTMESS("F", "MATERIAL1_6", valr=(valP, young, slope), valk=name)

    matNames = mater.getMaterialNames()
    if "TRACTION" not in matNames or "ELAS" not in matNames:
        return

    trac = mater.getFunction("TRACTION", "SIGM")
    propT = trac.getProperties()
    if propT[0] not in ("FONCTION", "NAPPE"):
        # should probably be blocked in catalog
        UTMESS("F", "MATERIAL1_10")
        return

    moduleE = mater.getFunction("ELAS", "E")
    if not moduleE:
        moduleE = mater.getValueReal("ELAS", "E")
        if propT[0] == "NAPPE":
            for i, para in enumerate(trac.getParameters()):
                _check(para, propT[2], moduleE, trac.getValues()[i])
        else:
            _check(None, None, moduleE, trac.getValues())
    else:
        propE = moduleE.getProperties()
        if propT[0] == "FONCTION":
            UTMESS("F", "MATERIAL1_8", valk=propE[2])
            return
        if propT[2] != propE[2]:
            UTMESS("F", "MATERIAL1_9", valk=(propE[2], propT[2]))
            return
        for i, para in enumerate(trac.getParameters()):
            try:
                young = moduleE(para)
            except AsterError:
                young = None

            if young is None:
                UTMESS("F", "MATERIAL1_7", valk=propE[2], valr=para)
            else:
                _check(para, propT[2], young, trac.getValues()[i])


# internal methods
def check_keywords(kwargs):
    """Check for DEFI_MATERIAU keywords

    Arguments:
        kwargs (dict): User's keywords, changed in place.
    """

    if "DIS_ECRO_TRAC" in kwargs:
        check_dis_ecro_trac(kwargs["DIS_ECRO_TRAC"])
    if "DIS_CHOC_ENDO" in kwargs:
        check_dis_choc_endo(kwargs["DIS_CHOC_ENDO"])
    if "DIS_CHOC_ELAS" in kwargs:
        check_dis_choc_elas(kwargs["DIS_CHOC_ELAS"], options=["RIGIP"])
    if "JONC_ENDO_PLAS" in kwargs:
        check_dis_jvp(kwargs["JONC_ENDO_PLAS"])
    if "THER_NL" in kwargs:
        add_enthalpy(kwargs["THER_NL"])
    if "THER_NL_ORTH" in kwargs:
        add_enthalpy(kwargs["THER_NL_ORTH"])


def check_dis_ecro_trac(keywords):
    """Check for function for DIS_ECRO_TRAC

    Arguments:
        keywords (dict): DIS_ECRO_TRAC keyword, changed in place.
    """

    # jean-luc.flejou@edf.fr
    def _message(num, mess=""):
        dict_args = dict(valk=("DIS_ECRO_TRAC", "FX=f(DX) | FTAN=f(DTAN)", mess), vali=num)
        UTMESS("F", "DISCRETS_62", **dict_args)

    iffx = False
    ifft = False
    precis = 1.0e-08
    if "FX" in keywords:
        iffx = True
        fct_x = keywords["FX"]

    if "FTAN" in keywords:
        ifft = True
        fct_t = keywords["FTAN"]

    if (iffx or ifft) == False:
        _message(1)

    if iffx:
        # Les vérifications sur la fonction
        #       interpolation LIN LIN
        #       prolongée à gauche et à droite exclue
        #       paramètre 'DX' ou 'DTAN'
        OkFct = type(fct_x) is Function
        param = fct_x.Parametres()
        OkFct = OkFct and param["INTERPOL"][0] == "LIN"
        OkFct = OkFct and param["INTERPOL"][1] == "LIN"
        OkFct = OkFct and param["PROL_DROITE"] == "EXCLU"
        OkFct = OkFct and param["PROL_GAUCHE"] == "EXCLU"
        OkFct = OkFct and param["NOM_PARA"] == "DX"
        if not OkFct:
            _message(2, "%s" % param)

        # avoir 3 points minimum ou exactement
        absc_x, ordo_x = fct_x.Valeurs()
        OkFct = OkFct and len(absc_x) >= 3
        if not OkFct:
            _message(3, "%s" % len(absc_x))

        # Point n°1: (DX=0, FX=0)

        dx = absc_x[0]
        fx = ordo_x[0]
        OkFct = OkFct and dx >= 0.0 and abs(dx) <= precis
        OkFct = OkFct and fx >= 0.0 and abs(fx) <= precis
        if not OkFct:
            _message(4, "[%s %s]" % (dx, fx))

        # fx et dx sont strictement positifs, dFx >0 , dDx >0
        #   Au lieu de la boucle, on peut faire :
        #       xx=np.where(np.diff(absc) <= 0.0 or np.diff(ordo) <= 0.0)[0]
        #       if ( len(xx) != 0):
        #           message 6 : absc[xx[0]] ordo[xx[0]] absc[xx[0]+1] ordo[xx[0]+1]
        #       dfx= np.diff(ordo)/np.diff(absc)
        #       xx=np.where(np.diff(dfx) <= 0.0 )[0]
        #       if ( len(xx) != 0):
        #           message 7 : xx[0] dfx[xx[0]] dfx[xx[0]+1]
        for ii in range(1, len(absc_x)):
            if absc_x[ii] <= dx or ordo_x[ii] <= fx:
                _message(
                    5,
                    "Ddx, Dfx > 0 : p(i)[%s %s]  "
                    "p(i+1)[%s %s]" % (dx, fx, absc_x[ii], ordo_x[ii]),
                )
            if ii == 1:
                dfx = (ordo_x[ii] - fx) / (absc_x[ii] - dx)
                raidex = dfx
            else:
                dfx = (ordo_x[ii] - fx) / (absc_x[ii] - dx)
                if dfx > raidex:
                    _message(6, "(%d) : %s > %s" % (ii, dfx, raidex))

            dx = absc_x[ii]
            fx = ordo_x[ii]
            raidex = dfx

    if ifft:
        # Les vérifications sur la fonction
        #       interpolation LIN LIN
        #       prolongée à gauche et à droite exclue
        #       paramètre 'DX' ou 'DTAN'
        OkFct = type(fct_t) is Function
        param = fct_t.Parametres()
        OkFct = OkFct and param["INTERPOL"][0] == "LIN"
        OkFct = OkFct and param["INTERPOL"][1] == "LIN"
        OkFct = OkFct and param["PROL_DROITE"] == "EXCLU"
        OkFct = OkFct and param["PROL_GAUCHE"] == "EXCLU"
        OkFct = OkFct and param["NOM_PARA"] == "DTAN"
        if not OkFct:
            _message(2, "%s" % param)

        # avoir 3 points minimum ou exactement
        absc_t, ordo_t = fct_t.Valeurs()
        if keywords["ECROUISSAGE"] == "ISOTROPE":
            OkFct = OkFct and len(absc_t) >= 3
        elif keywords["ECROUISSAGE"] == "CINEMATIQUE":
            OkFct = OkFct and len(absc_t) == 3
        else:
            raise RuntimeError("Unknown value")
        if not OkFct:
            _message(3, "%s" % len(absc_t))

        # Point n°1: (DX=0, FX=0)
        dx = absc_t[0]
        fx = ordo_t[0]
        OkFct = OkFct and dx >= 0.0 and abs(dx) <= precis
        OkFct = OkFct and fx >= 0.0 and abs(fx) <= precis
        if not OkFct:
            _message(4, "[%s %s]" % (dx, fx))

        # fx et dx sont strictement positifs, dFx >0 , dDx >0
        #   Au lieu de la boucle, on peut faire :
        #       xx=np.where(np.diff(absc) <= 0.0 or np.diff(ordo) <= 0.0)[0]
        #       if ( len(xx) != 0):
        #           message 6 : absc[xx[0]] ordo[xx[0]] absc[xx[0]+1] ordo[xx[0]+1]
        #       dfx= np.diff(ordo)/np.diff(absc)
        #       xx=np.where(np.diff(dfx) <= 0.0 )[0]
        #       if ( len(xx) != 0):
        #           message 7 : xx[0] dfx[xx[0]] dfx[xx[0]+1]
        for ii in range(1, len(absc_t)):
            if absc_t[ii] <= dx or ordo_t[ii] <= fx:
                _message(
                    5,
                    "Ddx, Dfx > 0 : p(i)[%s %s]  "
                    "p(i+1)[%s %s]" % (dx, fx, absc_t[ii], ordo_t[ii]),
                )
            if ii == 1:
                dfx = (ordo_t[ii] - fx) / (absc_t[ii] - dx)
                raidex = dfx
            else:
                dfx = (ordo_t[ii] - fx) / (absc_t[ii] - dx)
                if dfx > raidex:
                    _message(6, "(%d) : %s > %s" % (ii, dfx, raidex))

            dx = absc_t[ii]
            fx = ordo_t[ii]
            raidex = dfx


def check_dis_choc_endo(keywords):
    """Check for functions for DIS_CHOC_ENDO

    Arguments:
        keywords (dict): DIS_CHOC_ENDO keyword, changed in place.
    """

    # jean-luc.flejou@edf.fr
    def _message(num, mess2="", mess3=""):
        UTMESS("F", "DISCRETS_63", valk=("DIS_CHOC_ENDO", mess2, mess3), vali=(num,))

    precis = 1.0e-08
    # Conditions communes aux 3 fonctions
    #   paramètre 'DX'
    #   interpolation LIN LIN
    #   prolongée à gauche et à droite : constant ou exclue (donc pas linéaire)
    LesFcts = [keywords["FX"], keywords["RIGI_NOR"], keywords["AMOR_NOR"]]
    LesFctsName = []
    for fct in LesFcts:
        OkFct = type(fct) is Function
        param = fct.Parametres()
        OkFct = OkFct and param["NOM_PARA"] == "DX"
        OkFct = OkFct and param["INTERPOL"][0] == "LIN"
        OkFct = OkFct and param["INTERPOL"][1] == "LIN"
        OkFct = OkFct and param["PROL_DROITE"] != "LINEAIRE"
        OkFct = OkFct and param["PROL_GAUCHE"] != "LINEAIRE"
        LesFctsName.append(fct.getName())
        if not OkFct:
            _message(2, fct.getName(), "%s" % param)
    # Même nombre de point, 5 points minimum
    Fxx, Fxy = keywords["FX"].Valeurs()
    Rix, Riy = keywords["RIGI_NOR"].Valeurs()
    Amx, Amy = keywords["AMOR_NOR"].Valeurs()
    OkFct = len(Fxx) == len(Rix) == len(Amx)
    OkFct = OkFct and (len(Fxx) >= 5)
    if not OkFct:
        _message(3, "%s" % LesFctsName, "%d, %d, %d" % (len(Fxx), len(Rix), len(Amx)))
    # La 1ère abscisse c'est ZERO
    x1 = Fxx[0]
    if not (0.0 <= x1 <= precis):
        _message(4, "%s" % LesFctsName, "%s" % x1)
    # Même abscisses pour les 3 fonctions, à la précision près
    # Abscisses strictement croissantes, à la précision près
    #   Au lieu de la boucle, on peut faire :
    #       xx=np.where(np.abs(Fxx-Rix) + np.abs(Fxx-Amx) > precis )[0]
    #       if ( len(xx) != 0):
    #           message 5 : xx[0] Fxx[xx[0]] Rix[xx[0]] Amx[xx[0]]
    #       xx=np.where(np.diff(Fxx)<0 or np.diff(Rix)<0 or np.diff(Amx)<0)[0]
    #       if ( len(xx) != 0):
    #           message 6 : xx[0] Fxx[xx[0]] Fxx[xx[0]+1]
    xp1 = -1.0
    for ii in range(len(Fxx)):
        x1 = Fxx[ii]
        x2 = Rix[ii]
        x3 = Amx[ii]
        ddx = abs(x1 - x2) + abs(x1 - x3)
        if ddx > precis:
            _message(5, "%s" % LesFctsName, "(%d) : %s, %s, %s" % (ii + 1, x1, x2, x3))
        if xp1 >= x1:
            _message(6, "%s" % LesFctsName, "(%d) : %s, %s" % (ii + 1, xp1, x1))
        xp1 = x1
    # FX : les 2 premiers points ont la même valeur à la précision relative près
    if abs(Fxy[0] - Fxy[1]) > Fxy[0] * precis:
        _message(7, keywords["FX"].userName)
    # RIGI_NOR : les 2 premiers points ont la même valeur à la précision relative près
    if abs(Riy[0] - Riy[1]) > Riy[0] * precis:
        _message(8, keywords["RIGI_NOR"].userName)
    # RIGI_NOR : pente décroissante, à partir du 3ème point.
    #   Au lieu de la boucle, on peut faire :
    #       xx=np.where(np.diff(Riy[2:]) > 0.0 )[0]+2
    #       if ( len(xx) != 0):
    #           message 9 : xx[0] Riy[xx[0]] Riy[xx[0]+1]
    pente = Riy[2]
    for ii in range(3, len(Riy)):
        if Riy[ii] - pente > Riy[0] * precis:
            _message(9, "%s" % keywords["RIGI_NOR"].userName, "(%d) : %s %s" % (ii, pente, Riy[ii]))
        pente = Riy[ii]
    # --------------------------------------------------------------- Fin des vérifications
    # Création des fonctions
    newFx = Function()
    newFx.setResultName("Force   (plast cumulée)")
    newRi = Function()
    newRi.setResultName("Raideur (plast cumulée)")
    newAm = Function()
    newAm.setResultName("Amort.  (plast cumulée)")
    newFx.setExtrapolation("CC")
    newRi.setExtrapolation("CC")
    newAm.setExtrapolation("CC")
    newFx.setInterpolation("LIN LIN")
    newRi.setInterpolation("LIN LIN")
    newAm.setInterpolation("LIN LIN")
    newFx.setParameterName("PCUM")
    newRi.setParameterName("PCUM")
    newAm.setParameterName("PCUM")
    # Modification des abscisses pour avoir la plasticité cumulée et plus le déplacement
    pp9 = numpy.round(numpy.array(Fxx) - numpy.array(Fxy) / numpy.array(Riy), 10)
    # Le 1er point a une abscisse négative et la valeur du 2ème point
    pp9[0] = -pp9[2]
    # Vérification que p est strictement croissant.
    #   Au lieu de la boucle, on peut faire :
    #       xx=np.where(np.diff(pp9) < 0)[0]
    #       if ( len(xx) != 0):
    #           message 10 : xx[0] pp9[xx[0]] pp9[xx[0]+1]
    pp = pp9[0]
    for ii in range(1, len(pp9)):
        if pp > pp9[ii]:
            _message(10, mess3="(%d) : %s %s" % (ii, pp, pp9[ii]))
        pp = pp9[ii]

    # Affectations des valeurs
    newFx.setValues(pp9, Fxy)
    newRi.setValues(pp9, Riy)
    newAm.setValues(pp9, Amy)
    # Affectation des nouvelles fonctions
    keywords["FXP"] = newFx
    keywords["RIGIP"] = newRi
    keywords["AMORP"] = newAm


def check_dis_jvp(keywords):
    """Check for parameters in JONC_ENDO_PLAS

    Arguments:
        keywords (dict): JONC_ENDO_PLAS keyword, changed in place.
    """

    def _message(num):
        UTMESS("F", "DISCRETS_65", valk=("JONC_ENDO_PLAS"), vali=num)

    ke = keywords["KE"]
    kp = keywords["KP"]
    kdp = keywords["KDP"]
    kdm = keywords["KDM"]
    myp = keywords["MYP"]
    mym = keywords["MYM"]
    rdp = keywords["RDP"]
    rdm = keywords["RDM"]

    if ke < kp:
        _message(1)
    elif kdp < kp or kdp > ke:
        _message(2)
    elif kdm < kp or kdm > ke:
        _message(3)
    elif myp < ke * rdp:
        _message(4)
    elif mym > ke * rdm:
        _message(5)


def add_enthalpy(keywords):
    """Check for functions for THER_NL. Create "Beta" from "Rho_CP" if not given

    Arguments:
        keywords (dict): THER_NL keyword, changed in place.
    """

    # Create "Beta" from "Rho_CP" if not given
    if keywords.get("BETA") is None:
        beta = Function()
        createEnthalpy(keywords["RHO_CP"], beta)
        keywords["BETA"] = beta
