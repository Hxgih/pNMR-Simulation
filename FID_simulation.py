# This script simulates the FID signal of a pNMR probe.
#
# Author: René Reimann (2020)
#
# The ideas are based on DocDB #16856 and DocDB #11289
# https://gm2-docdb.fnal.gov/cgi-bin/private/ShowDocument?docid=16856
# https://gm2-docdb.fnal.gov/cgi-bin/private/ShowDocument?docid=11289

################################################################################
# Import first

import numpy as np
from scipy import integrate
from scipy import fftpack
from numericalunits import µ0, kB, hbar, mm, cm, m, s, ms, us, ns, Hz, kHz, MHz
from numericalunits import T, K, g, kg, mol, A, uV, mV, V

ppm = 1e-6
ppb = 1e-9
ppt = 1e-12
ppq = 1e-15
T0 = -273.15*K


class RingMagnet(object):
    """Class representing the magnetic field of a RingMagnet.

    The main magnetic field B0 is directing in y-direction.
    Deviations are described by multipoles.
    The strength of different multipoles can be set by
        magnet.An[multipole id] =  strength
    The magnetic field 3D vector can be calculated at any point (x,y,z) by
    calling the class instance.
    Further helper functions for pretty prints and unit handling are provided.
    """
    def __init__(self, B0):
        """
        Parameters:
        * B0: float, strength of main direction of the magnetic field.

        Note:
            * Main magnetic field is a dipole field in y-direction
            * You can set further multipole strength by
                  magnet.An[multipole id] = strength
            * Provide the correct unit for gradient strength, e.g. T/cm, ...
        """
        self.An = { # dipoles
                   1: 0*T,
                   2: B0,
                   3: 0*T,
                   # quadrupoles
                   4: 0*T/mm,
                   5: 0*T/mm,
                   6: 0*T/mm,
                   7: 0*T/mm,
                   8: 0*T/mm,
                   # sextupoles
                   9: 0*T/mm**2,
                  10: 0*T/mm**2,
                  11: 0*T/mm**2,
                  12: 0*T/mm**2,
                  13: 0*T/mm**2,
                  14: 0*T/mm**2,
                  15: 0*T/mm**2,
                  # octupole
                  16: 0*T/mm**3,
                  17: 0*T/mm**3,
                  18: 0*T/mm**3,
                  19: 0*T/mm**3,
                  20: 0*T/mm**3,
                  21: 0*T/mm**3,
                  22: 0*T/mm**3,
                  23: 0*T/mm**3,
                  24: 0*T/mm**3,
                 }

        self.P = { # dipoles
                   1: {"x": lambda x, y, z: 1, "y": lambda x, y, z: 0, "z": lambda x, y, z: 0},
                   2: {"x": lambda x, y, z: 0, "y": lambda x, y, z: 1, "z": lambda x, y, z: 0},
                   3: {"x": lambda x, y, z: 1, "y": lambda x, y, z: 0, "z": lambda x, y, z: 1},
                   # quadrupoles
                   4: {"x": lambda x, y, z: x, "y": lambda x, y, z: -y, "z": lambda x, y, z: 0},
                   5: {"x": lambda x, y, z: z, "y": lambda x, y, z: 0, "z": lambda x, y, z: x},
                   6: {"x": lambda x, y, z: 0, "y": lambda x, y, z: -y, "z": lambda x, y, z: z},
                   7: {"x": lambda x, y, z: y, "y": lambda x, y, z: x, "z": lambda x, y, z: 0},
                   8: {"x": lambda x, y, z: 0, "y": lambda x, y, z: z, "z": lambda x, y, z: y},
                   # sextupoles
                   9: {"x": lambda x, y, z: x**2-y**2, "y": lambda x, y, z: -2*x*y, "z": lambda x, y, z: 0},
                  10: {"x": lambda x, y, z: 2*x*z, "y": lambda x, y, z: -2*y*z, "z": lambda x, y, z: x**2-y**2},
                  11: {"x": lambda x, y, z: z**2-y**2, "y": lambda x, y, z: -2*x*y, "z": lambda x, y, z: 2*x*y},
                  12: {"x": lambda x, y, z: 0, "y": lambda x, y, z: -2*y*z, "z": lambda x, y, z: z**2-y**2},
                  13: {"x": lambda x, y, z: 2*x*y, "y": lambda x, y, z: x**2-y**2, "z": lambda x, y, z: 0},
                  14: {"x": lambda x, y, z: y*z, "y": lambda x, y, z: x*z, "z": lambda x, y, z: x*y},
                  15: {"x": lambda x, y, z: 0, "y": lambda x, y, z: z**2-y**2, "z": lambda x, y, z: 2*y*z},
                  # octupole
                  16: {"x": lambda x, y, z: x**3 - 3*x*y**2, "y": lambda x, y, z: y**3-3*x**2*y, "z": lambda x, y, z: 0},
                  17: {"x": lambda x, y, z: 3*x**2*z-3*z*y**2, "y": lambda x, y, z: -6*x*y*z, "z": lambda x, y, z: x**3 - 3*x*y**2},
                  18: {"x": lambda x, y, z: 3*x*z**2-3*x*y**2, "y": lambda x, y, z: -3*x**2*y-3*z**2*y+2*y**3, "z": lambda x, y, z: 3*x**2*z-3*z*y**2},
                  19: {"x": lambda x, y, z: z**3-3*z*y**2, "y": lambda x, y, z: -6*x*y*z, "z": lambda x, y, z: 3*x*z**2 - 3*x*y**2},
                  20: {"x": lambda x, y, z: 0, "y": lambda x, y, z: y**3-3*z**2*y, "z": lambda x, y, z: z**3-3*z*y**2},
                  21: {"x": lambda x, y, z: 3*x**2*y-y**3, "y": lambda x, y, z: x**3-3*x*y**2, "z": lambda x, y, z: 0},
                  22: {"x": lambda x, y, z: 6*x*y*z, "y": lambda x, y, z: 3*x**2*z-3*z*y**2, "z": lambda x, y, z: 3*x**2*y-y**3},
                  23: {"x": lambda x, y, z: 3*z**2*y-y**3, "y": lambda x, y, z: 3*x*z**2-3*x*y**2, "z": lambda x, y, z: 6*x*y*z},
                  24: {"x": lambda x, y, z: 0, "y": lambda x, y, z: z**3-3*z*y**2, "z": lambda x, y, z: 3*z**2*y-y**3},
                 }

    def B_field(self, x=0, y=0, z=0):
        """Evaluates magnetic field at position x, y, z

        Parameters:
        * x: float, x position
        * y: float, y position
        * z: float, z position

        Returns:
        * array of length 3,  Magnetic field at position (x,y,z)
        """
        Bx = 0
        By = 0
        Bz = 0
        for i in self.P.keys():
            Bx += self.An[i]*self.P[i]["x"](x, y, z)
            By += self.An[i]*self.P[i]["y"](x, y, z)
            Bz += self.An[i]*self.P[i]["z"](x, y, z)
        return [Bx, By, Bz]

    def __call__(self, x=0, y=0, z=0):
        """Evaluates magnetic field at position x, y, z

        Parameters:
        * x: float, x position
        * y: float, y position
        * z: float, z position

        Returns:
        * array of length 3,  Magnetic field at position (x,y,z)
        """
        return self.B_field(x, y, z)

    def strength_to_str(self, multipole, strength):
        """Pretty string for multipole strength.

        Parameters:
        * multipole: int, Number of the multipole, allowed range 1 - 24.
        * strength: float, relative strength of the multipole at 1 cm distance

        Returns:
        * string giving type, of multipole, strength of gradient and shape of multipole
        """
        str = "%.1f ppm"%(strength/ppm)
        if strength < 1*ppm:
            str = "%.1f ppb"%(strength/ppb)

        vec = self.multipole_vector_str(multipole)

        if 1<=multipole and multipole <= 3:
            return "Dipole: %s$\cdot %s^T$"%(str, vec)

        if 4<=multipole and multipole <= 8:
            return "Quadrupole: %s/cm$\cdot %s^T$"%(str, vec)

        if 9<=multipole and multipole <= 15:
            return "Sextupole: %s/cm$^2\cdot %s^T$"%(str, vec)

        if 16<=multipole and multipole <= 24:
            return "Octupole: %s/cm$^3\cdot %s^T$"%(str, vec)

    def multipole_vector_str(self, multipole):
        """String representation of a multipole

        Parameters:
        * multipole: int, number of multipole, allowed range 1 - 24

        Returns:
        * string, shape of multipole
        """
        if multipole==1: return "(1, 0, 0)"
        if multipole==2: return "(0, 1, 0)"
        if multipole==3: return "(0, 0, 1)"

        if multipole==4: return "(x, -y, 0)"
        if multipole==5: return "(z, 0, x)"
        if multipole==6: return "(0, -y, z)"
        if multipole==7: return "(y, x, 0)"
        if multipole==8: return "(0, z, y)"

        if multipole==9: return "(x^2-y^2, -2xy, 0)"
        if multipole==10: return "(2xz, -2yz, x^2-y^2)"
        if multipole==11: return "(z^2-y^2, -2xy, 2xy)"
        if multipole==12: return "(0, -2yz, z^2-y^2)"
        if multipole==13: return "(2xy, x^2-y^2, 0)"
        if multipole==14: return "(yz, xz, xy)"
        if multipole==15: return "(0, z^2-y^2, 2yz)"

        if multipole==16: return "(x^3-3xy^2, y^3-3x^2y,0)"
        if multipole==17: return "(3x^2z-3zy^2, -6xyz, x^3 - 3xy^2)"
        if multipole==18: return "(3xz^2-3xy^2, -3x^2y-3z^2y+2y^3, 3x^2z-3zy^2)"
        if multipole==19: return "(z^3-3zy^2, -6xyz, 3xz^2 - 3xy^2)"
        if multipole==20: return "(0, y^3-3z^2y, z^3-3zy^2)"
        if multipole==21: return "(3x^2y-y^3, x^3-3xy^2, 0)"
        if multipole==22: return "(6xyz, 3x^2z-3zy^2, 3x^2y-y^3)"
        if multipole==23: return "(3z^2y-y^3, 3xz^2-3xy^2, 6xyz)"
        if multipole==24: return "(0, z^3-3zy^2, 3z^2y-y^3)"

    def multipole_name(self, multipole):
        """Returns type of multipole as string

        Parameters:
        * multipole: int, number of multipole, allowed range 1 - 24

        Returns:
        * string, type of multipole
        """
        if 1 <= multipole and multipole <= 3:
            return "Dipole"
        if 4 <= multipole and multipole <= 8:
            return "Quadrupole"
        if 9 <= multipole and multipole <= 15:
            return "Sextupole"
        if 16 <= multipole and multipole <= 24:
            return "Octupole"
        raise ValueError("Multipoles are only defined for index 1 to 24.")

    def set_strength_at_1cm(self, multipole, strength):
        """Calculates DeltaB from multipole at 1 cm distance. Takes different
        units from different multipoles into account

        Parameters:
        * multipole: int, number of multipole, allowed range 1 - 24
        * strength: float, strength of gradient
        """

        if  multipole < 1 or multipole > 24:
            raise ValueError("Multipoles are only defined for index 1 to 24.")
        elif 4 <= multipole and multipole <= 8:
            strength /= cm
        elif 9 <= multipole and multipole <= 15:
            strength /= cm**2
        elif 16 <= multipole and multipole <= 24:
            strength /= cm**3
        self.An[multipole] = strength*self.An[2]


