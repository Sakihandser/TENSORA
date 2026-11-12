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
:py:class:`DiscreteComputation` --- DiscreteComputation object
******************************************************
"""

from libaster import (
    AssemblyMatrixDisplacementReal,
    AssemblyMatrixPressureComplex,
    AssemblyMatrixTemperatureReal,
    DiscreteComputation,
)

from ..Solvers import Residuals
from ..Supervis import IntegrationError
from ..Utilities import injector, profile, MPI


@injector(DiscreteComputation)
class ExtendedDiscreteComputation:
    def __getinitargs__(self):
        """Returns the argument required to reinitialize a MaterialField
        object during unpickling.
        """
        return (self.getPhysicalProblem(),)

    # add profile to theses methods
    getThermalNeumannForces = profile(DiscreteComputation.getThermalNeumannForces)
    getThermalVolumetricForces = profile(DiscreteComputation.getThermalVolumetricForces)
    getThermalExchangeForces = profile(DiscreteComputation.getThermalExchangeForces)
    getTransientThermalLoadForces = profile(DiscreteComputation.getTransientThermalLoadForces)
    getTransientThermalForces = profile(DiscreteComputation.getTransientThermalForces)
    getThermalExchangeMatrix = profile(DiscreteComputation.getThermalExchangeMatrix)
    getLinearCapacityMatrix = profile(DiscreteComputation.getLinearCapacityMatrix)

    @profile
    def getDirichletBC(self, time=0.0):
        """Return the imposed displacement vector used to remove imposed DDL

        Arguments:
              time (float): Current time (default 0.0)

        Returns:
              FieldOnNodes: imposed BC vector
        """

        phys_pb = self.getPhysicalProblem()

        if phys_pb.isMechanical():
            return self.getMechanicalDirichletBC(time)
        elif phys_pb.isThermal():
            return self.getThermalDirichletBC(time)
        elif phys_pb.isAcoustic():
            return self.getAcousticDirichletBC(time)
        else:
            raise RuntimeError("Unknown physics")

    @profile
    def getLinearStiffnessMatrix(
        self,
        time=0.0,
        fourierMode=-1,
        varc_curr=None,
        groupOfCells=[],
        with_dual=True,
        assembly=False,
    ):
        """Return the elementary matrices for stiffness matrix depending of the physic.
        Option RIGI_MECA or RIGI_THER or RIGI_ACOU.

        Arguments:
              time (float): Current time for external state variable evaluation.
                Only needed if material depends on time (default: 0.0)
              fourierMode (int): Fourier mode (default: -1)
              varc_curr (FieldOnCellsReal): external state variables at current time (default: None)
              groupOfCells (list[str]): compute matrices on given groups of cells.
                  If it is empty, the full model is used
              with_dual (bool): compute dual terms or not (default: True)
              assembly (bool): assemble elementary matrix (default: False)
        Returns:
              ElementaryMatrix / AssemblyMatrix: (elementary) stiffness matrix depends
                on 'assembly' keyword
        """

        phys_pb = self.getPhysicalProblem()

        if phys_pb.isMechanical():
            matr_elem = self.getElasticStiffnessMatrix(
                time, fourierMode, varc_curr, groupOfCells, with_dual
            )

            if assembly:
                matr_asse = AssemblyMatrixDisplacementReal(self.getPhysicalProblem())
                matr_asse.assemble(matr_elem, self.getPhysicalProblem().getListOfLoads())
                return matr_asse

        elif phys_pb.isThermal():
            matr_elem = self.getLinearConductivityMatrix(
                time, fourierMode, varc_curr, groupOfCells, with_dual
            )

            if assembly:
                matr_asse = AssemblyMatrixTemperatureReal(self.getPhysicalProblem())
                matr_asse.assemble(matr_elem, self.getPhysicalProblem().getListOfLoads())
                return matr_asse

        elif phys_pb.isAcoustic():
            matr_elem = self.getLinearMobilityMatrix(groupOfCells, with_dual)

            if assembly:
                matr_asse = AssemblyMatrixPressureComplex(self.getPhysicalProblem())
                matr_asse.assemble(matr_elem, self.getPhysicalProblem().getListOfLoads())
                return matr_asse
        else:
            raise RuntimeError("Unknown physic")

        return matr_elem

    @profile
    def getDualStiffnessMatrix(self, assembly=False):
        """Return the elementary matrices for dual stiffness matrix depending of the physic.

        Arguments:
              assembly (bool): assemble elementary matrix (default: False)
        Returns:
              ElementaryMatrix: elementary dual stiffness matrix
        """

        phys_pb = self.getPhysicalProblem()

        if phys_pb.isMechanical():
            matr_elem = self.getDualElasticStiffnessMatrix()

            if assembly:
                matr_asse = AssemblyMatrixDisplacementReal(self.getPhysicalProblem())
                matr_asse.assemble(matr_elem, self.getPhysicalProblem().getListOfLoads())
                return matr_asse

        elif phys_pb.isThermal():
            matr_elem = self.getDualLinearConductivityMatrix()

            if assembly:
                matr_asse = AssemblyMatrixTemperatureReal(self.getPhysicalProblem())
                matr_asse.assemble(matr_elem, self.getPhysicalProblem().getListOfLoads())
                return matr_asse

        elif phys_pb.isAcoustic():
            matr_elem = self.getDualLinearMobilityMatrix()

            if assembly:
                matr_asse = AssemblyMatrixPressureComplex(self.getPhysicalProblem())
                matr_asse.assemble(matr_elem, self.getPhysicalProblem().getListOfLoads())
                return matr_asse

        else:
            raise RuntimeError("Unknown physic")

        return matr_elem

    @profile
    def getMassMatrix(self, time=0.0, varc_curr=None, groupOfCells=[], assembly=False):
        """Return the elementary matrices formass matrix depending of the physic.
        Option MASS_MECA or MASS_THER or MASS_ACOU.

        Arguments:
              time (float): Current time for external state variable evaluation.
                Only needed if material depends on time (default: 0.0)
              varc_curr (FieldOnCellsReal): external state variables at current time (default: None)
              groupOfCells (list[str]): compute matrices on given groups of cells.
                  If it is empty, the full model is used
              assembly (bool): assemble elementary matrix (default: False)
        Returns:
              ElementaryMatrix: elementary mass matrix
        """

        phys_pb = self.getPhysicalProblem()

        if phys_pb.isMechanical():
            matr_elem = self.getMechanicalMassMatrix(False, varc_curr, groupOfCells)

            if assembly:
                matr_asse = AssemblyMatrixDisplacementReal(self.getPhysicalProblem())
                matr_asse.assemble(matr_elem, self.getPhysicalProblem().getListOfLoads())
                return matr_asse

        elif phys_pb.isThermal():
            matr_elem = self.getLinearCapacityMatrix(time, varc_curr, groupOfCells)

            if assembly:
                matr_asse = AssemblyMatrixTemperatureReal(self.getPhysicalProblem())
                matr_asse.assemble(matr_elem, self.getPhysicalProblem().getListOfLoads())
                return matr_asse

        elif phys_pb.isAcoustic():
            matr_elem = self.getCompressibilityMatrix(groupOfCells)

            if assembly:
                matr_asse = AssemblyMatrixPressureComplex(self.getPhysicalProblem())
                matr_asse.assemble(matr_elem, self.getPhysicalProblem().getListOfLoads())
                return matr_asse
        else:
            raise RuntimeError("Unknown physic")

        return matr_elem

    @profile
    def getDampingMatrix(
        self,
        massMatrix=None,
        stiffnessMatrix=None,
        varc_curr=None,
        groupOfCells=[],
        fluiInt=1,
        ondeFlui=1,
        assembly=False,
    ):
        """Return the elementary matrices for damping matrix depending of the physic.
        Option AMOR_MECA or AMOR_ACOU.

        Arguments:
              massMatrix : elementary mass matrix.
              stiffnessMatrix : elementary stiffness matrix.
              varc_curr (FieldOnCellsReal): external state variables at current time (default: None)
              groupOfCells (list[str]): compute matrices on given groups of cells.
                  If it is empty, the full model is used
              fluiInt (int) : xxxx xxxx xxxx xxxx.
              ondeFlui (int) : xxxx xxxx xxxx xxxx.
              assembly (bool): assemble elementary matrix (default: False)
        Returns:
              ElementaryMatrix: elementary damping matrix
        """

        phys_pb = self.getPhysicalProblem()

        if phys_pb.isMechanical():
            matr_elem = self.getMechanicalDampingMatrix(
                massMatrix, stiffnessMatrix, varc_curr, groupOfCells, fluiInt, ondeFlui
            )

            if assembly:
                matr_asse = AssemblyMatrixDisplacementReal(self.getPhysicalProblem())
                matr_asse.assemble(matr_elem, self.getPhysicalProblem().getListOfLoads())
                return matr_asse

        elif phys_pb.isThermal():
            raise RuntimeError("Not implemented yet")

        elif phys_pb.isAcoustic():
            matr_elem = self.getImpedanceMatrix(ondeFlui)

            if assembly:
                matr_asse = AssemblyMatrixPressureComplex(self.getPhysicalProblem())
                matr_asse.assemble(matr_elem, self.getPhysicalProblem().getListOfLoads())
                return matr_asse

        else:
            raise RuntimeError("Unknown physic")

        return matr_elem

    @profile
    def getVolumetricForces(
        self, time_curr=0.0, time_step=0.0, theta=1, mode=0, varc_curr=None, assembly=True
    ):
        """Return the volumetric forces field

        Arguments:
                time_curr (float): Current time
                time_step (float): Time increment
                theta (float): Theta parameter for time-integration
                mode (int) : fourier mode
                varc_curr (FieldOnCellsReal): external state variables at current time (default: None)
                assembly (bool): assemble if True

        Returns:
                ElementaryVector: elementary volumetric forces vector if assembly=False
                FieldOnNodes: volumetric forces field if assembly=True
        """

        phys_pb = self.getPhysicalProblem()

        if phys_pb.isThermal():
            return self.getThermalVolumetricForces(time_curr, varc_curr, assembly)
        elif phys_pb.isMechanical():
            return self.getMechanicalVolumetricForces(
                time_curr, time_step, theta, mode, varc_curr, assembly
            )
        elif phys_pb.isAcoustic():
            return self.getAcousticVolumetricForces(assembly)
        else:
            raise RuntimeError("Not implemented")

    @profile
    def getNeumannForces(
        self, time_curr=0.0, time_step=0.0, theta=1, mode=0, varc_curr=None, assembly=True
    ):
        """Return the Neumann forces field

        Arguments:
                time_curr (float): Current time
                time_step (float): Time increment
                theta (float): Theta parameter for time-integration
                mode (int) : fourier mode
                varc_curr (FieldOnCellsReal): external state variables at current time (default: None)
                assembly (bool): assemble if True

        Returns:
                ElementaryVector: elementary Neumann forces vector if assembly=False
                FieldOnNodes: Neumann forces field if assembly=True
        """

        phys_pb = self.getPhysicalProblem()

        if phys_pb.isThermal():
            return self.getThermalNeumannForces(time_curr, assembly)
        elif phys_pb.isMechanical():
            return self.getMechanicalNeumannForces(
                time_curr, time_step, theta, mode, varc_curr, assembly
            )
        elif phys_pb.isAcoustic():
            return self.getAcousticNeumannForces(assembly)
        else:
            raise RuntimeError("Not implemented")

    @profile
    def getNonLinearNeumannForces(self, U, time_curr, assembly=True):
        """Return the nonlinear Neumann forces field

        Arguments:
                U : current primal solution
                time_curr (float): current time
                assembly (bool): assemble if True

        Returns:
                ElementaryVector: elementary Neumann forces vector if assembly=False
                FieldOnNodes: Neumann forces field if assembly=True
        """

        phys_pb = self.getPhysicalProblem()

        if phys_pb.isThermal():
            return self.getThermalNonLinearNeumannForces(U, time_curr, assembly)
        elif phys_pb.isMechanical():
            raise RuntimeError("Not implemented")
        elif phys_pb.isAcoustic():
            raise RuntimeError("Not implemented")
        else:
            raise RuntimeError("Not implemented")

    @profile
    def getImposedDualBC(self, time_curr=0.0, assembly=True):
        """Return imposed nodal BC field

        Arguments:
                time_curr (float): Current time
                assembly (bool): assemble if True

        Returns:
                ElementaryVector: elementary imposed nodal BC vector if assembly=False
                FieldOnNodes: imposed nodal BC field if assembly=True
        """

        phys_pb = self.getPhysicalProblem()

        if phys_pb.isThermal():
            return self.getThermalImposedDualBC(time_curr, assembly)
        elif phys_pb.isMechanical():
            return self.getMechanicalImposedDualBC(time_curr, assembly)
        elif phys_pb.isAcoustic():
            return self.getAcousticImposedDualBC(assembly)
        else:
            raise RuntimeError("Not implemented")

    @profile
    def getInternalResidual(self, phys_state, scaling=1.0, tmp_internVar=None):
        """Compute internal residual R_int(u, Lagr).

            R_int(u, Lagr) = [B^t.Sig(u) + B^t.Lagr, B^t.primal-primal_impo]

        Arguments:
            phys_state (PhysicalState): physical state
            scaling (float): Scaling factor for Lagrange multipliers (default: 1.0)

        Returns:
            Residuals: residuals container
            FieldOnCellsReal: internal state variables (VARI_ELGA)
            FieldOnCellsReal: Cauchy stress tensor (SIEF_ELGA)
        """

        phys_pb = self.getPhysicalProblem()

        # Compute internal forces (B^t.stress)
        if phys_pb.isMechanical():
            if tmp_internVar is None:
                tempVar = phys_state.internVar
            else:
                tempVar = tmp_internVar
            _, codret, internVar, stress, r_stress = self.getInternalMechanicalForces(
                phys_state.U_t,
                phys_state.deltaU,
                phys_state.stress,
                phys_state.internVar,
                tempVar,
                phys_state.time_prev,
                phys_state.time_step,
                phys_state.getState(-1).externVar,
                phys_state.externVar,
            )
        else:
            codret, stress, r_stress = self.getInternalThermalForces(
                phys_state.U_t, phys_state.deltaU, phys_state.externVar
            )
            internVar = None

        resi = Residuals()

        resi.resi_stress = r_stress.copy()
        r_int = r_stress

        if codret > 0:
            raise IntegrationError("MECANONLINE10_1")

        phys_pb = self.getPhysicalProblem()
        if phys_pb.getDOFNumbering().useLagrangeDOF():
            # Compute kinematic forces (B^t.Lagr_curr)
            dualizedBC_forces = self.getDualForces(phys_state.U)
            resi.resi_dual = dualizedBC_forces

            # Compute dualized BC (B^t.U - primal_impo)
            # Compute dualized BC (B^t.U)
            dualizedBC_disp = self.getDualPrimal(phys_state.U, scaling)

            # Imposed dualized BC (primal_impo)
            dualizedBC_impo = self.getImposedDualBC(phys_state.time_curr)

            r_int += dualizedBC_forces + dualizedBC_disp - dualizedBC_impo
        else:
            resi.resi_dual = phys_state.createPrimal(phys_pb, 0.0)

        resi.resi_int = r_int

        return resi, internVar, stress

    @profile
    def getExternalResidual(self, phys_state):
        """Compute external residual R_ext(u, Lagr)

        R_ext(u, Lagr) = [(f(u),v), 0]

        Arguments:
            phys_state (PhysicalState) : physical state

        Returns
            FieldOnNodesReal: external residual field
        """

        resi_ext = None
        if self.getPhysicalProblem().isThermal():
            resi_ext = self.getNeumannForces(phys_state.time_curr, varc_curr=phys_state.externVar)

            resi_ext += self.getVolumetricForces(
                phys_state.time_curr, varc_curr=phys_state.externVar
            )

            resi_ext += self.getNonLinearNeumannForces(phys_state.U, phys_state.time_curr)

            resi_ext += self.getThermalExchangeForces(phys_state.U, phys_state.time_curr)
            resi_ext += self.getThermalNonLinearVolumetricForces(phys_state.U, phys_state.time_curr)
        elif self.getPhysicalProblem().isMechanical():
            resi_ext = self.getNeumannForces(
                phys_state.time_curr, time_step=phys_state.time_step, varc_curr=phys_state.externVar
            )

            resi_ext += self.getVolumetricForces(
                phys_state.time_curr, varc_curr=phys_state.externVar
            )

            resi_ext -= self.getMechanicalCouplingForces(
                phys_state.U_t, phys_state.deltaU, phys_state.time_prev, phys_state.time_step
            )
        else:
            raise RuntimeError()

        return resi_ext

    @profile
    def getContactResidual(self, phys_state, contact_manager):
        """Compute contact residual R_cont(u, Lagr)

        Arguments:
            phys_state (PhysicalState) : physical state
            contact_manager (ContactManager) : contact manager

        Returns
            FieldOnNodesReal: contact residual field

        """

        if contact_manager:
            if contact_manager.isEnabled and contact_manager.isPaired:
                if contact_manager.defi.isParallel():
                    cMesh = contact_manager.defi.getConnectionModel().getMesh()
                    U_t = phys_state.U_t.transfertToConnectionMesh(cMesh)
                    deltaU = phys_state.deltaU.transfertToConnectionMesh(cMesh)
                else:
                    U_t = phys_state.U_t
                    deltaU = phys_state.deltaU
                # Compute contact forces
                contact_forces = self.getContactForces(
                    contact_manager.getPairingCoordinates(),
                    U_t,
                    deltaU,
                    phys_state.time_prev,
                    phys_state.time_step,
                    contact_manager.data(),
                    contact_manager.coef_cont,
                    contact_manager.coef_frot,
                )
            else:
                contact_forces = phys_state.createPrimal(self.getPhysicalProblem(), 0.0)
        else:
            contact_forces = phys_state.createPrimal(self.getPhysicalProblem(), 0.0)

        return contact_forces

    @profile
    def getResidual(self, phys_state, contact_manager=None, scaling=1.0, tmp_internVar=None):
        """Compute R(u, Lagr) = - (Rint(u, Lagr) + Rcont(u, Lagr) - Rext(u, Lagr)).

        This is not the true residual but the opposite.

        Arguments:
            phys_state (PhysicalState) : physical state
            contact_manager (ContactManager) : contact manager
            scaling (float): Scaling factor for Lagrange multipliers (default: 1.0).

        Returns:
            tuple(Residuals, FieldOnCellsReal, FieldOnCellsReal):
            Tuple with residuals, internal state variables (VARI_ELGA),
            Cauchy stress tensor (SIEF_ELGA).
        """

        resi, internVar, stress = self.getInternalResidual(phys_state, scaling, tmp_internVar)
        resi.resi_ext = self.getExternalResidual(phys_state)
        resi.resi_cont = self.getContactResidual(phys_state, contact_manager)

        # Compute residual
        resi.resi = -(resi.resi_int + resi.resi_cont - resi.resi_ext)

        return resi, internVar, stress

    @profile
    def getInternalTangentMatrix(
        self, phys_state, matrix_type="TANGENTE", assemble=False, tmp_internVar=None
    ):
        """Compute K(u) = d(Rint(u)) / du

        Arguments:
            phys_state (PhysicalState) : physical state
            matrix_type (str): type of matrix used.
            assemble (bool): assemble or not the matrix

        Returns:
            int : error code flag
            ElementaryMatrixDisplacementReal: rigidity matrix.
            ElementaryMatrixDisplacementReal: dual matrix.
        """
        # Main object for discrete computation
        phys_pb = self.getPhysicalProblem()

        # Compute rigidity matrix
        if matrix_type in ("PRED_ELASTIQUE", "ELASTIQUE"):
            matr_elem_rigi = self.getLinearStiffnessMatrix(
                time=phys_state.time_curr, varc_curr=phys_state.externVar, with_dual=False
            )
            codret = 0
        elif matrix_type == "PRED_TANGENTE":
            if phys_pb.isMechanical():
                _, codret, matr_elem_rigi = self.getPredictionTangentStiffnessMatrix(
                    phys_state.U_t,
                    phys_state.deltaU,
                    phys_state.stress,
                    phys_state.internVar,
                    phys_state.time_prev,
                    phys_state.time_step,
                    phys_state.getState(-1).externVar,
                    phys_state.externVar,
                )
            else:
                matr_elem_rigi = self.getTangentConductivityMatrix(
                    phys_state.U_t, phys_state.deltaU, phys_state.externVar, with_dual=False
                )
                codret = 0
        elif matrix_type == "TANGENTE":
            if phys_pb.isMechanical():
                if tmp_internVar is None:
                    tempVar = phys_state.internVar
                else:
                    tempVar = tmp_internVar
                _, codret, matr_elem_rigi = self.getTangentStiffnessMatrix(
                    phys_state.U_t,
                    phys_state.deltaU,
                    phys_state.stress,
                    phys_state.internVar,
                    tempVar,
                    phys_state.time_prev,
                    phys_state.time_step,
                    phys_state.getState(-1).externVar,
                    phys_state.externVar,
                )
            else:
                matr_elem_rigi = self.getTangentConductivityMatrix(
                    phys_state.U_t, phys_state.deltaU, phys_state.externVar, with_dual=False
                )
                codret = 0
        else:
            raise RuntimeError("Matrix not supported: %s" % (matrix_type))

        # Compute dual matrix
        matr_elem_dual = self.getDualStiffnessMatrix()

        if assemble:
            if codret > 0:
                raise IntegrationError("MECANONLINE10_1")

            # Assemble matrix
            elemMatr = []
            elemMatr.append(matr_elem_rigi)
            elemMatr.append(matr_elem_dual)

            jacobian = AssemblyMatrixDisplacementReal(self.getPhysicalProblem())
            jacobian.assemble(elemMatr, self.getPhysicalProblem().getListOfLoads())

            return jacobian

        return codret, matr_elem_rigi, matr_elem_dual

    @profile
    def getContactTangentMatrix(self, phys_state, contact_manager):
        """Compute K(u) = d(Rcont(u) ) / du

        Arguments:
            phys_state (PhysicalState) : physical state
            contact_manager (ContactManager) : contact manager

        Returns:
           ElementaryMatrixDisplacementReal: Contact matrix.
        """
        if contact_manager:
            if contact_manager.isEnabled and contact_manager.isPaired:
                if contact_manager.defi.isParallel():
                    cMesh = contact_manager.defi.getConnectionModel().getMesh()
                    U_t = phys_state.U_t.transfertToConnectionMesh(cMesh)
                    deltaU = phys_state.deltaU.transfertToConnectionMesh(cMesh)
                else:
                    U_t = phys_state.U_t
                    deltaU = phys_state.deltaU
                matr_elem_cont = self.getContactMatrix(
                    contact_manager.getPairingCoordinates(),
                    U_t,
                    deltaU,
                    phys_state.time_prev,
                    phys_state.time_step,
                    contact_manager.data(),
                    contact_manager.coef_cont,
                    contact_manager.coef_frot,
                )

                return matr_elem_cont

        return None

    @profile
    def getExternalTangentMatrix(self, phys_state):
        """Compute external tangent matrix for nonlinear problem.
            K(u) = d(Rext(u)) / du

        Arguments:
            phys_state (PhysicalState) : physical state

        Returns:
            ElementaryMatrixDisplacementReal: external tangent matrix.
        """

        phys_pb = self.getPhysicalProblem()

        # Compute elementary matrix
        matr_elem_ext = None

        if phys_pb.isThermal():
            matr_elem_ext = self.getThermalExchangeMatrix(phys_state.time_curr)

            matr_elem_ext.addElementaryTerm(
                self.getThermalTangentNonLinearNeumannMatrix(
                    phys_state.U, phys_state.time_curr, phys_state.externVar
                ).getElementaryTerms()
            )
            matr_elem_ext.addElementaryTerm(
                self.getThermalTangentNonLinearVolumetricMatrix(
                    phys_state.U, phys_state.time_curr
                ).getElementaryTerms()
            )
            matr_elem_ext.build()
        elif phys_pb.isMechanical():
            matr_elem_ext = self.getMechanicalCouplingMatrix(
                phys_state.U_t, phys_state.deltaU, phys_state.time_prev, phys_state.time_step
            )

        return matr_elem_ext

    @profile
    def getTangentMatrix(
        self,
        phys_state,
        matrix_type="TANGENTE",
        contact_manager=None,
        assemble=True,
        tmp_internVar=None,
    ):
        """Compute tangent matrix for nonlinear problem.
            K(u) = d(Rint(u) - Rext(u)) / du

        Arguments:
            phys_state (PhysicalState) : physical state
            matrix_type (str): type of matrix used.
            contact_manager (ContactManager) : contact manager
            assemble (bool): assemble or not the matrix
            tmp_internVar = intenal variables values at the previous newton iteration

        Returns:
            AssemblyMatrixDisplacementReal: Tangent matrix.
        """

        phys_pb = self.getPhysicalProblem()

        # Compute elementary matrix
        codret, matr_elem_rigi, matr_elem_dual = self.getInternalTangentMatrix(
            phys_state, matrix_type, False, tmp_internVar
        )
        if codret > 0:
            raise IntegrationError("MECANONLINE10_1")

        matr_elem_cont = self.getContactTangentMatrix(phys_state, contact_manager)
        matr_elem_ext = self.getExternalTangentMatrix(phys_state)

        if assemble:
            elemMatr = []
            elemMatr.append(matr_elem_rigi)
            elemMatr.append(matr_elem_dual)
            elemMatr.append(matr_elem_cont)
            elemMatr.append(matr_elem_ext)

            # Assemble matrix
            if phys_pb.isMechanical():
                jacobian = AssemblyMatrixDisplacementReal(phys_pb)
            else:
                jacobian = AssemblyMatrixTemperatureReal(phys_pb)
            jacobian.assemble(elemMatr, phys_pb.getListOfLoads())

            return jacobian

        return matr_elem_rigi, matr_elem_dual, matr_elem_cont, matr_elem_ext
