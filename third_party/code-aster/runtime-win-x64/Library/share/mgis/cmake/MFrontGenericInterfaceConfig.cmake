
####### Expanded from @PACKAGE_INIT@ by configure_package_config_file() #######
####### Any changes to this file will be overwritten by the next CMake run ####
####### The input file was MFrontGenericInterfaceConfig.cmake.in                            ########

get_filename_component(PACKAGE_PREFIX_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../" ABSOLUTE)

####################################################################################

set(MGIS_FUNCTION_SUPPORT ON)
set(MGIS_HAVE_TFEL ON)

if(MGIS_HAVE_TFEL)

   if(TFEL_DIR)
     set(TFEL_MODULE_PATH ${TFEL_DIR})
   else(TFEL_DIR)
     if(TFELHOME)
       set(TFEL_MODULE_PATH ${TFELHOME})
     else(TFELHOME)
       if(DEFINED ENV{${VERSIONED_TFEL_HOME}})
          set(TFEL_MODULE_PATH "$ENV{${VERSIONED_TFEL_HOME}}")
       else(DEFINED ENV{${VERSIONED_TFEL_HOME}})
         if(DEFINED ENV{TFELHOME})
            set(TFEL_MODULE_PATH "$ENV{TFELHOME}")      
         endif(DEFINED ENV{TFELHOME})
       endif(DEFINED ENV{${VERSIONED_TFEL_HOME}})
     endif(TFELHOME)
   endif(TFEL_DIR)

  find_package(TFELMath REQUIRED
    HINTS "${CMAKE_CURRENT_LIST_DIR}" "${TFEL_MODULE_PATH}")
  find_package(TFELMFrontDatabase REQUIRED
    HINTS "${CMAKE_CURRENT_LIST_DIR}" "${TFEL_MODULE_PATH}")

endif(MGIS_HAVE_TFEL)

if(UNIX)
  set(Threads_FOUND TRUE)
  if(Threads_FOUND)
    find_package(Threads REQUIRED)
  endif(Threads_FOUND)
endif(UNIX)

set(MGIS_REQUIRED_ADDITIONAL_PACKAGES "")
foreach(_package ${MGIS_REQUIRED_ADDITIONAL_PACKAGES})
  find_package(${_package} REQUIRED)
endforeach()

include("${CMAKE_CURRENT_LIST_DIR}/MFrontGenericInterfaceTargets.cmake")
