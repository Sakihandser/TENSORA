#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::TFELMath" for configuration "Release"
set_property(TARGET tfel::TFELMath APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::TFELMath PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/TFELMath.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/TFELMath.dll"
  )

list(APPEND _cmake_import_check_targets tfel::TFELMath )
list(APPEND _cmake_import_check_files_for_tfel::TFELMath "${_IMPORT_PREFIX}/bin/TFELMath.lib" "${_IMPORT_PREFIX}/bin/TFELMath.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
