#pragma once
#include <stdexcept>
#include <string>
#define NOMINMAX
#include <windows.h>
#define CL_TARGET_OPENCL_VERSION 120
#include "vendor/opencl/CL/cl.h"

namespace fem::opencl {
inline void Check(cl_int code, const char* operation) {
    if (code != CL_SUCCESS)
        throw std::runtime_error(std::string(operation) + " (OpenCL " + std::to_string(code) + ")");
}

// Load only the system ICD loader, never a DLL found in the working directory.
struct OpenClApi {
    HMODULE library = nullptr;
#define FEM_CL_FUNCTION(name) decltype(&::name) name = nullptr;
    FEM_CL_FUNCTION(clGetPlatformIDs)
    FEM_CL_FUNCTION(clGetDeviceIDs)
    FEM_CL_FUNCTION(clGetDeviceInfo)
    FEM_CL_FUNCTION(clCreateContext)
    FEM_CL_FUNCTION(clCreateCommandQueue)
    FEM_CL_FUNCTION(clCreateProgramWithSource)
    FEM_CL_FUNCTION(clBuildProgram)
    FEM_CL_FUNCTION(clGetProgramBuildInfo)
    FEM_CL_FUNCTION(clCreateKernel)
    FEM_CL_FUNCTION(clCreateBuffer)
    FEM_CL_FUNCTION(clSetKernelArg)
    FEM_CL_FUNCTION(clEnqueueWriteBuffer)
    FEM_CL_FUNCTION(clEnqueueReadBuffer)
    FEM_CL_FUNCTION(clEnqueueNDRangeKernel)
    FEM_CL_FUNCTION(clReleaseMemObject)
    FEM_CL_FUNCTION(clReleaseKernel)
    FEM_CL_FUNCTION(clReleaseProgram)
    FEM_CL_FUNCTION(clReleaseCommandQueue)
    FEM_CL_FUNCTION(clReleaseContext)
#undef FEM_CL_FUNCTION
    OpenClApi() {
        library = LoadLibraryExW(L"OpenCL.dll", nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32);
        if (!library) throw std::runtime_error("system OpenCL runtime unavailable");
        try {
#define FEM_CL_LOAD(name) name = reinterpret_cast<decltype(name)>(GetProcAddress(library, #name)); if (!name) throw std::runtime_error("missing " #name);
            FEM_CL_LOAD(clGetPlatformIDs)
            FEM_CL_LOAD(clGetDeviceIDs)
            FEM_CL_LOAD(clGetDeviceInfo)
            FEM_CL_LOAD(clCreateContext)
            FEM_CL_LOAD(clCreateCommandQueue)
            FEM_CL_LOAD(clCreateProgramWithSource)
            FEM_CL_LOAD(clBuildProgram)
            FEM_CL_LOAD(clGetProgramBuildInfo)
            FEM_CL_LOAD(clCreateKernel)
            FEM_CL_LOAD(clCreateBuffer)
            FEM_CL_LOAD(clSetKernelArg)
            FEM_CL_LOAD(clEnqueueWriteBuffer)
            FEM_CL_LOAD(clEnqueueReadBuffer)
            FEM_CL_LOAD(clEnqueueNDRangeKernel)
            FEM_CL_LOAD(clReleaseMemObject)
            FEM_CL_LOAD(clReleaseKernel)
            FEM_CL_LOAD(clReleaseProgram)
            FEM_CL_LOAD(clReleaseCommandQueue)
            FEM_CL_LOAD(clReleaseContext)
#undef FEM_CL_LOAD
        } catch (...) { FreeLibrary(library); library = nullptr; throw; }
    }
    ~OpenClApi() { if (library) FreeLibrary(library); }
};

} // namespace fem::opencl
