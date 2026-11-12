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

from ...Cata.Syntax import _F
from ...Messages import UTMESS
from ...CodeCommands import CREA_TABLE, POST_ELEM, CREA_CHAMP, PROD_MATR_CHAM


def getGravityCenter(model, cara, mater, group_ma):
    """
    Calculation of the gravity center

    Arguments:
        model (model): model associated to the mode_meca object
        cara (cara_elem): Elementary caracteristics associated to the mode_meca object
        mater (cham_mater): Material field associated to the mode_meca object
        group_ma (grma) : groups of elements
    Returns:
        float(3) : coordinates of gravity center
    """

    if cara is not None:
        Mass_Iner = POST_ELEM(
            MODELE=model, CARA_ELEM=cara, CHAM_MATER=mater, MASS_INER=_F(GROUP_MA=group_ma)
        )
    else:
        Mass_Iner = POST_ELEM(
            MODELE=model, CARA_ELEM=cara, CHAM_MATER=mater, MASS_INER=_F(GROUP_MA=group_ma)
        )

    Mass_Tot = Mass_Iner.EXTR_TABLE().values()

    if len(group_ma) > 1:
        for i1, lieu in enumerate(Mass_Tot["LIEU"]):
            if lieu == "UNION_GROUP_MA":
                ind = i1
                break
    else:
        ind = 0

    centerCoord = [Mass_Tot["CDG_%s" % d][ind] for d in ["X", "Y", "Z"]]

    return centerCoord


def getNodesFromGroups(mesh, group_ma):
    """
    Get list of nodes associated to the groupes of elements

    Arguments:
        mesh (mesh): mesh associated to the mode_meca object
        group_ma (grma) : groups of elements
    Returns:
        Nodes (list of int) : list of node numbers
    """
    Nodes = []
    for name in group_ma:
        Nodes += mesh.getNodesFromCells(group_name=name, localNumbering=True)

    Nodes = list(set(Nodes))

    return Nodes


