#----------------------------------------------------------------
# Generated CMake target import file.
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "mgis::MFrontGenericInterface-c" for configuration ""
set_property(TARGET mgis::MFrontGenericInterface-c APPEND PROPERTY IMPORTED_CONFIGURATIONS NOCONFIG)
set_target_properties(mgis::MFrontGenericInterface-c PROPERTIES
  IMPORTED_IMPLIB_NOCONFIG "${_IMPORT_PREFIX}/bin/MFrontGenericInterface-c.lib"
  IMPORTED_LINK_DEPENDENT_LIBRARIES_NOCONFIG "mgis::MFrontGenericInterface"
  IMPORTED_LOCATION_NOCONFIG "${_IMPORT_PREFIX}/bin/MFrontGenericInterface-c.dll"
  )

list(APPEND _cmake_import_check_targets mgis::MFrontGenericInterface-c )
list(APPEND _cmake_import_check_files_for_mgis::MFrontGenericInterface-c "${_IMPORT_PREFIX}/bin/MFrontGenericInterface-c.lib" "${_IMPORT_PREFIX}/bin/MFrontGenericInterface-c.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
