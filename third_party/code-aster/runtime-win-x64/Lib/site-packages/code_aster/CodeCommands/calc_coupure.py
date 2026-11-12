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

from ..Cata.Syntax import _F
from ..CodeCommands import CALC_CHAMP, CREA_TABLE, POST_RELEVE_T
from ..Messages import UTMESS
from ..Objects.table_py import Table

L_CMP = ["RESULT_X", "RESULT_Y", "RESULT_Z", "MOMENT_X", "MOMENT_Y", "MOMENT_Z"]
L_CMP_RESU = ["R1", "R2", "R3", "M1", "M2", "M3"]
L_DIRECTION = ["X", "Y", "Z"]
D_DIRECTION = {"X": 0, "Y": 1, "Z": 2}
COMB_NEWMARK = [
    [1, 0.4, 0.4],
    [1, -0.4, 0.4],
    [1, -0.4, -0.4],
    [1, 0.4, -0.4],
    [-1, 0.4, 0.4],
    [-1, -0.4, 0.4],
    [-1, -0.4, -0.4],
    [-1, 0.4, -0.4],
    [0.4, 1, 0.4],
    [-0.4, 1, 0.4],
    [-0.4, 1, -0.4],
    [0.4, 1, -0.4],
    [0.4, -1, 0.4],
    [-0.4, -1, 0.4],
    [-0.4, -1, -0.4],
    [0.4, -1, -0.4],
    [0.4, 0.4, 1],
    [-0.4, 0.4, 1],
    [-0.4, -0.4, 1],
    [0.4, -0.4, 1],
    [0.4, 0.4, -1],
    [-0.4, 0.4, -1],
    [-0.4, -0.4, -1],
    [0.4, -0.4, -1],
]
NOM_NEWMARK = [";".join([str(v) for v in comb]) for comb in COMB_NEWMARK]


def calc_coupure_ops(self, **args):
    """
    Corps de la commande MACR_COUP
    Commande pour calculer la reaction d'un group de maille sur
    un groupe de noeud en reduisant le torseur en un point donne
    et dans un repere utilisateur donne.
    La commande gere en deuxieme partie le cas modal spectral (CQC signee)
    avec prise en compte du pseudo-mode.
    """

    args = _F(args)

    if args.get("MODAL_SPECTRAL") == "NON":
        worker = CalcCoupure(args)
        worker.checkData()
        table_resu = worker.calcTout()
    else:
        worker = CalcCoupureModSpec(args)
        worker.checkData()
        table_resu = worker.calcModSpec()
    return table_resu


