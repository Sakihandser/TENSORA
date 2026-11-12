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

# ------------------------------------------------------------------------
# POST_NEWMARK : Dynamic stability analysis of earth dams and embankments
# ------------------------------------------------------------------------

import aster
import numpy as np
from scipy.optimize import curve_fit

from ..Cata.Syntax import _F
from ..CodeCommands import (
    AFFE_MATERIAU,
    AFFE_MODELE,
    CALC_CHAMP,
    CALC_FONCTION,
    CALC_TABLE,
    CREA_CHAMP,
    CREA_MAILLAGE,
    CREA_RESU,
    CREA_TABLE,
    DEFI_FONCTION,
    DEFI_GROUP,
    DEFI_MATERIAU,
    FORMULE,
    IMPR_RESU,
    MACR_ADAP_MAIL,
    MODI_MAILLAGE,
    POST_ELEM,
    POST_RELEVE_T,
    PROJ_CHAMP,
)
from ..Messages import UTMESS, MasquerAlarme, RetablirAlarme
from ..Objects import Mesh
from ..Objects.table_py import Table
from ..Supervis import CO


def get_static_shear(sign_static, sigt_static, phi, cohesion):
    ## Obtain static shear for FS analysis
    ## All input are considered as vectors definde at each node of the sliding line
    ## Mohr-Coulomb criteria for friction materials
    ##
    ## Input : sign_static : normal stress  (N)
    ##         sigt_static : tangential stress (T)
    ##         phi : friction angle (rad) (phi)
    ##         cohesion (c)
    ## Output : available_shear : total shear stress along the slinding line
    ##                            sum(N*tan(phi)-c)
    ##          static_shear : total shear stress mobilised along the sliding line
    ##                            sum(T)

    tanphi = np.tan(np.pi * np.array(phi) / 180.0)

    available_shear = np.sum(np.array(sign_static) * tanphi - np.array(cohesion))
    static_shear = np.sum(np.array(sigt_static))

    return available_shear, static_shear


def get_static_shear_vector(sign_static, sigt_static, phi, cohesion):
    ## Same function as get_static_shear but on keeping vector form
    ## for visualisation of stress along the sliding line

    tanphi = np.tan(np.pi * np.array(phi) / 180.0)

    available_shear = np.array(sign_static) * tanphi - np.array(cohesion)
    static_shear = np.array(sigt_static)

    return available_shear, static_shear


def get_dynamic_shear(sign1_dyn, sigt1_dyn, phi, cohesion, inst):
    ## Obtain shear for dynamic analysis for FS calculation
    ## All input are considered as vectors definde at each node of the sliding line
    ## Mohr-Coulomb criteria for friction materials
    ##
    ## Input : sign1_static : normal stress  (N)
    ##         sigt1_static : tangential stress (T)
    ##         phi : friction angle (rad) (phi)
    ##         cohesion (c)
    ##         inst : time list from dynamic calculation
    ## Output : available_shear : total shear stress along the slinding line at
    ##                            each time step
    ##                            sum(N*tan(phi)-c)
    ##          static_shear : total shear stress mobilised along the sliding line
    ##                          at each time step
    ##                            sum(T)

    tanphi = np.tan(np.pi * np.array(phi) / 180.0)

    dynamic_shear = []
    available_shear = []
    for jj in range(len(inst)):
        ###### value limited to static result
        #      for j,value in enumerate(sigt1_dyn[jj][0]):
        #        if value > 0:
        #          sigt1_dyn[jj][0][j] = 0
        available_shear.append(np.sum(np.array(sign1_dyn[jj][0]) * tanphi))
        dynamic_shear.append(np.sum(np.array(sigt1_dyn[jj][0])))

    available_shear = np.array(available_shear)
    dynamic_shear = np.array(dynamic_shear)

    return available_shear, dynamic_shear


def get_dynamic_shear_vector(sigt1_dyn, inst):
    ## Same function as get_dynamic_shear but on keeping vector form
    ## for visualisation of stress along the sliding line

    dynamic_shear = []
    for jj in range(len(inst)):
        ###### value limited to static FS
        #      for j,value in enumerate(sigt1_dyn[jj][0]):
        #        if value < 0:
        #          sigt1_dyn[jj][0][j] = 0

        dynamic_shear.append(np.array(sigt1_dyn[jj][0][0]))

    dynamic_shear = np.array(dynamic_shear)

    return dynamic_shear


def get_local_FS(sign, sigt, phi, cohesion):
    ## Obtain local FS values
    ## Can be used as fonction to get Fs values direct on mesh for visualisation
    ## Mohr-Coulomb criteria for friction materials
    ##
    ## Input : sign : normal stress  (N)
    ##         sigt : tangential stress (T)
    ##         phi : friction angle (rad) (phi)
    ##         cohesion (c)
    ##         inst : time list from dynamic calculation
    ## Output : FS : factor of safety defined as : (N*tan(phi)-c)/T

    tanphi = np.tan(np.pi * phi / 180.0)
    static_shear = sign * tanphi - cohesion
    try:
        FS = static_shear / sigt
    except:
        FS = 0.0

    return FS


def getMaterialonNewMesh(chmat, TYPE, pos=None):
    ## Get Material from a given mesh and duplicate on a more reffined mesh
    ## by using MACR_ADAP_MAIL command
    ##
    ## Input : chmat : Material Field (from AFFE_MATERIAU)
    ## Output : NEWMESH : reffined mesh
    ##          NewCHMAT : New Material Field applied on NEWMESH

    posx = pos[0]
    posy = pos[1]
    r = pos[2]

    if TYPE == "MAILLAGE":
        MACR_ADAP_MAIL(
            MAILLAGE_N=chmat.getMesh(),
            MAILLAGE_NP1=CO("NEWMESH"),
            ADAPTATION="RAFFINEMENT_UNIFORME",
        )
    elif TYPE == "CERCLE":
        MACR_ADAP_MAIL(
            MAILLAGE_N=chmat.getMesh(),
            MAILLAGE_NP1=CO("NEWMESH"),
            ADAPTATION="RAFF_DERA_ZONE",
            ZONE=_F(
                TYPE="DISQUE", USAGE="RAFFINEMENT", X_CENTRE=posx, Y_CENTRE=posy, RAYON=1.2 * r
            ),
        )

    mater = []
    # get materials and mesh objects
    MatOnMeshEnt = chmat.getVectorOfPartOfMaterialField()

    # loop on materials
    for mat in MatOnMeshEnt:
        # material
        list_mat = mat.getVectorOfMaterial()
        OriginMat = list_mat[0]

        # necessary only to get material properties
        Matnames = OriginMat.getMaterialNames()

        # group_ma
        meshEnt = mat.getMeshEntity()
        meshNames = meshEnt.getNames()

        mater.append(_F(MATER=(OriginMat,), GROUP_MA=meshNames))

    NewCHMAT = AFFE_MATERIAU(MAILLAGE=NEWMESH, AFFE=mater)

    return NEWMESH, NewCHMAT


