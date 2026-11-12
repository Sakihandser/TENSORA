#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::MFrontProfiling" for configuration "Release"
set_property(TARGET tfel::MFrontProfiling APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::MFrontProfiling PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/MFrontProfiling.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/MFrontProfiling.dll"
  )

list(APPEND _cmake_import_check_targets tfel::MFrontProfiling )
list(APPEND _cmake_import_check_files_for_tfel::MFrontProfiling "${_IMPORT_PREFIX}/bin/MFrontProfiling.lib" "${_IMPORT_PREFIX}/bin/MFrontProfiling.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
