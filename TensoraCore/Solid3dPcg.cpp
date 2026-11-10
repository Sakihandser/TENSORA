#include "OpenClApi.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <fcntl.h>
#include <io.h>
#include <omp.h>
#include <vector>

namespace {
using fem::opencl::Check;
using fem::opencl::OpenClApi;
constexpr unsigned maxIterations = 8000;
constexpr size_t workgroup = 128;

template<class T> void read(T* data, size_t count) {
    if (fread(data, sizeof(T), count, stdin) != count) throw std::runtime_error("incomplete PCG input");
}

struct Matrix {
    std::vector<cl_uint> offsets, columns;
    std::vector<double> blocks, inverse, force;
    unsigned rows;
    double tolerance;
    Matrix() {
        cl_uint header[3];
        read(header, 3);
        rows = header[1];
        const auto nonzero = header[2];
        if (header[0] != 0x31474350 || !rows || rows > 350000 || !nonzero || nonzero > 15000000)
            throw std::runtime_error("invalid PCG header");
        read(&tolerance, 1);
        offsets.resize(rows + 1);
        columns.resize(nonzero);
        blocks.resize(size_t(nonzero) * 9);
        inverse.resize(size_t(rows) * 3);
        force.resize(inverse.size());
        read(offsets.data(), offsets.size());
        read(columns.data(), columns.size());
        read(blocks.data(), blocks.size());
        read(inverse.data(), inverse.size());
        read(force.data(), force.size());
        if (offsets.front() || offsets.back() != nonzero || !std::is_sorted(offsets.begin(), offsets.end()) ||
            *std::max_element(columns.begin(), columns.end()) >= rows)
            throw std::runtime_error("invalid PCG matrix");
    }
};

struct Solution { unsigned iterations; std::vector<double> x; };

Solution cpu(const Matrix& a) {
    omp_set_num_threads(std::min(8, omp_get_num_procs()));
    const int size = static_cast<int>(a.force.size());
    std::vector<double> x(size), r=a.force, p(size), z(size), ap(size);
    double rz=0, norm=0;
    for (int i=0; i<size; i++) { p[i]=r[i]*a.inverse[i]; rz+=r[i]*p[i]; norm+=r[i]*r[i]; }
    unsigned iteration=0;
    const double target=a.tolerance*a.tolerance;
    for (; iteration<maxIterations && norm>target; iteration++) {
        double pap=0;
        #pragma omp parallel for schedule(static) reduction(+:pap)
        for (int row=0; row<static_cast<int>(a.rows); row++) {
            const int i=3*row;
            double u=0,v=0,w=0;
            for (auto j=a.offsets[row]; j<a.offsets[row+1]; j++) {
                const double* b=&a.blocks[size_t(j)*9];
                const double* q=&p[size_t(a.columns[j])*3];
                u+=b[0]*q[0]+b[1]*q[1]+b[2]*q[2];
                v+=b[3]*q[0]+b[4]*q[1]+b[5]*q[2];
                w+=b[6]*q[0]+b[7]*q[1]+b[8]*q[2];
            }
            ap[i]=a.inverse[i]?u:0;
            ap[i+1]=a.inverse[i+1]?v:0;
            ap[i+2]=a.inverse[i+2]?w:0;
            pap+=p[i]*ap[i]+p[i+1]*ap[i+1]+p[i+2]*ap[i+2];
        }
        if (!(pap>0)) throw std::runtime_error("PCG matrix is not positive definite");
        const double alpha=rz/pap;
        double next=0;
        norm=0;
        #pragma omp parallel for schedule(static) reduction(+:next,norm)
        for (int i=0; i<size; i++) {
            x[i]+=alpha*p[i];
            r[i]-=alpha*ap[i];
            z[i]=r[i]*a.inverse[i];
            next+=r[i]*z[i];
            norm+=r[i]*r[i];
        }
        const double beta=next/rz;
        rz=next;
        #pragma omp parallel for schedule(static)
        for (int i=0; i<size; i++) p[i]=z[i]+beta*p[i];
    }
    return {iteration,std::move(x)};
}

const char* source=R"CLC(
#pragma OPENCL EXTENSION cl_khr_fp64 : enable
// Each workgroup reduces its contribution. Only partial sums cross PCIe.
void reduce(__local double2* localSum, double2 value, __global double2* sums) {
    uint lane=get_local_id(0);
    localSum[lane]=value;
    for (uint stride=get_local_size(0)/2; stride>0; stride/=2) {
        barrier(CLK_LOCAL_MEM_FENCE);
        if (lane<stride) localSum[lane]+=localSum[lane+stride];
    }
    if (lane==0) sums[get_group_id(0)]=localSum[0];
}
__kernel void product(uint rows, __global const uint* offsets, __global const uint* columns,
    __global const double* blocks, __global const double* inverse, __global const double* p,
    __global double* ap, __global double2* sums, __local double2* scratch) {
    uint row=get_global_id(0);
    double pap=0;
    if (row<rows) {
        double3 sum=(double3)(0);
        for (uint j=offsets[row]; j<offsets[row+1]; j++) {
            __global const double* b=blocks+9*j;
            double3 v=vload3(columns[j],p);
            sum.x+=dot(vload3(0,b),v);
            sum.y+=dot(vload3(1,b),v);
            sum.z+=dot(vload3(2,b),v);
        }
        sum=select((double3)(0),sum,vload3(row,inverse)!=(double3)(0));
        vstore3(sum,row,ap);
        pap=dot(sum,vload3(row,p));
    }
    reduce(scratch,(double2)(pap,0),sums);
}
__kernel void advance(uint size, double alpha, __global const double* inverse,
    __global double* x, __global double* r, __global const double* p, __global const double* ap,
    __global double* z, __global double2* sums, __local double2* scratch) {
    uint i=get_global_id(0);
    double2 value=(double2)(0);
    if (i<size) {
        x[i]+=alpha*p[i];
        double next=r[i]-alpha*ap[i];
        r[i]=next;
        z[i]=next*inverse[i];
        value=(double2)(next*z[i],next*next);
    }
    reduce(scratch,value,sums);
}
__kernel void direction(uint size, double beta, __global const double* z, __global double* p) {
    uint i=get_global_id(0);
    if (i<size) p[i]=z[i]+beta*p[i];
}
)CLC";