def getRigidBodyModes(dofNumbering, group_ma, centerCoord):
    """

    Build the 6 rigid body modes :
    - 3 translation modes
    - 3 rotation modes around the point centerCoord

    Arguments:
        dofNumbering : dof numbering (NUME_DDL)
        group_ma (grma) : groups of elements
        centerCoord : coordinates of the rotation center

    Returns:
        rigidModesFields : list of 6 FieldsOnNodes
        excludedDOF : list of dofId not on the groups
    """
    model = dofNumbering.getModel()
    mesh = model.getMesh()

    nbMeshNodes = mesh.getNumberOfNodes()
    nodesCoordinates = np.asarray(mesh.getCoordinates().getValues())
    nodesCoordinates = nodesCoordinates.reshape((nbMeshNodes, 3))

    # Build rigid modes on all nodes and 6 componants (even if componant doesn't exist)
    rigidModesOnMesh = np.zeros((6 * nbMeshNodes, 6))
    rigidModesOnMesh[::6, 0] += 1.0  # -- Trans. X
    rigidModesOnMesh[1::6, 1] += 1.0  # -- Trans. Y
    rigidModesOnMesh[2::6, 2] += 1.0  # -- Trans. Z
    # -- Rot. X
    rigidModesOnMesh[3::6, 3] += 1.0
    rigidModesOnMesh[1::6, 3] -= nodesCoordinates[:, 2] - centerCoord[2]
    rigidModesOnMesh[2::6, 3] += nodesCoordinates[:, 1] - centerCoord[1]
    # -- Rot. Y
    rigidModesOnMesh[4::6, 4] += 1.0
    rigidModesOnMesh[2::6, 4] -= nodesCoordinates[:, 0] - centerCoord[0]
    rigidModesOnMesh[0::6, 4] += nodesCoordinates[:, 2] - centerCoord[2]
    # -- Rot. Z
    rigidModesOnMesh[5::6, 5] += 1.0
    rigidModesOnMesh[1::6, 5] += nodesCoordinates[:, 0] - centerCoord[0]
    rigidModesOnMesh[0::6, 5] -= nodesCoordinates[:, 1] - centerCoord[1]

    # Filter rigid modes on groups
    selectedNodes = getNodesFromGroups(mesh, group_ma)
    meshNodes = mesh.getNodes(localNumbering=True)

    Eqn = dofNumbering.getEquationNumbering()
    if isinstance(Eqn, tuple) | isinstance(Eqn, list):
        Equ = Eqn[0]

    dicDOF = Eqn.getDOFFromNodeAndComponentId()
    # {(NodeId,CompId) : eqId}
    # First DOF/eqId Id is 0
    # Fisrt NodeId is 0
    # Fisrt Componant Id is 1

    # pseudo DOF numbering (100*NodeId + CompId) is used if a node has more than 6 DOFs
    # associate pseudo DOF to six components DOFs numbering (6*no+ icomp) used in rigidModesOnMesh
    pseudoToSixCompDOFs = {
        100 * no + j1 + 1: 6 * i1 + j1 for i1, no in enumerate(meshNodes) for j1 in range(6)
    }
    # list of pseudo DOF of the groups (used if a node has more than 6 DOFs)
    selectedPseudoDOFs = [
        100 * no + j1 + 1 for i1, no in enumerate(selectedNodes) for j1 in range(6)
    ]
    # associate pseudo DOF to real DOF Id (from EquationNumbering)
    pseudoToRealDOFs = {100 * k[0] + k[1]: dicDOF[k] for k in dicDOF.keys()}

    selectedRealDOFs = []
    selectedSixCompDOFs = []

    # build the list of select groups dof Id : selectedRealDOFs
    # build the list of select groups rigidModesOnMesh Id : selectedSixCompDOFs
    for pseudoDof in selectedPseudoDOFs:
        if pseudoDof in pseudoToRealDOFs:
            selectedRealDOFs.append(pseudoToRealDOFs[pseudoDof])
            selectedSixCompDOFs.append(pseudoToSixCompDOFs[pseudoDof])

    nbDOF = dofNumbering.getNumberOfDOFs()
    # list of dofIds not on the groups
    excludedDOF = list(set(np.arange(nbDOF)).difference(selectedRealDOFs))
    excludedDOF.sort()

    rigidModesOnSelectedNodes = np.zeros((nbDOF, 6))
    rigidModesOnSelectedNodes[selectedRealDOFs, :] = rigidModesOnMesh[selectedSixCompDOFs, :]

    rigidModesFields = [None] * 6
    for idir in range(6):
        # create a fieldOnNodes
        rigidModesFields[idir] = CREA_CHAMP(
            MODELE=model,
            NUME_DDL=dofNumbering,
            PROL_ZERO="OUI",
            OPERATION="AFFE",
            TYPE_CHAM="NOEU_DEPL_R",
            AFFE=(_F(TOUT="OUI", NOM_CMP="DX", VALE=0.0),),
        )
        # add values
        rigidModesFields[idir].setValues(rigidModesOnSelectedNodes[:, idir])

    return rigidModesFields, excludedDOF


