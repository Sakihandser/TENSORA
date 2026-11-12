#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::CalculiXInterface" for configuration "Release"
set_property(TARGET tfel::CalculiXInterface APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::CalculiXInterface PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/CalculiXInterface.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/CalculiXInterface.dll"
  )

list(APPEND _cmake_import_check_targets tfel::CalculiXInterface )
list(APPEND _cmake_import_check_files_for_tfel::CalculiXInterface "${_IMPORT_PREFIX}/bin/CalculiXInterface.lib" "${_IMPORT_PREFIX}/bin/CalculiXInterface.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
