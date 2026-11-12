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

from ...Objects import (
    ContactComputation,
    ContactPairing,
    ParallelContactNew,
    ParallelContactPairing,
    ParallelFrictionNew,
)
from ...Utilities import no_new_attributes, profile


class ContactManager:
    """Solve contact problem."""

    defi = pair = comp = None
    coef_cont = coef_frot = None
    problem = None
    nb_pairing = 0
    __setattr__ = no_new_attributes(object.__setattr__)

    def __init__(self, definition, phys_pb):
        """Initialize contact solver.

        Arguments:
            definition (ContactNew): contact definition
            phys_pb (PhysicalProblem): physical problem
        """
        super().__init__()
        self.nb_pairing = 0
        self.defi = definition
        self.problem = phys_pb
        if self.defi is not None:
            if isinstance(self.defi, (ParallelFrictionNew, ParallelContactNew)):
                self.pair = ParallelContactPairing(self.defi)
            else:
                self.pair = ContactPairing(self.defi)
            self.comp = ContactComputation(self.defi)
            self.coef_cont, self.coef_frot = self.comp.contactCoefficient()

    @profile
    def pairing(self):
        """Pairing between contact zones."""
        if not self.isEnabled:
            return
        self.pair.compute()

        # Numbering does not change but connectivity yes.
        phys_pb = self.problem
        if isinstance(self.defi, (ParallelFrictionNew, ParallelContactNew)):
            fed_defi = self.defi.getParallelFiniteElementDescriptor()
        else:
            fed_defi = self.defi.getFiniteElementDescriptor()

        if self.isPaired:
            if isinstance(self.pair, ParallelContactPairing):
                fed_pair = self.pair.getParallelFiniteElementDescriptor()
            else:
                fed_pair = self.pair.getFiniteElementDescriptor()
            phys_pb.setContactSlaveFED(fed_defi)
            phys_pb.setContactFED(fed_pair)
            model = phys_pb.getModel()
            loads = phys_pb.getListOfLoads()
            phys_pb.getDOFNumbering().computeRenumbering(model, loads, fed_defi, fed_pair)

        self.nb_pairing += 1

    @profile
    def getPairingCoordinates(self):
        """Get the coordinates field used for pairing.

        Returns:
            MeshCoordinatesField: coordinates of nodes used for pairing
        """
        if not self.isEnabled:
            return
        return self.pair.getCoordinates()

    @profile
    def setPairingCoordinates(self, coor):
        """Set the coordinates field used for pairing.

        Returns:
            coor (MeshCoordinatesField): coordinates of nodes used for pairing
        """
        if not self.isEnabled:
            return
        self.pair.setCoordinates(coor)

    @profile
    def data(self):
        """Compute data for DiscreteComputation.

        Returns:
            (FieldOnCellsReal): data
        """
        if not self.isEnabled or not self.isPaired:
            return
        return self.comp.contactData(
            self.pair, self.problem.getMaterialField(), self.nb_pairing <= 1
        )

    @property
    def isEnabled(self):
        """Contact is enable or not

        Returns:
            bool: True if enable else False
        """
        if self.defi is not None:
            return True

        return False

    @property
    def isPaired(self):
        """Pairing is done or not

        Returns:
            bool: True if paired else False
        """
        if self.comp.hasVirtualCells(self.pair):
            return True

        return False

    def update(self, phys_state):
        """Update contact solver.

        Arguments:
            phys_state (PhysicalSate): physical state
        """
        if not self.isEnabled:
            return
        self.pair.updateCoordinates(phys_state.U)