def getMeshwithALLGroup(__mail, grpma):
    ## Define mesh group called 'ALL' containing all grpma
    __mail = DEFI_GROUP(
        reuse=__mail,
        MAILLAGE=__mail,
        CREA_GROUP_MA=_F(
            NOM="ALL",
            # TYPE_MAILLE = '2D',
            UNION=grpma,
        ),
    )
    return None


def cleanMeshwithALLGroup(__mail):
    ## Clean mesh group called 'ALL' from __mail
    __mail = DEFI_GROUP(reuse=__mail, MAILLAGE=__mail, DETR_GROUP_MA=_F(NOM=("ALL",)))

    return None


def getMeshwithGLISSEGroupCERCLE(__mail, pos, gname):
    ## Obtain mesh group 'GLISSE 'defining sliding zone on mesh
    ## Used only for CERCLE option
    ## Input : __mail : mesh
    ##         pos : vector with [posx,posy,r]
    ##         gname : group of mesh name of sliding zone
    ## Output : none (as mesh groups are directly available on mesh object on main program)

    posx = pos[0]
    posy = pos[1]
    r = pos[2]

    __mail = DEFI_GROUP(
        reuse=__mail,
        MAILLAGE=__mail,
        CREA_GROUP_MA=_F(
            NOM="GLISSE_",
            # TYPE_MAILLE = '2D',
            OPTION="SPHERE",
            POINT=(posx, posy),
            RAYON=r,
        ),
    )

    __mail = DEFI_GROUP(
        reuse=__mail,
        MAILLAGE=__mail,
        CREA_GROUP_MA=_F(
            NOM=gname,
            # TYPE_MAILLE = '2D',
            INTERSEC=("GLISSE_", "ALL"),
        ),
    )

    __mail = DEFI_GROUP(
        reuse=__mail,
        MAILLAGE=__mail,
        CREA_GROUP_MA=_F(NOM="NGLISSE", TYPE_MAILLE="2D", DIFFE=("ALL", gname)),
    )

    __mail = DEFI_GROUP(
        reuse=__mail, MAILLAGE=__mail, CREA_GROUP_NO=_F(GROUP_MA=("NGLISSE", gname))
    )

    # __mail = DEFI_GROUP(reuse = __mail,
    #           MAILLAGE = __mail,
    #           CREA_GROUP_NO = _F( NOM = 'LIGNE',
    #                               INTERSEC = ('GLISSE','NGLISSE'),),)

    # IMPR_RESU(RESU=_F(MAILLAGE = __mail,),FORMAT='MED',UNITE=22)

    return None


def getMeshwithGLISSEGroupMAILLAGE(__mail, __mail_2, gname):
    ## Obtain mesh group 'GLISSE 'defining sliding zone on mesh
    ## Used only for MAILLAGE option
    ## Input : __mail : struture mesh
    ##         __mail_2 : sliding zone mesh
    ##         gname : group of mesh name of sliding zone
    ## Output : none (as mesh groups are directly available on mesh object on main program)

    DEFI_GROUP(
        reuse=__mail,
        MAILLAGE=__mail,
        CREA_GROUP_NO=_F(
            NOM="GLISSE_",
            OPTION="INCLUSION",
            MAILLAGE_INCL=__mail_2,
            GROUP_MA_INCL="DOMAIN_",
            GROUP_MA="ALL",
            CAS_FIGURE="2D",
        ),
    )

    __mail = DEFI_GROUP(
        reuse=__mail,
        MAILLAGE=__mail,
        CREA_GROUP_MA=_F(
            NOM="GLISSE_", OPTION="APPUI", TYPE_APPUI="AU_MOINS_UN", GROUP_NO="GLISSE_"
        ),
    )

    __mail = DEFI_GROUP(
        reuse=__mail,
        MAILLAGE=__mail,
        CREA_GROUP_MA=_F(
            NOM=gname,
            # TYPE_MAILLE = '2D',
            INTERSEC=("GLISSE_", "ALL"),
        ),
    )

    __mail = DEFI_GROUP(
        reuse=__mail,
        MAILLAGE=__mail,
        CREA_GROUP_MA=_F(NOM="NGLISSE", TYPE_MAILLE="2D", DIFFE=("ALL", gname)),
    )

    __mail = DEFI_GROUP(
        reuse=__mail, MAILLAGE=__mail, CREA_GROUP_NO=_F(GROUP_MA=("NGLISSE", gname))
    )

    return None


def cleanStructureMeshwithCreatedGroup(__mail, TYPE, gname, keep_gname=False):
    ## Clean mesh groups on structure mesh
    ## Input : __mail : structure mesh
    ##          TYPE : "CERCLE or "MAILLAGE"
    ##          gname : group of mesh name of sliding zone
    ##          keep_gname = True to keep gname on mesh, False to delete it

    if keep_gname:
        __mail = DEFI_GROUP(
            reuse=__mail,
            MAILLAGE=__mail,
            DETR_GROUP_MA=_F(NOM=("GLISSE_")),
            DETR_GROUP_NO=_F(NOM=("GLISSE",)),
        )

    else:
        __mail = DEFI_GROUP(
            reuse=__mail,
            MAILLAGE=__mail,
            DETR_GROUP_MA=_F(NOM=(gname, "GLISSE_")),
            DETR_GROUP_NO=_F(NOM=("GLISSE",)),
        )

    __mail = (
        DEFI_GROUP(
            reuse=__mail,
            MAILLAGE=__mail,
            DETR_GROUP_MA=_F(NOM=("NGLISSE")),
            DETR_GROUP_NO=_F(NOM=("NGLISSE")),
        ),
    )

    if TYPE == "MAILLAGE":
        __mail = DEFI_GROUP(reuse=__mail, MAILLAGE=__mail, DETR_GROUP_NO=_F(NOM=("GLISSE_")))

    return None


def cleanRuptureMeshwithCreatedGroup(__mail_1):
    ## Clean mesh groups on sliding zone mesh
    ## Input : __mail_1 : sliding zone mesh

    __mail_1 = DEFI_GROUP(
        reuse=__mail_1,
        MAILLAGE=__mail_1,
        DETR_GROUP_MA=_F(NOM=("RUPTURE", "ALL")),
        DETR_GROUP_NO=_F(NOM=("RUPTURE")),
    )
    __mail_1 = DEFI_GROUP(
        reuse=__mail_1,
        MAILLAGE=__mail_1,
        DETR_GROUP_NO=_F(NOM=("LIGNE_", "DOMAIN_")),
        DETR_GROUP_MA=_F(NOM=("LIGNE_", "DOMAIN_", "DOMAIN_L")),
    )
    return None


