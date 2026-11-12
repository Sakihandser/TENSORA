#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::LSDYNAInterface" for configuration "Release"
set_property(TARGET tfel::LSDYNAInterface APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::LSDYNAInterface PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/LSDYNAInterface.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/LSDYNAInterface.dll"
  )

list(APPEND _cmake_import_check_targets tfel::LSDYNAInterface )
list(APPEND _cmake_import_check_files_for_tfel::LSDYNAInterface "${_IMPORT_PREFIX}/bin/LSDYNAInterface.lib" "${_IMPORT_PREFIX}/bin/LSDYNAInterface.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
