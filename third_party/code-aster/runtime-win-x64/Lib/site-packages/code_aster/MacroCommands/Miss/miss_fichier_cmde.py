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


"""Construction d'un fichier de commandes Miss"""

import os
import os.path as osp
import re
import tempfile
from math import sqrt
from pprint import pformat

from .miss_domain import MissDomains
from .miss_utils import dict_format


class MissCmdeGenerator:
    """Construit un fichier de commandes Miss"""

    _dbg = False

    def __init__(self, param, struct, filename_callback):
        """Initialisation
        `filename_callback` fournit un nom de fichier 'local' pour un
        type donné"""
        self.param = param
        self.fname = filename_callback
        self.dinf = {
            "titre": struct.titre,
            "fich_mvol": self.fname("mvol"),
            "fich_chp": self.fname("chp"),
            "fich_sol": self.fname("sol"),
            "fich_impe": self.fname("resu_impe"),
            "fich_forc": self.fname("resu_forc"),
            "fich_ext": self.fname("ext"),
            "binaire": "",
            "surf": "",
            "rfic": "",
        }
        if self.param["AUTO"] == "OUI":
            if self.param["OPTION_RFIC"] == "OUI":
                self.dinf["rfic"] = str(self.param["RFIC"])
        else:
            if self.param["RFIC"] != 0.0:
                self.dinf["rfic"] = str(self.param["RFIC"])

        if self.param["TYPE"] == "BINAIRE":
            self.dinf["binaire"] = "BINA"
        if self.param["SURF"] == "OUI":
            self.dinf["surf"] = "SURF"

        self.domain = MissDomains(
            self.param["_hasPC"], self.param["ISSF"] == "OUI", self.param["_hasSL"]
        )
        # lignes du fichier
        self.lines = []
        # pour savoir si forces/impédances ont été calculées
        self._impe_calc = False
        self._forc_calc = False

    def build(self):
        """Construit et retourne le fichier"""
        lines = ["* Debut de l etude Miss", "* ---------------------"]
        lines.extend(self.build_data())
        lines.extend(self.build_calcul())
        lines.extend(self.build_post())
        lines.extend(["*", "* Fin de l etude Miss", "* -------------------", "FIN"])
        content = os.linesep.join(lines)
        text = remove_empty_lines(content)
        if self._dbg:
            dtmp = tempfile.mkdtemp(prefix=self.param["PROJET"] + "_")
            with open(osp.join(dtmp, "command"), "w") as f:
                f.write(text)
            with open(osp.join(dtmp, "para"), "w") as f:
                f.write(pformat(self.param))
            print("#dbg command file:", osp.join(dtmp, "command"))
        return text

    def build_data(self):
        """Définition du menu DATA"""
        lines = [
            "*",
            "* Nom generique des fichiers MISS",
            "* --------------------------------",
            "GENER %s" % self.param["PROJET"],
            "*",
            "* Debut du menu DATA",
            "* ------------------",
            "DATA",
            "*",
            "* Titre de l etude",
            "*-----------------",
            "TITRE",
            "%s" % self.dinf["titre"],
            "*",
            "* Lecture du maillage",
            "*--------------------",
            "MVOL %s" % self.dinf["fich_mvol"],
        ]
        lines.extend(self.bloc_group())
        lines.extend(self.bloc_modes())
        lines.extend(self.bloc_integr())
        lines.extend(self.bloc_lfreq())
        lines.extend(self.bloc_domain())
        lines.extend(["*", "* Fin du menu DATA", "* ----------------", "FIND"])
        return lines

    def build_calcul(self):
        """Définition des calculs"""
        lines = ["*", "* Debut de l execution", "* --------------------"]
        lines.extend(self.calcul_champ_incident())
        _use_bcle_freq = self.param["ISSF"] == "OUI" or self.param["_hasPC"]
        if _use_bcle_freq:
            lines.extend(
                [
                    "*",
                    "* Boucle sur les frequences",
                    "* -------------------------",
                    "DOFReq TOUTES SAVE MVFD TOT UI TUI IMPD FORCE",
                ]
            )
        lines.extend(self._chargement_domaine("sol"))
        lines.extend(self.calcul_fonction_green())
        lines.extend(self.calcul_champs())
        lines.extend(self.calcul_global())
        if _use_bcle_freq:
            lines.extend(
                [
                    "*",
                    "* Fin de la boucle sur les frequences",
                    "* -----------------------------------",
                    "ENDFreq",
                ]
            )
        lines.extend(["*", "* Fin de l execution", "* ------------------"])
        return lines

    def build_post(self):
        """Définition des post-traitements"""
        lines = ["*", "* Debut du post-traitement", "* ------------------------"]
        if not self.param["_hasPC"]:
            if self._impe_calc:
                lines.extend(
                    [
                        "*",
                        "* Post-traitement des impédances",
                        "* ------------------------------",
                        "POST",
                        "FICH %s  %s" % (self.dinf["fich_impe"], self.dinf["binaire"]),
                        "IMPDC",
                        "FREQ TOUTES",
                        "CHPU TOUS",
                        "CHPT TOUS",
                        "FINP",
                    ]
                )
            if self._forc_calc:
                lines.extend(
                    [
                        "*",
                        "* Post-traitement des forces sismiques",
                        "* ------------------------------------",
                        "POST",
                        "FICH %s" % self.dinf["fich_forc"],
                        "FORCE",
                        "FREQ TOUTES",
                        "DDL TOUS",
                        "UI TOUS",
                        "FINP",
                    ]
                )
        else:
            if self.param["ISSF"] == "OUI":
                nbmode = self.param["NBM_TOT"]
            else:
                nbmode = self.param["NBM_STA"]
            lcham = self.param["TOUT_CHAM"] == "OUI"
            if self.param["_calc_impe"]:
                lines.extend(
                    [
                        "*",
                        "* Post-traitement des impédances",
                        "* ------------------------------",
                        "POST",
                        "FICH %s  %s" % (self.dinf["fich_impe"], self.dinf["binaire"]),
                        "IMPDC",
                        "FREQ TOUTES",
                        "CHPU  DE    1 A    %d  PAS 1" % nbmode,
                        "CHPT DE    1 A    %d  PAS 1" % nbmode,
                        "FINP",
                    ]
                )
            if self.param["_calc_forc"]:
                lines.extend(
                    [
                        "*",
                        "* Post-traitement des forces sismiques",
                        "* ------------------------------------",
                        "POST",
                        "FICH %s" % self.dinf["fich_forc"],
                        "FORCE",
                        "FREQ TOUTES",
                        "DDL  DE    1 A    %d  PAS 1" % nbmode,
                        "UI TOUS",
                        "FINP",
                    ]
                )
            lines.extend(
                [
                    "*",
                    "* Definition du signal",
                    "* --------------------",
                    "SIGNAL LIRE %s" % self.fname("01.sign"),
                ]
            )
            lines.extend(self._chargement_domaine("sol"))
            if lcham:
                lines.extend(
                    [
                        "*",
                        "* Post-traitement aux points de controle",
                        "* --------------------------------------",
                        "POST",
                        ("SPEC NF=%%%(I)s FMAX=%%%(R)s" % dict_format)
                        % (self.param["_nbfreq"], self.param["FREQ_MAX"]),
                        "FICH %s" % self.fname("01.csol.a"),
                        "CSOL LEGENDE ACCELERATIONS",
                        "FREQ TOUTES",
                        "CHAMP DE    1 A    3  PAS 1",
                        "POINTS DE    1 A    %d  PAS 1" % self.param["_nbPC"],
                        "DDL TOUS",
                        "FINS",
                        "*",
                        ("SPEC NF=%%%(I)s FMAX=%%%(R)s" % dict_format)
                        % (self.param["_nbfreq"], self.param["FREQ_MAX"]),
                        "FICH %s" % self.fname("01.csol.v"),
                        "CSOL LEGENDE VITESSES",
                        "FREQ TOUTES",
                        "CHAMP DE    1 A    3  PAS 1",
                        "POINTS DE    1 A    %d  PAS 1" % self.param["_nbPC"],
                        "DDL TOUS",
                        "FINS",
                        "*",
                        ("SPEC NF=%%%(I)s FMAX=%%%(R)s" % dict_format)
                        % (self.param["_nbfreq"], self.param["FREQ_MAX"]),
                        "FICH %s" % self.fname("01.csol.d"),
                        "CSOL LEGENDE DEPLACEMENTS",
                        "FREQ TOUTES",
                        "CHAMP DE    1 A    3  PAS 1",
                        "POINTS DE    1 A    %d  PAS 1" % self.param["_nbPC"],
                        "DDL TOUS",
                        "FINS",
                        "*",
                        "FINP",
                    ]
                )
            else:
                lines.extend(
                    [
                        "*",
                        "* Post-traitement aux points de controle",
                        "* --------------------------------------",
                        "POST",
                        ("SPEC NF=%%%(I)s FMAX=%%%(R)s" % dict_format)
                        % (self.param["_nbfreq"], self.param["FREQ_MAX"]),
                        "FICH %s" % self.fname("01.csol.a"),
                        "CSOL LEGENDE ACCELERATIONS",
                        "FREQ TOUTES",
                        "CHAMP DE    1 A    3  PAS 1",
                        "POINTS DE    1 A    %d  PAS 1" % self.param["_nbPC"],
                        "DDL TOUS",
                        "FINS",
                        "*",
                        "FINP",
                    ]
                )
        lines.extend(["*", "* Fin du post-traitement", "* ----------------------"])
        return lines

    def bloc_group(self):
        """Déclaration des groupes"""
        lines = ["*", "* Definition des groupes", "* ----------------------", "GROUP"]
        group = self.domain.group
        # for interf in ('sol-struct', 'fluide-struct', 'sol-fluide',
        #'sol libre'):
        # if group.get(interf):
        # lines.extend(['%4d SURF' % group[interf], 'FIN'])
        if self.domain.def_all_domains:
            for volu in ("pc", "struct"):
                if group.get(volu):
                    lines.extend(["%4d VOLUME" % group[volu], "FIN"])
        lines.append("FING")
        return lines

    def bloc_modes(self):
        """Déclaration des modes"""
        lines = [
            "*",
            "* Definition des modes",
            "* --------------------",
            "CHAMP",
            "LIRE %s" % self.dinf["fich_chp"],
        ]
        return lines

    def bloc_integr(self):
        """Paramètres d'intégration"""
        lines = [
            "*",
            "* Parametres d integration",
            "* ------------------------",
            "INTEGRATION RECT 6 8 TRIANGLE 12 12",
        ]
        return lines

    def bloc_lfreq(self):
        """Définition des fréquences de calcul"""
        lines = [
            "*",
            "* Definition de la plage de frequences",
            "* ------------------------------------",
        ]
        freq_min = self.param["FREQ_MIN"]
        freq_max = self.param["FREQ_MAX"]
        freq_pas = self.param["FREQ_PAS"]
        freq_imag = self.param["FREQ_IMAG"]
        list_freq = self.param["LIST_FREQ"]
        freq = self.param["FREQ"]
        _nbfreq = 0
        # formats possibles pour les fréquences
        assert (freq_min, list_freq, freq).count(
            None
        ) == 2, "expect at most FREQ_MIN, LIST_FREQ or FREQ, not together"
        if freq_min is not None:
            lines.append(
                (
                    "FREQUENCE DE %%(freq_min)%(R)s A %%(freq_max)%(R)s "
                    "PAS %%(freq_pas)%(R)s\n" % dict_format
                )
                % locals()
            )
            _nbfreq = int((freq_max - freq_min) / freq_pas) + 2
        if list_freq is not None:
            lfreq = list_freq.getValues()
            nbf = len(lfreq)
            lines.extend(
                [
                    ("FREQUENCE %%%(I)s" % dict_format) % nbf,
                    (dict_format["sR"] * nbf) % tuple(lfreq),
                ]
            )
            _nbfreq = nbf + 1
        elif freq is not None:
            lfreq = freq
            nbf = len(lfreq)
            lines.extend(
                [
                    ("FREQUENCE %%%(I)s" % dict_format) % nbf,
                    (dict_format["sR"] * nbf) % tuple(lfreq),
                ]
            )
            _nbfreq = nbf + 1
        if freq_imag is not None:
            lines.append(("IMGO %%%(R)s\n" % dict_format) % freq_imag)
        # _nbfreq will be used in miss_post
        self.param.set("_nbfreq", _nbfreq)
        return lines

    def bloc_domain(self):
        """Définition des sous-domaines"""
        lines = ["*", "* Definition des sous-domaines", "* ----------------------------"]
        if self.domain.def_all_domains:
            lines.extend(
                [
                    "*",
                    "* Definition du sous-domaine structure",
                    "* ------------------------------------",
                    "SDOMAINE %4d GROUPE " % self.domain["struct"][0]
                    + "".join(["%4d" % i for i in self.domain["struct"][1]]),
                    "KCM",
                    "FINS",
                ]
            )
        lines.extend(
            [
                "*",
                "* Definition du sous-domaine sol",
                "* ------------------------------",
                "SDOMAINE %4d GROUPE " % self.domain["sol"][0]
                + "".join(["%4d" % i for i in self.domain["sol"][1]]),
                self._materiau_sol(),
                "FINS",
            ]
        )
        return lines

    def calcul_champ_incident(self):
        """Calcul des champs incidents"""
        lines = []
        if self.param["_hasPC"]:
            lines.extend(
                [
                    "*",
                    "* Chargement du domaine structure",
                    "* -------------------------------",
                    "DOMAINE %4d" % self.domain["struct"][0],
                    "EXTERIEUR",
                    "LIRE %s" % self.dinf["fich_ext"],
                    "FINE",
                ]
            )
        lines.extend(self._chargement_domaine("sol"))
        lines.extend(self._stratification_sol())
        lines.extend(self._source_sol())
        if self.param["_hasPC"]:
            lines.extend(
                [
                    "*",
                    "* Calcul des champs incidents aux points de controle",
                    "* --------------------------------------------------",
                    "EXEC CONTROLE UI",
                ]
            )
        return lines

    def calcul_fonction_green(self):
        """Calcul des fonctions de Green"""
        lines = []
        strat = self._stratification_sol()
        if strat:
            lines.extend(strat)
            lines.extend(
                [
                    "*",
                    "* Calcul des fonctions de Green",
                    "* -----------------------------",
                    "EXEC SPFR",
                ]
            )
        return lines

    def calcul_champs(self):
        """Calcul des champs rayonnés aux interfaces, et/ou assemblage des
        impédances et forces sismiques induites"""
        lines = []
        args = "IMPEdance FORCe"
        if self.param["_hasPC"]:
            args = "UD0 CHAMP IMPEdance FORCe"
        lines.extend(
            [
                "*",
                "* Calcul des forces et impedances",
                "* -------------------------------",
                "EXEC UGTG %s" % args + self._rfic(),
            ]
        )
        self._impe_calc = "IMPEdance" in args
        self._forc_calc = "FORCe" in args
        return lines

    def calcul_global(self):
        """Résolution globale si nécessaire"""
        lines = []
        if self.param["_hasPC"] or self.param["ISSF"] == "OUI":
            lines.extend(
                [
                    "*",
                    "* Resolution du probleme d interaction",
                    "* ------------------------------------",
                    "EXEC GLOBAL",
                ]
            )
        if self.param["_hasPC"]:
            lines.extend(self._chargement_domaine("sol"))
            lines.extend(
                [
                    "*",
                    "* Synthese des champs sur les interfaces",
                    "* --------------------------------------",
                    "EXEC DIFFracte UTOT TTOT",
                ]
            )
            lines.extend(self._stratification_sol())
            lines.extend(
                [
                    "*",
                    "* Synthese des champs sur les points de controle",
                    "* ----------------------------------------------",
                    "EXEC CONTrole UTOT TTOT NOGEO",
                ]
            )
        return lines

    def _materiau_sol(self):
        """Définition du matériau sol : stratifié ou homogène"""
        if self.param.get("MATER_SOL"):
            val = self.param["MATER_SOL"]
            young = val["E"]
            vnu = val["NU"]
            rho = val["RHO"]
            beta = val["AMOR_HYST"] or 0.0
            mat = "MATE RO %%%(R)s VP %%%(R)s VS %%%(R)s BETA %%%(R)s" % dict_format
            vp = sqrt(young * (1.0 - vnu) / (rho * (1.0 + vnu) * (1.0 - 2.0 * vnu)))
            vs = sqrt(young / (2.0 * rho * (1.0 + vnu)))
            line = mat % (rho, vp, vs, beta)
        else:
            line = "STRAtifie"
        return line

    def _stratification_sol(self):
        """Définition de la stratification du sol"""
        if self.param.get("MATER_SOL"):
            return []
        z0 = self.param["Z0"]
        lines = [
            "*",
            "* Definition de la stratification du sol",
            "* --------------------------------------",
            ("DOS2M Z0 %%%(R)s  %%s" % dict_format) % (z0, self.dinf["surf"]),
            "LIRE %s" % self.dinf["fich_sol"],
        ]
        return lines

    def _source_sol(self):
        """Définition des sources dans le sol"""
        lines = []
        src = self.param.get("SOURCE_SOL")
        if type(src) in (list, tuple):
            if len(src) > 0:
                assert len(src) == 1
                src = src[0]
        if not src:
            z0 = self.param["Z0"]
            lines.extend(
                [
                    "*",
                    "* Definition des champs incidents",
                    "* -------------------------------",
                    "INCI 3",
                    ("DPLANE SV 1. Z0 %%%(R)s" % dict_format) % z0,
                    "0. 0. 1.",
                    ("DPLANE SH 1. Z0 %%%(R)s" % dict_format) % z0,
                    "0. 0. 1.",
                    ("DPLANE P 1. Z0 %%%(R)s" % dict_format) % z0,
                    "0. 0. 1.",
                ]
            )
        else:
            lines.extend(
                [
                    "*",
                    "* Definition de source dans le sol",
                    "* --------------------------------",
                    "EXEC SPFR",
                    "INCI 1",
                    ("SOURCE %%%(R)s %%%(R)s %%%(R)s" % dict_format) % src["POINT"],
                    ("       %%%(R)s %%%(R)s %%%(R)s" % dict_format) % src["DIRECTION"],
                ]
            )
        lines.extend(
            ["*", "* Calcul des champs incidents", "* ---------------------------", "EXEC INCI"]
        )
        return lines

    def _chargement_domaine(self, dom):
        """Chargement d'un domaine"""
        lines = [
            "*",
            "* Chargement du domaine %s" % dom,
            "* -------------------------------",
            "DOMAINE %4d" % self.domain[dom][0],
        ]
        return lines

    def _rfic(self):
        """Retourne les paramètres si RFIC (résonances fictives) est utilisé"""
        line = ""
        if self.dinf["rfic"]:
            line = " RFIC %s %s" % (self.dinf["rfic"], self.dinf["rfic"])
        return line


