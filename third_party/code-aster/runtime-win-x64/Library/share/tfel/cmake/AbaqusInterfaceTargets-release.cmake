#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::AbaqusInterface" for configuration "Release"
set_property(TARGET tfel::AbaqusInterface APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::AbaqusInterface PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/AbaqusInterface.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/AbaqusInterface.dll"
  )

list(APPEND _cmake_import_check_targets tfel::AbaqusInterface )
list(APPEND _cmake_import_check_files_for_tfel::AbaqusInterface "${_IMPORT_PREFIX}/bin/AbaqusInterface.lib" "${_IMPORT_PREFIX}/bin/AbaqusInterface.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
