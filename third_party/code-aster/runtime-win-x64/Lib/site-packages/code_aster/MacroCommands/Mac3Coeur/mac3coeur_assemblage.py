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
Module dédié à la macro MAC3COEUR.

Par simplicité (pour la diffusion), les modules définissant les propriétés
des assemblages sont placés dans datg (avec un suffixe '.datg').
C'est pour cette raison qu'on utilise un objet ACFactory qui importe
les modules "catalogues d'assemblages" et retourne les objets associés.

On définit ici la classe principale Assemblage et ses dérivées pour
certains types d'assemblages.
"""

from math import pi
from ...Utilities import logger
from ...Cata.Syntax import _F
from ...CodeCommands import DEFI_FONCTION, DEFI_MATERIAU, DEFI_COMPOR
from .mac3coeur_factory import Mac3Factory


class Assemblage:
    """Classe définissant un assemblage combustible."""

    required_parameters = [
        # Caractéristiques matériau
        # Rigidité en rotation des liaisons grille-tube guide
        "KR_GM",
        "KR_GE",
        # Rigidité caractéristique des grilles de mélanges
        "KNAXM",
        "KY_CM",
        "KM1",
        "KM2",
        # Rigidité caractéristique des grilles extremites
        "KNAXE",
        "KY_CE",
        "KE1",
        "KE2",
        # Caractéristiques géométriques
        # des grilles
        "altitude",
        "epaisseur",
        "longueur",
        # des tubes-guides
        "NBTG",
        "RAY1GU",
        "EP1GU",
        "RAY2GU",
        "EP2GU",
        "LONTU",
        "XINFT",
        "XSUPT",
        # des crayons
        "NBCR",
        "RAYCRA",
        "EPCRA",
        "LONCR",
        "XINFC",
        "XSUPC",
        # des grilles
        "NBGR",
        "m_gri",
        # des embouts
        "EEI0",
        "EES0",
        "Leinf",
        "Keinf",
        "Lesup",
        "Kesup",
        # Perte de charges
        "K_EBSU",
        "K_GRE",
        "K_GRM",
        "K_TUB",
        "K_EBIN",
        # Poussee d Archimede de chaque élément
        "AFEBSU_1",
        "AFGRE_1",
        "AFGRM_1",
        "AFTG_1",
        "AFCRA_1",
        "AFEBIN_1",
    ]
    optional_parameters = [
        # Dilatation des grilles due a burnup thermique + alpha_thermique + fluence
        "dilatBU",
        "AL_DIL",
    ]

    computed_parameters = [
        # Caractéristiques géométriques calculées à partir d'autres paramètres
        # des tubes-guides
        "EPMOY",
        "S_TG_C",
        "I_TG_C",
        "S_TG_R",
        "I_TG_R",
        "S_TG_B",
        "I_TG_B",
        # des crayons
        "S_CR",
        "I_CR",
        # des embouts
        "Heinf",
        "Hesup",
    ]

    parameters = required_parameters + optional_parameters + computed_parameters

    _nb_cr_mesh = 0
    _nb_tg_mesh = 0
    _nb_nodes_grid = 0
    _position_todamac = None
    _position_toaster = None
    _posast = None
    _posdam = None
    _mate = None
    _type = None
    _name = None
    _cycle = None
    _bow = None

    @property
    def nb_cr_mesh(self):
        """Number of fuel rod segments of the mesh"""
        assert self._nb_cr_mesh > 0, "Parameter not set"
        return self._nb_cr_mesh

    @nb_cr_mesh.setter
    def nb_cr_mesh(self, val):
        assert val in (1, 4, 9, 16, 25, 36), "Invalid Parameter %s" % val
        self._nb_cr_mesh = val

    @property
    def nb_tg_mesh(self):
        """Number of tubes segments of the mesh"""
        assert self._nb_tg_mesh > 0, "Parameter not set"
        return self._nb_tg_mesh

    @nb_tg_mesh.setter
    def nb_tg_mesh(self, val):
        assert val in (1, 24, 25), "Invalid Parameter %s" % val
        self._nb_tg_mesh = val

    @property
    def nb_nodes_grid(self):
        """Number of nodes of a grid"""
        assert self._nb_nodes_grid > 0, "Parameter not set"
        return self._nb_nodes_grid

    @nb_nodes_grid.setter
    def nb_nodes_grid(self, val):
        assert val >= 4, "Invalid Parameter %s" % val
        self._nb_nodes_grid = val

    @property
    def position_todamac(self):
        """Fonction de changement de repere DAMAC-ASTER."""
        assert self._position_todamac, "Function not set."
        return self._position_todamac

    @position_todamac.setter
    def position_todamac(self, func):
        self._position_todamac = func

    @property
    def position_toaster(self):
        """Fonction de changement de repere DAMAC-ASTER."""
        assert self._position_toaster, "Function not set."
        return self._position_toaster

    @position_toaster.setter
    def position_toaster(self, func):
        self._position_toaster = func

    @property
    def pos_aster(self):
        """Retourne la position Aster de l'assemblage."""
        assert self._posast, "Position not set."
        return self._posast

    @pos_aster.setter
    def pos_aster(self, position):
        self._posast = position
        self._posdam = self.position_todamac(position)

    @property
    def pos_damac(self):
        """Retourne la position Damac de l'assemblage."""
        assert self._posdam, "Position not set."
        return self._posdam

    @pos_damac.setter
    def pos_damac(self, position):
        self._posast = self.position_toaster(position)
        self._posdam = position

    @property
    def materiau(self):
        """Retourne les matériaux de l'assemblage."""
        assert self._mate is not None, "Parameter not set"
        return self._mate

    @materiau.setter
    def materiau(self, mate):
        self._mate = mate

    @property
    def typeAC(self):
        """Retourne le type de l'assemblage."""
        assert self._type is not None, "Parameter not set"
        return self._type

    @typeAC.setter
    def typeAC(self, type):
        self._type = type

    @property
    def name(self):
        """Retourne le nom de l'assemblage."""
        assert self._name is not None, "Parameter not set"
        return self._name

    @name.setter
    def name(self, name):
        self._name = name

    @property
    def cycle(self):
        """Retourne le cycle de l'assemblage."""
        assert self._cycle is not None, "Parameter not set"
        return self._cycle

    @cycle.setter
    def cycle(self, cycle):
        self._cycle = cycle

    @property
    def bow(self):
        """Retourne la déformée (damac) de l'assemblage."""
        return self._bow

    @bow.setter
    def bow(self, bow):
        self._bow = bow

    def __init__(self, type_coeur):
        """Initialisation d'un type d'assemblage."""

        self.bow = {}
        self.type_coeur = type_coeur
        self._para = {}
        self._keys = {}.fromkeys(self.parameters, True)
        self._init_from_attrs()

    def _init_from_attrs(self):
        """Initialisation à partir des attributs de classe."""
        for attr in dir(self):
            if self._keys.get(attr):
                self._para[attr] = getattr(self, attr)

    def __getattr__(self, para):
        """Retourne la valeur d'un paramètre."""
        if self._para.get(para) is None:
            raise KeyError("parameter not defined : '%s'" % para)
        return self._para.get(para)

    def definition(self, **params):
        """Définition des paramètres.
        On peut appeler plusieurs fois, notamment quand certains paramètres
        dépendent de la valeur d'autres."""
        for para, value in list(params.items()):
            if not self._keys.get(para):
                raise KeyError("unknown parameter : '%s'" % para)
            self._para[para] = value

    def _check_mandatory_parameters(self):
        """Vérification des caractéristiques obligatoires."""
        req = [key for key in self.required_parameters if self._para.get(key) is None]
        assert len(req) == 0, "Missing parameters: %s" % repr(req)

    def _check_computed_parameters(self):
        """Vérification des caractéristiques obligatoires."""
        req = [key for key in self.computed_parameters if self._para.get(key) is None]
        assert len(req) == 0, "Missing parameters: %s" % repr(req)

    def check(self):
        """Vérification des données."""
        # call all '_check_*' methods
        for name in dir(self):
            if name.startswith("_check_"):
                fcheck = getattr(self, name)
                if callable(fcheck):
                    fcheck()

    def post_definition(self):
        """Méthode appelée après toutes les définitions.
        Définition des caractéristiques déterminées à partir des
        autres"""

        self._check_mandatory_parameters()

        self.definition(
            EPMOY=(self.EP1GU + self.EP2GU) / 2,
            Heinf=((self.Leinf * self.Keinf) / self.EEI0) ** 0.5,
            Hesup=((self.Lesup * self.Kesup) / self.EES0) ** 0.5,
        )

        self.definition(
            S_TG_C=pi * (self.RAY1GU**2 - (self.RAY1GU - self.EP1GU) ** 2),
            I_TG_C=pi / 4 * (self.RAY1GU**4 - (self.RAY1GU - self.EP1GU) ** 4),
            S_TG_R=pi * (self.RAY2GU**2 - (self.RAY2GU - self.EP2GU) ** 2),
            I_TG_R=pi / 4 * (self.RAY2GU**4 - (self.RAY2GU - self.EP2GU) ** 4),
            S_TG_B=pi * (self.RAY2GU**2 - (self.RAY2GU - self.EPMOY) ** 2),
            I_TG_B=pi / 4 * (self.RAY2GU**4 - (self.RAY2GU - self.EPMOY) ** 4),
            S_CR=pi * (self.RAYCRA**2 - (self.RAYCRA - self.EPCRA) ** 2),
            I_CR=pi / 4 * (self.RAYCRA**4 - (self.RAYCRA - self.EPCRA) ** 4),
        )

    def mcf_geom_fibre(self):
        """Retourne les mots-clés facteurs pour DEFI_GEOM_FIBRE."""

        def vale_4fibres(surf, iner):
            """Retourne les triplets (y, z, val) pour les 4 fibres."""
            squart = surf / 4.0
            excent = (iner / (2 * squart)) ** 0.5
            # fmt: off
            val = (
                0.0,  excent, squart,
                0.0, -excent, squart,
                excent,  0.0, squart,
               -excent,  0.0, squart,
            )
            # fmt: on
            return val

        mcf = (
            # crayon
            _F(
                GROUP_FIBRE="CR_%s" % self.pos_aster,
                COOR_AXE_POUTRE=(0.0, 0.0),
                CARA="SURFACE",
                VALE=vale_4fibres(self.S_CR, self.I_CR),
            ),
            # partie courante des tubes-guides
            _F(
                GROUP_FIBRE="LG_%s" % self.pos_aster,
                COOR_AXE_POUTRE=(0.0, 0.0),
                CARA="SURFACE",
                VALE=vale_4fibres(self.S_TG_C, self.I_TG_C),
            ),
            # biais des tubes-guides
            _F(
                GROUP_FIBRE="BI_%s" % self.pos_aster,
                COOR_AXE_POUTRE=(0.0, 0.0),
                CARA="SURFACE",
                VALE=vale_4fibres(self.S_TG_B, self.I_TG_B),
            ),
            # retreint des tubes-guides
            _F(
                GROUP_FIBRE="RE_%s" % self.pos_aster,
                COOR_AXE_POUTRE=(0.0, 0.0),
                CARA="SURFACE",
                VALE=vale_4fibres(self.S_TG_R, self.I_TG_R),
            ),
        )
        return mcf

    def mcf_compor_fibre(self, GFF):
        """Retourne les mots-clés facteurs pour DEFI_COMPOR."""

        _CMPC = DEFI_COMPOR(
            GEOM_FIBRE=GFF,
            MATER_SECT=self.materiau["CR"],
            MULTIFIBRE=_F(
                GROUP_FIBRE="CR_%s" % self.pos_aster,
                MATER=self.materiau["CR"],
                RELATION="GRAN_IRRA_LOG",
            ),
        )
        _CMPT = DEFI_COMPOR(
            GEOM_FIBRE=GFF,
            MATER_SECT=self.materiau["TG"],
            MULTIFIBRE=_F(
                GROUP_FIBRE=(
                    "LG_%s" % self.pos_aster,
                    "BI_%s" % self.pos_aster,
                    "RE_%s" % self.pos_aster,
                ),
                MATER=self.materiau["TG"],
                RELATION="GRAN_IRRA_LOG",
            ),
        )

        mtmp = (
            _F(GROUP_MA="CR_%s" % self.pos_aster, COMPOR=_CMPC),
            _F(GROUP_MA="TG_%s" % self.pos_aster, COMPOR=_CMPT),
        )

        return mtmp

    def liste_gma_fluence(self):
        """Retourne la liste des groupes de mailles impactees par la fluence"""
        l_gma = (
            "CR_%s" % self.pos_aster,
            "LG_%s" % self.pos_aster,
            "BI_%s" % self.pos_aster,
            "RE_%s" % self.pos_aster,
            "GC_%s_B" % self.pos_aster,
            "GC_%s_T" % self.pos_aster,
            "GC_%s_M" % self.pos_aster,
            "MNT_%s" % self.pos_aster,
        )
        return (l_gma, self.cycle)

    def mcf_cara_multifibre(self):
        """Retourne les mots-clés facteurs pour AFFE_CARA_ELEM/MULTIFIBRE."""
        mcf = (
            _F(GROUP_MA="CR_%s" % self.pos_aster, GROUP_FIBRE="CR_%s" % self.pos_aster),
            _F(GROUP_MA="LG_%s" % self.pos_aster, GROUP_FIBRE="LG_%s" % self.pos_aster),
            _F(GROUP_MA="BI_%s" % self.pos_aster, GROUP_FIBRE="BI_%s" % self.pos_aster),
            _F(GROUP_MA="RE_%s" % self.pos_aster, GROUP_FIBRE="RE_%s" % self.pos_aster),
        )
        return mcf

    def mcf_cara_barre(self):
        """Retourne les mots-clés facteurs pour AFFE_CARA_ELEM/BARRE."""
        # On donne une section unitaire
        mcf = (_F(GROUP_MA="MNT_%s" % self.pos_aster, SECTION="GENERALE", CARA="A", VALE=1.0),)
        return mcf

    def mcf_AC_mater(self):
        """Retourne les mots-clés facteurs pour AFFE_MATERIAU/AFFE."""

        # Avec raideur en parallele KP et KT
        kp = kt = 1.0e4 / self.nb_cr_mesh
        _MAT_BCR = DEFI_MATERIAU(DIS_CONTACT=_F(RIGI_NOR=1.0e9, JEU=0.0, KP=kp, KT=kt))

        mcf = (
            _F(GROUP_MA="CR_%s" % self.pos_aster, MATER=self.materiau["CR"]),
            _F(GROUP_MA="TG_%s" % self.pos_aster, MATER=self.materiau["TG"]),
            _F(GROUP_MA="ES_%s" % self.pos_aster, MATER=self.materiau["ES"]),
            _F(GROUP_MA="EI_%s" % self.pos_aster, MATER=self.materiau["EI"]),
            _F(GROUP_MA="MNT_%s" % self.pos_aster, MATER=self.materiau["MNT"]),
            _F(GROUP_MA="GC_%s_B" % self.pos_aster, MATER=self.materiau["GC_EB"]),
            _F(GROUP_MA="GC_%s_T" % self.pos_aster, MATER=self.materiau["GC_EH"]),
            _F(GROUP_MA="GC_%s_M" % self.pos_aster, MATER=self.materiau["GC_ME"]),
            _F(GROUP_MA="DI_%s" % self.pos_aster, MATER=self.materiau["DIL"]),
            _F(GROUP_MA="CREI_%s" % self.pos_aster, MATER=_MAT_BCR),
        )

        return mcf

    def mcf_cara_poutre(self):
        """Retourne les mots-clés facteurs pour AFFE_CARA_ELEM/POUTRE."""
        mcf = (
            # crayons
            _F(
                GROUP_MA="CR_%s" % self.pos_aster,
                SECTION="GENERALE",
                CARA=("A", "IZ", "IY", "JX", "AY", "AZ", "EY", "EZ"),
                VALE=(self.S_CR, self.I_CR, self.I_CR, self.I_CR * 2.0, 1.0, 1.0, 0.0, 0.0),
            ),
            # partie courante des tubes-guides
            _F(
                GROUP_MA="LG_%s" % self.pos_aster,
                SECTION="GENERALE",
                CARA=("A", "IZ", "IY", "JX", "AY", "AZ"),
                VALE=(self.S_TG_C, self.I_TG_C, self.I_TG_C, self.I_TG_C * 2.0, 1.0, 1.0),
            ),
            # biais des tubes-guides
            _F(
                GROUP_MA="BI_%s" % self.pos_aster,
                SECTION="GENERALE",
                CARA=("A", "IZ", "IY", "JX", "AY", "AZ"),
                VALE=(self.S_TG_B, self.I_TG_B, self.I_TG_B, self.I_TG_B * 2.0, 1.0, 1.0),
            ),
            # retreint des tubes-guides
            _F(
                GROUP_MA="RE_%s" % self.pos_aster,
                SECTION="GENERALE",
                CARA=("A", "IZ", "IY", "JX", "AY", "AZ"),
                VALE=(self.S_TG_R, self.I_TG_R, self.I_TG_R, self.I_TG_R * 2.0, 1.0, 1.0),
            ),
            # embouts inférieurs
            _F(
                GROUP_MA="EI_%s" % self.pos_aster,
                SECTION="RECTANGLE",
                CARA=("H",),
                VALE=(self.Heinf,),
            ),
            # embouts supérieurs
            _F(
                GROUP_MA="ES_%s" % self.pos_aster,
                SECTION="RECTANGLE",
                CARA=("H",),
                VALE=(self.Hesup,),
            ),
            # dilatation
            _F(
                GROUP_MA="DI_%s" % self.pos_aster,
                SECTION="RECTANGLE",
                CARA=("HY", "HZ"),
                VALE=(0.03, 0.2138),
            ),
        )
        return mcf

    def mcf_cara_discret(self):
        """Retourne les mots-clés facteurs pour AFFE_CARA_ELEM/DISCRET."""

        def vale_K_TR_D_L(kr, nb):
            """Retourne les valeurs pour un K_TR_D_L."""
            kx = ky = kry = 1.0e9 / 4.0
            kz = 0.0
            krx = krz = kr / 4.0
            output = [kx, ky, kz, krx, kry, krz]

            return [i * nb for i in output]

        def vale_K_TR_L(kn_ax, ky_c, k1, k2, nbcr):
            """Retourne les valeurs pour un K_TR_L."""
            carel = [0.0] * 78
            carel[1 - 1] = kn_ax
            carel[3 - 1] = ky_c / 4.0
            carel[10 - 1] = (k1 - k2) / 2.0
            carel[21 - 1] = k2 / 2.0
            carel[28 - 1] = kn_ax
            carel[36 - 1] = ky_c / 4.0
            carel[55 - 1] = (k1 - k2) / 2.0
            carel[78 - 1] = k2 / 2.0
            carel[22 - 1] = -1.0 * kn_ax
            carel[30 - 1] = -1.0 * ky_c / 4.0
            carel[49 - 1] = -1.0 * (k1 - k2) / 2.0
            carel[72 - 1] = -1.0 * k2 / 2.0
            return [i * nbcr for i in carel]

        def vale_K_T_D_L(kr, nb):
            kx = ky = kz = kr / nb
            output = [kx, ky, kz]
            return output

        mcf = (
            # --- Pour les discrets des liaisons grilles / crayons
            # --- Pour les grilles de melanges
            _F(
                GROUP_MA="GC_%s_M" % self.pos_aster,
                REPERE="LOCAL",
                CARA="K_TR_L",
                VALE=vale_K_TR_L(
                    self.KNAXM, self.KY_CM, self.KM1, self.KM2, self.NBCR / self.nb_cr_mesh
                ),
            ),
            _F(
                GROUP_MA="GC_%s_M" % self.pos_aster,
                REPERE="LOCAL",
                CARA="M_TR_D_L",
                VALE=(0.0, 0.0, 0.0, 0.0),
            ),
            # --- Pour les grilles extremites
            _F(
                GROUP_MA=("GC_%s_B" % self.pos_aster, "GC_%s_T" % self.pos_aster),
                REPERE="LOCAL",
                CARA="K_TR_L",
                VALE=vale_K_TR_L(
                    self.KNAXE, self.KY_CE, self.KE1, self.KE2, self.NBCR / self.nb_cr_mesh
                ),
            ),
            _F(
                GROUP_MA=("GC_%s_B" % self.pos_aster, "GC_%s_T" % self.pos_aster),
                REPERE="LOCAL",
                CARA="M_TR_D_L",
                VALE=(0.0, 0.0, 0.0, 0.0),
            ),
            # discrets des liaisons grilles / tubes-guide
            # grilles de mélanges
            _F(
                GROUP_MA="GT_%s_M" % self.pos_aster,
                REPERE="LOCAL",
                CARA="K_TR_D_L",
                VALE=vale_K_TR_D_L(self.KR_GM, self.NBTG / self.nb_tg_mesh),
            ),
            _F(
                GROUP_MA="GT_%s_M" % self.pos_aster,
                REPERE="LOCAL",
                CARA="M_TR_D_L",
                VALE=(0.0, 0.0, 0.0, 0.0),
            ),
            # grilles extrémités
            _F(
                GROUP_MA="GT_%s_E" % self.pos_aster,
                REPERE="LOCAL",
                CARA="K_TR_D_L",
                VALE=vale_K_TR_D_L(self.KR_GE, self.NBTG / self.nb_tg_mesh),
            ),
            _F(
                GROUP_MA="GT_%s_E" % self.pos_aster,
                REPERE="LOCAL",
                CARA="M_TR_D_L",
                VALE=(0.0, 0.0, 0.0, 0.0),
            ),
            # poids des grilles
            _F(
                GROUP_MA="GR_%s" % self.pos_aster,
                REPERE="LOCAL",
                CARA="M_T_D_N",
                VALE=self.m_gri / self.nb_nodes_grid,
            ),
            # ressort pour blocage bas crayons
            _F(
                GROUP_MA="CREI_%s" % self.pos_aster,
                REPERE="LOCAL",
                CARA="K_T_D_L",
                VALE=vale_K_T_D_L(1.0e9, self.nb_cr_mesh),
            ),
        )
        return mcf

    def mcf_deform_impo(self):
        """Retourne les mots-clés facteurs pour AFFE_CHAR_CINE/MECA_IMPO."""
        mcf = []
        for igr in range(1, self.NBGR + 1):
            mcf.append(
                _F(
                    GROUP_NO="P_%s_%d" % (self.pos_aster, igr),
                    DY=self.bow["DY%d" % igr],
                    DZ=self.bow["DZ%d" % igr],
                )
            )
        return mcf

    def mcf_archimede_nodal(self):
        """Retourne les mots-clés facteurs pour AFFE_CHAR_MECA/FORCE_NODALE
        dans la prise en compte de la poussée d Archimede."""
        mcf = []
        mcf.append(_F(GROUP_NO="PS_%s" % self.pos_aster, FX=self.AFEBSU_1))
        mcf.append(_F(GROUP_NO="PI_%s" % self.pos_aster, FX=self.AFEBIN_1))

        mcf.append(_F(GROUP_NO="G_%s_1" % self.pos_aster, FX=self.AFGRE_1 / self.nb_nodes_grid))
        for igr in range(1, self.NBGR - 1):
            mcf.append(
                _F(
                    GROUP_NO="G_%s_%d" % (self.pos_aster, igr + 1),
                    FX=self.AFGRM_1 / self.nb_nodes_grid,
                )
            )

        mcf.append(
            _F(
                GROUP_NO="G_%s_%d" % (self.pos_aster, self.NBGR),
                FX=self.AFGRE_1 / self.nb_nodes_grid,
            )
        )
        return mcf

    def mcf_archimede_poutre(self):
        """Retourne les mots-clés facteurs pour AFFE_CHAR_MECA_F/FORCE_POUTRE
        dans la prise en compte de la poussée d Archimede."""

        force_rep_tg = self.AFTG_1 / self.LONTU / self.nb_tg_mesh
        FXTG = DEFI_FONCTION(
            NOM_PARA="X",
            PROL_DROITE="CONSTANT",
            PROL_GAUCHE="CONSTANT",
            VALE=(self.XINFT, force_rep_tg, self.XSUPT, force_rep_tg),
        )

        force_rep_cr = self.AFCRA_1 / self.LONCR / self.nb_cr_mesh
        FXCR = DEFI_FONCTION(
            NOM_PARA="X",
            PROL_DROITE="CONSTANT",
            PROL_GAUCHE="CONSTANT",
            VALE=(self.XINFC, force_rep_cr, self.XSUPC, force_rep_cr),
        )

        logger.debug("<MAC3_ASSEMBLAGE><ARCHIMEDE>: TG %s %s" % (self.pos_aster, force_rep_tg))
        logger.debug("<MAC3_ASSEMBLAGE><ARCHIMEDE>: CR %s %s" % (self.pos_aster, force_rep_cr))

        mcf = (
            _F(GROUP_MA="TG_%s" % self.pos_aster, FX=FXTG),
            _F(GROUP_MA="CR_%s" % self.pos_aster, FX=FXCR),
        )
        return mcf


class AssemblageAFAXL(Assemblage):
    """Particularités du type AFAXL."""

    pass


class ACFactory(Mac3Factory):
    """Classe pour construire les objets Assemblage."""

    def build_supported_types(self):
        """Construit la liste des types autorisés."""
        ctxt = {}
        for obj, val in list(globals().items()):
            if isinstance(val, type) and issubclass(val, Assemblage):
                ctxt[obj] = val
        return ctxt
