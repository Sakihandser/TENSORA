#pragma once
#include "OpenRadiossJH2.h"
#include <string>
#include <stdexcept>
#include <cstring>
namespace fem { namespace upstream_eos {
inline constexpr const char* Commit="b4f71a7748770dfa6ce4d678754c463c09262fb7";
using Evaluate=int(__cdecl*)(int,const double*,double,double,double*);
struct Library{
 HMODULE module=nullptr;Evaluate evaluate=nullptr,energy=nullptr;
 Library(){
  wchar_t file[32768];const DWORD n=GetModuleFileNameW(nullptr,file,32768);
  if(n==0||n>=32768)throw std::runtime_error("Cannot locate the upstream gas EOS runtime directory.");
  std::wstring p(file,n);p.resize(p.find_last_of(L"\\/")+1);p+=L"singularity_eos.dll";
  module=LoadLibraryExW(p.c_str(),nullptr,LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR|LOAD_LIBRARY_SEARCH_SYSTEM32);
  if(!module)throw std::runtime_error("Singularity-EOS runtime is missing; deploy singularity_eos.dll next to the native core.");
  const auto abi=reinterpret_cast<int(__cdecl*)()>(GetProcAddress(module,"tensora_eos_abi"));
  const auto source=reinterpret_cast<const char*(__cdecl*)()>(GetProcAddress(module,"tensora_eos_source"));
  evaluate=reinterpret_cast<Evaluate>(GetProcAddress(module,"tensora_eos_evaluate"));energy=reinterpret_cast<Evaluate>(GetProcAddress(module,"tensora_eos_energy"));
  if(!abi||abi()!=1||!source||std::strcmp(source(),Commit)!=0||!evaluate||!energy){FreeLibrary(module);throw std::runtime_error("Singularity-EOS runtime ABI/source version mismatch.");}
 }
};
inline const Library& Runtime(){static const Library library;return library;}
}}
