#include "ParallelSparseSolve.h"

#if defined(_WIN64)
#define NOMINMAX
#include <windows.h>
#include <array>
#include <filesystem>

namespace {
class MklLibrary {
public:
    MklLibrary() {
        std::array<wchar_t, 32768> executablePath{};
        const DWORD pathLength = GetModuleFileNameW(nullptr, executablePath.data(), static_cast<DWORD>(executablePath.size()));
        if (!pathLength || pathLength >= executablePath.size()) return;
        const auto releaseDirectory = std::filesystem::path(executablePath.data()).parent_path();
        const auto directory = releaseDirectory.parent_path().parent_path().parent_path() /
            L"third_party/code-aster/runtime-win-x64/Library/bin";
        std::error_code error;
        for (const auto file : {L"mkl_rt.3.dll", L"mkl_core.3.dll", L"mkl_intel_thread.3.dll", L"mkl_def.3.dll", L"libiomp5md.dll"}) {
            if (!std::filesystem::is_regular_file(directory / file, error)) return;
        }

        // MKL loads its threading and CPU-specific libraries on first use.
        // Limit the changed search path to this call in the solver process.
        const DWORD length = GetDllDirectoryW(static_cast<DWORD>(previousDirectory.size()), previousDirectory.data());
        if (length >= previousDirectory.size() || !SetDllDirectoryW(directory.c_str())) return;
        directoryChanged = true;
        module = LoadLibraryExW((directory / L"mkl_rt.3.dll").c_str(), nullptr,
                               LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | LOAD_LIBRARY_SEARCH_SYSTEM32);
    }

    ~MklLibrary() {
        if (module) FreeLibrary(module);
        if (directoryChanged) SetDllDirectoryW(previousDirectory[0] ? previousDirectory.data() : nullptr);
    }

    MklLibrary(const MklLibrary&) = delete;
    MklLibrary& operator=(const MklLibrary&) = delete;

    template <typename Function> Function find(const char* name) const {
        return module ? reinterpret_cast<Function>(GetProcAddress(module, name)) : nullptr;
    }

private:
    HMODULE module = nullptr;
    bool directoryChanged = false;
    std::array<wchar_t, 32768> previousDirectory{};
};
} // namespace
#endif

namespace fem {
bool TryParallelSparseSolve(const Eigen::SparseMatrix<double>& stiffness, const Eigen::VectorXd& force,
                           int threads, Eigen::VectorXd& displacement) {
#if defined(_WIN64)
    using SetLayer = int (*)(int);
    using SetThreads = int (*)(int);
    using Init = void (*)(void*, const int*, int*);
    using Solve = void (*)(void*, const int*, const int*, const int*, const int*, const int*, const void*,
                          const int*, const int*, int*, const int*, int*, const int*, void*, void*, int*);
    const MklLibrary mkl;
    // These mixed-case exports use the Windows C calling convention for scalar arguments.
    const auto setInterface = mkl.find<SetLayer>("MKL_Set_Interface_Layer");
    const auto setThreading = mkl.find<SetLayer>("MKL_Set_Threading_Layer");
    const auto setThreads = mkl.find<SetThreads>("MKL_Set_Num_Threads_Local");
    const auto init = mkl.find<Init>("pardisoinit");
    const auto solve = mkl.find<Solve>("pardiso");
    if (!setInterface || !setThreading || !setThreads || !init || !solve ||
        setInterface(0) != 0 || setThreading(0) != 0) return false;

    Eigen::VectorXd rhs = force;
    displacement.resize(force.size());
    void* handle[64]{};
    int parameters[64]{};
    const int spd = 2, one = 1, quiet = 0, size = static_cast<int>(stiffness.rows());
    const int factorAndSolve = 13, release = -1;
    int error = 0, releaseError = 0;
    const int previousThreads = setThreads(threads);
    init(handle, &spd, parameters);
    parameters[0] = 1; // Use the initialized parameters with the overrides below.
    parameters[1] = 3; // Parallel nested dissection.
    parameters[34] = 1; // Zero-based column indices.

    // The lower triangle in column-major storage is the upper triangle in CSR.
    solve(handle, &one, &one, &spd, &factorAndSolve, &size, stiffness.valuePtr(), stiffness.outerIndexPtr(),
          stiffness.innerIndexPtr(), nullptr, &one, parameters, &quiet, rhs.data(), displacement.data(), &error);
    solve(handle, &one, &one, &spd, &release, &size, stiffness.valuePtr(), stiffness.outerIndexPtr(),
          stiffness.innerIndexPtr(), nullptr, &one, parameters, &quiet, rhs.data(), displacement.data(), &releaseError);
    setThreads(previousThreads);
    if (error || !displacement.allFinite()) return false;

    const Eigen::VectorXd residual = force - stiffness.selfadjointView<Eigen::Lower>() * displacement;
    return residual.allFinite() && residual.lpNorm<Eigen::Infinity>() <=
        std::max(1e-12, force.lpNorm<Eigen::Infinity>() * 1e-7);
#else
    (void)stiffness;
    (void)force;
    (void)threads;
    (void)displacement;
    return false;
#endif
}
} // namespace fem
