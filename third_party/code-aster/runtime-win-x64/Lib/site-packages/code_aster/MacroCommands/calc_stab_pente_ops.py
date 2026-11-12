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
import tempfile
from typing import List, Dict, Callable
from datetime import datetime
from ..Messages import UTMESS
from ..Cata.Syntax import _F
from ..Supervis import CO
from ..MacroCommands.macr_adap_mail_ops import HOMARD_INFOS
from ..Objects import Material, Mesh, Model, Physics, Modelings, ExternalVariableTraits
from ..CodeCommands import (
    DEFI_GROUP,
    AFFE_MATERIAU,
    AFFE_MODELE,
    STAT_NON_LINE,
    CALC_CHAMP,
    CREA_CHAMP,
    CREA_MAILLAGE,
    CREA_RESU,
    MACR_ADAP_MAIL,
    POST_RELEVE_T,
    POST_ELEM,
    PROJ_CHAMP,
    CREA_TABLE,
    FORMULE,
)


def calc_stab_pente_ops(self, **args):
    if args["METHODE_STAB"] == "SRM":
        TABFS = calc_srm(self, args)
    else:
        if args["METHODE_LEM"] in ["BISHOP", "FELLENIUS"]:
            Solver = Surf_Circ_Solver(self, args)
        else:
            Solver = Surf_Non_Circ_Solver(self, args)

        TABFS = Solver.run()
        del Solver

    return TABFS


def calc_srm(self, args):
    """SRM solver

    Args:
        args (dict): Input parameters.

    Returns:
        Table Aster: Table containing the output results.
    """

    chmat = args["CHAM_MATER"]
    modele = args["MODELE"]

    # Vérification du maillage en entrée
    if not chmat.getMesh() == modele.getMesh():
        UTMESS("F", "CALCSTABPENTE_1")
    assert chmat.getMesh() == modele.getMesh()

    # Récupération du concept de maillage, de l'affectation des matériaux et des variables de commande
    mesh = chmat.getMesh()
    Para_Mat = get_para_mat(chmat)
    List_Affe_ExtVari = get_syntax_affevarc(chmat)

    # Vérification et analyse de l'affectation des matériaux dans la zone SRM
    dict_zone_deg = None
    has_zone_srm = False
    lgrma_cree = []

    if args.get("GROUP_MA") is not None:
        has_zone_srm = True
        lgrma_deg = args["GROUP_MA"]
        mesh, dict_zone_deg, lgrma_cree = check_srm_zone(lgrma_deg, Para_Mat)
        Para_Mat["MAILLAGE"] = mesh

    # Mots clé INVARIANT de l'AFFE_MATERIAU
    KW_Chmat_Fix = {}
    KW_Chmat_Fix["MAILLAGE"] = mesh
    if len(List_Affe_ExtVari) > 0:
        KW_Chmat_Fix["AFFE_VARC"] = List_Affe_ExtVari

    # Mots clé INVARIANT du STAT_NON_LINE
    KW_Solveur_Fix = {}
    KW_Solveur_Fix["MODELE"] = modele

    mc_increment = args.get("INCREMENT")
    KW_Solveur_Fix["INCREMENT"] = mc_increment
    if mc_increment["INST_FIN"] is not None:
        tfin = mc_increment["INST_FIN"]
    else:
        linst = mc_increment["LIST_INST"].getValues()
        if mc_increment["NUME_INST_FIN"] is not None:
            tfin = linst[mc_increment["NUME_INST_FIN"]]
        else:
            tfin = linst[-1]

    KW_Solveur_Fix["CONVERGENCE"] = args.get("CONVERGENCE")

    mc_cpt = args.get("COMPORTEMENT")

    CPT_UTIL = check_srm_cpt(mc_cpt, mesh, args)

    KW_Solveur_Fix["COMPORTEMENT"] = mc_cpt
    KW_Solveur_Fix["EXCIT"] = args.get("EXCIT")

    # Paramètres qui contrôlent la convergence de l'algorithme SRM
    para_fs = args["FS"][0]
    fact = para_fs["FS_INIT"]
    prec = para_fs["INCR_INIT"]
    prec_fin = para_fs["RESI_MAXI"]
    num_iter_max = para_fs["ITER_MAXI"]
    loi_vari = para_fs["METHODE"]

    if fact < 0:
        UTMESS("F", "CALCSTABPENTE_13")

    if prec_fin > prec:
        UTMESS("A", "CALCSTABPENTE_2", valr=prec)
        prec_fin = prec

    if loi_vari == "LINEAIRE":
        d_prec = (prec - prec_fin) / para_fs["ITER_RAFF_LINE"]
    else:
        d_prec = None

    num_iter = 0
    NC_fact = -1  # Indicateur de fact "divergant" qu'on vient de trouver

    __DISPT = FORMULE(NOM_PARA=("DX", "DY"), VALE="sqrt(DX*DX + DY*DY)")
    lfos = []
    lmaxdisp = []

    while True:
        if num_iter == num_iter_max:
            # Non-convergence
            UTMESS("F", "CALCSTABPENTE_3")
            break

        KW_Mat_Deg = gene_deg_kwmat(CPT_UTIL, Para_Mat, dict_zone_deg, fact, args)

        __CM_DEG = AFFE_MATERIAU(AFFE=KW_Mat_Deg, **KW_Chmat_Fix)

        try:
            __RESU = STAT_NON_LINE(CHAM_MATER=__CM_DEG, **KW_Solveur_Fix)
        except:
            if num_iter == 0:
                # FS_INIT trop grand.
                UTMESS("F", "CALCSTABPENTE_4")

            del __CM_DEG

            if prec - prec_fin > 1e-10:
                # Raffiner la précision suivant la loi indiquée
                NC_fact = fact
                fact, prec = refinement(fact, prec, d_prec)
                continue
            else:
                break

        # En cas de convergence --> Post-traitement

        __RESU = CALC_CHAMP(reuse=__RESU, RESULTAT=__RESU, VARI_INTERNE=("VARI_NOEU",))

        __CHDEP = CREA_CHAMP(
            INST=tfin, NOM_CHAM="DEPL", OPERATION="EXTR", RESULTAT=__RESU, TYPE_CHAM="NOEU_DEPL_R"
        )
        __CHFONC = CREA_CHAMP(
            AFFE=_F(NOM_CMP=("X1",), TOUT="OUI", VALE_F=(__DISPT,)),
            MAILLAGE=mesh,
            OPERATION="AFFE",
            TYPE_CHAM="NOEU_NEUT_F",
        )
        __CHDT = CREA_CHAMP(
            CHAM_F=__CHFONC, CHAM_PARA=(__CHDEP,), OPERATION="EVAL", TYPE_CHAM="NOEU_NEUT_R"
        )
        if has_zone_srm:
            # Calcul du depl_tot_maxi dans la zone srm
            __TABDT = POST_RELEVE_T(
                ACTION=_F(
                    CHAM_GD=__CHDT,
                    INTITULE="XX",
                    GROUP_MA=lgrma_deg,
                    OPERATION=("EXTREMA",),
                    TOUT="OUI",
                )
            )
        else:
            # Calcul du depl_tot_maxi dans le modèle entier
            __TABDT = POST_RELEVE_T(
                ACTION=_F(CHAM_GD=__CHDT, INTITULE="XX", OPERATION=("EXTREMA",), TOUT="OUI")
            )
        tabdt = __TABDT.EXTR_TABLE().values()
        lmaxdisp.append(tabdt["VALE"][2])
        lfos.append(fact)

        # MAJ des iterateurs
        fact += prec
        num_iter += 1
        if np.abs(NC_fact - fact) < prec:
            fact, prec = refinement(fact, prec, d_prec)
        del __CHDEP, __CHFONC, __CHDT, __TABDT

    # FIN de l'algorithme SRM
    if args.get("CHAM_DEFO") is not None:
        self.register_result(__RESU, args["CHAM_DEFO"])
    l_num_ord = [i + 1 for i in range(len(lfos))]
    TABFS = CREA_TABLE(
        LISTE=(
            _F(LISTE_I=l_num_ord, PARA="NUMERO"),
            _F(LISTE_R=lfos, PARA="FS"),
            _F(LISTE_R=lmaxdisp, PARA="DISP_TOT_MAXI"),
        )
    )

    # Suppression des modifications sur le maillage
    if len(lgrma_cree) > 0:
        mesh = DEFI_GROUP(DETR_GROUP_MA=_F(NOM=lgrma_cree), MAILLAGE=mesh)

    return TABFS


def refinement(fact, prec, d_prec):
    """Computes the refinement factor and precision.

    Args:
        fact (float): Current reduction factor.
        prec (float): Current reduction factor increment (precision).
        d_prec (float/None Type): Variation of precision if METHODE = 'LINEAIRE', None if not.

    Returns:
        tuple: Tuple containing the reduction factor and precision after refinement.
    """

    fact_raf = fact - prec
    if d_prec is None:
        prec_raf = prec / 2
    else:
        prec_raf = prec - d_prec
    fact_raf += prec_raf

    return fact_raf, prec_raf


def check_srm_cpt(mc_cpt, mesh, args):
    """Verify that there exist only one material behaviour
    among MOHR_COULOMB and DRUCKER_PRAGER in the SRM zone.

    Args:
        mc_cpt (list): List of factor keywords of the keyword 'COMPORTEMENT'.
        mesh (Mesh object): Mesh involved in the input cham_mater.
        args (dict): Input arguments of the macro-command.

    Returns:
        str: Name of the material behaviour used in the SRM algorithm.
    """

    cpt_auto = ["MOHR_COULOMB", "DRUCK_PRAGER"]
    cpt_exis = []
    if args.get("TOUT") is not None:
        for mcf_cpt in mc_cpt:
            if mcf_cpt["RELATION"] not in cpt_auto:
                UTMESS("F", "CALCSTABPENTE_5", valk=mcf_cpt["RELATION"])
            cpt_exis.append(mcf_cpt["RELATION"])
    else:
        lgrma_deg = args["GROUP_MA"]
        for mcf_cpt in mc_cpt:
            if mcf_cpt.get("MAILLE"):
                UTMESS("F", "CALCSTABPENTE_6")

            isGPMA = mcf_cpt.get("GROUP_MA")

            cpt = mcf_cpt["RELATION"]
            if isGPMA is None:
                if cpt not in cpt_auto:
                    UTMESS("F", "CALCSTABPENTE_5", valk=cpt)
                cpt_exis.append(cpt)
            else:
                lgrma_cpt = mcf_cpt["GROUP_MA"]
                for grma in lgrma_deg:
                    lgrma_inter = check_ma_intersec(mesh, grma, lgrma_cpt)
                    if len(lgrma_inter) > 1:
                        if cpt not in cpt_auto:
                            UTMESS("F", "CALCSTABPENTE_5", valk=cpt)
                        cpt_exis.append(cpt)

    cpt_exis = list(set(cpt_exis))

    if len(cpt_exis) != 1:
        UTMESS("F", "CALCSTABPENTE_7")

    return cpt_exis[0]


def check_srm_zone(lgrma_deg, Para_Mat):
    """In case of SRM analysis applied to a part of the model,
    verify the existence of the group_mas defining the SRM zone in the group_mas involved
    in the input cham_mater.
    if exist --> copy the group_ma,
    if not exist --> calculate the sous-groupe_ma if intersection detected.

    Args:
        lgrma_deg (list[str]): List of the group_ma defining the SRM zone.
        Para_Mat (dict): Materials and the related groupe_mas involved in the input cham_mater.

    Returns:
        tuple: Tuple containing the mesh enriched by the sous-group_mas,
            dict with materials in the SRM zone as keys and the concerned group_mas as values,
            and the list of names of created group_mas.
    """

    mesh = Para_Mat["MAILLAGE"]
    mat_zone = Para_Mat["AFFE_MATER"]
    dict_zone_deg = {}
    motcles_creagrma = []
    lgrma_cree = []

    lmat = list(mat_zone.keys())

    for imat in range(len(lmat)):
        mat = lmat[imat]
        if mat_zone[mat] == "TOUT":
            dict_zone_deg[mat] = lgrma_deg
        else:
            lgrma_srm = []
            lgrma_auxi = []
            for grma_deg in lgrma_deg:
                if grma_deg in mat_zone[mat]:
                    lgrma_srm.append(grma_deg)
                else:
                    lgrma_inter = check_ma_intersec(mesh, grma_deg, mat_zone[mat])

                    if len(lgrma_inter) > 1:
                        # mat se trouve dans la zone SRM --> Créer grma d'intersec
                        nom_grma = grma_deg + "_mat" + str(imat) + "_SRM"
                        if len(nom_grma) > 24:
                            UTMESS("F", "CALCSTABPENTE_8", valk=grma_deg)
                        motcles_creagrma.extend(
                            [
                                _F(UNION=lgrma_inter[1:], NOM=nom_grma + "_U"),
                                _F(INTERSEC=(lgrma_inter[0], nom_grma + "_U"), NOM=nom_grma),
                            ]
                        )
                        # motcles_creagrma.append(_F(INTERSEC=lgrma_inter, NOM=nom_grma))
                        lgrma_auxi.append(nom_grma + "_U")
                        lgrma_srm.append(nom_grma)

            if len(lgrma_srm) > 0:
                dict_zone_deg[mat] = lgrma_srm
                lgrma_cree.extend(lgrma_srm + lgrma_auxi)

    if motcles_creagrma:
        mesh = DEFI_GROUP(CREA_GROUP_MA=motcles_creagrma, MAILLAGE=mesh)

    return mesh, dict_zone_deg, lgrma_cree


def check_ma_intersec(mesh, grma_obj, lgrma):
    """Detect the intersection between a group_ma and a list of group_mas.

    Args:
        mesh (Mesh object): Mesh involved in the input cham_mater.
        grma_obj (str): Name of the group_ma to be checked.
        lgrma (list[str]): List of the groups_mas that grma_obj may intersect with.

    Returns:
        list: List of the group_mas in lgrma presenting common cells with grma_obj.
    """
    grma_all = mesh.getGroupsOfCells()
    lgrma_inter = [grma_obj]

    if grma_obj not in grma_all:
        UTMESS("F", "CALCSTABPENTE_9", valk=grma_obj)

    nugrma_obj = mesh.getCells(grma_obj)

    for grma in lgrma:
        nugrma = mesh.getCells(grma)
        nucom = list(set(nugrma) & set(nugrma_obj))

        if len(nucom) > 0:
            lgrma_inter.append(grma)

    return lgrma_inter


def gene_deg_kwmat(CPT_SRM, Para_Mat, dict_zone_deg, fact, args):
    """Generate the factor keywords 'AFFE' of the operator AFFE_MATERIAU
    which produces the degraded cham_mater.

    Args:
        CPT_SRM (str): Material behaviour used in the SRM algorithm.
        Para_Mat (dict): Input material field parameters.
        dict_zone_deg (dict): Degraded material field parameters in the SRM zone.
        fact (float): Strength reduction factor.
        args (dict): Arguments of CALC_STAB_PENTE.

    Returns:
        dict: Dict of the factor keywords of AFFE_MATERIAU.
    """

    mat_zone = Para_Mat["AFFE_MATER"]
    KW_Mat_Deg = []

    if args.get("TOUT") is not None:
        # La zone SRM est la totalité du maillage
        for mat in list(mat_zone.keys()):
            nom_mats = mat.getMaterialNames()

            # Vérifier l'existance de CPT_SRM dans les cpts du matériau
            if CPT_SRM not in nom_mats:
                UTMESS("F", "CALCSTABPENTE_10")

            # Générer le matériau dégradé
            Matdeg = gene_deg_mat(mat, CPT_SRM, fact)
            if mat_zone[mat] == "TOUT":
                KW_Mat_Deg.append(_F(MATER=(Matdeg,), TOUT="OUI"))
            else:
                KW_Mat_Deg.append(_F(MATER=(Matdeg,), GROUP_MA=mat_zone[mat]))

    elif args.get("GROUP_MA") is not None:
        # Affectation par le principe de surcharge

        # Etape 1 : Reproduction du cham_mater saint
        for mat in list(mat_zone.keys()):
            if mat_zone[mat] == "TOUT":
                KW_Mat_Deg.append(_F(MATER=(mat,), TOUT="OUI"))
            else:
                KW_Mat_Deg.append(_F(MATER=(mat,), GROUP_MA=mat_zone[mat]))

        # Etape 2 : Dégradation dans la zone SRM
        for mat in list(dict_zone_deg.keys()):
            if CPT_SRM not in mat.getMaterialNames():
                UTMESS("F", "CALCSTABPENTE_10")

            Matdeg = gene_deg_mat(mat, CPT_SRM, fact)
            KW_Mat_Deg.append(_F(MATER=(Matdeg,), GROUP_MA=dict_zone_deg[mat]))

    else:
        raise TypeError("At least {0} or {1} is required".format("TOUT", "GROUP_MA"))

    return KW_Mat_Deg


