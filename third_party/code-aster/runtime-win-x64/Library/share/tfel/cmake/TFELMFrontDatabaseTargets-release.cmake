#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::TFELMFrontDatabase" for configuration "Release"
set_property(TARGET tfel::TFELMFrontDatabase APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::TFELMFrontDatabase PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/TFELMFrontDatabase.lib"
  IMPORTED_LINK_DEPENDENT_LIBRARIES_RELEASE "tfel::TFELSystem;tfel::TFELUtilities"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/TFELMFrontDatabase.dll"
  )

list(APPEND _cmake_import_check_targets tfel::TFELMFrontDatabase )
list(APPEND _cmake_import_check_files_for_tfel::TFELMFrontDatabase "${_IMPORT_PREFIX}/bin/TFELMFrontDatabase.lib" "${_IMPORT_PREFIX}/bin/TFELMFrontDatabase.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
