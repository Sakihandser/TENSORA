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
:py:class:`DataStructure` --- Base of all objects
*************************************************
"""

import libaster
from libaster import DataStructure

from ..CodeCommands import COPIER
from ..Objects.Serialization import InternalStateBuilder
from ..Utilities import import_object, injector


@injector(DataStructure)
class ExtendedDataStructure:
    """This class defines the base class of the DataStructures."""

    cata_sdj = None
    internalStateBuilder = InternalStateBuilder

    orig_getName = DataStructure.getName

    def getName(self):
        """
        Overload standard `getName()` function to eliminate whitespace at both
        ends of the string.

        .. note:: The C++ constructor automaticaly adds a whitespace when it
            creates a new object from the result name of this overloaded
            function `getName()`.
        """
        return self.orig_getName().strip()

    def is_typco(self):
        """Tell if it is an auxiliary result."""
        return False

    def copy(self):
        """Returns a copy of the object."""
        new = COPIER(CONCEPT=self)
        return new

    def __getinitargs__(self):
        """Returns the argument required to reinitialize a derivated
        DataStructure object during unpickling.

        .. note:: This implementation does not satisfy any constructor of the
            base DataStructure. But most of the derivated class should have
            a constructor accepting the Jeveux name.
        """
        return (self.getName(),)

    def __getstate__(self):
        """Return internal state.

        Derivated *DataStructure* types should defined a dedicated *InternalStateBuilder*
        class to serialize its specific content.
        """
        return self.internalStateBuilder().save(self)

    def __setstate__(self, state):
        """Restore internal state.

        Arguments:
            state (*InternalStateBuilder*): Internal state.
        """
        assert isinstance(state, InternalStateBuilder), f"unexpected type: {state}"
        state.restore(self)

    def addDependencies(self, *others):
        """Add some other *DataStructure* as dependencies.

        Arguments:
            others (list[~.DataStructure]): Dependencies.
        """
        for obj in others:
            self.addDependency(obj)

    @property
    def sdj(self):
        """Return the DataStructure catalog."""
        if self._ptr_sdj is None:
            cata_sdj = getattr(self, "cata_sdj", None)
            if not cata_sdj:
                cata_sdj = DICT_SDJ.get(self.__class__.__name__)
            assert cata_sdj, "The attribute 'cata_sdj' must be defined in the class {}".format(
                self.__class__.__name__
            )
            ptr_class_sdj = import_object("code_aster." + cata_sdj)
            self._ptr_sdj = ptr_class_sdj(nomj=self.getName())
        return self._ptr_sdj

    def use_count(self):
        """Return the number of reference to the DataStructure.

        Warning: Use only for debugging! Supported datastructures in
        ``PythonBindings/DebugInterface.cxx``.
        """
        return libaster.use_count(self)

    def __eq__(self, other):
        """Tell if *other* is a *DataStructure* and points to the same object.

        Returns:
            bool: *True* if the objects are the same.
        """
        return isinstance(other, DataStructure) and self.id() == other.id()


# This dictionnary avoids to add the DataStructure "_ext.py" file just
# to define the SD definition.
DICT_SDJ = {
    "AcousticModeResult": "SD.sd_dyna_phys.sd_dyna_phys",
    "BehaviourDefinition": "SD.sd_compor.sd_compor",
    "BucklingModeResult": "SD.sd_dyna_phys.sd_dyna_phys",
    "Contact": "SD.sd_contact.sd_contact",
    "ContactNew": "SD.sd_char_cont.sd_char_cont",
    "Crack": "SD.sd_fond_fissure.sd_fond_fissure",
    "CyclicSymmetryMode": "SD.sd_mode_cycl.sd_mode_cycl",
    "DataField": "SD.sd_champ.sd_champ",
    "ElementaryVector": "SD.sd_vect_elem.sd_vect_elem",
    "ElementaryVectorDisplacementReal": "SD.sd_vect_elem.sd_vect_elem",
    "ElementaryVectorPressureComplex": "SD.sd_vect_elem.sd_vect_elem",
    "ElementaryVectorTemperatureReal": "SD.sd_vect_elem.sd_vect_elem",
    "EquationNumbering": "SD.sd_nume_equa.sd_nume_equa",
    "FiberGeometry": "SD.sd_gfibre.sd_gfibre",
    "FluidStructureInteraction": "SD.sd_type_flui_stru.sd_type_flui_stru",
    "FluidStructureModalBasis": "SD.sd_melasflu.sd_melasflu",
    "FrictionNew": "SD.sd_char_frot.sd_char_frot",
    "FullHarmonicAcousticResult": "SD.sd_dyna_phys.sd_dyna_phys",
    "FullHarmonicResult": "SD.sd_dyna_gene.sd_dyna_gene",
    "GeneralizedDOFNumbering": "SD.sd_nume_ddl_gene.sd_nume_ddl_gene",
    "GeneralizedModeResult": "SD.sd_dyna_gene.sd_dyna_gene",
    "GeneralizedResultComplex": "SD.sd_dyna_gene.sd_dyna_gene",
    "GeneralizedResultReal": "SD.sd_dyna_gene.sd_dyna_gene",
    "GenericModalBasis": "SD.sd_dyna_phys.sd_dyna_phys",
    "Grid": "SD.sd_grille.sd_grille",
    "HarmoGeneralizedResult": "SD.sd_dyna_gene.sd_dyna_gene",
    "InterspectralMatrix": "SD.sd_interspectre.sd_interspectre",
    "MechanicalLoadReal": "SD.sd_char_meca.sd_char_meca",
    "MechanicalLoadFunction": "SD.sd_char_meca.sd_char_meca",
    "MechanicalLoadComplex": "SD.sd_char_meca.sd_char_meca",
    "MeshesMapping": "SD.sd_corresp_2_mailla.sd_corresp_2_mailla",
    "ModeResultComplex": "SD.sd_dyna_phys.sd_dyna_phys",
    "ParallelContactNew": "SD.sd_char_cont.sd_char_cont",
    "ParallelFrictionNew": "SD.sd_char_frot.sd_char_frot",
    "RitzBasis": "SD.sd_dyna_phys.sd_dyna_phys",
    "Skeleton": "SD.sd_squelette.sd_squelette",
    "StaticMacroElement": "SD.sd_macr_elem_stat.sd_macr_elem_stat",
    "StructureInterface": "SD.sd_interf_dyna_clas.sd_interf_dyna_clas",
    "TimesList": "SD.sd_list_inst.sd_list_inst",
    "TurbulentSpectrum": "SD.sd_spectre.sd_spectre",
}
