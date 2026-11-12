#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::TFELMathCubicSpline" for configuration "Release"
set_property(TARGET tfel::TFELMathCubicSpline APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::TFELMathCubicSpline PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/TFELMathCubicSpline.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/TFELMathCubicSpline.dll"
  )

list(APPEND _cmake_import_check_targets tfel::TFELMathCubicSpline )
list(APPEND _cmake_import_check_files_for_tfel::TFELMathCubicSpline "${_IMPORT_PREFIX}/bin/TFELMathCubicSpline.lib" "${_IMPORT_PREFIX}/bin/TFELMathCubicSpline.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
