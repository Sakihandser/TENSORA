#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::TFELException" for configuration "Release"
set_property(TARGET tfel::TFELException APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::TFELException PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/TFELException.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/TFELException.dll"
  )

list(APPEND _cmake_import_check_targets tfel::TFELException )
list(APPEND _cmake_import_check_files_for_tfel::TFELException "${_IMPORT_PREFIX}/bin/TFELException.lib" "${_IMPORT_PREFIX}/bin/TFELException.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