struct Gpu {
    OpenClApi api;
    cl_context context=nullptr;
    cl_command_queue queue=nullptr;
    cl_program program=nullptr;
    std::vector<cl_mem> buffers;
    std::vector<cl_kernel> kernels;
    ~Gpu() {
        for (auto buffer:buffers) api.clReleaseMemObject(buffer);
        for (auto kernel:kernels) api.clReleaseKernel(kernel);
        if (program) api.clReleaseProgram(program);
        if (queue) api.clReleaseCommandQueue(queue);
        if (context) api.clReleaseContext(context);
    }
    void initialize() {
        cl_uint count=0, best=0;
        Check(api.clGetPlatformIDs(0,nullptr,&count),"enumerate OpenCL platforms");
        std::vector<cl_platform_id> platforms(count);
        Check(api.clGetPlatformIDs(count,platforms.data(),nullptr),"get OpenCL platforms");
        cl_device_id selected=nullptr;
        for (auto platform:platforms) {
            if (api.clGetDeviceIDs(platform,CL_DEVICE_TYPE_GPU,0,nullptr,&count)!=CL_SUCCESS) continue;
            std::vector<cl_device_id> devices(count);
            Check(api.clGetDeviceIDs(platform,CL_DEVICE_TYPE_GPU,count,devices.data(),nullptr),"get GPUs");
            for (auto device:devices) {
                cl_device_fp_config fp64=0;
                cl_bool available=CL_FALSE, compiler=CL_FALSE;
                cl_uint units=0;
                api.clGetDeviceInfo(device,CL_DEVICE_DOUBLE_FP_CONFIG,sizeof(fp64),&fp64,nullptr);
                api.clGetDeviceInfo(device,CL_DEVICE_AVAILABLE,sizeof(available),&available,nullptr);
                api.clGetDeviceInfo(device,CL_DEVICE_COMPILER_AVAILABLE,sizeof(compiler),&compiler,nullptr);
                api.clGetDeviceInfo(device,CL_DEVICE_MAX_COMPUTE_UNITS,sizeof(units),&units,nullptr);
                if (fp64 && !(fp64&CL_FP_SOFT_FLOAT) && available && compiler && units>best) {
                    best=units; selected=device;
                }
            }
        }
        if (!selected) throw std::runtime_error("no compatible OpenCL FP64 GPU");
        cl_int error;
        context=api.clCreateContext(nullptr,1,&selected,nullptr,nullptr,&error);
        Check(error,"create OpenCL context");
        queue=api.clCreateCommandQueue(context,selected,0,&error);
        Check(error,"create OpenCL queue");
        program=api.clCreateProgramWithSource(context,1,&source,nullptr,&error);
        Check(error,"create OpenCL program");
        error=api.clBuildProgram(program,1,&selected,"-cl-std=CL1.2",nullptr,nullptr);
        if (error!=CL_SUCCESS) {
            char log[4096]{};
            api.clGetProgramBuildInfo(program,selected,CL_PROGRAM_BUILD_LOG,sizeof(log),log,nullptr);
            throw std::runtime_error(std::string("compile PCG kernels: ")+log);
        }
    }
    template<class T> cl_mem upload(const std::vector<T>& values, cl_mem_flags access) {
        return buffer(values.size()*sizeof(T),access|CL_MEM_COPY_HOST_PTR,const_cast<T*>(values.data()));
    }
    cl_mem buffer(size_t size, cl_mem_flags flags=CL_MEM_READ_WRITE, void* data=nullptr) {
        cl_int error;
        auto value=api.clCreateBuffer(context,flags,size,data,&error);
        Check(error,"allocate GPU buffer");
        buffers.push_back(value);
        return value;
    }
    cl_kernel kernel(const char* name) {
        cl_int error;
        auto value=api.clCreateKernel(program,name,&error);
        Check(error,name);
        kernels.push_back(value);
        return value;
    }
    template<class T> void arg(cl_kernel kernel, cl_uint i, const T& value) {
        Check(api.clSetKernelArg(kernel,i,sizeof(T),&value),"set kernel argument");
    }
    void local(cl_kernel kernel, cl_uint i) {
        Check(api.clSetKernelArg(kernel,i,workgroup*2*sizeof(double),nullptr),"set local scratch");
    }
    void enqueue(cl_kernel kernel, size_t groups) {
        const size_t global=groups*workgroup;
        Check(api.clEnqueueNDRangeKernel(queue,kernel,1,nullptr,&global,&workgroup,0,nullptr,nullptr),"run GPU kernel");
    }
    void download(cl_mem buffer, size_t size, void* target) {
        Check(api.clEnqueueReadBuffer(queue,buffer,CL_TRUE,0,size,target,0,nullptr,nullptr),"read GPU results");
    }
};

