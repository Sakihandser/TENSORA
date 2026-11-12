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
Ce module définit des fonctions permettant de manipuler un résultat issu de THYC
"""

from ...Cata.Syntax import _F
from ...CodeCommands import AFFE_CHAR_MECA, AFFE_CHAR_MECA_F
from ...Objects import Function
from ...Messages import ASSERT, UTMESS
from ...Helpers.LogicalUnit import LogicalUnitFile
from ...Utilities import logger
from .thyc_result import ThycResult


def DEFI_FONCTION_PROFILE(px, py):
    func = Function()
    func.setParameterName("X")
    func.setExtrapolation("CC")
    func.setInterpolation("LIN LIN")
    func.setValues(px, py)
    return func


class ThycLoadManager:
    """Object to represent a result read from THYC"""

    __slots__ = ("chtr_nodal", "chtr_poutre", "chax_nodal", "chax_poutre")

    @classmethod
    def from_unit(cls, coeur, model, unit):
        fname = LogicalUnitFile.filename_from_unit(unit)
        thyc_load = cls.from_file(coeur, model, fname)
        return thyc_load

    @classmethod
    def from_file(cls, coeur, model, fname):
        """XXX
        À définir dans un autre module : fonction qui prend un Coeur en argument
        ou un objet ThycLoadManager avec .read(), .hydr_load()... pour récupérer les
        différents résultats
        """
        # Fonction multiplicative de la force hydrodynamique axiale.
        # On multiplie par 0.708 les forces hydrodynamiques a froid pour obtenir
        # celles a chaud.
        FOHYFR_1 = 1.0  # Valeur a froid
        FOHYCH_1 = 0.708  # Valeur a chaud
        RAT_CHFR = FOHYCH_1 / FOHYFR_1  # Ratio chaud froid

        thyc_load = cls()
        thyc_resu = ThycResult()
        thyc_resu.grids_position = coeur.altitude
        thyc_resu.nozzles_position = (coeur.XINFT, coeur.XSUPT)
        thyc_resu.apply_nozzle_transversal_load = True
        thyc_resu.read_thyc_file(fname)
        ASSERT(coeur.NBAC == thyc_resu.fa_number)
        if not all(abs(thyc_resu.cells_size - thyc_resu.cells_size_from_center) < 1.0e-4):
            UTMESS("A", "COEUR0_6")
            logger.debug("<THYC_LOAD><COEUR0_6>: cells_size = %s" % (thyc_resu.cells_size))
            logger.debug(
                "<THYC_LOAD><COEUR0_6>: cells_size_from_center = %s"
                % (thyc_resu.cells_size_from_center)
            )

        logger.debug("<THYC_LOAD>: Start")
        n1 = len(thyc_resu.grids_index)
        n2 = len(thyc_resu.grids_position)
        if n1 != n2:
            UTMESS("F", "COEUR0_7", vali=(n1, n2))
        logger.debug("<THYC_LOAD>: Grids index %s" % thyc_resu.grids_index)
        logger.debug("<THYC_LOAD>: Nozzles index %s" % thyc_resu.nozzles_index)

        # Recuperation des efforts transverses sur les grilles
        nodal_tr = []
        linear_tr = []
        nodal_ax = []
        linear_ax = []

        chThyc = {}
        for posX_thyc, posY_thyc in thyc_resu.fa_positions:
            posi_aster = coeur.position_fromthyc(posX_thyc, posY_thyc)
            logger.debug(
                "<THYC_LOAD>: Position THYC : (%s, %s) MAC3 : %s"
                % (posX_thyc, posY_thyc, posi_aster)
            )

            idAC = coeur.position_todamac(posi_aster)
            ac = coeur.collAC[idAC]

            tr_x = thyc_resu.transversal_force_x(posX_thyc, posY_thyc)
            tr_y = thyc_resu.transversal_force_y(posX_thyc, posY_thyc)
            force_ax = thyc_resu.axial_force(posX_thyc, posY_thyc)

            cr_grp_ma = "CR_%s" % posi_aster

            for j, grid_j in enumerate(thyc_resu.grids_index):
                grid_grp_no = "G_%s_%d" % (posi_aster, j + 1)
                chThyc["X"] = tr_x[grid_j] / ac.nb_nodes_grid
                chThyc["Y"] = tr_y[grid_j] / ac.nb_nodes_grid

                logger.debug(
                    "<THYC_LOAD><TRANSVERSAL>: Grid group %s : LoadX = %s, LoadY = %s"
                    % (grid_grp_no, chThyc["X"], chThyc["Y"])
                )

                chAsterY = coeur.coefFromThyc("Y") * chThyc[coeur.axeFromThyc("Y")]
                chAsterZ = coeur.coefFromThyc("Z") * chThyc[coeur.axeFromThyc("Z")]
                nodal_tr.extend([_F(GROUP_NO=grid_grp_no, FY=chAsterY, FZ=chAsterZ)])

            for direction in ("X", "Y"):
                px, py, fy = thyc_resu.get_transversal_load_profile(
                    posX_thyc, posY_thyc, direction, coeur.coefToThyc(direction)
                )
                logger.debug(
                    "<THYC_LOAD><TRANSVERSAL>: Rod group %s, direction %s" % (cr_grp_ma, direction)
                )
                logger.debug("<THYC_LOAD><TRANSVERSAL>:   px = %s" % px)
                logger.debug("<THYC_LOAD><TRANSVERSAL>:   py = %s" % py)
                logger.debug("<THYC_LOAD><TRANSVERSAL>:   fy = %s" % fy)

                chThyc[direction] = DEFI_FONCTION_PROFILE(px, [v / coeur.nb_cr_mesh for v in py])

            linear_tr.extend(
                [
                    _F(
                        GROUP_MA=cr_grp_ma,
                        FY=chThyc[coeur.axeFromThyc("Y")],
                        FZ=chThyc[coeur.axeFromThyc("Z")],
                    )
                ]
            )

            # Chargements axiaux
            KTOT = ac.K_GRM * (ac.NBGR - 2) + ac.K_GRE * 2 + ac.K_EBSU + ac.K_TUB + ac.K_EBIN

            # Force axiale pour une grille extremite (inf)
            grp_ax_g1 = "G_%s_1" % posi_aster
            f_ax_g1 = force_ax / RAT_CHFR * ac.K_GRE / KTOT / ac.nb_nodes_grid
            nodal_ax.extend([_F(GROUP_NO=grp_ax_g1, FX=f_ax_g1)])
            logger.debug(
                "<THYC_LOAD><AXIAL>: Grid group %s : Axial Load = %s" % (grp_ax_g1, f_ax_g1)
            )

            # Force axiale pour chacune des grilles de mélange
            for j in range(1, ac.NBGR - 1):
                grp_ax_gi = "G_%s_%d" % (posi_aster, j + 1)
                f_ax_gi = force_ax / RAT_CHFR * ac.K_GRM / KTOT / ac.nb_nodes_grid
                nodal_ax.extend([_F(GROUP_NO=grp_ax_gi, FX=f_ax_gi)])
                logger.debug(
                    "<THYC_LOAD><AXIAL>: Grid group %s : Axial Load = %s" % (grp_ax_gi, f_ax_gi)
                )

            grp_ax_glast = "G_%s_%d" % (posi_aster, ac.NBGR)
            f_ax_glast = force_ax / RAT_CHFR * ac.K_GRE / KTOT / ac.nb_nodes_grid
            nodal_ax.extend([_F(GROUP_NO=grp_ax_glast, FX=f_ax_glast)])
            logger.debug(
                "<THYC_LOAD><AXIAL>: Grid group %s : Axial Load = %s" % (grp_ax_glast, f_ax_glast)
            )

            # Force axiale pour l'embout inferieur
            grp_ax_pi = "PI_%s" % posi_aster
            f_ax_pi = force_ax / RAT_CHFR * ac.K_EBIN / KTOT
            nodal_ax.extend([_F(GROUP_NO=grp_ax_pi, FX=f_ax_pi)])
            logger.debug(
                "<THYC_LOAD><AXIAL>: Nozzle group %s : Axial Load = %s" % (grp_ax_pi, f_ax_pi)
            )

            # Force axiale pour l'embout superieur
            grp_ax_ps = "PS_%s" % posi_aster
            f_ax_ps = force_ax / RAT_CHFR * ac.K_EBSU / KTOT
            nodal_ax.extend([_F(GROUP_NO=grp_ax_ps, FX=f_ax_ps)])
            logger.debug(
                "<THYC_LOAD><AXIAL>: Nozzle group %s : Axial Load = %s" % (grp_ax_ps, f_ax_ps)
            )

            # Force axiale pour les crayons
            cr_grp_ma = "CR_%s" % posi_aster
            f_ax_cr = (
                force_ax / RAT_CHFR * ac.K_TUB / KTOT * ac.NBCR / (ac.NBCR + ac.NBTG) / ac.LONCR
            )
            f_ax_cr /= ac.nb_cr_mesh
            _FXC = DEFI_FONCTION_PROFILE([ac.XINFC, ac.XSUPC], [f_ax_cr, f_ax_cr])
            linear_ax.extend([_F(GROUP_MA=cr_grp_ma, FX=_FXC)])
            logger.debug(
                "<THYC_LOAD><AXIAL>: Rod group %s : Axial Load = %s" % (cr_grp_ma, f_ax_cr)
            )

            # Force axiale pour les tubes-guides
            tg_grp_ma = "TG_%s" % posi_aster
            f_ax_tg = (
                force_ax / RAT_CHFR * ac.K_TUB / KTOT * ac.NBTG / (ac.NBCR + ac.NBTG) / ac.LONTU
            )
            f_ax_tg /= ac.nb_tg_mesh
            _FXT = DEFI_FONCTION_PROFILE([ac.XINFT, ac.XSUPT], [f_ax_tg, f_ax_tg])
            linear_ax.extend([_F(GROUP_MA=tg_grp_ma, FX=_FXT)])
            logger.debug(
                "<THYC_LOAD><AXIAL>: Tubes group %s : Axial Load = %s" % (tg_grp_ma, f_ax_tg)
            )

        thyc_load.chtr_nodal = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=nodal_tr)
        thyc_load.chtr_poutre = AFFE_CHAR_MECA_F(MODELE=model, FORCE_POUTRE=linear_tr)
        thyc_load.chax_nodal = AFFE_CHAR_MECA(MODELE=model, FORCE_NODALE=nodal_ax)
        thyc_load.chax_poutre = AFFE_CHAR_MECA_F(MODELE=model, FORCE_POUTRE=linear_ax)

        logger.debug("<THYC_LOAD>: Reading of THYC file completed.")

        return thyc_load
