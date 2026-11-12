#----------------------------------------------------------------
# Generated CMake target import file.
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "mgis::MFrontGenericInterface-fortran" for configuration ""
set_property(TARGET mgis::MFrontGenericInterface-fortran APPEND PROPERTY IMPORTED_CONFIGURATIONS NOCONFIG)
set_target_properties(mgis::MFrontGenericInterface-fortran PROPERTIES
  IMPORTED_IMPLIB_NOCONFIG "${_IMPORT_PREFIX}/bin/MFrontGenericInterface-fortran.lib"
  IMPORTED_LOCATION_NOCONFIG "${_IMPORT_PREFIX}/bin/MFrontGenericInterface-fortran.dll"
  )

list(APPEND _cmake_import_check_targets mgis::MFrontGenericInterface-fortran )
list(APPEND _cmake_import_check_files_for_mgis::MFrontGenericInterface-fortran "${_IMPORT_PREFIX}/bin/MFrontGenericInterface-fortran.lib" "${_IMPORT_PREFIX}/bin/MFrontGenericInterface-fortran.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
