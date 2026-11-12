#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "SCOTCH::scotcherrexit" for configuration "Release"
set_property(TARGET SCOTCH::scotcherrexit APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(SCOTCH::scotcherrexit PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "C"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/scotcherrexit.lib"
  )

list(APPEND _cmake_import_check_targets SCOTCH::scotcherrexit )
list(APPEND _cmake_import_check_files_for_SCOTCH::scotcherrexit "${_IMPORT_PREFIX}/lib/scotcherrexit.lib" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
