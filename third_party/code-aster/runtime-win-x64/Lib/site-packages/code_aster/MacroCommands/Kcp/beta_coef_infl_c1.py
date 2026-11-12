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


def coef_pts_C1(ix1, ix2, iy1, iy2):

    coef = np.array(
        [
            [
                [0.263, 0.263, 0.263, 0.263, 0.263],
                [0.264, 0.238, 0.214, 0.193, 0.174],
                [0.264, 0.217, 0.178, 0.147, 0.121],
                [0.265, 0.186, 0.131, 0.0927, 0.0661],
                [0.267, 0.148, 0.0832, 0.048, 0.0285],
                [0.270, 0.125, 0.0605, 0.0308, 0.0167],
                [0.272, 0.111, 0.0479, 0.0226, 0.0119],
                [0.277, 0.093, 0.0351, 0.0156, 0.00821],
                [0.281, 0.083, 0.029, 0.0127, 0.00691],
            ],
            [
                [0.244, 0.244, 0.244, 0.244, 0.244],
                [0.245, 0.22, 0.197, 0.177, 0.16],
                [0.245, 0.2, 0.164, 0.134, 0.11],
                [0.246, 0.171, 0.119, 0.0836, 0.0589],
                [0.248, 0.135, 0.0747, 0.042, 0.0242],
                [0.251, 0.114, 0.0534, 0.0261, 0.0135],
                [0.253, 0.1, 0.0416, 0.0186, 0.00916],
                [0.257, 0.083, 0.0295, 0.0121, 0.00591],
                [0.261, 0.073, 0.0238, 0.00958, 0.0048],
            ],
            [
                [0.215, 0.215, 0.215, 0.215, 0.215],
                [0.216, 0.193, 0.173, 0.155, 0.139],
                [0.216, 0.176, 0.143, 0.116, 0.0945],
                [0.217, 0.149, 0.103, 0.0711, 0.0492],
                [0.219, 0.117, 0.0626, 0.034, 0.0187],
                [0.22, 0.097, 0.0434, 0.02, 0.0095],
                [0.222, 0.084, 0.0328, 0.0134, 0.00587],
                [0.224, 0.068, 0.022, 0.00786, 0.00324],
                [0.227, 0.0587, 0.0169, 0.00571, 0.0024],
            ],
            [
                [0.185, 0.185, 0.185, 0.185, 0.185],
                [0.185, 0.165, 0.147, 0.132, 0.118],
                [0.185, 0.15, 0.121, 0.0979, 0.0792],
                [0.185, 0.126, 0.0861, 0.0588, 0.0402],
                [0.186, 0.0974, 0.0511, 0.027, 0.0143],
                [0.187, 0.0801, 0.0346, 0.0151, 0.0067],
                [0.188, 0.0686, 0.0254, 0.00963, 0.00378],
                [0.19, 0.0544, 0.0161, 0.00508, 0.00176],
                [0.191, 0.0461, 0.0118, 0.00337, 0.00116],
            ],
            [
                [0.156, 0.156, 0.156, 0.156, 0.156],
                [0.156, 0.139, 0.124, 0.111, 0.0991],
                [0.156, 0.126, 0.102, 0.082, 0.0662],
                [0.156, 0.106, 0.0719, 0.0487, 0.0331],
                [0.157, 0.0811, 0.042, 0.0218, 0.0113],
                [0.158, 0.0662, 0.0279, 0.0118, 0.00505],
                [0.158, 0.0563, 0.0202, 0.00731, 0.0027],
                [0.159, 0.044, 0.0124, 0.0036, 0.00111],
                [0.16, 0.0368, 0.00874, 0.00223, 0.000665],
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
