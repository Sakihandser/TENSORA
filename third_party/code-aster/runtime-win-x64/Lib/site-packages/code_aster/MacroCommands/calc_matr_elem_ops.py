# coding: utf-8

# Copyright (C) 1991 - 2026  EDF www.code-aster.org
#
# This file is part of Code_Aster.
#
# Code_Aster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Code_Aster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Code_Aster.  If not, see <http://www.gnu.org/licenses/>.

from ..Objects import PhysicalProblem, DiscreteComputation

from ..Utilities import force_list


def calc_matr_elem_ops(self, **args):
    """Execute the command CALC_MATR_ELEM.

    Arguments:
        **args (dict): User's args.

    Returns:
        ElementaryMatrix: elementary matrix
    """

    # Define problem
    model = args["MODELE"]
    mater = args.get("CHAM_MATER")
    cara = args.get("CARA_ELEM")
    phys_pb = PhysicalProblem(model, mater, cara)

    loads = args.get("CHARGE")
    if loads is not None:
        for load in force_list(loads):
            phys_pb.addLoad(load)

    phys_pb.computeListOfLoads()

    disc_comp = DiscreteComputation(phys_pb)

    time = args["INST"]

    myOption = args["OPTION"]

    fourier = args.get("MODE_FOURIER")

    group_ma = args.get("GROUP_MA")
    if group_ma is None:
        group_ma = []
    else:
        group_ma = force_list(group_ma)

    varc = None
    if mater and mater.hasExternalStateVariable():
        varc = phys_pb.getExternalStateVariables(time)

    matr_elem = None
    if myOption in ("RIGI_MECA", "RIGI_THER", "RIGI_ACOU"):
        if "CALC_ELEM_MODELE" not in args or args["CALC_ELEM_MODELE"] == "OUI":
            matr_elem = disc_comp.getLinearStiffnessMatrix(time, fourier, varc, group_ma)

            if model.isThermal():
                matr_elem_exch = disc_comp.getThermalExchangeMatrix(time)
                matr_elem.addElementaryTerm(matr_elem_exch.getElementaryTerms())
                matr_elem.build()
        else:
            matr_elem = disc_comp.getDualStiffnessMatrix()

    elif myOption == "RIGI_GEOM":
        sief_elga = args.get("SIEF_ELGA")
        strx_elga = args.get("STRX_ELGA")
        displ = args.get("DEPL")

        matr_elem = disc_comp.getGeometricStiffnessMatrix(
            sief_elga, strx_elga, displ, fourier, group_ma
        )

    elif myOption == "RIGI_ROTA":
        matr_elem = disc_comp.getRotationalStiffnessMatrix(group_ma)

    elif myOption == "RIGI_GYRO":
        matr_elem = disc_comp.getGyroscopicStiffnessMatrix(group_ma)

    elif myOption == "MECA_GYRO":
        matr_elem = disc_comp.getGyroscopicDampingMatrix(group_ma)

    elif myOption in ("MASS_MECA", "MASS_THER", "MASS_ACOU"):
        matr_elem = disc_comp.getMassMatrix(time, varc, group_ma)

    elif myOption == "MASS_MECA_DIAG":
        matr_elem = disc_comp.getMechanicalMassMatrix(True, varc, group_ma)

    elif myOption == "AMOR_MECA":
        amorflui = args["AMOR_FLUI"]
        v_nor = args["VNOR"]
        if amorflui == "OUI":
            flui_int = int(1)
        else:
            flui_int = int(0)
        if v_nor == 1.0:
            onde_flui = int(1)
        else:
            onde_flui = int(0)
        getMechanicalMassMatrix = args.get("MASS_MECA")
        stiffnessMatrix = args.get("RIGI_MECA")
        matr_elem = disc_comp.getMechanicalDampingMatrix(
            getMechanicalMassMatrix, stiffnessMatrix, varc, group_ma, flui_int, onde_flui
        )

    elif myOption == "RIGI_MECA_HYST":
        stiffnessMatrix = args["RIGI_MECA"]
        matr_elem = disc_comp.getHystereticStiffnessMatrix(stiffnessMatrix, varc, group_ma)

    elif myOption == "AMOR_ACOU":
        v_nor = args["VNOR"]
        if v_nor == 1.0:
            onde_flui = int(1)
        else:
            onde_flui = int(0)
        matr_elem = disc_comp.getImpedanceMatrix(onde_flui)

    elif myOption == "RIGI_FLUI_STRU":
        matr_elem = disc_comp.getFluidStructureStiffnessMatrix(
            varc_curr=varc, groupOfCells=group_ma
        )

        matr_rigi_dual = disc_comp.getDualStiffnessMatrix()
        matr_elem.addElementaryTerm(matr_rigi_dual.getElementaryTerms())
        matr_elem.build()

    elif myOption == "MASS_FLUI_STRU":
        matr_elem = disc_comp.getFluidStructureMassMatrix(groupOfCells=group_ma)

    elif myOption == "IMPE_MECA":
        v_nor = args["VNOR"]
        if v_nor == 1.0:
            onde_flui = int(1)
        else:
            onde_flui = int(0)
        matr_elem = disc_comp.getImpedanceBoundaryMatrix(group_ma, onde_flui)

    elif myOption == "ONDE_FLUI":
        matr_elem = disc_comp.getImpedanceWaveMatrix(group_ma)

    else:
        raise RuntimeError("Option %s not implemented" % (myOption))
    matr_elem.setModel(model)

    return matr_elem
