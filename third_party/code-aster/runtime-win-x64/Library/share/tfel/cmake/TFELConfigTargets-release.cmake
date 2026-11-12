#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::TFELConfig" for configuration "Release"
set_property(TARGET tfel::TFELConfig APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::TFELConfig PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/TFELConfig.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/TFELConfig.dll"
  )

list(APPEND _cmake_import_check_targets tfel::TFELConfig )
list(APPEND _cmake_import_check_files_for_tfel::TFELConfig "${_IMPORT_PREFIX}/bin/TFELConfig.lib" "${_IMPORT_PREFIX}/bin/TFELConfig.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
