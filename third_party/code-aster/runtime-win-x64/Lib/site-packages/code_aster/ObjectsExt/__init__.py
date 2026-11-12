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
This module provides extensions to pybind11 objects with pure
Python functions.
"""

# ensure DataStructure is extended first
from .datastructure_ext import DataStructure

# extend DataStructures using metaclasses
from .acousticload_ext import AcousticLoadComplex
from .assemblymatrix_ext import AssemblyMatrixDisplacementComplex, AssemblyMatrixDisplacementReal
from .constantfieldoncells_ext import ConstantFieldOnCellsReal
from .contact_ext import Contact
from .dirichletbc_ext import MechanicalDirichletBC, ThermalDirichletBC, AcousticDirichletBC
from .discretecomputation_ext import DiscreteComputation
from .dofnumbering_ext import DOFNumbering
from .generalizeddofnumbering_ext import GeneralizedDOFNumbering
from .dynamicmacroelement_ext import DynamicMacroElement
from .dynamicresults_ext import TransientGeneralizedResult
from .elementarycharacteristics_ext import ElementaryCharacteristics
from .elementarymatrix_ext import (
    ElementaryMatrixDisplacementComplex,
    ElementaryMatrixDisplacementReal,
    ElementaryMatrixPressureComplex,
    ElementaryMatrixTemperatureReal,
)
from .fieldoncells_ext import FieldOnCellsReal
from .fieldonnodes_ext import FieldOnNodesReal
from .simplefieldonnodes_ext import SimpleFieldOnNodesReal, SimpleFieldOnNodesComplex
from .simplefieldoncells_ext import SimpleFieldOnCellsReal
from .finiteelementdescriptor_ext import FiniteElementDescriptor
from .formula_ext import Formula
from .function2d_ext import Function2D
from .function_ext import Function
from .generalizedassemblymatrix_ext import (
    GeneralizedAssemblyMatrixComplex,
    GeneralizedAssemblyMatrixReal,
)
from .generalizedassemblyvector_ext import (
    GeneralizedAssemblyVectorComplex,
    GeneralizedAssemblyVectorReal,
)
from .generalizedload_ext import GeneralizedLoad
from .generalizedmodel_ext import GeneralizedModel
from .equationnumbering_ext import EquationNumbering
from .linearsolver_ext import (
    GcpcSolver,
    LdltSolver,
    MultFrontSolver,
    MumpsSolver,
    PetscSolver,
    LinearSolver,
)
from .listoffloats_ext import ListOfFloats
from .listofintegers_ext import ListOfIntegers
from .listofloads_ext import ListOfLoads
from .material_ext import Material
from .materialfield_ext import MaterialField
from .mesh_ext import Mesh
from .meshcoordinatesfield_ext import MeshCoordinatesField
from .mgis_behaviour_ext import MGISBehaviour
from .model_ext import Model
from .moderesult_ext import ModeResult
from .paralleldofnumbering_ext import ParallelDOFNumbering
from .parallelequationnumbering_ext import ParallelEquationNumbering
from .parallelfiniteelementdescriptor_ext import ParallelFiniteElementDescriptor
from .parallelmechanicalload_ext import ParallelMechanicalLoadReal, ParallelMechanicalLoadFunction
from .parallelmesh_ext import ConnectionMesh, ParallelMesh
from .parallelthermalload_ext import ParallelThermalLoadReal, ParallelThermalLoadFunction
from .prestressingcable_ext import PrestressingCable
from .physicalproblem_ext import PhysicalProblem
from .result_ext import Result
from .table_ext import Table
from .timeslist_ext import TimesList
from .thermalload_ext import ThermalLoadReal, ThermalLoadFunction
from .thermalresult_ext import ThermalResult
from .dryingresult_ext import DryingResult
from .fullresult_ext import FullResult
from .generalizedresults_ext import TransientGeneralizedResult, HarmoGeneralizedResult
from .xfemcrack_ext import XfemCrack
