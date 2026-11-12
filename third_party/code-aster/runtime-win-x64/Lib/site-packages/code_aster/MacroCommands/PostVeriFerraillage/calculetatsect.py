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
from scipy.optimize import fsolve
from ...Messages import UTMESS


class sectionELU:
    """
    Class definition for the computation of the parameters related to the section state at ULS
    """

    def __init__(
        self,
        marge,
        code,
        uc,
        clacier,
        typdiag,
        epais,
        csup,
        cinf,
        fyk,
        fck,
        alphacc,
        Es,
        gammab,
        gammas,
        Asinf,
        Assup,
        N,
        M,
        Nrd,
        Mrd,
    ):

        # Propriétes générales
        self.marge = marge
        self.code = code
        self.uc = uc
        self.clacier = clacier
        self.typdiag = typdiag
        self.h = epais
        self.csup = csup
        self.cinf = cinf
        self.fyk = fyk
        self.fck = fck
        self.alphacc = alphacc
        self.Es = Es
        self.gammab = gammab
        self.gammas = gammas
        # self.Asinf = Asinf
        # self.Assup = Assup
        self.N = N
        self.M = M
        self.Nrd = Nrd
        self.Mrd = Mrd

        if self.marge < 0:
            UTMESS("A", "VERIFERRAILLAGE_17")
            self.N = Nrd
            self.M = Mrd

        if self.code == 1:
            # Propriétés béton
            self.epsilon_cu = 3.5e-3
            self.epsilon_c2 = 2.0e-3
            self.n = 2.0
            self.fcd = self.alphacc * self.fck / self.gammab

            # Propriétés acier
            self.epsilon_smax = 10e-3
            self.fyd = self.fyk / self.gammas
            self.epsilon_yd = self.fyd / self.Es

        if self.code == 2:
            if self.uc == 0:
                self.unite_pa = 1.0e-6
            elif self.uc == 1:
                self.unite_pa = 1.0

            if self.clacier == 0:
                self.epsilon_smax = 0.9 * 2.5e-2
                self.ktys = 1.05
            elif clacier == 1:
                self.epsilon_smax = 0.9 * 5.0e-2
                self.ktys = 1.08
            else:
                self.epsilon_smax = 0.9 * 7.5e-2
                self.ktys = 1.15

            self.epsilon_cu = min(
                3.5e-3,
                0.26 * 0.01 + 3.5 * 0.01 * (((90.0 - self.fck * self.unite_pa) / 100.0) ** 4),
            )
            self.epsilon_c2 = 2.0e-3
            if (self.fck * self.unite_pa) >= (50.0):
                self.epsilon_c2 = 0.2 * 0.01 + 0.0085 * 0.01 * (
                    (self.fck * self.unite_pa - 50.0) ** (0.53)
                )

            self.n = min(2.0, 1.4 + 23.4 * (((90.0 - self.fck * self.unite_pa) / 100.0) ** 4))
            self.fyd = self.fyk / self.gammas
            self.fcd = self.fck * self.alphacc / self.gammab
            self.epsilon_yd = self.fyd / self.Es

        # Propriétés section
        dinf = self.h - self.cinf
        dsup = self.h - self.csup
        self.b = 1

        if M >= 0:
            self.d = dinf
            self.dp = self.csup
            self.Asinf = Asinf
            self.Assup = Assup
        else:
            self.d = dsup
            self.dp = self.cinf
            self.Asinf = Assup
            self.Assup = Asinf

    def concrete_force(self, x, curv):
        """Computes the compression force on the concrete.

        This function computes the integral of the stress over the area of
        compressed concrete

        Arguments:
            x: the depth of the neutral axis
            curv: slope of the strain diagram
        Returns:
            Fc: the value of the compresion force on the concrete
        """
        # calcul de alpha

        epsilon_concrete = self.epsilon(x, curv)[0]

        # calcul de la hauteur comprimée
        upper_bound = max(0, min(x, self.h))

        # calcul de la profondeur de ec2
        xc = 0
        if epsilon_concrete > self.epsilon_c2:
            xc = x * (1 - self.epsilon_c2 / epsilon_concrete)

        Fc = 0

        if (x > 0) & (epsilon_concrete > 0):

            A = epsilon_concrete / self.epsilon_c2
            temp1 = x / (3.0 * A)
            temp2 = A * (upper_bound / x - 1.0) + 1.0
            temp3 = A * (xc / x - 1.0) + 1.0

            Fc = self.fcd * (upper_bound - temp1 * (temp2**3 - temp3**3))

        return Fc

    def concrete_moment(self, x, curv):
        """Computes the moment on the concrete with respect to the center of gravity
            of the uncracked section.

        This function computes the integral of the stress times the distance
         with respect to the center of gravity of the uncracked section over the area of
        compressed concrete

        Arguments:
            x: the depth of the neutral axis
            curv: slope of the strain diagram
        Returns:
            Mc: the value of the moment on the concrete with respect to the center of
            gravity of the uncracked section
        """

        epsilon_concrete = self.epsilon(x, curv)[0]
        # calcul de la hauteur comprimée
        upper_bound = max(0, min(x, self.h))

        # calcul de la profondeur de ec2
        xc = 0
        if epsilon_concrete > self.epsilon_c2:
            xc = x * (1 - self.epsilon_c2 / epsilon_concrete)
        if epsilon_concrete > self.epsilon_cu:
            epsilon_concrete = self.epsilon_cu

        # Initialisation of the resultant vector
        Mc = 0

        if (x > 0) & (epsilon_concrete > 0):

            A = epsilon_concrete / self.epsilon_c2

            temp1 = (self.h / 2 - xc) ** 2
            temp2 = (self.h / 2 - upper_bound) ** 2

            M1 = self.b * self.fcd / 2 * (temp1 - temp2)

            M2 = self.b * self.fcd * xc / 2 * (self.h - xc)

            temp3 = x / 3 / A * (x - self.h / 2)
            temp4 = (1 - A / x * (x - xc)) ** 3
            temp5 = (1 - A / x * (x - upper_bound)) ** 3
            M31 = self.b * self.fcd * temp3 * (temp4 - temp5)
            temp6 = (
                1 / 2 * (x - xc) ** 2
                - 2 / 3 * A / x * (x - xc) ** 3
                + 1 / 4 * A**2 / x**2 * (x - xc) ** 4
            )
            temp7 = (
                1 / 2 * (x - upper_bound) ** 2
                - 2 / 3 * A / x * (x - upper_bound) ** 3
                + 1 / 4 * A**2 / x**2 * (x - upper_bound) ** 4
            )

            M32 = self.b * self.fcd * (temp6 - temp7)

            Mc = M1 + M2 - M31 - M32

        return Mc

    def sigma_steel(self, epsilon):
        """Computes the stress on the reinforcement steel.

        This function computes the stress on the reinforcement steel using the
        material law.

        Arguments:
            epsilon: strain of the steel
        Returns:
            sigma: stress on th steel
        """
        if abs(epsilon) <= self.epsilon_yd:
            sigma = self.Es * epsilon
        else:
            if self.typdiag == 1:
                sigma = np.sign(epsilon) * self.fyd
            else:
                A = (
                    self.fyd
                    * (self.ktys * self.epsilon_yd - self.epsilon_smax)
                    / (self.epsilon_yd - self.epsilon_smax)
                )
                B = (self.ktys * self.fyd - self.fyd) / (self.epsilon_smax - self.epsilon_yd)
                sigma = A * np.sign(epsilon) + B * epsilon
        return sigma

    def steel_force(self, x, curv):
        """Computes the force on the top and bottom reinforcement steel.

        This function computes the force on the top and bottom reinforcement steel as the product
        between the stress and the are of steel

        Arguments:
            x: the depth of the neutral axis
            curv: slope of the strain diagram
        Returns:
            Fs (a list): the first value is the force on the bottom steel and the
            second value is the force on the top steel
        """

        # Calcul de la déformation des aciers

        epsilon_inf = self.epsilon(x, curv)[1]
        epsilon_sup = self.epsilon(x, curv)[2]

        # Calcul des tensions dans les aciers

        sigma_sinf = self.sigma_steel(epsilon_inf)
        sigma_ssup = self.sigma_steel(epsilon_sup)

        # Calcul des forces dans les aciers
        Fsinf = self.Asinf * sigma_sinf
        Fssup = self.Assup * sigma_ssup

        return [Fsinf, Fssup]

    def compute_residual_ELU(self, unknown):
        """Computes the residual of the set of equations representing
             the equilibrium of the section to translation and rotation of the section.

        This function computes the difference between the external forces and internal
        forces (axial force and bending moment)

        Arguments:
            unknown(a list): the first value is the depth of the neutral axis and
            the second value is the slope of the strain diagram

        Returns:
            f (a list): the first value is the residual of the equilibrium to translation
            and the second value the residual of the equilibrium to rotation of the section
        """

        x, curv = unknown

        f1 = (
            self.N
            - self.b * self.concrete_force(x, curv)
            - self.steel_force(x, curv)[0]
            - self.steel_force(x, curv)[1]
        )
        f2 = (
            abs(self.M)
            - self.concrete_moment(x, curv)
            - self.steel_force(x, curv)[0] * (self.h / 2 - self.d)
            - self.steel_force(x, curv)[1] * (self.h / 2 - self.dp)
        )
        return [f1, f2]

    def epsilon(self, x, curv):
        """Computes the strain on the top fiber of concrete
        and the reinforcement steel.

        This function computes the strain on the top fiber of concrete and
        on the reinforcement steel using the Bernoulli hypothesis
        Arguments:
            x: the depth of the neutral axis
            curv: slope of the strain diagram
        Returns:
            epsilon (a list) : the first value is the strain on the top fiber of concrete
            the second value is the strain on the bottom reinforcement and the third value is
            the strain on the top reinforcement
        """
        epsilon_inf = -curv * (self.d - x)
        epsilon_sup = -curv * (self.dp - x)
        epsilon_concrete = max(0, x * curv)
        epsilon_C = max(0, -curv * (3 / 7 * self.h - x))

        return [epsilon_concrete, epsilon_inf, epsilon_sup, epsilon_C]

    def compute_x_and_curv_ELU(self, X0):
        """Computes the depth of neutral axis and the slope of the strain diagram
            required for the equilibrium of the section.

        This function computes the equilibrium configuration at the ULS using the
        Newton-Raphson iterations

        Arguments:
            X0: starting point of the NR iterations
        Returns:
            x (a list): the first value is the the depth of the neutral axis and the
            second value is the slope of the strain diagram.
        """

        x = fsolve(self.compute_residual_ELU, X0, epsfcn=1e-15)
        return x

    def compute_etat_section_ELU(self, X0):
        """Computes the parameters related to the section state at ULS

        This function computes the parameters related to the section state at ULS,
        by computing first the strain configuration, from which the stress is calculated
        by using material law

        Arguments:
            X0 (a list): starting point of the NR iterations. The first value is the
            depth of the neutral axis and the second value is the slope of the strain diagram
        Returns:
            hc: the height of the compressed part of the section
            epsilon (a list): the first value is the strain on the top fiber of concrete
                the second value is the strain on the bottom reinforcement and the third value is
                the strain on the top reinforcement
            sigma (a list): the first value is the stress on the top fiber of concrete
                the second value is the stress on the bottom reinforcement and the third value is
                the stress on the top reinforcement
        """

        # On initialise les valeurs en sorties à -1
        hc = -1
        epsilon = [-1, -1, -1]
        sigma = [-1, -1, -1]

        # On élimine les cas ou la classe du béton dépasse 50 MPa. Les valeurs retournées sont égales a -1
        if self.code == 2:
            if self.fck * self.unite_pa > 50:
                UTMESS("A", "VERIFERRAILLAGE_16")
            elif self.marge == 2.0:
                UTMESS("A", "VERIFERRAILLAGE_11")
            else:

                # On calcule la profondeur de l'axez neutre et la courbure
                x, curv = self.compute_x_and_curv_ELU(X0)

                # On calcule la hauteur comprimée
                hc = max(0, min(x, self.h))

                # On calcule els déformations
                epsilon = self.epsilon(x, curv)

                # On calcule les tensions
                sigma_concrete = self.fcd * (1 - (1 - epsilon[0] / self.epsilon_c2) ** 2)
                if epsilon[0] >= self.epsilon_c2:
                    sigma_concrete = self.fcd

                sigma_steel_inf = self.Es * epsilon[1]
                if abs(epsilon[1]) > self.epsilon_yd:
                    sigma_steel_inf = np.sign(epsilon[1]) * self.fyd

                sigma_steel_sup = self.Es * epsilon[2]
                if abs(epsilon[2]) > self.epsilon_yd:
                    sigma_steel_sup = np.sign(epsilon[2]) * self.fyd

                sigma = [sigma_concrete, sigma_steel_inf, sigma_steel_sup]

                if self.M < 0:
                    hc = max(0, min(x, self.h))
                    curv = -curv
                    sigma[1], sigma[2] = sigma[2], sigma[1]
                    epsilon[1], epsilon[2] = epsilon[2], epsilon[1]

        return [hc, epsilon, sigma]


