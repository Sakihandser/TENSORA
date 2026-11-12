#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::TFELNUMODIS" for configuration "Release"
set_property(TARGET tfel::TFELNUMODIS APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::TFELNUMODIS PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/TFELNUMODIS.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/TFELNUMODIS.dll"
  )

list(APPEND _cmake_import_check_targets tfel::TFELNUMODIS )
list(APPEND _cmake_import_check_files_for_tfel::TFELNUMODIS "${_IMPORT_PREFIX}/bin/TFELNUMODIS.lib" "${_IMPORT_PREFIX}/bin/TFELNUMODIS.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
