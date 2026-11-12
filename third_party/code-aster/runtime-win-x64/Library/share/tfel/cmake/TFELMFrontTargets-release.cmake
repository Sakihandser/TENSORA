#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::TFELMFront" for configuration "Release"
set_property(TARGET tfel::TFELMFront APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::TFELMFront PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/TFELMFront.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/TFELMFront.dll"
  )

list(APPEND _cmake_import_check_targets tfel::TFELMFront )
list(APPEND _cmake_import_check_files_for_tfel::TFELMFront "${_IMPORT_PREFIX}/bin/TFELMFront.lib" "${_IMPORT_PREFIX}/bin/TFELMFront.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
