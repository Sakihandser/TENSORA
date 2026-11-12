#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::TFELMathKriging" for configuration "Release"
set_property(TARGET tfel::TFELMathKriging APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::TFELMathKriging PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/TFELMathKriging.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/TFELMathKriging.dll"
  )

list(APPEND _cmake_import_check_targets tfel::TFELMathKriging )
list(APPEND _cmake_import_check_files_for_tfel::TFELMathKriging "${_IMPORT_PREFIX}/bin/TFELMathKriging.lib" "${_IMPORT_PREFIX}/bin/TFELMathKriging.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
