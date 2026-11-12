#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::CyranoInterface" for configuration "Release"
set_property(TARGET tfel::CyranoInterface APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::CyranoInterface PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/CyranoInterface.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/CyranoInterface.dll"
  )

list(APPEND _cmake_import_check_targets tfel::CyranoInterface )
list(APPEND _cmake_import_check_files_for_tfel::CyranoInterface "${_IMPORT_PREFIX}/bin/CyranoInterface.lib" "${_IMPORT_PREFIX}/bin/CyranoInterface.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
