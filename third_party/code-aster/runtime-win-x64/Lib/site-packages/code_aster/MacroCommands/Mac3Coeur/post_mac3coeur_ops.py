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
from ...CodeCommands import CREA_TABLE
from ...Objects.table_py import Table
from .mac3coeur_coeur import CoeurFactory
from .mac3coeur_commons import MAC3_ROUND, CollectionMAC3


class CollectionDiscretChoc(CollectionMAC3):
    @property
    def values(self):
        return np.array(self.filter(("RES", "CU_")))

    @property
    def values_internal(self):
        return np.array(self.filter("RES"))

    @property
    def values_external(self):
        return np.array(self.filter("CU_"))

    def analysis(self):
        quantiles = (70, 80, 90, 95, 99)

        values = {}

        for i in quantiles:
            values["Quan%s_CU_%d" % (self.label, i)] = np.percentile(self.values_external, i)
            values["Quan%s_AC_%d" % (self.label, i)] = np.percentile(self.values_internal, i)
            values["Quan%s_%d" % (self.label, i)] = np.percentile(self.values, i)

            qu_cu_grids_i = np.percentile(self.values_external, i, axis=0)
            qu_ac_grids_i = np.percentile(self.values_internal, i, axis=0)
            qu_grids_i = np.percentile(self.values, i, axis=0)

            nb_grids = qu_cu_grids_i.size
            for j in range(nb_grids):
                values["Quan%s_CU_G%d_%d" % (self.label, j + 1, i)] = qu_cu_grids_i[j]
                values["Quan%s_AC_G%d_%d" % (self.label, j + 1, i)] = qu_ac_grids_i[j]
                values["Quan%s_G%d_%d" % (self.label, j + 1, i)] = qu_grids_i[j]

        for key, item in values.items():
            values[key] = np.around(item, MAC3_ROUND)

        return values

    def extr_table(self):
        nb_grids = self.values.shape[1]

        listdic = [{key: self[key][i] for key in self.keys} for i in range(nb_grids)]
        listpara = self.keys
        f = lambda s: "K24" if s.startswith("GRILLE") else "R"
        listtype = [f(i) for i in listpara]
        return Table(listdic, listpara, listtype)

    def extr_analysis_table(self):
        values = self.analysis()

        listdic = [values]
        listpara = sorted(values.keys())
        listtype = ["R"] * len(listpara)

        print("STATS_POSTMAC3 = ", values)

        return Table(listdic, listpara, listtype)


