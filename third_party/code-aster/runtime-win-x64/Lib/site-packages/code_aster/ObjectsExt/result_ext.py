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

"""
:py:class:`Result` --- Results container
**************************************************
"""

import os.path as osp
import subprocess

import aster

from ..MedUtils.MedConverter import fromMedFileData, toMedFileData
from ..Messages import UTMESS
from ..Objects import DirichletBC, MechanicalLoadComplex, Result
from ..Objects.Serialization import InternalStateBuilder
from ..Utilities import (
    MPI,
    ExecutionParameter,
    InterpolateList,
    SearchList,
    SharedTmpdir,
    force_list,
    injector,
    is_number,
    logger,
)


class ResultStateBuilder(InternalStateBuilder):
    """Class that returns the internal state of a *Result*."""

    def _addFields(self, result, fieldNames, indexes):
        for i in indexes:
            for fieldName in fieldNames:
                try:
                    curField = result.getField(fieldName, i, updatePtr=False)
                    self._st["fields"][i][fieldName] = curField
                except:
                    pass

    def save(self, result):
        """Return the internal state of a *Result* to be pickled.

        Arguments:
            result (*Result*): The *Result* object to be pickled.

        Returns:
            *InternalStateBuilder*: The internal state itself.
        """
        super().save(result)
        # mesh
        self._st["mesh"] = result.getMesh()
        # list of indexs
        self._st["index"] = result.getIndexes()
        # list of Model objects
        self._st["model"] = []
        # list of MaterialField objects
        self._st["mater"] = []
        # list of ElementaryCharacteristics
        self._st["cara_elem"] = []
        # list of list of loads
        self._st["loads"] = []
        # list of ligrel
        self._st["feds"] = result.getFiniteElementDescriptors()
        # list of nume_equa
        self._st["fnds"] = result.getEquationNumberings()
        for i in self._st["index"]:
            if result.hasModel(i):
                self._st["model"].append(result.getModel(i))
            if result.hasMaterialField(i):
                self._st["mater"].append(result.getMaterialField(i))
            if result.hasElementaryCharacteristics(i):
                self._st["cara_elem"].append(result.getElementaryCharacteristics(i))
            if result.hasListOfLoads(i):
                self._st["loads"].append(result.getListOfLoads(i))

        if len(self._st["index"]) != len(self._st["model"]):
            logger.debug(
                f"Inconsistent definition of models: "
                f"{len(self._st['index'])} indexs, {len(self._st['model'])} models"
            )
            self._st["model"] = []
        if len(self._st["index"]) != len(self._st["mater"]):
            logger.debug(
                f"Inconsistent definition of materials fields: "
                f"{len(self._st['index'])} indexs, {len(self._st['mater'])} materials"
            )
            self._st["mater"] = []
        if len(self._st["cara_elem"]) > 0 and len(self._st["index"]) != len(self._st["cara_elem"]):
            logger.debug(
                f"Inconsistent definition of elementary characteristics fields: "
                f"{len(self._st['index'])} indexs, {len(self._st['cara_elem'])} elementary characteristics"
            )
            self._st["cara_elem"] = []
        if len(self._st["loads"]) > 0 and len(self._st["index"]) != len(self._st["loads"]):
            logger.debug(
                f"Inconsistent definition of list of loads: "
                f"{len(self._st['index'])} indexs, {len(self._st['loads'])} list of loads"
            )
            self._st["loads"] = []

        indexes = self._st["index"]
        self._st["fields"] = {}
        for i in indexes:
            self._st["fields"][i] = {}
        self._addFields(result, result.getFieldsOnNodesRealNames(), indexes)
        self._addFields(result, result.getFieldsOnNodesComplexNames(), indexes)
        self._addFields(result, result.getFieldsOnCellsRealNames(), indexes)
        self._addFields(result, result.getFieldsOnCellsComplexNames(), indexes)
        self._addFields(result, result.getFieldsOnCellsLongNames(), indexes)
        self._addFields(result, result.getConstantFieldsOnCellsRealNames(), indexes)
        self._addFields(result, result.getConstantFieldsOnCellsChar16Names(), indexes)

        return self

    def restore(self, result):
        """Restore the *DataStructure* content from the previously saved internal
        state.

        Arguments:
            result (*DataStructure*): The *DataStructure* object to be restored.
        """
        super().restore(result)
        result.setMesh(self._st["mesh"])
        for i, index in enumerate(self._st["index"]):
            if self._st["model"]:
                result.setModel(self._st["model"][i], index)
            if self._st["mater"]:
                result.setMaterialField(self._st["mater"][i], index)
            if len(self._st["cara_elem"]) > 0 and self._st["cara_elem"]:
                result.setElementaryCharacteristics(self._st["cara_elem"][i], index)
            if len(self._st["loads"]) > 0 and self._st["loads"]:
                result.setListOfLoads(self._st["loads"][i], index)

        for fed in self._st["feds"]:
            result.addFiniteElementDescriptor(fed)
        for fnd in self._st["fnds"]:
            result.addEquationNumbering(fnd)
        for index in self._st["fields"]:
            fields = self._st["fields"][index]
            for fieldName in fields:
                result.setField(fields[fieldName], fieldName, index)