class MissCmdeGeneratorInci(MissCmdeGenerator):
    """Construit un fichier de commandes Miss
    Calcul du champ incident pour la methode Laplace-temps"""

    def bloc_lfreq(self):
        """Définition des fréquences de calcul"""
        nbf = int(self.param["INST_FIN"] / self.param["PAS_INST"])
        frq = 1.0 / self.param["PAS_INST"]
        self.param["FREQ_MAX"] = frq
        self.param["FREQ_MIN"] = frq / nbf
        self.param["FREQ_PAS"] = frq / nbf
        # car FREQ_IMAG ne sert qu'à déclencher le traitement
        self.param.set("FREQ_IMAG", None)
        return super(MissCmdeGeneratorInci, self).bloc_lfreq()

    def calcul_champs(self):
        """Assemblage des forces sismiques induites"""
        lines = [
            "*",
            "* Calcul des forces sismiques",
            "* ---------------------------",
            "EXEC UGTG FORCe" + self._rfic(),
        ]
        self._forc_calc = True
        return lines


class MissCmdeGeneratorISSF(MissCmdeGenerator):
    """Construit un fichier de commandes Miss dans le cas ISSF"""

    def bloc_domain(self):
        """Définition des sous-domaines"""
        lines = super(MissCmdeGeneratorISSF, self).bloc_domain()
        lines.extend(
            [
                "*",
                "* Definition du sous-domaine sol",
                "* ------------------------------",
                "SDOMAINE %4d GROUPE " % self.domain["fluide"][0]
                + "".join(["%4d" % i for i in self.domain["fluide"][1]]),
                self._materiau_fluide(),
                "FINS",
            ]
        )
        return lines

    def calcul_champ_incident(self):
        """Calcul des champs incidents"""
        lines = super(MissCmdeGeneratorISSF, self).calcul_champ_incident()
        lines.extend(self._chargement_domaine("fluide"))
        lines.extend(self._source_fluide())
        return lines

    def calcul_champs(self):
        """Calcul des champs rayonnés aux interfaces, et/ou assemblage des
        impédances et forces sismiques induites"""
        lines = super(MissCmdeGeneratorISSF, self).calcul_champs()
        lines.extend(self._chargement_domaine("fluide"))
        lines.extend(
            [
                "*",
                "* Calcul des forces et impedances",
                "* -------------------------------",
                "EXEC UGTG IMPEdance FORCe" + self._rfic(),
            ]
        )
        return lines

    def _source_sol(self):
        """Définition des sources dans le sol"""
        if not self.param.get("SOURCE_FLUIDE"):
            return super(MissCmdeGeneratorISSF, self)._source_sol()
        else:
            return []

    def _materiau_fluide(self):
        """Définition des propriétés du fluide acoustique homogène"""
        assert self.param.get("MATER_FLUIDE"), "'MATER_FLUIDE' must be defined"
        # si SURF='OUI': demi-espace fluide, sinon FLUIDE
        mat = "%%s RO %%%(R)s CELER %%%(R)s BETA %%%(R)s SURF 0." % dict_format
        typ = "FLUIDE"
        val = self.param["MATER_FLUIDE"]
        if val["DEMI_ESPACE"] == "OUI":
            typ = "DFLUIDE"
        rho = val["RHO"]
        celr = val["CELE"]
        beta = val["AMOR_BETA"] or 0.0
        line = mat % (typ, rho, celr, beta)
        return line

    def _source_fluide(self):
        """Définition des sources dans le fluide"""
        lines = []
        src = self.param.get("SOURCE_FLUIDE")
        if type(src) in (list, tuple):
            if len(src) > 0:
                assert len(src) == 1
                src = src[0]
        if src:
            lines.extend(
                [
                    "*",
                    "* Definition de source dans le fluide",
                    "* -----------------------------------",
                    "INCI 1",
                    ("SOURCE %%%(R)s %%%(R)s %%%(R)s" % dict_format) % src["POINT"],
                    "       1.",
                    "*",
                    "* Calcul des champs incidents",
                    "* ---------------------------",
                    "EXEC INCI",
                ]
            )
        return lines


def MissCmdeGen(param, struct, filename_callback, lapl_temps=False):
    """Return un objet générateur de fichier de commandes Miss"""
    if lapl_temps:
        return MissCmdeGeneratorInci(param, struct, filename_callback)
    elif param["ISSF"] == "OUI":
        return MissCmdeGeneratorISSF(param, struct, filename_callback)
    else:
        return MissCmdeGenerator(param, struct, filename_callback)


def remove_empty_lines(text):
    """Remove empty lines from `text`"""
    lines = [line for line in text.splitlines() if line.strip()]
    lines.append("")
    return os.linesep.join(lines)


def remove_comments(text):
    """Remove Miss comments from `text`"""
    recmt = re.compile(r"^\*")
    lines = [line for line in text.splitlines() if not recmt.search(line)]
    return os.linesep.join(lines)
