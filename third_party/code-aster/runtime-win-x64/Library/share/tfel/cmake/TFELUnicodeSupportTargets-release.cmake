#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::TFELUnicodeSupport" for configuration "Release"
set_property(TARGET tfel::TFELUnicodeSupport APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::TFELUnicodeSupport PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/TFELUnicodeSupport.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/TFELUnicodeSupport.dll"
  )

list(APPEND _cmake_import_check_targets tfel::TFELUnicodeSupport )
list(APPEND _cmake_import_check_files_for_tfel::TFELUnicodeSupport "${_IMPORT_PREFIX}/bin/TFELUnicodeSupport.lib" "${_IMPORT_PREFIX}/bin/TFELUnicodeSupport.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