@injector(Result)
class ExtendedResult:
    cata_sdj = "SD.sd_resultat.sd_resultat"
    internalStateBuilder = ResultStateBuilder

    def _createIndexFromParameter(self, para, value, crit, prec):
        """
        Create the index corresponding to a given value of an access parameter.

        Arguments:
            para (str) : name of the access parameter (NUME_ORDRE, INST, etc..)
            value (float|int|str) : value of the access parameter
            crit (str) : search criterion ABSOLU or RELATIF
            prec (float) : precision for the search criterion

        Returns:
            index (int) : the corresponding index (index)
        """
        acpara = self.getAccessParameters()
        if para not in acpara:
            UTMESS("F", "RESULT1_8")
        if isinstance(value, int):
            storageIndex = self.createIndexFromParameter(para, value)
        elif isinstance(value, str):
            storageIndex = self.createIndexFromParameter(para, value)
        else:
            raise ValueError(f"Type of access to result is invalid {value!r}")

        return storageIndex

    def getIndexFromParameter(self, para, value, crit, prec, throw_except=True):
        """
        Get the index corresponding to a given value of an access parameter.

        Arguments:
            para (str): name of the access parameter (NUME_ORDRE, INST, etc..)
            value (float|int|str): value of the access parameter
            crit (str): search criterion ABSOLU or RELATIF
            prec (float): precision for the search criterion
            throw_except (bool): throw an exception in case of error, else it returns -1.

        Returns:
            index (int) : the corresponding index (index)
        """
        parameters = self.getAccessParameters()
        return self._getIndexFromParameter(parameters, para, value, crit, prec, throw_except)

    @staticmethod
    def _getIndexFromParameter(parameters, para, value, crit, prec, throw_except=True):
        if not para in parameters:
            msg = "Missing parameter {}".format(para)
            raise ValueError(msg)

        if para not in parameters:
            UTMESS("F", "RESULT1_8")
        if is_number(value):
            slist = SearchList(parameters[para], prec, crit)
            try:
                internalStorage = slist.index(value)
            except ValueError:
                if throw_except:
                    raise
                return -1
        elif isinstance(value, str):
            slist = parameters[para]
            try:
                internalStorage = slist.index(value)
            except ValueError:
                if throw_except:
                    raise
                return -1
        else:
            raise ValueError(f"Type of access to result is invalid {value!r}")

        return parameters["NUME_ORDRE"][internalStorage]

    @classmethod
    def getIndexesFromKeywords(cls, parameters, keywords):
        """Get the index corresponding appropriate values to extract from
        given keywords

        Arguments:
            parameters (dict): Access parameters as returned by ``getAccessParameters()``.
            keywords (dict): Dict of keywords
                Supported keywords (only one value is permitted between):
                    TOUT_ORDRE, NUME_ORDRE, INST, LIST_INST, FREQ, LIST_FREQ,
                    LIST_ORDRE

        Return:
            list: Indexes.
        """
        # All supported keywords
        admissible_keywords = (
            "TOUT_ORDRE",
            "NUME_ORDRE",
            "LIST_ORDRE",
            "INST",
            "LIST_INST",
            "FREQ",
            "LIST_FREQ",
        )

        # Elements of keywords that are supported
        detected_keywords = set(keywords).intersection(admissible_keywords)

        # Error handling for "keywords" input
        if len(detected_keywords) != 1:
            raise KeyError(f"Exactly one of {admissible_keywords} is expected")

        # --- Handling of detected keyword ---
        processed_kw = detected_keywords.pop()

        # Get CRITERE and PRECISION from keywords if they exist. Otherwise,
        #   default value are chosen.
        crit_para = keywords.get("CRITERE", "RELATIF")
        prec_para = keywords.get("PRECISION", 1.0e-6)

        if processed_kw == "TOUT_ORDRE" and keywords[processed_kw] == "OUI":
            return parameters["NUME_ORDRE"]
        if processed_kw.startswith("LIST_"):
            if processed_kw == "LIST_ORDRE":
                para = "NUME_ORDRE"
            else:
                para = processed_kw[5:]
            values = keywords[processed_kw].getValues()
        else:
            para = processed_kw
            values = force_list(keywords[processed_kw])
        indexes = [
            cls._getIndexFromParameter(
                parameters, para, value, crit_para, prec_para, throw_except=False
            )
            for value in values
        ]
        indexes = [idx for idx in indexes if idx >= 0]
        return indexes

    def build(self, feds=[], fnds=[], excit={}):
        """Build the result from the name of the result. It stores fields which are setted in c++ or
        created in fortran

        Arguments:
            feds (list[FiniteElementDescriptor]) : list of additional finite element descriptor used to
                build FieldOnCells
            fnds (list[EquationNumbering]) : list of additional field description used to
                build FieldOnNodes
            excit (dict) : dict of EXCIT keywords to build ListOfLoads

        Returns:
            bool: *True* if ok.
        """

        self._build(feds, fnds)

        # build list of loads
        if excit:
            litsLoads = self.getListOfLoads(self.getLastIndex())

            loadNames = litsLoads.getLoadNames()

            for dictLoad in excit:
                charge = dictLoad["CHARGE"]
                # some load like RELA_CINE_BP are not stored
                if charge.getName() in loadNames:
                    if "FONC_MULT" in dictLoad:
                        if isinstance(charge, DirichletBC):
                            litsLoads.addDirichletBC(
                                charge, dictLoad["FONC_MULT"], dictLoad["TYPE_CHARGE"]
                            )
                        elif charge.getType() == "CHAR_MECA" and not isinstance(
                            charge, MechanicalLoadComplex
                        ):
                            litsLoads.addLoad(
                                charge, dictLoad["FONC_MULT"], dictLoad["TYPE_CHARGE"]
                            )
                        else:
                            litsLoads.addLoad(charge, dictLoad["FONC_MULT"])
                    else:
                        if isinstance(charge, DirichletBC):
                            litsLoads.addDirichletBC(charge, dictLoad["TYPE_CHARGE"])
                        elif charge.getType() == "CHAR_MECA" and not isinstance(
                            charge, MechanicalLoadComplex
                        ):
                            litsLoads.addLoad(charge, dictLoad["TYPE_CHARGE"])
                        else:
                            litsLoads.addLoad(charge)

    def getField(
        self, name, value=None, para="NUME_ORDRE", crit="RELATIF", prec=1.0e-6, updatePtr=True
    ):
        """Get the specified field by its name and a parameter access.

        Arguments:
            name (str): symbolic name of the field in the result (ex: 'DEPL', 'VITE'...)
            value (float|int|str): value of the access parameter
            para (str): name of the access parameter (NUME_ORDRE, INST, etc..)
            crit (str): search criterion ABSOLU or RELATIF
            prec (float): precision for the search criterion
            updatePtr (bool): update the pointer on the field values if *True* (default).
                The argument should not be disabled by the user, mainly for internal use.

        Returns:
            FieldXXX: field to get with type in (FieldOnNodesXXX/FieldOnCellsXXX/
            ConstantFieldOnCellXXX)
        """
        assert crit in ("ABSOLU", "RELATIF")

        if para in ("NUME_ORDRE",):
            storageIndex = value
        else:
            storageIndex = self.getIndexFromParameter(para, value, crit, prec, throw_except=True)

        if storageIndex == -1:
            UTMESS("F", "RESULT1_9")

        names = self.getFieldsOnNodesRealNames()
        if name in names:
            return self._getFieldOnNodesReal(name, storageIndex, updatePtr=updatePtr)

        names = self.getFieldsOnNodesComplexNames()
        if name in names:
            return self._getFieldOnNodesComplex(name, storageIndex, updatePtr=updatePtr)

        names = self.getFieldsOnCellsRealNames()
        if name in names:
            return self._getFieldOnCellsReal(name, storageIndex, updatePtr=updatePtr)

        names = self.getFieldsOnCellsComplexNames()
        if name in names:
            return self._getFieldOnCellsComplex(name, storageIndex, updatePtr=updatePtr)

        names = self.getFieldsOnCellsLongNames()
        if name in names:
            return self._getFieldOnCellsLong(name, storageIndex, updatePtr=updatePtr)

        names = self.getConstantFieldsOnCellsRealNames()
        if name in names:
            return self._getConstantFieldOnCellsReal(name, storageIndex, updatePtr=updatePtr)

        names = self.getConstantFieldsOnCellsChar16Names()
        if name in names:
            return self._getConstantFieldOnCellsChar16(name, storageIndex, updatePtr=updatePtr)

        names = self.getGeneralizedVectorRealNames()
        if name in names:
            return self.getGeneralizedVectorReal(name, storageIndex)

        names = self.getGeneralizedVectorComplexNames()
        if name in names:
            return self.getGeneralizedVectorComplex(name, storageIndex)

        raise KeyError("name of field %s not found" % name)

    def interpolateField(
        self, name, value, left="EXCLU", right="EXCLU", crit="RELATIF", prec=1.0e-6, updatePtr=True
    ):
        """Interpolate the specified field by its name and a time value.

        Arguments:
            name (str): symbolic name of the field in the result (ex: 'DEPL', 'VITE'...)
            value (float|int|str): value of time (the access parameter)
            left (str): extrapolation (EXCLU, LINEAIRE, CONSTANT)
            right (str): extrapolation (EXCLU, LINEAIRE, CONSTANT)
            crit (str): search criterion ABSOLU or RELATIF
            prec (float): precision for the search criterion
            updatePtr (bool): update the pointer on the field values if *True* (default).
                The argument should not be disabled by the user, mainly for internal use.

        Returns:
            FieldXXX: field to get with type in (FieldOnNodesXXX/FieldOnCellsXXX/
            ConstantFieldOnCellXXX)
        """

        if not name in self.getFieldsNames():
            raise ValueError(f"Invalid field name {name}")

        acpara = self.getAccessParameters()
        para = "INST"
        if not para in acpara:
            raise KeyError(f"Access parameter `{para}` is not available")

        times = InterpolateList(acpara["INST"], left, right, prec, crit)
        times.assertInclude(value)

        kws = {
            "name": name,
            "value": value,
            "para": "INST",
            "left": left,
            "right": right,
            "crit": crit,
            "prec": prec,
            "updatePtr": updatePtr,
        }

        names = self.getFieldsOnNodesRealNames()
        if name in names:
            return self._interpolateFieldOnNodesReal(**kws)
        names = self.getFieldsOnCellsRealNames()
        if name in names:
            return self._interpolateFieldOnCellsReal(**kws)

        raise KeyError("cannot interpolate field %s" % name)

    def setField(self, field, name, value=None, para="NUME_ORDRE", crit="RELATIF", prec=1.0e-6):
        """Set the specified field. This is an overlay to existing methods
        for each type of field.

        Arguments:
            field : field
            name (str): symbolic name of the field in the result (ex: 'DEPL', 'VITE'...)
            value (float|int|str) : value of the access parameter
            para (str) : name of the access parameter (NUME_ORDRE, INST, etc..)
            crit (str) : search criterion ABSOLU or RELATIF
            prec (float) : precision for the search criterion
        """

        assert crit in ("ABSOLU", "RELATIF")

        if para in ("NUME_ORDRE",):
            storageIndex = value
        else:
            storageIndex = self.getIndexFromParameter(para, value, crit, prec, throw_except=False)

        if storageIndex == None:
            UTMESS("F", "RESULT2_10")

        if storageIndex < 0:
            storageIndex = self._createIndexFromParameter(para, value, crit, prec)
            if storageIndex < 0:
                raise KeyError("Echec lors de la création du paramètre")

        self._setField(field, name, storageIndex)

    def plot(self, command="gmsh", local=True, split=False):
        """Plot the result.

        Arguments:
            command (str): Program to be executed to plot the result.
            local (bool): Print in separate files if *True*. Otherwise an unique file is used.
            split (bool): Display the fields on each subdomain separately if *True*. Otherwise the global fields are displayed.
        """
        comm = MPI.ASTER_COMM_WORLD
        mesh = self.getMesh()
        opt = "Mesh.VolumeEdges = 0;Mesh.VolumeFaces=0;Mesh.SurfaceEdges=0;Mesh.SurfaceFaces=0;View[0].ShowElement = 1;"
        if (local and mesh.isParallel()) or (split and mesh.isParallel()):
            with SharedTmpdir("plot") as tmpdir:
                filename = osp.join(tmpdir.path, f"field_{comm.rank}.med")
                self.printMedFile(filename, local=True)
                comm.Barrier()
                if comm.rank == 0:
                    if split:
                        for i in range(comm.size):
                            ff = osp.join(tmpdir.path, f"field_{i}.med")
                            subprocess.run(
                                [
                                    ExecutionParameter().get_option(f"prog:{command}"),
                                    "-string",
                                    opt,
                                    ff,
                                ]
                            )
                    else:
                        files = [osp.join(tmpdir.path, f"field_{i}.med") for i in range(comm.size)]
                        subprocess.run(
                            [ExecutionParameter().get_option(f"prog:{command}"), "-string", opt]
                            + files
                        )
        else:
            with SharedTmpdir("plot") as tmpdir:
                filename = osp.join(tmpdir.path, "field.med")
                self.printMedFile(filename, local=False)
                if comm.rank == 0:
                    subprocess.run(
                        [
                            ExecutionParameter().get_option(f"prog:{command}"),
                            "-string",
                            opt,
                            filename,
                        ]
                    )
        print("waiting for all plotting processes...")
        comm.Barrier()

    def createMedCouplingResult(self, medmesh=None, profile=False, prefix=""):
        """Export the result to a new MED container.

        The export is limited to fields on nodes (Real) only.

        Arguments:
            medmesh, optional (*MEDFileUMesh*): The medcoupling support mesh.
            profile, optional (bool): True to create a MED profile from field mask.
            prefix,  optional (str): Prefix for field names.

        Returns:
            field ( MEDFileData ) : The result in med format ( medcoupling ).
        """

        return toMedFileData(self, medmesh, profile, prefix)

    @classmethod
    def fromMedCouplingResult(cls, medresult, astermesh=None):
        """Create a new result from an existing MED container.

        The import is limited to fields on nodes (Real) without profile.

        Arguments:
            medresult (MEDFileData) : The result in med format ( medcoupling ).
            astermesh, optional (Mesh): The aster support mesh.

        Returns:
            result ( Result ) : The result in Aster format.
        """

        result = cls()
        fromMedFileData(result, medresult, astermesh)

        return result
