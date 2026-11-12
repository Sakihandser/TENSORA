# coding=utf-8
# --------------------------------------------------------------------
# Copyright (C) 1991 - 2026 - EDF - www.code-aster.org
# This file is part of code_aster.
#
# code_aster is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# code_aster is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with code_aster.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------

import numpy as NP

from . import TensorModule

try:
    from ...Utilities import sympy
    from sympy import Matrix, eye, zeros, ones, cos, sin, symbols

    X, Y, Z = sympy.symbols("X Y Z")
    ASTER_HAVE_SYMPY = True
except ImportError:
    ASTER_HAVE_SYMPY = False


def kron(i, j):
    return 1 if i == j else 0


def antikron(i, j):
    return 0.0 if i == j else 1.0


def dif(i, j, n, m):
    if i == n and j == m:
        return -1.0
    elif i == m and j == n:
        return 1.0
    else:
        return 0.0


def HookeIsotropic(E, NU):
    lamda = E * NU / ((1 + NU) * (1 - 2 * NU))
    mu = E / (2 * (1 + NU))
    C = NP.zeros((3, 3, 3, 3))
    for i in range(3):
        for j in range(3):
            for k in range(3):
                for l in range(3):
                    C[i][j][k][l] = lamda * kron(i, j) * kron(k, l) + mu * (
                        kron(i, k) * kron(j, l) + kron(i, l) * kron(j, k)
                    )
    return TensorModule.Tensor(C)


# definition des matrices des angles rotation nautique
def Rotation(alpha, beta, gamma):
    if not ASTER_HAVE_SYMPY:
        raise ImportError("Sympy is required for Rotation function")

    alpha, beta, gamma = map(float, (alpha, beta, gamma))
    Ralpha = NP.zeros((3, 3))
    for i in range(3):
        for j in range(3):
            Ralpha[i, j] = cos(alpha * antikron(i, 2)) * kron(i, j) + sympy.sin(
                alpha * dif(i, j, 0, 1)
            )

    Rotation = Ralpha  # sympy.Matrix(Ralpha.tolist())*sympy.Matrix(Rbeta.tolist())*sympy.Matrix(Rgamma.tolist())
    return TensorModule.Tensor(NP.array(Rotation.tolist()))


def HookeIsotropicP(E, NU):
    if not ASTER_HAVE_SYMPY:
        raise ImportError("Sympy is required for HookeIsotropicP")

    lamda = E * NU / ((1.0 + NU) * (1.0 - 2.0 * NU))
    mu = E / (2.0 * (1.0 + NU))

    A = (lamda * ones(3) + 2 * mu * eye(3)).row_join(zeros(3))
    B = zeros(3).row_join(mu * eye(3))
    C = A.col_join(B)

    return TensorModule.Tensor(NP.array(C.tolist()))


def HookeOrthotropic(E_L, E_T, E_N, NU_LT, NU_LN, NU_TN, G_LT, G_LN, G_TN):
    E_L = float(E_L)
    E_T = float(E_T)
    E_N = float(E_N)
    NU_LT = float(NU_LT)
    NU_TN = float(NU_TN)
    NU_LN = float(NU_LN)
    G_LT = float(G_LT)
    G_TN = float(G_TN)
    G_LN = float(G_LN)
    NU_TL = (E_T / E_L) * NU_LT
    NU_NT = (E_N / E_T) * NU_TN
    NU_NL = (E_N / E_L) * NU_LN
    DELTA = (1 - NU_TN * NU_NT - NU_NL * NU_LN - NU_LT * NU_TL - 2 * NU_TN * NU_NL * NU_LT) / (
        E_L * E_T * E_N
    )
    C_reduit = NP.resize(0.0, (6, 6))
    C_reduit[0, 0] = (1 - NU_TN * NU_NT) / (E_T * E_N)
    C_reduit[0, 1] = (NU_TL + NU_NL * NU_TN) / (E_T * E_N)
    C_reduit[0, 2] = (NU_NL + NU_TL * NU_NT) / (E_T * E_N)
    C_reduit[1, 0] = (NU_LT + NU_LN * NU_NT) / (E_L * E_N)
    C_reduit[1, 1] = (1 - NU_NL * NU_LN) / (E_L * E_N)
    C_reduit[1, 2] = (NU_NT + NU_LT * NU_NL) / (E_L * E_N)
    C_reduit[2, 0] = (NU_LN + NU_LT * NU_TN) / (E_L * E_T)
    C_reduit[2, 1] = (NU_TN + NU_TL * NU_LN) / (E_L * E_T)
    C_reduit[2, 2] = (1 - NU_LT * NU_TL) / (E_L * E_T)
    C_reduit[3, 3] = G_LT * DELTA
    C_reduit[4, 4] = G_LN * DELTA
    C_reduit[5, 5] = G_TN * DELTA
    C_reduit = C_reduit / DELTA
    C = NP.resize(0.0, (3, 3, 3, 3))
    I = NP.array([[0, 3, 4], [3, 1, 5], [4, 5, 2]])
    K = I
    for i in range(3):
        for j in range(3):
            for k in range(3):
                for l in range(3):
                    C[i][j][k][l] = C_reduit[I[i][j], K[k][l]]
    return TensorModule.Tensor(C)


def HookeOrthotropicOrienteQuelconque(
    E_L, E_T, E_N, NU_LT, NU_LN, NU_TN, G_LT, G_LN, G_TN, alpha, beta, gamma
):
    R = Rotation(alpha, beta, gamma)
    H_Ortho = HookeOrthotropic(E_L, E_T, E_N, NU_LT, NU_LN, NU_TN, G_LT, G_LN, G_TN)
    Tens = NP.resize(0.0, (3, 3, 3, 3))
    for i in range(3):
        for j in range(3):
            for k in range(3):
                for l in range(3):
                    for I in range(3):
                        for J in range(3):
                            for K in range(3):
                                for L in range(3):
                                    Tens[i][j][k][l] = (
                                        Tens[i][j][k][l]
                                        + R[i, I]
                                        * R[j, J]
                                        * R[k, K]
                                        * R[l, L]
                                        * H_Ortho[I][J][K][L]
                                    )
    return TensorModule.Tensor(Tens)
