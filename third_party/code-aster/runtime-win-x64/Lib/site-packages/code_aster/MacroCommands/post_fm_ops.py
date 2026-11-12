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
from ..Messages import UTMESS
from ..Cata.Syntax import _F
from ..CodeCommands import POST_RELEVE_T, CREA_TABLE
from .Fracture.post_k_varc import POST_K_VARC

# ===========================================================================
#           CORPS DE LA MACRO "POST_FM"
#           ------------------------------
# USAGE :
#
# ===========================================================================


class PostFM:
    """
    classe POST_FM
    """

    epsfcn = np.finfo(np.dtype(float)).eps
    _eps = epsfcn**0.5

    def __init__(self, resultat, inst, temp, g_elas, g_plas, group_no):
        model = resultat.getModel()
        mesh = model.getMesh()
        nodes = mesh.getNodes(group_no, localNumbering=True)
        # on vérifie qu'il y a un unique noeud dans le groupe de noeud => ERREUR
        if len(nodes) != 1:
            UTMESS("F", "POSTFM_1", vali=len(nodes), valk=group_no)
        node = nodes[0]
        # récupération des entrées : inst, temp, g_elas et g_plas
        self._inst = np.array(inst)
        self._temp = np.array(temp)
        self._g_elas = np.maximum(0.0, np.array(g_elas))
        self._g_plas = np.maximum(0.0, np.array(g_plas))
        # récupération du materiau
        chmat = resultat.getMaterialField()
        self._retrieve_material(chmat, mesh, node)
        # récupération des entrées du matériau : young, nu et kic
        self._retrieve_material_properties()
        # initialisation des sorties
        self._k_elas = None
        self._k_plas = None
        self._k_cp = None
        self._fm_asn = None
        self._fm_plas = None

    @staticmethod
    def is_node_in_cell_groups(mesh, connectivity, cell_groups, node):
        """return True if node is found in cell_groups"""
        for cell_group in cell_groups:
            cells = mesh.getCells(cell_group)
            for cell in cells:
                if node in connectivity[cell]:
                    return True
        return False

    def _retrieve_material(self, chmat, mesh, node):
        """retrieve material located at node, from chmat
        store in self._material"""
        self._material = None
        parts = chmat.getVectorOfPartOfMaterialField()
        connectivity = mesh.getConnectivity()
        for part in parts:
            cell_groups = part.getMeshEntity().getNames()
            if self.is_node_in_cell_groups(mesh, connectivity, cell_groups, node):
                # on vérifie qu'il n'y a pas une deuxième affectation => ERREUR
                if self._material is not None:
                    UTMESS("F", "POSTFM_2")
                materials = part.getVectorOfMaterial()
                assert len(materials) == 1
                self._material = materials[0]
                # on vérifie que le materiau est bien affecté par RUPT_FM => ERREUR
                valres, codret = self._material.RCVALE("RUPT_FM", "TEMP", self._temp[0], "KIC", 2)
                if codret[0] != 0:
                    UTMESS("F", "POSTFM_3", valk=("KIC", "RUPT_FM"))
        # on vérifie qu'on a bien trouvé un materiau => ERREUR
        if self._material is None:
            UTMESS("F", "POSTFM_4")

    def _retrieve_material_properties(self):
        """retrieve Young modulus, Poisson ratio and KIC
        store in self._young, self._nu and self._kic"""
        young = []
        nu = []
        kic = []
        for temp in self._temp:
            valres, _ = self._material.RCVALE("ELAS", "TEMP", temp, ("E", "NU"), 2)
            young.append(valres[0])
            nu.append(valres[1])
            valres, _ = self._material.RCVALE("RUPT_FM", "TEMP", temp, "KIC", 2)
            kic.append(valres[0])
        self._young = np.array(young)
        self._nu = np.array(nu)
        self._kic = np.array(kic)

    @property
    def inst(self):
        """return inst"""
        return self._inst

    @property
    def temp(self):
        """return temp"""
        return self._temp

    @property
    def k_ic(self):
        """return kic"""
        return self._kic

    @property
    def k_elas(self):
        """return k_elas"""
        if self._k_elas is None:
            self._k_elas = np.sqrt(self._young * self._g_elas / (1 - self._nu**2))
        return self._k_elas

    @property
    def k_plas(self):
        """return k_plas"""
        if self._k_plas is None:
            self._k_plas = np.sqrt(self._young * self._g_plas / (1 - self._nu**2))
        return self._k_plas

    @property
    def k_cp(self):
        """return k_cp"""
        if self._k_cp is None:
            self._compute_k_cp()
        return self._k_cp

    @property
    def fm_asn(self):
        """return fm_asn"""
        if self._fm_asn is None:
            self._compute_fm_asn()
        return self._fm_asn

    @property
    def fm_plas(self):
        """return fm_plas"""
        if self._fm_plas is None and self._default_is_ddr():
            self._compute_fm_asn()
        return self._fm_plas

    def _default_is_ddr(self):
        """return true if default is DDR, else default is DSR"""
        f_plas = max(self.k_plas) / max(self.k_elas)
        return f_plas < 1.0

    def _compute_k_cp(self):
        """compute k_cp"""
        default_is_ddr = self._default_is_ddr()
        # get growing phase
        delta_k_elas = np.insert(self.k_elas[1:] - self.k_elas[:-1], 0, 0)
        k_elas_is_growing = delta_k_elas > 0
        # get delta_k over growing phase
        delta_k = self.k_plas - self.k_elas
        if default_is_ddr:
            delta_k *= -1
        delta_k *= k_elas_is_growing
        # compute delta_k_max
        delta_k_max = np.zeros([len(self.k_elas)])
        for i in range(len(delta_k)):
            delta_k_max[i] = max(0, max(delta_k[: i + 1]))
        if default_is_ddr:
            delta_k_max *= -1
        # deduce k_cp
        self._k_cp = self.k_elas + delta_k_max

    def _compute_fm_asn(self):
        """compute fm_asn"""
        self._fm_asn = self.k_ic / np.maximum(self._eps, self.k_cp)
        if self._default_is_ddr():
            self._fm_plas = self._fm_asn
            self._fm_asn = self.k_ic / np.maximum(self._eps, self.k_elas)


