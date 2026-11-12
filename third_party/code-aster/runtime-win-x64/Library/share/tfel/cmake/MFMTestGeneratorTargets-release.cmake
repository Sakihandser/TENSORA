#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::MFMTestGenerator" for configuration "Release"
set_property(TARGET tfel::MFMTestGenerator APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::MFMTestGenerator PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/MFMTestGenerator.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/MFMTestGenerator.dll"
  )

list(APPEND _cmake_import_check_targets tfel::MFMTestGenerator )
list(APPEND _cmake_import_check_files_for_tfel::MFMTestGenerator "${_IMPORT_PREFIX}/bin/MFMTestGenerator.lib" "${_IMPORT_PREFIX}/bin/MFMTestGenerator.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
