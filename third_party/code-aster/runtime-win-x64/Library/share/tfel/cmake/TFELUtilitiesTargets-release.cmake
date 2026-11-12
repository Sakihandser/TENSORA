#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::TFELUtilities" for configuration "Release"
set_property(TARGET tfel::TFELUtilities APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::TFELUtilities PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/TFELUtilities.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/TFELUtilities.dll"
  )

list(APPEND _cmake_import_check_targets tfel::TFELUtilities )
list(APPEND _cmake_import_check_files_for_tfel::TFELUtilities "${_IMPORT_PREFIX}/bin/TFELUtilities.lib" "${_IMPORT_PREFIX}/bin/TFELUtilities.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
