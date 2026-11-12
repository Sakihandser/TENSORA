#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::TFELSystem" for configuration "Release"
set_property(TARGET tfel::TFELSystem APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::TFELSystem PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/TFELSystem.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/TFELSystem.dll"
  )

list(APPEND _cmake_import_check_targets tfel::TFELSystem )
list(APPEND _cmake_import_check_files_for_tfel::TFELSystem "${_IMPORT_PREFIX}/bin/TFELSystem.lib" "${_IMPORT_PREFIX}/bin/TFELSystem.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