def cleanRuptureMeshwithCreatedGroupYASEG(__mail_1, yaseg2, yaseg3):
    ## Clean mesh groups on sliding zone mesh if no slinding line group was given
    ## Input : __mail_1 : sliding zone mesh
    ##        yaseg2 : if SEG2 elements were found
    ##        yaseg3 : if SEG3 elements were found

    if yaseg2:
        __mail_1 = DEFI_GROUP(reuse=__mail_1, MAILLAGE=__mail_1, DETR_GROUP_NO=_F(NOM=("LIGNE_2",)))
    if yaseg3:
        __mail_1 = DEFI_GROUP(reuse=__mail_1, MAILLAGE=__mail_1, DETR_GROUP_NO=_F(NOM=("LIGNE_3",)))

    return None


def linear_function(x, a, b):
    ## Define linear function for ky calculation
    y = a * x + b

    return y


def root_linear_function(a, b, y):
    x = (-b + y) / a

    return x


def slice_array(x, val_min, val_max):
    x = np.array(x)
    filter_array = (x > val_min) & (x < val_max)

    return filter_array


def get_ky_value(FsP, acc, nstd=3):
    ## Obtain ky value from dynamic safety factors and mean acceleration
    ## Input : FsP : list of dynamic safety values
    ##         acc : mean acceleration of sliding zone
    ##         nstd : number of std for linear regression
    ## Output : ay : limit acceleration leading to unitary safty factor

    ## we look at safety factor values around 1
    filter_array = slice_array(FsP, val_min=0.8, val_max=1.2)
    reduced_acce = acc[filter_array]
    reduced_fs = FsP[filter_array]

    # verify if reduced_acce list is empty
    if len(reduced_acce) == 0:
        val_min = min(FsP)
        val_max = max(FsP)
        if val_min > 1.0:
            ay = 1.1 * max(acc)
        elif val_max < 1.0:
            ay = 0.0
    else:
        accN = np.linspace(min(acc), max(acc), 50)
        popt, pcov = curve_fit(linear_function, reduced_acce, reduced_fs)
        fs_nume = linear_function(accN, popt[0], popt[1])
        mean_ay = root_linear_function(popt[0], popt[1], y=1)  # y=1 as root for FS=1
        perr = np.sqrt(np.diag(pcov))
        ## ay is chosen 3 sigma lower from the obtained mean regression value
        ay = root_linear_function(popt[0] - nstd * perr[0], popt[1] - nstd * perr[1], y=1)

    ky = ay / 9.81
    return ky


