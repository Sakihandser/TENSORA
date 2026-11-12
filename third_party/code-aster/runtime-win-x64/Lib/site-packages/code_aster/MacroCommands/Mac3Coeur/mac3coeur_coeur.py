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

Définition d'une conception de coeur (ensemble d'assemblages).
"""

import os.path as osp
from ...Utilities import logger, ExecutionParameter

from ...Cata.Syntax import _F
from ...CodeCommands import (
    AFFE_CARA_ELEM,
    AFFE_CHAR_CINE,
    AFFE_CHAR_CINE_F,
    AFFE_CHAR_MECA,
    AFFE_CHAR_MECA_F,
    AFFE_MATERIAU,
    AFFE_MODELE,
    CREA_CHAMP,
    CREA_MAILLAGE,
    CREA_RESU,
    DEFI_FONCTION,
    DEFI_GEOM_FIBRE,
    DEFI_LIST_INST,
    DEFI_LIST_REEL,
    DEFI_MATERIAU,
    DEFI_NAPPE,
    FORMULE,
    INCLUDE_MATERIAU,
    RECU_TABLE,
)
from .mac3coeur_assemblage import ACFactory
from .mac3coeur_factory import Mac3Factory
from .mac3coeur_commons import CollectionMAC3, flat_list


class Coeur:
    """Classe définissant un coeur de reacteur."""

    required_parameters = [
        # Nombre d'assemblages pour définir le coeur
        "NBAC",
        # Position des grilles pour definition du champ de fluence
        "altitude",
        # Position des crayons et tubes-guides pour definition du champ de
        # fluence
        "XINFT",
        "XSUPT",
        "XINFC",
        "XSUPC",
        "LONCR",
        "LONTU",
        # Caractéristique de la cuve
        "pas_assemblage",
        "XINFCUVE",
        "XSUPCUVE",
        # ---fleche des ressorts de maintien à la fermeture de la cuve
        "flechResMaint",
        # ---Dimensions de la cavité entre PIC (ou FSC) et PSC
        "Hcav1centre",
        "Hcav2centre",
        "Hcav3centre",
        "Hcav4centre",
        "Hcav1periph",
        "Hcav2periph",
        "Hcav3periph",
        "Hcav4periph",
        # Températures caractérisitiques
        "TP_REF",
        "ARRET_FR",
        "ARRET_CH",
        "TINFCUVE",
        "TSUPCUVE",
        "TENVELOP",
        "TP_TG1",
        "TP_TG2",
        "TXX1",
        "TXX2",
        "TXX3",
        "TXX4",
        # Abscisses caracteristiques pour le profil de temperature des crayons
        "SXX2",
        "SXX3",
        # paramètres de l'interpolation linéaire
        # du coefficient de dilatation des internes de cuve
        "ALPH1",
        "ALPH2",
        # Post-traitement des lames
        #'nomContactAssLame', 'nomContactCuve',
        # Valeurs de gravité et tables de l'eau à pression int cuve
        "ACC_PESA",
        "RHO_EAU20",
        "RHO_EAU60",
        "RHO_EAU307",
    ]

    _inst_name = ("T0", "T0b", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T8b", "T9")
    _subd_name = ("N0", "N0b", "N1", "N2", "N3", "N4", "N5", "N6", "N7", "N8", "N8b", "N9")
    _type_coeur = None
    _is_multi_rod = False
    _has_corner_mesh = False
    _len_mnt = 1.0

    @property
    def is_multi_rod(self):
        return self._is_multi_rod

    @property
    def has_corner_mesh(self):
        return self._has_corner_mesh

    @property
    def len_mnt(self):
        return self._len_mnt

    @property
    def type_coeur(self):
        return self._type_coeur

    @property
    def nb_cr_mesh(self):
        """Number of rods in mesh"""
        assert self.collAC.size > 0, "Parameter not set"
        ls_items = list(set((ac.nb_cr_mesh for ac in self.collAC)))
        assert len(ls_items) == 1, "Invalid mesh"
        return ls_items[0]

    @property
    def nb_tg_mesh(self):
        """Number of tubes in mesh"""
        assert self.collAC.size > 0, "Parameter not set"
        ls_items = list(set((ac.nb_tg_mesh for ac in self.collAC)))
        assert len(ls_items) == 1, "Invalid mesh"
        return ls_items[0]

    @property
    def NBGR(self):
        """Number of tubes in mesh"""
        assert self.collAC.size > 0, "Parameter not set"
        ls_items = list(set((ac.NBGR for ac in self.collAC)))
        assert len(ls_items) == 1, "Invalid mesh"
        return ls_items[0]

    def __init__(self, name, type_coeur, datg, longueur=None):
        """Initialisation d'un type de coeur."""
        self.name = name
        self._type_coeur = type_coeur
        self.NBAC = 0
        self.factory = ACFactory(datg)
        self.collAC = CollectionMAC3("AC")
        self._mateAC = {}
        self.temps_simu = {}.fromkeys(self._inst_name)
        self.temps_archiv = None
        self.sub_temps_simu = {}.fromkeys(self._subd_name)
        self._para = {}
        self._keys = {}.fromkeys(self.required_parameters)
        self._init_from_attrs()
        self.longueur = longueur

    def init_from_mesh(self, mesh):
        """Avoid recursion and add data from mesh. Load materials considering geometry."""
        self.recuperation_donnees_geom(mesh)

        update_materials = {
            "TG": self.nb_tg_mesh,
            "CR": self.nb_cr_mesh,
            "GC_ME": self.nb_cr_mesh,
            "GC_EB": self.nb_cr_mesh,
            "GC_EH": self.nb_cr_mesh,
            "MNT": self.len_mnt,
        }
        if self.has_corner_mesh:
            update_materials["DIL"] = 2.0 - 2.0**0.5

        self.load_materials(update_materials)

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

    def get_contactAssLame(self):
        return self.nomContactAssLame

    def get_contactCuve(self):
        return self.nomContactCuve

    def get_geom_coeur(self):
        """Retourne la géométrie du coeur."""
        raise NotImplementedError

    def watergap_toaster(self, gap):
        """Retourne la position de la lame d'eau DAMAC au format Aster."""

        data = gap.split("_")
        sz = len(data)
        errmsg = "Water Gap position error %s." % gap

        assert sz in (2, 3), errmsg
        tag = data[0]
        assert tag in ("RES", "CU"), errmsg

        if tag == "RES":
            ac1, ac2 = data[1][:3], data[1][3:]
            p1 = self.position_toaster(ac1).replace("_", "")
            p2 = self.position_toaster(ac2).replace("_", "")
            loc = f"{tag}_{p1}{p2}"
        else:
            ac1, orie = data[1], data[2]
            p1 = self.position_toaster(ac1).replace("_", "")
            loc = f"{tag}_{p1}_{orie}"

        return loc

    def watergap_todamac(self, gap):
        """Retourne la position de la lame d'eau Aster au format DAMAC."""
        data = gap.split("_")
        sz = len(data)
        errmsg = "Water Gap position error %s." % gap

        assert sz in (2, 3), errmsg
        tag = data[0]
        assert tag in ("RES", "CU"), errmsg

        if tag == "RES":
            ac1, ac2 = data[1][:2], data[1][2:]
            p1 = self.position_todamac("%s_%s" % (ac1[0], ac1[1]))
            p2 = self.position_todamac("%s_%s" % (ac2[0], ac2[1]))
            loc = f"{tag}_{p1}{p2}"
        else:
            ac1, orie = data[1], data[2]
            p1 = self.position_todamac("%s_%s" % (ac1[0], ac1[1]))
            loc = f"{tag}_{p1}_{orie}"

        return loc

    def position_toaster(self, position):
        """Retourne la position Aster correspondant à la position DAMAC."""
        raise NotImplementedError

    def position_todamac(self, position):
        """Retourne la position DAMAC correspondant à la position Aster."""
        raise NotImplementedError

    def position_fromthyc(self, posX, posY):
        """Retourne la position Aster correspondant à la position Thyc."""
        raise NotImplementedError

    def get_length(self):
        if self.longueur:
            l = len(self.ALPHA_MAC[: self.longueur])
        else:
            l = len(self.ALPHA_MAC)
        return l

    def get_pos_index(self, pos_aster):
        dir1, dir2 = pos_aster.split("_")
        return (self.ALPHA_MAC.index(dir1), self.ALPHA_MAC.index(dir2))

    def init_from_table(self, damactab):
        """Initialise le coeur à partir d'une table."""
        self.NBAC = len(damactab)
        for item in damactab:
            idAC = item["idAC"].strip()
            typeAC = item["Milieu"].strip()
            nameAC = item["Repere"].strip()

            ac = self.factory.get(typeAC)(self.type_coeur)
            ac.position_todamac = self.position_todamac
            ac.position_toaster = self.position_toaster
            ac.pos_damac = idAC
            ac.cycle = item["Cycle"]
            ac.name = nameAC
            for igr in range(ac._para.get("NBGR")):
                ac.bow["DY%d" % (igr + 1)] = item["XG%d" % (igr + 1)] / 1000.0
                ac.bow["DZ%d" % (igr + 1)] = item["YG%d" % (igr + 1)] / 1000.0

            ac.post_definition()
            ac.check()
            self.collAC[idAC] = ac

    def load_materials(self, update_materials={}):
        assert not self._mateAC
        for ac in self.collAC:
            ac.materiau = self._mateAC.setdefault(
                ac.typeAC, MateriauAC(ac.typeAC, update_materials)
            )

    ### CARAC
    def mcf_geom_fibre(self):
        """Retourne les mots-clés facteurs pour DEFI_GEOM_FIBRE."""
        return flat_list([ac.mcf_geom_fibre() for ac in self.collAC])

    def definition_geom_fibre(self):
        GFF = DEFI_GEOM_FIBRE(FIBRE=self.mcf_geom_fibre())
        return GFF

    def mcf_compor_fibre(self, GFF):
        return flat_list([ac.mcf_compor_fibre(GFF) for ac in self.collAC])

    def mcf_cara_multifibre(self):
        """Retourne les mots-clés facteurs pour AFFE_CARA_ELEM/MULTIFIBRE."""
        return flat_list([ac.mcf_cara_multifibre() for ac in self.collAC])

    def mcf_cara_barre(self):
        """Retourne les mots-clés facteurs pour AFFE_CARA_ELEM/BARRE."""
        return flat_list([ac.mcf_cara_barre() for ac in self.collAC])

    def mcf_cara_poutre(self):
        """Retourne les mots-clés facteurs pour AFFE_CARA_ELEM/POUTRE."""
        return flat_list([ac.mcf_cara_poutre() for ac in self.collAC])

    def mcf_cara_discret(self):
        """Retourne les mots-clés facteurs pour AFFE_CARA_ELEM/DISCRET."""
        return flat_list([ac.mcf_cara_discret() for ac in self.collAC])

    def mcf_deform_impo(self):
        """Retourne les mots-clés facteurs pour AFFE_CHAR_CINE/MECA_IMPO."""
        return flat_list([ac.mcf_deform_impo() for ac in self.collAC])

    def affe_char_lame(self, MODELE):
        _AF_CIN = AFFE_CHAR_CINE(MODELE=MODELE, MECA_IMPO=self.mcf_deform_impo())
        return _AF_CIN

    def mcf_archimede_nodal(self):
        """Retourne les mots-clés facteurs pour AFFE_CHAR_MECA/FORCE_NODALE."""
        return flat_list([ac.mcf_archimede_nodal() for ac in self.collAC])

    def definition_archimede_nodal(self, MODELE):
        _ARCH_1 = AFFE_CHAR_MECA(MODELE=MODELE, FORCE_NODALE=self.mcf_archimede_nodal())
        return _ARCH_1

    def mcf_archimede_poutre(self):
        """Retourne les mots-clés facteurs pour AFFE_CHAR_MECA_F/FORCE_POUTRE."""
        return flat_list([ac.mcf_archimede_poutre() for ac in self.collAC])

    def definition_archimede_poutre(self, MODELE):
        _FOARCH_1 = AFFE_CHAR_MECA_F(MODELE=MODELE, FORCE_POUTRE=self.mcf_archimede_poutre())
        return _FOARCH_1

    def definition_temp_archimede(self, use_archimede):
        """Valeur à froid (20 degrés) de la force d'Archimède = 860/985.46*1000.52"""
        assert self.temps_simu["T0"] is not None, "`definition_time` must be called first!"

        assert use_archimede in ("OUI", "NON")

        # cas ou la force d'archimede est activee
        gravity = self.ACC_PESA if use_archimede == "OUI" else 0.0

        ARCHFR1 = gravity * self.RHO_EAU20
        ARCHFR2 = gravity * self.RHO_EAU60
        ARCHCH = gravity * self.RHO_EAU307

        _ARCH_F1 = DEFI_FONCTION(
            NOM_PARA="INST",
            PROL_DROITE="CONSTANT",
            PROL_GAUCHE="CONSTANT",
            # fmt: off
            VALE=(
                self.temps_simu["T0"], ARCHFR1,
                self.temps_simu["T1"], ARCHFR1,
                self.temps_simu["T2"], ARCHFR2,
                self.temps_simu["T4"], ARCHCH,
                self.temps_simu["T5"], ARCHCH,
                self.temps_simu["T7"], ARCHFR2,
                self.temps_simu["T8"], ARCHFR1,
                self.temps_simu["T9"], ARCHFR1,
            ),
            # fmt: on
        )

        return _ARCH_F1

    def definition_temp_hydro_axiale(self, coef_mult_thv):
        """Fonction multiplicative de la force hydrodynamique axiale.
        On multiplie par 0.708 les forces hydrodynamiques a froid pour obtenir celles a chaud."""
        assert self.temps_simu["T0"] is not None, "`definition_time` must be called first!"
        FOHYFR_1 = 1.0 * coef_mult_thv  # Valeur a froid
        FOHYCH_1 = 0.708 * coef_mult_thv  # Valeur a chaud

        _HYDR_F1 = DEFI_FONCTION(
            NOM_PARA="INST",
            PROL_DROITE="CONSTANT",
            PROL_GAUCHE="CONSTANT",
            # fmt: off
            VALE=(
                self.temps_simu["T0"], 0.0,
                self.temps_simu["T1"], 0.0,
                self.temps_simu["T2"], FOHYFR_1,
                self.temps_simu["T3"], FOHYCH_1,
                self.temps_simu["T4"], FOHYCH_1,
                self.temps_simu["T5"], FOHYCH_1,
                self.temps_simu["T6"], FOHYCH_1,
                self.temps_simu["T7"], FOHYFR_1,
                self.temps_simu["T8"], 0.0,
                self.temps_simu["T9"], 0.0,
            ),
            # fmt: on
        )
        return _HYDR_F1

    def definition_effort_transverse(self, coef_mult_tht):
        """Fonction multiplicative pour la prise en compte des efforts transverses."""
        assert self.temps_simu["T0"] is not None, "`definition_time` must be called first!"
        AVEC = 1.0 * coef_mult_tht
        SANS = 0.0

        _F_TRAN1 = DEFI_FONCTION(
            NOM_PARA="INST",
            PROL_DROITE="CONSTANT",
            PROL_GAUCHE="CONSTANT",
            # fmt: off
            VALE=(
                self.temps_simu["T0"], SANS,
                self.temps_simu["T1"], SANS,
                self.temps_simu["T2"], SANS,
                self.temps_simu["T4"], AVEC,
                self.temps_simu["T5"], AVEC,
                self.temps_simu["T7"], SANS,
                self.temps_simu["T8"], SANS,
                self.temps_simu["T9"], SANS,
            ),
            # fmt: on
        )
        return _F_TRAN1

    def definition_cara_coeur(self, MODELE, GFF):
        mcm = self.mcf_cara_multifibre()
        mcr = self.mcf_cara_barre()
        mcp = self.mcf_cara_poutre()
        mcd = self.mcf_cara_discret()
        mtmp = _F(GROUP_MA="RES_TOT", REPERE="LOCAL", CARA="K_T_D_L", VALE=(0.0, 0.0, 0.0))
        mcd.append(mtmp)
        mtmp = _F(GROUP_MA="RES_TOT", REPERE="LOCAL", CARA="M_T_D_L", VALE=0.0)
        mcd.append(mtmp)

        _CARA = AFFE_CARA_ELEM(
            MODELE=MODELE,
            POUTRE=mcp,
            BARRE=mcr,
            GEOM_FIBRE=GFF,
            MULTIFIBRE=mcm,
            DISCRET=mcd,
            ORIENTATION=(
                _F(
                    GROUP_MA=("ELA_EX", "ELA_ME", "RIG_EX", "RIG_ME", "DIL"),
                    CARA="VECT_Y",
                    VALE=(1.0, 0.0, 0.0),
                ),
            ),
        )
        return _CARA

    def definition_pesanteur(self, MODELE):
        _PESA = AFFE_CHAR_MECA(
            MODELE=MODELE, PESANTEUR=_F(GRAVITE=9.81, DIRECTION=(-1.0, 0.0, 0.0))
        )
        return _PESA

    def definition_maintien_type(self, model, typ, force=None, compression_init=False):
        """Retourne le chargement dû au couvercle de la cuve selon le type"""
        assert typ in ("FORCE", "DEPL_PSC")
        if typ != "FORCE":
            head_load = self.definition_effor_maintien(model, compression_init)
        else:
            head_load = self.definition_effor_maintien_force(model, force, compression_init)

        return head_load

    def definition_effor_maintien(self, MODELE, compression_init):
        """Retourne les déplacements imposés aux noeuds modélisant la PSC
        et traduisant la fermeture de la cuve"""
        assert self.temps_simu["T0"] is not None, "`definition_time` must be called first!"

        if compression_init:
            _DXpsc = DEFI_FONCTION(
                NOM_PARA="INST",
                # fmt: off
                VALE=(
                    -2.0, 0.0,
                    -1.0, 0.0,
                    -0.75, -1.0 * self.flechResMaint,
                    -0.25, -1.0 * self.flechResMaint,
                    self.temps_simu["T0"], 0.0,
                    self.temps_simu["T0b"], 0.0,
                    self.temps_simu["T1"], -1.0 * self.flechResMaint,
                    self.temps_simu["T2"], -1.0 * self.flechResMaint,
                    self.temps_simu["T3"], -1.0 * self.flechResMaint,
                    self.temps_simu["T4"], -1.0 * self.flechResMaint,
                    self.temps_simu["T5"], -1.0 * self.flechResMaint,
                    self.temps_simu["T6"], -1.0 * self.flechResMaint,
                    self.temps_simu["T7"], -1.0 * self.flechResMaint,
                    self.temps_simu["T8"], -1.0 * self.flechResMaint,
                    self.temps_simu["T8b"], -1.0 * self.flechResMaint / 3.0,
                    self.temps_simu["T9"], 0.0,
                ),
                # fmt: on
                PROL_DROITE="CONSTANT",
                PROL_GAUCHE="CONSTANT",
            )
        else:
            _DXpsc = DEFI_FONCTION(
                NOM_PARA="INST",
                # fmt: off
                VALE=(
                    -2.0, 0.0,
                    -1.0, 0.0,
                    # -0.75,  -1. * self.flechResMaint,
                    # -0.25,  -1. * self.flechResMaint,
                    self.temps_simu["T0"], 0.0,
                    self.temps_simu["T0b"], 0.0,
                    self.temps_simu["T1"], -1.0 * self.flechResMaint,
                    self.temps_simu["T2"], -1.0 * self.flechResMaint,
                    self.temps_simu["T3"], -1.0 * self.flechResMaint,
                    self.temps_simu["T4"], -1.0 * self.flechResMaint,
                    self.temps_simu["T5"], -1.0 * self.flechResMaint,
                    self.temps_simu["T6"], -1.0 * self.flechResMaint,
                    self.temps_simu["T7"], -1.0 * self.flechResMaint,
                    self.temps_simu["T8"], -1.0 * self.flechResMaint,
                    self.temps_simu["T8b"], -1.0 * self.flechResMaint / 3.0,
                    self.temps_simu["T9"], 0.0,
                ),
                # fmt: on
                PROL_DROITE="CONSTANT",
                PROL_GAUCHE="CONSTANT",
            )

        _F_EMBO = AFFE_CHAR_CINE_F(MODELE=MODELE, MECA_IMPO=_F(GROUP_NO="PMNT_S", DX=_DXpsc))
        return _F_EMBO

    def definition_effor_maintien_force(self, MODELE, ForceMaintien, compression_init):
        """Retourne le chargement d'effort de maintien considéré constant"""
        assert self.temps_simu["T0"] is not None, "`definition_time` must be called first!"

        if compression_init:
            _FXpsc = DEFI_FONCTION(
                NOM_PARA="INST",
                # fmt: off
                VALE=(
                    -2.0, 0.0,
                    -1.0, 0.0,
                    -0.75, -1.0 * ForceMaintien,
                    -0.25, -1.0 * ForceMaintien,
                    self.temps_simu["T0"], 0.0,
                    self.temps_simu["T0b"], 0.0,
                    self.temps_simu["T1"], -1.0 * ForceMaintien,
                    self.temps_simu["T2"], -1.0 * ForceMaintien,
                    self.temps_simu["T3"], -1.0 * ForceMaintien,
                    self.temps_simu["T4"], -1.0 * ForceMaintien,
                    self.temps_simu["T5"], -1.0 * ForceMaintien,
                    self.temps_simu["T6"], -1.0 * ForceMaintien,
                    self.temps_simu["T7"], -1.0 * ForceMaintien,
                    self.temps_simu["T8"], -1.0 * ForceMaintien,
                    self.temps_simu["T8b"], -1.0 * ForceMaintien / 30.0,
                    self.temps_simu["T9"], 0.0,
                ),
                # fmt: on
                PROL_DROITE="CONSTANT",
                PROL_GAUCHE="CONSTANT",
            )
        else:
            _FXpsc = DEFI_FONCTION(
                NOM_PARA="INST",
                # fmt: off
                VALE=(
                    -2.0, 0.0,
                    -1.0, 0.0,
                    # -0.75, -1. * ForceMaintien,
                    # -0.25, -1. * ForceMaintien,
                    self.temps_simu["T0"], 0.0,
                    self.temps_simu["T0b"], 0.0,
                    self.temps_simu["T1"], -1.0 * ForceMaintien,
                    self.temps_simu["T2"], -1.0 * ForceMaintien,
                    self.temps_simu["T3"], -1.0 * ForceMaintien,
                    self.temps_simu["T4"], -1.0 * ForceMaintien,
                    self.temps_simu["T5"], -1.0 * ForceMaintien,
                    self.temps_simu["T6"], -1.0 * ForceMaintien,
                    self.temps_simu["T7"], -1.0 * ForceMaintien,
                    self.temps_simu["T8"], -1.0 * ForceMaintien,
                    self.temps_simu["T8b"], -1.0 * ForceMaintien / 30.0,
                    self.temps_simu["T9"], 0.0,
                ),
                # fmt: on
                PROL_DROITE="CONSTANT",
                PROL_GAUCHE="CONSTANT",
            )

        _F_EMBO = AFFE_CHAR_MECA_F(MODELE=MODELE, FORCE_NODALE=_F(GROUP_NO="PMNT_S", FX=_FXpsc))
        return _F_EMBO

    def affectation_maillage(self, MA0):

        gno_names = MA0.getGroupsOfNodes()
        gma_names = MA0.getGroupsOfCells()

        # Noeuds en liaison solide
        linked_total_nodes_names = [
            i for i in gno_names if i.startswith(("G_", "CREIBAS_", "TGBAS_", "TGHAUT_"))
        ]
        linked_total_nodes = set(MA0.getNodes(linked_total_nodes_names, localNumbering=True))

        # Noeuds avec déplacement imposé
        load_nodes_names = [i for i in gno_names if i.startswith("P_")]
        load_nodes = set(MA0.getNodes(load_nodes_names, localNumbering=True))

        # Ensemble des noeuds en liaison moins ceux avec déplacement imposé
        linked_local_nodes = linked_total_nodes - load_nodes

        # Creation des groupes complementaires des noeuds qui ne sont pas en liaison
        gno_all = set(range(MA0.getNumberOfNodes()))
        unlinked_total = gno_all - linked_total_nodes
        unlinked_local = gno_all - linked_local_nodes

        if "UNLINKED_TOTAL" not in gno_names:
            MA0.setGroupOfNodes("UNLINKED_TOTAL", tuple(unlinked_total))

        if "UNLINKED_LOCAL" not in gno_names:
            MA0.setGroupOfNodes("UNLINKED_LOCAL", tuple(unlinked_local))

        dict_grids = []
        grids_middle = []
        grids_extr = []
        grids_lock = []

        lsnbgrids = list(set(ac.NBGR for ac in self.collAC))
        assert len(lsnbgrids) == 1, "Invalid Mesh"
        nbgr = lsnbgrids[0]

        for ac in self.collAC:
            LIS_GNO = []
            for igr in range(ac.NBGR):
                LIS_GNO.append("G_%s_%d" % (ac.pos_aster, igr + 1))
                grids_lock.append("P_%s_%d" % (ac.pos_aster, igr + 1))

            dict_grids.append({"NOM_GROUP_MA": "GR_%s" % ac.pos_aster, "GROUP_NO": LIS_GNO})

        for igr in range(0, nbgr):
            grid_name = "GRIL_%d" % (igr + 1)
            dict_grids.append({"NOM_GROUP_MA": grid_name, "GROUP_NO": grid_name})
            if igr in (0, nbgr - 1):
                grids_extr.append(grid_name)
            else:
                grids_middle.append(grid_name)

        MA = CREA_MAILLAGE(MAILLAGE=MA0, CREA_POI1=tuple(dict_grids))

        if "GRIL_I" not in gma_names:
            gril_i = MA.getCells(tuple(set(grids_middle)))
            MA.setGroupOfCells("GRIL_I", gril_i)

        if "GRIL_E" not in gma_names:
            gril_e = MA.getCells(tuple(set(grids_extr)))
            MA.setGroupOfCells("GRIL_E", gril_e)

        if "LISPG" not in gno_names:
            lispg = MA.getNodes(tuple(set(grids_lock)), localNumbering=True)
            MA.setGroupOfNodes("LISPG", lispg)

        for gname in ("T_GUIDE", "EBOSUP", "EBOINF", "CRAYON", "ELA", "DIL", "MAINTIEN"):
            if gname not in gno_names:
                nodes_grp = MA.getNodesFromCells(gname, True)
                MA.setGroupOfNodes(gname, nodes_grp)

        return MA

    def check_groups(self, mesh):
        cu_groups = [i for i in mesh.getGroupsOfCells() if i.startswith("CU_")]
        if not set(cu_groups) == set(self.get_contactCuve()):
            return False
        return True

    def recuperation_donnees_geom(self, MAILL):
        """recuperation de donnees géometrique a partir du maillage"""

        # --- recuperation de donnees géometriques ---
        # nombre d'assemblages dans le coeur

        self.NBAC = self.collAC.size
        coords_x = MAILL.getCoordinates().toNumpy().T[0].copy()
        gcells = MAILL.getGroupsOfCells()
        gnodes = MAILL.getGroupsOfNodes()

        # Mailles MNT
        mnt_names = [i for i in gcells if i.startswith("MNT_")]
        mnt_nodes = MAILL.getNodesFromCells(mnt_names, True)
        mnt_x = set(coords_x[mnt_nodes])
        sz = len(mnt_x)
        assert sz == 2, "Invalid mesh %s" % sz
        self._len_mnt = round(max(mnt_x) - min(mnt_x), 8)

        self._is_multi_rod = len([i for i in gnodes if i.startswith("CREIBAS_")]) > 0
        self._has_corner_mesh = len([i for i in gcells if i.startswith("RES_COIN")]) > 0

        for ac in self.collAC:
            id_cr = "CR_%s" % ac.pos_aster
            grp_cr = [i for i in gcells if (i.startswith(id_cr) and i != id_cr)]
            ac.nb_cr_mesh = max(1, len(grp_cr))

            id_tg = "TG_%s" % ac.pos_aster
            grp_tg = [i for i in gcells if (i.startswith(id_tg) and i != id_tg)]
            ac.nb_tg_mesh = max(1, len(grp_tg))

            id_grid = "G_%s" % ac.pos_aster
            grp_grid = [i for i in gnodes if (i.startswith(id_grid) and i != id_grid)]
            ls_nodes_grid = list(set(len(MAILL.getNodes(i, localNumbering=True)) for i in grp_grid))
            sz = len(ls_nodes_grid)
            assert sz == 1, "Invalid mesh %d" % sz
            ac.nb_nodes_grid = ls_nodes_grid[0]
            logger.debug("<MAC3_COEUR>: nb_nodes_grid(%s) = %s" % (ac.pos_aster, ac.nb_nodes_grid))

        logger.debug("<MAC3_COEUR>: nb_cr_mesh = %s" % (self.nb_cr_mesh))
        logger.debug("<MAC3_COEUR>: nb_tg_mesh = %s" % (self.nb_tg_mesh))

        # altitudes mini et maxi de la cavité de coeur
        x_eboinf = coords_x[MAILL.getNodesFromCells("EBOINF", True)]
        self.XINFCUVE = x_eboinf.min()
        logger.debug("<MAC3_COEUR>: xinfcuve = %s" % (self.XINFCUVE))

        x_maintien = coords_x[MAILL.getNodesFromCells("MAINTIEN", True)]
        self.XSUPCUVE = x_maintien.max()
        logger.debug("<MAC3_COEUR>: xsupcuve = %s" % (self.XSUPCUVE))

        # altitudes mini et maxi, et longueur de l'ensemble des crayons
        x_crayon = coords_x[MAILL.getNodesFromCells("CRAYON", True)]
        self.XINFC = x_crayon.min()
        self.XSUPC = x_crayon.max()
        self.LONCR = self.XSUPC - self.XINFC
        logger.debug("<MAC3_COEUR>: xinfcrayon = %s" % (self.XINFC))
        logger.debug("<MAC3_COEUR>: xsupcrayon = %s" % (self.XSUPC))
        logger.debug("<MAC3_COEUR>: lcrayon = %s" % (self.LONCR))

        # altitudes mini et maxi, et longueur de l'ensemble des tubes
        x_tguide = coords_x[MAILL.getNodesFromCells("T_GUIDE", True)]
        self.XINFT = min(x_tguide)
        self.XSUPT = max(x_tguide)
        self.LONTU = self.XSUPT - self.XINFT
        logger.debug("<MAC3_COEUR>: xinftube = %s" % (self.XINFT))
        logger.debug("<MAC3_COEUR>: xsuptube = %s" % (self.XSUPT))
        logger.debug("<MAC3_COEUR>: ltube = %s" % (self.LONTU))

        # altitudes moyennes des grilles
        self.altitude = []
        for igr in range(self.NBGR):
            x_gr = coords_x[MAILL.getNodesFromCells("GRIL_%d" % (igr + 1), True)]
            h_gri = 0.5 * (x_gr.min() + x_gr.max())
            logger.debug("<MAC3_COEUR>: h_gri %s = %s" % (igr + 1, h_gri))
            self.altitude.append(h_gri)

    def cl_rigidite_grille(self):
        return [
            _F(GROUP_NO="G_%s_%d" % (ac.pos_aster, igr + 1))
            for ac in self.collAC
            for igr in range(ac._para["NBGR"])
        ]

    def cl_rigidite_embouts(self):

        rigi_einf = [
            _F(
                GROUP_NO=(
                    "CREIBAS_%s" % (ac.pos_aster),
                    "TGBAS_%s" % (ac.pos_aster),
                    "PI_%s" % (ac.pos_aster),
                )
            )
            for ac in self.collAC
        ]

        rigi_esup = [
            _F(GROUP_NO=("TGHAUT_%s" % ac.pos_aster, "PS_%s" % ac.pos_aster)) for ac in self.collAC
        ]

        return rigi_einf + rigi_esup

    def affectation_modele(self, MAILLAGE):
        _MODELE = AFFE_MODELE(
            MAILLAGE=MAILLAGE,
            AFFE=(
                _F(GROUP_MA=("CRAYON", "T_GUIDE"), PHENOMENE="MECANIQUE", MODELISATION="POU_D_TGM"),
                _F(
                    GROUP_MA=("EBOSUP", "EBOINF", "DIL"),
                    PHENOMENE="MECANIQUE",
                    MODELISATION="POU_D_E",
                ),
                _F(GROUP_MA=("ELA", "RIG"), PHENOMENE="MECANIQUE", MODELISATION="DIS_TR"),
                _F(
                    GROUP_MA=("GRIL_I", "GRIL_E", "RES_TOT", "CREI"),
                    PHENOMENE="MECANIQUE",
                    MODELISATION="DIS_T",
                ),
                _F(GROUP_MA=("MAINTIEN",), PHENOMENE="MECANIQUE", MODELISATION="BARRE"),
            ),
        )

        return _MODELE

    def definition_time(self, fluence=0.0, subdivis=1, nbSubdEchec=10):
        """Return the list of timesteps"""
        _LI = self.definition_time_arch(fluence, subdivis)

        if nbSubdEchec == 1:
            return _LI
        else:
            _TE = DEFI_LIST_INST(
                DEFI_LIST=_F(LIST_INST=_LI),
                ECHEC=(
                    _F(
                        EVENEMENT="ERREUR",
                        ACTION="DECOUPE",
                        SUBD_METHODE="MANUEL",
                        SUBD_PAS=4,
                        SUBD_NIVEAU=nbSubdEchec,
                        SUBD_PAS_MINI=1.0e-8,
                    ),
                    _F(
                        EVENEMENT="DIVE_RESI",
                        ACTION="DECOUPE",
                        SUBD_METHODE="MANUEL",
                        SUBD_PAS=4,
                        SUBD_NIVEAU=nbSubdEchec,
                        SUBD_PAS_MINI=1.0e-8,
                    ),
                ),
            )
            return _TE

    def definition_time_arch(self, fluence, subdivis):
        """Return the list of timesteps"""

        def m_time(iname, sname):
            # for debugging use NOMBRE=1
            m_time = (_F(JUSQU_A=self.temps_simu[iname], NOMBRE=int(self.sub_temps_simu[sname])),)
            return m_time

        self.init_temps_simu(fluence, subdivis)

        _list = []
        for iname, sname in zip(self._inst_name, self._subd_name):
            _list.extend(m_time(iname, sname))

        _LI = DEFI_LIST_REEL(DEBUT=-1, INTERVALLE=_list)
        return _LI

    def init_temps_simu(self, fluence, subdivis):
        """Initialise les temps caracteristiques"""
        Dt = 1.0e-3
        self.temps_simu["T0"] = 0.0
        self.temps_simu["T0b"] = self.temps_simu["T0"] + Dt / 2
        self.temps_simu["T1"] = self.temps_simu["T0"] + Dt
        self.temps_simu["T2"] = self.temps_simu["T1"] + Dt
        self.temps_simu["T3"] = self.temps_simu["T2"] + Dt
        self.temps_simu["T4"] = self.temps_simu["T3"] + Dt
        self.temps_simu["T5"] = self.temps_simu["T4"] + max(fluence, Dt)
        self.temps_simu["T6"] = self.temps_simu["T5"] + Dt
        self.temps_simu["T7"] = self.temps_simu["T6"] + Dt
        self.temps_simu["T8"] = self.temps_simu["T7"] + Dt
        self.temps_simu["T8b"] = self.temps_simu["T8"] + Dt / 2
        self.temps_simu["T9"] = self.temps_simu["T8"] + Dt

        self.sub_temps_simu["N0"] = 4
        self.sub_temps_simu["N0b"] = 1
        self.sub_temps_simu["N1"] = 2 * subdivis
        self.sub_temps_simu["N2"] = 2
        self.sub_temps_simu["N3"] = 2 * subdivis
        self.sub_temps_simu["N4"] = 2 * subdivis
        self.sub_temps_simu["N5"] = 50
        self.sub_temps_simu["N6"] = 2 * subdivis
        self.sub_temps_simu["N7"] = 2 * subdivis
        self.sub_temps_simu["N8"] = 2
        self.sub_temps_simu["N8b"] = 4 * subdivis
        self.sub_temps_simu["N9"] = 1

    def definition_fluence(self, fluence, MAILLAGE, fluence_cycle, lame=False):
        """Return the time evolution of the field of fluence"""
        assert self.temps_simu["T0"] is not None, "`definition_time` must be called first!"

        #
        # CREATION D UNE NAPPE DE FLUX NEUTRONIQUE DANS LE COEUR   #
        #
        # CREATION DE LA PARTIE GEOMETRIQUE        #
        #
        _CHXN = CREA_CHAMP(
            OPERATION="EXTR", TYPE_CHAM="NOEU_GEOM_R", NOM_CHAM="GEOMETRIE", MAILLAGE=MAILLAGE
        )

        #
        # CREATION DU PROFIL AXIAL DE FLUX   #
        #
        _FLUXAX1 = DEFI_FONCTION(
            NOM_PARA="X",
            # fmt: off
            VALE=(
                self.altitude[0], 0.54,
                self.altitude[1], 1.0,
                self.altitude[-3], 1.0,
                self.altitude[-2], 0.85,
                self.altitude[-1], 0.06,
            ),
            # fmt: on
            PROL_DROITE="CONSTANT",
            PROL_GAUCHE="CONSTANT",
        )

        #
        # DEFINITION DU CHAMP NEUTRONIQUE RADIAL (CONSTANT)        #
        #
        Y_1 = -1.0
        Y_2 = 1.0

        _FLY_1 = DEFI_FONCTION(
            NOM_PARA="Y", VALE=(Y_1, 1.0, Y_2, 1.0), PROL_DROITE="CONSTANT", PROL_GAUCHE="CONSTANT"
        )

        _FLY_2 = DEFI_FONCTION(
            NOM_PARA="Y", VALE=(Y_1, 1.0, Y_2, 1.0), PROL_DROITE="CONSTANT", PROL_GAUCHE="CONSTANT"
        )

        _FLUXRD1 = DEFI_NAPPE(
            NOM_PARA="Z",
            PARA=(Y_1, Y_2),
            FONCTION=(_FLY_1, _FLY_2),
            PROL_DROITE="CONSTANT",
            PROL_GAUCHE="CONSTANT",
        )

        # ------------------------------------------------
        # CREATION DU CHAMP ASSOCIE A LA FONCTION FLUXAX1
        # ------------------------------------------------
        _CH_FAX = CREA_CHAMP(
            OPERATION="AFFE",
            TYPE_CHAM="NOEU_NEUT_F",
            MAILLAGE=MAILLAGE,
            AFFE=(
                _F(
                    GROUP_MA=("T_GUIDE", "CRAYON", "ELA", "MAINTIEN"), NOM_CMP="X1", VALE_F=_FLUXAX1
                ),
            ),
        )

        _CH_FAXR = CREA_CHAMP(
            OPERATION="EVAL", TYPE_CHAM="NOEU_NEUT_R", CHAM_F=_CH_FAX, CHAM_PARA=_CHXN
        )

        # -----------------------------------------------
        # CREATION DU CHAMP ASSOCIE A LA FONCTION FLUXRD1
        # -----------------------------------------------
        _CH_FRD = CREA_CHAMP(
            OPERATION="AFFE",
            TYPE_CHAM="NOEU_NEUT_F",
            MAILLAGE=MAILLAGE,
            AFFE=(_F(TOUT="OUI", NOM_CMP="X2", VALE_F=_FLUXRD1),),
        )

        _CH_FRDR = CREA_CHAMP(
            OPERATION="EVAL", TYPE_CHAM="NOEU_NEUT_R", CHAM_F=_CH_FRD, CHAM_PARA=_CHXN
        )

        _MULT = FORMULE(NOM_PARA=("X1", "X2", "INST"), VALE="X1*X2*INST")

        _CHRES = CREA_CHAMP(
            OPERATION="AFFE",
            TYPE_CHAM="NOEU_NEUT_F",
            MAILLAGE=MAILLAGE,
            AFFE=(
                _F(GROUP_MA=("T_GUIDE", "CRAYON", "ELA", "MAINTIEN"), NOM_CMP="X1", VALE_F=_MULT),
            ),
        )

        # -----------------------------------------------------
        # CREATION DU CHAMP FLUENC1 ASSOCIE A LA LISTE LINST
        # -----------------------------------------------------
        mcfm = []
        mcf0 = []
        mcf1 = []
        for ac in self.collAC:
            (lgma, cyc) = ac.liste_gma_fluence()
            # pour calcul lame : on prend le nombre de cycle (e.g. assemblage neuf : 0)
            # pour calcul deformation : le nombre de cycle est celui donne
            #                           dans le DAMAC (donc en fin de cycle)
            #                           (e.g. assemblage neuf : 1)
            #                           il faut donc retrancher 1 au nombre de cycles
            if lame:
                nb_cycle = cyc
            else:
                nb_cycle = cyc - 1
            mtmpm = _F(GROUP_MA=lgma, NOM_CMP="INST", VALE=0.0)
            mtmp0 = _F(GROUP_MA=lgma, NOM_CMP="INST", VALE=nb_cycle * fluence_cycle)
            mtmp1 = _F(GROUP_MA=lgma, NOM_CMP="INST", VALE=nb_cycle * fluence_cycle + fluence)
            mcfm.append(mtmpm)
            mcf0.append(mtmp0)
            mcf1.append(mtmp1)

        _INST_M = CREA_CHAMP(
            OPERATION="AFFE", TYPE_CHAM="NOEU_INST_R", MAILLAGE=MAILLAGE, AFFE=mcfm
        )

        _REST_M = CREA_CHAMP(
            OPERATION="EVAL",
            TYPE_CHAM="NOEU_NEUT_R",
            CHAM_F=_CHRES,
            CHAM_PARA=(_CH_FAXR, _CH_FRDR, _INST_M),
        )

        _RES_M = CREA_CHAMP(
            OPERATION="ASSE",
            TYPE_CHAM="NOEU_IRRA_R",
            MAILLAGE=MAILLAGE,
            ASSE=(
                _F(
                    GROUP_MA=("T_GUIDE", "CRAYON", "ELA", "MAINTIEN"),
                    CHAM_GD=_REST_M,
                    NOM_CMP="X1",
                    NOM_CMP_RESU="IRRA",
                ),
            ),
        )

        _INST_0 = CREA_CHAMP(
            OPERATION="AFFE", TYPE_CHAM="NOEU_INST_R", MAILLAGE=MAILLAGE, AFFE=mcf0
        )

        _REST_0 = CREA_CHAMP(
            OPERATION="EVAL",
            TYPE_CHAM="NOEU_NEUT_R",
            CHAM_F=_CHRES,
            CHAM_PARA=(_CH_FAXR, _CH_FRDR, _INST_0),
        )

        _RES_0 = CREA_CHAMP(
            OPERATION="ASSE",
            TYPE_CHAM="NOEU_IRRA_R",
            MAILLAGE=MAILLAGE,
            ASSE=(
                _F(
                    GROUP_MA=("T_GUIDE", "CRAYON", "ELA", "MAINTIEN"),
                    CHAM_GD=_REST_0,
                    NOM_CMP="X1",
                    NOM_CMP_RESU="IRRA",
                ),
            ),
        )

        _INST_1 = CREA_CHAMP(
            OPERATION="AFFE", TYPE_CHAM="NOEU_INST_R", MAILLAGE=MAILLAGE, AFFE=mcf1
        )

        _REST_1 = CREA_CHAMP(
            OPERATION="EVAL",
            TYPE_CHAM="NOEU_NEUT_R",
            CHAM_F=_CHRES,
            CHAM_PARA=(_CH_FAXR, _CH_FRDR, _INST_1),
        )

        _RES_1 = CREA_CHAMP(
            OPERATION="ASSE",
            TYPE_CHAM="NOEU_IRRA_R",
            MAILLAGE=MAILLAGE,
            ASSE=(
                _F(
                    GROUP_MA=("T_GUIDE", "CRAYON", "ELA", "MAINTIEN"),
                    CHAM_GD=_REST_1,
                    NOM_CMP="X1",
                    NOM_CMP_RESU="IRRA",
                ),
            ),
        )

        _FLUENC = CREA_RESU(
            TYPE_RESU="EVOL_VARC",
            OPERATION="AFFE",
            AFFE=(
                _F(NOM_CHAM="IRRA", CHAM_GD=_RES_M, INST=-1, PRECISION=1.0e-8),
                _F(NOM_CHAM="IRRA", CHAM_GD=_RES_M, INST=-0.75, PRECISION=1.0e-8),
                _F(NOM_CHAM="IRRA", CHAM_GD=_RES_0, INST=-0.25, PRECISION=1.0e-8),
                _F(NOM_CHAM="IRRA", CHAM_GD=_RES_0, INST=self.temps_simu["T4"], PRECISION=1.0e-8),
                _F(NOM_CHAM="IRRA", CHAM_GD=_RES_1, INST=self.temps_simu["T5"], PRECISION=1.0e-8),
                _F(NOM_CHAM="IRRA", CHAM_GD=_RES_1, INST=self.temps_simu["T9"], PRECISION=1.0e-8),
            ),
        )

        return _FLUENC

    def mcf_crea_champ_dil(self):
        # AAA modifier Tref => -Tref
        mcf = []
        groups_ma_tini = []

        for ac in self.collAC:
            # boucle sur les grilles
            try:
                _alpha = ac._para["AL_DIL"]
                _dilatbu = ac._para["dilatBU"]
            except KeyError:
                _alpha = 1.0
                _dilatbu = [0.0] * ac._para["NBGR"]

            if all(i == 0.0 for i in _dilatbu):
                groups_ma_tini.extend(
                    ["DI_%s%d" % (ac.pos_aster, (igr + 1)) for igr in range(ac._para["NBGR"])]
                )
            else:
                for igr in range(0, ac._para["NBGR"]):
                    Ttmp_val = self.TP_REF - _dilatbu[igr] / _alpha
                    mtmp = (
                        (
                            _F(
                                NOM_CMP="TEMP",
                                GROUP_MA="DI_%s%d" % (ac.pos_aster, (igr + 1)),
                                VALE=Ttmp_val,
                            )
                        ),
                    )
                    mcf.extend(mtmp)

        if groups_ma_tini:
            Ttmp_val = self.TP_REF
            mtmp = ((_F(NOM_CMP="TEMP", GROUP_MA=groups_ma_tini, VALE=Ttmp_val)),)
            mcf.extend(mtmp)

        return mcf

    def definition_champ_temperature(self, MAILLAGE):
        """Return the time evolution of the field of temperature"""
        assert self.temps_simu["T0"] is not None, "`definition_time` must be called first!"

        #
        # Temperatures utiles pour les calculs sous flux neutronique #
        #
        # Temperature de reference #
        #
        # TP_REF   =
        # ARRET_FR =  arret a froid (temp moyenne cuve)
        # ARRET_CH =  arret a chaud (297.2 dans doc TF JD DC 1494)
        # c est une temperature moyenne en cuve

        # profil lineaire de temperature pour les TG
        # TP_TG1 = temperature TG pour xinft
        # TP_TG2 = temperature TG pour xsupt

        #
        # DEFINITION DES TEMPERATURES NODALES EVOLUTIVES   #
        #
        # TEMPERATURE DE REFERENCE (A L'ARRET)         #
        #

        _F_TP1_1 = DEFI_FONCTION(
            NOM_PARA="X",
            NOM_RESU="TEMP",
            PROL_DROITE="CONSTANT",
            PROL_GAUCHE="CONSTANT",
            VALE=(self.XINFT, self.TP_REF, self.XSUPT, self.TP_REF),
        )

        #
        # AFFECTATION DE REFENCE DU CHAMP DE TEMPERATURE  #
        # D UN AC (A l'ARRET)                 #
        #

        _CHTEM11 = CREA_CHAMP(
            TYPE_CHAM="NOEU_TEMP_F",
            MAILLAGE=MAILLAGE,
            OPERATION="AFFE",
            AFFE=(
                _F(
                    GROUP_NO=("T_GUIDE", "EBOSUP", "EBOINF", "CRAYON", "ELA", "DIL", "MAINTIEN"),
                    NOM_CMP="TEMP",
                    VALE_F=_F_TP1_1,
                ),
            ),
        )

        _CHTEM1N = CREA_CHAMP(
            OPERATION="ASSE",
            TYPE_CHAM="NOEU_NEUT_F",
            MAILLAGE=MAILLAGE,
            ASSE=_F(
                GROUP_NO=("T_GUIDE", "EBOSUP", "EBOINF", "CRAYON", "ELA", "DIL", "MAINTIEN"),
                CHAM_GD=_CHTEM11,
                NOM_CMP=("TEMP",),
                NOM_CMP_RESU=("X1",),
            ),
        )

        _CHXN = CREA_CHAMP(
            OPERATION="EXTR", TYPE_CHAM="NOEU_GEOM_R", NOM_CHAM="GEOMETRIE", MAILLAGE=MAILLAGE
        )

        _CHTEM1A = CREA_CHAMP(
            OPERATION="EVAL", CHAM_F=_CHTEM1N, CHAM_PARA=_CHXN, TYPE_CHAM="NOEU_NEUT_R"
        )

        _CHTEM1B = CREA_CHAMP(
            OPERATION="ASSE",
            TYPE_CHAM="NOEU_TEMP_R",
            MAILLAGE=MAILLAGE,
            ASSE=_F(
                GROUP_NO=("T_GUIDE", "EBOSUP", "EBOINF", "CRAYON", "ELA", "DIL", "MAINTIEN"),
                CHAM_GD=_CHTEM1A,
                NOM_CMP=("X1",),
                NOM_CMP_RESU=("TEMP",),
            ),
        )

        # champ de dilatation du a l'irradiation des grilles
        mcf_champ_dil = self.mcf_crea_champ_dil()

        _CHTEM1D = CREA_CHAMP(
            TYPE_CHAM="NOEU_TEMP_R", MAILLAGE=MAILLAGE, OPERATION="AFFE", AFFE=mcf_champ_dil
        )

        _CHTEM10 = CREA_CHAMP(
            OPERATION="ASSE",
            MAILLAGE=MAILLAGE,
            TYPE_CHAM="NOEU_TEMP_R",
            ASSE=(
                _F(
                    CHAM_GD=_CHTEM1B,
                    GROUP_NO=("T_GUIDE", "EBOSUP", "EBOINF", "CRAYON", "ELA", "MAINTIEN"),
                ),
                _F(CHAM_GD=_CHTEM1D, GROUP_MA="DIL"),
            ),
        )
        #
        # TEMPERATURE EN PHASE ARRET A FROID           #
        #

        _F_TP2_1 = DEFI_FONCTION(
            NOM_PARA="X",
            NOM_RESU="TEMP",
            PROL_DROITE="CONSTANT",
            PROL_GAUCHE="CONSTANT",
            VALE=(self.XINFT, self.ARRET_FR, self.XSUPT, self.ARRET_FR),
        )

        #
        # AFFECTATION DE REFENCE DU CHAMP DE TEMPERATURE  #
        # D UN AC PENDANT LA PHASE D'ARRET A FROID             #
        #

        _CHTEM21 = CREA_CHAMP(
            TYPE_CHAM="NOEU_TEMP_F",
            MAILLAGE=MAILLAGE,
            OPERATION="AFFE",
            AFFE=(
                _F(
                    GROUP_NO=("T_GUIDE", "EBOSUP", "EBOINF", "CRAYON", "ELA", "DIL", "MAINTIEN"),
                    NOM_CMP="TEMP",
                    VALE_F=_F_TP2_1,
                ),
            ),
        )

        #
        # TEMPERATURE EN PHASE ARRET A CHAUD           #
        #

        _F_TP3_1 = DEFI_FONCTION(
            NOM_PARA="X",
            NOM_RESU="TEMP",
            PROL_DROITE="CONSTANT",
            PROL_GAUCHE="CONSTANT",
            VALE=(self.XINFT, self.ARRET_CH, self.XSUPT, self.ARRET_CH),
        )

        #
        # AFFECTATION DE REFENCE DU CHAMP DE TEMPERATURE  #
        # D UN AC PENDANT LA PHASE D'ARRET A CHAUD             #
        #

        _CHTEM31 = CREA_CHAMP(
            TYPE_CHAM="NOEU_TEMP_F",
            MAILLAGE=MAILLAGE,
            OPERATION="AFFE",
            AFFE=(
                _F(
                    GROUP_NO=("T_GUIDE", "EBOSUP", "EBOINF", "CRAYON", "ELA", "DIL", "MAINTIEN"),
                    NOM_CMP="TEMP",
                    VALE_F=_F_TP3_1,
                ),
            ),
        )

        #
        # EVOLUTION DE LA TEMPERATURE DANS LES CRAYONS     #
        # PENDANT LA PHASE D'IRRADIATION             #
        #

        XX1 = self.XINFC
        XX2 = XX1 + self.LONCR * self.SXX2
        XX3 = XX1 + self.LONCR * self.SXX3
        XX4 = XX1 + self.LONCR

        _F_CR3 = DEFI_FONCTION(
            NOM_PARA="X",
            NOM_RESU="TEMP",
            PROL_DROITE="LINEAIRE",
            PROL_GAUCHE="LINEAIRE",
            VALE=(XX1, self.TXX1, XX2, self.TXX2, XX3, self.TXX3, XX4, self.TXX4),
        )

        #
        # EVOLUTION DE LA TEMPERATURE DANS LES TUBES-GUIDE #
        # ET AUTRES COMPOSANTS EN PHASE D'IRRADIATION      #
        #

        _F_TP4_1 = DEFI_FONCTION(
            NOM_PARA="X",
            NOM_RESU="TEMP",
            PROL_DROITE="CONSTANT",
            PROL_GAUCHE="CONSTANT",
            VALE=(self.XINFT, self.TP_TG1, self.XSUPT, self.TP_TG2),
        )

        _CHTEM41 = CREA_CHAMP(
            TYPE_CHAM="NOEU_TEMP_F",
            MAILLAGE=MAILLAGE,
            OPERATION="AFFE",
            AFFE=(
                _F(
                    GROUP_NO=("T_GUIDE", "EBOSUP", "EBOINF", "ELA", "DIL", "MAINTIEN"),
                    NOM_CMP="TEMP",
                    VALE_F=_F_TP4_1,
                ),
                _F(GROUP_NO="CRAYON", NOM_CMP="TEMP", VALE_F=_F_CR3),
            ),
        )

        _CHTH_1 = CREA_RESU(
            TYPE_RESU="EVOL_THER",
            OPERATION="AFFE",
            AFFE=(
                _F(NOM_CHAM="TEMP", CHAM_GD=_CHTEM10, INST=-1, PRECISION=1.0e-8),
                _F(NOM_CHAM="TEMP", CHAM_GD=_CHTEM41, INST=-0.75, PRECISION=1.0e-8),
                _F(NOM_CHAM="TEMP", CHAM_GD=_CHTEM41, INST=-0.25, PRECISION=1.0e-8),
                _F(NOM_CHAM="TEMP", CHAM_GD=_CHTEM11, INST=0.0, PRECISION=1.0e-8),
                _F(NOM_CHAM="TEMP", CHAM_GD=_CHTEM11, INST=self.temps_simu["T1"], PRECISION=1.0e-8),
                _F(NOM_CHAM="TEMP", CHAM_GD=_CHTEM21, INST=self.temps_simu["T2"], PRECISION=1.0e-8),
                _F(NOM_CHAM="TEMP", CHAM_GD=_CHTEM31, INST=self.temps_simu["T3"], PRECISION=1.0e-8),
                _F(NOM_CHAM="TEMP", CHAM_GD=_CHTEM41, INST=self.temps_simu["T4"], PRECISION=1.0e-8),
                _F(NOM_CHAM="TEMP", CHAM_GD=_CHTEM41, INST=self.temps_simu["T5"], PRECISION=1.0e-8),
                _F(NOM_CHAM="TEMP", CHAM_GD=_CHTEM31, INST=self.temps_simu["T6"], PRECISION=1.0e-8),
                _F(NOM_CHAM="TEMP", CHAM_GD=_CHTEM21, INST=self.temps_simu["T7"], PRECISION=1.0e-8),
                _F(NOM_CHAM="TEMP", CHAM_GD=_CHTEM11, INST=self.temps_simu["T8"], PRECISION=1.0e-8),
                _F(NOM_CHAM="TEMP", CHAM_GD=_CHTEM11, INST=self.temps_simu["T9"], PRECISION=1.0e-8),
            ),
        )

        return _CHTH_1

    def definition_materiau(self, MAILLAGE, GFF, FLUENCE, CHTH, CONTACT="NON", RATIO=1.0):

        mcf_affe_mater = self.mcf_coeur_mater(CONTACT, RATIO)
        mcf_affe_varc = self.mcf_coeur_varc(FLUENCE, CHTH)
        # Affectation des materiau dans le coeur
        _A_MAT = AFFE_MATERIAU(
            MAILLAGE=MAILLAGE,
            AFFE_VARC=mcf_affe_varc,
            AFFE=mcf_affe_mater,
            AFFE_COMPOR=self.mcf_compor_fibre(GFF),
        )
        return _A_MAT

    def mcf_coeur_varc(self, FLUENCE, CHTH):
        mcf = []
        # variable de commande d'irradiation
        _VARCIRR = (
            _F(NOM_VARC="IRRA", TOUT="OUI", EVOL=FLUENCE, PROL_DROITE="CONSTANT"),
            _F(
                NOM_VARC="TEMP", TOUT="OUI", EVOL=CHTH, PROL_DROITE="CONSTANT", VALE_REF=self.TP_REF
            ),
        )
        mcf.extend(_VARCIRR)

        for ac in self.collAC:
            try:
                _alpha = ac._para["AL_DIL"]
                _dilatbu = ac._para["dilatBU"]

                if not all(i == 0.0 for i in _dilatbu):
                    for igr in range(ac._para["NBGR"]):
                        Ttmp = self.TP_REF - _dilatbu[igr] / _alpha
                        mtmp = (
                            (
                                _F(
                                    NOM_VARC="TEMP",
                                    GROUP_MA="DI_%s%d" % (ac.pos_aster, (igr + 1)),
                                    EVOL=CHTH,
                                    PROL_DROITE="CONSTANT",
                                    VALE_REF=Ttmp,
                                )
                            ),
                        )
                        mcf.extend(mtmp)

            except KeyError:
                pass

        return mcf

    def mcf_coeur_mater(self, CONTACT, RATIO):

        if CONTACT == "OUI":
            _M_RES = DEFI_MATERIAU(DIS_CONTACT=_F(RIGI_NOR=1.0e9 * RATIO + 1.0e1 * (1.0 - RATIO)))
            _M_COIN = DEFI_MATERIAU(
                DIS_CONTACT=_F(
                    RIGI_NOR=1.0e9 * RATIO + 1.0e1 * (1.0 - RATIO),
                    CONTACT="COIN_2D",
                    PRECISION=(1.0e-02, 1.0e-05, 1.0e-05),
                )
            )
        else:
            _M_RES = DEFI_MATERIAU(DIS_CONTACT=_F(RIGI_NOR=1.0e1))
            _M_COIN = DEFI_MATERIAU(
                DIS_CONTACT=_F(
                    RIGI_NOR=1.0e1, CONTACT="COIN_2D", PRECISION=(1.0e-02, 1.0e-05, 1.0e-05)
                )
            )

        mcf = flat_list([ac.mcf_AC_mater() for ac in self.collAC])
        mcf.extend((_F(GROUP_MA="RES_TOT", MATER=_M_RES),))
        if self.has_corner_mesh:
            mcf.extend((_F(GROUP_MA="RES_COIN", MATER=_M_COIN),))

        return mcf

    def dilatation_cuve(
        self, MODEL, MAILL, is_char_ini=False, maintien_grille=False, T_CONST_CUVE=None
    ):
        """Retourne les déplacements imposés aux noeuds modélisant les internes de cuves
        (supports inférieur (PIC ou FSC), supérieur (PSC) et cloisons)
        et traduisant les dilatations thermiques des internes
        et leurs deformations de natures mecaniques"""

        err_msg = "`definition_time` must be called first!"
        assert self.temps_simu["T0"] is not None, err_msg

        # definition des evolutions de températures
        # sur la PIC/FSC, la PSC et l'enveloppe
        _TEMPPIC = DEFI_FONCTION(
            NOM_PARA="INST",
            NOM_RESU="TEMP",
            # fmt: off
            VALE=(
                -2.0, self.TP_REF,
                -1.0, self.TP_REF,
                self.temps_simu["T0"], self.TP_REF,
                self.temps_simu["T1"], self.TP_REF,
                self.temps_simu["T2"], self.ARRET_FR,
                self.temps_simu["T3"], T_CONST_CUVE or self.ARRET_CH,
                self.temps_simu["T4"], T_CONST_CUVE or self.TINFCUVE,
                self.temps_simu["T5"], T_CONST_CUVE or self.TINFCUVE,
                self.temps_simu["T6"], T_CONST_CUVE or self.ARRET_CH,
                self.temps_simu["T7"], self.ARRET_FR,
                self.temps_simu["T8"], self.TP_REF,
                self.temps_simu["T9"], self.TP_REF,
            ),
            # fmt: on
            PROL_DROITE="CONSTANT",
            PROL_GAUCHE="CONSTANT",
        )

        _TEMPPSC = DEFI_FONCTION(
            NOM_PARA="INST",
            NOM_RESU="TEMP",
            # fmt: off
            VALE=(
                -2.0, self.TP_REF,
                -1.0, self.TP_REF,
                self.temps_simu["T0"], self.TP_REF,
                self.temps_simu["T1"], self.TP_REF,
                self.temps_simu["T2"], self.ARRET_FR,
                self.temps_simu["T3"], T_CONST_CUVE or self.ARRET_CH,
                self.temps_simu["T4"], T_CONST_CUVE or self.TSUPCUVE,
                self.temps_simu["T5"], T_CONST_CUVE or self.TSUPCUVE,
                self.temps_simu["T6"], T_CONST_CUVE or self.ARRET_CH,
                self.temps_simu["T7"], self.ARRET_FR,
                self.temps_simu["T8"], self.TP_REF,
                self.temps_simu["T9"], self.TP_REF,
            ),
            # fmt: on
            PROL_DROITE="CONSTANT",
            PROL_GAUCHE="CONSTANT",
        )

        _TEMPENV = DEFI_FONCTION(
            NOM_PARA="INST",
            NOM_RESU="TEMP",
            # fmt: off
            VALE=(
                -2.0, self.TP_REF,
                -1.0, self.TP_REF,
                self.temps_simu["T0"], self.TP_REF,
                self.temps_simu["T1"], self.TP_REF,
                self.temps_simu["T2"], self.ARRET_FR,
                self.temps_simu["T3"], T_CONST_CUVE or self.ARRET_CH,
                self.temps_simu["T4"], T_CONST_CUVE or self.TENVELOP,
                self.temps_simu["T5"], T_CONST_CUVE or self.TENVELOP,
                self.temps_simu["T6"], T_CONST_CUVE or self.ARRET_CH,
                self.temps_simu["T7"], self.ARRET_FR,
                self.temps_simu["T8"], self.TP_REF,
                self.temps_simu["T9"], self.TP_REF,
            ),
            # fmt: on
            PROL_DROITE="CONSTANT",
            PROL_GAUCHE="CONSTANT",
        )

        # Donnees geometriques
        # coordonnees centre cuve
        _TABG = RECU_TABLE(CO=MAILL, NOM_TABLE="CARA_GEOM")
        xmin = _TABG["X_MIN", 1]
        xmax = _TABG["X_MAX", 1]
        ymin = _TABG["Y_MIN", 1]
        ymax = _TABG["Y_MAX", 1]
        zmin = _TABG["Z_MIN", 1]
        zmax = _TABG["Z_MAX", 1]
        Y0 = (ymin + ymax) / 2.0
        Z0 = (zmin + zmax) / 2.0
        # rayon de la PSC
        radius_psc = (ymax - ymin) / 2.0

        # interpolation linéaire du coefficient de dilatation
        # des internes de cuve en fonction de la température
        alpha_part = "({alpha1:e} * func_temp_part(INST) + {alpha2:e})".format(
            alpha1=self.ALPH1, alpha2=self.ALPH2
        )

        # ---------------------------------------------------------------
        # --                  Dilatations radiales                     --
        # --      du cloisonnement, de la PIC/FSC, et de la PSC        --
        # ---------------------------------------------------------------
        ac_pos = "(sqrt(((Y - {y0:f})**2) + ((Z - {z0:f})**2)))".format(y0=Y0, z0=Z0)

        epsilon = 1.0e-6
        # on rentre un epsilon pour le cas où L=0 (assemblage central)
        # pour éviter la division par zéro
        ac_pos_cos = "(Y - {y0:f})/({dist} + {eps:e})".format(y0=Y0, eps=epsilon, dist=ac_pos)
        ac_pos_sin = "(Z - {z0:f})/({dist} + {eps:e})".format(z0=Z0, eps=epsilon, dist=ac_pos)

        ac_pos_dilat = "{radial_pos} * {alpha} * (func_temp_part(INST) - {t_ref:f})".format(
            radial_pos=ac_pos, alpha=alpha_part, t_ref=self.TP_REF
        )
        dilat_function_Y = "{radius} * {coef}".format(radius=ac_pos_dilat, coef=ac_pos_cos)
        dilat_function_Z = "{radius} * {coef}".format(radius=ac_pos_dilat, coef=ac_pos_sin)

        _DthYenv = FORMULE(
            NOM_PARA=("X", "Y", "Z", "INST"), VALE=dilat_function_Y, func_temp_part=_TEMPENV
        )

        _DthZenv = FORMULE(
            NOM_PARA=("X", "Y", "Z", "INST"), VALE=dilat_function_Z, func_temp_part=_TEMPENV
        )

        _DthYpic = FORMULE(
            NOM_PARA=("X", "Y", "Z", "INST"), VALE=dilat_function_Y, func_temp_part=_TEMPPIC
        )

        _DthZpic = FORMULE(
            NOM_PARA=("X", "Y", "Z", "INST"), VALE=dilat_function_Z, func_temp_part=_TEMPPIC
        )

        _DthYpsc = FORMULE(
            NOM_PARA=("X", "Y", "Z", "INST"), VALE=dilat_function_Y, func_temp_part=_TEMPPSC
        )

        _DthZpsc = FORMULE(
            NOM_PARA=("X", "Y", "Z", "INST"), VALE=dilat_function_Z, func_temp_part=_TEMPPSC
        )

        # ---------------------------------------------------------------
        # --                  Deplacements verticaux                   --
        # --                      de la PIC/FSC                        --
        # ---------------------------------------------------------------
        # le déplacement de la PIC est égal à la différence de hauteur de cavité
        # (entre l'instant "cuve fermée à 20C"et l'instant considéré)
        #
        # centre du coeur
        _DthXpicCentre = DEFI_FONCTION(
            NOM_PARA="INST",
            # fmt: off
            VALE=(
                -2.0, 0.0,
                -1.0, 0.0,
                self.temps_simu["T0"], 0.0,
                self.temps_simu["T0b"], 0.0,
                self.temps_simu["T1"], self.Hcav1centre - self.Hcav1centre,
                self.temps_simu["T2"], self.Hcav1centre - self.Hcav2centre,
                self.temps_simu["T3"], self.Hcav1centre - self.Hcav3centre,
                self.temps_simu["T4"], self.Hcav1centre - self.Hcav4centre,
                self.temps_simu["T5"], self.Hcav1centre - self.Hcav4centre,
                self.temps_simu["T6"], self.Hcav1centre - self.Hcav3centre,
                self.temps_simu["T7"], self.Hcav1centre - self.Hcav2centre,
                self.temps_simu["T8"], self.Hcav1centre - self.Hcav1centre,
                self.temps_simu["T9"], 0.0,
            ),
            # fmt: on
            PROL_DROITE="CONSTANT",
            PROL_GAUCHE="CONSTANT",
        )
        # peripherie du coeur
        _DthXpicPeriph = DEFI_FONCTION(
            NOM_PARA="INST",
            # fmt: off
            VALE=(
                -2.0, 0.0,
                -1.0, 0.0,
                self.temps_simu["T0"], 0.0,
                self.temps_simu["T0b"], 0.0,
                self.temps_simu["T1"], self.Hcav1periph - self.Hcav1periph,
                self.temps_simu["T2"], self.Hcav1periph - self.Hcav2periph,
                self.temps_simu["T3"], self.Hcav1periph - self.Hcav3periph,
                self.temps_simu["T4"], self.Hcav1periph - self.Hcav4periph,
                self.temps_simu["T5"], self.Hcav1periph - self.Hcav4periph,
                self.temps_simu["T6"], self.Hcav1periph - self.Hcav3periph,
                self.temps_simu["T7"], self.Hcav1periph - self.Hcav2periph,
                self.temps_simu["T8"], self.Hcav1periph - self.Hcav1periph,
                self.temps_simu["T9"], 0.0,
            ),
            # fmt: on
            PROL_DROITE="CONSTANT",
            PROL_GAUCHE="CONSTANT",
        )

        f_DthXpic = (
            "((dx_ext(INST) - dx_int(INST)) / ({radius:f}**2) * ({dist})**2 + dx_int(INST))".format(
                radius=radius_psc, dist=ac_pos
            )
        )

        _DthXpic = FORMULE(
            NOM_PARA=("X", "Y", "Z", "INST"),
            VALE=f_DthXpic,
            dx_ext=_DthXpicPeriph,
            dx_int=_DthXpicCentre,
        )

        # ---------------------------------------------------------------
        # --                Deplacements  verticaux                    --
        # --               des noeuds du cloisonnement                 --
        # ---------------------------------------------------------------

        f_DthX = "(-1. * dx_ext(INST) / ({x_max:f} - {x_min:f}) * X + dx_ext(INST))".format(
            x_min=self.XINFCUVE, x_max=self.XSUPCUVE
        )

        _DthXenv = FORMULE(NOM_PARA=("X", "INST"), VALE=f_DthX, dx_ext=_DthXpicPeriph)

        # ---------------------------------------------------------------
        # --                  chargement resultant                     --
        # ---------------------------------------------------------------
        if is_char_ini:
            _dilatation = AFFE_CHAR_CINE_F(
                MODELE=MODEL,
                MECA_IMPO=(_F(GROUP_NO="FIX", DX=_DthXpic), _F(GROUP_NO="P_CUV", DX=_DthXenv)),
            )
        else:
            if maintien_grille:
                _dilatation = AFFE_CHAR_CINE_F(
                    MODELE=MODEL,
                    MECA_IMPO=(
                        _F(GROUP_NO="FIX", DX=_DthXpic, DY=_DthYpic, DZ=_DthZpic),
                        _F(GROUP_NO="PMNT_S", DY=_DthYpsc, DZ=_DthZpsc),
                        _F(GROUP_NO="LISPG", DY=_DthYpsc, DZ=_DthZpsc),
                        _F(GROUP_NO="P_CUV", DX=_DthXenv, DY=_DthYenv, DZ=_DthZenv),
                    ),
                )
            else:
                _dilatation = AFFE_CHAR_CINE_F(
                    MODELE=MODEL,
                    MECA_IMPO=(
                        _F(GROUP_NO="FIX", DX=_DthXpic, DY=_DthYpic, DZ=_DthZpic),
                        _F(GROUP_NO="PMNT_S", DY=_DthYpsc, DZ=_DthZpsc),
                        _F(GROUP_NO="P_CUV", DX=_DthXenv, DY=_DthYenv, DZ=_DthZenv),
                    ),
                )

        return _dilatation


