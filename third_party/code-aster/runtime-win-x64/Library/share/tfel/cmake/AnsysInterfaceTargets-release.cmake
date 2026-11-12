#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::AnsysInterface" for configuration "Release"
set_property(TARGET tfel::AnsysInterface APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::AnsysInterface PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/AnsysInterface.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/AnsysInterface.dll"
  )

list(APPEND _cmake_import_check_targets tfel::AnsysInterface )
list(APPEND _cmake_import_check_files_for_tfel::AnsysInterface "${_IMPORT_PREFIX}/bin/AnsysInterface.lib" "${_IMPORT_PREFIX}/bin/AnsysInterface.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
