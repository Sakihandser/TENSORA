#pragma once

#include <Eigen/SparseCore>

namespace fem {
bool TryParallelSparseSolve(const Eigen::SparseMatrix<double>& stiffness, const Eigen::VectorXd& force,
                           int threads, Eigen::VectorXd& displacement);
}