class sectionELS:
    """
    Class definition for the computation of the parameters related to the section state at SLS
    """

    def __init__(
        self,
        marge,
        epais,
        csup,
        cinf,
        sigmaxs,
        sigmaxbsup,
        sigmaxbinf,
        Es,
        n,
        Asinf,
        Assup,
        N,
        M,
        Nrd,
        Mrd,
    ):

        # Propriétes générales
        self.marge = marge
        self.h = epais
        self.csup = csup
        self.cinf = cinf
        self.Es = Es
        self.n = n
        self.N = N
        self.M = M
        self.sigmaxs = sigmaxs
        self.sigmaxbsup = sigmaxbsup
        self.sigmaxbinf = sigmaxbinf
        self.Nrd = Nrd
        self.Mrd = Mrd

        if self.marge < 0:
            UTMESS("A", "VERIFERRAILLAGE_17")
            self.N = Nrd
            self.M = Mrd

        # Propriétés section
        dinf = self.h - self.cinf
        dsup = self.h - self.csup
        self.b = 1

        if M >= 0:
            self.d = dinf
            self.dp = self.csup
            self.Asinf = Asinf
            self.Assup = Assup

        else:
            self.d = dsup
            self.dp = self.cinf
            self.Asinf = Assup
            self.Assup = Asinf

    def compute_etat_section_ELS(self):
        """Computes the parameters related to the section state at SLS

        This function computes the parameters related to the section state at SLS,
        by computing first the strain configuration, from which the stress is calculated
        by using material law

        Arguments:
           Empty
        Returns:
            hc: the height of the compressed part of the section
            epsilon (a list): the first value is the strain on the top fiber of concrete,
                the second value is the strain and the bottom fiber of cocnrete,
                the third value is the strain on the bottom reinforcement and
                the fourth value is the strain on the top reinforcement
            sigma (a list): the first value is the stress on the top fiber of concrete
                the second value is the stress on the bottom reinforcement and the third value is
                the stress on the top reinforcement

        """
        # On calcule la profondeur de l'axez neutre et la courbure
        x, curv = self.compute_x_and_curv_ELS()

        # On calcule la hauteur comprimée
        hc = max(0, min(x, self.h))

        if curv != 0:

            # On calcule les déformations
            epsilon = self.epsilon(x, curv)

            # On calcule les tensions
            sigma_concrete_sup = self.Es / self.n * epsilon[0]
            sigma_concrete_inf = self.Es / self.n * epsilon[1]
            sigma_steel_inf = self.Es * epsilon[2]
            sigma_steel_sup = self.Es * epsilon[3]

        else:
            # On calcule les tensions
            if np.sign(self.N) == -1:
                # Traction uniforme
                sigma_concrete_sup = 0
                sigma_concrete_inf = 0
                sigma_steel_inf = self.N / 2 / self.Asinf
                sigma_steel_sup = self.N / 2 / self.Assup
            else:
                # Compression uniforme
                Astot = self.Asinf + self.Assup
                sigma_concrete_sup = self.N / (self.h * self.b + self.n * Astot)
                sigma_concrete_inf = self.N / (self.h * self.b + self.n * Astot)
                sigma_steel_inf = self.n * sigma_concrete_sup
                sigma_steel_sup = self.n * sigma_concrete_sup

            # On calcule les déformations
            epsilon = [0, 0, 0, 0, 0]
            epsilon[0] = sigma_concrete_sup / self.Es * self.n
            epsilon[1] = sigma_concrete_inf / self.Es * self.n
            epsilon[2] = sigma_steel_inf / self.Es
            epsilon[3] = sigma_steel_sup / self.Es

        sigma = [sigma_concrete_sup, sigma_concrete_inf, sigma_steel_inf, sigma_steel_sup]

        if self.M < 0:
            hc = max(0, min(x, self.h))
            curv = -curv
            sigma[2], sigma[3] = sigma[3], sigma[2]
            epsilon[2], epsilon[3] = epsilon[3], epsilon[2]

        return [hc, epsilon, sigma]

    def compute_x_and_curv_ELS(self):
        """Computes the depth of neutral axis and the slope of the strain diagram
            required for the equilibrium of the section.

        This function computes the equilibrium configuration at the ULS using the
        Cardan approach to solve a polynomial equation of degree 3.

        Arguments:
            Empty
        Returns:
            x (a list): the first value is the the depth of the neutral axis and the
            second value is the slope of the strain diagram.
        """

        if self.N != 0:

            # calcul de l'eccentricité
            e = abs(self.M) / self.N

            x1 = -1
            x2 = -1
            x3 = -1

            # On suppose que la section est partiellement comprimée

            # Equation de l'axe neutre: ax**3 + bx**2 + cx + d=0

            A = 1 / 6
            B = e / 2 - self.h / 4
            C = self.n * self.Assup * (e - self.h / 2 + self.dp) + self.n * self.Asinf * (
                e - self.h / 2 + self.d
            )
            D = self.n * self.Assup * self.dp * (
                self.h / 2 - self.dp - e
            ) + self.n * self.Asinf * self.d * (self.h / 2 - self.d - e)
            # Calcul de la position de l'axe neutre
            p = (3 * A * C - B**2) / (3 * A**2)
            q = (2 * B**3 - 9 * A * B * C + 27 * A**2 * D) / (27 * A**3)

            delta = (q / 2) ** 2 + (p / 3) ** 3

            if delta > 0:
                u = np.cbrt((-q / 2 + np.sqrt(delta)))
                v = np.cbrt((-q / 2 - np.sqrt(delta)))
                x1 = -B / 3 / A + u + v

            elif delta < 0:
                theta = np.arccos(-q / 2 * np.sqrt(-27 / p**3))
                x1 = -B / 3 / A + 2 * np.sqrt(-p / 3) * np.cos(theta / 3)
                x2 = -B / 3 / A + 2 * np.sqrt(-p / 3) * np.cos(theta / 3 + 2 / 3 * np.pi)
                x3 = -B / 3 / A + 2 * np.sqrt(-p / 3) * np.cos(theta / 3 + 4 / 3 * np.pi)
            else:
                x1 = 2 * np.cbrt(-q / 2)
                x2 = -np.cbrt(-q / 2)
                x3 = x2

            X = [x1, x2, x3]

            x = [xi for xi in X if ((xi > 0) & (xi <= self.h))]
            x = x[0] if len(x) == 1 else None

            if x is not None:

                curv = (
                    self.N
                    / (self.Es / self.n)
                    / (
                        x**2 / 2
                        + self.n * self.Assup * (x - self.dp)
                        + self.n * self.Asinf * (x - self.d)
                    )
                )

            else:

                # la section est soit entierement tendue soit entierement comprimée

                if self.N >= 0:
                    # La section est entierement comprimée
                    A = (
                        self.n * self.Assup * (e - self.h / 2 + self.dp)
                        + self.n * self.Asinf * (e - self.h / 2 + self.d)
                        + self.h * e
                    )
                    B = (
                        self.n * self.Assup * self.dp * (self.h / 2 - self.dp - e)
                        + self.n * self.Asinf * self.d * (self.h / 2 - self.d - e)
                        - self.h**3 / 12
                        - self.h**2 / 2 * e
                    )
                else:
                    # La section est entierement tendue
                    A = self.Assup * (e - self.h / 2 + self.dp) + self.Asinf * (
                        e - self.h / 2 + self.d
                    )
                    B = self.Assup * self.dp * (self.h / 2 - self.dp - e) + self.Asinf * self.d * (
                        self.h / 2 - self.d - e
                    )

                # Calcul de la position de l'axe neutre
                if A != 0:
                    x = -B / A
                    curv = (
                        self.N
                        / (self.Es / self.n)
                        / (
                            (1 + np.sign(self.N)) / 2 * (2 * x - self.h) * self.h / 2
                            + self.n * self.Assup * (x - self.dp)
                            + self.n * self.Asinf * (x - self.d)
                        )
                    )
                else:
                    x = np.sign(self.N) * 10000 * self.h
                    curv = 0
        else:
            # On est en flexion simple
            x, curv = 0, 0
            if self.M != 0:
                A = self.b / 2
                B = self.n * (self.Assup + self.Asinf)
                C = -self.n * (self.Assup * self.dp + self.Asinf * self.d)
                delta = B**2 - 4 * A * C
                if delta >= 0:
                    x = (-B + np.sqrt(delta)) / 2 / A
                    # Calcul du moment quadratique
                    I = (
                        self.b * x**3 / 3
                        + self.n * self.Asinf * (self.d - x) ** 2
                        + self.n * self.Assup * (self.dp - x) ** 2
                    )
                    curv = abs(self.M) / I / self.Es * self.n
                else:
                    UTMESS("A", "VERIFERRAILLAGE_19")

        return [x, curv]

    def epsilon(self, x, curv):
        """Computes the strain on the top and bottom fiber of concrete
        and the reinforcement steel.

        This function computes the strain on the top and bottom fiber of concrete and
        on the reinforcement steel using the Bernoulli hypothesis
        Arguments:
            x: the depth of the neutral axis
            curv: slope of the strain diagram
        Returns:
            epsilon (a list) : the first value is the strain on the top fiber of concrete,
            the second value is the strain on the bottom fiber of concrete
            the third value is the strain on the bottom reinforcement and the third value is
            the fourth on the top reinforcement
        """
        epsilon_inf = -curv * (self.d - x)
        epsilon_sup = -curv * (self.dp - x)
        epsilon_concrete_sup = max(0, x * curv)
        epsilon_concrete_inf = max(0, -curv * (self.h - x))
        return [epsilon_concrete_sup, epsilon_concrete_inf, epsilon_inf, epsilon_sup]