class Coupure(object):
    """
    Class of a given 'coupure' used to the reaction on given nodes coming from
    given mesh elements at a certain point
    """

    def __init__(self, resultat, force, kwargs):
        """Initialization

        Arguments:
            resultat (sd_resultat) : result to be exploited
            force (string) : name of the field to be exploited (REAC_NODA or FORCE_NOAD) (default FORCE_NODA)
            nom (string) : name of the 'coupure'
            gpma (string) : name of the group of elements to be exploited
            gpno (string) : name of the group of node on which the torsor is computed
            x (list[float]) : coordinates of the X local axis (default [1, 0, 0])
            Y (list[float])  : coordinates of the Y local axis (default [0, 1, 0])
            Z (list[float])  : coordinates of the Z local axis (default [0, 0, 1])
            veri_ortho [string] : define is the orthogonality of local axis has to be checked
        """
        self.resultat = resultat
        self.force = force
        self.nom = kwargs.get("NOM")
        self.gpma = kwargs.get("GROUP_MA")
        self.gpno = kwargs.get("GROUP_NO")
        self.point = kwargs.get("POINT")
        self.x = kwargs.get("AXE_X")
        self.y = kwargs.get("AXE_Y")
        self.z = kwargs.get("AXE_Z")
        self.veri_ortho = kwargs.get("VERI_ORTHO")

        self._matpass = None
        self.axe_x = np.array(self.x) / np.linalg.norm(np.array(self.x))
        self.axe_y = np.array(self.y) / np.linalg.norm(np.array(self.y))
        self.axe_z = np.array(self.z) / np.linalg.norm(np.array(self.z))

    def checkOrtho(self):
        """Check if the given axis are orthogonal"""
        if self.veri_ortho == "OUI":
            if abs(np.vdot(self.axe_x, self.axe_y)) > 1e-5:
                UTMESS("F", "COUPURE_1", valr=np.vdot(self.axe_x, self.axe_y))
            if abs(np.vdot(self.axe_x, self.axe_z)) > 1e-5:
                UTMESS("F", "COUPURE_2", valr=np.vdot(self.axe_x, self.axe_z))
            if abs(np.vdot(self.axe_y, self.axe_z)) > 1e-5:
                UTMESS("F", "COUPURE_3", valr=np.vdot(self.axe_y, self.axe_y))
            return True
        return False

    def setMatPass(self):
        """Compute the transition matrix from 'global' to 'local' axis

        Returns:
            np.array : 6 * 6 diagonal bloc matrix with on the diagoanl the 3*3 transition matrix
        """
        if self._matpass is None:
            mat_pass = np.linalg.inv(np.concatenate([[self.axe_x], [self.axe_y], [self.axe_z]]).T)
            # on cree une matrice diagonale par bloc en mettant 2 fois la matrice de passage sur la diag
            # on peut ensuite faire le produit directement avec FX, FY, FZ, MX, MY, MZ
            self._matpass = np.kron(np.eye(2, dtype=int), mat_pass)
        return self._matpass

    def calcTorseurGlobal(self):
        """Compute the torsor in the global frame

        Returns:
            np.array : 6 * 1 torsor
        """
        if self.gpma:
            RES = CALC_CHAMP(RESULTAT=self.resultat, FORCE=self.force, GROUP_MA=self.gpma)

        else:
            RES = CALC_CHAMP(RESULTAT=self.resultat, FORCE=self.force, TOUT="OUI")

        T = POST_RELEVE_T(
            ACTION=_F(
                OPERATION="EXTRACTION",
                INTITULE="Resultante",
                RESULTAT=RES,
                GROUP_NO=self.gpno,
                NOM_CHAM=self.force,
                RESULTANTE=("DX", "DY", "DZ"),
                MOMENT=("DRX", "DRY", "DRZ"),
                POINT=self.point,
            )
        )

        d_t = T.EXTR_TABLE().values()
        del RES, T
        return np.array([d_t[i] for i in L_CMP])

    def calcTorseurLocal(self):
        """Put the torsor in the local frame

        Returns:
            np.array : 6 * 1 torsor
        """
        return self.setMatPass().dot(self.calcTorseurGlobal())


class CalcCoupure(object):
    """Base class to work on a set of 'coupures'"""

    def __init__(self, kwargs):
        """Initialization

        Arguments:
            resultat (sd_resultat): result to be exploited
            force (string): name of the field to be exploited (REAC_NODA or FORCE_NOAD) (default FORCE_NODA)
            l_coupure (dict): parameters of the set of 'coupures' to be used
        """
        self.resultat = kwargs.get("RESULTAT")
        self.force = kwargs.get("FORCE")
        self.modspec = kwargs.get("MODAL_SPECTRAL")
        self.l_coupure = kwargs.get("COUPURE")

        self.nrank = self.resultat.getNumberOfIndexes()
        self.tab_resu = Table()
        self.d_res = {c: [] for c in L_CMP_RESU}
        self.d_res["NOM"] = []
        self.l_para_rank = self.resultat.getAccessParameters().keys()
        self._get_coupure = None
        self._calc_tout = None
        self._extr_table = None

    def getCoupure(self):
        """Creates the objetcs 'Coupure' from the argument under l_coupure and get them into a list

        Returns:
            List of 'Coupure'
        """
        if self._get_coupure is None:
            self._get_coupure = [
                Coupure(self.resultat, self.force, coupure) for coupure in self.l_coupure
            ]
        return self._get_coupure

    def checkData(self):
        """Check if the arguments are coherents to compute and work on the set of 'coupure'"""
        # On verifie que toutes les coupures ont des noms differents
        l_name = [coupure.nom for coupure in self.getCoupure()]
        if len(l_name) != len(set(l_name)):
            UTMESS("F", "COUPURE_6")

        # Verification que les reperes sont orthorgonaux
        for coupure in self.getCoupure():
            coupure.checkOrtho()

        # On verifie que le concept est bien un mode_meca si on fait un calcul modal-spectral
        if self.modspec == "OUI":
            if self.resultat.getType() != "MODE_MECA":
                UTMESS("F", "COUPURE_7")

    # TODO: cette methode peut etre simpliee ?
    def calcTout(self):
        """Compute all the set of 'coupures'

        Returns:
            dict: to be used to create an Aster table
        """
        if self._calc_tout is None:
            for coupure in self.getCoupure():
                ar = coupure.calcTorseurLocal()
                d_res = {}
                for k, i in enumerate(L_CMP_RESU):
                    d_res[i] = ar[k].tolist()
                d_res["NOM"] = [coupure.nom for i in range(self.nrank)]
                for para_rank in self.l_para_rank:
                    d_res[para_rank] = self.resultat.getAccessParameters().get(para_rank)
                # on transforme le dictionnaire de list en liste de dictionnaires
                # chaque dictionnaire correspond a une ligne du tableau
                l_line = [dict(zip(d_res, t)) for t in zip(*d_res.values())]
                for line in l_line:
                    self.tab_resu.append(line)
            self._calc_tout = self.tab_resu.dict_CREA_TABLE()
            self._calc_tout = CREA_TABLE(TYPE_TABLE="TABLE", **self.calcTout())
        return self._calc_tout

    def extrPyTable(self):
        """Extract the py_table from a table_sdaster

        Returns:
            table_py.Table
        """
        if self._extr_table is None:
            self._extr_table = self.calcTout().EXTR_TABLE()
        return self._extr_table


