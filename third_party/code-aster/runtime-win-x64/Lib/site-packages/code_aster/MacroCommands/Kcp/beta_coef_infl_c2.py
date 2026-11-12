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

import numpy as np


def coef_pts_C2(ix1, ix2, iy1, iy2):

    coef = np.array(
        [
            [
                [0.284, 0.284, 0.284, 0.284, 0.284],
                [0.284, 0.256, 0.231, 0.208, 0.187],
                [0.284, 0.233, 0.192, 0.158, 0.131],
                [0.285, 0.2, 0.141, 0.101, 0.072],
                [0.287, 0.160, 0.0904, 0.0525, 0.0314],
                [0.29, 0.136, 0.0661, 0.0339, 0.0186],
                [0.293, 0.12, 0.0525, 0.0251, 0.0133],
                [0.298, 0.101, 0.0387, 0.0174, 0.00926],
                [0.302, 0.0899, 0.032, 0.0143, 0.00779],
            ],
            [
                [0.262, 0.262, 0.262, 0.262, 0.262],
                [0.262, 0.236, 0.212, 0.191, 0.171],
                [0.263, 0.215, 0.176, 0.144, 0.118],
                [0.264, 0.184, 0.129, 0.0904, 0.0639],
                [0.266, 0.146, 0.0809, 0.0458, 0.0266],
                [0.269, 0.123, 0.0582, 0.0287, 0.015],
                [0.271, 0.108, 0.0455, 0.0206, 0.0103],
                [0.276, 0.09, 0.0326, 0.0136, 0.00673],
                [0.28, 0.079, 0.0264, 0.0108, 0.00548],
            ],
            [
                [0.229, 0.229, 0.229, 0.229, 0.229],
                [0.23, 0.206, 0.184, 0.165, 0.148],
                [0.23, 0.187, 0.152, 0.124, 0.101],
                [0.231, 0.159, 0.11, 0.0761, 0.0528],
                [0.233, 0.125, 0.0672, 0.0366, 0.0203],
                [0.235, 0.104, 0.0468, 0.0217, 0.0104],
                [0.236, 0.09, 0.0355, 0.0147, 0.00651],
                [0.239, 0.0732, 0.024, 0.00871, 0.00366],
                [0.242, 0.0633, 0.0185, 0.00639, 0.00274],
            ],
            [
                [0.195, 0.195, 0.195, 0.195, 0.195],
                [0.195, 0.174, 0.155, 0.139, 0.124],
                [0.195, 0.158, 0.128, 0.103, 0.0837],
                [0.195, 0.133, 0.091, 0.0622, 0.0426],
                [0.196, 0.103, 0.0541, 0.0286, 0.0152],
                [0.197, 0.0847, 0.0367, 0.0161, 0.00719],
                [0.198, 0.0726, 0.027, 0.0103, 0.00409],
                [0.2, 0.0577, 0.0173, 0.0055, 0.00194],
                [0.202, 0.049, 0.0127, 0.00369, 0.0013],
            ],
            [
                [0.163, 0.163, 0.163, 0.163, 0.163],
                [0.163, 0.146, 0.13, 0.116, 0.104],
                [0.163, 0.132, 0.106, 0.0857, 0.0692],
                [0.163, 0.111, 0.0751, 0.051, 0.0346],
                [0.164, 0.0848, 0.0439, 0.0228, 0.0119],
                [0.165, 0.0693, 0.0293, 0.0124, 0.00532],
                [0.165, 0.0589, 0.0212, 0.0077, 0.00285],
                [0.166, 0.0461, 0.013, 0.00382, 0.00119],
                [0.167, 0.0386, 0.00923, 0.00239, 0.000723],
            ],
            [
                [np.nan, np.nan, np.nan, np.nan, np.nan],
                [np.nan, np.nan, np.nan, np.nan, np.nan],
                [np.nan, np.nan, np.nan, np.nan, np.nan],
                [np.nan, np.nan, np.nan, np.nan, np.nan],
                [np.nan, np.nan, np.nan, np.nan, np.nan],
                [np.nan, np.nan, np.nan, np.nan, np.nan],
                [np.nan, np.nan, np.nan, np.nan, np.nan],
                [np.nan, np.nan, np.nan, np.nan, np.nan],
                [np.nan, np.nan, np.nan, np.nan, np.nan],
            ],
        ]
    )

    return coef[ix1, iy1, :], coef[ix2, iy1, :], coef[ix1, iy2, :], coef[ix2, iy2, :]