def gene_deg_mat(OriginMat, cpt, fact):
    """Generate the Material object with the degraded material behaviour parameters.

    Args:
        OriginMat (Material object): Undegraded materiau.
        cpt (str): Material behaviour used in the SRM algorithm.
        fact (float): Strength reduction factor.

    Returns:
        Material object: Degraded material object.
    """

    Matdeg = Material(OriginMat, [cpt])

    propval = {}
    if cpt == "MOHR_COULOMB":
        Phi_0 = OriginMat.getValueReal(cpt, "PHI")
        Psi_0 = OriginMat.getValueReal(cpt, "ANGDIL")
        if Phi_0 != Psi_0:
            UTMESS("A", "CALCSTABPENTE_11")
        Phi_deg = np.arctan(np.tan(Phi_0 / 180 * np.pi) / fact) * 180 / np.pi
        propval["ANGDIL"] = Phi_deg
        propval["COHESION"] = OriginMat.getValueReal(cpt, "COHESION") / fact
        propval["PHI"] = Phi_deg

    elif cpt == "DRUCK_PRAGER":
        # Réduction c-phi
        A = OriginMat.getValueReal(cpt, "ALPHA")
        SY = OriginMat.getValueReal(cpt, "SY")
        PSI = OriginMat.getValueReal(cpt, "DILAT")
        propval["P_ULTM"] = OriginMat.getValueReal(cpt, "P_ULTM")
        num_ecroui = OriginMat.getValueReal(cpt, "TYPE_DP")
        if num_ecroui == 1.0:
            ECROUI = "LINEAIRE"
            propval["H"] = OriginMat.getValueReal(cpt, "H")
        elif num_ecroui == 2.0:
            ECROUI = "PARABOLIQUE"
            propval["SY_UTLM"] = OriginMat.getValueReal(cpt, "SY_UTLM")
        propval["ECROUISSAGE"] = ECROUI

        tan_phi_deg = 3 * A / (2 * np.sqrt((2 * A + 1) * (1 - A))) / fact
        c_deg = SY / (2 * np.sqrt((2 * A + 1) * (1 - A))) / fact
        psi_deg = np.arctan(np.tan(PSI / 180 * np.pi) / fact) * 180 / np.pi

        sin = tan_phi_deg / np.sqrt(1 + tan_phi_deg**2)
        cos = 1.0 / np.sqrt(1 + tan_phi_deg**2)

        propval["ALPHA"] = 2 * sin / (3 - sin)
        propval["SY"] = 6 * c_deg * cos / (3 - sin)
        propval["DILAT"] = psi_deg

    Matdeg.addProperties(cpt, **propval)

    return Matdeg


def get_para_mat(chmat):
    """Extract the mesh, materials and the associated group_mas from the input cham_mater.

    Args:
        chmat (MaterialField object): Input material field.

    Returns:
        dict: Dict containing the mesh and the material affectation parameters.
    """

    para_mat = {}
    para_mat["MAILLAGE"] = chmat.getMesh()
    para_mat["AFFE_MATER"] = {}

    # Récupérer les matériaux et les entités de maillage associées
    MatOnMeshEnt = chmat.getMaterialsOnMeshEntities()
    for curIter in MatOnMeshEnt:
        list_mat = curIter[0]
        if len(list_mat) > 1:
            UTMESS("F", "CALCSTABPENTE_12")

        meshEnt = curIter[1]
        if str(meshEnt.getType()) == "EntityType.GroupOfCellsType":
            para_mat["AFFE_MATER"][list_mat[0]] = meshEnt.getNames()
        else:
            para_mat["AFFE_MATER"][list_mat[0]] = "TOUT"

    return para_mat


def get_syntax_affevarc(chmat):
    """Extract the command variables from the input material field.

    Args:
        chmat (MaterialField object): Input material field.

    Returns:
        dict: Dict containing the factor keywords of 'AFFE_VARC'.
    """

    ExtVariAffe = chmat.getExtStateVariablesOnMeshEntities()
    List_Affe_ExtVari = []
    if len(ExtVariAffe) > 0:
        for curIter in ExtVariAffe:
            dict_extvari = {}
            # Reconstruction des syntaxes liées à l'objet ExternalStateVariable
            ExtVari = curIter[0]
            Nom_varc = ExternalVariableTraits.getExternVarTypeStr(ExtVari.getType())
            dict_extvari["NOM_VARC"] = Nom_varc

            inputField = ExtVari.getField()
            evolParam = ExtVari.getEvolutionParameter()

            if inputField:
                dict_extvari["CHAM_GD"] = inputField
            if evolParam:
                dict_extvari["EVOL"] = evolParam.getTransientResult()
                dict_extvari["PROL_GAUCHE"] = evolParam.getLeftExtension()
                dict_extvari["PROL_DROITE"] = evolParam.getRightExtension()
                if evolParam.getFieldName():
                    dict_extvari["NOM_CHAM"] = evolParam.getFieldName()
                if evolParam.getTimeFormula():
                    dict_extvari["FONC_INST"] = evolParam.getTimeFormula()
                if evolParam.getTimeFunction():
                    dict_extvari["FONC_INST"] = evolParam.getTimeFunction()
            if ExtVari.isSetRefe():
                dict_extvari["VALE_REF"] = ExtVari.getReferenceValue()

            # Reconstruction des syntaxes liées aux entités du maillage
            meshEnt = curIter[1]
            if str(meshEnt.getType()) == "EntityType.GroupOfCellsType":
                dict_extvari["GROUP_MA"] = meshEnt.getNames()
            else:
                dict_extvari["TOUT"] = "OUI"

            List_Affe_ExtVari.append(_F(dict_extvari))

    return List_Affe_ExtVari


def zone_gliss(X, Y, resu_stab):
    """Indicate if the given location belongs to the sliding mass or not.

    Args:
        X (float): Abscissa of the interested location.
        Y (float): Ordinate of the interested location.
        resu_stab (dict): Result dictionnary of the LEM calculation.

    Returns:
        float: one if the location belongs to the sliding mass and zero if not.
    """

    if resu_stab.get("RAYON") is not None:
        # Surface circulaire
        Rayon = resu_stab["RAYON"]
        x_center = resu_stab["CENTRE_X"]
        y_center = resu_stab["CENTRE_Y"]
        x_1 = resu_stab["X_ENTRE"]
        x_2 = resu_stab["X_SORTIE"]
        if Rayon**2 - (X - x_center) ** 2 - (Y - y_center) ** 2 >= 1e-6 and x_1 <= X <= x_2:
            return 1.0
        else:
            return 0.0

    else:
        # Surface non-circulaire
        coor_X = resu_stab["COOR_X"]
        coor_Y = resu_stab["COOR_Y"]
        for n in range(np.size(coor_X, 0) - 1):
            if X >= coor_X[n] and X < coor_X[n + 1]:
                k = (coor_Y[n + 1] - coor_Y[n]) / (coor_X[n + 1] - coor_X[n])
                b = coor_Y[n] - k * coor_X[n]
                if (Y - k * X - b) >= 1e-6:
                    return 1.0
                else:
                    return 0.0
        return 0.0


def outline_slice_circ(X, Y, x0, y0, x1, x2, R, N, sigma):
    """Calculate the indicator of the proximity to the slice outline for circular failure surface.

    Args:
        X (float): Abscissa of the input point.
        Y (float): Ordiante of the input point.
        x0 (float): Abscissa of the sliding circle centre.
        y0 (float): Ordinate of the sliding circle centre.
        x1 (float): Abscissa of the sliding circle endpoint 1.
        x2 (float): Abscissa of the sliding circle endpoint 2.
        R (float): Radius of the sliding circle.
        N (int): Number of slices.
        sigma (float): Standard deviation of gaussian distribution.

    Returns:
        float: Value of proximity indicator.
    """

    d_min = np.inf
    width = np.abs(x2 - x1) / N

    d_cerc = R - np.sqrt((X - x0) ** 2 + (Y - y0) ** 2)
    if d_cerc > 1e-8:
        # maille dans la partie glissante
        for n in range(N - 1):
            d_tran = np.abs(X - np.min([x1, x2]) - width * (n + 1))
            if d_tran < d_min:
                d_min = d_tran
        if d_cerc < d_min:
            d_min = d_cerc
    else:
        d_min = np.abs(d_cerc)

    return 1.0 / np.sqrt(2 * np.pi) / sigma * np.exp(-(d_min**2) / 2 / sigma**2)


def outline_slice_nc(X, Y, para_geom, N, sigma):
    """Calculate the indicator of the proximity to the slice outline for non-circular failure surface.

    Args:
        X (float): Abscissa of the input point.
        Y (float): Ordiante of the input point.
        para_geom (list[float]): Array containing the coordinates of the intermediate points of the failure surface.
        N (int): Number of slices.
        sigma (float): Standard deviation of gaussian distribution.

    Returns:
        float: Value of proximity indicator.
    """

    d_min = np.inf
    # si x_e < X < x_s, on calcule d_min, infini sinon
    for n in range(N):
        if X >= para_geom[n, 0] and X < para_geom[n + 1, 0]:
            d_tran_l = np.abs(X - para_geom[n, 0])
            d_tran_r = np.abs(X - para_geom[n + 1, 0])
            if n == 0:
                d_tran = d_tran_r
            elif n == N - 1:
                d_tran = d_tran_l
            else:
                d_tran = np.min([d_tran_l, d_tran_r])

            k = (para_geom[n + 1, 1] - para_geom[n, 1]) / (para_geom[n + 1, 0] - para_geom[n, 0])
            b = para_geom[n, 1] - k * (para_geom[n, 0])
            d_tran_base = (Y - k * X - b) / np.sqrt(k**2 + 1)
            if d_tran_base > 1e-8:
                d_min = np.min([d_tran, d_tran_base])
            else:
                d_min = np.abs(d_tran_base)

    return 1.0 / np.sqrt(2 * np.pi) / sigma * np.exp(-(d_min**2) / 2 / sigma**2)