class StorageRingMagnet(RingMagnet):
    def __init__(self, B0=1.45*T):
        super().__init__(B0)


class Material(object):
    """ An Material instance holds material related properties """
    def __init__(self, name, formula=None, density=None, molar_mass=None, T1=None, T2=None, gyromagnetic_ratio=None):
        """Generate Material instance

        Parameters:
        * name: str, Name of the Material
        * formula: str, chemical formula of the Material
        * density: float, density of the material, e.g. in units of g/cm^3
        * molar_mass: float, molare Masse of the Material, e.g. in units of g/mol
        * T1: float, longitudinal relaxation time of the Material, e.g. in s
        * T2: float, transversal relaxation time of the Material, e.g. in s
        * gyromagnetic_ratio: float, gyromagnetic ration of protons shifted by material effects
        """
        # gyromagnetic ratio, value for free proton: 2.6752218744e8*Hz/T
        # magnetic moment,  value for free proton: 1.41060679736e-26*J/T
        self.name = name
        self.formula = formula
        self.density = density
        self.molar_mass = molar_mass
        self.T1 = T1
        self.T2 = T2
        self.gyromagnetic_ratio = gyromagnetic_ratio
        self.magnetic_moment = self.gyromagnetic_ratio*hbar/2

    def __str__(self):
        """String representation of the Material for pretty printing."""
        info = []
        if self.formula is not None:
            info.append(self.formula)
        if self.density is not None:
            info.append("%f g/cm^3"%(self.density/(g/cm**3)))
        if self.molar_mass is not None:
            info.append("%f g/mol"%(self.molar_mass/(g/mol)))
        if self.T1 is not None:
            info.append("%f ms"%(self.T1/ms))
        if self.T2 is not None:
            info.append("%f ms"%(self.T2/ms))
        if self.gyromagnetic_ratio is not None:
            info.append("%f Hz/T"%(self.gyromagnetic_ratio/(Hz/T)))
        return self.name + "(" + ", ".join(info) + ")"

    @property
    def number_density(self):
        # NA * density / molar_mass
        # the package numericalunits already converts "mol" using the Avrogardo
        # constant thus we do not need the extra factor if using numericalunits
        return self.density / self.molar_mass