class CollectionPostAC(CollectionMAC3):
    def __init__(self, label):
        super().__init__(label)

        self.maxRho = 0.0
        self.maxGravite = 0.0
        self.locMaxRho = ""
        self.locMaxGravite = ""
        self.maxDeplGrille = [0.0] * 10
        self.locMaxDeplGrille = [""] * 10
        self.moyenneRho = 0.0
        self.moyenneGravite = 0.0
        self.sigmaGravite = 0.0
        self.maxRhoParType = {}
        self.maxGraviteParType = {}
        self.moyenneRhoParType = {}
        self.moyenneGraviteParType = {}

    def analysis(self):
        for pos_damac in sorted(self.keys):
            AC = self[pos_damac]

            if AC["Rho"] > self.maxRho:
                self.maxRho = AC["Rho"]
                self.locMaxRho = pos_damac

            if AC["Gravite"] > self.maxGravite:
                self.maxGravite = AC["Gravite"]
                self.locMaxGravite = pos_damac

            for g in range(AC.nb_grilles):
                if AC["NormF"][g] > self.maxDeplGrille[g]:
                    self.maxDeplGrille[g] = AC["NormF"][g]
                    self.locMaxDeplGrille[g] = pos_damac

        self.moyenneRho = np.mean(tuple(AC["Rho"] for AC in self))
        self.moyenneGravite = np.mean(tuple(AC["Gravite"] for AC in self))

        self.sigmaGravite = np.sqrt(
            np.mean((np.array(tuple(AC["Gravite"] for AC in self)) - self.moyenneGravite) ** 2)
        )

        types = set((AC["TypeAC"] for AC in self))
        self.maxRhoParType = {
            i: max((AC["Rho"] for AC in self if i == AC["TypeAC"])) for i in types
        }
        self.maxGraviteParType = {
            i: max((AC["Gravite"] for AC in self if i == AC["TypeAC"])) for i in types
        }
        self.moyenneRhoParType = {
            i: np.mean(tuple(AC["Rho"] for AC in self if i == AC["TypeAC"])) for i in types
        }
        self.moyenneGraviteParType = {
            i: np.mean(tuple(AC["Gravite"] for AC in self if i == AC["TypeAC"])) for i in types
        }

    def extr_table(self):
        listdic = [AC.get_fleche_props(self.label) for pos, AC in sorted(self.items())]
        listpara, listtype = PostAC.fleche_parameters_types(self.label)
        return Table(listdic, listpara, listtype)

    def extr_analysis_table(self):
        self.analysis()

        values = {
            "moyRhoCoeur": self.moyenneRho,
            "maxRhoCoeur": self.maxRho,
            "moyGravCoeur": self.moyenneGravite,
            "maxGravCoeur": self.maxGravite,
            "sigGravCoeur": self.sigmaGravite,
            "locMaxRho": self.locMaxRho,
            "locMaxGrav": self.locMaxGravite,
        }

        values.update({"moR%s" % typ: value for typ, value in self.moyenneRhoParType.items()})
        values.update({"maR%s" % typ: value for typ, value in self.maxRhoParType.items()})
        values.update({"maG%s" % typ: value for typ, value in self.maxGraviteParType.items()})
        values.update({"moG%s" % typ: value for typ, value in self.moyenneGraviteParType.items()})
        values.update(
            {
                "locMaxDeplG%i" % (i + 1): value
                for i, value in enumerate(self.locMaxDeplGrille)
                if value != ""
            }
        )
        values.update(
            {
                "maxDeplGrille%i" % (i + 1): self.maxDeplGrille[i]
                for i, value in enumerate(self.locMaxDeplGrille)
                if value != ""
            }
        )

        listpara = sorted(values.keys())
        f = lambda s: "K24" if s.startswith("loc") else "R"
        listtype = [f(i) for i in listpara]

        print("STATS_POSTMAC3 = ", values)

        return Table([values], listpara, listtype)


