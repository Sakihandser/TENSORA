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

from libaster import deleteTemporaryObjects, setFortranLoggingLevel, resetFortranLoggingLevel

from ..Cata.Syntax import _F
from ..Messages import UTMESS
from ..Objects import ExternalStateVariable, MaterialField, EvolutionParameter, EntityType
from ..Utilities import force_list


def affe_materiau_ops(self, **args):
    """Execute the command.

    Arguments:
        **args (dict): User's keywords.
    """

    args = _F(args)

    setFortranLoggingLevel(args["INFO"])

    # create result
    mesh = None
    model = args.get("MODELE")
    if "MAILLAGE" in args:
        mesh = args["MAILLAGE"]
    else:
        mesh = model.getMesh()
    material = MaterialField(mesh)
    if model is not None:
        material.setModel(model)

    fkw = args.get("AFFE")

    # Retrieve the materials from a given material field
    if fkw is None:
        refMaterialField = args.get("CHAM_MATER")
        assert refMaterialField is not None
        if refMaterialField.getMesh() is not mesh:
            para_msg = (
                refMaterialField.getMesh().getName(),
                refMaterialField.getName(),
                mesh.getName(),
            )
            UTMESS("F", "MATERIAL2_60", valk=para_msg)
        if refMaterialField.hasExternalStateVariable():
            UTMESS("A", "MATERIAL2_61", valk=refMaterialField.getName())
        fkw = []
        for lmat, meshEntity in refMaterialField.getMaterialsOnMeshEntities():
            entityType = meshEntity.getType()
            if entityType == EntityType.AllMeshEntitiesType:
                fkw.append(dict(TOUT="OUI", MATER=lmat))
            elif entityType == EntityType.GroupOfCellsType:
                fkw.append(dict(GROUP_MA=meshEntity.getNames(), MATER=lmat))
            else:
                raise AssertionError
        assert len(fkw) > 0

    if isinstance(fkw, dict):
        _addMaterial(material, fkw)
    elif type(fkw) in (list, tuple):
        for curDict in fkw:
            _addMaterial(material, curDict)
    else:
        raise TypeError("Unexpected type: {0!r} {1}".format(fkw, type(fkw)))

    fkw = args.get("AFFE_COMPOR")
    if fkw is not None:
        if isinstance(fkw, dict):
            _addBehaviour(material, fkw)
        elif type(fkw) in (list, tuple):
            for curDict in fkw:
                _addBehaviour(material, curDict)
        else:
            raise TypeError("Unexpected type: {0!r} {1}".format(fkw, type(fkw)))

    fkw = args.get("AFFE_VARC")
    if fkw is not None:
        if isinstance(fkw, dict):
            _addExternalStateVariables(material, fkw, mesh)
        elif type(fkw) in (list, tuple):
            for curDict in fkw:
                _addExternalStateVariables(material, curDict, mesh)
        else:
            raise TypeError("Unexpected type: {0!r} {1}".format(fkw, type(fkw)))

    material.build()

    resetFortranLoggingLevel()
    deleteTemporaryObjects()

    return material


def _addBehaviour(material, fkw):
    kwTout = fkw.get("TOUT")
    kwGrMa = fkw.get("GROUP_MA")
    compor = fkw["COMPOR"]

    if kwTout is not None:
        material.addBehaviourOnMesh(compor)
    elif kwGrMa is not None:
        kwGrMa = force_list(kwGrMa)
        material.addBehaviourOnGroupOfCells(compor, kwGrMa)
    else:
        raise TypeError("At least {0} or {1} is required".format("TOUT", "GROUP_MA"))


