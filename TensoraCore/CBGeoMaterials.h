#pragma once
// Material kernels accept a ParticleBase pointer but do not dereference it.
// Exclude the unused MPM particle/mesh implementation at this build boundary.
#define MPM_PARTICLE_H_
#define MPM_PARTICLEBASE_H_
#ifndef _USE_MATH_DEFINES
#define _USE_MATH_DEFINES
#endif
#include <memory>
#include <vector>
#include <string>
#include <materials/linear_elastic.h>
#include <materials/mohr_coulomb.h>
