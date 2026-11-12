#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::TFELGlossary" for configuration "Release"
set_property(TARGET tfel::TFELGlossary APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::TFELGlossary PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/TFELGlossary.lib"
  IMPORTED_LINK_DEPENDENT_LIBRARIES_RELEASE "tfel::TFELUtilities"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/TFELGlossary.dll"
  )

list(APPEND _cmake_import_check_targets tfel::TFELGlossary )
list(APPEND _cmake_import_check_files_for_tfel::TFELGlossary "${_IMPORT_PREFIX}/bin/TFELGlossary.lib" "${_IMPORT_PREFIX}/bin/TFELGlossary.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