PetroleumJelly = Material(name = "Petroleum Jelly",
                           formula = "C40H46N4O10",
                           density = 0.848*g/cm**3,
                           molar_mass = 742.8*g/mol,
                           T1 = 1*s,
                           T2 = 40*ms,
                           gyromagnetic_ratio=(2*np.pi)*61.79*MHz/(1.45*T),
                           )

sigma_H2O = lambda T: 25691e-9 - 10.36e-9*(T-(25*K+T0))/K
mag_susceptibility_H2O = lambda T: -9049e-9*(1 + 1.39e-4*(T-(20*K+T0))/K - 1.27e-7 *(T/K-(20+T0/K))**2 + 8.09e-10 *(T/K-(20+T0/K))**3 )
delta_b_H2O = lambda T: (0.49991537 - (1/3)) * mag_susceptibility_H2O(T)
omega_p_meas = lambda T: 2.6752218744e8*Hz/T*(1 - sigma_H2O(T) - delta_b_H2O(T) + 5.5*ppb )
PP_Water = Material(name = "Ultra-Pure ASTM Type 1 Water",
                           formula = "H2O",
                           density = 997*kg/m**3,
                           molar_mass = 18.01528*g/mol,
                           T1 = 3*s,
                           T2 = 3*s,
                           gyromagnetic_ratio=omega_p_meas(300*K),
                           )


