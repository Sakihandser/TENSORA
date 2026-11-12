#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::DianaFEAInterface" for configuration "Release"
set_property(TARGET tfel::DianaFEAInterface APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::DianaFEAInterface PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/DianaFEAInterface.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/DianaFEAInterface.dll"
  )

list(APPEND _cmake_import_check_targets tfel::DianaFEAInterface )
list(APPEND _cmake_import_check_files_for_tfel::DianaFEAInterface "${_IMPORT_PREFIX}/bin/DianaFEAInterface.lib" "${_IMPORT_PREFIX}/bin/DianaFEAInterface.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
