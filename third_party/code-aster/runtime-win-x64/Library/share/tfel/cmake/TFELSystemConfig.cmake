
####### Expanded from @PACKAGE_INIT@ by configure_package_config_file() #######
####### Any changes to this file will be overwritten by the next CMake run ####
####### The input file was TFELSystemConfig.cmake.in                            ########

get_filename_component(PACKAGE_PREFIX_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../" ABSOLUTE)

####################################################################################

include("${CMAKE_CURRENT_LIST_DIR}/tfel-modules-common.cmake")
find_package(TFELException REQUIRED
  HINTS "${CMAKE_CURRENT_LIST_DIR}" "${TFEL_MODULE_PATH}")

include("${CMAKE_CURRENT_LIST_DIR}/TFELSystemTargets.cmake")