def _addExternalStateVariables(material, fkw, mesh):
    kwTout = fkw.get("TOUT")
    kwGrMa = fkw.get("GROUP_MA")
    nomVarc = fkw["NOM_VARC"]
    chamGd = fkw.get("CHAM_GD")
    evol = fkw.get("EVOL")
    grp = None

    # Construct main object
    if kwTout is not None:
        externalVar = createExternalStateVariable(fkw, nomVarc, mesh, kwTout, grp)
        material.addExternalStateVariable(externalVar)
    elif kwGrMa is not None:
        kwGrMa = force_list(kwGrMa)
        for grp in kwGrMa:
            externalVar = createExternalStateVariable(fkw, nomVarc, mesh, kwTout, grp)
            material.addExternalStateVariable(externalVar)
    else:
        externalVar = createExternalStateVariable(fkw, nomVarc, mesh, kwTout, grp)
        material.addExternalStateVariable(externalVar)

    # Some dependencies
    if chamGd is not None:
        material.addDependency(chamGd)
    if evol is not None:
        material.addDependency(evol)


def createExternalStateVariable(fkw, nomVarc, mesh, kwTout, grp):
    chamGd = fkw.get("CHAM_GD")
    valeRef = fkw.get("VALE_REF")
    evol = fkw.get("EVOL")

    # Construct main object
    if kwTout is not None:
        externalVar = ExternalStateVariable(nomVarc, mesh)
    elif grp is not None:
        externalVar = ExternalStateVariable(nomVarc, mesh, grp)
    else:
        externalVar = ExternalStateVariable(nomVarc, mesh)

    # Set reference value
    if valeRef is not None:
        externalVar.setReferenceValue(valeRef)

    # Set field for value of external state variable
    if chamGd is not None:
        externalVar.setField(chamGd)

    # Set transient result for value of external state variable
    if evol is not None:

        def _name2field(name):
            if name == "HYDR":
                return "HYDR_ELNO"
            if name in ("M_ACIER", "M_ZIRC"):
                return "META_ELNO"
            if name.startswith("NEUT"):
                return "NEUT"
            if name not in ("CORR", "EPSA", "GEOM", "IRRA", "PTOT", "TEMP", "SECH"):
                raise KeyError("Unknown external state variables")
            return name

        fieldName = fkw.get("NOM_CHAM")
        evolParameter = EvolutionParameter(evol, fieldName or _name2field(nomVarc))

        foncInst = fkw.get("FONC_INST")
        if foncInst is not None:
            evolParameter.setTimeFunction(foncInst)

        rightExtension = fkw.get("PROL_DROITE")
        if rightExtension is not None:
            evolParameter.setRightExtension(rightExtension)

        leftExtension = fkw.get("PROL_GAUCHE")
        if leftExtension is not None:
            evolParameter.setLeftExtension(leftExtension)

        # Set evolution paramaeter for external state variable
        externalVar.setEvolutionParameter(evolParameter)

    return externalVar


def _addMaterial(material, fkw):
    kwTout = fkw.get("TOUT")
    kwGrMa = fkw.get("GROUP_MA")
    kwMail = fkw.get("MAILLE")
    mater = fkw["MATER"]
    if type(mater) is not list:
        mater = list(mater)

    if len(mater) == 1:
        if kwTout is not None:
            material.addMaterialOnMesh(mater[0])
        elif kwGrMa is not None:
            kwGrMa = force_list(kwGrMa)
            material.addMaterialOnGroupOfCells(mater[0], kwGrMa)
        elif kwMail is not None:
            raise RuntimeError("MAILLE is no more supported")
        else:
            raise TypeError("At least {0} or {1} is required".format("TOUT", "GROUP_MA"))
    else:
        if kwTout is not None:
            material.addMultipleMaterialOnMesh(mater)
        elif kwGrMa is not None:
            kwGrMa = force_list(kwGrMa)
            material.addMultipleMaterialOnGroupOfCells(mater, kwGrMa)
        elif kwMail is not None:
            raise RuntimeError("MAILLE is no more supported")
        else:
            raise TypeError("At least {0} or {1} is required".format("TOUT", "GROUP_MA"))
