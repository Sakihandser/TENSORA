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

from libaster import Physics, Modelings
from ...Cata.Syntax import _F
from ...CodeCommands import AFFE_MATERIAU, CALC_CHAMP
from ...Objects import Model
from ...Messages import ASSERT, UTMESS

from . import HomoType
from .rest_homo_utilities import RelocManager
from .rest_homo_massif import createLocalTherResult, createLocalElasResult


def rest_homo_ops(self, **kwargs):
    """
    Main function for field relocalisation.

    This function performs the relocalisation of fields based on the provided global results
    and user settings. It supports both mechanical and thermal field relocalisation.

    """

    # Read the user settings
    resu_glob_meca = kwargs.get("EVOL_ELAS")
    resu_glob_ther = kwargs.get("EVOL_THER")
    kwaffemat = kwargs.get("AFFE")
    user_type_homo = HomoType.str2value(kwargs.get("TYPE_HOMO"))
    rmanager = RelocManager(kwargs)

    # Relocalisation is only programmed for Bulk homogeneisation
    if not (user_type_homo == rmanager.type_homo):
        UTMESS("F", "HOMO1_16", valk=user_type_homo)

    resu_ther = None
    if resu_glob_ther is not None:
        resu_ther = createLocalTherResult(rmanager, resu_glob_ther)

        varckw = {
            "NOM_VARC": "TEMP",
            "EVOL": resu_ther,
            "NOM_CHAM": "TEMP",
            "VALE_REF": rmanager.temp_ref,
        }

        mod_ther = Model(rmanager.ver_mesh)
        mod_ther.addModelingOnMesh(Physics.Thermal, Modelings.Tridimensional)
        mod_ther.build()

        fmat_ther = AFFE_MATERIAU(MODELE=mod_ther, AFFE=kwaffemat)
        resu_ther.setModel(mod_ther)
        resu_ther.setMaterialField(fmat_ther)

        if "FLUX_ELGA" in kwargs.get("OPTION"):
            resu_ther = CALC_CHAMP(reuse=resu_ther, RESULTAT=resu_ther, THERMIQUE=("FLUX_ELGA"))

    else:
        # If missing create a constant field at reference temperature
        rmanager.setConstantTP0Function()
        varckw = {
            "NOM_VARC": "TEMP",
            "CHAM_GD": rmanager.temp_ref_field,
            "VALE_REF": rmanager.temp_ref,
        }

    resu_meca = None
    if resu_glob_meca is not None:
        resu_meca = createLocalElasResult(rmanager, resu_glob_meca)

        mod_meca = Model(rmanager.ver_mesh)
        mod_meca.addModelingOnMesh(Physics.Mechanics, Modelings.Tridimensional)
        mod_meca.build()

        fmat_meca = AFFE_MATERIAU(MODELE=mod_meca, AFFE=kwaffemat, AFFE_VARC=_F(**varckw))

        resu_meca.setModel(mod_meca)
        resu_meca.setMaterialField(fmat_meca)

        if "SIEF_ELGA" in kwargs.get("OPTION"):
            resu_meca = CALC_CHAMP(reuse=resu_meca, RESULTAT=resu_meca, CONTRAINTE=("SIEF_ELGA"))

        result = resu_meca
    else:
        result = resu_ther

    ASSERT(result is not None)
    return result