def post_newmark_ops(self, **args):
    """
    Command to evaluate seismic performance of earth dams and embankments
    for Newamrk approach (sliding block)
    Only available for 2D models
    """

    MasquerAlarme("MODELE1_63")
    MasquerAlarme("MODELE1_64")
    MasquerAlarme("CALCULEL5_48")
    ##sys.stdout.flush() pour vider les #prints

    args = _F(args)
    INFO = args["INFO"]

    ONLY_FS = False
    if args["RESULTAT"] is not None:
        RESULTAT = args["RESULTAT"]
        __model = None
        ### get model from result
        try:
            __model = RESULTAT.getModel()
        except:
            raise NameError("No model")
        __mail = __model.getMesh()
        dim = __mail.getDimension()
        if dim == 3:
            ## 3D models not supported by the command
            UTMESS("F", "POST0_51")
        ## possibly necessary to deal with the case of multiple materials on Result

    else:
        ONLY_FS = True

    if args["RESULTAT_PESANTEUR"] is not None:
        RESULTAT_PESANTEUR = args["RESULTAT_PESANTEUR"]
        __modST = None
        try:
            __modST = RESULTAT_PESANTEUR.getModel()
        except:
            raise NameError("No model")
        ### RECUPERATION DU MAILLAGE DANS LE RESULTAT STATIQUE
        if ONLY_FS:
            __mail = __modST.getMesh()
            dim = __mail.getDimension()
            if dim == 3:
                UTMESS("F", "POST0_51")
        else:
            __mailST = __modST.getMesh()
            dim = __mailST.getDimension()
            if dim == 3:
                UTMESS("F", "POST0_51")

    ### KY coefficient [g]
    if args["KY"] is not None:
        ky = args["KY"]
        ### gravity acceleration
        g = 9.81
        ## critical acceleration
        ay = ky * g

    ### Get mesh groups used on dynamic calculation (defining model)
    grpma = args["GROUP_MA_CALC"]

    ### Get mesh groups used on dynamic calculation (defining model)
    gname = "GLISSE"
    if args["MAILLAGE_RESU"] is not None:
        if args["MAILLAGE_RESU"]["NOM_GROUP"] is not None:
            gname = args["MAILLAGE_RESU"]["NOM_GROUP"]

    ### Position of sliding circle
    fac_cercle = 1.0
    if args["POSITION"] is not None:
        if args["POSITION"] == "AMONT":
            fac_cercle = -1.0

    pos = None
    TYPE = "MAILLAGE"
    getMeshwithALLGroup(__mail, grpma)
    ### Slinding zone defined as circle
    if args["RAYON"] is not None:
        TYPE = "CERCLE"
        r = args["RAYON"]
        posx = args["CENTRE_X"]
        posy = args["CENTRE_Y"]
        pos = [posx, posy, r]

        getMeshwithGLISSEGroupCERCLE(__mail, pos, gname)

        ### Create a disk mesh to compute safety factors
        ### refine value (7) is taken from discretisation used for static FS validation
        raff = 7
        if args["RAFF_CERCLE"] is not None:
            raff = args["RAFF_CERCLE"]
        __mail_1 = Mesh.buildDisk(radius=r, refine=raff)
        __mail_1 = MODI_MAILLAGE(reuse=__mail_1, MAILLAGE=__mail_1, TRANSLATION=(posx, posy))

    if TYPE == "MAILLAGE":
        __mail_1 = args["MAILLAGE_GLIS"]

    __mail_1 = DEFI_GROUP(
        reuse=__mail_1,
        MAILLAGE=__mail_1,
        CREA_GROUP_MA=_F(
            NOM="ALL",
            # TYPE_MAILLE = '2D',
            TOUT="OUI",
        ),
    )

    DEFI_GROUP(
        reuse=__mail_1,
        MAILLAGE=__mail_1,
        CREA_GROUP_NO=_F(
            NOM="DOMAIN_",
            OPTION="INCLUSION",
            MAILLAGE_INCL=__mail,
            GROUP_MA_INCL="ALL",
            GROUP_MA="ALL",
            CAS_FIGURE="2D",
        ),
    )

    DEFI_GROUP(
        reuse=__mail_1,
        MAILLAGE=__mail_1,
        CREA_GROUP_MA=_F(
            NOM="DOMAIN_", OPTION="APPUI", TYPE_APPUI="AU_MOINS_UN", GROUP_NO="DOMAIN_"
        ),
    ),

    if args["GROUP_MA_GLIS"] is not None:
        __mail_1 = DEFI_GROUP(
            reuse=__mail_1,
            MAILLAGE=__mail_1,
            CREA_GROUP_MA=_F(NOM="RUPTURE", UNION=args["GROUP_MA_GLIS"]),
        )

    else:
        __mail_1 = DEFI_GROUP(
            reuse=__mail_1,
            MAILLAGE=__mail_1,
            CREA_GROUP_MA=_F(NOM="RUPTURE", TYPE_MAILLE="2D", TOUT="OUI"),
        )

    __mail_1 = DEFI_GROUP(
        reuse=__mail_1, MAILLAGE=__mail_1, CREA_GROUP_NO=_F(NOM="RUPTURE", GROUP_MA="RUPTURE")
    )

    if args["GROUP_MA_LIGNE"] is not None:
        ma_ligne = args["GROUP_MA_LIGNE"]

    ## In case GROUP_MA_LIGNE not available : all SEG2 and SEG3 meshs are considered
    else:
        seg = []
        yaseg2 = __mail_1.hasCellsOfType("SEG2")
        if yaseg2:
            seg.append("LIGNE_2")
            __mail_1 = DEFI_GROUP(
                reuse=__mail_1,
                MAILLAGE=__mail_1,
                CREA_GROUP_MA=_F(NOM="LIGNE_2", TYPE_MAILLE=("SEG2"), TOUT="OUI"),
            )

        yaseg3 = __mail_1.hasCellsOfType("SEG3")
        if yaseg3:
            seg.append("LIGNE_3")
            __mail_1 = DEFI_GROUP(
                reuse=__mail_1,
                MAILLAGE=__mail_1,
                CREA_GROUP_MA=_F(NOM="LIGNE_3", TYPE_MAILLE=("SEG3"), TOUT="OUI"),
            )

        ma_ligne = seg

    DEFI_GROUP(
        reuse=__mail_1,
        MAILLAGE=__mail_1,
        CREA_GROUP_NO=_F(
            NOM="LIGNE_",
            OPTION="INCLUSION",
            MAILLAGE_INCL=__mail,
            GROUP_MA_INCL="ALL",
            GROUP_MA=ma_ligne,
            CAS_FIGURE="2D",
        ),
    )

    DEFI_GROUP(
        reuse=__mail_1,
        MAILLAGE=__mail_1,
        CREA_GROUP_MA=_F(NOM="LIGNE_", OPTION="APPUI", TYPE_APPUI="SOMMET", GROUP_NO="LIGNE_"),
    ),

    # mesh orientation on slinding line
    __mail_1 = MODI_MAILLAGE(
        reuse=__mail_1,
        MAILLAGE=__mail_1,
        # ORIE_PEAU=_F(GROUP_MA_PEAU=("LIGNE_",), GROUP_MA_INTERNE=("RUPTURE")),
        ORIE_PEAU=_F(GROUP_MA_PEAU=("LIGNE_",), GROUP_MA_INTERNE=("DOMAIN_")),
    )

    DEFI_GROUP(
        reuse=__mail_1,
        MAILLAGE=__mail_1,
        CREA_GROUP_MA=_F(
            NOM="DOMAIN_L", OPTION="APPUI", TYPE_APPUI="AU_MOINS_UN", GROUP_NO="LIGNE_"
        ),
    ),

    ## Restrain sliding mesh to the common zone to the structure mesh to increase numerical performance
    __mail_2 = CREA_MAILLAGE(
        MAILLAGE=__mail_1,  # INFO=2,
        RESTREINT=_F(
            # GROUP_MA=("LIGNE_", "DOMAIN_", "RUPTURE"), GROUP_NO=("LIGNE_", "DOMAIN_", "RUPTURE")
            # GROUP_MA=("LIGNE_", "DOMAIN_", "DOMAIN_L"),
            GROUP_MA=("LIGNE_", "DOMAIN_L"),
            GROUP_NO=("LIGNE_",),
        ),
    )

    IMPR_RESU(RESU=_F(MAILLAGE=__mail_2), FORMAT="MED", UNITE=22)

    __mail_L = CREA_MAILLAGE(
        MAILLAGE=__mail_2, RESTREINT=_F(GROUP_MA=("LIGNE_",), GROUP_NO=("LIGNE_",))  # INFO=2,
    )

    if TYPE == "MAILLAGE":
        getMeshwithGLISSEGroupMAILLAGE(__mail, __mail_1, gname)
    # IMPR_RESU(RESU=_F(MAILLAGE = __mail_2,),FORMAT='MED',UNITE=23)

    ## Restrain sliding mesh to the common zone to the structure mesh to increase numerical performance
    __mail_s = CREA_MAILLAGE(
        MAILLAGE=__mail,  # INFO=2,
        RESTREINT=_F(
            GROUP_MA=(gname),
            # GROUP_NO=("LIGNE_",),
        ),
    )

    ###############################################################################
    ####
    #### SAFETY FACTOR CALCULATION
    ####
    ###############################################################################

    if args["RESULTAT_PESANTEUR"] is not None:
        ## ASSERT necessary if original model other than D_PLAN
        ## model in this case on slinding mesh
        __MODST = AFFE_MODELE(
            MAILLAGE=__mail_2,
            AFFE=(_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="D_PLAN"),),
            VERI_JACOBIEN="NON",
        )
        __MODST2 = AFFE_MODELE(
            MAILLAGE=__mail_s,
            AFFE=(_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="D_PLAN"),),
            VERI_JACOBIEN="NON",
        )

        __MODL = AFFE_MODELE(
            MAILLAGE=__mail_L,
            AFFE=(_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="D_PLAN"),),
            VERI_JACOBIEN="NON",
        )

        ## False material only necessary for CREA_RESU
        ## Stress are true as they are projected from structure mesh
        __MATBID = DEFI_MATERIAU(ELAS=_F(E=1.0, NU=0.3, RHO=1.0))

        __MATST = AFFE_MATERIAU(MAILLAGE=__mail_2, AFFE=_F(MATER=__MATBID, TOUT="OUI"))
        __MATST2 = AFFE_MATERIAU(MAILLAGE=__mail_s, AFFE=_F(MATER=__MATBID, TOUT="OUI"))

        ## Obtain static stress field on the auxiliary model at the sliding mesh
        ## Result with true stresses and flase material for SIRO_ELEM

        __instFS = RESULTAT_PESANTEUR.getAccessParameters()["INST"][-1]

        if args["METHODE"] == "ECLA_PG":
            __CSTPGO = CREA_CHAMP(
                OPERATION="EXTR",
                NOM_CHAM="SIEF_ELGA",
                TYPE_CHAM="ELGA_SIEF_R",
                RESULTAT=RESULTAT_PESANTEUR,
                INST=__instFS,
            )

            __CSTPGF = PROJ_CHAMP(
                METHODE="ECLA_PG",
                CHAM_GD=__CSTPGO,
                MODELE_1=__modST,
                MODELE_2=__MODST,
                CAS_FIGURE="2D",
                PROL_ZERO="OUI",
                #                     DISTANCE_MAX=0.1,
            )

        elif args["METHODE"] == "COLLOCATION":
            __RSTPGF = PROJ_CHAMP(
                METHODE="COLLOCATION",
                RESULTAT=RESULTAT_PESANTEUR,
                MODELE_1=__modST,
                MODELE_2=__MODST2,
                NOM_CHAM="SIEF_NOEU",
                CAS_FIGURE="2D",
                PROL_ZERO="OUI",
                #                     DISTANCE_MAX=0.1,
            )

            __CSTPGN = CREA_CHAMP(
                OPERATION="EXTR",
                NOM_CHAM="SIEF_NOEU",
                TYPE_CHAM="NOEU_SIEF_R",
                RESULTAT=__RSTPGF,
                INST=__instFS,
            )

            __CSTPGO = CREA_CHAMP(
                OPERATION="DISC", TYPE_CHAM="ELGA_SIEF_R", CHAM_GD=__CSTPGN, MODELE=__MODST2
            )

            __CSTPGF = PROJ_CHAMP(
                METHODE="ECLA_PG",
                CHAM_GD=__CSTPGO,
                MODELE_1=__MODST2,
                MODELE_2=__MODST,
                CAS_FIGURE="2D",
                PROL_ZERO="OUI",
                #                     DISTANCE_MAX=0.1,
            )

        ## Static result with SIEF_ELGA obtained at the sliding mesh
        __recoST = CREA_RESU(
            OPERATION="AFFE",
            TYPE_RESU="DYNA_TRANS",
            AFFE=(
                _F(
                    NOM_CHAM="SIEF_ELGA",
                    MODELE=__MODST,
                    CHAM_MATER=__MATST,
                    CHAM_GD=__CSTPGF,
                    INST=0.0,
                ),
            ),
        )

        __recoST = CALC_CHAMP(
            reuse=__recoST,
            RESULTAT=__recoST,
            GROUP_MA="LIGNE_",
            MODELE=__MODST,
            CONTRAINTE=("SIRO_ELEM",),
        )

        ## Get SIRO_ELEM stresses from static calculation
        __CSIST = CREA_CHAMP(
            OPERATION="EXTR",
            NOM_CHAM="SIRO_ELEM",
            TYPE_CHAM="ELEM_SIEF_R",
            RESULTAT=__recoST,
            NUME_ORDRE=1,
        )

        SIGN_stat = __CSIST.getValuesWithDescription("SIG_N", [])
        SIGTN_stat = __CSIST.getValuesWithDescription("SIG_TN", [])

        ## Obtain friction angle phi and cohesion to static analysis
        __chPHNO = PROJ_CHAMP(
            METHODE="COLLOCATION",
            CHAM_GD=args["CHAM_PHI"],
            MAILLAGE_1=__mail,
            MAILLAGE_2=__mail_2,
            PROL_ZERO="OUI",
            #                     DISTANCE_MAX=0.1,
        )

        __chPHEL = CREA_CHAMP(
            OPERATION="DISC",
            CHAM_GD=__chPHNO,
            MODELE=__MODST,
            TYPE_CHAM="ELEM_NEUT_R",
            PROL_ZERO="OUI",
        )

        __chCONO = PROJ_CHAMP(
            METHODE="COLLOCATION",
            CHAM_GD=args["CHAM_COHESION"],
            MAILLAGE_1=__mail,
            MAILLAGE_2=__mail_2,
            PROL_ZERO="OUI",
            #                     DISTANCE_MAX=0.1,
        )

        __chCOEL = CREA_CHAMP(
            OPERATION="DISC",
            CHAM_GD=__chCONO,
            MODELE=__MODST,
            TYPE_CHAM="ELEM_NEUT_R",
            PROL_ZERO="OUI",
            # INFO=2,
        )

        __chCPEL = CREA_CHAMP(
            OPERATION="ASSE",
            TYPE_CHAM="ELEM_NEUT_R",
            MODELE=__MODST,
            PROL_ZERO="OUI",
            ASSE=(
                _F(GROUP_MA="LIGNE_", CHAM_GD=__chPHEL, CUMUL="OUI", COEF_R=1.0),
                _F(GROUP_MA="LIGNE_", CHAM_GD=__chCOEL, CUMUL="OUI", COEF_R=1.0),
            ),
        )

        ## Friction angle phi and cohesion on sliding line
        __chCPLG = PROJ_CHAMP(
            METHODE="COLLOCATION",
            CHAM_GD=__chCPEL,
            MODELE_1=__MODST,
            MODELE_2=__MODL,
            CAS_FIGURE="1.5D",
            PROL_ZERO="OUI",
            INFO=2,
            #                     DISTANCE_MAX=0.1,
        )

        ## Local static safety factor on mesh
        __FstS = FORMULE(
            VALE="get_local_FS(SIG_N,SIG_TN,X1,X2)",
            NOM_PARA=("SIG_N", "SIG_TN", "X1", "X2"),
            get_local_FS=get_local_FS,
        )

        __chSTSF = CREA_CHAMP(
            OPERATION="AFFE",
            TYPE_CHAM="ELEM_NEUT_F",
            MODELE=__MODST,
            PROL_ZERO="OUI",
            AFFE=_F(GROUP_MA="LIGNE_", NOM_CMP="X1", VALE_F=__FstS),
        )

        __chSTSR = CREA_CHAMP(
            TYPE_CHAM="ELEM_NEUT_R",
            OPERATION="EVAL",
            CHAM_F=__chSTSF,
            CHAM_PARA=(__CSIST, __chCPEL),
            INFO=1,
        )

        __chSTSL = PROJ_CHAMP(
            METHODE="COLLOCATION",
            CHAM_GD=__chSTSR,
            MODELE_1=__MODST,
            MODELE_2=__MODL,
            CAS_FIGURE="1.5D",
            PROL_ZERO="OUI",
            INFO=2,
            #                     DISTANCE_MAX=0.1,
        )

        ## Global static safety factor Fsp
        phiL = __chCPLG.getValuesWithDescription("X1", [])
        cohesionL = __chCPLG.getValuesWithDescription("X2", [])

        available_shear, static_shear = get_static_shear(
            SIGN_stat[0], SIGTN_stat[0], phiL[0], cohesionL[0]
        )
        available_shear_v, static_shear_v = get_static_shear_vector(
            SIGN_stat[0], SIGTN_stat[0], phiL[0], cohesionL[0]
        )

        FSp = fac_cercle * available_shear / (static_shear)

        ## Global static safety factor node by node FspL
        FSpL = []
        for k in range(len(available_shear_v)):
            try:
                FSpL.append(fac_cercle * available_shear_v[k] / (static_shear_v[k]))
            except:
                FSpL.append(0.0)

        ## Table for output static safety factor
        if args["RESULTAT"] is None:
            tabini = Table(para=["INST", "FS"], typ=["R", "R"])
            if args["RESULTAT"] is None:
                tabini.append({"INST": 0.0, "FS": FSp})
                self.register_result(__chSTSL, args["CHAM_FS"])

            dprod = tabini.dict_CREA_TABLE()
            tabout = CREA_TABLE(**dprod)

        ################################################################################
        #### FR:
        #### CALCUL FACTEUR DE SECURITE EN DYNAMIQUE (uniquement si RESULTAT_PESANTEUR est fourni)
        #### Dans ce cas, il faut qu'une phase statique prélable au calcul dynamique soit
        #### réalisé, afin que les contraintes du résultat dynamique intégrent les
        #### contraintes statiques
        ####
        #### EN:
        #### DYNAMIC SAFETY FACTOR CALCULATION (only if RESULTAT_PESANTEUR is available)
        #### In this case, a static analysis previously conduct to the dynamic analysis is
        #### necessary, as to integrated statci stresses to the dyanmic results
        ################################################################################

        ##### Only with sliding mesh
        if args["RESULTAT"] is not None:
            __MODYN = AFFE_MODELE(
                MAILLAGE=__mail_2,
                AFFE=(_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="D_PLAN"),),
                VERI_JACOBIEN="NON",
            )
            __MODYNS = AFFE_MODELE(
                MAILLAGE=__mail_s,
                AFFE=(_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="D_PLAN"),),
                VERI_JACOBIEN="NON",
            )

            ## False material only necessary for CREA_RESU
            ## Stress are true as they are projected from structure mesh
            __MATBIDD = DEFI_MATERIAU(ELAS=_F(E=1.0, NU=0.3, RHO=1.0))

            __MATDYN = AFFE_MATERIAU(MAILLAGE=__mail_2, AFFE=_F(MATER=__MATBIDD, TOUT="OUI"))
            __MATDYNS = AFFE_MATERIAU(MAILLAGE=__mail_s, AFFE=_F(MATER=__MATBIDD, TOUT="OUI"))

            __instSD = RESULTAT.getAccessParameters()["INST"]

            ## Create dynamic result with stresses from structure mesh using ECLA_PG projection
            ## on slinding mesh
            if args["METHODE"] == "ECLA_PG":
                __recoSD = PROJ_CHAMP(
                    METHODE="ECLA_PG",
                    RESULTAT=RESULTAT,
                    MODELE_1=__model,
                    MODELE_2=__MODYN,
                    CAS_FIGURE="2D",
                    PROL_ZERO="OUI",
                    TOUT_ORDRE="OUI",
                    NOM_CHAM="SIEF_ELGA",
                )
            ## Loop to create dynamic result with stresses from structure mesh using COLLOCATION projection
            ## on slinding mesh
            ## faster but possibly more imprecise results
            if args["METHODE"] == "COLLOCATION":
                __RSDPGF = PROJ_CHAMP(
                    METHODE="COLLOCATION",
                    RESULTAT=RESULTAT,
                    MODELE_1=__model,
                    MODELE_2=__MODYN,
                    # VIS_A_VIS=_F(GROUP_MA_1="GLISSE", GROUP_MA_2="GLISSE"),
                    NOM_CHAM="SIEF_NOEU",
                    CAS_FIGURE="2D",
                    PROL_ZERO="OUI",
                    #                     DISTANCE_MAX=0.1,
                )

                __CSDPGI = CREA_CHAMP(
                    OPERATION="EXTR",
                    NOM_CHAM="SIEF_NOEU",
                    TYPE_CHAM="NOEU_SIEF_R",
                    RESULTAT=__RSDPGF,
                    INST=__instSD[0],
                )

                __CSDPGO = CREA_CHAMP(
                    OPERATION="DISC", TYPE_CHAM="ELGA_SIEF_R", CHAM_GD=__CSDPGI, MODELE=__MODYN
                )

                ## Create dynamic result with SIEF_ELGA on sliding mesh
                __recoSD = CREA_RESU(
                    OPERATION="AFFE",
                    TYPE_RESU="DYNA_TRANS",
                    AFFE=(
                        _F(
                            NOM_CHAM="SIEF_ELGA",
                            MODELE=__MODYN,
                            CHAM_MATER=__MATDYN,
                            CHAM_GD=__CSDPGO,
                            INST=__instSD[0],
                        ),
                    ),
                )
                for inst in __instSD[1:]:

                    ## Loop to create dynamic result with stresses from structure mesh using ECLA_PG projection
                    ## on sliding mesh
                    __CSDPGI = CREA_CHAMP(
                        OPERATION="EXTR",
                        NOM_CHAM="SIEF_NOEU",
                        TYPE_CHAM="NOEU_SIEF_R",
                        RESULTAT=__RSDPGF,
                        INST=inst,
                    )
                    __CSDPGO = CREA_CHAMP(
                        OPERATION="DISC", TYPE_CHAM="ELGA_SIEF_R", CHAM_GD=__CSDPGI, MODELE=__MODYN
                    )

                    __recoSD = CREA_RESU(
                        reuse=__recoSD,
                        RESULTAT=__recoSD,
                        OPERATION="AFFE",
                        TYPE_RESU="DYNA_TRANS",
                        AFFE=(
                            _F(
                                NOM_CHAM="SIEF_ELGA",
                                MODELE=__MODYN,
                                CHAM_MATER=__MATDYN,
                                CHAM_GD=__CSDPGO,
                                INST=inst,
                            ),
                        ),
                    )

            ## In case static analysis was performed, dynamic safety factor can be calculated
            if args["RESULTAT_PESANTEUR"] is not None:
                ## Obtain SIRO_ELEM on sliding line
                __recoSD = CALC_CHAMP(
                    reuse=__recoSD,
                    RESULTAT=__recoSD,
                    GROUP_MA="LIGNE_",
                    MODELE=__MODYN,
                    CONTRAINTE=("SIRO_ELEM",),
                )

                ## Get normal and shear stresses at the sliding line at each time step
                SIGN_dyn = []
                SIGT_dyn = []

                for inst in __instSD:
                    # print ("Instant de calcul = "+str(inst))

                    __CSISD = CREA_CHAMP(
                        OPERATION="EXTR",
                        NOM_CHAM="SIRO_ELEM",
                        TYPE_CHAM="ELEM_SIEF_R",
                        RESULTAT=__recoSD,
                        INST=inst,
                    )

                    SIGN_dyna = __CSISD.getValuesWithDescription("SIG_N", [])
                    SIGTN_dyna = __CSISD.getValuesWithDescription("SIG_TN", [])

                    SIGN_dyn.append(SIGN_dyna)
                    SIGT_dyn.append(SIGTN_dyna)

                ## Available and mobilized stresses at the slinding line
                available_shear_dyn, dynamic_shear = get_dynamic_shear(
                    SIGN_dyn, SIGT_dyn, phiL[0], cohesionL[0], __instSD
                )
                dynamic_shear_v = get_dynamic_shear_vector(SIGT_dyn, __instSD)

                shear_factor = 1.0
                # if args["RESULTAT"].getType().lower() == "dyna_trans":
                #     shear_factor = np.sqrt(2.0)
                #     shear_factor = 1.0

                ## Dynamic safety factor defined as considering dynamic variation
                ## of available shear
                FSp = (
                    fac_cercle
                    * (available_shear - available_shear_dyn)
                    / (static_shear - shear_factor * dynamic_shear)
                )

                ## Dynamic safety factor neglecting dynamic variation of available shear
                ## (static value is considered)
                # FSp = (
                #     fac_cercle
                #     * (available_shear)
                #     / (static_shear - shear_factor * dynamic_shear)
                # )

                ## Global static safety factor node by node FspL
                FSpL = []
                for k in range(len(available_shear_v)):
                    try:
                        FSpL.append(
                            fac_cercle
                            * available_shear_v[k]
                            / (static_shear_v[k] - shear_factor * dynamic_shear_v[k])
                        )
                    except:
                        FSpL.append(0.0)

                tabini = Table(para=["INST", "FS"], typ=["R", "R"])

                ## Table for output dynamic safety factor
                for j in range(len(__instSD)):
                    tabini.append({"INST": __instSD[j], "FS": FSp[j]})

                dprod = tabini.dict_CREA_TABLE()
                __TFS = CREA_TABLE(**dprod)

    ###############################################################################
    ####
    #### NEWMARK ANALYSIS FOR DYNAMIC RESULTS
    ####
    ###############################################################################

    if args["RESULTAT"] is not None:
        ## Some mesh group definitions on structure mesh to obtain center of mass of sliding zone
        ## Mass obtained from GROUPE_MA 'GLISSE'

        __tabmas = POST_ELEM(RESULTAT=RESULTAT, MASS_INER=_F(GROUP_MA=gname))

        masse = __tabmas["MASSE", 1]

        cdgx = __tabmas["CDG_X", 1]
        cdgy = __tabmas["CDG_Y", 1]

        VERIF_MASSE = args["VERI_MASSE"]
        __ch_mat = RESULTAT.getMaterialField()

        ## Mass verification option as it depends on mesh discretisation
        if VERIF_MASSE == "OUI":
            if (__ch_mat is None) and (args["CHAM_MATER"] is None):
                UTMESS("A", "POST0_52")
                VERIF_MASSE = "NON"

        if VERIF_MASSE == "OUI":
            if __ch_mat is not None:
                CHMAT = __ch_mat
            else:
                CHMAT = args["CHAM_MATER"]

            ## Iterative loop for mesh refinement and mass calculation on reffined mesh

            if INFO == 2:
                text = "Remaillage activé pour estimation de la masse de la zone qui glisse"
                aster.affiche("MESSAGE", text)

            iterat = 1
            #        Newmeshs=[]
            #        Newmeshs.append(__mail)
            CHMATs = []
            CHMATs.append(CHMAT)
            masses = []
            masses.append(masse)
            error = 1.0
            while (error > args["RESI_RELA"]) and (iterat < args["ITER_MAXI"] + 1):
                cleanStructureMeshwithCreatedGroup(__mail, TYPE, gname)

                NewMesh, CHMAT = getMaterialonNewMesh(CHMATs[-1], TYPE, pos)
                CHMATs.append(CHMAT)
                __MODMAT = AFFE_MODELE(
                    MAILLAGE=NewMesh,
                    AFFE=(_F(TOUT="OUI", PHENOMENE="MECANIQUE", MODELISATION="D_PLAN"),),
                    VERI_JACOBIEN="NON",
                )

                if TYPE == "CERCLE":
                    getMeshwithGLISSEGroupCERCLE(NewMesh, pos, gname)

                elif TYPE == "MAILLAGE":
                    getMeshwithGLISSEGroupMAILLAGE(NewMesh, __mail_2, gname)

                __tabmas = POST_ELEM(
                    CHAM_MATER=CHMAT, MODELE=__MODMAT, MASS_INER=_F(GROUP_MA=gname)
                )

                masses.append(__tabmas["MASSE", 1])
                cdgx = __tabmas["CDG_X", 1]
                cdgy = __tabmas["CDG_Y", 1]
                error = abs((masses[-1] - masses[-2]) / masses[-1])
                if INFO == 2:
                    text = "Iteration : " + str(iterat)
                    aster.affiche("MESSAGE", text)
                    text = "Erreur relative = " + str(error)
                    aster.affiche("MESSAGE", text)

                iterat = iterat + 1

            masse = masses[-1]
            if TYPE == "CERCLE":
                getMeshwithGLISSEGroupCERCLE(__mail, pos, gname)

            elif TYPE == "MAILLAGE":
                getMeshwithGLISSEGroupMAILLAGE(__mail, __mail_2, gname)

            if args["MAILLAGE_RESU"] is not None:
                if args["MAILLAGE_RESU"]["MAILLAGE_MASSE"] is not None:
                    self.register_result(NewMesh, args["MAILLAGE_RESU"]["MAILLAGE_MASSE"])

        ##############################################################################
        ##   Method : Mean acceleration obtained as force over mass of the sliding zone
        ##############################################################################

        ## SIEF_ELGA field need to be obtained by the user
        ## Force along the slinding line from dynamic analysis

        __RESU3 = CALC_CHAMP(
            RESULTAT=RESULTAT,
            MODELE=__model,
            CHAM_MATER=__ch_mat,
            FORCE=("FORC_NODA"),
            GROUP_MA=(gname),
        )

        __tabFLI = POST_RELEVE_T(
            ACTION=_F(
                INTITULE="RESU",
                OPERATION="EXTRACTION",
                GROUP_NO="NGLISSE",
                RESULTANTE=("DX", "DY"),
                RESULTAT=__RESU3,
                NOM_CHAM="FORC_NODA",
            )
        )

        ################################################################################
        ####
        #### CACUL DE L'ACCELERATION MOYENNE A PARTIR DE LA RESULTANTE ET DE LA MASSE
        #### DE LA ZONE DE GLISSEMENT
        ####
        ################################################################################

        fresu = __tabFLI.EXTR_TABLE()
        forcex = fresu.values()["DX"]
        forcey = fresu.values()["DY"]
        time = fresu.values()["INST"]

        accyFLI = fac_cercle * np.array(forcey) / masse
        accxFLI = fac_cercle * np.array(forcex) / masse

        __accyFL = (
            DEFI_FONCTION(
                NOM_RESU="ACCE_MOY", NOM_PARA="INST", ABSCISSE=time, ORDONNEE=list(accyFLI)
            ),
        )

        __accxFL = (
            DEFI_FONCTION(
                NOM_RESU="ACCE_MOY", NOM_PARA="INST", ABSCISSE=time, ORDONNEE=list(accxFLI)
            ),
        )

        ## In case of MONO_APUI calculation is performed, dynamic calculation performed on relative basis
        ## and need to calculate total acceleration (as being the sum of relative + entrainement accelerations)
        ## This wave modeling approach is not recommended
        # if args["ACCE_ENTRAINEMENT"] is not None:
        #     foncx = args["ACCE_ENTRAINEMENT"].Ordo()
        #     timex = args["ACCE_ENTRAINEMENT"].Absc()
        #     ## Interpolation to get same time steps on dynamic and input acceleration
        #     foncxx = np.interp(time, timex, foncx)
        #     time = np.array(time)
        #     accxFLI = accxFLI + foncxx

        #     __accxFL = (
        #         DEFI_FONCTION(
        #             NOM_RESU="ACCE_MOY",
        #             NOM_PARA="INST",
        #             ABSCISSE=list(time),
        #             ORDONNEE=list(accxFLI),
        #         ),
        #     )

        ###############################################################################
        ##  Obtain irreversible displacements from mean acceleration
        ##############################################################################

        acc = accxFLI

        ## verify if ky is given, otherwise obtain it from dynamic safety factor
        if args["RESULTAT_PESANTEUR"] is not None:
            if args["KY"] is None:
                nstd = 3.0
                if args["NB_ECART_TYPE"] is not None:
                    nstd = args["NB_ECART_TYPE"]
                aster.affiche("MESSAGE", "NB_ECART_TYPE = " + str(args["NB_ECART_TYPE"]))

                ky = get_ky_value(FSp, acc, nstd)
                ay = ky * 9.81

                tabini = Table(para=["INST", "KY"], typ=["R", "R"])
                ## Table for output critical acceleration
                for j in range(len(__instSD)):
                    tabini.append({"INST": __instSD[j], "KY": ky})
                dprod = tabini.dict_CREA_TABLE()
                __TKY = CREA_TABLE(**dprod)

                if INFO == 2:
                    text = "Accélération critique : " + str(ky) + " g"
                    aster.affiche("MESSAGE", text)

        ## Velocity calculation imposing ay value on accelerations and
        ## Then imposes velocity always positive
        acc = acc - ay
        vite = list([0])
        for i in range(1, len(time)):
            deltav = (acc[i] + acc[i - 1]) * (time[i] - time[i - 1]) * 0.5
            viteaux = np.max([0, vite[i - 1] + deltav])
            vite.append(viteaux)

        __vitAF = (
            DEFI_FONCTION(NOM_RESU="VITE", NOM_PARA="INST", ABSCISSE=time, ORDONNEE=list(vite)),
        )

        __deplAF = CALC_FONCTION(INTEGRE=_F(FONCTION=__vitAF))

        ## Output table

        __tabvAF = CREA_TABLE(FONCTION=_F(FONCTION=__vitAF))
        __tabdAF = CREA_TABLE(FONCTION=_F(FONCTION=__deplAF))

        tabout = CREA_TABLE(FONCTION=_F(FONCTION=__accxFL))

        act_table = []
        act_table.append(_F(OPERATION="COMB", TABLE=__tabvAF, NOM_PARA="INST"))
        act_table.append(_F(OPERATION="COMB", TABLE=__tabdAF, NOM_PARA="INST"))

        tabout = CALC_TABLE(reuse=tabout, TABLE=tabout, ACTION=act_table)

        if args["RESULTAT_PESANTEUR"] is not None:
            tabout = CALC_TABLE(
                TABLE=tabout, ACTION=_F(OPERATION="COMB", TABLE=__TFS, NOM_PARA="INST")
            )
            if args["KY"] is None:
                tabout = CALC_TABLE(
                    TABLE=tabout, ACTION=_F(OPERATION="COMB", TABLE=__TKY, NOM_PARA="INST")
                )

    ## Cleaning of mesh groups created in the command

    cleanMeshwithALLGroup(__mail)

    if args["MAILLAGE_RESU"] is not None:
        if args["MAILLAGE_RESU"]["MAILLAGE"] is not None:
            cleanStructureMeshwithCreatedGroup(__mail, TYPE, gname, keep_gname=True)
            mail_out = CREA_MAILLAGE(
                MAILLAGE=__mail,
                RESTREINT=_F(
                    GROUP_MA=__mail.getGroupsOfCells(), GROUP_NO=__mail.getGroupsOfNodes()
                ),
            )
            self.register_result(mail_out, args["MAILLAGE_RESU"]["MAILLAGE"])
            __mail = DEFI_GROUP(reuse=__mail, MAILLAGE=__mail, DETR_GROUP_MA=_F(NOM=(gname)))
        else:
            cleanStructureMeshwithCreatedGroup(__mail, TYPE, gname, keep_gname=False)
    else:
        cleanStructureMeshwithCreatedGroup(__mail, TYPE, gname, keep_gname=False)

    if TYPE == "MAILLAGE":
        cleanRuptureMeshwithCreatedGroup(__mail_1)
        if args["GROUP_MA_LIGNE"] is None:
            cleanRuptureMeshwithCreatedGroupYASEG(__mail_1, yaseg2, yaseg3)

    RetablirAlarme("MODELE1_63")
    RetablirAlarme("MODELE1_64")
    RetablirAlarme("CALCULEL5_48")
    return tabout