class LEM_Solver:
    """Solver object containing the LEM-related methods."""

    def __init__(self, parent, args):
        self.parent = parent

        self.surf_circ = False
        self.bishop = False
        self.spencer = False

        if args["METHODE_LEM"] in ["BISHOP", "FELLENIUS"]:
            self.surf_circ = True
            if args["METHODE_LEM"] == "BISHOP":
                self.bishop = True
        else:
            if args["METHODE_LEM"] == "SPENCER":
                self.spencer = True

        self.cham_defo = args.get("CHAM_DEFO")

        self.chmat = args["CHAM_MATER"]
        para_mat = get_para_mat(self.chmat)
        self.affe_mat = para_mat["AFFE_MATER"]
        self.mesh = self.chmat.getMesh()
        self.connex = self.mesh.getMedConnectivity()

        x1_min = args["X1_MINI"]
        x1_max = args["X1_MAXI"]
        x2_min = args["X2_MINI"]
        x2_max = args["X2_MAXI"]

        # Vérifier la légitimité des x1 et x2
        if x1_min > x1_max or x2_min > x2_max or x1_max > x2_min:
            UTMESS("F", "CALCSTABPENTE_14")

        self.x_lim_1 = [x1_min, x1_max]
        self.x_lim_2 = [x2_min, x2_max]

        # General parameters
        self.nb_tran = args["NB_TRANCHE"]
        mc_raff_mail = args["RAFF_MAIL"]
        self.nb_max_adap = mc_raff_mail["NB_RAFF_MAXI"]
        self.resi_FS = mc_raff_mail["RAFF_CRIT_STAB"]
        self.cpt = args["CRITERE"]
        self.phi_c_equi = args.get("PHI_C_EQUI") == "OUI"
        self.tole_dist = args.get("TOLE_DIST")

        # Get slope info from input mesh
        self.grma_pente = args["GROUP_MA"]
        self.analyse_mesh()
        ## verify settings
        if x1_min < np.min(self.pente[:, 0]) or x2_max > np.max(self.pente[:, 0]):
            UTMESS("F", "CALCSTABPENTE_16")

        # Quel côté du barrage s'agit-il ?
        y1 = np.interp(x1_min, self.pente[:, 0], self.pente[:, 1])
        y2 = np.interp(x2_max, self.pente[:, 0], self.pente[:, 1])
        self.is_upstream = True if y1 < y2 else False

        # Get hydrostatic pressure if provided
        self.f_pres = args.get("FONC_PRES")
        if self.f_pres is not None:
            self.calc_pres_nodal()

        # Get acceleration coefficient if provided
        self.kv = 0.0
        self.kh = 0.0
        self.calc_kc = False
        if args.get("ACCE") is not None:
            acce_para = args["ACCE"]
            self.calc_kc = acce_para.get("CALC_KC") == "OUI"
            if not self.calc_kc:
                ka = acce_para["COEF_ACCE"]
                dir = np.array(acce_para["DIRECTION"], dtype=np.float64)
                if np.max(np.abs(dir)) < 1e-6:
                    UTMESS("F", "CALCSTABPENTE_22")
                dir /= np.linalg.norm(dir)
                self.kh, self.kv = dir * ka

        # Define the pore-pressure field
        self.ptot_type = None
        for ptype in ["LIGN_PHREA", "COEF_RU", "CHAM_PRES"]:
            if args.get(ptype) is not None:
                self.ptot_type = ptype
                pore_pres_para = args[ptype]
                break

        if self.ptot_type == "LIGN_PHREA":
            self.piezo = self.get_field_map(pore_pres_para, lign_phrea=True)
        elif self.ptot_type == "COEF_RU":
            self.ru = self.get_field_map(pore_pres_para)
        elif self.ptot_type == "CHAM_PRES":
            self.use_idw = pore_pres_para["ALGO_PRES"] == "INVERSE"
            self.mod_pres = pore_pres_para["RESULTAT"].getModel()

            # pressure field extraction
            __chpres = CREA_CHAMP(
                TYPE_CHAM="NOEU_DEPL_R",
                OPERATION="EXTR",
                NOM_CHAM="DEPL",
                **{
                    key: pore_pres_para[key]
                    for key in ["RESULTAT", "NUME_ORDRE", "INST", "PRECISION"]
                    if pore_pres_para.get(key) is not None
                },
            )
            __mod_2 = AFFE_MODELE(
                AFFE=_F(MODELISATION=("D_PLAN",), PHENOMENE="MECANIQUE", TOUT="OUI"),
                MAILLAGE=self.mesh,
            )
            self.chpres = PROJ_CHAMP(
                METHODE="COLLOCATION", MODELE_1=self.mod_pres, MODELE_2=__mod_2, CHAM_GD=__chpres
            )

            ## check model --> THM
            cmps = self.chpres.getComponents()
            if "PRE1" not in cmps:
                UTMESS("F", "CALCSTABPENTE_23")

            # saturé ou non-saturé ?
            ncmp = len(cmps)
            self.is_satu = ncmp == 1

            if self.use_idw:
                # case 1: IDW interpolation
                self.chpresval = np.array(self.chpres.getValues()).reshape((-1, ncmp))
            else:
                # case 2: PROJ_CHAMP
                self.gene_mesh_poi()

            del __chpres, __mod_2

        ## get unsaturated zone settings
        self.has_suction = args.get("SUCCION") == "OUI"
        self.phi_b = {}
        if args.get("PHI_B") is not None:
            self.phi_b = self.get_field_map(args["PHI_B"])

    def analyse_mesh(self):
        """Get slope information from the input mesh."""

        coord = self.mesh.getCoordinates().getValues()
        coord = np.array(coord).reshape((-1, 3))
        meshtypes = self.mesh.getMedCellsTypes()
        nno_pente = self.mesh.getNodesFromCells(self.grma_pente, False)

        center = np.zeros((len(self.connex), 2))
        size_p = []
        coor_p = []
        min_cell_size = np.inf
        rec_nno_p = []
        for ncell in range(len(self.connex)):
            if meshtypes[ncell] // 100 == 1:
                # éliminer les éléments SEG où le matériau n'est pas défini
                center[ncell, :] = [np.inf, np.inf]
                continue
            x = 0.0
            y = 0.0
            for nnode in self.connex[ncell]:
                x += coord[nnode, 0]
                y += coord[nnode, 1]

            center[ncell, :] = np.array([x, y]) / len(self.connex[ncell])

            size = np.linalg.norm(
                np.max(coord[self.connex[ncell], :], axis=0)
                - np.min(coord[self.connex[ncell], :], axis=0)
            )
            if size < min_cell_size:
                min_cell_size = size

            size_y = np.max(coord[self.connex[ncell], 1]) - np.min(coord[self.connex[ncell], 1])
            for nnode in self.connex[ncell]:
                if nnode in nno_pente and nnode not in rec_nno_p:
                    coor_p.append(coord[nnode, :2])
                    size_p.append(size_y)
                    rec_nno_p.append(nnode)

        coor_p = np.array(coor_p, dtype=np.float64)
        size_p = np.array(size_p, dtype=np.float64)

        # Coordonnées des neouds sur la pente
        indsort = np.lexsort((-coor_p[:, 1], coor_p[:, 0]))
        coor_p = coor_p[indsort, :]
        size_p = size_p[indsort]

        ## Tau de pente et sa variation --> identifier les neouds convexs
        l_nno_cvex = []
        l_k = []
        l_dk = []
        for nno in range(coor_p.shape[0] - 1):
            dx = coor_p[nno + 1, 0] - coor_p[nno, 0]
            dy = coor_p[nno + 1, 1] - coor_p[nno, 1]
            k = None if np.abs(dx) < 1e-6 else dy / dx
            l_k.append(k)
            if nno == 0:
                continue
            if l_k[-2] is None and l_k[-1] is not None:
                l_nno_cvex.append(nno)
            if None not in l_k[-2:]:
                dk = l_k[-1] - l_k[-2]
                l_dk.append(dk)
                if dk > 1e-6:
                    l_nno_cvex.append(nno)
            else:
                l_dk.append(None)

        self.coord = coord
        self.pente = coor_p
        self.size_p = size_p
        self.k = l_k
        self.dk = l_dk
        self.nno_cvex = l_nno_cvex
        self.y_bas = np.min(coord[:, 1])
        self.min_cell_size = min_cell_size
        self.centre = center

        return

    def get_field_map(self, l_mc_fact, lign_phrea=False):
        """Mapping the zone-dependant properties to the related set of cells.

        Args:
            l_mc_fact (list[dict]): List of factor keywords.
            lign_phrea (bool, optional): Indicate if the mapped property is phreatic line. Defaults to False.

        Returns:
            dict: Mapping dictionary.
        """

        if isinstance(l_mc_fact, dict):
            l_mc_fact = [l_mc_fact]

        fd_map = {}
        n_occ = 0
        for para in l_mc_fact:
            if para.get("TOUT") == "OUI":
                l_ncells = np.arange(self.mesh.getNumberOfCells())
            else:
                l_grmas = para.get("GROUP_MA")
                l_ncells = []
                for grma in l_grmas:
                    l_ncells += [
                        ncell for ncell in self.mesh.getCells(grma) if ncell not in l_ncells
                    ]

            if not lign_phrea:
                fd_map.update({para["VALE"]: l_ncells})
                continue

            tab_piezo = para["TABLE"].EXTR_TABLE().values()
            heads = list(tab_piezo.keys())
            f_piezo = np.array([tab_piezo[heads[ind - 1]] for ind in para["INDIC_PIEZO"]]).T
            f_angle = np.zeros((f_piezo.shape[0] - 1, 2))
            for ind in range(f_piezo.shape[0] - 1):
                x_1 = f_piezo[ind, 0]
                x_2 = f_piezo[ind + 1, 0]
                dh = f_piezo[ind + 1, 1] - f_piezo[ind, 1]
                f_angle[ind, 0] = f_piezo[ind, 0]
                if abs(x_1 - x_2) < 1e-6:
                    f_angle[ind, 1] = np.pi / 2 * np.sign(dh)
                else:
                    f_angle[ind, 1] = np.arctan(dh / (x_2 - x_1))

            d_piezo = {"piezo": f_piezo, "angle": f_angle, "p_max": para.get("PRES_MAX", np.inf)}
            fd_map.update({n_occ: {"cells": l_ncells, "d_piezo": d_piezo}})
            n_occ += 1

        return fd_map

    def calc_pres_nodal(self):
        """Calculate the nodal pressure field on the slope surface."""

        __MAIL = DEFI_GROUP(
            MAILLAGE=self.mesh, CREA_GROUP_NO=_F(NOM="PENTE_NO", GROUP_MA=self.grma_pente)
        )
        __CHNORM = CREA_CHAMP(
            TYPE_CHAM="NOEU_GEOM_R",
            OPERATION="NORMALE",
            MODELE=AFFE_MODELE(
                MAILLAGE=__MAIL, AFFE=_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="D_PLAN")
            ),
            GROUP_MA=self.grma_pente,
        )
        __CHNORMD = CREA_CHAMP(
            TYPE_CHAM="NOEU_DEPL_R",
            OPERATION="ASSE",
            MAILLAGE=__MAIL,
            ASSE=_F(
                GROUP_MA=self.grma_pente,
                CHAM_GD=__CHNORM,
                NOM_CMP=("X", "Y"),
                NOM_CMP_RESU=("DX", "DY"),
            ),
        )
        __CHGEOM = CREA_CHAMP(
            TYPE_CHAM="NOEU_GEOM_R", OPERATION="EXTR", NOM_CHAM="GEOMETRIE", MAILLAGE=__MAIL
        )
        __CHPRESF = CREA_CHAMP(
            TYPE_CHAM="NOEU_NEUT_F",
            OPERATION="AFFE",
            MAILLAGE=__MAIL,
            AFFE=_F(
                GROUP_MA=self.grma_pente,
                NOM_CMP=("X1", "X2"),
                VALE_F=(
                    FORMULE(VALE="- f_p(Y) * DX", NOM_PARA=("DX", "Y"), f_p=self.f_pres),
                    FORMULE(VALE="- f_p(Y) * DY", NOM_PARA=("DY", "Y"), f_p=self.f_pres),
                ),
            ),
        )
        __CHPRES = CREA_CHAMP(
            TYPE_CHAM="NOEU_NEUT_R",
            OPERATION="EVAL",
            CHAM_F=__CHPRESF,
            CHAM_PARA=(__CHGEOM, __CHNORMD),
        )
        __TABPRES = POST_RELEVE_T(
            ACTION=_F(
                INTITULE="PRES",
                OPERATION="EXTRACTION",
                GROUP_NO="PENTE_NO",
                CHAM_GD=__CHPRES,
                TOUT_CMP="OUI",
            )
        )

        tabpres = __TABPRES.EXTR_TABLE().values()
        ext_pres = np.array([tabpres[nom_para] for nom_para in ["COOR_X", "COOR_Y", "X1", "X2"]]).T
        self.ext_pres = ext_pres[np.argsort(ext_pres[:, 0])]

        del __MAIL, __CHNORM, __CHNORMD, __CHGEOM, __CHPRESF, __CHPRES, __TABPRES

        return

    def get_properties_on_surface(self, para_geom, is_circ=True):
        """Get the material properties and pore pressure on the failure surface.

        Args:
            para_geom (dict): Dict containing geometry parameters of slip surface.
            is_circ (bool): Circular surface indicator.

        Returns:
            list[float], list[float]: Material properties array (nb_tran, 3) and pore pressure array (nb_tran, 2).
        """

        def get_phi_c(mater):
            # get phi (rad) and c values
            if self.cpt == "MOHR_COULOMB":
                phi = mater.getValueReal("MOHR_COULOMB", "PHI") * np.pi / 180.0
                c = mater.getValueReal("MOHR_COULOMB", "COHESION")
            else:
                A = mater.getValueReal("DRUCK_PRAGER", "ALPHA")
                SY = mater.getValueReal("DRUCK_PRAGER", "SY")
                phi = np.arctan(3 * A / (2 * np.sqrt((2 * A + 1) * (1 - A))))
                c = SY / (2 * np.sqrt((2 * A + 1) * (1 - A)))
            return [phi, c]

        def get_mat(x, demi_w):
            # get material at coordiante x
            dist_min = np.inf
            for ncell in range(np.size(self.centre, 0)):
                x_c, y_c = self.centre[ncell, :]
                if abs(x_c - x[0]) > demi_w:
                    continue
                if abs(y_c - x[1]) > demi_w:
                    continue
                dist = np.linalg.norm(x - self.centre[ncell, :])
                if dist < dist_min:
                    dist_min = dist
                    ncell_base = ncell

            mat_c = self.chmat.getMaterialOnCell(ncell_base)
            if mat_c is None:
                UTMESS("F", "CALCSTABPENTE_24", vali=ncell_base + 1)
            return mat_c

        def check_mat(coor1, coor2, dmin, demi_w):
            # get interlayer coordiantes and the associated materials with TOLE_DIST = dmin
            m1 = get_mat(coor1, demi_w)
            m2 = get_mat(coor2, demi_w)
            if m1 == m2:
                return []

            if np.linalg.norm(coor1 - coor2) <= dmin:
                return [(coor2, m2)]

            mat_interm = []
            coorm = (coor1 + coor2) / 2
            mat_interm += check_mat(coor1, coorm, dmin, demi_w)
            mat_interm += check_mat(coorm, coor2, dmin, demi_w)

            return mat_interm

        def get_mat_equi(ntran, coor):
            # Calculate equivalent phi-c at the base of ntran
            coor1, coor2 = coor[ntran, :], coor[ntran + 1, :]
            demi_w = coor[ntran + 1, 0] - coor[ntran, 0]
            dmin = np.linalg.norm(coor1 - coor2) / 20.0
            mat_interm = check_mat(coor[ntran, :], coor[ntran + 1, :], dmin, demi_w)
            mat = get_mat(coor1, demi_w)
            prop = np.array(get_phi_c(mat))

            if len(mat_interm):
                prop[0] = np.tan(prop[0])
                prop *= np.linalg.norm(mat_interm[0][0] - coor1)

                for ind, tup in enumerate(mat_interm):
                    coor, m = tup
                    coorn = coor2 if ind == len(mat_interm) - 1 else mat_interm[ind + 1][0]
                    phi, c = get_phi_c(m)
                    prop += np.array([np.tan(phi), c]) * np.linalg.norm(coorn - coor)

                prop /= np.linalg.norm(coor1 - coor2)
                prop[0] = np.arctan(prop[0])

            return prop

        def idw_interp(ncell):
            # Inverse Distance Weighted Interpolation
            l_nodes = self.connex[ncell][:]
            inv_dist_tot = 0.0
            p = 2
            res = np.zeros((self.chpresval.shape[1]))
            for nnode in l_nodes:
                dist = np.linalg.norm(c_base[ntran, :] - self.coord[nnode, :2])
                if dist < 1e-10:
                    res = self.chpresval[nnode, :]
                    inv_dist_tot = 0.0
                    break
                res += (1.0 / dist) ** p * self.chpresval[nnode, :]
                inv_dist_tot += (1.0 / dist) ** p

            if inv_dist_tot > 0:
                res /= inv_dist_tot
            return res

        # Calculate slice base centers
        c_base = np.zeros((self.nb_tran, 2))
        coor = para_geom["coor"]
        if is_circ:
            centre = np.array(para_geom["centre"])
            vec = coor - centre
            l_tta = np.angle(vec[:, 0] + vec[:, 1] * 1.0j)  # angle dans le repère cylindrique
            l_tta = np.where(l_tta < np.pi / 2, l_tta, l_tta - 2 * np.pi)
            for ntran in range(self.nb_tran):
                tta_c = (l_tta[ntran] + l_tta[ntran + 1]) / 2
                c_base[ntran, :] = (
                    para_geom["R"] * np.array([np.cos(tta_c), np.sin(tta_c)]) + centre
                )

        else:
            for ntran in range(self.nb_tran):
                c_base[ntran, :] = (coor[ntran, :] + coor[ntran + 1, :]) / 2

        mat_prop = np.zeros((self.nb_tran, 3))  # phi, c, phi_b
        ptot = np.zeros((self.nb_tran, 2))  # p_air, p_capillaire

        for ntran in range(np.size(c_base, 0)):
            dist_min = np.inf
            for ncell in range(np.size(self.centre, 0)):
                no_c = self.centre[ncell, :]
                if no_c[0] < coor[ntran, 0] or no_c[0] > coor[ntran + 1, 0]:
                    continue
                dist = np.linalg.norm(c_base[ntran, :] - self.centre[ncell, :])
                if dist < dist_min:
                    dist_min = dist
                    ncell_base = ncell

            # Material property at the base center
            mat_tran = get_mat(c_base[ntran, :], (coor[ntran + 1, 0] - coor[ntran, 0]) / 2)

            # Vérifier que le comportement existe dans le matériau
            if mat_tran is None:
                UTMESS("F", "CALCSTABPENTE_24", vali=ncell_base + 1)
            nom_mats = mat_tran.getMaterialNames()
            if self.cpt not in nom_mats:
                UTMESS("F", "CALCSTABPENTE_10")

            # Récupération des propriétés de résistance
            mat_prop[ntran, :2] = (
                get_mat_equi(ntran, coor) if self.phi_c_equi else get_phi_c(mat_tran)
            )

            # Pression interstitielle à la base de la tranche
            if self.ptot_type == "LIGN_PHREA":
                p_w = 0.0
                for piezo_info in self.piezo.values():
                    if ncell_base in piezo_info["cells"]:
                        piezo, angle, p_max = piezo_info["d_piezo"].values()
                        h_hydro = (
                            np.interp(c_base[ntran, 0], piezo[:, 0], piezo[:, 1]) - c_base[ntran, 1]
                        )
                        ang = np.interp(c_base[ntran, 0], angle[:, 0], angle[:, 1])
                        p_w = h_hydro * 1e3 * 9.81 * np.cos(ang) ** 2
                        ptot[ntran, 1] = min([ptot[ntran, 0] - p_w, p_max])  # pression capillaire
            elif self.ptot_type == "COEF_RU":
                # abuse de langage, ptot ici représente r_u
                ru = 0.0
                for val, l_ncells in self.ru.items():
                    if ncell_base in l_ncells:
                        ru = val
                ptot[ntran, 1] = -ru
            elif self.ptot_type == "CHAM_PRES":
                # Evaluation of field value on centre_base
                if not self.use_idw and ntran == 0:
                    ptot = self.interp_pres(c_base)
                elif self.use_idw:
                    pres = idw_interp(ncell_base)
                    if self.is_satu:
                        ptot[ntran, 1] = -pres
                    else:
                        ptot[ntran, :] = pres[[1, 0]]

            # Suction Strength
            if ptot[ntran, 1] <= 0.0:
                # saturated zone
                mat_prop[ntran, 2] = mat_prop[ntran, 0]
            elif self.has_suction:
                # unsaturated zone
                ## calculate phi_b
                if self.phi_b:
                    # suction strength calculated by user-input constant phi_b
                    found = False
                    for val, l_ncells in self.phi_b.items():
                        if ncell_base in l_ncells:
                            mat_prop[ntran, 2] = val * np.pi / 180.0
                            found = True
                    if not found:
                        UTMESS("F", "CALCSTABPENTE_25", vali=ncell_base + 1)
                else:
                    if "THM_DIFFU" not in nom_mats:
                        UTMESS("F", "CALCSTABPENTE_26")

                    try:
                        # evaluate effective water content by SATU_PRES fonction
                        f_vwc = mat_tran.getFunction("THM_DIFFU", "SATU_PRES")
                        sat_liqu = f_vwc.Ordo()
                        pcap = f_vwc.Absc()
                        s_sat = max(sat_liqu)
                        s_res = min(sat_liqu)
                        s_w = np.interp(np.log10(ptot[ntran, 1]), np.log10(pcap), sat_liqu)
                        s_effe = (s_w - s_res) / (s_sat - s_res)
                    except:
                        # evaluate effective water content by Van-Genuchten Model
                        vg_n = mat_tran.getValueReal("THM_DIFFU", "VG_N")
                        vg_pr = mat_tran.getValueReal("THM_DIFFU", "VG_PR")
                        s_effe = 1.0 / (1.0 + (ptot[ntran, 1] / vg_pr) ** vg_n) ** (
                            1.0 - 1.0 / vg_n
                        )

                    # equivalent phi_b
                    phi_eq = np.arctan(s_effe * np.tan(mat_prop[ntran, 0]))
                    mat_prop[ntran, 2] = phi_eq

        return mat_prop, ptot

    def calc_poids_tranche(self, mesh, centre_base, width_tran):
        """Calculate the deadweight of the soil slices.

        Args:
            mesh (Mesh object): Input mesh.
            centre_base (list[float]): Array of dimension (nb_tran, 2) containing the coordiantes of the centre of slices' base.
            width_tran (float): Uniform width of the slices.

        Returns:
            list[float]: Array containing the deadweight of the soil slices.
        """

        poids = np.zeros(self.nb_tran)
        barycent = np.zeros((self.nb_tran, 2))

        # Générer un maillage réduit contenant la masse glissante seule
        kw_affe_mat = []
        kw_crea_grma = []
        l_grma_mat = []
        l_grma_auxi = []
        imat = 0
        for mat, l_grma in self.affe_mat.items():
            if l_grma == "TOUT":
                kw_affe_mat.append(_F(MATER=mat, TOUT="OUI"))
            else:
                l_cemat = []
                for grma in l_grma:
                    l_cemat.extend(mesh.getCells(grma))
                l_ceglis = mesh.getCells("GLISS")
                l_cecom = list(set(l_cemat) & set(l_ceglis))
                if len(l_cecom) > 0:
                    nom_grma = "_".join(["gliss", "mat" + str(imat)])
                    if len(l_grma) > 1:
                        kw_crea_grma.extend(
                            [
                                _F(UNION=l_grma, NOM=nom_grma + "_U"),
                                _F(INTERSEC=("GLISS", nom_grma + "_U"), NOM=nom_grma),
                            ]
                        )
                        l_grma_auxi.append(nom_grma + "_U")
                    else:
                        kw_crea_grma.append(_F(INTERSEC=("GLISS", l_grma[0]), NOM=nom_grma))
                    kw_affe_mat.append(_F(MATER=mat, GROUP_MA=nom_grma))
                    l_grma_mat.append(nom_grma)
            imat += 1

        if len(kw_crea_grma) > 0:
            mesh = DEFI_GROUP(reuse=mesh, MAILLAGE=mesh, CREA_GROUP_MA=kw_crea_grma)
        __MA_RED = CREA_MAILLAGE(MAILLAGE=mesh, RESTREINT=_F(GROUP_MA=["GLISS"] + l_grma_mat))
        __CHMRED = AFFE_MATERIAU(AFFE=kw_affe_mat, MAILLAGE=__MA_RED)

        __MODRED = AFFE_MODELE(
            AFFE=_F(MODELISATION=("D_PLAN",), PHENOMENE="MECANIQUE", TOUT="OUI"), MAILLAGE=__MA_RED
        )

        # Création des grmas des tranches
        nom_tran = ["TRAN_" + str(ntran) for ntran in range(self.nb_tran)]
        nom_grma_del = []
        kw_crea_grma = []
        for ntran in range(self.nb_tran):
            nom_grma_del += [nom_tran[ntran]]
            if ntran == 0:
                kw_crea_grma += [
                    _F(
                        ANGL_NAUT=(0.0,),
                        DIST=width_tran / 2,
                        NOM=nom_tran[ntran],
                        OPTION="BANDE",
                        POINT=centre_base[ntran, :],
                    )
                ]
            else:
                kw_crea_grma += [
                    _F(
                        ANGL_NAUT=(0.0,),
                        DIST=width_tran / 2,
                        NOM=nom_tran[ntran] + "_inter",
                        OPTION="BANDE",
                        POINT=centre_base[ntran, :],
                    ),
                    _F(
                        DIFFE=(nom_tran[ntran] + "_inter", nom_tran[ntran - 1]), NOM=nom_tran[ntran]
                    ),
                ]

                nom_grma_del.append(nom_tran[ntran] + "_inter")

        __MA_RED = DEFI_GROUP(reuse=__MA_RED, MAILLAGE=__MA_RED, CREA_GROUP_MA=kw_crea_grma)

        # Calcul poids propre
        for ntran in range(self.nb_tran):
            __TABM = POST_ELEM(
                CHAM_MATER=__CHMRED, MODELE=__MODRED, MASS_INER=_F(GROUP_MA=(nom_tran[ntran],))
            )

            poids[ntran] = __TABM["MASSE", 1] * 9.81
            barycent[ntran, :] = np.array([__TABM[key, 1] for key in ["CDG_X", "CDG_Y"]])

        if len(l_grma_mat) > 0:
            mesh = DEFI_GROUP(
                DETR_GROUP_MA=_F(NOM=l_grma_mat + l_grma_auxi), MAILLAGE=mesh, reuse=mesh
            )

        del __MODRED, __CHMRED, __TABM, __MA_RED

        return poids, barycent

    def calc_char_ext(self, x_e, x_s, centre: List) -> Dict:
        """Calculate the external loadings resulted from hydrostatic pressure

        Args:
            x_e (float): Abscissa of the left end of slip surface.
            x_s (float): Abscissa of the right end of slip surface.
            centre (List): Coordiante of the point about which the moment is calculated.

        Returns:
            Dict: Dictionary containing the force and moment results.
        """

        def interp_f_pres(x):
            l_pres = [x]
            l_pres += [
                np.interp(x, self.ext_pres[:, 0], self.ext_pres[:, ind]) for ind in range(1, 4)
            ]
            return l_pres

        moment = 0.0  # moment de résistance, anticlockwise as positive
        l_x1 = np.linspace(x_e, x_s, self.nb_tran + 1)
        char_ext = {}

        if self.f_pres is not None:
            # rearrange the nodal pressure according to slices
            fp_slice = [[] for i in range(self.nb_tran)]
            ind_s = 0
            fp_slice[0].append(interp_f_pres(x_e))
            for p_data in self.ext_pres:
                if p_data[0] < l_x1[0]:
                    continue
                if p_data[0] > l_x1[-1]:
                    fp_slice[-1].append(interp_f_pres(x_s))
                    break

                if p_data[0] > l_x1[ind_s + 1]:
                    for sub_is in [ind_s, ind_s + 1]:
                        fp_slice[sub_is].append(interp_f_pres(l_x1[ind_s + 1]))
                    ind_s += 1

                fp_slice[ind_s].append(p_data.tolist())

            # pressure force and moment integration
            pres_v = np.zeros((self.nb_tran, 2))
            centre = np.array(centre)
            for ind_s in range(self.nb_tran):
                p_slice = np.array(fp_slice[ind_s])
                l_pente = np.zeros(p_slice.shape[0])
                for ipos in range(1, p_slice.shape[0]):
                    l_pente[ipos] = (
                        np.linalg.norm(p_slice[ipos, :2] - p_slice[ipos - 1, :2])
                        + l_pente[ipos - 1]
                    )
                # calcul de la force de pression
                pres_v[ind_s, :] = np.trapezoid(p_slice[:, 2:], l_pente, axis=0)
                # calcul du moment de pression
                coor_c = centre if len(centre.shape) == 1 else centre[ind_s, :]
                vec_c = p_slice[:, :2] - coor_c
                moment += np.trapezoid(np.cross(vec_c, p_slice[:, 2:]), l_pente)

            char_ext.update(
                {
                    "pres": {
                        "module": np.linalg.norm(pres_v, axis=1),
                        "angle": np.angle(pres_v[:, 0] + pres_v[:, 1] * 1.0j)
                        + np.pi / 2,  # tau de pente moyen dans le repère global
                    }
                }
            )

        char_ext["moment"] = moment

        return char_ext

    def crea_champ_pilo(self, para_geom, sigma, mesh):
        """Create the field of proximity to which the mesh will be adapted.

        Args:
            para_geom (list[float]): Geometric parameters of the failure surface.
            sigma (float): Standard deviation of gaussien distribution.
            mesh (Mesh object): Input mesh.

        Returns:
            cham_no object: Field of proximity.
        """

        if self.surf_circ:
            x_e = para_geom["X_ENTER"]
            x_s = para_geom["X_SORTI"]
            R = para_geom["RAYON"]
            x_centre, y_centre = self.solve_circle(x_e, x_s, R)
            __FOUTL = FORMULE(
                NOM_PARA=("X", "Y"),
                VALE="outline_slice_circ(X, Y, x_centre, y_centre, x_e, x_s, R, nb_tran, sigma)",
                outline_slice_circ=outline_slice_circ,
                x_centre=x_centre,
                y_centre=y_centre,
                x_e=x_e,
                x_s=x_s,
                R=R,
                nb_tran=self.nb_tran,
                sigma=sigma,
            )
        else:
            __FOUTL = FORMULE(
                NOM_PARA=("X", "Y"),
                VALE="outline_slice_nc(X, Y, para_geom, nb_tran, sigma)",
                outline_slice_nc=outline_slice_nc,
                para_geom=para_geom,
                nb_tran=self.nb_tran,
                sigma=sigma,
            )

        __CHGEO = CREA_CHAMP(
            MAILLAGE=mesh, NOM_CHAM="GEOMETRIE", OPERATION="EXTR", TYPE_CHAM="NOEU_GEOM_R"
        )

        __CHFON = CREA_CHAMP(
            AFFE=_F(NOM_CMP=("X1"), TOUT="OUI", VALE_F=(__FOUTL)),
            MAILLAGE=mesh,
            OPERATION="AFFE",
            TYPE_CHAM="NOEU_NEUT_F",
        )

        __CHPILO = CREA_CHAMP(
            CHAM_F=__CHFON, CHAM_PARA=(__CHGEO,), OPERATION="EVAL", TYPE_CHAM="NOEU_NEUT_R"
        )

        return __CHPILO

    def raff_maillage(self, resu_stab, f_eval: Callable):
        """Refine the mesh around the outline the soil slices.

        Args:
            resu_stab (dict): Dictionnary containing the result of failure surface searching.

        Returns:
            list[float]: Array containing the FS corresponding to the refined meshes.
        """

        l_FS = []
        FS = resu_stab["FS"]
        resi = np.inf
        k_adap = 0
        l_nom_mailraf = [None for i in range(self.nb_max_adap + 1)]
        l_FS.append(FS)

        if self.surf_circ:
            x_enter_FS = resu_stab["X_ENTRE"]
            x_sorti_FS = resu_stab["X_SORTIE"]
            R_FS = resu_stab["RAYON"]
            para_geom = {"X_ENTER": x_enter_FS, "X_SORTI": x_sorti_FS, "RAYON": R_FS}
        else:
            coord_X = resu_stab["COOR_X"]
            coord_Y = resu_stab["COOR_Y"]
            x_enter_FS = coord_X[0]
            x_sorti_FS = coord_X[-1]
            para_geom = np.vstack((coord_X, coord_Y))
            para_geom = para_geom.transpose()
            # Retrouver l'état des variables optimal
            etat_opti = coord_Y.copy()
            etat_opti[0] = coord_X[0]
            etat_opti[-1] = coord_X[-1]

        sigma = 0.3 * np.abs(x_enter_FS - x_sorti_FS) / self.nb_tran

        MAILRAF = self.mesh

        while resi > self.resi_FS and k_adap < self.nb_max_adap:
            k_adap += 1
            l_nom_mailraf[k_adap] = "MAILRAF_" + str(k_adap)

            __CHPILO = self.crea_champ_pilo(para_geom, sigma, MAILRAF)

            # seuil_raff compte les mailles dont la somme de proximité = 68.2% (Très proches) --> Raffiner
            # seuil_dera compte les mailles dont la somme de proximite = 4.6% (Très loins) --> Déraffiner
            seuil_raff = 1.0 / np.sqrt(2 * np.pi) / sigma * np.exp(-0.5)
            seuil_dera = 1.0 / np.sqrt(2 * np.pi) / sigma * np.exp(-2.0)

            HOMARD_INFOS.new()
            MACR_ADAP_MAIL(
                ADAPTATION="RAFF_DERA",
                MAILLAGE_N=MAILRAF,
                MAILLAGE_NP1=CO(l_nom_mailraf[k_adap]),
                CHAM_GD=__CHPILO,
                CRIT_RAFF_ABS=float(format(seuil_raff, ".4f")),
                CRIT_DERA_ABS=float(format(seuil_dera, ".4f")),
            )
            HOMARD_INFOS.pop()
            del MAILRAF, __CHPILO

            MAILRAF = globals()[l_nom_mailraf[k_adap]]

            sigma /= 2

            if self.surf_circ:
                FS_raf = f_eval(x_enter_FS, x_sorti_FS, R_FS, MAILRAF=MAILRAF)
            else:
                FS_raf = f_eval(etat_opti, MAILRAF=MAILRAF)

            resi = np.abs(FS_raf - FS)
            FS = FS_raf
            l_FS.append(FS)

        if self.cham_defo is not None:
            self.regis_cham_defo(resu_stab, MAILRAF)

        del MAILRAF

        return l_FS

    def regis_cham_defo(self, resu_stab, mesh):
        """Output the field visualizing the failure surface.

        Args:
            resu_stab (list[float]): Array containing the result of failure surface searching.
            mesh (Mesh object): Input mesh.
        """

        __FGLISS = FORMULE(
            NOM_PARA=("X", "Y"),
            VALE="zone_gliss(X, Y, resu_stab)",
            zone_gliss=zone_gliss,
            resu_stab=resu_stab,
        )

        __CHGEO = CREA_CHAMP(
            MAILLAGE=mesh, NOM_CHAM="GEOMETRIE", OPERATION="EXTR", TYPE_CHAM="NOEU_GEOM_R"
        )

        __CHFONC = CREA_CHAMP(
            AFFE=_F(NOM_CMP=("X1"), TOUT="OUI", VALE_F=(__FGLISS)),
            MAILLAGE=mesh,
            OPERATION="AFFE",
            TYPE_CHAM="NOEU_NEUT_F",
        )

        __CHEVAL = CREA_CHAMP(
            CHAM_F=__CHFONC, CHAM_PARA=(__CHGEO,), OPERATION="EVAL", TYPE_CHAM="NOEU_NEUT_R"
        )

        __CHDEPL = CREA_CHAMP(
            ASSE=_F(CHAM_GD=__CHEVAL, NOM_CMP=("X1"), NOM_CMP_RESU=("DX"), TOUT="OUI"),
            MAILLAGE=mesh,
            OPERATION="ASSE",
            TYPE_CHAM="NOEU_DEPL_R",
        )

        __REDEPL = CREA_RESU(
            AFFE=(_F(NOM_CHAM="DEPL", CHAM_GD=__CHDEPL, INST=(0.0,)),),
            OPERATION="AFFE",
            TYPE_RESU="EVOL_NOLI",
        )

        self.parent.register_result(__REDEPL, self.cham_defo)

    def gene_mesh_poi(self):
        """Generate template mesh composed of 0D elements for pore-pressure interpolation"""

        cont = []
        cont += ["TITRE", "FINSF", "COOR_2D"]
        for nno in range(self.nb_tran):
            cont.append("N{:d} {:21.14E} {:21.14E}".format(nno + 1, nno, 0))

        cont.append("FINSF")
        for nno in range(self.nb_tran):
            cont += ["GROUP_NO", "N" + str(nno + 1), "N" + str(nno + 1), "FINSF"]

        cont.append("POI1")
        cont += ["P{0:d} N{0:d}".format(nno + 1) for nno in range(self.nb_tran)]
        cont.append("FINSF")
        cont.append("FIN")

        mesh_file = tempfile.NamedTemporaryFile()
        with open(mesh_file.name, "w") as f:
            f.write("\n".join(cont))

        __mesh_poi = Mesh()
        __mesh_poi.readAsterFile(mesh_file.name)
        mesh_file.close()
        self.mesh_poi = __mesh_poi
        return

    def interp_pres(self, coors):
        """Interpolate pore-pressure field by PROJ_CHAMP

        Args:
            coors (ndarray): 2D coordiantes of soil slice base centers

        Returns:
            ndarray: air pressure and capillary pressure
        """

        f_coor = self.mesh_poi.getCoordinates()
        for nno, xy in enumerate(coors):
            node = f_coor.getNode(nno)
            for idim in range(2):
                node[idim] += xy[idim] - node[idim]
            f_coor.setNode(node)

        __mod_poi = Model(self.mesh_poi)
        __mod_poi.addModelingOnMesh(Physics.Mechanics, Modelings.DIS_T_2D)
        __mod_poi.build()

        __ch_poi = PROJ_CHAMP(
            METHODE="COLLOCATION", MODELE_1=self.mod_pres, MODELE_2=__mod_poi, CHAM_GD=self.chpres
        )

        fieldval = np.array(__ch_poi.getValues()).reshape((self.nb_tran, -1))
        ptot_poi = np.zeros((self.nb_tran, 2))
        if fieldval.shape[1] == 1:
            # saturated model
            ptot_poi[:, 1] = -fieldval[0, :]
        else:
            # unsaturated model
            ptot_poi = fieldval[:, [1, 0]]

        del __mod_poi, __ch_poi

        return ptot_poi


