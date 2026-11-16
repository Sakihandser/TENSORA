cmake_minimum_required(VERSION 3.20)
project(mfem_fsi CXX)

# MFEM is built from the unmodified mfem-4.10 source (see scripts/build-mfem-fsi.ps1).
find_package(mfem REQUIRED NAMES MFEM)
add_executable(mfem_fsi mfem_fsi.cpp)
target_link_libraries(mfem_fsi PRIVATE mfem)
target_include_directories(mfem_fsi PRIVATE ${MFEM_INCLUDE_DIRS})
