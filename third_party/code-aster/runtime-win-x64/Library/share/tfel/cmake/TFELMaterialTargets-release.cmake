#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::TFELMaterial" for configuration "Release"
set_property(TARGET tfel::TFELMaterial APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::TFELMaterial PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/TFELMaterial.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/TFELMaterial.dll"
  )

list(APPEND _cmake_import_check_targets tfel::TFELMaterial )
list(APPEND _cmake_import_check_files_for_tfel::TFELMaterial "${_IMPORT_PREFIX}/bin/TFELMaterial.lib" "${_IMPORT_PREFIX}/bin/TFELMaterial.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