class Surf_Circ_Solver(LEM_Solver):
    """Solver object containing the methods for circular failure surface searching and FS calculation."""

    def __init__(self, parent, args):
        super(Surf_Circ_Solver, self).__init__(parent, args)
        self.x_bande_1 = np.linspace(self.x_lim_1[0], self.x_lim_1[1], num=args["NB_POINT_1"])
        self.x_bande_2 = np.linspace(self.x_lim_2[0], self.x_lim_2[1], num=args["NB_POINT_2"])
        if self.x_lim_1[1] - self.x_lim_1[0] < 1e-6:
            self.x_bande_1 = [self.x_lim_1[0]]
        if self.x_lim_2[1] - self.x_lim_2[0] < 1e-6:
            self.x_bande_2 = [self.x_lim_2[0]]

        self.nb_r = args["NB_RAYON"]

        if args.get("Y_MINI") is not None or args.get("Y_MAXI") is not None:
            self.def_y_lim = True
        else:
            self.def_y_lim = False

        self.y_min = args.get("Y_MINI")
        self.y_max = args.get("Y_MAXI")
        if self.y_min is not None:
            # Vérification du y_min
            y1 = np.interp(self.x_lim_1[1], self.pente[:, 0], self.pente[:, 1])
            y2 = np.interp(self.x_lim_2[0], self.pente[:, 0], self.pente[:, 1])
            if self.y_min > np.min([y1, y2]):
                UTMESS("F", "CALCSTABPENTE_19")

        # niveau d'impression
        self.impr_detail = args.get("INFO_TABLE") == 2

    def check_circle(self, x_e, x_s, R):
        """Verify the kinematic acceptability of the slip surface.

        Args:
            x_e (float): Abscissa of the left end of slip surface.
            x_s (float): Abscissa of the right end of slip surface.
            R (float): Radius.

        Returns:
            int: return code. 0: valid, < 0: invalid.
        """

        x_centre, y_centre = self.solve_circle(x_e, x_s, R)

        for ind in range(np.size(self.pente, 0)):
            x_p = self.pente[ind, 0]
            y_p = self.pente[ind, 1]
            if x_p - x_e < 1e-6 or x_s - x_p < 1e-6:
                continue

            # assurer que la pente à l'intérieur du cercle et prendre une marge aux points aigus
            r_tol = R - self.min_cell_size if ind in self.nno_cvex else R
            if (x_p - x_centre) ** 2 + (y_p - y_centre) ** 2 - r_tol**2 >= 0.0:
                # surface critique au-dessus de la pente
                return -1

        # assurer que les points interm prennent la marge
        for x_i in np.linspace(x_e, x_s, self.nb_tran, endpoint=False)[1:]:
            y_p = np.interp(x_i, self.pente[:, 0], self.pente[:, 1])
            y_i = self.calc_y(x_i, [x_centre, y_centre], R)
            marge_y = 2 * self.size_p[np.where(self.pente[:, 0] <= x_i)[0][-1]]
            if y_p - y_i < marge_y:
                return -2

        if self.y_bas + R - y_centre > 1e-3:
            dx = np.sqrt(R**2 - (self.y_bas - y_centre) ** 2)
            if x_centre + dx - x_e > 1e-6 and x_s - x_centre + dx > 1e-6:
                # surface critique hors du modèle
                return -3

        return 0

    def solve_circle(self, x_e, x_s, R=None, yb=None, xb=None):
        """Calculate the centre coordinates of a circle.

        Args:
            x_e (float): Abscissa of the enter point.
            x_s (float): Abscissa of the exit point .
            R (float, optional): Radius of the circle. Defaults to None.
            yb (float, optional): Ordinate of the horizontal tangential line. Defaults to None.
            xb (float, optional): Abscissa of vertical tangential line. Defaults to None.

        Returns:
            float, float: Coordinates of the circle centre.
        """

        x1 = x_e
        x2 = x_s
        y1 = np.interp(x_e, self.pente[:, 0], self.pente[:, 1])
        y2 = np.interp(x_s, self.pente[:, 0], self.pente[:, 1])

        # x0 = c1 - c2y0
        c1 = (x2**2 - x1**2 + y2**2 - y1**2) / 2 / (x2 - x1)
        c2 = (y2 - y1) / (x2 - x1)

        # Ay0^2 + By0 + C = 0
        if R is not None:
            A = c2**2 + 1
            B = 2 * (x1 - c1) * c2 - 2 * y1
            C = (x1 - c1) ** 2 + y1**2 - R**2

        elif yb is not None:
            A = c2**2
            B = 2 * (x1 - c1) * c2 - 2 * y1 + 2 * yb
            C = (x1 - c1) ** 2 + y1**2 - yb**2
            delta = B**2 - 4 * A * C

        else:
            A = 1.0
            B = 2 * (x1 * c2 - y1 - c2 * xb)
            C = (x1 - c1) ** 2 + y1**2 - (xb - c1) ** 2

        delta = B**2 - 4 * A * C
        if np.abs(delta) < 1e-6:
            delta = 0.0
        else:
            if delta < 0.0:
                if R is None:
                    raise Exception("Echec solve circle")
                dist = np.linalg.norm([x_e - x_s, y1 - y2]) / 2
                UTMESS("F", "CALCSTABPENTE_32", valr=[R, dist, x_e, x_s])

        sgn = 1.0 if R is not None else -1.0
        y0 = (-B + sgn * np.sqrt(delta)) / 2 / A
        x0 = c1 - c2 * y0

        return x0, y0

    def radius_tripnt(self, l_x: List[float], l_y: List[float]) -> float:
        """Solve the radius of the circle passing throught the given 3 points.

        Args:
            l_x (List[float]): Abscissa list of the 3 points.
            l_y (List[float]): Ordinate list of the 3 points.

        Returns:
            float: Radius of the circle.
        """

        assert len(l_x) >= 3 and len(l_y) >= 3
        x1, x2, x3 = l_x[:3]
        y1, y2, y3 = l_y[:3]

        A = np.array([[x1 - x2, y1 - y2], [x1 - x3, y1 - y3]])
        if np.abs(np.linalg.det(A)) < 1e-6:
            raise Exception("Fatal: Colinear points.")
        b = 0.5 * np.array([x1**2 - x2**2 + y1**2 - y2**2, x1**2 - x3**2 + y1**2 - y3**2])
        centre = np.linalg.inv(A) @ b
        R = np.linalg.norm(centre - np.array([x1, y1]))

        return R

    def calc_para_geom(self, x_e, x_s, R):
        """Calculate geometrical parameters of the slip surface.

        Args:
            x_e (float): Abscissa of the left end of slip surface.
            x_s (float): Abscissa of the right end of slip surface.
            R (float): Radius of slip surface.

        Returns:
            dict: Dictionary containing the center, radius and interm points coordinates.
        """

        width = (x_s - x_e) / self.nb_tran
        x_0, y_0 = self.solve_circle(x_e, x_s, R)
        coor = []
        for npnt in range(self.nb_tran + 1):
            x_i = x_e + width * npnt
            y_i = self.calc_y(x_i, [x_0, y_0], R)
            coor.append([x_i, y_i])

        para_geom = {"centre": [x_0, y_0], "R": R, "coor": np.array(coor, dtype=np.float64)}

        return para_geom

    def calc_y(self, x, centre: List, R):
        """Calculate the lower intersection of a vertical line with a circle.

        Args:
            x (float): Abscissa.
            centre (List): Circle center.
            R (float): Circle radius.

        Returns:
            float: Intersection ordinate.
        """

        x0, y0 = centre
        if np.abs(x - x0) - R > 1e-6:
            return None
        y = y0 - np.sqrt(max([R**2 - (x - x0) ** 2, 0.0]))

        return y

    def calc_bishop(self, x_e, x_s, Rayon, MAILRAF=None):
        """Calculate the factor of security for circular failure surfaces.

        Args:
            x_e (float): Abscissa of the enter point.
            x_s (float): Abscissa of the exit point.
            Rayon (float): Radius of the failure surface.
            MAILRAF (Mesh object, optional): Refined mesh. Defaults to None.

        Returns:
            float: Factor of security.
        """

        # ===========================================================
        # 1. Initialisation
        # ===========================================================
        if MAILRAF is None:
            MAILRAF = self.mesh

        para_geom = self.calc_para_geom(x_e, x_s, Rayon)
        x_centre, y_centre = para_geom["centre"]
        width_tran = np.abs(x_e - x_s) / self.nb_tran

        # Division du modèle en tranches
        centre_base = np.zeros((self.nb_tran, 2))
        alpha = np.zeros(self.nb_tran)

        # ============================================================
        # 2. Calcul des alpha et propriété materiaux (maillage originel)
        # ============================================================
        for ntran in range(self.nb_tran):

            coor_c = [x_centre, y_centre]
            centre_base[ntran, 0] = (ntran + 1 / 2) * width_tran + np.min([x_e, x_s])
            centre_base[ntran, 1] = self.calc_y(centre_base[ntran, 0], coor_c, Rayon)

            x_1 = centre_base[ntran, 0] - 0.5 * width_tran
            x_2 = x_1 + width_tran
            tan_a = (self.calc_y(x_2, coor_c, Rayon) - self.calc_y(x_1, coor_c, Rayon)) / width_tran
            alpha[ntran] = np.arctan(tan_a)

        # Identifier les propriétés matériaux sur la surface critique
        mat_prop, ptot = self.get_properties_on_surface(para_geom)

        # =============================================
        # 3. Calcul des poids propres (maillage raffiné)
        # =============================================

        # Création grma de la partie glissante et calcul des poids des tranches
        MAILRAF = DEFI_GROUP(
            reuse=MAILRAF,
            MAILLAGE=MAILRAF,
            CREA_GROUP_MA=_F(
                OPTION="SPHERE",
                POINT=(x_centre, y_centre),
                RAYON=Rayon,
                CRIT_NOEUD="TOUS",
                NOM="GLISS",
                TYPE_MAILLE="2D",
            ),
        )

        poids, barycent = self.calc_poids_tranche(MAILRAF, centre_base, width_tran)

        MAILRAF = DEFI_GROUP(
            DETR_GROUP_MA=_F(NOM=("GLISS")),
            DETR_GROUP_NO=_F(NOM=("GLISS_N")),
            MAILLAGE=MAILRAF,
            reuse=MAILRAF,
        )

        # retrouver la vraie valeur de ptot en utilisant le poids obtenu
        if self.ptot_type == "COEF_RU":
            # par définition, p = r_u * gamma_s * H_s
            ptot[:, 1] = ptot[:, 1] * poids / width_tran

        # ===========================================
        # 4. Calcul des chargements méca externes
        # ===========================================

        char_ext = self.calc_char_ext(x_e, x_s, centre=np.array([x_centre, y_centre]))
        moment = char_ext.get("moment")
        pres_info = char_ext.get("pres")
        pres = pres_info["module"] if pres_info is not None else np.zeros_like(poids)
        beta = pres_info["angle"] if pres_info is not None else np.zeros_like(alpha)

        ## force normale due aux chargements externes (méthode Fellenius)
        fN_ext = pres * np.cos(alpha - beta) + poids * (
            self.kh * np.sin(alpha) - self.kv * np.cos(alpha)
        )

        ## force verticale due aux chargements externes (méthode Bishop), global Y positive
        fV_ext = -pres * np.cos(beta) + self.kv * poids

        # prise en compte de l'accélération volumique
        if not self.calc_kc:
            moment += np.sum(
                (self.kv * (barycent[:, 0] - x_centre) - self.kh * (barycent[:, 1] - y_centre))
                * poids
            )

        # ===========================================
        # 5. Calcul du FS
        # ===========================================

        sign_shear = 1.0 if self.is_upstream else -1.0
        tan_phi = np.tan(mat_prop[:, 0])

        if not self.bishop:
            effe_ptot = np.zeros_like(poids)
            for ntran in range(self.nb_tran):
                if ptot[ntran, 1] < 0:
                    effe_ptot[ntran] = (
                        (ptot[ntran, 1] - ptot[ntran, 0])
                        * width_tran
                        * np.cos(alpha[ntran])
                        * np.tan(mat_prop[ntran, 0])
                    )
                else:
                    effe_ptot[ntran] = -ptot[ntran, 0] * width_tran * np.cos(alpha[ntran]) * np.tan(
                        mat_prop[ntran, 0]
                    ) + ptot[ntran, 1] * width_tran / np.cos(alpha[ntran]) * np.tan(
                        mat_prop[ntran, 2]
                    )

            cdl = mat_prop[:, 1] * width_tran / np.cos(alpha)
            if self.calc_kc:
                # calculer le coefficient d'accélération critique
                k_c = np.sum(
                    sign_shear * (poids * np.sin(alpha) + pres * np.sin(alpha - beta))
                    - (
                        cdl
                        + (poids * np.cos(alpha) + pres * np.cos(alpha - beta)) * tan_phi
                        + effe_ptot
                    )
                ) / np.sum(poids * (np.sin(alpha) * tan_phi + sign_shear * np.cos(alpha)))

                # k_c = np.sum(
                #     sign_shear * (poids * np.sin(alpha) - moment / Rayon)
                #     - (cdl + (poids * np.cos(alpha) + pres * np.cos(alpha - beta)) * tan_phi + effe_ptot)
                # ) / np.sum(poids * (np.sin(alpha) * tan_phi + sign_shear * (barycent[:, 1] - y_centre) / Rayon))

                return np.abs(k_c)

            FS_resu = np.sum(cdl + (poids * np.cos(alpha) + fN_ext) * tan_phi + effe_ptot) / np.abs(
                np.sum(
                    poids * np.sin(alpha)
                    + pres * np.sin(alpha - beta)
                    - self.kh * poids * np.cos(alpha)
                    - self.kv * poids * np.sin(alpha)
                )
            )
            # ) / np.abs(np.sum(poids * np.sin(alpha)) - moment / Rayon)
        else:
            resi_max = 1e-6
            resi = 1.0
            FS = 1.0
            nb_iter_max = 1e3
            nb_iter = 1

            s_verti = (
                mat_prop[:, 1] * width_tran
                + (poids - fV_ext - ptot[:, 0] * width_tran) * tan_phi
                + ptot[:, 1] * width_tran * np.tan(mat_prop[:, 2])
            )

            if self.calc_kc:
                # calculer le coefficient d'accélération critique
                k_c = (
                    np.sum(
                        s_verti / (np.cos(alpha) + sign_shear * (np.sin(alpha) * tan_phi))
                        - poids * np.sin(alpha)
                    )
                    + moment / Rayon
                ) / np.sum(poids * (barycent[:, 1] - y_centre) / Rayon)

                return np.abs(k_c)

            while resi > resi_max:
                FS_new = np.sum(
                    s_verti / (np.cos(alpha) + sign_shear * (np.sin(alpha) * tan_phi / FS))
                ) / np.abs(np.sum(poids * np.sin(alpha)) - moment / Rayon)

                resi = np.abs(FS_new - FS)
                FS = FS_new

                nb_iter += 1
                if nb_iter > nb_iter_max:
                    # Divergence iteration point fixe
                    return 1e4

            FS_resu = FS

        return FS_resu

    def search_surf_crit(self):
        """Search for the critical surface minimizing the FS.

        Returns:
            dict: Dictionary containing the result of failure surface searching.
        """

        def eval_fs(l_R):
            # Evaluate the safety factor for a given list of radius.
            return [self.calc_bishop(x_e, x_s, R) for R in l_R]

        def cvt_rd(r):
            # Convert radius to d.
            return r - np.sqrt(r**2 - t**2)

        def cvt_dr(d):
            # Convert d to radius.
            return (t**2 + d**2) / 2 / d

        def calc_max_rayon():
            # Calculate the maximum radius

            k = (y_s - y_e) / (x_s - x_e)
            b = y_s - k * x_s
            R_m = -1.0
            for i_c in self.nno_cvex:
                pnt = self.pente[i_c, :2]
                if x_e < pnt[0] < x_s and k * pnt[0] + b > pnt[1]:
                    R = self.radius_tripnt(
                        [x_e, pnt[0], x_s], [y_e, pnt[1] - self.min_cell_size, y_s]
                    )
                    if R_m < 0.0 or R < R_m:
                        R_m = R

            if R_m < 0.0:
                return None

            # check validity of R_m
            nb_iter = 0
            ret = self.check_circle(x_e, x_s, R_m)
            while ret < 0:
                # invalid R_m --> calculate a valid R_m
                nb_iter += 1
                if nb_iter > 100:
                    UTMESS("F", "CALCSTABPENTE_27", vali=ret)

                if ret == -1:
                    # à cause des points convexes
                    R_m -= self.min_cell_size
                elif ret == -2:
                    # à cause de la position d'un point interm
                    xc, yc = self.solve_circle(x_e, x_s, R_m)
                    for x_i in np.linspace(x_e, x_s, self.nb_tran, endpoint=False)[1:]:
                        y_p = np.interp(x_i, self.pente[:, 0], self.pente[:, 1])
                        y_i = self.calc_y(x_i, [xc, yc], R_m)
                        marge_y = 2 * self.size_p[np.where(self.pente[:, 0] <= x_i)[0][-1]]
                        if y_p - y_i < marge_y:
                            R_m = self.radius_tripnt(
                                [x_e, x_i, x_s], [y_e, y_p - 1.05 * marge_y, y_s]
                            )
                            break
                elif ret == -3:
                    # Foudantion de taille insuffisante
                    UTMESS("F", "CALCSTABPENTE_29")

                ret = self.check_circle(x_e, x_s, R_m)

            return R_m

        resu_stab_circ = {}
        FS_MIN = np.inf

        surf_stat = []
        nb_surf_test = 0

        for x_e in self.x_bande_1:
            for x_s in self.x_bande_2:
                y_e = np.interp(x_e, self.pente[:, 0], self.pente[:, 1])
                y_s = np.interp(x_s, self.pente[:, 0], self.pente[:, 1])
                y_lower = np.min([y_e, y_s])
                t = np.linalg.norm([x_s - x_e, y_s - y_e]) / 2
                xb = x_e if y_e > y_s else x_s

                # R_min
                x_t, y_t = self.solve_circle(x_e, x_s, xb=xb)
                R_0 = np.abs(x_t - xb)
                if y_t - R_0 < self.y_bas:
                    # if hors du modèle, commencer par le cercle tangent à la base
                    x_t, y_t = self.solve_circle(x_e, x_s, yb=self.y_bas)
                    R_0 = y_t - self.y_bas

                # R_max
                R_max = calc_max_rayon()

                # User-defined horizontal tangential lines
                if self.y_min is not None:
                    ## use user-defined R_min
                    if self.y_min > y_lower:
                        continue
                    x_t, y_t = self.solve_circle(x_e, x_s, yb=self.y_min)
                    R_0 = y_t - self.y_min

                if self.y_max is not None:
                    # use user-defined R_max
                    if self.y_max >= y_lower:
                        y_sup = y_lower
                    else:
                        y_sup = self.y_max
                    x_c, y_c = self.solve_circle(x_e, x_s, yb=y_sup)
                    R_max = y_c - y_sup

                # Generate sequence of d
                d_0 = cvt_rd(R_0)
                if R_max is not None:
                    d_1 = cvt_rd(R_max)
                    if d_1 > d_0:
                        d_0, d_1 = d_1, d_0
                    incr_d = (d_0 - d_1) / (self.nb_r - 1)
                    l_d = np.linspace(d_0, d_1, self.nb_r, dtype=np.float64)
                else:
                    incr_d = d_0 / self.nb_r
                    l_d = np.arange(d_0, 0.0, -incr_d, dtype=np.float64)

                # Special Case
                if incr_d < 1e-6:
                    # Une rayon seule à tester
                    R_t = cvt_dr(l_d[0])
                    if self.check_circle(x_e, x_s, R_t) < 0:
                        UTMESS("F", "CALCSTABPENTE_28", valr=(x_e, x_s, R_t))

                    FS_0 = self.calc_bishop(x_e, x_s, R_t)
                    nb_surf_test += 1

                    regis_fs = [FS_0]
                    xc, yc = self.solve_circle(x_e, x_s, R_t)
                    surf_stat.append([xc, yc, R_t, FS_0])
                    if FS_0 < FS_MIN:
                        FS_MIN = FS_0
                        R_FS = R_t
                        x_enter_FS = x_e
                        x_sorti_FS = x_s
                    continue

                # Generate circular surfaces and evaluate FS
                surf_sub = []
                regis_fs = []
                l_R = []
                for d in l_d:
                    R_t = cvt_dr(d)
                    ret = self.check_circle(x_e, x_s, R_t)
                    if ret < 0:
                        break
                    xc, yc = self.solve_circle(x_e, x_s, R_t)
                    surf_sub.append([xc, yc, R_t])
                    l_R.append(R_t)
                    nb_surf_test += 1

                if not len(l_R):
                    UTMESS("F", "CALCSTABPENTE_30", vali=ret)

                l_d = l_d[: len(l_R)]
                regis_fs = eval_fs(l_R)

                for ind, fs in enumerate(regis_fs):
                    surf_sub[ind].append(fs)
                surf_stat += surf_sub

                FS_loc_min = min(regis_fs)

                # Mise à jour du mimima global
                if FS_loc_min < FS_MIN:
                    ind_min = regis_fs.index(FS_loc_min)
                    x_enter_FS = x_e
                    x_sorti_FS = x_s
                    d_FS = l_d[ind_min]
                    R_FS = cvt_dr(d_FS)

                    # Trouver la vraie mimina par la méthode de bifurcation
                    resi = np.inf
                    n_div = 1
                    fs_stat = np.zeros(5)
                    for i in range(5):
                        fs_stat[i] = np.inf
                    if ind_min == 0:
                        fs_stat[1:3] = np.array(regis_fs[:2])
                    elif ind_min == len(regis_fs) - 1:
                        fs_stat[:2] = np.array(regis_fs[ind_min - 1 :])
                    else:
                        fs_stat[:3] = np.array(regis_fs[ind_min - 1 : ind_min + 2])

                    while resi > 1e-3:
                        if fs_stat[0] == np.inf:
                            fs_stat[4] = self.calc_bishop(
                                x_e, x_s, cvt_dr(d_FS - incr_d / 2**n_div)
                            )
                        elif fs_stat[2] == np.inf:
                            fs_stat[3] = self.calc_bishop(
                                x_e, x_s, cvt_dr(d_FS + incr_d / 2**n_div)
                            )
                        else:
                            fs_stat[3:] = eval_fs(
                                [cvt_dr(d_FS + incr_d / 2**n_div), cvt_dr(d_FS - incr_d / 2**n_div)]
                            )

                        # Eviter les surfaces illégales et enregistrer les surface testees
                        for ind in [3, 4]:
                            if np.isnan(fs_stat[ind]):
                                fs_stat[ind] = np.inf
                            else:
                                nb_surf_test += 1
                                if ind == 3:
                                    d = d_FS + incr_d / 2**n_div
                                else:
                                    d = d_FS - incr_d / 2**n_div
                                xc, yc = self.solve_circle(x_e, x_s, cvt_dr(d))
                                surf_stat.append([xc, yc, cvt_dr(d), fs_stat[ind]])

                        FS = np.min(fs_stat)
                        if FS < FS_loc_min:
                            # Nouvel minima trouvé
                            ind_min = np.argmin(fs_stat)
                            if ind_min == 3:
                                d_FS += incr_d / 2**n_div
                                fs_stat[:3] = fs_stat[[0, 3, 1]]
                            else:
                                d_FS -= incr_d / 2**n_div
                                fs_stat[:3] = fs_stat[[1, 4, 2]]
                            R_FS = cvt_dr(d_FS)

                        resi = np.abs(FS - FS_loc_min)
                        FS_loc_min = FS
                        n_div += 1

                    FS_MIN = FS_loc_min

        # Sort by Radius
        surf_stat = np.array(surf_stat)
        ind_sort_r = np.argsort(surf_stat[:, 2])
        surf_stat = surf_stat[ind_sort_r, :]

        resu_stab_circ["RAYON"] = R_FS
        resu_stab_circ["X_ENTRE"] = x_enter_FS
        resu_stab_circ["X_SORTIE"] = x_sorti_FS
        resu_stab_circ["Y_ENTRE"] = np.interp(x_enter_FS, self.pente[:, 0], self.pente[:, 1])
        resu_stab_circ["Y_SORTIE"] = np.interp(x_sorti_FS, self.pente[:, 0], self.pente[:, 1])

        x_centre_FS, y_centre_FS = self.solve_circle(x_enter_FS, x_sorti_FS, R_FS)
        resu_stab_circ["CENTRE_X"] = x_centre_FS
        resu_stab_circ["CENTRE_Y"] = y_centre_FS
        resu_stab_circ["FS"] = FS_MIN

        resu_stab_circ["NB_SURF_TEST"] = nb_surf_test
        resu_stab_circ["HIST_CENTRE_X"] = surf_stat[:, 0]
        resu_stab_circ["HIST_CENTRE_Y"] = surf_stat[:, 1]
        resu_stab_circ["HIST_RAYON"] = surf_stat[:, 2]
        resu_stab_circ["HIST_FS"] = surf_stat[:, 3]

        return resu_stab_circ

    def run(self):
        """Perform the stability analysis using LEM method with circular failure surface.

        Returns:
            table object: Output table of the macro-command.
        """

        resu_stab_circ = self.search_surf_crit()
        l_FS = self.raff_maillage(resu_stab_circ, self.calc_bishop)

        nom_resu = "KC" if self.calc_kc else "FS"

        kw_list_table = [
            _F(LISTE_I=[i for i in range(len(l_FS))], PARA="NUME_RAFF"),
            _F(LISTE_R=l_FS, PARA=nom_resu),
            _F(LISTE_R=[resu_stab_circ["X_ENTRE"]], PARA="X_1"),
            _F(LISTE_R=[resu_stab_circ["Y_ENTRE"]], PARA="Y_1"),
            _F(LISTE_R=[resu_stab_circ["X_SORTIE"]], PARA="X_2"),
            _F(LISTE_R=[resu_stab_circ["Y_SORTIE"]], PARA="Y_2"),
            _F(LISTE_R=[resu_stab_circ["CENTRE_X"]], PARA="CENTRE_X"),
            _F(LISTE_R=[resu_stab_circ["CENTRE_Y"]], PARA="CENTRE_Y"),
            _F(LISTE_R=[resu_stab_circ["RAYON"]], PARA="RAYON"),
        ]

        if self.impr_detail:
            kw_list_table += [
                _F(LISTE_I=[resu_stab_circ["NB_SURF_TEST"]], PARA="NB_SURF_TEST"),
                _F(
                    LISTE_R=[
                        np.min(resu_stab_circ["HIST_CENTRE_X"]),
                        np.max(resu_stab_circ["HIST_CENTRE_X"]),
                    ],
                    PARA="EXT_CENTRE_X",
                ),
                _F(
                    LISTE_R=[
                        np.min(resu_stab_circ["HIST_CENTRE_Y"]),
                        np.max(resu_stab_circ["HIST_CENTRE_Y"]),
                    ],
                    PARA="EXT_CENTRE_Y",
                ),
                _F(
                    LISTE_R=[
                        np.min(resu_stab_circ["HIST_RAYON"]),
                        np.max(resu_stab_circ["HIST_RAYON"]),
                    ],
                    PARA="EXT_RAYON",
                ),
                _F(LISTE_R=resu_stab_circ["HIST_RAYON"], PARA="HIST_RAYON"),
                _F(LISTE_R=resu_stab_circ["HIST_CENTRE_X"], PARA="HIST_CENTRE_X"),
                _F(LISTE_R=resu_stab_circ["HIST_CENTRE_Y"], PARA="HIST_CENTRE_Y"),
                _F(LISTE_R=resu_stab_circ["HIST_FS"], PARA="HIST_" + nom_resu),
            ]

        TABFS = CREA_TABLE(LISTE=kw_list_table)

        return TABFS