class PostAC:
    def __getitem__(self, key):
        return self._props[key]

    def __setitem__(self, key, item):
        self._props[key] = item

    def __init__(self, coor_x, dy, dz, AC):
        fy = dy - dy[0] - (dy[-1] - dy[0]) / (coor_x[-1] - coor_x[0]) * (coor_x - coor_x[0])
        fz = dz - dz[0] - (dz[-1] - dz[0]) / (coor_x[-1] - coor_x[0]) * (coor_x - coor_x[0])
        FormeY, FormeZ, Forme = self._compute_forme(fy, fz)

        self.nb_grilles = len(coor_x)

        self._props = {
            "PositionDAMAC": AC.pos_damac,
            "PositionASTER": AC.pos_aster,
            "Cycle": AC.cycle,
            "Repere": AC.name,
            "Rho": np.around(self._compute_rho(fy, fz), MAC3_ROUND),
            "DepY": dy[0] - dy[-1],
            "DepZ": dz[0] - dz[-1],
            "TypeAC": AC.typeAC,
            "MinY": fy.min(),
            "MaxY": fy.max(),
            "CCY": fy.max() - fy.min(),
            "MinZ": fz.min(),
            "MaxZ": fz.max(),
            "CCZ": fz.max() - fz.min(),
            "FormeY": FormeY,
            "FormeZ": FormeZ,
            "Forme": Forme,
            "Gravite": np.around(self._compute_gravite(coor_x, fy, fz), MAC3_ROUND),
            "NormF": np.around(self._compute_norm(fy, fz), MAC3_ROUND),
            "FY": fy,
            "FZ": fz,
        }

        self._props.update({"XG%d" % (i + 1): 0.0 for i in range(10)})
        self._props.update({"YG%d" % (i + 1): 0.0 for i in range(10)})

        self._props.update({"XG%d" % (i + 1): val for i, val in enumerate(fy)})
        self._props.update({"YG%d" % (i + 1): val for i, val in enumerate(fz)})

    def _compute_rho(self, fy, fz):
        return max(
            [
                np.sqrt((fy[i] - fy[j]) ** 2 + (fz[i] - fz[j]) ** 2)
                for i in range(self.nb_grilles - 1)
                for j in range(i + 1, self.nb_grilles)
            ]
        )

    def _compute_norm(self, fy, fz):
        return np.sqrt(fy**2 + fz**2)

    def _compute_gravite(self, coor_x, fy, fz):
        K_star = 100000.0
        sum_of_squared_sin = 0

        for i in range(1, len(coor_x) - 1):
            gi_p = np.array((fy[i - 1], fz[i - 1], coor_x[i - 1]))  # previous grid
            gi_c = np.array((fy[i], fz[i], coor_x[i]))  # current grid
            gi_n = np.array((fy[i + 1], fz[i + 1], coor_x[i + 1]))  # next grid

            squared_cos = np.dot(gi_c - gi_p, gi_n - gi_c) / (
                np.linalg.norm(gi_c - gi_p) * np.linalg.norm(gi_n - gi_c)
            )
            sum_of_squared_sin += 1.0 - squared_cos

        return K_star * sum_of_squared_sin

    def _compute_forme(self, fx, fy):
        crit = 0.5

        A1x = abs(min(fx))
        A2x = abs(max(fx))
        CCx = max(fx) - min(fx)
        shape_x = "S" if (A1x > crit and A2x > crit) else "C"

        A1y = abs(min(fy))
        A2y = abs(max(fy))
        CCy = max(fy) - min(fy)
        shape_y = "S" if (A1y > crit and A2y > crit) else "C"

        letters = "".join(sorted(set((shape_x, shape_y))))
        shape_global = "2%s" % letters if len(letters) == 1 else letters

        return shape_x, shape_y, shape_global

    def get_fleche_props(self, label):
        fleche_props = {
            label: self["PositionDAMAC"],
            "Cycle": self["Cycle"],
            "T5": 0.0,
            "T6": 0.0,
            "Repere": self["Repere"],
            "Ro": self["Rho"],
            "EinfXgg": self["DepY"],
            "EinfYgg": self["DepZ"],
            "Milieu": self["TypeAC"],
            "Min X": self["MinY"],
            "Max X": self["MaxY"],
            "CC X": self["CCY"],
            "Min Y": self["MinZ"],
            "Max Y": self["MaxZ"],
            "CC Y": self["CCZ"],
            "Forme X": self["FormeY"],
            "Forme Y": self["FormeZ"],
            "Forme": self["Forme"],
        }
        fleche_props.update({"XG%d" % (i + 1): self["XG%d" % (i + 1)] for i in range(10)})
        fleche_props.update({"YG%d" % (i + 1): self["YG%d" % (i + 1)] for i in range(10)})

        return fleche_props

    @staticmethod
    def fleche_parameters_types(label):
        para = [label, "Cycle", "T5", "T6", "Repere", "Ro", "EinfXgg", "EinfYgg"]
        para += ["XG%d" % (d + 1) for d in range(10)] + ["YG%d" % (d + 1) for d in range(10)]
        para += [
            "Milieu",
            "Min X",
            "Max X",
            "CC X",
            "Min Y",
            "Max Y",
            "CC Y",
            "Forme X",
            "Forme Y",
            "Forme",
        ]

        types = ["K24", "I", "R", "R", "K24", "R", "R", "R"]
        types += ["R"] * 20
        types += ["K24", "R", "R", "R", "R", "R", "R", "K8", "K8", "K8"]

        return para, types