class CoeurFactory(Mac3Factory):
    """Classe pour construire les objets Coeur."""

    # Ex.: La classe "Coeur" sera nommée Coeur_900 dans le fichier
    # Coeur_900.datg
    prefix = "Coeur_"

    @classmethod
    def build(cls, type_coeur, sdtab, longueur=None):
        """Return a `Coeur` object of the given type"""
        rcdir = ExecutionParameter().get_option("rcdir")
        datg = osp.join(rcdir, "datg")
        factory = cls(datg)
        # prepare the Table object
        damactab = sdtab.EXTR_TABLE()
        name = damactab.para[0]
        damactab.Renomme(name, "idAC")
        coeur = factory.get(type_coeur)(name, type_coeur, datg, longueur)
        coeur.init_from_table(damactab)
        return coeur

    @classmethod
    def buildFromMesh(
        cls, type_coeur, sdtab, mesh, contact="NON", fluence_level=0.0, longueur=None
    ):

        core = CoeurFactory.build(type_coeur, sdtab, longueur)
        model = core.affectation_modele(mesh)
        core.init_from_mesh(mesh)
        gfibre = core.definition_geom_fibre()
        carael = core.definition_cara_coeur(model, gfibre)
        timeline = core.definition_time(fluence_level)
        fluence = core.definition_fluence(fluence_level, mesh, 0.0)
        tempfield = core.definition_champ_temperature(mesh)
        mater = core.definition_materiau(mesh, gfibre, fluence, tempfield, CONTACT=contact)

        return model, carael, mater

    def build_supported_types(self):
        """Construit la liste des types autorisés."""
        ctxt = {}
        for obj, val in list(globals().items()):
            if isinstance(val, type) and issubclass(val, Coeur):
                ctxt[obj] = val
        return ctxt


class MateriauAC:
    """Conteneur des matériaux d'un assemblage."""

    _types = ("DIL", "MNT", "ES", "EI", "CR", "TG", "GC_ME", "GC_EB", "GC_EH")

    def __init__(self, typeAC, update_values):
        """Initialisation"""
        self.typeAC = typeAC
        self._mate = {}
        self.include_materiau(update_values)

    def __getitem__(self, para):
        """Retourne le matériau pour un composant."""
        if self._mate.get(para) is None:
            raise KeyError("Material not defined : '%s'" % para)
        return self._mate.get(para)

    def include_materiau(self, update_values):
        """Crée les matériaux"""

        for typ in self._types:
            cmult = update_values.get(typ, 1.0)
            logger.debug("<MAC3_COEUR>: Loading material %s with CMULT %s" % (typ, cmult))
            self._mate[typ] = INCLUDE_MATERIAU(
                NOM_AFNOR="%s_%s" % (self.typeAC, typ),
                TYPE_MODELE="REF",
                VARIANTE="A",
                TYPE_VALE="NOMI",
                COEF_MULT=cmult,
            )