class Surf_Non_Circ_Solver(LEM_Solver):
    """Solver object containing the methods for non-circular failure surface searching and FS calculation."""

    def __init__(self, parent, args):
        super(Surf_Non_Circ_Solver, self).__init__(parent, args)
        self.kw_efwa = args["ALGO_EFWA"]
        # niveau d'impression
        self.impr_detail = args.get("INFO_TABLE") == 2
        # germe pour les tirages aléatoires
        self.seed = args.get("INIT_ALEA")

    def bilan_last_tranche(
        self, poids, width, alpha, mat_prop, ptot, char_ext: Dict, spencer=True, ang_dir=None
    ):
        """Solve the FS-lambda coupling equations with the condition of null force and moment on the right of the last slice.

        Args:
            poids (list[float]): Array containing the deadweight of the slices.
            width (float): Uniform width of the slices.
            alpha (list[float]): Array containing the inclination angles of the slices' base.
            mat_prop (list[float]): Array of material properties on the base of slices.
            ptot (list[float]): Array of pore pressure on the base of slices.
            spencer (bool, optional): Indicate if the Spencer procedure is employed. Defaults to True.
            ang_dir (list[float], optional): Tangent of the interslice force direction at the ends of the failure surface. Defaults to None.

        Returns:
            float: Factor of security.
        """

        N = np.size(poids, 0)
        max_resi = 1e-6
        max_resi_sub = 1e-6
        lamb = 0.0
        FS = 1.0
        resi_FS = 1.0
        resi_lamb = 1.0
        max_iter = 100
        max_iter_sub = 200
        nb_iter = 0

        # Signe dépendante de côté de la pente
        sign_shear = 1.0 if self.is_upstream else -1.0

        # Récupérer les variables liés aux chargements externes
        moment = char_ext.get("moment")
        pres_info = char_ext.get("pres")
        pres = pres_info["module"] if pres_info is not None else np.zeros_like(poids)
        beta = pres_info["angle"] if pres_info is not None else np.zeros_like(alpha)

        tan_phi = np.tan(mat_prop[:, 0])
        tan_phi_b = np.tan(mat_prop[:, 2])
        effe_ptot_c = (
            (-ptot[:, 0] * tan_phi + ptot[:, 1] * tan_phi_b + mat_prop[:, 1])
            * width
            / np.cos(alpha)
        )

        if self.calc_kc:
            # f_resist = all shear forces generated by loadings other than lateral acceleration
            f_resist = (
                pres * np.sin(beta - alpha)
                - poids * np.sin(alpha)
                + sign_shear
                * ((poids * np.cos(alpha) + pres * np.cos(beta - alpha)) * tan_phi + effe_ptot_c)
            )
            # f_tangent = shear force due to lateral acceleration
            f_tangent = -poids * (np.cos(alpha) + sign_shear * np.sin(alpha) * tan_phi)
        else:
            # Force de résistance
            fN_ext = pres * np.cos(alpha - beta) + poids * (
                self.kh * np.sin(alpha) - self.kv * np.cos(alpha)
            )
            f_resist = (poids * np.cos(alpha) + fN_ext) * tan_phi + effe_ptot_c
            f_resist *= sign_shear

            # Force tangentielle mobilisante
            fS_ext = -pres * np.sin(beta - alpha) - poids * (
                self.kh * np.cos(alpha) + self.kv * np.sin(alpha)
            )
            f_tangent = poids * np.sin(alpha) + fS_ext

        # Résolution lambda et FS par itération point fixe
        while resi_FS > max_resi or resi_lamb > max_resi:
            nb_iter += 1

            lamb_old = lamb
            # Calcul des angles tan(theta) = f0(x) + lambda*sin(x) [Chen and Morgenstern, 1983]
            # Cardinal(f) = N
            if spencer:
                # f0 = 0 et f = 1 --> Méthode Spencer
                theta = np.arctan(np.ones(N) * lamb)
                f0 = np.zeros(N)
                f1 = np.ones(N)
            else:
                # f0 = variation linéaire, f = sin(pi/width*(x-x_min)) --> Méthode MP
                f0 = np.linspace(ang_dir[0], ang_dir[1], N + 1)[1:]
                f1 = np.sin(np.linspace(0.0, np.pi, N + 1)[1:])
                theta = np.arctan(f0 + f1 * lamb)

            FS_old = FS
            # Mise à jour du FS
            FS_sub = FS
            resi_sub = 1.0
            nb_iter_sub = 1.0
            while resi_sub > max_resi_sub:
                coef_z = 1.0 if self.calc_kc else FS
                Phi = coef_z * np.cos(alpha - theta) + sign_shear * np.sin(alpha - theta) * tan_phi
                Psi = np.zeros(N - 1)

                numer = f_resist[-1]
                denom = f_tangent[-1]
                for n in range(N - 2, -1, -1):
                    Psi[n] = (
                        coef_z * np.cos(alpha[n + 1] - theta[n])
                        + sign_shear * np.sin(alpha[n + 1] - theta[n]) * np.tan(mat_prop[n + 1, 0])
                    ) / Phi[n]
                    PI_psi = 1.0
                    for j in range(n, N - 1):
                        PI_psi *= Psi[j]
                    numer += f_resist[n] * PI_psi
                    denom += f_tangent[n] * PI_psi

                FS = numer / denom
                if self.calc_kc:
                    break
                resi_sub = np.abs(FS_sub - FS)
                FS_sub = FS
                if nb_iter_sub > max_iter_sub:
                    # Divergence
                    return 1e4
                else:
                    nb_iter_sub += 1

            resi_FS = np.abs(FS - FS_old)

            # Force d'interantion entre tranches, F_n = 0
            F_inter = np.zeros(N)
            F_inter[0] = (f_resist[0] - FS * f_tangent[0]) / Phi[0]
            for n in range(1, N - 1):
                F_inter[n] = (
                    Psi[n - 1] * F_inter[n - 1] * Phi[n - 1] + f_resist[n] - FS * f_tangent[n]
                ) / Phi[n]
            F_hor = F_inter * np.cos(theta)

            # Mise à jour de lambda
            numer_l = np.tan(alpha[0]) * F_hor[0] - f0[0] * F_hor[0]
            denom_l = f1[0] * F_hor[0]

            for n in range(1, N):
                numer_l += np.tan(alpha[n]) * (F_hor[n] + F_hor[n - 1]) - (
                    f0[n] * F_hor[n] + f0[n - 1] * F_hor[n - 1]
                )
                denom_l += f1[n] * F_hor[n] + f1[n - 1] * F_hor[n - 1]

            moment_ext = moment
            if self.calc_kc:
                moment_ext += char_ext["mom_late"] * FS
            lamb = (numer_l + moment_ext * 2 / width) / denom_l
            resi_lamb = np.abs(lamb_old - lamb)

            if nb_iter == max_iter:
                UTMESS("I", "CALCSTABPENTE_17")
                return 1e4

        if self.calc_kc:
            #  si coef séisme, dans le repère global, k_c = FS peut être négatif
            FS = np.abs(FS)

        if FS < 0:
            # FS négatif à cause de d'une surface irréaliste, donc à éliminer
            return 1e4

        return FS

    def calc_morgenstern(self, vari_etat, MAILRAF=None):
        """Calculate the factor of security for non-circular failure surfaces.

        Args:
            vari_etat (list[float]): Array containing the abscissa of the end points and the ordinates of the intermediate points.
            MAILRAF (Mesh object, optional): Refined mesh. Defaults to None.

        Returns:
            float: Factor of security.
        """

        x_e = vari_etat[0]
        x_s = vari_etat[-1]
        l_Y = vari_etat[1:-1]

        N = len(l_Y) + 1
        surf_X = np.linspace(x_e, x_s, N + 1)
        surf_Y = np.array([np.interp(x_e, self.pente[:, 0], self.pente[:, 1])])
        surf_Y = np.concatenate((surf_Y, np.array(l_Y)))
        surf_Y = np.append(surf_Y, np.interp(x_s, self.pente[:, 0], self.pente[:, 1]))

        # Division du modèle en tranches et calculer ALPHA, CENTRE_BASE, C et PHI
        centre_base = np.zeros((N, 2))
        alpha = np.zeros(N)
        width_tran = np.abs(x_e - x_s) / N

        for ntran in range(N):
            centre_base[ntran, 0] = (surf_X[ntran] + surf_X[ntran + 1]) / 2
            centre_base[ntran, 1] = (surf_Y[ntran] + surf_Y[ntran + 1]) / 2
            tan_a = (surf_Y[ntran + 1] - surf_Y[ntran]) / (surf_X[ntran + 1] - surf_X[ntran])
            alpha[ntran] = np.arctan(tan_a)

        mat_prop, ptot = self.get_properties_on_surface(
            {"coor": np.array(self.get_surf_coor(vari_etat)).T}, is_circ=False
        )

        # Calcul des poids propres des tranches et création du grma de la partie glissante
        if MAILRAF is None:
            MAILRAF = self.mesh

        ## grma de la mass glissante
        l_grma_cree = []
        kw_crea_grma = []
        d = 100.0
        for ntran in range(self.nb_tran):
            x_d = centre_base[ntran, 0] - np.sin(alpha[ntran]) * d
            y_d = centre_base[ntran, 1] + np.cos(alpha[ntran]) * d
            nom_grma = "_".join([str(ntran), "base"])
            l_grma_cree.append(nom_grma)
            kw_crea_grma.append(
                _F(
                    OPTION="BANDE",
                    ANGL_NAUT=(alpha[ntran] * 180.0 / np.pi + 90.0,),
                    DIST=d,
                    POINT=(x_d, y_d),
                    NOM=nom_grma,
                    TYPE_MAILLE="2D",
                    CRIT_NOEUD="TOUS",
                )
            )
        kw_crea_grma.append(_F(INTERSEC=l_grma_cree, NOM="GLISS"))
        MAILRAF = DEFI_GROUP(reuse=MAILRAF, MAILLAGE=MAILRAF, CREA_GROUP_MA=kw_crea_grma)
        poids, barycent = self.calc_poids_tranche(MAILRAF, centre_base, width_tran)

        ## destruction
        l_grma_cree.append("GLISS")
        MAILRAF = DEFI_GROUP(reuse=MAILRAF, MAILLAGE=MAILRAF, DETR_GROUP_MA=_F(NOM=l_grma_cree))

        # retrouver la vraie valeur de ptot en utilisant le poids obtenu
        if self.ptot_type == "COEF_RU":
            # par définition, p = r_u * gamma_s * H_s
            ptot[:, 1] = ptot[:, 1] * poids / width_tran

        # Calcul des chargements méca externes
        char_ext = self.calc_char_ext(x_e, x_s, centre=centre_base.tolist())

        ## prise en compte de l'accélération volumique
        if not self.calc_kc:
            char_ext["moment"] += np.sum(
                np.cross(barycent - centre_base, [self.kh, self.kv]) * poids
            )
        else:
            char_ext.update({"mom_late": np.sum((centre_base[:, 1] - barycent[:, 1]) * poids)})

        # Résolution du FS
        if self.spencer:
            FS = self.bilan_last_tranche(poids, width_tran, alpha, mat_prop, ptot, char_ext)
        else:
            nno_l = np.where(self.pente[:, 0] >= x_e)[0][0]
            nno_r = np.where(self.pente[:, 0] <= x_s)[0][-1]
            tan_ang = []
            for ind, nno in enumerate([nno_l, nno_r]):
                incr = 1 if ind == 0 else -1
                tan = (self.pente[nno, 1] - self.pente[nno + incr, 1]) / (
                    self.pente[nno, 0] - self.pente[nno + incr, 0]
                )
                tan_ang.append(tan)

            FS = self.bilan_last_tranche(
                poids, width_tran, alpha, mat_prop, ptot, char_ext, spencer=False, ang_dir=tan_ang
            )

        return FS

    def get_surf_coor(self, vari_etat):
        """Recover the interm point coordinates of a non-circular slip surface.

        Args:
            etat_vari (ndarray): List of state variables.

        Returns:
            list[ndarray]: List of abscissa and ordinates.
        """

        coor_y = vari_etat.copy()
        coor_y[0] = np.interp(vari_etat[0], self.pente[:, 0], self.pente[:, 1])
        coor_y[-1] = np.interp(vari_etat[-1], self.pente[:, 0], self.pente[:, 1])
        coor_x = np.linspace(vari_etat[0], vari_etat[-1], self.nb_tran + 1)

        return [coor_x, coor_y]

    def run(self):
        """Perform the stability analysis using LEM method with circular failure surface.

        Returns:
            table object: Output table of the macro-command.
        """

        efwa_optimizer = Efwa_Optimizer(self)
        etat_opti, FS_opti, hist_fs, surf_stat = efwa_optimizer.optimize()
        resu_stab_nc = {}

        # Restaurer les coordonnées des points sur la surface critique
        coord_X, coord_Y = self.get_surf_coor(etat_opti)

        resu_stab_nc["COOR_X"] = coord_X
        resu_stab_nc["COOR_Y"] = coord_Y
        resu_stab_nc["FS"] = FS_opti

        # Raffinement du maillage
        l_FS = self.raff_maillage(resu_stab_nc, self.calc_morgenstern)

        # Statistic surface testees
        coll_coor_x = np.zeros((self.nb_tran + 1, len(surf_stat)))
        coll_coor_y = np.zeros((self.nb_tran + 1, len(surf_stat)))

        for ind in range(len(surf_stat)):
            coord_X, coord_Y = self.get_surf_coor(surf_stat[ind])
            coll_coor_x[:, ind] = coord_X
            coll_coor_y[:, ind] = coord_Y

        nom_resu = "FS" if not self.calc_kc else "KC"
        if self.kw_efwa["ETAT_INIT"] is not None:
            tab_init = efwa_optimizer.get_tab_init()

            if "RAYON" not in tab_init and "MIN_X" in tab_init:
                # Take into account the statistic info in initial input
                hist_fs = tab_init["HIST_" + nom_resu] + hist_fs

                if len(tab_init["MIN_X"]) == self.nb_tran + 1:
                    coll_coor_x = np.hstack(
                        (
                            coll_coor_x,
                            np.array(tab_init["MIN_X"]).reshape(-1, 1),
                            np.array(tab_init["MAX_X"]).reshape(-1, 1),
                        )
                    )

                    coll_coor_y = np.hstack(
                        (
                            coll_coor_y,
                            np.array(tab_init["MIN_Y"]).reshape(-1, 1),
                            np.array(tab_init["MAX_Y"]).reshape(-1, 1),
                        )
                    )

        kw_list_table = [
            _F(LISTE_I=[i for i in range(len(l_FS))], PARA="NUME_RAFF"),
            _F(LISTE_R=l_FS, PARA=nom_resu),
            _F(LISTE_I=[i for i in range(self.nb_tran + 1)], PARA="NUME_POINT"),
            _F(LISTE_R=resu_stab_nc["COOR_X"], PARA="COOR_X"),
            _F(LISTE_R=resu_stab_nc["COOR_Y"], PARA="COOR_Y"),
        ]

        if self.impr_detail:
            kw_list_table += [
                _F(LISTE_R=np.min(coll_coor_x, axis=1), PARA="MIN_X"),
                _F(LISTE_R=np.max(coll_coor_x, axis=1), PARA="MAX_X"),
                _F(LISTE_R=np.min(coll_coor_y, axis=1), PARA="MIN_Y"),
                _F(LISTE_R=np.max(coll_coor_y, axis=1), PARA="MAX_Y"),
                _F(LISTE_I=[i for i in range(len(hist_fs))], PARA="NUME_ITER"),
                _F(LISTE_R=hist_fs, PARA="HIST_" + nom_resu),
            ]

        TABFS = CREA_TABLE(LISTE=kw_list_table)

        return TABFS


