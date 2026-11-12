#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::TFELMathParser" for configuration "Release"
set_property(TARGET tfel::TFELMathParser APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::TFELMathParser PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/TFELMathParser.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/TFELMathParser.dll"
  )

list(APPEND _cmake_import_check_targets tfel::TFELMathParser )
list(APPEND _cmake_import_check_files_for_tfel::TFELMathParser "${_IMPORT_PREFIX}/bin/TFELMathParser.lib" "${_IMPORT_PREFIX}/bin/TFELMathParser.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
