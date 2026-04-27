"""Simulation tools for classical and quantum-interference-inspired profilometry."""

from .surfaces import load_surface_sur, make_surface
from .sim_classical import simulate_psi4
from .sim_quantum import simulate_coincidence, simulate_coincidence_psi4
from .reconstruct import reconstruct_psi4, height_from_phase
from .metrics import roughness_metrics