def post_mac3coeur_ops(self, **args):
    """Corps principal de la macro de post-traitement de MAC3COEUR"""

    RESU = args["RESULTAT"]
    inst = args["INST"]

    core_type = args["TYPE_COEUR"]
    row_size = args["NB_ASSEMBLAGE"] if "LIGNE" in core_type else None

    TYPE_CALCUL = args.get("TYPE_CALCUL")
    OPERATION = args.get("OPERATION")

    datamac = args["TABLE"]
    output_as_aster = args.get("FORMAT", "DAMAC") in ("ASTER",)

    label_type, label_calcul = datamac.EXTR_TABLE().titr.split()
    nb_grids = 8 if "900" in label_type else 10

    core_mac3 = CoeurFactory.build(core_type, datamac, row_size)

    #
    # LAME
    #

    if TYPE_CALCUL in ("LAME",):
        collection = CollectionDiscretChoc("LE")
        collection["GRILLE"] = ["G%s" % (i + 1) for i in range(nb_grids)]

        for name in core_mac3.get_contactAssLame() + core_mac3.get_contactCuve():
            # Le déplacement suivant l'axe local x : V1
            TMP = CREA_TABLE(
                RESU=_F(
                    RESULTAT=RESU,
                    NOM_CMP="V1",
                    GROUP_MA=name,
                    NOM_CHAM="VARI_ELGA",
                    INST=inst,
                    PRECISION=1.0e-08,
                )
            )

            vals = np.stack(tuple(TMP.EXTR_TABLE().values()[i] for i in ("COOR_X", "V1")))
            vals = np.mean(
                vals.reshape(2, vals.shape[1] // 2, 2), axis=2
            )  # Moyenne sur les 2 noeuds du discret (qui portent tous la meme valeur)

            coor_x, v1 = np.around(1000.0 * vals[:, vals[0].argsort()], MAC3_ROUND)
            position = name if output_as_aster else core_mac3.watergap_todamac(name)
            collection[position] = v1

    #
    # FORCE_CONTACT
    #

    elif TYPE_CALCUL in ("FORCE_CONTACT",):
        collection = CollectionDiscretChoc("N")
        collection["GRILLE"] = ["G%s" % (i + 1) for i in range(nb_grids)]

        for name in core_mac3.get_contactAssLame() + core_mac3.get_contactCuve():
            TMP = CREA_TABLE(
                RESU=_F(
                    RESULTAT=RESU,
                    NOM_CMP="N",
                    GROUP_MA=name,
                    NOM_CHAM="SIEF_ELGA",
                    INST=inst,
                    PRECISION=1.0e-08,
                )
            )

            vals = np.abs(np.stack(tuple(TMP.EXTR_TABLE().values()[i] for i in ("COOR_X", "N"))))
            vals = np.mean(
                vals.reshape(2, vals.shape[1] // 2, 2), axis=2
            )  # Moyenne sur les 2 noeuds du discret (qui portent tous la meme valeur)

            coor_x, force = np.around(vals[:, vals[0].argsort()], MAC3_ROUND)
            position = name if output_as_aster else core_mac3.watergap_todamac(name)
            collection[position] = force

    #
    # DEFORMATION
    #

    elif TYPE_CALCUL in ("DEFORMATION",):
        collection = CollectionPostAC(label_calcul)
        for AC in core_mac3.collAC:
            TMP = CREA_TABLE(
                RESU=_F(
                    RESULTAT=RESU,
                    NOM_CMP=("DY", "DZ"),
                    GROUP_NO=["G_%s_%d" % (AC.pos_aster, g + 1) for g in range(AC.NBGR)],
                    NOM_CHAM="DEPL",
                    INST=inst,
                    PRECISION=1.0e-08,
                )
            )
            # Extraction des valeurs
            vals = np.stack(tuple(TMP.EXTR_TABLE().values()[i] for i in ("COOR_X", "DY", "DZ")))
            # Sort
            vals = vals[:, vals[0].argsort()]
            # Moyenne sur les discrets de la grille (qui portent tous la meme valeur)
            nb_disc = vals.shape[1] // AC.NBGR
            vals = np.mean(vals.reshape(vals.shape[0], AC.NBGR, nb_disc), axis=2)
            # Passage en mm et arrondi
            coor_x, dy, dz = np.around(1000.0 * vals[:, vals[0].argsort()], MAC3_ROUND)

            post_ac = PostAC(coor_x, dy, dz, AC)
            collection[post_ac["PositionDAMAC"]] = post_ac

    #
    # POST PROCESSING
    #

    if OPERATION in ("EXTRACTION",):
        table = collection.extr_table()
    else:
        table = collection.extr_analysis_table()

    return CREA_TABLE(**table.dict_CREA_TABLE())
