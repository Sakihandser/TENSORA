#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "SCOTCH::esmumps" for configuration "Release"
set_property(TARGET SCOTCH::esmumps APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(SCOTCH::esmumps PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "C"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/esmumps.lib"
  )

list(APPEND _cmake_import_check_targets SCOTCH::esmumps )
list(APPEND _cmake_import_check_files_for_SCOTCH::esmumps "${_IMPORT_PREFIX}/lib/esmumps.lib" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