class Efwa_Optimizer:
    """Optimizer object containing the methods related to the EFWA algorithm."""

    def __init__(self, lem_solver: Surf_Non_Circ_Solver):
        kw_efwa = lem_solver.kw_efwa
        self.lem_solver = lem_solver
        self.iter_maxi = kw_efwa["ITER_MAXI"]
        self.A = kw_efwa["A"]
        self.N = kw_efwa["N"]
        self.M = kw_efwa["M"]
        self.MG = kw_efwa["MG"]
        self.SA = kw_efwa["SA"]
        self.SB = kw_efwa["SB"]
        self.nb_stab_maxi = kw_efwa["NB_STAB_MAXI"]
        self.resi_maxi = kw_efwa["CRIT_STAB"]

        etat_init = kw_efwa.get("ETAT_INIT")
        self.tab_init = etat_init
        if etat_init is not None:
            tab_init = etat_init.EXTR_TABLE().values()
            ## remove None in tab_init at the end
            for key, l_val in tab_init.items():
                for ind, val in enumerate(l_val):
                    if val is None:
                        tab_init[key] = l_val[:ind]
                        break
            self.tab_init = tab_init

        # Prend le max y-dim comme marge si absent
        self.edge_bc_ctl = kw_efwa.get("MARGE_PENTE")

        self.bbas = lem_solver.x_lim_1
        self.bhaut = lem_solver.x_lim_2
        self.nb_tran = lem_solver.nb_tran
        self.nb_vari = lem_solver.nb_tran + 1

        self.get_pnt_aigu(lem_solver.pente)

        # Evaluer A_init et A_fina pour contrôler amplitude minimale d'explosion
        width = np.abs(sum(self.bbas) / 2 - sum(self.bhaut) / 2) / self.nb_tran
        self.A_init = width if kw_efwa.get("A_INIT") is None else kw_efwa["A_INIT"]
        self.A_fina = width * 0.1 if kw_efwa.get("A_FINAL") is None else kw_efwa["A_FINAL"]

        if self.N < 1:
            UTMESS("F", "CALCSTABPENTE_20")

        if not self.lem_solver.seed:
            now = datetime.now()
            self.lem_solver.seed = now.microsecond
            UTMESS("I", "SEISME_83", vali=self.lem_solver.seed)
        np.random.seed(self.lem_solver.seed)

    def get_tab_init(self):
        return self.tab_init

    def get_pnt_aigu(self, pente):
        """Find locations of slope ratio discontinuity

        Args:
            pente (ndarray): Coordinates of slope surface nodes.
        """

        l_k = self.lem_solver.k
        l_dk = self.lem_solver.dk

        pnt_aigu = []
        k_seg = []
        for ind, dk in enumerate(l_dk):
            kk = l_k[ind : ind + 2]
            if all(k is None for k in kk):
                continue
            if None in kk or np.abs(dk) > 1e-6:
                if not len(pnt_aigu):
                    k_seg.append(l_k[ind])
                pnt_aigu.append(pente[ind + 1, :])
                k_seg.append(l_k[ind + 1])

        if not len(k_seg):
            k_seg.append(l_k[0])

        ang_pente = np.zeros_like(k_seg).astype(np.float64)
        for ind, k in enumerate(k_seg):
            if k is None:
                ang_pente[ind] = np.pi / 2 if self.lem_solver.is_upstream else -np.pi / 2
            else:
                ang_pente[ind] = np.arctan(k)

        self.pnt_aigu = np.array(pnt_aigu, dtype=np.float64)
        self.ang_pente = ang_pente

        return

    def get_angle_pente(self, x, right: bool):
        """Calculate the slope angle at the given abscissa.

        Args:
            x (float): Abscissa value.
            right (bool): Take right-side slope angle if x coincide with a discontinous point.

        Returns:
            float: Slope angle in rad.
        """

        if self.pnt_aigu.shape[0] == 0:
            # pente non-segmentée
            ang_p = (
                0.0
                if np.min([np.abs(self.lem_solver.pente[ind, 0] - x) for ind in [0, -1]]) < 1e-6
                else self.ang_pente[0]
            )
        else:
            for i_pnt in range(self.pnt_aigu.shape[0]):
                pnt = self.pnt_aigu[i_pnt, :]
                if np.abs(pnt[0] - x) < 1e-6:
                    # coincidence
                    i_k = i_pnt
                    if right:
                        # on prend toujours le k hors de la masse glissante
                        i_k += 1
                    ang_p = self.ang_pente[i_k]
                    break
                if self.pnt_aigu.shape[0] == 1:
                    # 2 segments seuls
                    i_k = 0 if x < pnt[0] else 1
                    ang_p = self.ang_pente[i_k]
                    break
                if pnt[0] < x and self.pnt_aigu[i_pnt + 1, 0] > x:
                    # entre 2 points aigus
                    ang_p = self.ang_pente[i_pnt + 1]
                    break
                if i_pnt == self.pnt_aigu.shape[0] - 2:
                    # hors des points aigus
                    i_k = 0 if x < self.pnt_aigu[0, 0] else -1
                    ang_p = self.ang_pente[i_k]
                    break

        return ang_p

    def calc_bound(self, vari_etat, ivar, is_flip=None):
        """Calculate the lower and upper limits of a stat variable.

        Args:
            vari_etat (list[float]): Array of the current stat variables.
            ivar (int): Index of the stat variable.
            is_flip (None or bool, optional): Indicate if the slipe surface is flipped or not.

        Returns:
            float, float: Lower and upper limits.
        """
        is_up = self.lem_solver.is_upstream
        if is_flip is None:
            assert ivar > 0 and ivar < self.nb_vari - 1
            is_flip = vari_etat[-1] < vari_etat[0]

        acti_init = (is_up and is_flip) or (not is_up and not is_flip)
        b_extr = [self.bbas, self.bhaut]

        if ivar == 0:
            return b_extr[int(is_flip)]
        if ivar == self.nb_vari - 1:
            return b_extr[1 - int(is_flip)]

        x_e = vari_etat[0]
        x_s = vari_etat[-1]
        y_e = np.interp(x_e, self.lem_solver.pente[:, 0], self.lem_solver.pente[:, 1])
        y_s = np.interp(x_s, self.lem_solver.pente[:, 0], self.lem_solver.pente[:, 1])
        width_tran = (x_s - x_e) / self.nb_tran

        x_i = x_e + ivar * width_tran

        # Retrouver les coordonées des points précédents
        if ivar == 1:
            x2 = x_e
            y2 = y_e
        else:
            x1 = x_i - 2 * width_tran
            x2 = x_i - width_tran
            if ivar == 2:
                y1 = y_e
            else:
                y1 = vari_etat[ivar - 2]
            y2 = vari_etat[ivar - 1]

        # Calcul de la limite supérieure
        upper = ((x2 - x_i) * y_s + (x_i - x_s) * y2) / (x2 - x_s)

        ## Eviter l'intersection avec le profil de pente
        k = (y2 - upper) / (x2 - x_i)
        for pnt in self.pnt_aigu:
            x_n, y_n = pnt[:2]
            if x_n <= x2:
                continue
            if x_n >= x_s:
                break
            if k * (x_n - x2) + y2 - y_n > 1e-6:
                new_upper = ((x2 - x_i) * y_n + (x_i - x_n) * y2) / (x2 - x_n)
                if new_upper < upper:
                    upper = new_upper

        # Eviter que le point soit trop proche du bord
        y_pente = np.interp(x_i, self.lem_solver.pente[:, 0], self.lem_solver.pente[:, 1])
        if self.edge_bc_ctl is not None:
            marge_y = self.edge_bc_ctl
        else:
            marge_y = self.lem_solver.size_p[np.where(self.lem_solver.pente[:, 0] <= x_i)[0][-1]]

        upper = min([upper, y_pente - marge_y])

        # Calcul de la limite inférieure
        sgn = -1.0 if is_flip else 1.0
        if ivar == 1:
            # L'angle entre la surface et le profil de pente < 45 deg afin d'avoir assez de profondeur
            ang_init = np.pi / 4
            if acti_init:
                ang_init = np.pi / 3
            ang_e = self.get_angle_pente(x_e, is_flip)
            lower = y_e + np.tan(ang_e - sgn * ang_init) * width_tran
        else:
            lower = ((x1 - x_i) * y2 + (x_i - x2) * y1) / (x1 - x2)
            if ivar == self.nb_vari - 2 and acti_init:
                # verifier si la surface est lisse, corriger sinon
                ang_s = self.get_angle_pente(x_s, is_flip)
                y_min = y_s + np.tan(ang_s - sgn * np.pi / 4) * width_tran
                if lower < y_min:
                    lower = y_min

        # Eviter que la surface croisse avec le fond du modèle
        if lower < self.lem_solver.y_bas:
            lower = self.lem_solver.y_bas

        return lower, upper

    def get_etat_init(self):
        """Get initial slip surface.

        Returns:
            ndarray: Initial state variables.
        """
        # récupérer l'état initial indiqué par l'utilisateur

        etat_init = np.zeros(self.nb_vari)
        if "RAYON" in self.tab_init:
            # Initialisé par surface circulaire
            etat_init[0] = self.tab_init["X_1"][0]
            etat_init[-1] = self.tab_init["X_2"][0]
            x_1, x_2, x_c, y_c, r = [
                self.tab_init[key][0] for key in ["X_1", "X_2", "CENTRE_X", "CENTRE_Y", "RAYON"]
            ]
            etat_init[1:-1] = [
                y_c - np.sqrt(r**2 - (x - x_c) ** 2)
                for x in np.linspace(x_1, x_2, self.nb_vari)[1:-1]
            ]
        else:
            # Initialisé par surface non-circulaire
            etat_init[0] = self.tab_init["COOR_X"][0]
            etat_init[-1] = self.tab_init["COOR_X"][-1]
            if len(self.tab_init["COOR_X"]) == self.nb_vari:
                etat_init[1:-1] = self.tab_init["COOR_Y"][1:-1]
            else:
                # Nombre de tranches évolué --> Interpolation
                etat_init[1:-1] = [
                    np.interp(x, self.tab_init["COOR_X"], self.tab_init["COOR_Y"])
                    for x in np.linspace(etat_init[0], etat_init[-1], self.nb_vari)[1:-1]
                ]

        return etat_init

    def flip_cond(self, l_vari, ivar=1, passif=True):
        """Conditional flip of state variables.
        The output list begins with the initial point of surface generation.

        Args:
            l_vari (ndarray): Liste of variables to modify.
            ivar (int, optional): An indice in the liste. Defaults to 1.
            passif (bool, optional): Passive end initialted or not. Defaults to True.

        Returns:
            tuple: flipped list and the corresponding indice.
        """

        is_up = self.lem_solver.is_upstream
        flipped = True
        if (is_up and passif) or (not is_up and not passif):
            flipped = False
            return (l_vari, ivar, flipped)
        return (np.flip(l_vari, 0), self.nb_vari - 1 - ivar, flipped)

    def proc_point_interm(self, vari_etat, ivar=1, is_flip=None, check=False, recur=True):
        """Generate or verify a set of state variables

        Args:
            vari_etat (ndarray): Input state variables.
            ivar (int, optional): Beginning indice. Defaults to 1.
            check (bool, optional): Check or generate mode. Defaults to False.
            recur (bool, optional): Use recursive algorithm or not. Defaults to True.

        Returns:
            ndarray: Generated or verified variables, if failed return None
        """

        assert ivar >= 0
        if not check:
            # Récursion obligatoire pour générer une surface
            assert recur

        i_fin = self.nb_vari if check else self.nb_vari - 1
        if ivar == i_fin:
            return vari_etat

        vari_orig = vari_etat.copy()
        if not recur:
            for iivar in range(ivar, i_fin):
                lower, upper = self.calc_bound(vari_orig, iivar, is_flip)
                if upper < lower:
                    return None
                if vari_orig[iivar] < lower or vari_orig[iivar] > upper:
                    vari_orig[iivar] = np.random.uniform(lower, upper)
            return vari_orig

        lower, upper = self.calc_bound(vari_etat, ivar, is_flip)
        if upper < lower:
            return None

        nb_echec = -1
        while True:
            nb_echec += 1
            if nb_echec == 2:
                return None
            if (check and (vari_orig[ivar] < lower or vari_orig[ivar] > upper)) or (not check):
                vari_etat[ivar] = np.random.uniform(lower, upper)
            vari_etat_next = self.proc_point_interm(vari_etat, ivar + 1, is_flip, check)
            if vari_etat_next is not None:
                return vari_etat_next

    def optimize(self):
        """EFWA optimisation

        Returns:
            list[float], float: Geometric parameters of the critical surface and the associated FS.
        """

        def eval_fs(surfs):
            # Evaluate FS
            return np.array([self.lem_solver.calc_morgenstern(surf) for surf in surfs])

        # ---------------- INITIALIZATION ------------------
        surf_stat = []
        fireworks = np.zeros((self.N, self.nb_vari))

        fireworks[:, 0] = np.random.uniform(self.bbas[0], self.bbas[1], size=self.N)
        fireworks[:, -1] = np.random.uniform(self.bhaut[0], self.bhaut[1], size=self.N)

        # INITIALIZER : Générer les Y des points intermédiaires
        for ifw in range(self.N):
            surf = self.proc_point_interm(self.flip_cond(fireworks[ifw, :])[0])
            if surf is None:
                UTMESS("F", "CALCSTABPENTE_31")
            fireworks[ifw, :] = self.flip_cond(surf)[0]

        if self.tab_init is not None:
            # No kinematic acceptability check
            fireworks[0, :] = self.get_etat_init()

        fit = eval_fs(fireworks)
        for ifw in range(self.N):
            surf_stat.append(fireworks[ifw, :])

        FS_opti = np.min(fit)
        id_opti = np.argmin(fit)
        etat_opti = fireworks[id_opti, :]

        # ----------------- OPTIMISATION -------------------
        nb_iter = 1
        nb_stab = 0
        epsi = 1e-8
        hist_opti = [FS_opti]
        nb_etinc = np.zeros(self.N)
        ampli = np.zeros(self.N)

        while nb_iter <= self.iter_maxi and nb_stab < self.nb_stab_maxi:
            fs_max = np.max(fit)
            denom_etin = np.sum(fs_max - fit) + epsi
            denom_ampli = np.sum(fit - FS_opti) + epsi
            A_min = self.A_init - (self.A_init - self.A_fina) / self.iter_maxi * np.sqrt(
                (2 * self.iter_maxi - nb_iter - 1) * (nb_iter - 1)
            )

            for ifw in range(self.N):
                # CALC NB ETINCELLES
                Si = self.M * (fs_max - fit[ifw] + epsi) / denom_etin
                if Si < self.SA * self.M:
                    Si = self.SA * self.M
                if Si > self.SB * self.M:
                    Si = self.SB * self.M
                nb_etinc[ifw] = round(Si)

                # CALC AMPLITUDE
                denom_ampli = np.sum(fit - FS_opti) + epsi
                Ai = self.A * (fit[ifw] - FS_opti + epsi) / denom_ampli
                ampli[ifw] = max([Ai, A_min])

            nb_etinc = nb_etinc.astype("int64")

            # EXPLOSION
            etinc = np.zeros((np.sum(nb_etinc), self.nb_vari))
            etinc_gauss = np.zeros((self.MG, self.nb_vari))

            # Générer les étincelles ordinaires et évaluer FS
            for ifw in range(self.N):
                for ie in range(nb_etinc[ifw]):
                    ind = np.sum(nb_etinc[:ifw]) + ie
                    etinc[ind, :] = fireworks[ifw, :].copy()
                    pass_init = round(np.random.rand()) == 1

                    for ivar in range(self.nb_vari):
                        if round(np.random.rand()) == 1:
                            dx = ampli[ifw] * np.random.uniform(-1, 1)
                            surf = etinc[ind, :].copy()
                            surf[ivar] += dx

                            surf = self.proc_point_interm(
                                *self.flip_cond(surf, ivar, pass_init), check=True, recur=pass_init
                            )
                            if surf is None:
                                break
                            etinc[ind, :] = self.flip_cond(surf, passif=pass_init)[0]
                    surf_stat.append(etinc[ind, :])
            fit_etinc = eval_fs(etinc)

            # Générer les étincelles gaussiennes et évaluer FS
            for igauss in range(self.MG):
                id_luck = int(np.random.rand() * self.N) - 1
                etinc_gauss[igauss, :] = fireworks[id_luck, :].copy()
                pass_init = round(np.random.rand()) == 1

                for ivar in range(self.nb_vari):
                    if round(np.random.rand()) == 1:
                        coef_gauss = np.random.normal(1, 1)
                        surf = etinc_gauss[igauss, :].copy()
                        surf[ivar] += (
                            fireworks[id_opti, ivar] - etinc_gauss[igauss, ivar]
                        ) * coef_gauss

                        surf = self.proc_point_interm(
                            *self.flip_cond(surf, ivar, pass_init), check=True, recur=pass_init
                        )

                        if surf is None:
                            break
                        etinc_gauss[igauss, :] = self.flip_cond(surf, passif=pass_init)[0]

                surf_stat.append(etinc_gauss[igauss, :])
            fit_gauss = eval_fs(etinc_gauss)

            # SELECTION PAR L'ALGORITHME DE ROULETTE
            etinc_tot = np.vstack((fireworks, etinc, etinc_gauss))
            fit_tot = np.concatenate((fit, fit_etinc, fit_gauss))

            resi = np.abs(FS_opti - np.min(fit_tot))
            if resi < self.resi_maxi:
                nb_stab += 1
            else:
                nb_stab = 0

            FS_opti = np.min(fit_tot)
            idmin = np.argmin(fit_tot)
            etat_opti = etinc_tot[idmin, :]
            fireworks[0, :] = etat_opti
            fit[0] = FS_opti

            ## MAJ les variables d'itération
            hist_opti.append(FS_opti)
            nb_iter += 1
            id_opti = 0

            ## SHOTGUN
            if self.N == 1:
                continue
            if np.abs(np.max(fit_tot) - FS_opti) < 1e-6:
                ind_etin = np.random.randint(0, etinc_tot.shape[0], self.N - 1)
                fireworks[1:, :] = etinc_tot[ind_etin, :]
                fit[1:] = fit_tot[ind_etin, :]
            else:
                p = (np.max(fit_tot) - fit_tot) / (np.max(fit_tot) - FS_opti)
                p_cumul = np.zeros_like(p)
                for ifw in range(np.size(p, 0)):
                    p_cumul[ifw] = np.sum(p[: ifw + 1])

                shotgun = np.random.uniform(0, np.sum(p), self.N - 1)
                for ifw, val in enumerate(shotgun):
                    for ie, prob in enumerate(p_cumul):
                        if prob >= val:
                            fireworks[ifw + 1, :] = etinc_tot[ie, :]
                            fit[ifw + 1] = fit_tot[ie]
                            break

        return etat_opti, FS_opti, hist_opti, surf_stat