class ModSpec(object):
    """
    Class to store the parameters of the modal-spectral analysis
    """

    def __init__(self, args):
        """Initialization

        Arguments:
            mode_meca (ModeResult): modal analysis
            amor_reduit (list[float]): modal damping
            comb_mode (string): type of directionnal combination
            spec_osci (list[Function2D]): list of the spectrum (1 per direction)
            echelle (list[float]): list of coefficient to be applied to each spectrum to get into a coherent set of metrics
        """
        self.mode_meca = args.get("RESULTAT")
        self.amor_reduit = args.get("AMOR_REDUIT")
        self.comb_mode = args.get("COMB_MODE")
        self.spec_osci = args.get("SPEC_OSCI")
        self.echelle = args.get("ECHELLE")
        self._para = None
        self._amor = None
        self._mat_corr_cqc = None

    def getPara(self):
        """Extract the parameters of the modal analysis

        Returns:
            dict: dict of the modal analysis parameters
        """
        if self._para is None:
            self._para = self.mode_meca.getParameters()
        return self._para

    def getFreq(self):
        """Extract the list of frequencies of each modes of the modal analys

        Returns:
            list[float]: list of frequencies of each modes of the modal analys
        """
        return self.getPara()["FREQ"]

    def _fact_part(self, direction):
        """Extract the list of participation factor of the modal analysis for a given direction (global)

        Arguments:
            direction (string): direction to be extracted ('X', 'Y', 'Z')

        Returns:
            list[float]: list of participation factor of each modes of the modal analysis into a given direction (global)
        """
        return self.getPara()["FACT_PARTICI_D" + direction]

    def getFactPartX(self):
        """Extract the list of participation factor of the modal analysis in the X direction (global)

        Returns:
            list[float]: list of participation factor of each modes of the modal analysis in the X direction (global)
        """
        return self._fact_part("X")

    def getFactPartY(self):
        """Extract the list of participation factor of the modal analysis in the Y direction (global)

        Returns:
            list[float]: list of participation factor of each modes of the modal analysis in the Y direction (global)
        """
        return self._fact_part("Y")

    def getFactPartZ(self):
        """Extract the list of participation factor of the modal analysis in the Z direction (global)

        Returns:
            list[float]: list of participation factor of each modes of the modal analysis in the Z direction (global)
        """
        return self._fact_part("Z")

    def getNbMode(self):
        """Extract the number of modes in the modal analysis

        Returns:
            int: number of modes in the modal analysis
        """
        return len(self.getFreq())

    def getPulsation(self):
        """Compute the pulsation of each modes of the modal analysis

        Returns:
            list[float]: list of pulsation of each modes of the modal analysis
        """
        return [f * 2 * np.pi for f in self.getFreq()]

    def getAmor(self):
        """Create the list of modal damping to be used
        If 1 damping have been given, all the modes will use this value
        If a tuple or list of dampings have been given, it checks that the number of damping is equal to the number of modes

        Returns:
            list[float]: list of modal damping
        """
        if self._amor is None:
            if len(self.amor_reduit) == 1:
                self._amor = [self.amor_reduit[0] for f in self.getFreq()]
            elif len(self.amor_reduit) != self.getNbMode():
                UTMESS("F", "COUPURE_4", vali=(len(self.amor_reduit), self.getNbMode()))
            else:
                return self.amor_reduit
        return self._amor

    def getMatCorrCqc(self):
        """Compute the CQC correlation matrix

        Returns:
            np.array: CQC correlation matrix. Its shape is (nxn) with n the number of modes
        """
        if self._mat_corr_cqc is None:
            self._mat_corr_cqc = np.zeros(shape=[self.getNbMode(), self.getNbMode()])
            for i, (ai, wi) in enumerate(zip(self.getAmor(), self.getPulsation())):
                for j, (aj, wj) in enumerate(zip(self.getAmor(), self.getPulsation())):
                    e = wi / wj
                    self._mat_corr_cqc[i, j] = (
                        8
                        * e
                        * np.sqrt(ai * aj * e)
                        * (ai + aj * e)
                        / (
                            (1 - e**2) ** 2
                            + 4 * e * ai * aj * (1 + e**2)
                            + 4 * e**2 * (ai**2 + aj**2)
                        )
                    )
        return self._mat_corr_cqc

    def _acce(self, direction):
        """Extract the pseudo-acceleration of each modes for a given direction (global)

        Arguments:
            direction (string): direction to be extracted ('X', 'Y', 'Z')

        Returns:
            list[float]: list of pseudo-accelerations of each modes for a given direction (global)
        """
        i_direction = D_DIRECTION[direction]
        return [
            self.echelle[i_direction] * self.spec_osci[i_direction](a, f)
            for (a, f) in zip(self.getAmor(), self.getFreq())
        ]

    def getAcceX(self):
        """Extract the pseudo-acceleration of each modes in the 'X' direction (global)

        Returns:
            list[float]: list of pseudo-accelerations of each modes in the 'X' direction (global)
        """
        return self._acce("X")

    def getAcceY(self):
        """Extract the pseudo-acceleration of each modes in the 'Y' direction (global)

        Returns:
            list[float]: list of pseudo-accelerations of each modes in the 'Y' direction (global)
        """
        return self._acce("Y")

    def getAcceZ(self):
        """Extract the pseudo-acceleration of each modes in the 'Z' direction (global)

        Returns:
            list[float]: list of pseudo-accelerations of each modes in the 'Z' direction (global)
        """
        return self._acce("Z")

    def _zpa(self, direction):
        """Extract the pseudo-acceleration to be applied to the pseudo-mode used to complete the modal analysis (if MODE_CORR='OUI') in a given direction
        The value extracted corresponds to the acceleration computed at the frequency of the last modes for the smallest damping.

        Arguments:
            direction (string): direction to be extracted ('X', 'Y', 'Z')

        Returns:
            list[float]: pseudo-acceleration of the pseudo-modes in a given direction
        """
        i_direction = D_DIRECTION[direction]
        return self.echelle[i_direction] * self.spec_osci[i_direction](
            min(self.getAmor()), self.getFreq()[-1]
        )

    def getZpaX(self):
        """Extract the pseudo-acceleration to be applied to the pseudo-mode used to complete the modal analysis (if MODE_CORR='OUI') in the 'X' direction
        The value extracted corresponds to the acceleration computed at the frequency of the last modes for the smallest damping.

        Returns:
            list[float]: pseudo-acceleration of the pseudo-modes in the 'X' direction
        """
        return self._zpa("X")

    def getZpaY(self):
        """Extract the pseudo-acceleration to be applied to the pseudo-mode used to complete the modal analysis (if MODE_CORR='OUI') in the 'Y' direction
        The value extracted corresponds to the acceleration computed at the frequency of the last modes for the smallest damping.

        Returns:
            list[float]: pseudo-acceleration of the pseudo-modes in the 'Y' direction
        """
        return self._zpa("Y")

    def getZpaZ(self):
        """Extract the pseudo-acceleration to be applied to the pseudo-mode used to complete the modal analysis (if MODE_CORR='OUI') in the 'Z' direction
        The value extracted corresponds to the acceleration computed at the frequency of the last modes for the smallest damping.

        Returns:
            list[float]: pseudo-acceleration of the pseudo-modes in the 'Z' direction
        """
        return self._zpa("Z")