class Coil(object):
    r"""A coil parametrized by number of turns, length, diameter and current.

    You can calculate the magnetic field cause by the coil at any point in space.
    """
    def __init__(self, turns, length, diameter, current):
        r""" Generates a coil objsect.

        Parameters:
        * turns: int
        * length: float
        * diameter: float
        * current: float
        """
        self.turns = turns
        self.length = length
        self.radius = diameter/2.
        self.current = current

    def B_field(self, x, y, z):
        r"""The magnetic field of the coil
        Assume Biot-Savart law
        vec(B)(vec(r)) = µ0 / 4π ∮ I dvec(L) × vec(r)' / |vec(r)'|³

        Approximations:
            - static, Biot-Savart law only holds for static current,
              in case of time-dependence use Jefimenko's equations.
              Jefimenko's equation:
              vec(B)(vec(r)) = µ0 / 4π ∫ ( J(r',tᵣ)/|r-r'|³ + 1/(|r-r'|² c)  ∂J(r',tᵣ)/∂t) × (r-r') d³r'
              with t_r = t-|r-r'|/c
              --> |r-r'|/c of order 0.1 ns
            - infinite small cables, if cables are extendet use the dV form
              vec(B)(vec(r))  = µ0 / 4π ∭_V  (vec(J) dV) × vec(r)' / |vec(r)'|³
            - closed loop
            - constant current, can factor out the I from integral
        """

        phi = np.linspace(0, 2*np.pi*self.turns, 10000)
        sPhi = np.sin(phi)
        cPhi = np.cos(phi)
        lx = self.radius*sPhi
        ly = self.radius*cPhi
        lz = self.length/2 * (phi/(np.pi*self.turns)-1)
        dlx = ly
        dly = -lx
        dlz = self.length/(2*np.pi*self.turns)

        dist = np.sqrt((lx-x)**2+(ly-y)**2+(lz-z)**2)

        integrand_x = ( dly * (z-lz) - dlz * (y-ly) ) / dist**3
        integrand_y = ( dlz * (x-lx) - dlx * (z-lz) ) / dist**3
        integrand_z = ( dlx * (y-ly) - dly * (x-lx) ) / dist**3

        B_x = µ0/(4*np.pi) * self.current * integrate.simps(integrand_x, x=phi)
        B_y = µ0/(4*np.pi) * self.current * integrate.simps(integrand_y, x=phi)
        B_z = µ0/(4*np.pi) * self.current * integrate.simps(integrand_z, x=phi)

        return [B_x, B_y, B_z]

    def Bz(self, z):
        """ This is an analytical solution for the B_z component along the x=y=0
        axis. We used the formula from "Experimentalphysik 2" Demtröder Section
        3.2.6 d) (Page 95/96, 5th edition)
        """
        n = self.turns / self.length
        I = self.current
        L = self.length
        R = self.coil.radius
        B_z = lambda z: µ0*n*I/2*((z+L/2)/np.sqrt(R**2+(z+L/2)**2)-(z-L/2)/np.sqrt(R**2+(z-L/2)**2))
        return B_z(z)