def getModalMassIner(MODES, rigidBodyFields, excludedDOF, MASSE):
    """

    Calculation of the 'local' modal masses and inertias of the modes MODES with respect to the mass matrix MASSE,
    around the centerCoord point

    Arguments:
        MODES : mode_meca object
        rigidBodyFields : list of 6 fieldOnNodes
        excludedDOF : list of excluded DOFs
        MASSE : mass matrix

    Returns:
        table

    """

    nume_ddl = MODES.getDOFNumbering()
    model = nume_ddl.getModel()

    nbRigidModes = 6
    npMatrix = MASSE.toNumpy()
    # -- Product M * Ud
    M_Ud = [None] * nbRigidModes
    for n in range(nbRigidModes):
        M_Ud[n] = PROD_MATR_CHAM(MATR_ASSE=MASSE, CHAM_NO=rigidBodyFields[n])

    # -- directional global masse

    directionalglobalMasses = np.zeros(6)

    for n in range(nbRigidModes):
        fi = rigidBodyFields[n].getValues()
        ve = M_Ud[n].getValues()
        directionalglobalMasses[n] = np.dot(fi, ve)

    # -- normalization of modes with respect to the mass matrix to get modal generalized masses

    nbModes = MODES.getNumberOfIndexes()
    geneMassesSqrt = np.zeros(nbModes)
    for m in range(nbModes):
        phi = np.asarray(MODES.getField("DEPL", m + 1).getValues())
        phi[excludedDOF] = 0.0
        MphiVale = np.dot(npMatrix, phi)
        # MphiVale[excludedDOF] = 0.0

        geneMassesSqrt[m] = np.dot(phi, MphiVale)
        if geneMassesSqrt[m] > 0:
            geneMassesSqrt[m] = np.sqrt(geneMassesSqrt[m])

    # -- products Phi^T * (M * Ud)
    # -- division by generalized mass

    valeEffeUnit = np.zeros((nbModes, 6))
    valeEffe = np.zeros((nbModes, 6))
    for n in range(nbRigidModes):
        MUd = np.asarray(M_Ud[n].getValues())
        # mass matrix transformation to be "local" (approximation)
        MUd[excludedDOF] = 0.0
        Vale = np.zeros(nbModes)
        for m in range(nbModes):
            phi = MODES.getField("DEPL", m + 1).getValues()
            if geneMassesSqrt[m] > 0:
                Vale[m] = np.dot(MUd, phi) / geneMassesSqrt[m]
            else:
                Vale[m] = np.dot(MUd, phi)

        valeEffe[:, n] = [Val**2 for Val in Vale]
        if directionalglobalMasses[n] > 0:
            valeEffeUnit[:, n] = valeEffe[:, n] / directionalglobalMasses[n]
        else:
            valeEffeUnit[:, n] = valeEffe[:, n]

    table = CREA_TABLE(
        LISTE=(
            _F(LISTE_I=MODES.getAccessParameters()["NUME_ORDRE"], PARA="NUME_ORDRE"),
            _F(LISTE_I=MODES.getAccessParameters()["NUME_MODE"], PARA="NUME_MODE"),
            _F(LISTE_R=MODES.getAccessParameters()["FREQ"], PARA="FREQ"),
            _F(LISTE_R=valeEffe[:, 0], PARA="MASS_EFFE_DX"),
            _F(LISTE_R=valeEffe[:, 1], PARA="MASS_EFFE_DY"),
            _F(LISTE_R=valeEffe[:, 2], PARA="MASS_EFFE_DZ"),
            _F(LISTE_R=valeEffe[:, 3], PARA="INER_EFFE_DX"),
            _F(LISTE_R=valeEffe[:, 4], PARA="INER_EFFE_DY"),
            _F(LISTE_R=valeEffe[:, 5], PARA="INER_EFFE_DZ"),
            _F(LISTE_R=valeEffeUnit[:, 0], PARA="MASS_EFFE_UN_DX"),
            _F(LISTE_R=valeEffeUnit[:, 1], PARA="MASS_EFFE_UN_DY"),
            _F(LISTE_R=valeEffeUnit[:, 2], PARA="MASS_EFFE_UN_DZ"),
            _F(LISTE_R=valeEffeUnit[:, 3], PARA="INER_EFFE_UN_DX"),
            _F(LISTE_R=valeEffeUnit[:, 4], PARA="INER_EFFE_UN_DY"),
            _F(LISTE_R=valeEffeUnit[:, 5], PARA="INER_EFFE_UN_DZ"),
        )
    )

    return table


def post_mode_ops(self, MODE, GROUP_MA, MATR_MASS, CARA_ELEM=None):
    """
    Macro-command POST_MODE
    """

    nume_ddl = MODE.getDOFNumbering()
    model = nume_ddl.getModel()

    mater = None
    cara = CARA_ELEM

    mater = MODE.getMaterialField()

    if mater is None:
        UTMESS("F", "MODAL_25")

    group_ma = GROUP_MA
    t_list = isinstance(group_ma, list)
    t_tuple = isinstance(group_ma, tuple)
    if (not t_list) & (not t_tuple):
        group_ma = (group_ma,)

    gravityCenter = getGravityCenter(model, cara, mater, group_ma)
    rigidBodyFields, excludedDOF = getRigidBodyModes(nume_ddl, group_ma, gravityCenter)
    table = getModalMassIner(MODE, rigidBodyFields, excludedDOF, MATR_MASS)

    return table