class CalcModaleUnitaire(object):
    """Class to compute the modal-spectral analysis on a given item"""

    def __init__(self, mod_spect, val_mod, val_stat=None):
        """Initialization

        Arguments:
            mode_spect (ModSpec): ModSpec object that contains the parameters of the modal analysis
            val_mod (list[float]): list of modal values of the item (1 value per mode)
            val_stat (list[float]): list of unite accelerations (3 values, 1 per direction)
        """
        self.mod_spect = mod_spect
        self.val_mod = val_mod
        self.val_stat = val_stat

    def _val_phys(self, direction):
        """Compute the physical contribution of each mode

        Returns:
            list(float): List of physical contribution of each mode
        """
        val_phys = [
            f * s * r / p**2
            for (f, s, r, p) in zip(
                self.mod_spect._fact_part(direction),
                self.mod_spect._acce(direction),
                self.val_mod,
                self.mod_spect.getPulsation(),
            )
        ]
        return val_phys

    def _cqc_non_corr(self, direction):
        """Compute the CQC of the contributions of each mode without static correction

        Arguments:
            direction (string): direction to be extracted ('X', 'Y', 'Z')

        Returns:
            list(float): CQC of the contributions of each each mode without static correction in a given direction ('X', 'Y', 'Z')
        """
        ar = np.array(self._val_phys(direction))
        cqc = np.sqrt(ar.T.dot(self.mod_spect.getMatCorrCqc().dot(ar)))
        return cqc

    def _correction_statique(self, direction):
        """Compute the static correction to be applied

        Arguments:
            direction (string): direction to be extracted ('X', 'Y', 'Z')

        Returns:
            list(float): value of the static correction to be applied in the given direction
        """
        if self.val_stat is None:
            return 0

        i_direction = D_DIRECTION[direction]
        v_stat = self.val_stat[i_direction]
        l_m = [
            f * r / p**2
            for (f, r, p) in zip(
                self.mod_spect._fact_part(direction), self.val_mod, self.mod_spect.getPulsation()
            )
        ]
        return v_stat - sum(l_m)

    def _cqc(self, direction):
        """Compute the CQC of the contributions of each mode with static correction

        Arguments:
            direction (string): direction to be extracted ('X', 'Y', 'Z')

        Returns:
            list(float): CQC of the contributions of each each mode with static correction in a given direction ('X', 'Y', 'Z')
        """
        return np.sqrt(
            self._cqc_non_corr(direction) ** 2 + self._correction_statique(direction) ** 2
        )

    def calcCqcX(self):
        """Compute the CQC of the contributions of each mode with static correction in the 'X' direction

        Returns:
            list(float): CQC of the contributions of each each mode with static correction in the 'X' direction
        """
        return self._cqc("X")

    def calcCqcY(self):
        """Compute the CQC of the contributions of each mode with static correction in the 'Y' direction

        Returns:
            list(float): CQC of the contributions of each each mode with static correction in the 'Y' direction
        """
        return self._cqc("Y")

    def calcCqcZ(self):
        """Compute the CQC of the contributions of each mode with static correction in the 'Z' direction

        Returns:
            list(float): CQC of the contributions of each each mode with static correction in the 'Z' direction
        """
        return self._cqc("Z")

    def _signe(self, direction=None):
        """Compute the sign to be applied
        It uses the sign of the item for the static response in the given direction ('X', 'Y', 'Z')

        Returns:
            int: 1 or -1
        """
        i_drection = D_DIRECTION[direction]
        v = self.val_stat[i_drection]
        if v == 0:
            return 1
        return np.sign(v)

    def _cqc_signe(self, direction):
        """Compute the CQC of the contributions of each mode with static correction and sign it

        Arguments:
            direction (string): direction to be extracted ('X', 'Y', 'Z')

        Returns:
            list(float): CQC of the contributions of each each mode with static correction in a given direction ('X', 'Y', 'Z') and sign it
        """
        return self._cqc(direction) * self._signe(direction)

    def calcCqcSigneX(self):
        """Compute the CQC of the contributions of each mode with static correction in the 'X' direction and sign it

        Returns:
            list(float): CQC of the contributions of each each mode with static correction in the 'X' direction and sign it
        """
        return self._cqc_signe("X")

    def calcCqcSigneY(self):
        """Compute the CQC of the contributions of each mode with static correction in the 'Y' direction and sign it

        Returns:
            list(float): CQC of the contributions of each each mode with static correction in the 'Y' direction and sign it
        """
        return self._cqc_signe("Y")

    def calcCqcSigneZ(self):
        """Compute the CQC of the contributions of each mode with static correction in the 'Z' direction and sign it

        Returns:
            list(float): CQC of the contributions of each each mode with static correction in the 'Z' direction and sign it
        """
        return self._cqc_signe("Z")

    def calcCombQuad(self):
        """Compute the quadratic combination of the CQC in the 3 directions

        Returns:
            float: Quadratic combination of the CQC in the 3 directions
        """
        return np.sqrt(self.calcCqcX() ** 2 + self.calcCqcY() ** 2 + self.calcCqcZ() ** 2)

    def calcCombNewmark(self):
        """Compute the Newmark combinations of CQC values of the 3 directions using the following list of combinations:

        COMB_NEWMARK = [
            [1, 0.4, 0.4], [1, -0.4, 0.4], [1, -0.4, -0.4], [1, 0.4, -0.4],
            [-1, 0.4, 0.4], [-1, -0.4, 0.4], [-1, -0.4, -0.4], [-1, 0.4, -0.4],
            [0.4, 1, 0.4], [-0.4, 1, 0.4], [-0.4, 1, -0.4], [0.4, 1, -0.4],
            [0.4, -1, 0.4], [-0.4, -1, 0.4], [-0.4, -1, -0.4], [0.4, -1, -0.4],
            [0.4, 0.4, 1], [-0.4, 0.4, 1], [-0.4, -0.4, 1], [0.4, -0.4, 1],
            [0.4, 0.4, -1], [-0.4, 0.4, -1], [-0.4, -0.4, -1], [0.4, -0.4, -1]
        ]

        Returns:
            list(float): List of the 24 values of the Newmark combination of the CQC in the 3 directions
        """
        m_comb = np.array([COMB_NEWMARK])
        m = np.array([self.calcCqcSigneX(), self.calcCqcSigneY(), self.calcCqcSigneZ()])
        return m_comb.dot(m).tolist()[0]


