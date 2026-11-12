#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "SCOTCH::scotchmetisv3" for configuration "Release"
set_property(TARGET SCOTCH::scotchmetisv3 APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(SCOTCH::scotchmetisv3 PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "C"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/scotchmetisv3.lib"
  )

list(APPEND _cmake_import_check_targets SCOTCH::scotchmetisv3 )
list(APPEND _cmake_import_check_files_for_SCOTCH::scotchmetisv3 "${_IMPORT_PREFIX}/lib/scotchmetisv3.lib" )

# Import target "SCOTCH::scotchmetisv5" for configuration "Release"
set_property(TARGET SCOTCH::scotchmetisv5 APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(SCOTCH::scotchmetisv5 PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "C"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/scotchmetisv5.lib"
  )

list(APPEND _cmake_import_check_targets SCOTCH::scotchmetisv5 )
list(APPEND _cmake_import_check_files_for_SCOTCH::scotchmetisv5 "${_IMPORT_PREFIX}/lib/scotchmetisv5.lib" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
