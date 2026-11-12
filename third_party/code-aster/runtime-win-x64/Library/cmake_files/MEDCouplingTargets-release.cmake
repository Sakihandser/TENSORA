#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "interpkernel" for configuration "Release"
set_property(TARGET interpkernel APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(interpkernel PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/interpkernel.lib"
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELEASE "Ws2_32.lib;Userenv.lib"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/interpkernel.dll"
  )

list(APPEND _cmake_import_check_targets interpkernel )
list(APPEND _cmake_import_check_files_for_interpkernel "${_IMPORT_PREFIX}/lib/interpkernel.lib" "${_IMPORT_PREFIX}/bin/interpkernel.dll" )

# Import target "medcouplingcpp" for configuration "Release"
set_property(TARGET medcouplingcpp APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(medcouplingcpp PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/medcoupling.lib"
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELEASE "interpkernel"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/medcoupling.dll"
  )

list(APPEND _cmake_import_check_targets medcouplingcpp )
list(APPEND _cmake_import_check_files_for_medcouplingcpp "${_IMPORT_PREFIX}/lib/medcoupling.lib" "${_IMPORT_PREFIX}/bin/medcoupling.dll" )

# Import target "medcouplingremapper" for configuration "Release"
set_property(TARGET medcouplingremapper APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(medcouplingremapper PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/medcouplingremapper.lib"
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELEASE "medcouplingcpp"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/medcouplingremapper.dll"
  )

list(APPEND _cmake_import_check_targets medcouplingremapper )
list(APPEND _cmake_import_check_files_for_medcouplingremapper "${_IMPORT_PREFIX}/lib/medcouplingremapper.lib" "${_IMPORT_PREFIX}/bin/medcouplingremapper.dll" )

# Import target "medicoco" for configuration "Release"
set_property(TARGET medicoco APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(medicoco PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/medicoco.lib"
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELEASE "medcouplingcpp"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/medicoco.dll"
  )

list(APPEND _cmake_import_check_targets medicoco )
list(APPEND _cmake_import_check_files_for_medicoco "${_IMPORT_PREFIX}/lib/medicoco.lib" "${_IMPORT_PREFIX}/bin/medicoco.dll" )

# Import target "medloader" for configuration "Release"
set_property(TARGET medloader APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(medloader PROPERTIES
  IMPORTED_IMPLIB_RELEASE "${_IMPORT_PREFIX}/lib/medloader.lib"
  IMPORTED_LINK_INTERFACE_LIBRARIES_RELEASE "medcouplingcpp;medC;hdf5-shared"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/bin/medloader.dll"
  )

list(APPEND _cmake_import_check_targets medloader )
list(APPEND _cmake_import_check_files_for_medloader "${_IMPORT_PREFIX}/lib/medloader.lib" "${_IMPORT_PREFIX}/bin/medloader.dll" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
