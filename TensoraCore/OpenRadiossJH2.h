#pragma once
// Runtime binding only. No JH2 return mapping or damage law is implemented here.
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#include <string>
#include <stdexcept>
#include <cstring>

namespace fem { namespace openradioss {
inline constexpr const char* Commit="bad6688602d770e019b75773d2d5a48b4f9bd918";
using StepFunction=void(__cdecl*)(const double*,const double*,const double*,double,double,double,double*,double*,double*);
struct Library {
  HMODULE module=nullptr;
  StepFunction step=nullptr;
  Library(){
    wchar_t executable[32768];const DWORD n=GetModuleFileNameW(nullptr,executable,32768);
    if(n==0 || n>=32768)throw std::runtime_error("Cannot locate the OpenRadioss JH2 runtime directory.");
    std::wstring path(executable,n);path.resize(path.find_last_of(L"\\/")+1);path+=L"openradioss_jh2.dll";
    module=LoadLibraryExW(path.c_str(),nullptr,LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_SYSTEM32);
    if(!module)throw std::runtime_error("OpenRadioss JH2 runtime is missing or cannot be loaded; rebuild/deploy openradioss_jh2.dll next to the native core.");
    const auto abi=reinterpret_cast<int(__cdecl*)()>(GetProcAddress(module,"tensora_jh2_abi"));
    const auto source=reinterpret_cast<const char*(__cdecl*)()>(GetProcAddress(module,"tensora_jh2_source"));
    step=reinterpret_cast<StepFunction>(GetProcAddress(module,"tensora_jh2_step"));
    if(!abi || abi()!=1 || !source || std::strcmp(source(),Commit)!=0 || !step){
      FreeLibrary(module);module=nullptr;
      throw std::runtime_error("OpenRadioss JH2 runtime ABI/source version does not match this native core.");
    }
  }
  // Keep the module loaded for the process lifetime, including OpenMP workers.
};
inline const Library& Runtime(){static const Library library;return library;}
}}