Solution gpu(const Matrix& a) {
    Gpu g;
    g.initialize();
    const auto size=static_cast<cl_uint>(a.force.size());
    const auto groups=[](size_t n){return (n+workgroup-1)/workgroup;};
    const size_t rowGroups=groups(a.rows), vectorGroups=groups(size), bytes=size*sizeof(double);
    std::vector<double> x(size),p(size),partial(vectorGroups*2);
    double rz=0,norm=0;
    for (cl_uint i=0;i<size;i++) {p[i]=a.force[i]*a.inverse[i];rz+=a.force[i]*p[i];norm+=a.force[i]*a.force[i];}
    auto offsets=g.upload(a.offsets,CL_MEM_READ_ONLY),columns=g.upload(a.columns,CL_MEM_READ_ONLY);
    auto blocks=g.upload(a.blocks,CL_MEM_READ_ONLY),inverse=g.upload(a.inverse,CL_MEM_READ_ONLY);
    auto bx=g.upload(x,CL_MEM_READ_WRITE),bp=g.upload(p,CL_MEM_READ_WRITE),br=g.upload(a.force,CL_MEM_READ_WRITE);
    auto bz=g.buffer(bytes),ap=g.buffer(bytes),sums=g.buffer(partial.size()*sizeof(double));
    auto product=g.kernel("product"),advance=g.kernel("advance"),direction=g.kernel("direction");
    g.arg(product,0,a.rows);g.arg(product,1,offsets);g.arg(product,2,columns);g.arg(product,3,blocks);
    g.arg(product,4,inverse);g.arg(product,5,bp);g.arg(product,6,ap);g.arg(product,7,sums);g.local(product,8);
    g.arg(advance,0,size);g.arg(advance,2,inverse);g.arg(advance,3,bx);g.arg(advance,4,br);
    g.arg(advance,5,bp);g.arg(advance,6,ap);g.arg(advance,7,bz);g.arg(advance,8,sums);g.local(advance,9);
    g.arg(direction,0,size);g.arg(direction,2,bz);g.arg(direction,3,bp);
    unsigned iteration=0;
    const double target=a.tolerance*a.tolerance;
    for (;iteration<maxIterations&&norm>target;iteration++) {
        g.enqueue(product,rowGroups);
        g.download(sums,rowGroups*2*sizeof(double),partial.data());
        double pap=0;
        for (size_t j=0;j<rowGroups;j++) pap+=partial[2*j];
        if (!(pap>0)) throw std::runtime_error("GPU PCG matrix is not positive definite");
        g.arg(advance,1,rz/pap);g.enqueue(advance,vectorGroups);
        g.download(sums,partial.size()*sizeof(double),partial.data());
        double next=0;
        norm=0;
        for (size_t j=0;j<vectorGroups;j++) {next+=partial[2*j];norm+=partial[2*j+1];}
        g.arg(direction,1,next/rz);g.enqueue(direction,vectorGroups);
        rz=next;
    }
    g.download(bx,bytes,x.data());
    return {iteration,std::move(x)};
}
} // namespace

int main(int argc,char** argv) {
    _setmode(_fileno(stdin),_O_BINARY);
    _setmode(_fileno(stdout),_O_BINARY);
    try {
        if (argc!=2 || (std::string(argv[1])!="gpu" && std::string(argv[1])!="cpu"))
            throw std::runtime_error("use Solid3dPcg.exe cpu or gpu");
        const Matrix matrix;
        const auto result=std::string(argv[1])=="gpu"?gpu(matrix):cpu(matrix);
        if (fwrite(&result.iterations,sizeof(unsigned),1,stdout)!=1 ||
            fwrite(result.x.data(),sizeof(double),result.x.size(),stdout)!=result.x.size())
            throw std::runtime_error("could not write PCG solution");
        return 0;
    } catch(const std::exception& error) {
        std::fprintf(stderr,"%s\n",error.what());
        return 1;
    }
}