class Probe(object):
    def __init__(self, length, diameter, material, temp, B_field, coil, N_cells, seed):
        self.length = length
        self.radius = diameter / 2.
        self.V_cell = self.length * np.pi * self.radius**2

        self.material = material

        self.temp = temp
        self.B_field = B_field
        self.coil = coil

        self.rng = np.random.RandomState(seed)
        self.N_cells = N_cells

        self.initialize_cells(self.N_cells)

    def initialize_cells(self, N_cells):
        # place cells
        r = np.sqrt(self.rng.uniform(0,self.radius**2, size=N_cells))
        phi = self.rng.uniform(0, 2*np.pi, size=N_cells)
        self.cells_x = r*np.sin(phi)
        self.cells_y = r*np.cos(phi)
        self.cells_z = self.rng.uniform(-self.length/2., self.length/2., size=N_cells)

        # calculate quantities of cells
        B0 = np.array([self.B_field(x, y, z) for x, y, z in zip(self.cells_x, self.cells_y, self.cells_z)])
        self.cells_B0_x = B0[:,0]
        self.cells_B0_y = B0[:,1]
        self.cells_B0_z = B0[:,2]
        self.cells_B0 = np.sqrt(np.sum(B0**2, axis=-1))

        expon = self.material.magnetic_moment * self.cells_B0 / (kB*self.temp)
        self.cells_nuclear_polarization = (np.exp(expon) - np.exp(-expon))/(np.exp(expon) + np.exp(-expon))
        self.cells_magnetization = self.material.magnetic_moment * self.material.number_density * self.cells_nuclear_polarization
        # dipoles are aligned with the external field at the beginning
        self.cells_dipole_moment_mag = self.cells_magnetization * self.V_cell/N_cells

    def initialize_coil_field(self):
        # clculate B-field from coil for each cell
        B1 = np.array([self.coil.B_field(x, y, z) for x, y, z in zip(self.cells_x, self.cells_y, self.cells_z)])
        self.cells_B1_x = B1[:,0]
        self.cells_B1_y = B1[:,1]
        self.cells_B1_z = B1[:,2]
        self.cells_B1 = np.sqrt(np.sum(B1**2, axis=-1))

    def apply_rf_field(self, time=None):
        if time is None:
            time = self.t_90()

        if not hasattr(self, "cells_B1"):
            self.initialize_coil_field()

        # aproximation
        self.cells_mu_x = np.sin(self.material.gyromagnetic_ratio*self.cells_B1/2.*time)
        self.cells_mu_y = np.cos(self.material.gyromagnetic_ratio*self.cells_B1/2.*time)
        self.cells_mu_z = np.sin(self.material.gyromagnetic_ratio*self.cells_B1/2.*time)
        self.cells_mu_T = np.sqrt(self.cells_mu_x**2 + self.cells_mu_z**2)

    def apply_rf_field_nummerical(self,
                                  time=None,
                                  initial_condition=None,
                                  omega_rf=2*np.pi*61.79*MHz,
                                  with_relaxation=False,
                                  time_step=1.*ns,
                                  with_self_contribution=True):
        """Solves the Bloch Equation numerically for a RF pulse with length `time`
        and frequency `omega_rf`.

        Parameters:
            * time: Length of RF pulse (e.g. a pi/2 pulse time or pi pulse time)
                    If time is None, the pi/2 is estimated.
                    Default: None
            * initial_condition: Inital mu_x, mu_y, mu_z of cells.
                    Given as arrays of shap [3,N_cells]
                    If None the inital condition is assumed to be in equilibrium
                    and calculated from external B_field
                    Default: None
            * omega_rf: RF pulse frequency
                    If omega_rf is None, no RF pulse is applied and a Free
                    Induction Decay is happening
                    Default: 2 pi 61.79 MHz
            * with_relaxation: If true the relaxation terms are considered in the
                    Bloch equations. If false the relaxation terms are neglected.
                    Default: False
            * time_step: Float, maximal time step used in nummerical solution of
                    the Differential equation. Note that this value should be
                    sufficient smaller than the oscillation time scale.
                    Default: 1 ns
            * with_self_contribution: Boolean, if True we consider the additional
                    B-field from the magnetization of the cell.
                    Default: True
        Returns:
            * history: array of shape (7, N_time_steps)
                       times, mean_Mx, mean_My, mean_Mz, Mx(0,0,0), My(0,0,0), Mz(0,0,0)


        Note: all magnetizations are treated as relative parameters wrt to the
              equalibrium magnetization, i.e. all values are without units and
              restricted to -1 and 1.
        """

        if time is None:
            # if no time is given we estimate the pi/2 pulse duration and use that
            time = self.t_90()

        if initial_condition is None:
            # if no initial condition for the magnetization is given, we use the
            # equilibrium magnetization, which is aligned with the direction of
            # the external field.
            initial_condition = [self.cells_B0_x/self.cells_B0,
                                 self.cells_B0_y/self.cells_B0,
                                 self.cells_B0_z/self.cells_B0]

        if not hasattr(self, "cells_B1"):
            # if cells B1 is not yet calculated, calculate B1 components
            self.initialize_coil_field()

        # pulse frequency
        def Bloch_equation(t, M):
            M = M.reshape((3, self.N_cells))
            Mx, My, Mz = M[0], M[1], M[2]

            Bx = self.cells_B0_x
            By = self.cells_B0_y
            Bz = self.cells_B0_z
            if with_self_contribution:
                Bx = Bx + µ0*self.cells_magnetization*Mx
                By = By + µ0*self.cells_magnetization*My
                Bz = Bz + µ0*self.cells_magnetization*Mz
            if omega_rf is not None:
                rf_osci = np.sin(omega_rf*t)
                Bx = Bx + rf_osci * self.cells_B1_x
                By = By + rf_osci * self.cells_B1_y
                Bz = Bz + rf_osci * self.cells_B1_z
            dMx = self.material.gyromagnetic_ratio*(My*Bz-Mz*By)
            dMy = self.material.gyromagnetic_ratio*(Mz*Bx-Mx*Bz)
            dMz = self.material.gyromagnetic_ratio*(Mx*By-My*Bx)
            if with_relaxation:
                # note we approximate here that the external field is in y direction
                # in the ideal case we would calculate the B0_field direct and the ortogonal plane
                # note that we use relative magnetization , so the -1 is -M0
                dMx -= Mx/self.material.T2
                dMy -= (My-1)/self.material.T1
                dMz -= Mz/self.material.T2
            return np.array([dMx, dMy, dMz]).flatten()

        #solution = integrate.odeint(Bloch_equation,
        #                            y0=np.array(initial_condition).flatten(),
        #                            t=np.linspace(0., time, int(time/ns)))

        rk_res = integrate.RK45(Bloch_equation,
                                t0=0,
                                y0=np.array(initial_condition).flatten(),
                                t_bound=time,
                                max_step=0.1*ns)  # about 10 points per oscillation
        history = []

        idx = np.argmin(self.cells_x**2 + self.cells_y**2 + self.cells_z**2)
        M = None
        while rk_res.status == "running":
            M = rk_res.y.reshape((3, self.N_cells))
            Mx, My, Mz = M[0], M[1], M[2]                                       # 1
            #wx = self.cells_B1_x/np.sum(np.sort(self.cells_B1_x))
            #wy = self.cells_B1_y/np.sum(np.sort(self.cells_B1_y))
            #wz = self.cells_B1_z/np.sum(np.sort(self.cells_B1_z))
            #history.append([rk_res.t, np.sum(np.sort(Mx*wx)), np.sum(np.sort(My*wy)), np.sum(np.sort(Mz*wz)), Mx[idx], My[idx], Mz[idx]])
            history.append([rk_res.t, np.mean(Mx), np.mean(My), np.mean(Mz), Mx[idx], My[idx], Mz[idx]])
            rk_res.step()

        self.cells_mu_x = M[0]
        self.cells_mu_y = M[1]
        self.cells_mu_z = M[2]
        self.cells_mu_T = np.sqrt(self.cells_mu_x**2 + self.cells_mu_z**2)

        return history

    def t_90(self):
        brf = self.coil.B_field(0*mm,0*mm,0*mm)
        # B1 field strength is half of RF field
        b1 = np.sqrt(brf[0]**2+brf[1]**2+brf[2]**2)/2.
        t_90 = (np.pi/2)/(self.material.gyromagnetic_ratio*b1)
        return t_90

    def pickup_flux(self, t, mix_down=0*MHz, useAverage=True):
        # Φ(t) = Σ N B₂(r) * μ(t) / I
        # a mix down_frequency can be propergated through and will effect the
        # individual cells

        # flux in pickup coil depends on d/dt(B × μ)
        # --> y component static, no induction, does not contribute

        # d/dt ( μₜ sin(γₚ |B0| t) exp(-t/T2) )
        #       = μₜ [ d/dt( sin(γₚ |B0| t) ) exp(-t/T2) + sin(γₚ |B0| t) d/dt( exp(-t/T2) )]
        #       = μₜ [ γₚ |B0| cos(γₚ |B0| t) exp(-t/T2) + sin(γₚ |B0| t) (-1/T2) exp(-t/T2) ]
        #       = μₜ [ γₚ |B0| cos(γₚ |B0| t) -1/T2 * sin(γₚ |B0| t) ] exp(-t/T2)
        # make use of Addition theorem a cos(α) + b sin(α) = √(a² + b²) cos(α - arctan(-b/a))
        #       = μₜ √(γₚ² |B0|² + 1/T2²) cos(γₚ |B0| t - arctan(1/(T2γₚ |B0|)) exp(-t/T2)

        # a mix down_frequency can be propergated through and will effect the
        # individual cells, all operations before are linear
        # Note the mix down will only effect the

        # straight forward implementation
        # very inefficient
        # mu_x = lambda cell : cell.mu_T*np.sin((γₚ*cell.B0-mix_down)*t)*np.exp(-t/self.material.T2)
        # dmu_x_dt = lambda cell: cell.mu_T*np.sqrt((γₚ*cell.B0)**2 + 1/self.material.T2**2)*np.cos((γₚ*cell.B0-mix_down)*t - np.arctan(1/(self.material.T2*(γₚ*cell.B0)))*np.exp(-t/self.material.T2)
        # mu_y = lambda cell : cell.mu_z
        # dmu_y_dt = lambda cell: 0
        # mu_z = lambda cell : cell.mu_T*np.cos((γₚ*cell.B0-mix_down)*t)*np.exp(-t/self.material.T2)
        # dmu_z_dt = lambda cell: cell.mu_T*np.sqrt((γₚ*cell.B0)**2 + 1/self.material.T2**2)*np.sin((γₚ*cell.B0-mix_down)*t - np.arctan(1/(self.material.T2*(γₚ*cell.B0)))*np.exp(-t/self.material.T2)
        # return np.sum( [cell.B1.x * dmu_x_dt(cell) + cell.B1.y * dmu_y_dt(cell) + cell.B1.z * dmu_z_dt(cell) for cell in self.cells] )

        # From Faradays law we have
        # EMF = - d/dt (N * B * A)
        #     with vec(B)(t) = mu0 * vec(M)(t) = mu0 * M0 * vec(mu)(t)
        #     with vec(A) = pi*r^2 * vec(B_coil)/<B_coil>
        # EMF = N * pi * r^2 * mu0 * sum( vec(B_coil)/<B_coil> * M0 * d/dt( vec(mu)(t) ) )

        t = np.atleast_1d(t)

        magnitude = self.cells_mu_T*np.sqrt((self.material.gyromagnetic_ratio*self.cells_B0)**2 + 1/self.material.T2**2)
        phase = np.arctan(1./(self.material.T2*self.material.gyromagnetic_ratio*self.cells_B0))
        omega_mixed = (self.material.gyromagnetic_ratio*self.cells_B0-2*np.pi*mix_down)

        max_memory = 10000000
        N_cells = len(self.cells_B0)
        results = []
        idx_end = 0
        while idx_end != -1:
            idx_start = idx_end
            this_t = None
            if N_cells* len(t[idx_start:]) > max_memory:
                idx_end = idx_start + max_memory//N_cells
                this_t = t[idx_start:idx_end]
            else:
                idx_end = -1
                this_t = t[idx_start:]

            argument = np.outer(omega_mixed,this_t) - phase[:, None]
            # this is equal to Bx * dmu_x_dt + By * dmu_y_dt + Bz * dmu_z_dt
            # already assumed that dmu_y_dt is 0, so we can leave out that term
            B_x_dmu_dt = magnitude[:, None]*(self.cells_B1_x[:, None]*np.cos(argument) + self.cells_B1_z[:, None]*np.sin(argument))*(np.exp(-this_t/self.material.T2)[:, None]).T
            #return self.coil.turns * µ0 * np.sum(B_x_dmu_dt/self.cells_B1[:, None]*self.cells_magnetization[:, None], axis=0) * np.pi * self.coil.radius**2
            if useAverage:
                results.append(self.coil.turns * µ0 * np.sum(B_x_dmu_dt*self.cells_magnetization[:, None], axis=0) * np.pi * self.coil.radius**2 /np.mean(self.cells_B1[:, None]))
            else:
                results.append(self.coil.turns * µ0 * np.sum(B_x_dmu_dt*self.cells_magnetization[:, None]/self.cells_B1[:, None], axis=0) * np.pi * self.coil.radius**2)
            # Alternative
            # results.append(µ0 * np.mean(B_x_dmu_dt*self.cells_magnetization[:, None], axis=0) )/(self.cells_B1[:, None])
        results = np.concatenate(results)/N_cells
        return results


