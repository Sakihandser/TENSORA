#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "medC" for configuration "Release"
set_property(TARGET medC APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(medC PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/medC.lib"
  IMPORTED_LINK_DEPENDENT_LIBRARIES_RELEASE "hdf5-shared"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/medC.dll"
  )

list(APPEND _cmake_import_check_targets medC )
list(APPEND _cmake_import_check_files_for_medC "${_IMPORT_PREFIX}/lib/medC.lib" "${_IMPORT_PREFIX}/bin/medC.dll" )

# Import target "medfwrap" for configuration "Release"
set_property(TARGET medfwrap APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(medfwrap PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/medfwrap.lib"
  IMPORTED_LINK_DEPENDENT_LIBRARIES_RELEASE "medC"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/medfwrap.dll"
  )

list(APPEND _cmake_import_check_targets medfwrap )
list(APPEND _cmake_import_check_files_for_medfwrap "${_IMPORT_PREFIX}/lib/medfwrap.lib" "${_IMPORT_PREFIX}/bin/medfwrap.dll" )

# Import target "med" for configuration "Release"
set_property(TARGET med APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(med PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/med.lib"
  IMPORTED_LINK_DEPENDENT_LIBRARIES_RELEASE "medfwrap"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/med.dll"
  )

list(APPEND _cmake_import_check_targets med )
list(APPEND _cmake_import_check_files_for_med "${_IMPORT_PREFIX}/lib/med.lib" "${_IMPORT_PREFIX}/bin/med.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