class CalcCoupureModSpec(CalcCoupure, ModSpec):
    """
    Base class to work on a set of 'coupures' to be post-treated using modal-spectral combination
    The class inherits of the CalcCoupure class and of the ModSpec class
    """

    def __init__(self, kwargs):
        """Initialization

        Arguments:
            force (string): name of the field to be exploited (REAC_NODA or FORCE_NOAD) (default FORCE_NODA)
            l_coupure (dict): parameters of the set of 'coupures' to be used
            mode_meca (ModeResult): modal analysis
            amor_reduit (list[float]): modal damping
            comb_mode (string): type of directionnal combination
            spec_osci (list[Function2D]): list of the spectrum (1 per direction)
            echelle (list[float]): list of coefficient to be applied to each spectrum to get into a coherent set of metrics
            mode_corr (ModeResult): pseudo-mode / mode_statiques (3 NUME_ORDRE, 1 per direction)
            signe (string): 'OUI' to signed the CQC values
            comb_direction (string): type of directionnal combination ('QUAD' or 'NEWMARK')
        """
        CalcCoupure.__init__(self, kwargs)
        ModSpec.__init__(self, kwargs)
        self.mode_corr = kwargs.get("MODE_CORR")
        self.signe = kwargs.get("MODE_SIGNE")
        self.comb_direction = kwargs.get("COMB_DIRECTION")
        self._coupure_modecorr = None

    def setCoupureModeCorr(self):
        """Create the set of coupure object on the pseudo-mode

        Results:
            Coupure object: 'coupure' on the pseudo-mode
        """
        if self._coupure_modecorr is None:
            if self.mode_corr is None:
                return None
            self._coupure_modecorr = CalcCoupure(
                {
                    "RESULTAT": self.mode_corr,
                    "FORCE": self.force,
                    "MODAL_SPECTRAL": "NON",
                    "COUPURE": self.l_coupure,
                }
            )
        return self._coupure_modecorr

    def _calc_uni(self, nom_coupure, cmp):
        """Compute the modal-spectral the modal and static values of 1 given component of a given 'coupure'

        Arguments:
            nom_coupure (string): name of the 'coupure' to be extrated from the set of 'coupures'
            cmp (string): name of the component to be extracted (R1/R2/R3/M1/M2/M3)

        Results:
            CalcModaleUnitaire object: modal-spectral analysis of a given component of the given 'coupure'
        """
        val_mod = np.array((self.extrPyTable().NOM == nom_coupure)[cmp].values()[cmp])
        if self.mode_corr is None:
            val_stat = [0, 0, 0]
        else:
            val_stat = np.array(
                [
                    (
                        (self.setCoupureModeCorr().extrPyTable().NOM == nom_coupure)
                        & (self.setCoupureModeCorr().extrPyTable().NUME_MODE == i)
                    )[cmp].values()[cmp][0]
                    for i in [1, 2, 3]
                ]
            )
        return CalcModaleUnitaire(self, val_mod, val_stat)

    def _calc_cqc(self, direction):
        """Compute the CQC values with static correction of the whole set of 'coupures' and for each components in a given direction ('X', 'Y', 'Z')

        Arguments:
            direction (string): direction to be extracted ('X', 'Y', 'Z')

        Resultat:
            list: list of dict, each item corresponding to a line in the future table

        The keys of the dicts correspond to the parameters of the table (NOM, NUME_MODE, R1, R2...)
        """
        lines = []
        for coupure in self.getCoupure():
            d = {cmp: self._calc_uni(coupure.nom, cmp)._cqc(direction) for cmp in L_CMP_RESU}
            d["NOM"] = coupure.nom
            d["DIRECTION"] = direction
            d["NUME_ORDRE"] = D_DIRECTION[direction] + 1
            d["TYPE"] = "CQC_NON_SIGNE"
            lines.append(d)
        return lines

    def calcCqcX(self):
        """Compute the CQC values with static correction of the whole set of 'coupures' and for each components in the 'X' direction

        Resultat:
            list: list of dict, each item corresponding to a line in the future table

        The keys of the dicts correspond to the parameters of the table (NOM, NUME_MODE, R1, R2...)
        """
        return self._calc_cqc("X")

    def calcCqcY(self):
        """Compute the CQC values with static correction the the whole set of 'coupures' and for each components in the 'Y' direction

        Resultat:
            list: list of dict, each item corresponding to a line in the future table

        The keys of the dicts correspond to the parameters of the table (NOM, NUME_MODE, R1, R2...)
        """
        return self._calc_cqc("Y")

    def calcCqcZ(self):
        """Compute the CQC values with static correction of the whole set of 'coupures' and for each components in the 'Z' direction

        Resultat:
            list: list of dict, each item corresponding to a line in the future table

        The keys of the dicts correspond to the parameters of the table (NOM, NUME_MODE, R1, R2...)
        """
        return self._calc_cqc("Z")

    def _calc_cqc_signe(self, direction):
        """Compute the CQC values with static correction and signed of the whole set of 'coupures' and for each components in a given direction ('X', 'Y', 'Z')

        Arguments:
            direction (string): direction to be extracted ('X', 'Y', 'Z')

        Resultat:
            list: list of dict, each item corresponding to a line in the future table

        The keys of the dicts correspond to the parameters of the table (NOM, NUME_MODE, R1, R2...)
        """
        lines = []
        for coupure in self.getCoupure():
            d = {cmp: self._calc_uni(coupure.nom, cmp)._cqc_signe(direction) for cmp in L_CMP_RESU}
            d["NOM"] = coupure.nom
            d["DIRECTION"] = direction
            d["NUME_ORDRE"] = D_DIRECTION[direction] + 1
            d["TYPE"] = "CQC_SIGNE"
            lines.append(d)
        return lines

    def calcCqcSigneX(self):
        """Compute the CQC values with static correction and signed of the whole set of 'coupures' and for each components in the 'X' direction

        Resultat:
            list: list of dict, each item corresponding to a line in the future table

        The keys of the dicts correspond to the parameters of the table (NOM, NUME_MODE, R1, R2...)
        """
        return self._calc_cqc_signe("X")

    def calcCqcSigneY(self):
        """Compute the CQC values with static correction and signed of the whole set of 'coupures' and for each components in the 'Y' direction

        Resultat:
            list: list of dict, each item corresponding to a line in the future table

        The keys of the dicts correspond to the parameters of the table (NOM, NUME_MODE, R1, R2...)
        """
        return self._calc_cqc_signe("Y")

    def calcCqcSigneZ(self):
        """Compute the CQC values with static correction and signed of the whole set of 'coupures' and for each components in the 'Z' direction

        Resultat:
            list: list of dict, each item corresponding to a line in the future table

        The keys of the dicts correspond to the parameters of the table (NOM, NUME_MODE, R1, R2...)
        """
        return self._calc_cqc_signe("Z")

    def calcCombQuad(self):
        """Compute the quadratic combination of the CQC values of the 3 directions of the whole set of 'coupures' and for each components

        Resultat:
            list: list of dict, each item corresponding to a line in the future table

        The keys of the dicts correspond to the parameters of the table (NOM, NUME_MODE, R1, R2...)
        """
        lines = []
        for coupure in self.getCoupure():
            d = {cmp: self._calc_uni(coupure.nom, cmp).calcCombQuad() for cmp in L_CMP_RESU}
            d["NOM"] = coupure.nom
            d["DIRECTION"] = "XYZ"
            d["NUME_ORDRE"] = 4
            d["TYPE"] = "CQC"
            lines.append(d)
        return lines

    def calcCombNewmark(self):
        """Compute the Newmarks combinations of the CQC signed values of the 3 directions of the whole set of 'coupures' and for each components

        Resultat:
            list: list of dict, each item corresponding to a line in the future table

        The keys of the dicts correspond to the parameters of the table (NOM, NUME_MODE, R1, R2...)
        """
        lines = []
        for coupure in self.getCoupure():
            for i, nom in enumerate(NOM_NEWMARK):
                d = {
                    cmp: self._calc_uni(coupure.nom, cmp).calcCombNewmark()[i] for cmp in L_CMP_RESU
                }
                d["NOM"] = coupure.nom
                d["DIRECTION"] = nom
                d["NUME_ORDRE"] = i + 1
                d["TYPE"] = "NEWMARK"
                lines.append(d)
        return lines

    def calcModSpec(self):
        """Create the final dict to be

        Resultat:
            list: list of dict, each item corresponding to a line in the future table

        The keys of the dicts correspond to the parameters of the table (NOM, NUME_MODE, R1, R2...)
        """
        if self.comb_direction == "QUAD":
            lines = []
            # on aura 4 n°mode par coupure correspond à X, Y, Z et la combinaison quadratique des 3
            if self.signe == "OUI":
                for d in [
                    self.calcCqcSigneX(),
                    self.calcCqcSigneY(),
                    self.calcCqcSigneZ(),
                    self.calcCombQuad(),
                ]:
                    lines.extend(d)
            else:
                for d in [self.calcCqcX(), self.calcCqcY(), self.calcCqcZ(), self.calcCombQuad()]:
                    lines.extend(d)
        elif self.comb_direction == "NEWMARK":
            lines = self.calcCombNewmark()

        self.tab_resu = Table()
        for line in lines:
            self.tab_resu.append(line)
        tab = self.tab_resu.dict_CREA_TABLE()

        return CREA_TABLE(TYPE_TABLE="TABLE", **tab)
