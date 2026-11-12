
####### Expanded from @PACKAGE_INIT@ by configure_package_config_file() #######
####### Any changes to this file will be overwritten by the next CMake run ####
####### The input file was TFELMFrontConfig.cmake.in                            ########

get_filename_component(PACKAGE_PREFIX_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../" ABSOLUTE)

####################################################################################

include("${CMAKE_CURRENT_LIST_DIR}/tfel-modules-common.cmake")

find_package(TFELConfig REQUIRED
  HINTS "${CMAKE_CURRENT_LIST_DIR}" "${TFEL_MODULE_PATH}")
find_package(TFELException REQUIRED
  HINTS "${CMAKE_CURRENT_LIST_DIR}" "${TFEL_MODULE_PATH}")
find_package(TFELUnicodeSupport REQUIRED
  HINTS "${CMAKE_CURRENT_LIST_DIR}" "${TFEL_MODULE_PATH}")
find_package(TFELGlossary REQUIRED
  HINTS "${CMAKE_CURRENT_LIST_DIR}" "${TFEL_MODULE_PATH}")
find_package(TFELUtilities REQUIRED
  HINTS "${CMAKE_CURRENT_LIST_DIR}" "${TFEL_MODULE_PATH}")
find_package(TFELSystem REQUIRED
  HINTS "${CMAKE_CURRENT_LIST_DIR}" "${TFEL_MODULE_PATH}")
find_package(TFELMath REQUIRED
  HINTS "${CMAKE_CURRENT_LIST_DIR}" "${TFEL_MODULE_PATH}")
find_package(TFELMathKriging REQUIRED
  HINTS "${CMAKE_CURRENT_LIST_DIR}" "${TFEL_MODULE_PATH}")
find_package(TFELMathParser REQUIRED
  HINTS "${CMAKE_CURRENT_LIST_DIR}" "${TFEL_MODULE_PATH}")
find_package(TFELMathCubicSpline REQUIRED
  HINTS "${CMAKE_CURRENT_LIST_DIR}" "${TFEL_MODULE_PATH}")
find_package(TFELNUMODIS REQUIRED
  HINTS "${CMAKE_CURRENT_LIST_DIR}" "${TFEL_MODULE_PATH}")
find_package(TFELMaterial REQUIRED
  HINTS "${CMAKE_CURRENT_LIST_DIR}" "${TFEL_MODULE_PATH}")
find_package(MFrontLogStream REQUIRED
  HINTS "${CMAKE_CURRENT_LIST_DIR}" "${TFEL_MODULE_PATH}")

include("${CMAKE_CURRENT_LIST_DIR}/TFELMFrontTargets.cmake")
