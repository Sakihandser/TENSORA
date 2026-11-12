#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::TFELMTest" for configuration "Release"
set_property(TARGET tfel::TFELMTest APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::TFELMTest PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/TFELMTest.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/TFELMTest.dll"
  )

list(APPEND _cmake_import_check_targets tfel::TFELMTest )
list(APPEND _cmake_import_check_files_for_tfel::TFELMTest "${_IMPORT_PREFIX}/bin/TFELMTest.lib" "${_IMPORT_PREFIX}/bin/TFELMTest.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
