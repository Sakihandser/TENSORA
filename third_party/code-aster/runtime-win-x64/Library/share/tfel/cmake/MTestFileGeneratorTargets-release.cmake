#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "tfel::MTestFileGenerator" for configuration "Release"
set_property(TARGET tfel::MTestFileGenerator APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(tfel::MTestFileGenerator PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/bin/MTestFileGenerator.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/MTestFileGenerator.dll"
  )

list(APPEND _cmake_import_check_targets tfel::MTestFileGenerator )
list(APPEND _cmake_import_check_files_for_tfel::MTestFileGenerator "${_IMPORT_PREFIX}/bin/MTestFileGenerator.lib" "${_IMPORT_PREFIX}/bin/MTestFileGenerator.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
