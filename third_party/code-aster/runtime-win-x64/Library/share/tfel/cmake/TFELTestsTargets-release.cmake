#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::TFELTests" for configuration "Release"
set_property(TARGET tfel::TFELTests APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::TFELTests PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/TFELTests.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/TFELTests.dll"
  )

list(APPEND _cmake_import_check_targets tfel::TFELTests )
list(APPEND _cmake_import_check_files_for_tfel::TFELTests "${_IMPORT_PREFIX}/bin/TFELTests.lib" "${_IMPORT_PREFIX}/bin/TFELTests.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