def post_fm_ops(self, **kwargs):
    """
    Macro POST_FM
    """
    resultat = kwargs["RESULTAT"]
    table_g = kwargs["TABLE_G"]
    group_no = kwargs["GROUP_NO"]

    table_g_values = table_g.EXTR_TABLE().values()
    inst = table_g_values["INST"]
    g_elas = table_g_values["G_ELAS"]
    g_plas = table_g_values["G_PLAS"]

    if resultat.getMaterialField() is None:
        UTMESS("F", "POSTFM_5")

    temp = []
    for i in inst:
        __cham_no_temp = POST_K_VARC(RESULTAT=resultat, INST=i, NOM_VARC="TEMP")
        __table_temp = POST_RELEVE_T(
            ACTION=_F(
                OPERATION="EXTRACTION",
                INTITULE="TEMP",
                CHAM_GD=__cham_no_temp,
                GROUP_NO=group_no,
                NOM_CMP="TEMP",
            )
        )
        temp.extend(__table_temp.EXTR_TABLE().values()["TEMP"])

    post_fm = PostFM(resultat, inst, temp, g_elas, g_plas, group_no)
    liste = [
        {"LISTE_R": post_fm.inst, "PARA": "INST"},
        {"LISTE_R": post_fm.temp, "PARA": "TEMP"},
        {"LISTE_R": post_fm.k_ic, "PARA": "KIC"},
        {"LISTE_R": post_fm.k_elas, "PARA": "KELAS"},
        {"LISTE_R": post_fm.k_plas, "PARA": "KPLAS"},
        {"LISTE_R": post_fm.k_cp, "PARA": "KCP"},
        {"LISTE_R": post_fm.fm_asn, "PARA": "FM_ASN"},
    ]
    if post_fm.fm_plas is not None:
        liste.append({"LISTE_R": post_fm.fm_plas, "PARA": "FM_PLAS"})
    result = CREA_TABLE(LISTE=liste)
    return result
