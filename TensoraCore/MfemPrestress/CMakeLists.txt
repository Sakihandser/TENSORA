cmake_minimum_required(VERSION 3.20)
project(mfem_prestress CXX)

# MFEM is built from the unmodified mfem-4.10 source (see scripts/build-mfem-prestress.ps1).
find_package(mfem REQUIRED NAMES MFEM)
add_executable(mfem_prestress mfem_prestress.cpp)
target_link_libraries(mfem_prestress PRIVATE mfem)
target_include_directories(mfem_prestress PRIVATE ${MFEM_INCLUDE_DIRS})
