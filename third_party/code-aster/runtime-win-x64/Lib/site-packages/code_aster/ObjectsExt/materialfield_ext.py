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
:py:class:`MaterialField` --- Assignment of material properties on mesh
************************************************************************
"""

from libaster import EntityType, MaterialField

from ..Utilities import injector
from ..Objects.Serialization import InternalStateBuilder


class MaterialFieldStateBuilder(InternalStateBuilder):
    """Class that returns the internal state of a *MaterialField*."""

    entity2num = {
        EntityType.AllMeshEntitiesType: 0,
        EntityType.GroupOfCellsType: 1,
        EntityType.CellType: 2,
    }

    def save(self, field):
        """Return the internal state of a *MaterialField* to be pickled.

        Arguments:
            field (*MaterialField*): The *MaterialField* object to be pickled.

        Returns:
            *InternalStateBuilder*: The internal state itself.
        """
        super().save(field)
        self._st["mesh"] = field.getMesh()
        self._st["part"] = []
        for part in field.getVectorOfPartOfMaterialField():
            occ = {
                "mater": part.getVectorOfMaterial(),
                "type": self.entity2num[part.getMeshEntity().getType()],
                "names": part.getMeshEntity().getNames(),
            }
            self._st["part"].append(occ)

        # varc
        self._st["varc"] = []
        for value in field.getExtStateVariablesOnMeshEntities():
            varc, meshEntity = value
            self._st["varc"].append(varc)

        return self

    def restore(self, field):
        """Restore the *DataStructure* content from the previously saved internal
        state.

        Arguments:
            field (*DataStructure*): The *DataStructure* object to be restored.
        """
        super().restore(field)
        for occ in self._st["part"]:
            if occ["type"] == 0:
                if len(occ["mater"]) == 1:
                    field.addMaterialOnMesh(occ["mater"][0])
                else:
                    field.addMultipleMaterialOnMesh(occ["mater"])
            elif occ["type"] == 1:
                if len(occ["mater"]) == 1:
                    field.addMaterialOnGroupOfCells(occ["mater"][0], occ["names"])
                else:
                    field.addMultipleMaterialOnGroupOfCells(occ["mater"], occ["names"])
            else:
                raise RuntimeError("Programming error")

        for varc in self._st["varc"]:
            field.addExternalStateVariable(varc)


@injector(MaterialField)
class ExtendedMaterialField:
    cata_sdj = "SD.sd_cham_mater.sd_cham_mater"
    internalStateBuilder = MaterialFieldStateBuilder

    def __getinitargs__(self):
        """Returns the argument required to reinitialize a MaterialField
        object during unpickling.
        """
        return (self.getName(), self.getMesh())