class Noise(object):
    r"""Class to generate noise and drift for time series. We plan to support
    different kind of noise and drift.
    """

    def __init__(self, white_noise=None, freq_power=None, scale_freq=None,
                 drift_lin=None,
                 drift_exp=None, drift_exp_time=None, rng=None):
        r"""Creates a Noise object that can be called to generate noise for time
        series.

        Parameters:
            - freq_power = Power of the f^alpha Power density spectrum. Default 1
            - drift_lin = strength of linear drift
            - drift_exp = strength of exponential dirft
            - rng = RandomState object used to generate random numbers.
        """
        self.freq_power = freq_power
        self.scale_freq = scale_freq
        self.white_noise = white_noise
        self.drift_lin = drift_lin
        self.drift_exp = drift_exp
        self.drift_exp_time = drift_exp_time
        self.rng = rng
        if self.rng is None:
            self.rng = np.random.RandomState()

    def get_freq_noise(self, times, rng):
        N = len(times)
        rand_noise = rng.normal(loc=0.0, scale=self.scale_freq, size=N)
        freq = np.fft.fftfreq(N, d=times[1]-times[0])
        fft  = fftpack.fft(rand_noise)
        fft[freq!=0] *= np.power(np.abs(freq[freq!=0]), 0.5*self.freq_power)
        fft[freq==0] = 0
        noise = fftpack.ifft(fft)
        return np.real(noise)

    def get_white_noise(self, times, rng):
        return rng.normal(loc=0.0, scale=self.white_noise)

    def get_linear_drift(self, times):
        return times*self.drift_lin

    def get_exp_drift(self, times):
        return  self.drift_exp*np.exp(-times/self.drift_exp_time)

    def __call__(self, times, rng=None):
        if rng is None: rng = self.rng
        noise = np.zeros_like(times)
        if self.freq_power is not None and self.scale_freq is not None:
            noise += self.get_freq_noise(times, rng=rng)
        if self.white_noise is not None:
            noise += self.get_white_noise(times, rng=rng)
        if self.drift_lin is not None:
            noise += self.get_linear_drift(times)
        if self.drift_exp is not None and self.drift_exp_time is not None:
            noise += self.get_exp_drift(times)
        return noise


class FixedProbe(Probe):
    def __init__(self, B_field, N_cells=1000, seed=12345):
        current = 0.7*A # ???
        fix_probe_coil = Coil(turns=30,
                              length=15.0*mm,
                              diameter=4.6*mm,
                              current=current)
        super().__init__(length = 30.0*mm,
                         diameter = 1.5*mm,
                         material = PetroleumJelly,
                         temp = (273.15 + 26.85) * K,
                         B_field = B_field,
                         coil = fix_probe_coil,
                         N_cells = N_cells,
                         seed = seed)


class PlungingProbe(Probe):
    def __init__(self, B_field, N_cells=1000, seed=12345):

        # L = 0.5 uH
        # C_p = 1-12 pF
        # C_s = 1-12 pF in series with L*C_p
        current = 0.7*A # ???

        plunging_probe_coil = Coil(turns=5.5,
                              length=10.0*mm,
                              diameter=15.065*mm+(0.97*mm/2),
                              current=current=)

        super().__init__(length = 228.6*mm,
                         diameter = 4.2065*mm,
                         material = PP_Water,
                         temp = (273.15 + 26.85) * K,
                         B_field = B_field,
                         coil = plunging_probe_coil,
                         N_cells = N_cells,
                         seed = seed)
